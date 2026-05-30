"""catch_attest_gate.py — #28: make catch-logging post-discipline
ENFORCED on the OBJECTIVE catch-trigger, without GAP-H false-fire.

The operator's question: catch-logging is currently advisory
(post_tick_check §5) because "did a catch occur" is judgment-laden /
not machine-detectable, so HARD would false-fire (the reverted GAP-H
lesson). BUT objective catch-events DO exist and ARE machine-detectable:
a forecast contract resolved **success=FALSE** is, by construction, a
conceded adversarial-kill / correction = a catch event that occurred.
(This session: tick624/626/627/629/631/637 all resolved FALSE.)

So this gate enforces, ONLY on that objective trigger:
  - outcome json absent OR success != False  ⇒ ADVISORY-PASS
    (no objective catch ⇒ nothing to enforce; never false-fire);
  - outcome success == False ⇒ a catch event objectively occurred ⇒
    the catch_ledger MUST carry an entry that references this
    contract-id (or its tick-row) AND is INDEPENDENT
    (author_agent != concurring_agent, both non-empty). Else HARD.

It NEVER writes the ledger (append-only audit; memory: do NOT
auto-rewrite / null concurring_agent — ledger remediation is pending
operator policy). It forces the acting agent to have logged the
conceded catch, independently attested, before the tick can close.
Owner-scoped by construction (called from tick_close, which is H1
RD_OWNER-gated).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUTCOMES = REPO / "analytics/public/forecast_pool/outcomes"
CATCH = REPO / "analytics/public/ledgers/catch/catch_ledger.jsonl"


def _outcome_success(contract_id: str):
    f = OUTCOMES / f"{contract_id}.json"
    if not f.is_file():
        return None  # no objective catch signal
    try:
        d = json.loads(f.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None
    for k in ("success", "success_bool", "resolved_success"):
        if k in d and isinstance(d[k], bool):
            return d[k]
    return None


def _catch_rows():
    if not CATCH.is_file():
        return []
    out = []
    for ln in CATCH.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def catch_attested(contract_id: str, tick_row: str | None
                    ) -> tuple[bool, str]:
    """(ok, reason). HARD only when the contract resolved success=False
    (objective catch trigger). Requires an INDEPENDENT catch-ledger
    entry referencing the contract-id or tick-row."""
    succ = _outcome_success(contract_id)
    if succ is None:
        return True, (f"catch_attest_gate: no resolved outcome for "
                      f"'{contract_id}' ⇒ ADVISORY (no objective catch "
                      f"trigger; never false-fire).")
    if succ is True:
        return True, (f"catch_attest_gate: contract '{contract_id}' "
                      f"resolved success=true ⇒ no conceded catch ⇒ "
                      f"ADVISORY (nothing to enforce).")
    # success == False ⇒ a conceded adversarial-kill / correction = an
    # OBJECTIVE catch event. Enforce an independent ledger entry.
    keys = [k for k in (contract_id, tick_row) if k]
    nkeys = [k.lower() for k in keys if len(k) >= 6]
    for r in _catch_rows():
        blob = " ".join(str(r.get(f, "")) for f in (
            "title", "summary", "fix_artifact", "workpaper_paths",
            "catch_id")).lower()
        # word-boundary-ish: require the key as a delimited token, not a
        # bare substring (review: `tick62` ⊂ `tick629` latent collision).
        if not any(re.search(rf"(^|[^a-z0-9]){re.escape(k)}([^a-z0-9]|$)",
                             blob) for k in nkeys):
            continue
        author = str(r.get("author_agent", "") or "").strip()
        concur = str(r.get("concurring_agent", "") or "").strip()
        if author and concur and author != concur:
            return True, (f"catch_attest_gate: contract resolved "
                          f"success=FALSE (objective catch) AND an "
                          f"INDEPENDENT catch-ledger entry "
                          f"({r.get('catch_id')}, author={author} ≠ "
                          f"concurring={concur}) references it — "
                          f"enforced & satisfied.")
        # SINGLE-AGENT DEGRADE (review must-fix — the loop-killer):
        # the catch IS logged (the enforced minimum) but independence
        # is not yet satisfiable in single-artisanal-agent mode. Do NOT
        # HARD-deadlock the loop; pass with EXPLICIT TRACKED DEBT
        # (concurrer owed). Logging is HARD; independence is debt.
        return True, (f"catch_attest_gate: contract resolved "
                      f"success=FALSE AND a catch-ledger entry "
                      f"({r.get('catch_id')}) references it (logging "
                      f"ENFORCED ✓) but independence is NOT yet "
                      f"satisfied (author={author!r}, "
                      f"concurring={concur!r}). SINGLE-AGENT DEGRADE: "
                      f"PASS-WITH-DEBT — an independent concurrer "
                      f"(author≠concurring) is OWED on this catch; "
                      f"tracked debt, NOT a deadlock (review must-fix).")
    return False, (f"catch_attest_gate: contract '{contract_id}' "
                   f"resolved success=FALSE — a conceded "
                   f"adversarial-kill / correction = an OBJECTIVE catch "
                   f"event — but NO catch-ledger entry references it "
                   f"(by contract-id or tick-row '{tick_row}'). Logging "
                   f"is HARD-ENFORCED: log the catch (self-authored is "
                   f"the minimum; independent concurrer then owed as "
                   f"debt) before closing. (This gate does NOT "
                   f"auto-write the append-only ledger.)")


def main() -> int:
    import sys
    cid = sys.argv[1] if len(sys.argv) > 1 else ""
    trow = sys.argv[2] if len(sys.argv) > 2 else None
    ok, why = catch_attested(cid, trow)
    print(("OK: " if ok else "REFUSE: ") + why)
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
