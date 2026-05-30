#!/usr/bin/env python3
"""
validate_prescription_surfacing.py

META-RCA fix (2026-05-16). Closes the **buried-prescription / point-fix
treadmill** failure class.

RECURRING META-FAILURE (the class this validator mechanizes away):
A correct prescribed move exists in the apparatus (an orchestration-menu
leaf/sub_class, an org/patterns entry, a mandate MUST/duty) but lands
NON-FORCING — a `confidence: candidate` sub_class, an INDEX pointer, a
mandate-by-reference, or a memory note. Nothing mechanically asserts the
invariant "every prescription is FORCED on the relevant precheck path,
or it fails closed." So prescriptions go dead-at-precheck SILENTLY; the
operator eventually notices one (e.g. void-mining unused across >=10 NS
recurrences; micro-forecast unused ~10 ticks; menu sub_class routing
dead-at-precheck); the repair each time is ONE bespoke hand-authored
forcing block for THAT prescription. N buried prescriptions => N
operator-catches => N hand-authored blocks. No generative closure.

This validator IS the generative closure: it enumerates the prescription
set and asserts each has a forcing surfacing on the precheck path. A new
buried prescription is then flagged the SAME tick (post_tick_check leg),
not after the operator notices the Nth recurrence. Hand-authored forcing
blocks remain valid as the substantive content; this guarantees COVERAGE
so the treadmill cannot re-form.

DISCIPLINE: a blocking gate must never false-FAIL (the surfacing test is
a grep heuristic). Therefore advisory by default (WARN, exit 0). Flip
`--blocking` only after calibration shows the gap list is true-positive
clean (mirrors the 3-tier discipline-linter calibration discipline).

Prescription set (mechanically enumerable, no judgment):
  * orchestration_menu.yaml — every top-level leaf + every sub_class
  * org/patterns/INDEX.md   — every PATTERN-xxx id

Surfacing corpus (the precheck path that actually FORCES a move):
  * scripts/public/control/rd_tick_brief.py        (kernel §8/§8c)
  * projects/ns_millennium_hunt/scripts/ns_scientific_amnesia_precheck.py (role module)
  * scripts/public/control/post_tick_check.py       (post legs)
  * org/key_results/*.md                            (closure_daemon duties)

A prescription is "surfaced" iff its id / leaf-name / a pattern token in
its default_chain appears in the surfacing corpus. Else => surfacing_gap.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MENU = REPO / "org/menu/orchestration_menu.yaml"
PATTERNS_INDEX = REPO / "org/patterns/INDEX.md"
ARCH_INDEX = REPO / "analytics/public/index/architecture_index.jsonl"
DEPLOY_LEDGER = REPO / "analytics/public/ledgers/pattern_deployment/pattern_deployment_ledger.jsonl"
NEGATIVE_OUTCOMES = {"event_0", "failed", "killed", "no_progress", None, ""}
SURFACING_FILES = [
    REPO / "scripts/public/control/rd_tick_brief.py",
    REPO / "projects/ns_millennium_hunt/scripts/ns_scientific_amnesia_precheck.py",
    REPO / "scripts/public/control/post_tick_check.py",
]
KR_DIR = REPO / "org/key_results"


def load_corpus() -> str:
    parts = []
    for f in SURFACING_FILES:
        if f.exists():
            parts.append(f.read_text(encoding="utf-8", errors="ignore"))
    if KR_DIR.exists():
        for kr in KR_DIR.glob("*.md"):
            txt = kr.read_text(encoding="utf-8", errors="ignore")
            if "owner_role: research_director" in txt and "recurrence" in txt:
                parts.append(txt)
    return "\n".join(parts)


def enumerate_prescriptions() -> list[tuple[str, str, list[str]]]:
    """Return (kind, name, tokens) — tokens any of which surfacing-hits."""
    out: list[tuple[str, str, list[str]]] = []

    if MENU.exists():
        cur_leaf = None
        in_sub = False
        chain: list[str] = []
        for raw in MENU.read_text(encoding="utf-8").splitlines():
            m_leaf = re.match(r"^  ([a-z_]+):\s*$", raw)
            m_sub_hdr = re.match(r"^    sub_classes:\s*$", raw)
            m_sub = re.match(r"^      ([a-z_]+):\s*$", raw)
            m_pat = re.search(r"(PATTERN-\d+)", raw)
            if m_leaf:
                cur_leaf = m_leaf.group(1)
                in_sub = False
                chain = []
                out.append(("menu_leaf", cur_leaf, [cur_leaf]))
            elif m_sub_hdr:
                in_sub = True
            elif m_sub and in_sub and cur_leaf:
                sub = m_sub.group(1)
                out.append(("menu_sub_class", f"{cur_leaf}.{sub}", [sub]))
            if m_pat and cur_leaf:
                # attach chain pattern as an alt surfacing token for the leaf
                for i, (k, n, t) in enumerate(out):
                    if n == cur_leaf and k == "menu_leaf":
                        if m_pat.group(1) not in t:
                            t.append(m_pat.group(1))

    if PATTERNS_INDEX.exists():
        for m in re.finditer(r"(PATTERN-\d+)", PATTERNS_INDEX.read_text(encoding="utf-8")):
            pid = m.group(1)
            if not any(n == pid for _, n, _ in out):
                out.append(("pattern", pid, [pid]))

    # dedupe by (kind,name)
    seen = set()
    uniq = []
    for row in out:
        key = (row[0], row[1])
        if key not in seen:
            seen.add(key)
            uniq.append(row)
    return uniq


def candidate_chains() -> dict[str, list[str]]:
    """Map `leaf.sub` (confidence: candidate) -> its chain PATTERN ids.
    These are the promotion-eligible prescriptions; usage of their
    chain on >=3 distinct substrates (non-negative outcome) flips them
    to leaf. Closes the catch-22 loop mechanically."""
    out: dict[str, list[str]] = {}
    if not MENU.exists():
        return out
    cur_leaf = None
    cur_sub = None
    in_sub = False
    for raw in MENU.read_text(encoding="utf-8").splitlines():
        m_leaf = re.match(r"^  ([a-z_]+):\s*$", raw)
        if re.match(r"^    sub_classes:\s*$", raw):
            in_sub = True
            continue
        m_sub = re.match(r"^      ([a-z_]+):\s*$", raw)
        if m_leaf:
            cur_leaf, cur_sub, in_sub = m_leaf.group(1), None, False
        elif m_sub and in_sub and cur_leaf:
            cur_sub = f"{cur_leaf}.{m_sub.group(1)}"
        elif cur_sub:
            if "confidence:" in raw and "candidate" in raw:
                out.setdefault(cur_sub, [])
            # ONLY count chain list-items `- PATTERN-xxx` (default_chain
            # / chain_addition), never prose/other refs — over-capture
            # across boundaries inflated substrate counts (false-promote).
            mp = re.match(r"^\s+-\s+(PATTERN-\d+)\b", raw)
            if mp and cur_sub in out:
                out[cur_sub].append(mp.group(1))
    return {k: v for k, v in out.items()}


def promotion_recommendations() -> list[str]:
    if not DEPLOY_LEDGER.exists():
        return []
    rows = []
    for ln in DEPLOY_LEDGER.read_text(errors="ignore").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(__import__("json").loads(ln))
        except Exception:
            pass
    recs = []
    for sub, pats in candidate_chains().items():
        if not pats:
            continue
        subs_ok = set()
        for r in rows:
            deployed = {r.get("primary_pattern")} | set(r.get("secondary_patterns") or [])
            if deployed & set(pats) and r.get("outcome_bucket_realized") not in NEGATIVE_OUTCOMES:
                subs_ok.add(r.get("substrate"))
        if len(subs_ok) >= 3:
            recs.append(f"PROMOTE-READY: {sub} — chain {','.join(pats)} "
                        f"deployed on {len(subs_ok)} distinct substrates "
                        f"with non-negative outcome; flip confidence: leaf")
    return recs


def validate(corpus: str, presc: list[tuple[str, str, list[str]]]):
    gaps, surfaced = [], []
    for kind, name, tokens in presc:
        hit = any(tok and tok in corpus for tok in tokens)
        (surfaced if hit else gaps).append(f"{kind}: {name}")
    return gaps, surfaced


def arch_self_surfacing_gaps(top_n: int = 12) -> tuple[list[str], int]:
    """Completeness backstop (GP-188 2026-05-16 reviewer-prescribed reframe).

    The deterministic primitive_tick_surface ranking is only a WEAK PRIOR.
    A primitive can be correctly registered in the architecture index yet
    be un-rankable even for *its own declared applicability* (e.g. a
    low-impact primitive buried under the 10*impact term — the
    LAGRANGIAN-DERIVATION class). This calls the REAL surfacing mechanism
    (not a lexical proxy) with each primitive's own applicability vector as
    the query, and flags any primitive that does not appear in its own
    top-N. Only primitives that declare an applicability vector are tested
    (a primitive that declares what it is for but cannot surface for that
    purpose is the actionable gap; doc/pattern rows without applicability
    are out of scope here). Advisory only — never a hard FAIL on its own.
    """
    if not ARCH_INDEX.exists():
        return [], 0
    src = str(REPO / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    try:
        from ztare.research_director.primitive_tick_surface import (  # type: ignore
            build_primitive_tick_surface,
        )
    except Exception as exc:  # pragma: no cover - import-env guard
        return [f"(skipped: cannot import primitive_tick_surface: {exc})"], 0

    import json as _json
    gaps: list[str] = []
    tested = 0
    for ln in ARCH_INDEX.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            row = _json.loads(ln)
        except Exception:
            continue
        pid = str(row.get("id") or "").strip()
        appl = row.get("applicability") or []
        appl = [str(a).strip() for a in appl if str(a).strip()]
        if not pid or not appl:
            continue
        tested += 1
        try:
            surf = build_primitive_tick_surface(query_terms=appl, top_n=top_n)
            ids = {h.id for h in surf.top_hits}
        except Exception as exc:
            gaps.append(f"{pid} (surface error: {exc})")
            continue
        if pid not in ids:
            gaps.append(
                f"{pid} — NOT in own top-{top_n} when queried by its own "
                f"applicability {appl}; capability is registered but "
                f"un-rankable for its declared purpose"
            )
    return gaps, tested


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocking", action="store_true",
                    help="exit 1 on any surfacing_gap (only after calibration)")
    ap.add_argument("--verbose-arch", action="store_true",
                    help="list every arch-index self-surfacing gap "
                         "(default: coverage metric + bounded sample only — "
                         "a full per-tick spew is itself the buried-"
                         "prescription anti-pattern)")
    args = ap.parse_args()

    if not MENU.exists():
        print(f"FATAL: {MENU} does not exist", file=sys.stderr)
        return 2

    corpus = load_corpus()
    presc = enumerate_prescriptions()
    gaps, surfaced = validate(corpus, presc)

    print(f"INFO: {len(surfaced)} prescriptions FORCED on precheck path")
    for g in gaps:
        print(f"WARN: surfacing_gap — prescription has NO forcing "
              f"surfacing on precheck path: {g}")

    arch_gaps, arch_tested = arch_self_surfacing_gaps()
    cov = (arch_tested - len(arch_gaps)) / arch_tested if arch_tested else 1.0
    print(f"INFO: arch-index completeness backstop — "
          f"{arch_tested - len(arch_gaps)}/{arch_tested} primitives "
          f"self-surfacing ({cov:.0%} deterministic-prior coverage). "
          f"The deterministic surface is a WEAK PRIOR only; the forced "
          f"authoritative path is agent primitives_considered (GAP-F).")
    shown = arch_gaps if args.verbose_arch else arch_gaps[:10]
    for ag in shown:
        print(f"WARN: arch_primitive: {ag}")
    if not args.verbose_arch and len(arch_gaps) > len(shown):
        print(f"WARN: ... {len(arch_gaps) - len(shown)} more "
              f"self-surfacing gaps (run --verbose-arch for the full list)")

    promos = promotion_recommendations()
    for p in promos:
        print(f"INFO: {p}")

    # Only menu/pattern prescriptions gate. The arch-index completeness
    # backstop (arch_self_surfacing_gaps) is always advisory — never a
    # hard FAIL on its own, even in --blocking mode (GP-188 reframe).
    if gaps and args.blocking:
        print(f"\nFAIL: {len(gaps)} surfacing_gap (blocking mode)",
              file=sys.stderr)
        return 1
    print(f"\nOK: {len(presc)} prescriptions checked, "
          f"{len(gaps)} surfacing_gap (advisory)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
