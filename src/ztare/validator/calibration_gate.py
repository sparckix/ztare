"""calibration_gate.py — mechanizes the converged precondition:
a channel may be flipped to owner-scoped-HARD ONLY after it passes a
false-positive-free calibration on the acting owner's OWN recent rows.

Why this exists (3 independent adversaries + operator converged,
2026-05-16): owner-scoped-HARD fixes cross-agent false-block but does
NOTHING for own-agent false-fire. GAP-E/GAP-F are grep heuristics that
false-positive on the acting agent's own legitimate rows; HARD-ifying a
heuristic = self-inflicted false-FAIL = the reverted GAP-H regression.
The precondition ("only flip after FP-free calibration on the owner's
own artifacts") was a PRINCIPLE in comments/memory — i.e. advisory,
i.e. glossable, i.e. it guaranteed nothing. This module makes it a
MECHANISM: `hard_allowed(channel, owner)` is the single gate every
validator's `--blocking` path MUST consult; it returns True ONLY if a
calibration ledger entry attests, for THIS (channel, owner):
  - n_checked >= MIN_CALIBRATION_N
  - false_positives == 0
  - author != concurring  (the FP=0 attestation is independently
    adjudicated, NOT self-attested by the acting owner — mirrors the
    catch self-attest author≠concurring discipline; a self-attested
    FP-free claim is the gloss again)
Absent/failing entry ⇒ HARD is mechanically REFUSED (the validator
falls back to advisory regardless of the `--blocking` flag). Channels
stay advisory by MECHANISM, not by hope.

Deterministic, closed-vocab channels (e.g. dispatch_ledger GAP-G:
closed SANCTIONED set, proven negative control) can earn an eligibility
entry; heuristic channels (GAP-E/F, menu top-k) cannot until a real
FP-free adjudicated calibration is recorded — which the evidence
currently refutes for GAP-F (token-soup false-fires).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LEDGER = REPO / "analytics/public/ledgers/calibration/hard_eligibility.jsonl"
MIN_CALIBRATION_N = 30

# DETERMINISTIC closed-vocab channels are HARD-eligible BY CONSTRUCTION
# (a fixed closed vocabulary + a proven negative control — no heuristic
# false-fire surface), so they do NOT require a calibration ledger
# entry. Calibration-gating these was an over-application of the
# heuristic precondition that silently made GAP-G enforcement inert
# everywhere (dispatch_ledger_check AND post_tick §8c) — the converged
# principle was always "deterministic closed-vocab qualifies; heuristics
# (gap_e/gap_f/menu) need calibration". Only heuristic channels consult
# the ledger.
DETERMINISTIC_CLOSED_VOCAB = {"gap_g"}


def _entries() -> list[dict]:
    if not LEDGER.exists():
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


def hard_allowed(channel: str, owner: str | None) -> tuple[bool, str]:
    """(allowed, reason). HARD is allowed ONLY with a valid FP-free,
    independently-adjudicated calibration entry for (channel, owner).
    owner=None ⇒ never allowed (no attributable calibration subject)."""
    if channel in DETERMINISTIC_CLOSED_VOCAB:
        return True, (f"HARD allowed: {channel} is a DETERMINISTIC "
                      f"closed-vocab channel — HARD-eligible by "
                      f"construction (closed vocabulary + proven "
                      f"negative control; no heuristic false-fire "
                      f"surface ⇒ no calibration ledger required).")
    if not owner:
        return False, ("HARD refused: no owner (calibration is "
                       "per-acting-owner; set --owner/RD_OWNER)")
    best = None
    for e in _entries():
        if e.get("channel") == channel and e.get("owner") == owner:
            best = e  # last wins (append-only; latest calibration)
    if best is None:
        return False, (f"HARD refused: no calibration entry for "
                       f"channel={channel} owner={owner} — channel stays "
                       f"ADVISORY by mechanism until FP-free calibration "
                       f"is recorded (the converged precondition).")
    n = int(best.get("n_checked", 0) or 0)
    fp = int(best.get("false_positives", -1))
    author = str(best.get("author", "") or "")
    concurring = str(best.get("concurring", "") or "")
    if n < MIN_CALIBRATION_N:
        return False, (f"HARD refused: calibration n_checked={n} < "
                       f"{MIN_CALIBRATION_N} for {channel}/{owner}")
    if fp != 0:
        return False, (f"HARD refused: calibration false_positives={fp} "
                       f"(must be 0) for {channel}/{owner} — heuristic "
                       f"false-fires; stays advisory")
    if not author or not concurring or author == concurring:
        return False, (f"HARD refused: calibration FP=0 must be "
                       f"INDEPENDENTLY adjudicated (author != concurring; "
                       f"got author={author!r} concurring={concurring!r}) "
                       f"— self-attested FP-free is the gloss")
    return True, (f"HARD allowed: {channel}/{owner} calibrated "
                  f"n={n} fp=0 author={author} concurring={concurring}")


if __name__ == "__main__":
    import sys
    ch = sys.argv[1] if len(sys.argv) > 1 else "gap_f"
    ow = sys.argv[2] if len(sys.argv) > 2 else None
    ok, why = hard_allowed(ch, ow)
    print(f"hard_allowed({ch!r}, {ow!r}) = {ok}\n  {why}")
    sys.exit(0 if ok else 3)
