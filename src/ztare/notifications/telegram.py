"""Bidirectional Telegram channel for GP-128 / GP-128b manager comms.

Replaces ntfy.sh (retired 2026-04-25). The principal interacts with the
manager via a Telegram bot:

  * OUTBOUND (manager → principal): high-priority alerts via
    ``push_notification``; lightweight replies via ``reply``.
  * INBOUND (principal → manager): polled at each tick via
    ``poll_inbound``; commands STOP / PAUSE / RESUME / STATUS /
    DIRECTIVE are recognised, free-form text falls through as DIRECTIVE.

Stdlib-only (urllib + json) so it has zero pip dependencies.

Usage from agent / cron tick:
    from src.ztare.notifications.telegram import poll_inbound, push_notification
    messages = poll_inbound(consume=True)  # returns list[InboundMessage]
    push_notification(title="...", message="...", priority="high")

Or via CLI:
    python scripts/poll_telegram.py --consume
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional


# ── Config ────────────────────────────────────────────────────────────

CREDS_PATH = Path("org/mandates/.telegram_creds")  # gitignored
INBOUND_LOG = Path("org/sessions/inbound.jsonl")    # session-agnostic for now
OFFSET_PATH = Path("org/mandates/.telegram_offset") # gitignored
TELEGRAM_API_BASE = "https://api.telegram.org"

# Recognised explicit command verbs. Anything else falls through to
# DIRECTIVE.
EXPLICIT_VERBS = {"STOP", "PAUSE", "RESUME", "STATUS", "DIRECTIVE"}

log = logging.getLogger(__name__)


@dataclass
class Creds:
    bot_token: str
    principal_chat_id: int


@dataclass
class InboundMessage:
    update_id: int
    chat_id: int
    timestamp_unix: int
    raw_text: str
    command: str            # one of EXPLICIT_VERBS or "DIRECTIVE"
    payload: str            # the text after the verb (or the whole text)
    authorized: bool        # passed chat_id allowlist
    auth_reason: str        # "ok" or rejection reason


# ── Cred loading ──────────────────────────────────────────────────────

def _load_creds() -> Optional[Creds]:
    """Load bot token + principal chat_id from gitignored creds file.

    File format (key=value, one per line, '#'-prefixed comments OK):

        bot_token=123456:ABCDEF...
        principal_chat_id=123456789

    Returns None if the file is missing or malformed; caller should
    treat as "channel not yet configured" and skip silently.
    """
    if not CREDS_PATH.exists():
        return None
    try:
        kv: dict[str, str] = {}
        for line in CREDS_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            kv[k.strip()] = v.strip()
        token = kv.get("bot_token", "")
        chat_id_raw = kv.get("principal_chat_id", "")
        if not token or not chat_id_raw:
            log.warning("telegram creds incomplete at %s", CREDS_PATH)
            return None
        return Creds(bot_token=token, principal_chat_id=int(chat_id_raw))
    except Exception as exc:  # noqa: BLE001
        log.warning("could not parse telegram creds: %s", exc)
        return None


# ── Offset persistence ───────────────────────────────────────────────

def _load_offset() -> int:
    if not OFFSET_PATH.exists():
        return 0
    try:
        return int(OFFSET_PATH.read_text(encoding="utf-8").strip() or "0")
    except Exception:
        return 0


def _save_offset(offset: int) -> None:
    OFFSET_PATH.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_PATH.write_text(str(offset), encoding="utf-8")


# ── Telegram API ──────────────────────────────────────────────────────

def _api_call(token: str, method: str, params: dict, timeout: float = 5.0) -> Optional[dict]:
    url = f"{TELEGRAM_API_BASE}/bot{token}/{method}"
    qs = urllib.parse.urlencode(params)
    full = f"{url}?{qs}" if qs else url
    try:
        with urllib.request.urlopen(full, timeout=timeout) as resp:
            if 200 <= resp.status < 300:
                return json.loads(resp.read().decode("utf-8"))
            log.warning("telegram api %s status=%d", method, resp.status)
            return None
    except urllib.error.URLError as exc:
        log.warning("telegram api network error: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning("telegram api unexpected error: %s", exc)
        return None


# ── Message parsing ──────────────────────────────────────────────────

def _classify(text: str) -> tuple[str, str]:
    """Return (command, payload). Default command is 'DIRECTIVE'."""
    t = text.strip()
    if not t:
        return ("DIRECTIVE", "")
    # Explicit verb prefix: case-insensitive match on first whitespace token
    head, _, tail = t.partition(" ")
    head_norm = head.upper().rstrip(":").rstrip(".")
    if head_norm in EXPLICIT_VERBS:
        return (head_norm, tail.strip())
    # Bare verbs without payload (STOP, PAUSE, RESUME, STATUS)
    if head_norm in EXPLICIT_VERBS and not tail:
        return (head_norm, "")
    # Default: treat whole text as DIRECTIVE
    return ("DIRECTIVE", t)


def _authorize(chat_id: int, principal_chat_id: int) -> tuple[bool, str]:
    if chat_id != principal_chat_id:
        return (False, f"chat_id_mismatch (saw {chat_id}, expected {principal_chat_id})")
    return (True, "ok")


# ── Public API ────────────────────────────────────────────────────────

def poll_inbound(consume: bool = True, max_messages: int = 50) -> list[InboundMessage]:
    """Fetch new messages from Telegram.

    Parameters
    ----------
    consume : bool
        If True (default), advance the offset so subsequent polls skip
        these messages. Set False for a non-destructive peek.
    max_messages : int
        Cap on messages returned per call. Telegram's limit is 100.

    Returns
    -------
    list[InboundMessage]
        Empty list if channel unconfigured, no new messages, or auth
        failures across the board.
    """
    creds = _load_creds()
    if creds is None:
        return []

    offset = _load_offset()
    params = {
        "offset": offset,
        "limit": min(max_messages, 100),
        "timeout": 0,  # short poll; the agent's tick is the cadence
    }
    resp = _api_call(creds.bot_token, "getUpdates", params, timeout=5.0)
    if resp is None or not resp.get("ok"):
        return []

    out: list[InboundMessage] = []
    new_offset = offset
    for update in resp.get("result", []):
        update_id = int(update.get("update_id", 0))
        new_offset = max(new_offset, update_id + 1)
        msg = update.get("message") or update.get("edited_message") or {}
        if not msg:
            continue
        chat = msg.get("chat", {})
        chat_id = int(chat.get("id", 0))
        text = msg.get("text", "") or ""
        ts = int(msg.get("date", time.time()))
        cmd, payload = _classify(text)
        authorized, reason = _authorize(chat_id, creds.principal_chat_id)
        out.append(InboundMessage(
            update_id=update_id,
            chat_id=chat_id,
            timestamp_unix=ts,
            raw_text=text,
            command=cmd,
            payload=payload,
            authorized=authorized,
            auth_reason=reason,
        ))

    # Log all messages (authorized or not) for audit
    if out:
        _append_log(out)

    if consume and new_offset != offset:
        _save_offset(new_offset)

    return out


def authorized_messages(messages: Iterable[InboundMessage]) -> list[InboundMessage]:
    return [m for m in messages if m.authorized]


def _append_log(messages: Iterable[InboundMessage]) -> None:
    INBOUND_LOG.parent.mkdir(parents=True, exist_ok=True)
    with INBOUND_LOG.open("a", encoding="utf-8") as fh:
        for m in messages:
            fh.write(json.dumps(asdict(m)) + "\n")


# ── Outbound: replies + push notifications ──────────────────────────

# Priority → leading marker. Telegram has no native priority system, so
# we encode it in the message header. The principal's eye + an emoji
# keep the signal intuitive.
_PRIORITY_PREFIX = {
    "min":     "ℹ️ ",
    "low":     "ℹ️ ",
    "default": "📩 ",
    "medium":  "📩 ",
    "high":    "⚠️ ",
    "max":     "🚨 ",
    "urgent":  "🚨 ",
}


def reply(message: str, parse_mode: Optional[str] = None) -> bool:
    """Send a plain reply to the principal via the bot.

    Use for STATUS responses or quick acks. For prioritised alerts use
    ``push_notification`` (which adds an emoji prefix and a title).
    Returns True on success, False on any failure (including missing
    creds — failures are logged but never raise).
    """
    creds = _load_creds()
    if creds is None:
        log.warning(
            "telegram reply skipped: no creds at %s. "
            "Run scripts/telegram_setup.py to configure.",
            CREDS_PATH,
        )
        return False
    params = {
        "chat_id": str(creds.principal_chat_id),
        "text": message,
    }
    if parse_mode:
        params["parse_mode"] = parse_mode
    resp = _api_call(creds.bot_token, "sendMessage", params, timeout=5.0)
    return bool(resp and resp.get("ok"))


def push_notification(
    title: str,
    message: str,
    priority: str = "default",
    tags: Optional[Iterable[str]] = None,
    click_url: Optional[str] = None,
    timeout_seconds: float = 5.0,
) -> bool:
    """Send a prioritised notification to the principal via Telegram.

    Drop-in replacement for the legacy ntfy push_notification API.
    Priority is encoded as a leading emoji ("🚨 " for urgent, "⚠️ "
    for high, "📩 " for default, "ℹ️ " for low). Tags and click_url
    are appended at the bottom of the message body.

    Returns True on success, False on any failure (network, missing
    creds, HTTP). Failures are logged but do NOT raise — the
    filesystem inbox remains the authoritative escalation channel,
    just as it was for ntfy.
    """
    _ = timeout_seconds  # accepted for API compat with ntfy push.py
    prefix = _PRIORITY_PREFIX.get(priority.lower(), _PRIORITY_PREFIX["default"])
    body_parts = [f"{prefix}*{title}*", "", message]
    if tags:
        tag_line = " ".join(f"#{t}" for t in tags if t)
        if tag_line:
            body_parts.extend(["", tag_line])
    if click_url:
        body_parts.extend(["", click_url])
    full = "\n".join(body_parts)

    creds = _load_creds()
    if creds is None:
        log.warning(
            "telegram push skipped: no creds. Set up via scripts/telegram_setup.py.",
        )
        return False
    params = {
        "chat_id": str(creds.principal_chat_id),
        "text": full,
        "parse_mode": "Markdown",
    }
    resp = _api_call(creds.bot_token, "sendMessage", params, timeout=timeout_seconds)
    ok = bool(resp and resp.get("ok"))
    if not ok:
        log.warning("telegram push failed for title=%r", title)
    return ok


# ── CLI for one-shot polling (cron-friendly) ─────────────────────────

def _cli() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Poll Telegram inbound channel.")
    p.add_argument("--consume", action="store_true",
                   help="Advance offset (default off — peek mode).")
    p.add_argument("--json", action="store_true",
                   help="Emit JSON-array on stdout instead of human text.")
    p.add_argument("--authorized-only", action="store_true",
                   help="Filter to authorized messages.")
    args = p.parse_args()

    msgs = poll_inbound(consume=args.consume)
    if args.authorized_only:
        msgs = authorized_messages(msgs)

    if args.json:
        print(json.dumps([asdict(m) for m in msgs], indent=2))
    else:
        if not msgs:
            print("(no inbound messages)")
            return 0
        for m in msgs:
            tag = "OK" if m.authorized else f"REJECT ({m.auth_reason})"
            print(f"[{m.update_id}] {tag} cmd={m.command} payload={m.payload!r} text={m.raw_text!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
