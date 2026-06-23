"""stamped_state.py — GP-241 READ-SIDE TRUST BOUNDARY (Panel Round 2
must-fix; the keystone that makes the membrane real).

"Official" ≡ a row in the daemon's hash-chained stamped ledger with a
valid membrane_stamp AND an intact parent→official hash chain. A
hand-written F-row in EXPERIMENT_TRACK_RECORD.md / a raw transitions
write / a raw git commit is NOT in this ledger ⇒ NOT official ⇒ every
canonical reader must IGNORE it. Producer-side gating (the daemon) is
worthless unless consumers refuse to read unstamped state — that is
exactly the regress Panel Round 2 caught. This module is THE canonical
reader; rd_tick_brief / next-session bootstrap / manifest consumers
must call `official_transitions()` here, NOT scan the raw repo file.

Observe-mode honest note: on the dev box nothing OS-level stops a
non-daemon write to the store; the chain check detects tampering /
truncation but a forged-but-self-consistent chain by a process with
store write access is only fully closed by VPS OS-hardening (sole
ztare_verify writer). Stated, not laundered.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

# STORE-PATH INJECTION FIX (codex confirm sev-5, 2026-05-17): in
# ENFORCE mode the read-side trust boundary must NOT trust an
# agent-supplied $ZTARE_OFFICIAL_STORE (an agent could repoint it at
# an agent-writable fake ledger ⇒ hash-validity meaningless). Enforce
# is the DEFAULT and hardcodes /srv/ztare_official_store, verifying the
# resolved path is exactly that, a real dir, NOT a symlink, NOT
# world/group-writable. $ZTARE_OFFICIAL_STORE is honored ONLY when the
# explicit opt-in ZTARE_MEMBRANE_OBSERVE=1 is set (laptop/test). Any
# enforce-mode verification failure ⇒ fail-closed (no LEDGER ⇒ nothing
# is ever official except the frozen legacy manifest).
_ENFORCE_STORE = Path("/srv/ztare_official_store")
_OBSERVE = os.environ.get("ZTARE_MEMBRANE_OBSERVE") == "1"


def _verify_enforce_store(p: Path) -> bool:
    try:
        if p.is_symlink():
            return False
        rp = p.resolve()
        if rp != _ENFORCE_STORE.resolve():
            return False  # symlink/path redirection
        if not rp.is_dir():
            return False
        st = rp.stat()
        if st.st_mode & 0o022:           # group/world writable ⇒ unsafe
            return False
        return True
    except Exception:
        return False


if _OBSERVE:
    STORE = Path(os.environ.get(
        "ZTARE_OFFICIAL_STORE", str(Path.home() / "ztare_official_store")))
else:
    STORE = _ENFORCE_STORE if _verify_enforce_store(_ENFORCE_STORE) \
        else Path("/nonexistent/ztare_enforce_store_unverified")
LEDGER = STORE / "official" / "transitions.stamped.jsonl"

# BACKWARD-COMPAT via an IMMUTABLE, HASH-ADDRESSED LEGACY MANIFEST
# (cold GPT-5.5 xhigh must-fix 2026-05-17: the prior ts-lexical-compare
# grandfather was FAIL-OPEN — no-date / bad-tz / date-only / missing ts
# all silently grandfathered ⇒ post-cutover unstamped state treated
# official, the exact tick638/639 bypass). REPLACED: pre-cutover
# legitimacy ≡ the record id is in a frozen snapshot of the F-row ids
# that existed BEFORE cutover, verified against its sha256. There is NO
# timestamp comparison anywhere. Everything not in the verified
# manifest AND not daemon-stamped is FAIL-CLOSED (not official),
# regardless of any ts the agent supplies.
LEGACY_DIR = STORE / "legacy"
_LEGACY_TXT = LEGACY_DIR / "gp241_legacy_manifest.txt"
_LEGACY_SHA = LEGACY_DIR / "gp241_legacy_manifest.sha256"


def _legacy_ids() -> frozenset[str]:
    """Frozen pre-cutover F-row id set, ONLY if its content matches the
    committed sha256 (tamper/forge of the manifest ⇒ empty ⇒ fail-
    closed: nothing is grandfathered, everything must be stamped)."""
    try:
        blob = _LEGACY_TXT.read_text(encoding="utf-8")
        want = _LEGACY_SHA.read_text(encoding="utf-8").strip().split()[0]
        if hashlib.sha256(blob.encode()).hexdigest() != want:
            return frozenset()  # manifest tampered ⇒ trust NOTHING
        return frozenset(x.strip() for x in blob.splitlines() if x.strip())
    except Exception:
        return frozenset()  # absent/unreadable ⇒ fail-closed


def in_legacy(record_id: str | None) -> bool:
    """True iff record_id is EXACT-present in the verified frozen
    pre-cutover manifest. No ts, no heuristic, no substring — exact
    membership only (a forged 'pre-cutover' id not in the snapshot is
    NOT legacy ⇒ must be daemon-stamped)."""
    return bool(record_id) and record_id in _legacy_ids()


def _rows() -> list[dict]:
    if not LEDGER.is_file():
        return []
    out = []
    for ln in LEDGER.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def chain_valid(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """PURE: (valid_rows, integrity_errors) over a provided row list.
    A row is official iff it has a membrane_stamp AND its
    official_state_hash recomputes from the prior row's hash (intact
    append-only chain). Any break ⇒ all subsequent rows NON-official.
    Pure over its input ⇒ usable to verify content fetched from a
    REMOTE store with NO remote code execution (cold-fix blocker #2):
    the laptop fetches the world-readable ledger and recomputes sha256
    locally; it cannot make an unstamped pid validate without breaking
    sha256, and it provably never wrote any official row (OS perms)."""
    valid: list[dict] = []
    errs: list[str] = []
    parent = "GENESIS"
    chain_ok = True
    for i, r in enumerate(rows):
        if not chain_ok:
            errs.append(f"row {i}: dropped (upstream chain break)")
            continue
        if not r.get("membrane_stamp"):
            errs.append(f"row {i}: no membrane_stamp ⇒ NOT official")
            chain_ok = False
            continue
        body = {k: v for k, v in r.items()
                if k not in ("official_state_hash", "daemon_sig")}
        recomputed = hashlib.sha256(
            (parent + json.dumps(body, sort_keys=True)).encode()
        ).hexdigest()[:32]
        if r.get("parent_state_hash") != parent:
            errs.append(f"row {i}: parent_state_hash mismatch ⇒ chain break")
            chain_ok = False
            continue
        if recomputed != r.get("official_state_hash"):
            errs.append(f"row {i}: official_state_hash forged/edited "
                         f"⇒ chain break")
            chain_ok = False
            continue
        # cold round-4 blocker: a self-consistent hash-chain is
        # forgeable by ANY endpoint (sha256 is public). Require the
        # daemon's ed25519 signature over official_state_hash by the
        # PINNED public key — only the VPS-only private key can produce
        # it. No/invalid signature ⇒ chain break (fail-closed). This
        # takes endpoint identity OUT of the trust boundary.
        from ztare.gates._daemon_sig import verify as _dsig_verify
        if not _dsig_verify(r.get("official_state_hash", ""),
                            r.get("daemon_sig")):
            errs.append(f"row {i}: missing/invalid daemon signature "
                        f"⇒ NOT daemon-authored ⇒ chain break")
            chain_ok = False
            continue
        valid.append(r)
        parent = r["official_state_hash"]
    return valid, errs


def official_transitions() -> tuple[list[dict], list[str]]:
    """Local-store wrapper around the pure chain core."""
    return chain_valid(_rows())


def tick_started(tick_id: str) -> bool:
    """Pre-tick→contract migration read-side: a tick is OPENED under a
    daemon-minted contract IFF a chain-valid, daemon-SIGNED row with
    transition_type=='start_tick' AND tick_id matches exists. The
    pre-tick mandate is no longer print — it is this signed row."""
    if not tick_id:
        return False
    valid, _ = chain_valid(_rows())
    return any(r.get("transition_type") == "start_tick"
               and str(r.get("tick_id")) == str(tick_id)
               for r in valid)


def tick_closed(tick_id: str) -> bool:
    """FORCED-CLOSE read-side (2-cold-pass synthesis). A tick is
    closed IFF a chain-valid, DAEMON-SIGNED row exists with
    transition_type=='tick_close' AND close_verified is True AND
    tick_id matches. An agent-written EXPERIMENT_TRACK_RECORD.md F-row
    is NOT authority — only this signed transition is. chain_valid
    already requires the pinned daemon ed25519 signature, so a
    forged/local row cannot satisfy this."""
    if not tick_id:
        return False
    valid, _ = chain_valid(_rows())
    for r in valid:
        if (r.get("transition_type") == "tick_close"
                and r.get("close_verified") is True
                and str(r.get("tick_id")) == str(tick_id)):
            return True
    return False


def verify_fetched(ledger_text: str,
                   legacy_txt: str | None,
                   legacy_sha: str | None,
                   *, proposal_id: str | None = None,
                   record_id: str | None = None,
                   body_sha256: str | None = None) -> bool:
    """Cold-fix blocker #2/#3: verify content FETCHED from a remote
    world-readable store, entirely on the caller. NO remote code, NO
    sudo, NO env-controlled import path. Pure crypto:
      - legacy: record_id ∈ manifest IFF sha256(manifest)==its pinned
        sha (a tampered/extended manifest ⇒ sha mismatch ⇒ trust none);
      - chain: recompute the sha256 hash-chain over the fetched ledger
        and require proposal_id present in a chain-valid stamped row.
    Forge-proof: the agent cannot exhibit a sha256 chain that validates
    a pid it never got stamped, and OS perms prove it wrote no row."""
    if record_id and legacy_txt is not None and legacy_sha:
        try:
            want = legacy_sha.strip().split()[0]
            if hashlib.sha256(legacy_txt.encode()).hexdigest() == want:
                ids = {x.strip() for x in legacy_txt.splitlines()
                       if x.strip()}
                if record_id in ids:
                    return True
        except Exception:
            pass
    rows: list[dict] = []
    for ln in (ledger_text or "").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except Exception:
            continue
    valid, _ = chain_valid(rows)
    for r in valid:
        if not (proposal_id and r.get("proposal_id") == proposal_id):
            continue
        # cold re-review blocker #1: the verdict is bound to the EXACT
        # submitted body. A relabel attack (good B carrying bad A's
        # pid) cannot make A official: B's stamped row carries B's
        # body sha, never A's. Caller MUST supply the sha of exactly
        # what it submitted; absent/mismatch ⇒ NOT official.
        if not body_sha256:
            return False
        if r.get("proposal_body_sha256") == body_sha256:
            return True
    return False


def is_official(*, tick_contract_id: str | None = None,
                proposal_id: str | None = None,
                record_id: str | None = None,
                record_ts: str | None = None) -> bool:
    """FAIL-CLOSED (cold-fix). Official IFF:
      (1) record_id is EXACT-present in the verified frozen pre-cutover
          legacy manifest (legitimate history — NO ts heuristic), OR
      (2) it is in the daemon-stamped, chain-valid ledger.
    Everything else — missing/unparseable/post-cutover/no-id, a forged
    'pre-cutover' id not in the snapshot, a tampered manifest — is NOT
    official. `record_ts` is accepted for signature compatibility but
    is DELIBERATELY NOT consulted (the prior ts-compare was the
    fail-open hole). Default deny."""
    if in_legacy(record_id):
        return True
    valid, _ = official_transitions()
    for r in valid:
        if tick_contract_id and r.get("tick_contract_id") == tick_contract_id:
            return True
        if proposal_id and r.get("proposal_id") == proposal_id:
            return True
    return False  # fail-closed: not legacy-manifest, not stamped ⇒ NO


def latest_official_closure() -> dict | None:
    """The canonical 'previous tick closed' signal for rd_tick_brief —
    the LAST chain-valid stamped row, not whatever was hand-written
    into EXPERIMENT_TRACK_RECORD.md."""
    valid, _ = official_transitions()
    return valid[-1] if valid else None


def main() -> int:
    import sys
    valid, errs = official_transitions()
    print(json.dumps({"official_count": len(valid),
                       "integrity_errors": errs[:10],
                       "latest": (valid[-1].get("proposal_id")
                                  if valid else None)}, indent=2))
    return 0 if not errs else 1


if __name__ == "__main__":
    raise SystemExit(main())
