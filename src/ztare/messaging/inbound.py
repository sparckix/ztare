"""inbound.py — unified abstract inbound-message channel.

Operator 2026-05-17: the agent should receive steering from ANY of
{telegram, orbit, interactive} through ONE abstraction — so headless /
tmux / conversational are the same to the agent (the GP-241 thesis:
access-mode is irrelevant once the channel is uniform; enforcement is
the membrane's job, not this channel's).

This is the INVERSE of the GP-241 propose→verificator inbox: that is
the agent's only OUTPUT path (gated); this is a uniform INPUT path
(advisory — it carries human steering, it is NOT an enforcement gate,
so it deliberately does not have the membrane's fail-closed rigor;
worst case a message is missed, never a laundering hole).

Design: a `MessageSource` ABC with `poll()`. Concrete sources:
  - InteractiveSource: a watched local inbox dir (drop a .txt / write
    a line) — fully implemented + testable now; this is the tmux /
    "type to it" path and the headless poll-an-inbox hybrid.
  - TelegramSource: reads the existing VPS telegram bot's free-text
    spool (the bot already polls; today it only routes STOP/STATUS —
    this consumes its NL spool when present; degrades empty if absent).
  - OrbitSource: reads the orbit-sync message store (governance UI).
`MessageInbox` aggregates the configured sources, dedupes by id, and
returns time-ordered `InboundMessage`s for the agent's next turn/loop.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path

from src.ztare.common.paths import REPO_ROOT

# Inbound spool roots. Outside the agent's official-state path on
# purpose (input ≠ official state). Env-overridable for the VPS.
INBOUND_ROOT = Path(os.environ.get(
    "ZTARE_INBOUND_ROOT", str(REPO_ROOT / "ztare_workspace" / "inbound")))


@dataclass(frozen=True)
class InboundMessage:
    source: str          # "interactive" | "telegram" | "orbit"
    ts: str              # ISO-8601 UTC
    sender: str          # best-effort identity ("operator", chat id, …)
    text: str
    msg_id: str          # stable dedupe key

    def as_dict(self) -> dict:
        return asdict(self)


def _mid(source: str, ts: str, text: str) -> str:
    return source + ":" + hashlib.sha1(
        f"{ts}|{text}".encode("utf-8", "ignore")).hexdigest()[:16]


class MessageSource(ABC):
    name: str = "abstract"

    @abstractmethod
    def poll(self) -> list[InboundMessage]:
        """Return any NEW messages. Must be best-effort and NEVER raise
        (a flaky channel must not break the agent loop)."""


class InteractiveSource(MessageSource):
    """Watched inbox dir: write a `.txt` file (or append lines to
    `inbox.log`) and the agent picks it up next poll. This is the
    tmux/"type to it" path AND the headless poll-an-inbox hybrid —
    same abstraction, no daemon-vs-interactive split."""
    name = "interactive"

    def __init__(self, root: Path | None = None) -> None:
        self.dir = (root or INBOUND_ROOT) / "interactive"
        self.seen = self.dir / ".seen"

    def poll(self) -> list[InboundMessage]:
        out: list[InboundMessage] = []
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            seen = set()
            if self.seen.is_file():
                seen = set(self.seen.read_text(
                    encoding="utf-8", errors="ignore").split())
            for f in sorted(self.dir.glob("*.txt")):
                if f.is_symlink() or not f.is_file():
                    continue
                ts = time.strftime(
                    "%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(f.stat().st_mtime))
                text = f.read_text(encoding="utf-8", errors="ignore").strip()
                if not text:
                    continue
                mid = _mid("interactive", ts, text)
                if mid in seen:
                    continue
                out.append(InboundMessage(
                    "interactive", ts, "operator", text, mid))
                seen.add(mid)
            if out:
                self.seen.write_text(" ".join(sorted(seen)),
                                     encoding="utf-8")
        except Exception:
            return out  # never raise into the agent loop
        return out


class _SpoolSource(MessageSource):
    """Shared impl for telegram/orbit: each backend (the existing VPS
    telegram bot / orbit-sync) writes free-text it received into a
    JSONL spool; we consume rows we haven't seen. If the backend/spool
    is absent (e.g. on the laptop) this degrades to empty — no error,
    no fabricated traffic."""

    def __init__(self, name: str, spool: Path) -> None:
        self.name = name
        self.spool = spool
        self.cursor = spool.with_suffix(".cursor")

    def poll(self) -> list[InboundMessage]:
        out: list[InboundMessage] = []
        try:
            if not self.spool.is_file():
                return out
            done = 0
            if self.cursor.is_file():
                done = int(self.cursor.read_text(errors="ignore") or 0)
            lines = self.spool.read_text(
                encoding="utf-8", errors="ignore").splitlines()
            for ln in lines[done:]:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    r = json.loads(ln)
                except Exception:
                    continue
                text = str(r.get("text", "")).strip()
                if not text:
                    continue
                ts = str(r.get("ts") or time.strftime(
                    "%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()))
                sender = str(r.get("sender") or r.get("chat_id") or "?")
                out.append(InboundMessage(
                    self.name, ts, sender, text,
                    _mid(self.name, ts, text)))
            self.cursor.write_text(str(len(lines)), encoding="utf-8")
        except Exception:
            return out
        return out


class TelegramSource(_SpoolSource):
    def __init__(self, root: Path | None = None) -> None:
        super().__init__(
            "telegram",
            (root or INBOUND_ROOT) / "telegram" / "nl_spool.jsonl")


class OrbitSource(MessageSource):
    """Consumes Orbit's EXISTING per-role chat artifact
    (org/sessions/<role>/chat/<day>.jsonl, written by orbit
    git-sync.ts /api/chat/send — rows {id, ts, sender, text}). NO new
    spool, NO orbit-server edit: reuse the existing mechanism (the
    operator's 'update existing, don't duplicate' rule). Dedupe on the
    row's own stable `id`. Scans today + yesterday across all roles."""
    name = "orbit"

    def __init__(self, sessions_root: Path | None = None) -> None:
        self.root = sessions_root or (REPO_ROOT / "org" / "sessions")
        self.seen = INBOUND_ROOT / "orbit" / ".seen_ids"

    def poll(self) -> list[InboundMessage]:
        out: list[InboundMessage] = []
        try:
            if not self.root.is_dir():
                return out
            seen: set[str] = set()
            if self.seen.is_file():
                seen = set(self.seen.read_text(
                    encoding="utf-8", errors="ignore").split())
            days = {time.strftime("%Y-%m-%d", time.gmtime()),
                    time.strftime("%Y-%m-%d",
                                  time.gmtime(time.time() - 86400))}
            for chatf in sorted(self.root.glob("*/chat/*.jsonl")):
                if chatf.is_symlink() or not chatf.is_file():
                    continue
                if chatf.stem not in days:
                    continue
                role = chatf.parent.parent.name
                for ln in chatf.read_text(
                        encoding="utf-8", errors="ignore").splitlines():
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        r = json.loads(ln)
                    except Exception:
                        continue
                    rid = str(r.get("id") or "")
                    text = str(r.get("text", "")).strip()
                    if not rid or not text or rid in seen:
                        continue
                    out.append(InboundMessage(
                        "orbit",
                        str(r.get("ts") or time.strftime(
                            "%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())),
                        f"{r.get('sender', 'principal')}@{role}",
                        text, "orbit:" + rid))
                    seen.add(rid)
            if out:
                self.seen.parent.mkdir(parents=True, exist_ok=True)
                self.seen.write_text(" ".join(sorted(seen)),
                                     encoding="utf-8")
        except Exception:
            return out
        return out


class MessageInbox:
    """Aggregates configured sources into one time-ordered, deduped
    stream the agent drains each turn/loop. Default = all three."""

    def __init__(self, sources: list[MessageSource] | None = None) -> None:
        self.sources = sources or [
            InteractiveSource(), TelegramSource(), OrbitSource()]

    def drain(self) -> list[InboundMessage]:
        msgs: dict[str, InboundMessage] = {}
        for s in self.sources:
            for m in s.poll():
                msgs.setdefault(m.msg_id, m)  # dedupe by stable id
        return sorted(msgs.values(), key=lambda m: (m.ts, m.source))


def main() -> int:
    import sys
    inbox = MessageInbox()
    drained = [m.as_dict() for m in inbox.drain()]
    print(json.dumps({"count": len(drained), "messages": drained},
                      indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
