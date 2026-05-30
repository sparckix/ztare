"""dispatch_ledger_check.py — GAP-G: forced agent-dispatch self-account.

RCA (2026-05-16): the agent-dispatch-economy anti-pattern (do depth-n
forward work in-thread; dispatch agents ONLY for adversarial-kill or
genuine divide-and-conquer) WAS mechanized as an advisory PRINT inside
`rd_tick_brief.py:607` `predispatch_reminder()` — but that is (1) an
advisory print not a measured forcing check, (2) coupled to the
rd_tick_brief NS-pre-tick path, so out-of-loop meta-work that never
touches that path is never gated, (3) unenforced. Same failure class as
the GP-188 Q1 surfacing bug (forcing function path-coupled + advisory).

A first design (post-hoc transcript dispatch:compose ratio + maxrun) was
adversarially reviewed WRONG: the ratio/maxrun false-FIRES on the
*sanctioned* "compose → one adversarial-kill dispatch → compose" rhythm
and on legitimate divide-and-conquer, and the Claude-JSONL signal is
fleet-non-portable (codex agents have no such transcript) — reproducing
the very path-coupling the fix exists to remove. The reviewer-prescribed
correct design, implemented here: a **ledger-only forced self-account**,
path-independent, fleet-general, no false-FIRE on sanctioned cadence.

Mechanism (precise re-use of the GAP-F `primitives_considered` pattern —
`validate_primitives_considered.py`): every going-forward tick F-row
MUST carry a `dispatch_ledger:` self-account. Grammar:

    dispatch_ledger: none
    dispatch_ledger: <label>=<class>[; <label>=<class> ...]

Sanctioned classes (PATTERN-011): `adversarial_kill`,
`divide_and_conquer`, `cold_deanchor_carveout3`. A row missing the field
entirely, or a ledger entry whose class is not sanctioned, is the
flagged violation — an unsanctioned class string (e.g. `forward_work`)
is the honest self-incrimination the mechanism is designed to surface
(the operator cannot un-see a dispatch the author had to class as
forward-work). Advisory until calibrated (never false-FAIL):
retroactive-exempt — only rows dated today are checked.

Path-independent: standalone (`python dispatch_ledger_check.py
[--record PATH] [--blocking]`) AND an additive advisory subprocess leg
in post_tick (path-independent close-out, NOT rd_tick_brief — that is
the RCA root cause). Pure-Python, deterministic, no LLM, fleet-general.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT_RECORD = REPO / "research_areas/EXPERIMENT_TRACK_RECORD.md"

SANCTIONED = {"adversarial_kill", "divide_and_conquer", "cold_deanchor_carveout3"}
MARKER = "dispatch_ledger (GAP-G)"

_LEDGER_RE = re.compile(r"dispatch_ledger:\s*([^|]*)", re.IGNORECASE)
_DATE_RE = re.compile(r"`(\d{4}-\d{2}-\d{2})`")


def _parse_ledger(payload: str) -> tuple[bool, list[str]]:
    """(well_formed, unsanctioned_classes). `none` is well-formed."""
    body = payload.strip().strip("`").strip()
    if not body:
        return False, []
    if body.lower().startswith("none"):
        return True, []
    bad: list[str] = []
    for entry in re.split(r"[;,]", body):
        entry = entry.strip()
        if not entry:
            continue
        cls = entry.split("=", 1)[1].strip() if "=" in entry else entry
        cls = cls.split()[0].strip().lower() if cls else ""
        if cls not in SANCTIONED:
            bad.append(cls or "<empty>")
    return True, bad


def check_record(record: Path, only_date: str | None) -> list[str]:
    """Return human-readable violation lines (advisory). only_date:
    restrict to F-rows bearing this ISO date (retroactive-exempt);
    None ⇒ all rows (standalone audit mode)."""
    if not record.exists():
        return [f"{MARKER}: record not found: {record} (advisory; skipped)"]
    out: list[str] = []
    for ln in record.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not ln.lstrip().startswith("| F-"):
            continue
        if only_date is not None:
            d = _DATE_RE.search(ln)
            if not d or d.group(1) != only_date:
                continue
        rid = ln.split("|", 2)[1].strip() if "|" in ln else ln[:60]
        m = _LEDGER_RE.search(ln)
        if not m:
            out.append(f"{MARKER}: F-row `{rid}` has NO dispatch_ledger: "
                       f"self-account (every going-forward tick F-row must "
                       f"carry `dispatch_ledger: none` or "
                       f"`<label>=<sanctioned_class>`).")
            continue
        well_formed, bad = _parse_ledger(m.group(1))
        if not well_formed:
            out.append(f"{MARKER}: F-row `{rid}` dispatch_ledger present "
                       f"but empty/malformed.")
        for b in bad:
            out.append(f"{MARKER}: F-row `{rid}` declares an UNSANCTIONED "
                       f"dispatch class '{b}' (sanctioned: "
                       f"{sorted(SANCTIONED)}) — a dispatch that is not "
                       f"adversarial-kill / divide-and-conquer / "
                       f"cold-deanchor is the registered anti-pattern: "
                       f"the forward work should have been composed "
                       f"in-thread.")
    return out


def _row_owner(line: str) -> str | None:
    """Owner attribution of an F-row via an inline `owner:<id>` token
    (same forced-self-account convention as `dispatch_ledger:`). None ⇒
    unattributed (legacy/backlog ⇒ advisory, never the acting owner's
    HARD debt — exactly post_tick_check's owner semantics)."""
    m = re.search(r"owner:\s*([A-Za-z0-9_.:\-]+)", line)
    return m.group(1) if m else None


def main() -> int:
    import os
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", default=str(DEFAULT_RECORD),
                    help="work-unit record to audit (default: "
                         "EXPERIMENT_TRACK_RECORD.md)")
    ap.add_argument("--all-dates", action="store_true",
                    help="audit every F-row (default: only today's)")
    ap.add_argument("--owner", default=None,
                    help="acting RD owner. HARD only on rows this owner "
                         "created (`owner:<id>` token == this); other / "
                         "unattributed rows are advisory (owner-scoped "
                         "isolation, reuses post_tick_check semantics; "
                         "absent ⇒ $RD_OWNER ⇒ legacy global advisory).")
    ap.add_argument("--blocking", action="store_true",
                    help="exit 1 on the acting OWNER's own violations "
                         "(owner-scoped: un-glossable for the author, "
                         "never backlog-poisoned).")
    a = ap.parse_args()
    owner = a.owner or os.environ.get("RD_OWNER") or None
    if owner and not a.owner:
        print(f"  (owner-scoped via RD_OWNER={owner})")
    only = None if a.all_dates else date.today().isoformat()

    rec = Path(a.record)
    lines = (rec.read_text(encoding="utf-8", errors="ignore").splitlines()
             if rec.exists() else [])
    viols = check_record(rec, only)

    # Owner-scoped split (mirrors post_tick_check.py:135-159): a
    # violation on a row whose `owner:` == acting owner is that owner's
    # OWN debt ⇒ HARD; other-owner / unattributed ⇒ advisory; owner=None
    # ⇒ legacy global advisory (back-compat, no regression).
    def _viol_row(v: str) -> str:
        m = re.search(r"F-row `([^`]+)`", v)
        rid = m.group(1) if m else ""
        for ln in lines:
            if rid and rid in ln:
                return ln
        return ""

    hard, advisory = [], []
    for v in viols:
        ro = _row_owner(_viol_row(v))
        if owner is not None and ro == owner:
            hard.append(v)
        else:
            advisory.append(v)

    for v in advisory:
        print(f"WARN: {v}")
    for v in hard:
        print(f"HARD [owner={owner}: own-debt]: {v}")

    block = bool(hard) and a.blocking
    if block:
        try:
            from ztare.validator.calibration_gate import hard_allowed
        except Exception:
            import sys as _s
            _s.path.insert(0, str(REPO / "src"))
            from ztare.validator.calibration_gate import hard_allowed
        ok, why = hard_allowed("gap_g", owner)
        if not ok:
            block = False
            print(f"  CALIBRATION-GATE: {why} ⇒ --blocking DOWNGRADED "
                  f"to advisory (the converged precondition, mechanized).")
    scope = "all F-rows" if a.all_dates else f"F-rows dated {only}"
    print(f"\n{'FAIL' if block else 'OK'}: dispatch_ledger (GAP-G) — "
          f"{len(hard)} own-debt(HARD) + {len(advisory)} advisory over "
          f"{scope}; owner={owner or 'None(legacy-global-advisory)'} "
          f"({'blocking' if a.blocking else 'advisory'}).")
    return 1 if block else 0


if __name__ == "__main__":
    sys.exit(main())
