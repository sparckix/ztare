"""propose.py — the agent's ONLY path to consequential state.

The agent (claude/codex/headless) cannot write the official store. It
drops a proposal JSON into the verificator's inbox; the daemon gates
it. "No stamped proposal ⇒ no official transition."

THREE endpoint modes (Fix B — preflight-caught: self-spawn is a
laptop-only bootstrap, it cannot work under OS enforcement where the
agent user is FORBIDDEN to write the ztare_verify store):

  remote-enforce  ZTARE_VERIFICATOR_SSH set  → laptop ARTISANAL: submit
                  over SSH to the VPS verificator's inbox + poll the
                  VPS store (the single source of truth). The laptop
                  is a proposer+observer, NEVER an authority. This is
                  the "artisanal updates the VPS epistemic daemon" path.
  local-enforce   on the VPS itself (a verificator systemd daemon is
                  running; the agent CANNOT write the store) → submit
                  to the LOCAL inbox + poll the LOCAL store. Do NOT
                  self-spawn (can't write the ztare_verify store).
  observe         ZTARE_MEMBRANE_OBSERVE=1 → laptop sandbox/dry-run:
                  self-spawn a local daemon. Explicitly NOT official.

Channel for remote-enforce = SSH (key auth, BatchMode), atomic file
drop (tmp+mv) + poll. Host/key from env — NEVER hardcoded (leak-free,
same convention as deploy/vps_update.sh).

Usage:
  python -m src.ztare.gates.propose --type tick_close \
      --text "<transition text>" --declared '<json>'
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import hashlib
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

STORE = Path(os.environ.get(
    "ZTARE_OFFICIAL_STORE", str(Path.home() / "ztare_official_store")))
INBOX = STORE / "proposal_queue" / "inbox"

# remote-enforce (laptop artisanal → VPS verificator). Leak-free: host
# + key come from the environment, identical convention to
# deploy/vps_update.sh; the IP lives only in operator memory / docs.
VERIFICATOR_SSH = os.environ.get("ZTARE_VERIFICATOR_SSH", "").strip()
VPS_KEY = os.environ.get(
    "ZTARE_VPS_KEY", str(Path.home() / ".ssh" / "id_ed25519"))
# HARD-PINNED literal — NOT from env (cold round-3 blocker #1). The
# prior `ZTARE_VPS_OFFICIAL_STORE` env was agent-controllable: point it
# at a self-run fake store + fake watcher and verify_fetched() passes,
# forging OFFICIAL while bypassing the real daemon. Same class as the
# deleted ZTARE_VPS_GATE. The remote store path is now a constant; the
# ONLY agent-supplied remote input is the SSH target host (necessarily
# so — it is *where* to submit, leak-free convention; the security is
# the VPS daemon sole-writer + OS perms on this fixed path, and the
# read-side trust boundary stamped_state.py is likewise hard-pinned).
VPS_STORE = "/srv/ztare_official_store"
# NOTE: there is deliberately NO ZTARE_VPS_GATE / ZTARE_VPS_OFFICIAL_
# STORE env (cold blockers #2 & r3#1: agent-controlled paths/import
# steered the trust check = forge). The remote poll executes NO code
# on the VPS — it only `cat`s world-readable files at this FIXED path
# and verifies the sha256 chain locally.
import re as _re
_PID_RE = _re.compile(r"^[0-9]{8}T[0-9]{6}_[0-9a-f]{8}$")
OBSERVE = os.environ.get("ZTARE_MEMBRANE_OBSERVE", "") == "1"
# fail-closed poll budget (s) + interval. Timeout ⇒ REFUSED, NEVER
# fail-open to OFFICIAL.
TIMEOUT = int(os.environ.get("ZTARE_PROPOSE_TIMEOUT", "180"))
INTERVAL = int(os.environ.get("ZTARE_PROPOSE_POLL_INTERVAL", "5"))


def _ssh_base() -> list[str]:
    return ["ssh", "-i", VPS_KEY, "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=15", VERIFICATOR_SSH]


def _remote_submit(pid: str, body: str) -> None:
    """Atomically publish the proposal into the VPS inbox over SSH:
    write a .partial then mv (the daemon must never read a half file).
    The agent user is ACL'd to write ONLY this inbox, never the store."""
    rin = f"{VPS_STORE}/proposal_queue/inbox"
    pf = f"{rin}/{pid}.json.partial"
    fin = f"{rin}/{pid}.json"
    # umask 022 (NOT 077): the daemon runs as ztare_verify and MUST be
    # able to READ the dropped proposal. Proposals are not secret —
    # integrity (the stamp/chain) is the security property, not
    # proposal confidentiality. tmp+mv keeps the read atomic.
    cmd = (f"umask 022; mkdir -p {shlex.quote(rin)}; "
           f"cat > {shlex.quote(pf)} && chmod 0644 {shlex.quote(pf)} && "
           f"mv {shlex.quote(pf)} {shlex.quote(fin)}")
    r = subprocess.run(_ssh_base() + [cmd], input=body, text=True,
                        capture_output=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError(f"remote submit failed: {r.stderr.strip()[:300]}")


# Cold re-review blocker #6: in-band text sentinels are data-
# confusable — a stamped row's agent-controlled transition_text could
# contain the sentinel and truncate ledger parsing (liveness brick).
# FIX: each file is base64-encoded on the VPS before transport. The
# base64 alphabet is [A-Za-z0-9+/=] and CANNOT contain ':' — so a
# colon-delimited sentinel can never appear inside an encoded payload,
# regardless of file content. Framing is now content-independent.
_SENT = {"L": ":::ZL:::", "T": ":::ZT:::", "S": ":::ZS:::",
         "Q": ":::ZQ:::", "E": ":::ZE:::"}


def _remote_verdict(pid: str, ts: str,
                    body_sha256: str) -> tuple[str, str]:
    """Cold blocker #2/#3 STRUCTURAL FIX: execute NO code on the VPS.
    The poll only base64-`cat`s WORLD-READABLE fixed files (Fix A) and
    the agent's OWN quarantine record, then verifies the sha256
    hash-chain LOCALLY via stamped_state.verify_fetched. No sudo, no
    remote python, no env-controlled import path — transport fully out
    of the trust boundary. Forge-proof: the agent cannot exhibit a
    sha256 chain validating a pid it never got stamped (and, blocker
    #1, the verdict is bound to the EXACT submitted body via
    body_sha256), and OS perms prove it wrote no official row.

    pid is generated (ts+uuid) and additionally regex-pinned here
    before it touches the command (defense in depth)."""
    if not _PID_RE.match(pid):
        return "PENDING", f"refuse: pid failed charset pin: {pid!r}"
    ledger = f"{VPS_STORE}/official/transitions.stamped.jsonl"
    lt = f"{VPS_STORE}/legacy/gp241_legacy_manifest.txt"
    ls = f"{VPS_STORE}/legacy/gp241_legacy_manifest.sha256"
    qg = f"{VPS_STORE}/quarantine/{pid}"
    # Fixed read-only command: `echo` colon-sentinels + base64 of fixed
    # paths (+ the regex-pinned, shlex-quoted pid for the agent's OWN
    # quarantine file). base64 output cannot contain ':' ⇒ no file
    # content can forge a frame. Nothing here is agent-authored code.
    cmd = (
        f"echo '{_SENT['L']}'; base64 {shlex.quote(ledger)} 2>/dev/null; "
        f"echo '{_SENT['T']}'; base64 {shlex.quote(lt)} 2>/dev/null; "
        f"echo '{_SENT['S']}'; base64 {shlex.quote(ls)} 2>/dev/null; "
        f"echo '{_SENT['Q']}'; cat {shlex.quote(qg)}*.quarantine.json "
        f"{shlex.quote(qg)}*.reject.json 2>/dev/null | base64 2>/dev/null; "
        f"echo '{_SENT['E']}'"
    )
    try:
        r = subprocess.run(_ssh_base() + [cmd], text=True,
                            capture_output=True, timeout=30)
    except Exception as e:
        return "PENDING", f"ssh-poll-exc: {type(e).__name__}: {str(e)[:160]}"
    if r.returncode != 0:
        return "PENDING", f"ssh-poll-error: {r.stderr.strip()[:200]}"
    out = r.stdout
    if _SENT["E"] not in out:
        return "PENDING", f"truncated remote read: {out[:160]!r}"

    def _seg(a: str, b: str) -> str:
        try:
            enc = out.split(_SENT[a], 1)[1].split(_SENT[b], 1)[0]
            import base64 as _b64
            return _b64.b64decode(
                "".join(enc.split())).decode("utf-8", "replace")
        except Exception:
            return ""
    ledger_text = _seg("L", "T")
    legacy_txt = _seg("T", "S")
    legacy_sha = _seg("S", "Q")
    quar = _seg("Q", "E").strip()

    from ztare.gates.stamped_state import verify_fetched
    if verify_fetched(ledger_text, legacy_txt or None, legacy_sha or None,
                      proposal_id=pid, body_sha256=body_sha256):
        return "OFFICIAL", ("locally chain-verified against the "
                            "world-readable VPS ledger; verdict bound "
                            "to submitted body sha (no remote code)")
    if quar:
        return "QUARANTINED", quar[:600]
    return "PENDING", ""


def _local_verdict(pid: str, ts: str,
                   body_sha256: str) -> tuple[str, str]:
    from ztare.gates.stamped_state import verify_fetched
    from ztare.gates.stamped_state import (
        LEDGER, _LEGACY_TXT, _LEGACY_SHA)
    try:
        lt = _LEGACY_TXT.read_text(encoding="utf-8")
    except Exception:
        lt = None
    try:
        lsha = _LEGACY_SHA.read_text(encoding="utf-8")
    except Exception:
        lsha = None
    try:
        ledger_text = LEDGER.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        ledger_text = ""
    if verify_fetched(ledger_text, lt, lsha,
                      proposal_id=pid, body_sha256=body_sha256):
        return "OFFICIAL", "daemon-stamped; chain-valid; body-sha bound"
    qf = STORE / "quarantine"
    for f in (sorted(qf.glob(f"{pid}*"), reverse=True)
              if qf.is_dir() else []):
        return "QUARANTINED", f.read_text(
            encoding="utf-8", errors="ignore")[:600]
    return "PENDING", ""


def _poll(verdict_fn, pid: str, ts: str,
          body_sha256: str) -> tuple[str, str]:
    """Block fail-closed until OFFICIAL/QUARANTINED or TIMEOUT. Timeout
    ⇒ ('REFUSED', ...) — NEVER fall through to OFFICIAL."""
    deadline = time.time() + TIMEOUT
    last = ""
    while time.time() < deadline:
        state, detail = verdict_fn(pid, ts, body_sha256)
        if state == "OFFICIAL":
            return "OFFICIAL", detail
        if state == "QUARANTINED":
            return "QUARANTINED", detail
        last = detail
        time.sleep(INTERVAL)
    return "REFUSED", f"timeout {TIMEOUT}s with no stamp ({last})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", required=True,
                    help="result|closure|next_step|F_row|"
                         "forecast_resolution|artifact_promotion|tick_close")
    ap.add_argument("--text", required=True)
    ap.add_argument("--declared", default="{}")
    ap.add_argument("--goal", default="",
                    help="free-text research goal — the daemon RECOMPUTES "
                         "the start-tick obligation contract from this "
                         "(no goal ⇒ no official close if obligations fire)")
    ap.add_argument("--witnesses", default="{}",
                    help="JSON {item_id: {required_field: value,...}} "
                         "discharging each mandatory obligation")
    ap.add_argument("--why-not", default="{}",
                    help="JSON {item_id: {reason: <enum>, evidence:...}} "
                         "for obligations legitimately not applicable")
    # NOTE: there is deliberately NO --await flag. Synchronous
    # fail-closed wait is the ONLY behavior (operator 2026-05-17: every
    # param is a gaming hole — an opt-in forcing flag = "just don't
    # pass it" bypass). propose ALWAYS blocks on the daemon verdict.
    ap.add_argument("--declare", default="",
                    help="comma-sep typed signals the agent explicitly "
                         "asserts (proposes_new_route, declares_impossible, "
                         "citation_load_bearing, asks_discriminator, "
                         "positive_claim, stuck, load_bearing_arch_decision, "
                         "math_estimate). MANDATORY obligations key on these "
                         "typed declarations + --type, NOT goal prose "
                         "(paraphrase-proof; misdeclaration is surfaced).")
    ap.add_argument("--close", default="{}",
                    help="JSON close-transaction fields for --type "
                         "tick_close: {tick_id, contract_id, f_row_id, "
                         "f_row_body}. The DAEMON owns close: it "
                         "validates these and materializes the official "
                         "F-row itself (agent-written .md rows are not "
                         "authority — reverse-H3).")
    ap.add_argument("--agent-runtime", default=os.environ.get(
        "ZTARE_AGENT_RUNTIME", "claude-code"))
    ap.add_argument("--session-id", default=os.environ.get("ZTARE_SESSION", ""))
    a = ap.parse_args()
    try:
        declared = json.loads(a.declared)
        witnesses = json.loads(a.witnesses)
        why_not = json.loads(getattr(a, "why_not"))
        close = json.loads(a.close)
    except Exception as e:
        raise SystemExit(f"--declared/--witnesses/--why-not/--close must be JSON: {e}")
    pid = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
    submitted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    proposal = {
        "proposal_id": pid,
        "agent_runtime": a.agent_runtime,
        "session_id": a.session_id,
        "turn_id": os.environ.get("ZTARE_TURN", ""),
        "transition_type": a.type,
        "transition_text": a.text,
        "declared": declared,
        "goal": a.goal,
        "declared_signals": {s.strip(): True for s in a.declare.split(",")
                             if s.strip()},
        "witnesses": witnesses,
        "why_not": why_not,
        "close": close,
        "submitted_at": submitted_at,
    }
    body = json.dumps(proposal, indent=2)
    # cold re-review blocker #1: bind the verdict to the EXACT bytes we
    # submit. The daemon hashes the inbox file's exact content into the
    # row; we recompute the same here and require the stamped row to
    # carry this sha. A relabel (good B carrying our pid) cannot make
    # our work official — B's row has B's body sha, not ours.
    body_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()

    # ---- endpoint dispatch (Fix B) -----------------------------------
    # Precedence: explicit remote endpoint > observe sandbox > local
    # enforce (VPS-resident agent) > observe fallback (laptop dev).
    if VERIFICATOR_SSH:
        mode = "remote-enforce"
    elif OBSERVE:
        mode = "observe"
    elif STORE.is_dir() and not os.access(INBOX.parent.parent, os.W_OK):
        # store exists but the agent user cannot write it ⇒ a real
        # verificator owns it ⇒ a daemon is the only writer. Do NOT
        # self-spawn (can't write ztare_verify store): submit + poll.
        mode = "local-enforce"
    else:
        mode = "observe"

    if mode == "remote-enforce":
        # Round-5 blocker: remote-enforce trusts a LOCAL pinned pubkey
        # + local verifier code. If those are writable by this user,
        # the agent swaps the anchor for its own key and forges the
        # endpoint verdict. REFUSE unless the verifier+anchor are
        # demonstrably agent-unwritable (install them root-owned, like
        # /srv/ztare_gate on the VPS). Fail-closed, never silent-trust.
        from ztare.gates._daemon_sig import anchor_tamperproof
        _tp_ok, _tp_why = anchor_tamperproof()
        if not _tp_ok:
            print(json.dumps({
                "REFUSED": pid, "mode": mode,
                "note": "remote-enforce requires an agent-UNWRITABLE "
                        "verifier+anchor install — refusing rather than "
                        "trust a swappable local trust anchor (work is "
                        "NOT official)",
                "detail": _tp_why,
                "fix": "run deploy/install_local_verifier.sh (root) and "
                       "invoke propose from the installed copy"}))
            return 2
        try:
            _remote_submit(pid, body)
        except Exception as e:
            print(json.dumps({"REFUSED": pid, "mode": mode,
                              "note": "could not reach VPS verificator — "
                                      "work is NOT official",
                              "error": str(e)[:300]}))
            return 2
        state, detail = _poll(_remote_verdict, pid, submitted_at,
                              body_sha256)
    elif mode == "local-enforce":
        INBOX.mkdir(parents=True, exist_ok=True)
        tmp = INBOX / f"{pid}.json.partial"
        tmp.write_text(body)
        os.chmod(tmp, 0o644)  # daemon (ztare_verify) must read it
        tmp.rename(INBOX / f"{pid}.json")
        state, detail = _poll(_local_verdict, pid, submitted_at,
                              body_sha256)
    else:  # observe — laptop sandbox DRY-RUN. Cold blocker #1: observe
        # must NEVER emit OFFICIAL nor exit 0 — a self-spawned local
        # daemon on an agent-writable fake store proves NOTHING about
        # official state; any wrapper trusting exit 0 / "OFFICIAL" here
        # would be laundered. It returns an advisory dry-run verdict
        # and ALWAYS a non-zero exit.
        INBOX.mkdir(parents=True, exist_ok=True)
        (INBOX / f"{pid}.json").write_text(body)
        subprocess.run([sys.executable, "-m",
                        "src.ztare.gates.commit_membrane_daemon", "--once"],
                       capture_output=True, text=True, timeout=120)
        dry, dry_detail = _local_verdict(pid, submitted_at, body_sha256)
        print(json.dumps({
            "OBSERVE_ONLY": pid, "mode": mode,
            "dry_run_would_be": dry,
            "note": "DRY-RUN on a local sandbox store — NOT official, "
                    "NEVER counts; exit is always non-zero so no "
                    "wrapper can launder this as a real stamp",
            "detail": dry_detail}))
        return 3  # distinct non-zero: never confusable with OFFICIAL(0)

    if state == "OFFICIAL":
        print(json.dumps({"OFFICIAL": pid, "mode": mode, "note": detail}))
        return 0
    label = "QUARANTINED" if state == "QUARANTINED" else "REFUSED"
    print(json.dumps({label: pid, "mode": mode,
                      "note": "NOT daemon-stamped — work is NOT official; "
                              "do not proceed as if it were",
                      "detail": detail}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
