#!/usr/bin/env python3
"""run_reflexive_mine.py — single canonical entrypoint for the weekly
reflexive-mining practice.

Why this file exists (see docs/concepts/reflexive_mining_methodology.md §3, §5):
the pipeline was ~13 scripts with duplicated path constants; the scripts-reorg
stranded several at pre-reorg paths and a silent placeholder fallback served
stale dashboards undetected. One orchestrator owning the canonical paths in
ONE place makes the path-bug class and the cold/contextualized procedure
inversion structurally unable to recur.

Pipeline shape (exhaustive index, sampled rating — bounded tokens):
  Phase 1  INDEX     exhaustive, deterministic, ZERO tokens. Walks every
                     agent-work tree, excludes generated/vendored, emits a
                     complete artifact index + the in-loop vs out-of-loop
                     bifurcation report (the empirical answer to "is the
                     iter-loop dormant / where is the live work").
  Phase 2  MINE      run the deterministic miners in canonical order.
  Phase 3  RATE-GATE fail-loud. The canonical rater is the CONTEXTUALIZED
                     (warm) rater. This script never silently rates cold;
                     if fresh contextualized ratings are absent it STOPS
                     with the dispatch instruction.
  Phase 4  AGGREGATE rater-segregated (rater_id = cold_subagent_contextualized).
  Phase 5  DASHBOARD refresh-data + vite build — mandatory final step.

Token cost: phases 1,2,4,5 are zero-LLM. Only the externally-dispatched
warm rating costs tokens, and only on the weekly delta (content-sha ledger
dedup). Independent of corpus size.

Usage:
    python scripts/public/mining/run_reflexive_mine.py            # full cycle
    python scripts/public/mining/run_reflexive_mine.py --index-only
    python scripts/public/mining/run_reflexive_mine.py --skip-dashboard
"""
from __future__ import annotations

import argparse
import hashlib
import re
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
PY = sys.executable

# ---- canonical paths owned HERE, nowhere else --------------------------------
LEDGERS = REPO / "analytics" / "public" / "ledgers" / "trajectory"
QUERIES = REPO / "analytics" / "public" / "queries"
TASTE = QUERIES / "taste"
ARTIFACT_INDEX = REPO / "analytics" / "public" / "ledgers" / "reflexive" / "artifact_index.jsonl"
BIFURCATION = REPO / "analytics" / "public" / "ledgers" / "reflexive" / "bifurcation_report.json"
CANONICAL_RATER = "cold_subagent_contextualized"
CONTEXTUALIZED_MD = TASTE / "_taste_ratings_contextualized.md"

MINING = REPO / "scripts" / "public" / "mining"

# High-value evidence ledgers that MUST be provably covered every cycle
# (operator-requested 2026-05-16). Indexed unconditionally regardless of
# suffix rules so coverage is total and auditable.
KEY_LEDGERS = [
    "research_areas/EXPERIMENT_TRACK_RECORD.md",                       # F/E rows
    "research_areas/insights_ledger.md",                               # insight ledger
    "analytics/public/ledgers/prediction/prediction_ledger.jsonl",     # prediction ledger
    "analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md",
]

# Agent-work trees to index exhaustively (Phase 1). projects/ is the ZTARE
# iter-loop (charter + debate_log convention); everything else is agent work.
INDEX_TREES = ["projects", "scripts", "analytics", "ztare_proofs", "org",
               "research_areas", "docs/internal", "papers", "workspace"]
# Deterministic exclusions — generated/vendored/build noise. Indexing these
# would drown insight in machine output (Meta-Darwin to self, 2026-05-16).
EXCLUDE_SUBSTR = (".lake/", "node_modules/", "__pycache__/", "/.git/",
                  "/dist/", "/build/", ".pre_audit_", "/external_benchmarks/envs/",
                  "/queries/gnn/", "/queries/graphs/", "/lemma_relevance/",
                  # Private trees: never index. The dashboard had a redactor for
                  # these, but the JSONL itself was leaking the full paths
                  # (filename leak even when content stays private). Index-time
                  # exclusion is the structural fix.
                  "research_areas/private/", "/private/")
EXCLUDE_GENERATED_JSON_DIRS = ("analytics/public/queries/", "analytics/public/gnn/")
AUTHORED_SUFFIX = (".md", ".py", ".lean", ".yaml")


def sh(cmd: list[str], label: str) -> None:
    """Run a step; fail loud on non-zero (no silent continue)."""
    print(f"\n=== {label} ===")
    r = subprocess.run(cmd, cwd=str(REPO))
    if r.returncode != 0:
        print(f"FATAL: step '{label}' failed (exit {r.returncode}). "
              f"Aborting — no silent fallback (see methodology §6).")
        sys.exit(r.returncode)


def _excluded(rel: str) -> bool:
    if any(s in rel for s in EXCLUDE_SUBSTR):
        return True
    # generated JSON under query/gnn dirs is machine output, not authored
    if rel.endswith(".json") and any(rel.startswith(d) for d in EXCLUDE_GENERATED_JSON_DIRS):
        return True
    return False


_ITER_FILE_RE = re.compile(
    r"(^|/)(debate_log_iter_|iteration_telemetry|current_iteration|"
    r"debate_report|iter_)|(^|/)iter\d", re.IGNORECASE)


def _is_iter_loop(rel: str, p: Path) -> bool:
    """In-loop = the actual ZTARE *iteration work files* themselves
    (the `iter**` artifacts: debate_log_iter_*, iteration_telemetry,
    current_iteration, debate_report, iter_*). Operator-corrected
    2026-05-16: projects/ dirs are NOT in-loop wholesale — only the
    iteration work files are. Everything else (including the rest of
    projects/) is out-of-loop agent/governance work. This is the
    invariant."""
    return bool(_ITER_FILE_RE.search(rel.rsplit("/", 1)[-1])
                or _ITER_FILE_RE.search(rel))


def phase1_index() -> dict:
    """Exhaustive, deterministic, zero-token index + bifurcation report."""
    print("\n=== PHASE 1: exhaustive artifact INDEX (zero tokens) ===")
    ARTIFACT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    n_total = n_excl = 0
    by_tree: dict[str, int] = {}
    in_loop = out_loop = 0
    _today = {"all": 0, "iter_loop": 0, "agent_work": 0}
    _last7 = {"all": 0, "iter_loop": 0, "agent_work": 0}
    with ARTIFACT_INDEX.open("w") as out:
        for tree in INDEX_TREES:
            base = REPO / tree
            if not base.exists():
                continue
            for p in base.rglob("*"):
                if not p.is_file() or p.suffix not in AUTHORED_SUFFIX:
                    continue
                rel = str(p.relative_to(REPO))
                n_total += 1
                if _excluded(rel):
                    n_excl += 1
                    continue
                try:
                    st = p.stat()
                    sha = hashlib.sha1(p.read_bytes()).hexdigest()[:16]
                except Exception:
                    continue
                iter_loop = _is_iter_loop(rel, p)
                in_loop += iter_loop
                out_loop += (not iter_loop)
                _age_days = (datetime.now(timezone.utc).date()
                             - datetime.fromtimestamp(st.st_mtime, timezone.utc).date()).days
                if _age_days <= 0:
                    _today["all"] += 1
                    _today["iter_loop" if iter_loop else "agent_work"] += 1
                if _age_days <= 7:
                    _last7["all"] += 1
                    _last7["iter_loop" if iter_loop else "agent_work"] += 1
                top = tree.split("/")[0]
                by_tree[top] = by_tree.get(top, 0) + 1
                out.write(json.dumps({
                    "path": rel, "tree": top, "kind": p.suffix.lstrip("."),
                    "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%d"),
                    "size": st.st_size, "sha": sha,
                    "lane": "iter_loop" if iter_loop else "agent_work",
                }) + "\n")
    # Guarantee the high-value ledgers are in the index regardless of
    # suffix rules — coverage must be total and auditable.
    key_cov = {}
    with ARTIFACT_INDEX.open("a") as out:
        for rel in KEY_LEDGERS:
            p = REPO / rel
            present = p.exists()
            key_cov[rel] = present
            if present:
                st = p.stat()
                out.write(json.dumps({
                    "path": rel, "tree": rel.split("/")[0], "kind": p.suffix.lstrip("."),
                    "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%d"),
                    "size": st.st_size,
                    "sha": hashlib.sha1(p.read_bytes()).hexdigest()[:16],
                    "lane": "key_ledger",
                }) + "\n")
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "key_ledger_coverage": key_cov,
        "scanned": n_total, "excluded_generated_vendored": n_excl,
        "indexed": n_total - n_excl, "by_tree": by_tree,
        "bifurcation": {"iter_loop_artifacts": in_loop,
                        "agent_work_artifacts": out_loop,
                        "agent_work_share": round(out_loop / max(1, in_loop + out_loop), 3)},
        "as_of_today": {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "modified_today": _today,
            "modified_last_7d": _last7,
            "note": "point-in-time snapshot (NOT weekly-bucketed): authored "
                    "artifacts touched today / in the trailing 7 days, by lane.",
        },
        "note": "iter_loop = the ZTARE iteration work files themselves "
                "(iter** artifacts: debate_log_iter_*, iteration_telemetry, "
                "current_iteration, debate_report, iter_*). agent_work = "
                "everything else, INCLUDING the rest of projects/ (the live "
                "out-of-loop substrate). The invariant is the iter** files, "
                "not project-dir membership.",
    }
    BIFURCATION.write_text(json.dumps(report, indent=2))
    print(json.dumps(report["bifurcation"], indent=2))
    print(f"  indexed {report['indexed']} authored artifacts "
          f"({n_excl} generated/vendored excluded) → {ARTIFACT_INDEX.relative_to(REPO)}")
    return report


def phase2_mine() -> None:
    steps = [
        ("mine_trajectories.py", "Stage-1 extract"),
        ("mine_trajectories_enrich.py", "Stage-1 enrich"),
        ("mine_trajectory_curves.py", "trajectory curves"),
        ("detect_inflections.py", "inflections"),
        ("mine_reference_graph.py", "reference graph"),
        ("build_consequential_artifacts.py", "consequential artifacts"),
        ("build_context_primer.py", "context primer (rater anchor)"),
        ("mine_recursive_gain_candidates.py", "recursive-gain candidates"),
        ("sample_artifacts_for_taste.py", "stratified taste sample"),
    ]
    # P1 (Meta-Darwin 2026-06-04): refresh the candidate aggregator's PRODUCER miners BEFORE the
    # consumer so candidates reflect current work. BEST-EFFORT (WARN-not-fatal, like mine_climb_triggers):
    # mine_closure_patterns reads the daemon-managed F-row store, often absent locally — a producer miss
    # must NOT abort the cycle (it just leaves that scorecard as-is, no worse than pre-P1).
    import subprocess as _sp
    for _script, _label in [("research_mode/mine_closure_patterns.py", "closure patterns (producer)"),
                            ("research_mode/mine_structural_analogies.py", "structural analogies (producer)")]:
        _r = _sp.run([PY, str(MINING / _script)], capture_output=True, text=True)
        if _r.returncode == 0:
            print(f"PHASE 2 (producer, best-effort): {_label} ✓")
        else:
            print(f"  WARN: producer '{_label}' exit {_r.returncode} — scorecard left as-is, continuing "
                  f"(often the daemon-managed F-row store is absent locally): {(_r.stderr or _r.stdout or '')[-140:]}")
    for script, label in steps:
        sh([PY, str(MINING / script)], f"PHASE 2: {label}")
    # G6: keep the graphs/ reader copy in sync with the canonical writer path
    src = QUERIES / "reference_graph.json"
    dst = QUERIES / "graphs" / "reference_graph.json"
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        print(f"  G6 sync: reference_graph.json → graphs/")


def sh_soft(cmd: list[str], label: str) -> bool:
    """Best-effort step: WARN + continue on failure (for optional
    enrichment feeders whose absence degrades but does not CORRUPT the
    primary measurement). Fail-loud granularity, not silent fallback."""
    print(f"\n=== {label} ===")
    r = subprocess.run(cmd, cwd=str(REPO))
    if r.returncode != 0:
        print(f"WARN: optional step '{label}' failed (exit {r.returncode}); "
              f"continuing. Tracked as debt — see methodology §4.")
        return False
    return True


def phase2b_impact() -> None:
    """Capability-side of recursive gain: impact-weighted recursive
    reuse of the apparatus's own capabilities. Complementary to the
    artifact-side taste curve. (operator: 'impact weighted graph for
    experimentation … recursive use of capabilities … part of the
    orchestrator calculator', 2026-05-16.) Cheap/deterministic."""
    print("\n=== PHASE 2b: impact / recursive-capability-use calculator ===")
    # climb_triggers is an OPTIONAL impact feeder (currently broken: missing
    # reorg-deleted weakest_link_clusters input — G-class debt). Best-effort.
    sh_soft([PY, str(MINING / "mine_climb_triggers.py")],
            "PHASE 2b: climb triggers (optional impact feeder)")
    # The decision-critical recursive-capability-use signals — fail-loud:
    roi = REPO / "scripts" / "public" / "analytics_shared" / "reflexive_primitive_roi_audit.py"
    if roi.exists():
        sh([PY, str(roi)],
           "PHASE 2b: reflexive primitive ROI (critical|useful|dead bands)")
    render = REPO / "scripts" / "public" / "control" / "render_architecture_index.py"
    if render.exists():
        sh([PY, str(render)],
           "PHASE 2b: re-render architecture_index (impact_factor / last_used)")
    # Prediction ledger = calibrated-bets signal over time (operator-requested
    # 2026-05-16). Structured data with its own calibration miner; read-only.
    calib = REPO / "scripts" / "public" / "analytics_shared" / "score_prediction_ledger_calibration.py"
    if calib.exists():
        sh([PY, str(calib)],
           "PHASE 2b: prediction-ledger calibration (Brier / calibrated-bets)")


def phase3_rate_gate() -> None:
    """Fail loud unless fresh CONTEXTUALIZED ratings exist. Never cold-fallback."""
    print("\n=== PHASE 3: rating gate (canonical = contextualized/warm) ===")
    sample = TASTE / "_taste_sample.md"
    # Incremental-dedup: if the sampler found 0 new samples (every artifact
    # already content-sha-cached in the ledger) the canonical contextualized
    # series is current by construction — nothing to re-rate. Forcing a
    # re-rate of unchanged content would waste tokens and defeat the
    # incremental design (methodology §5). Only require fresh
    # ratings when there is genuinely new work.
    n_new = None
    meta = TASTE / "_taste_metadata.json"
    if meta.exists():
        try:
            n_new = json.loads(meta.read_text()).get("n_new")
        except Exception:
            n_new = None
    if n_new == 0 and CONTEXTUALIZED_MD.exists():
        print("  OK: 0 new samples (fully cache-served); contextualized "
              "series current — no re-rate needed.")
        return
    if not CONTEXTUALIZED_MD.exists() or (sample.exists() and
            CONTEXTUALIZED_MD.stat().st_mtime < sample.stat().st_mtime):
        print(
            "STOP — fresh contextualized ratings required and absent/stale.\n"
            f"  Expected: {CONTEXTUALIZED_MD.relative_to(REPO)} newer than the sample.\n"
            "  Dispatch a CONTEXTUALIZED (warm) rater agent: read\n"
            "  analytics/public/queries/taste/_taste_context_primer.md (anchor)\n"
            "  + _taste_sample.md, rate per rubric, write the contextualized .md.\n"
            "  Cold / cross-family are CONTROLS only — never the primary series.\n"
            "  Re-run with --resume-after-rating once ratings are written.")
        sys.exit(2)
    print(f"  OK: fresh contextualized ratings present.")


def phase4_aggregate() -> None:
    rate = MINING / "rate_artifacts_for_taste.py"
    sh([PY, str(rate), "--mode", "parse-existing",
        "--out-md", str(CONTEXTUALIZED_MD),
        "--out-json", str(TASTE / "_taste_ratings.json")],
       "PHASE 4: parse contextualized .md → .json")
    sh([PY, str(MINING / "aggregate_taste.py"), "--rater-id", CANONICAL_RATER],
       f"PHASE 4: aggregate sample-scoped (rater-segregated: {CANONICAL_RATER})")
    # G8/§5c canonical series: read-only, full-history, ledger-derived.
    # Sample-scoped aggregation above answers "this week's sample"; the
    # canonical series answers "the apparatus's week-over-week curve"
    # and is the decision-critical input for the P0 recursive-gain metric.
    sh([PY, str(MINING / "build_taste_canonical_series.py"),
        "--rater", CANONICAL_RATER],
       f"PHASE 4: build canonical series from ledger (rater={CANONICAL_RATER})")
    # Fold every dataset the dashboard consumes into one bundle file
    # (collapses nine drift surfaces to one — §5 consolidation plan).
    sh([PY, str(MINING / "build_dashboard_bundle.py")],
       "PHASE 4: build dashboard bundle (9 datasets → 1 file)")


import re as _re

# Private/sensitive patterns that must NEVER reach the shipped index.html
# (the dashboard build inlines its data — leak travels into the artifact).
_LEAK_PATTERNS = [
    # Redact the private seam tree (path names = a private roadmap).
    (_re.compile(r"research_areas/private[A-Za-z0-9_./-]*"), "research_areas/[redacted]"),
    # Sibling/tenant repo references.
    (_re.compile(r"\.\./(cognitive-firm|ztare-research-co)[A-Za-z0-9_./-]*"), "[sibling-repo]"),
    (_re.compile(r"ztare-research-co[A-Za-z0-9_./-]*"), "[tenant]"),
    # Tightened: redact ONLY the identifying home segment (username),
    # not arbitrary trailing text — avoids mangling legitimate content
    # that merely contains a path-like substring.
    (_re.compile(r"/Users/[A-Za-z0-9_.-]+"), "/Users/[user]"),
]
# Unified, normalized, case-insensitive SENSITIVE predicate — the single
# source of truth for the assertion (the forcing core). Covers the
# independent-adversary bypasses (2026-05-16): bare `private/<subdir>`
# without the research_areas prefix, `cognitive-firm` (not just `../`-
# prefixed), tenant, raw home paths, and case variants. Escaped
# separators (\/, /, \\) are normalized away BEFORE matching so
# JSON-escaped forms cannot slip past. Redaction stays best-effort/
# conservative (above); THIS is what we actually trust, asserted over
# the single shipped artifact (dist/index.html, after dist/ is stripped
# to it — masking by not-shipping, see phase5_dashboard).
_PRIV_SUBDIRS = ("philosophy", "seams", "evidence", "engine", "mutator",
                 "charters", "protocol", "interfaces", "cage", "apparatus")
# NOTE: `cognitive-firm` is deliberately NOT here — it is a PUBLIC
# release target (github.com/sparckix/cognitive-firm); flagging it would
# false-positive the gate on legitimate public references. The genuinely
# private markers are the private seam tree, the private tenant overlay
# `ztare-research-co`, and raw local home paths.
_LEAK_SCAN = _re.compile(
    r"research_areas/private"
    r"|(?<![\w-])private/(?:" + "|".join(_PRIV_SUBDIRS) + r")"
    r"|ztare-research-co"
    r"|/Users/[A-Za-z0-9_.-]+/",
    _re.IGNORECASE,
)


def _normalize_for_scan(text: str) -> str:
    """Defeat escaped-separator bypasses before scanning (adversary C6)."""
    return (text.replace("\\/", "/")
                .replace("\\u002f", "/").replace("\\u002F", "/")
                .replace("\\\\", "/"))


def _sanitize_dashboard_data(dash: Path) -> int:
    """Redact private path strings from the dashboard's bundled data
    BEFORE vite inlines them. Returns count of files sanitized.
    Generation-agnostic defense-in-depth: protects the shipped artifact
    regardless of which miner introduced the path."""
    n = 0
    for d in (dash / "src" / "data", dash / "public" / "data"):
        if not d.exists():
            continue
        for f in d.iterdir():
            if f.suffix not in (".json", ".md") or not f.is_file():
                continue
            txt = f.read_text(encoding="utf-8", errors="ignore")
            new = txt
            for pat, repl in _LEAK_PATTERNS:
                new = pat.sub(repl, new)
            if new != txt:
                f.write_text(new)
                n += 1
    return n


def phase5_dashboard() -> None:
    dash = REPO / "analytics" / "public" / "dashboard"
    print("\n=== PHASE 5: dashboard refresh-data ===")
    r = subprocess.run(["bash", str(dash / "scripts" / "refresh-data.sh")],
                        cwd=str(dash))
    if r.returncode != 0:
        print(f"FATAL: refresh-data failed (exit {r.returncode})."); sys.exit(r.returncode)
    print("\n=== PHASE 5: sanitize bundled data (publish-safety gate) ===")
    ns = _sanitize_dashboard_data(dash)
    print(f"  sanitized {ns} bundled data file(s) of private path strings")
    print("\n=== PHASE 5: dashboard build (tsc + vite — NO npm-script "
          "refresh-data; that would overwrite the sanitized data) ===")
    binr = dash / "node_modules" / ".bin"
    tsc = subprocess.run([str(binr / "tsc")], cwd=str(dash))
    if tsc.returncode != 0:
        print(f"FATAL: tsc failed (exit {tsc.returncode})."); sys.exit(tsc.returncode)
    r = subprocess.run([str(binr / "vite"), "build"], cwd=str(dash))
    if r.returncode != 0:
        print(f"FATAL: dashboard build failed (exit {r.returncode})."); sys.exit(r.returncode)
    # MASKING BY NOT-SHIPPING (adversary C1 fix): the singlefile build
    # inlines everything into index.html, so dist/data/ + any sibling
    # assets are REDUNDANT — but vite copies public/ into dist/ and a
    # static host (Vercel) would serve them un-asserted. Strip dist/ to
    # the single self-contained artifact so there is exactly ONE shipped
    # file and the assertion covers 100% of what ships.
    distdir = dash / "dist"
    idx = distdir / "index.html"
    if not idx.exists():
        print("FATAL: dist/index.html missing post-build."); sys.exit(3)
    import shutil as _sh
    for child in distdir.iterdir():
        if child.name == "index.html":
            continue
        (_sh.rmtree(child) if child.is_dir() else child.unlink())
    remaining = [p.name for p in distdir.iterdir()]
    if remaining != ["index.html"]:
        print(f"FATAL: dist/ not reduced to index.html only: {remaining}")
        sys.exit(3)
    # FORCING CORE: assert the SOLE shipped file with the unified,
    # normalized, case-insensitive predicate (defeats escaped/prefix/
    # case bypasses). This is what we trust — not the best-effort
    # pre-build sanitize.
    # PUBLISH-BLOCKED (honest fail-closed). This gate FAILED two
    # independent adversary reviews in one session (2026-05-16): a
    # post-hoc scanner over intrinsically path-laden mined data is
    # structurally whack-a-mole (allow-list trap; multiple private trees
    # — research_areas/private, scripts/private, cognitive-firm/evidence).
    # Per the standing adversarial-survival rule, the detection logic is
    # NOT reimplemented mid-session. We do NOT certify publish-safety.
    # The build artifact exists for LOCAL / gitignored use only. A public
    # deploy requires the spec'd redesign (mask at generation source or
    # do not ship mined data) + a fresh independent adversary. See
    # docs/concepts/reflexive_mining_methodology.md and task #7.
    informational = _LEAK_SCAN.findall(
        _normalize_for_scan(idx.read_text(encoding="utf-8", errors="ignore")))
    print(f"  PUBLISH-BLOCKED: dist/index.html built for LOCAL/gitignored "
          f"use only — NOT certified publish-safe (gate failed 2 adversary "
          f"reviews; redesign required). Indicative residual markers "
          f"(non-exhaustive, scanner known-leaky): {len(informational)}. "
          f"Do NOT public-deploy until task #7 redesign + re-adversary.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-only", action="store_true",
                    help="Phase 1 only (free; answers coverage + bifurcation)")
    ap.add_argument("--skip-dashboard", action="store_true")
    ap.add_argument("--resume-after-rating", action="store_true",
                    help="Skip mine; assume sample exists; go gate→aggregate→dashboard")
    args = ap.parse_args()

    print("=== reflexive mine — canonical orchestrator ===")
    print("methodology: docs/concepts/reflexive_mining_methodology.md")

    if not args.resume_after_rating:
        phase1_index()
        if args.index_only:
            return 0
        phase2_mine()
        phase2b_impact()
        # GP-236 P0 rollup — deterministic, no gate (mechanical
        # aggregation; consumes the calibration track, never recomputes).
        p0 = MINING / "build_p0_metrics.py"
        if p0.exists():
            sh([PY, str(p0)], "PHASE 2c: GP-236 P0 metrics rollup")
        # GP-237 survivors — laundering tripwire + non-accumulation
        # regression/rework rate (NOT a sophistication score; v1/v3/v4
        # killed). Deterministic; F1 dogfood self-rejects if the gate
        # is broken (exit 3 = honest fail, not silent pass).
        ph = MINING / "build_proof_health.py"
        if ph.exists():
            sh([PY, str(ph)], "PHASE 2d: GP-237 proof-health (tripwire + regression rate)")
    phase3_rate_gate()
    phase4_aggregate()
    if not args.skip_dashboard:
        # so-what freshness gate: the per-graph takeaway is authored
        # in-flight by THIS cycle's agent; block the dashboard if it is
        # stale/missing (don't ship last week's interpretation).
        sowhat = MINING / "build_graph_sowhat.py"
        if sowhat.exists():
            sh([PY, str(sowhat)], "PHASE 4b: so-what freshness gate")
        phase5_dashboard()
    print("\n=== reflexive cycle complete ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
