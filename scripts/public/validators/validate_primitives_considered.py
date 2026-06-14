#!/usr/bin/env python3
"""
validate_primitives_considered.py

rigorous forcing core for the "surfaced-but-not-used primitive"
failure (RCA 2026-05-16). Sibling of
validate_prescription_surfacing.py — it does NOT fork the parallel
agent's post_tick §3b block; it is wired as its own additive advisory
leg (GAP-F), exactly like GAP-E.

THE FAILURE THIS MECHANIZES AWAY
The architecture index is fresh, wired (rd_tick_brief §9), and carries
the right primitive for a tick — yet the agent ships the tick without
using it (e.g. a PDE estimate with dimensional/endpoint errors a
0-cost gate would have hard-blocked) because the surface is ADVISORY
and drowned in print. An advisory artifact nobody is forced to read is
epistemically identical to the noise it replaced. The only fix that
works is a MACHINE-CHECKED CONTRACT FIELD on the tick's F-row, same
enforcement class as §3b / ORDERING.

THE CONTRACT
A substantive tick F-row (dated today) MUST carry, somewhere in the
row, the token `primitives_considered:` listing the primitive ids it
considered, OR `why_not:<ID>` explicitly declining the top-ranked
registry primitive for that tick's scope. Absence ⇒ flag.

DESIGN (pre-empts the prior adversarial must-fix list):
 1. REGISTRY-DERIVED, never hardcoded: the expected primitive for a
    tick is computed from analytics/public/index/architecture_index.jsonl
    by matching the F-row's own scope text against each row's
    `applicability` + `description`, ranked by `impact_factor_expost`.
    If a gate/primitive is renamed/retired in the registry, this
    auto-tracks (no hand-authored list to rot).
 2. PER-F-ROW SELF-SCOPED: scope comes from each F-row's OWN text, not
    from a shared mutable surface file ⇒ no fleet-global race (the
    critical bug the last review caught).
 3. ADVISORY-FIRST, never-false-FAIL: default WARN / exit 0; `--blocking`
    only after calibration shows the flags are true-positive clean.
    Narrow exceptions + stderr breadcrumb — never silent-forever (the
    self-reproducing-disease bug the last review caught).
 4. NO MD / NO ARTIFACT: this validator IS the machine check; the MD is
    only ever a render elsewhere, never the mechanism.

Calibrate, then flip `--blocking`; wire as post_tick GAP-F advisory.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
INDEX = REPO / "analytics" / "public" / "index" / "architecture_index.jsonl"
TRACK = REPO / "research_areas" / "EXPERIMENT_TRACK_RECORD.md"

# RETROACTIVE-EXEMPT (adversary must-fix #3): the contract applies only
# to F-rows created strictly AFTER the gate is announced. All rows dated
# <= ANNOUNCE_DATE predate the contract and are exempt (a 100%-flag gate
# is dead-on-arrival / trains learned-helplessness = the buried-
# prescription failure recursing). F-row date convention is bare
# YYYY-MM-DD interpreted as UTC (matches _today()).
ANNOUNCE_DATE = "2026-05-16"

# IMPACT-THRESHOLD (must-fix #2): only a HIGH-impact registry primitive
# whose applicability CLASS matches the tick is a "must-consider". Raw
# token-soup overlap on description was noisy (TICK605→FRICTION-DEBATE);
# require a structured applicability-class match + impact >= threshold.
IMPACT_THRESHOLD = 4
CLASS_MATCH_MIN = 2  # >=2 shared significant tokens of ONE applicability entry

# Row-class selector tightened (must-fix #3 non-blocking): require an
# unambiguous tick marker, not generic words ("derived"/"kill"/"estimate"
# over-matched methodology rows). A real tick row's ID carries one of:
_TICK_ID_MARKERS = ("-tick", "tick5", "tick6", "recurrence", "-route1",
                    "-route-1", "-c7-", "-c3-", "-clay-")
_CONTRACT_TOKENS = ("primitives_considered:", "primitives-considered:",
                    "primitive_considered:", "why_not:", "why-not:")

# CLOSED machine-checkable why_not: vocabulary (mirrors GAP-G's closed
# SANCTIONED set; converged adversarial-review must-fix 2026-05-16). A
# `why_not:<ID>` decline is only valid if it carries one of these
# reasons — free prose is NOT a valid self-account (that was the
# substring-launderable AP-014 hole). Keep this set small + closed.
WHY_NOT_REASONS = (
    "not_applicable", "scope_mismatch", "superseded_by_alternative",
    "already_satisfied_upstream", "deferred_separate_task",
    "insufficient_evidence",
)


def load_registry() -> list[dict]:
    if not INDEX.exists():
        return []
    rows: list[dict] = []
    for ln in INDEX.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except Exception:
            continue  # one malformed row must not blind the validator
    return rows


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def _norm_id(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def expected_top_primitive(scope_text: str, registry: list[dict]) -> dict | None:
    """Principled signal (adversary must-fix #2). A registry primitive
    is a "must-consider" for this tick ONLY if BOTH:
      (a) at least one of its STRUCTURED `applicability` class-labels
          shares >= CLASS_MATCH_MIN significant tokens with the F-row
          scope (class match, not description token-soup — soup gave
          the spurious TICK605→FRICTION-DEBATE match), AND
      (b) impact_factor_expost >= IMPACT_THRESHOLD (only high-impact
          primitives are worth forcing).
    Ranked by impact, tie-broken by best class overlap. Pure function
    of (scope, registry) — no shared state, no race."""
    st = _tokens(scope_text)
    if not st:
        return None
    scored: list[tuple[float, int, dict]] = []
    for r in registry:
        impact = float(r.get("impact_factor_expost", 0) or 0)
        if impact < IMPACT_THRESHOLD:
            continue
        best_cls = 0
        for a in (r.get("applicability") or []):
            ov = len(st & _tokens(str(a)))
            if ov > best_cls:
                best_cls = ov
        if best_cls < CLASS_MATCH_MIN:
            continue
        scored.append((impact, best_cls, r))
    if not scored:
        return None
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return scored[0][2]


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _row_date(ln: str) -> str | None:
    # Canonical date = the backtick-wrapped date CELL (F-row col 2),
    # not the first date anywhere in the line. Converged must-fix:
    # a UTC-rollover resolve-stamp or scope-text date as first match
    # silently mis-exempts rows (exemption-bypass FP source).
    m = re.search(r"`(\d{4}-\d{2}-\d{2})`", ln)
    if m:
        return m.group(1)
    m = re.search(r"(\d{4}-\d{2}-\d{2})", ln)
    return m.group(1) if m else None


def _contract_value(low: str) -> str | None:
    """Text following the contract token, scoped to the MARKDOWN CELL
    that contains it (cell-aware). Converged must-fix: the prior
    'cut at first | after token' truncated to empty when the token sat
    near a cell edge (independent FP source). Split into cells first,
    find the cell holding a contract token, return its post-token text."""
    cells = low.split("|")
    for cell in cells:
        for tok in _CONTRACT_TOKENS:
            i = cell.find(tok)
            if i != -1:
                return cell[i + len(tok):]
    return None


def _session_new_scripts() -> list[str]:
    """git-untracked/added *.py under scripts|src — the reinvention
    surface (a NEW file is where duplication of a registered primitive
    actually happens; that is what bit this session, e.g. orphaned
    bundle_run / disposable run_*.py)."""
    import subprocess
    try:
        out = subprocess.run(["git", "status", "--porcelain"],
                              capture_output=True, text=True, timeout=20,
                              cwd=str(REPO)).stdout
    except Exception:
        return []
    paths: list[str] = []
    for ln in out.splitlines():
        st, _, p = ln.partition(" ")
        p = ln[3:].strip()
        if (ln[:2].strip() in ("??", "A", "AM")
                and p.endswith(".py")
                and (p.startswith("scripts/") or p.startswith("src/"))
                and "/test" not in p and not p.split("/")[-1].startswith("test_")):
            paths.append(p)
    return paths


def duplication_flags(registry: list[dict]) -> list[str]:
    """SYMMETRY arm (relayed-review): catch 'created a NEW file that
    duplicates a registered primitive' — the failure that actually bit
    this session. A new script whose stem ~matches a registered
    primitive's path-stem or normalized id ⇒ reinvention flag."""
    reg_stems = {}
    for r in registry:
        rp = str(r.get("path", ""))
        if rp:
            reg_stems[Path(rp).stem.lower()] = r.get("id")
        rid = _norm_id(str(r.get("id", "")))
        if rid:
            reg_stems.setdefault(rid, r.get("id"))
    out: list[str] = []
    for p in _session_new_scripts():
        stem = Path(p).stem.lower()
        nstem = _norm_id(stem)
        hit = None
        for k, rid in reg_stems.items():
            if not k:
                continue
            if k == stem or k == nstem or (len(k) >= 6 and (k in nstem or nstem in k)):
                hit = rid
                break
        if hit:
            out.append(
                f"NEW script '{p}' duplicates registered primitive "
                f"'{hit}' — extend/reuse it, do not reinvent (orphan "
                f"anti-pattern)")
    return out


def validate(blocking: bool) -> int:
    if not TRACK.exists():
        print(f"INFO: {TRACK} absent; nothing to check", file=sys.stderr)
        return 0
    registry = load_registry()
    if not registry:
        print("WARN: architecture index empty/unreadable — "
              "primitives_considered check degraded (advisory)",
              file=sys.stderr)
        return 0
    flags: list[str] = []
    # SYMMETRY arm — DISABLED 2026-05-16 (failed its own dogfood):
    # `git status --porcelain ??` means "untracked in THIS checkout",
    # NOT "created this session" — on this working copy that is 108
    # pre-existing files incl. the registered primitives themselves, so
    # duplication_flags produced 42 false positives (a primitive's own
    # file "duplicating" itself). Shipping that even advisory is the
    # 100%-noise treadmill this gate exists to kill. A correct
    # reinvention-arm needs: (a) a real session-baseline (git diff vs a
    # session-start ref), NOT untracked-state; (b) self-match exclusion
    # (skip when new path == the registered primitive's own path);
    # (c) calibration to a low FP rate. Spec'd for the primitives-considered gate; the
    # function is retained (not deleted) but NOT called until built
    # properly + dogfood-passed + adversary-passed. Consider-arm below
    # is sound and stays active (advisory).
    _ = duplication_flags  # keep referenced; intentionally not invoked
    checked = 0
    exempt = 0
    for ln in TRACK.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not ln.startswith("| F-"):
            continue
        rid = ln.split("|", 2)[1].strip()
        ridl = rid.lower()[:80]
        # tightened selector (must-fix #3): unambiguous tick marker in
        # the ID, not generic body words.
        if not any(m in ridl for m in _TICK_ID_MARKERS):
            continue
        # SCOPED TRIGGER (relayed-review b): only fire the
        # consider-an-existing-primitive arm on ticks that BUILD /
        # DISPATCH a capability or CREATE/mechanize a script — not
        # every tick (every-tick = noise = the treadmill it fights).
        scl = ln.lower()
        if not any(k in scl for k in (
                "build", "wire", "mechaniz", "validator", "gate",
                "primitive", "dispatch", "harness", "script", "pde",
                "estimate", "workbench", "forcing")):
            continue
        rdate = _row_date(ln)
        if rdate is None:
            continue
        # RETROACTIVE-EXEMPT: rows dated STRICTLY BEFORE the announce
        # date predate the contract. Converged must-fix: `<=` exempted
        # the announce-day rows too ⇒ on ANNOUNCE_DATE==today the
        # calibration corpus is EMPTY (gate checks 0 rows ⇒ a flip to
        # HARD is unmeasurable). `<` makes the announce day + after the
        # checkable calibration corpus (the evidence-generation mech).
        if rdate < ANNOUNCE_DATE:
            exempt += 1
            continue
        checked += 1
        cells = [c.strip() for c in ln.split("|")]
        scope = (cells[3] if len(cells) > 3 else "") + " " + rid
        top = expected_top_primitive(scope, registry)
        if top is None:
            continue  # no HIGH-impact applicability-class match (ok)
        exp_id = str(top.get("id", ""))
        cv = _contract_value(ln.lower())
        # STRUCTURED + MACHINE-CHECKABLE (converged must-fix): the
        # contract must NAME the specific expected id. A `primitives_
        # considered:` naming passes. A `why_not:` decline passes ONLY
        # if it also carries a reason from the CLOSED WHY_NOT_REASONS
        # vocabulary (free prose = the substring-launderable AP-014
        # hole; mirrors GAP-G's closed SANCTIONED set).
        ln_low = ln.lower()
        names_id = (cv is not None and _norm_id(exp_id)
                    and _norm_id(exp_id) in _norm_id(cv))
        if names_id:
            is_why_not = ("why_not:" in ln_low) or ("why-not:" in ln_low)
            if not is_why_not:
                continue  # affirmatively considered — pass
            if any(r in ln_low for r in WHY_NOT_REASONS):
                continue  # declined with a closed-vocab reason — pass
            flags.append(
                f"F-row '{rid[:70]}' `why_not:{exp_id}` lacks a CLOSED "
                f"reason {list(WHY_NOT_REASONS)} — free-prose decline is "
                f"not a machine-checkable self-account (AP-014)")
            continue
        flags.append(
            f"F-row '{rid[:70]}' must consider '{exp_id}' "
            f"(impact={top.get('impact_factor_expost')}, applicability-"
            f"class match) — no `primitives_considered:{exp_id}` / "
            f"`why_not:{exp_id}=<closed_reason>` names it")
    for f in flags:
        print(f"WARN: primitives_considered (GAP-F): {f}")
    print(f"\n{'FAIL' if (flags and blocking) else 'OK'}: {checked} "
          f"post-announce tick-rows checked, {exempt} retroactive-exempt, "
          f"{len(flags)} missing the specific-primitive contract"
          f"{' (advisory)' if not blocking else ''}")
    return 1 if (flags and blocking) else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocking", action="store_true",
                    help="exit 1 on any missing contract (only after "
                         "calibration shows flags are true-positive)")
    args = ap.parse_args()
    blocking = args.blocking
    if blocking:
        import os
        owner = os.environ.get("RD_OWNER") or None
        try:
            import sys as _s
            _s.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
            from ztare.validator.calibration_gate import hard_allowed
            ok, why = hard_allowed("gap_f", owner)
        except Exception as e:
            ok, why = False, f"calibration-gate unavailable ⇒ refuse HARD ({e})"
        if not ok:
            blocking = False
            print(f"CALIBRATION-GATE: {why} ⇒ --blocking DOWNGRADED to "
                  f"advisory (GAP-F is a heuristic; the converged "
                  f"precondition, mechanized — no FP-free calibration "
                  f"entry ⇒ no HARD).")
    try:
        return validate(blocking)
    except (OSError, ValueError) as e:  # narrow; never silent-forever
        print(f"WARN: primitives_considered check degraded "
              f"(advisory, not silent): {e}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
