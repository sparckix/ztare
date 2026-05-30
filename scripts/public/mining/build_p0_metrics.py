#!/usr/bin/env python3
"""build_p0_metrics.py — GP-236 P0 rollup. The instrument documenting its
own metrics. DETERMINISTIC, zero-token. CONSUMER/aggregator, NOT a
recomputer: prediction/forecast/RD-pessimism metrics are generated in the
calibration track (owned elsewhere — do not recompute here); this only
READS their canonical output. "Reliable" means honest: anything not
reliably computable from available data emits value=null with
status="not_yet_computable" + reason, never a fabricated number.

Spec: research_areas/private/seams/apparatus/instrumentation/GP-236_p0_metrics_rollup_seam.md
Out:  analytics/public/ledgers/reflexive/p0_metrics.json
"""
from __future__ import annotations
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
OUT = REPO / "analytics/public/ledgers/reflexive/p0_metrics.json"
HISTORY = REPO / "analytics/public/ledgers/reflexive/p0_metrics_history.jsonl"
M: list[dict] = []


def _load(rel: str):
    try:
        return json.loads((REPO / rel).read_text(encoding="utf-8"))
    except Exception:
        return None


def _infer_value_kind(value) -> str:
    """Tag each metric's value shape so the renderer can pick the right
    display. ``scalar`` → number/typography, ``breakdown`` → key:value
    grid, ``series`` → list-of-period rows / time series, ``null`` →
    not-yet-computable."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "scalar"  # rare; treat as scalar
    if isinstance(value, (int, float)):
        return "scalar"
    if isinstance(value, list):
        return "series"
    if isinstance(value, dict):
        return "breakdown"
    return "scalar"  # string or other — fall back to scalar typography


def add(group, key, label, value, unit, lane, tier, source, caveat,
        self_measured=True, status="ok", owner="p0_rollup"):
    M.append({"group": group, "key": key, "label": label, "value": value,
              "unit": unit, "lane": lane, "tier": tier, "source": source,
              "caveat": caveat, "self_measured": self_measured,
              "status": status, "owner": owner,
              "value_kind": _infer_value_kind(value)})


def nyc(group, key, label, lane, tier, source, reason, owner="p0_rollup"):
    add(group, key, label, None, "", lane, tier, source,
        reason, status="not_yet_computable", owner=owner)


# ───────────────────────── §3.1 EXOGENOUS ─────────────────────────
nyc("3.1_exogenous", "external_validation_events",
    "External-validation events (independent replication / external review)",
    "out_of_loop", "A", "papers/ + external-review artifacts",
    "No canonical exogenous-validation ledger exists yet. This is the "
    "ONLY Goodhart-resistant signal and per the adversary it is not even "
    "a metric — needs a tracked external_validation ledger before it can "
    "be a number. Deliberately null, not faked.")

cl = REPO / "analytics/public/ledgers/catch/catch_ledger.jsonl"
if cl.exists():
    rows = []
    for ln in cl.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if ln:
            try:
                rows.append(json.loads(ln))
            except Exception:
                pass
    if rows:
        def _is_operator(a: str) -> bool:
            a = (a or "").lower()
            return any(t in a for t in ("operator", "principal", "REDACTED_USER")) \
                and not any(t in a for t in ("agent", "claude", "codex"))
        op = sum(1 for r in rows if _is_operator(r.get("author_agent", "")))
        ag = len(rows) - op
        add("3.1_exogenous", "operator_vs_apparatus_diagnosis_ratio",
            "Operator-vs-apparatus diagnosis ratio",
            {"operator": op, "apparatus": ag,
             "operator_share": round(op / max(1, len(rows)), 3)},
            "ratio", "meta", "B",
            "analytics/public/ledgers/catch/catch_ledger.jsonl",
            "HEURISTIC on author_agent (no diagnosed_by field). The "
            "apparatus's reason to exist is to compress operator load; per "
            "goodhart_at_every_layer §3-4 spec-layer failures are ~100% "
            "operator-caught — interpret accordingly. Needs a real "
            "diagnosed_by field to be trustworthy.", self_measured=False)

# CONSUME the calibration track's stable block (owned elsewhere; P0
# only reads it — never recomputes; carry the producer's own caveats).
pcal = _load("analytics/public/forecast_pool/p0_calibration.json")
if pcal and (cfd := pcal.get("cross_family_disagreement")):
    add("3.1_exogenous", "cross_family_disagreement_rate",
        "Cross-family disagreement rate + resolution",
        {"rate": cfd.get("disagreement_rate"),
         "n_shared_contracts": cfd.get("n_shared_contracts"),
         "n_disagree": cfd.get("n_disagree"),
         "resolution_split": cfd.get("resolution_split")},
        "rate", "meta", "B",
        "analytics/public/forecast_pool/p0_calibration.json#cross_family_disagreement",
        "CONSUMED from the calibration track (Claude vs Codex; "
        f"{cfd.get('disagreement_def','')}). The genuine-independence "
        "signal — net-new, computed in their track, read-only here.",
        self_measured=False, owner="forecast_pool_track")
else:
    nyc("3.1_exogenous", "cross_family_disagreement_rate",
        "Cross-family disagreement rate + resolution", "meta", "B",
        "analytics/public/forecast_pool/p0_calibration.json",
        "CONSUMED — calibration track block not present; not recomputed.",
        owner="forecast_pool_track")

# ───────────────────────── §3.2 STATE ─────────────────────────
etr = REPO / "research_areas/EXPERIMENT_TRACK_RECORD.md"
if etr.exists():
    n_f = sum(1 for ln in etr.read_text(encoding="utf-8", errors="ignore")
              .splitlines() if ln.startswith("| E-"))
    add("3.2_state", "experiment_f_rows", "Experiment F/E rows", n_f,
        "rows", "meta", "A", "research_areas/EXPERIMENT_TRACK_RECORD.md",
        "genuine A (pure file fact); volume not quality")
papers = REPO / "papers"
if papers.exists():
    add("3.2_state", "papers", "Paper manuscripts",
        sum(1 for d in papers.iterdir()
            if d.is_dir() and not d.name.startswith(".")),
        "papers", "meta", "A", "papers/", "volume not quality")

bif = _load("analytics/public/ledgers/reflexive/bifurcation_report.json")
if bif:
    c = bif["bifurcation"]
    t = bif.get("as_of_today", {}).get("modified_last_7d", {})
    s = "analytics/public/ledgers/reflexive/bifurcation_report.json"
    add("3.2_state", "out_of_loop_share",
        "Out-of-loop share (cumulative / live-7d)",
        {"cumulative_pct": round(c["agent_work_share"] * 100),
         "live_7d_pct": round(100 * t.get("agent_work", 0) /
                              max(1, t.get("all", 1)))},
        "%", "out_of_loop", "B", s,
        "A→B (adversary): the iter** classifier changed 2026-05-16 — "
        "recomputing day-0 with today's classifier is redefinition, not "
        "recomputation. Carry the classifier-version window.")
    add("3.2_state", "iter_loop_files", "Iter-loop work files",
        c["iter_loop_artifacts"], "files", "in_loop", "B", s,
        "dormant substrate; same classifier-version caveat")
    add("3.2_state", "authored_artifacts_indexed",
        "Authored artifacts indexed", bif.get("indexed"), "files",
        "meta", "B", s,
        "A→B: mtime≈authorship broken by the May reorg for moved files; "
        "not true-A until a git-authorship-date fix lands")

leandir = REPO / "ztare_proofs" / "ZtareProofs"
if leandir.exists():
    try:
        r = subprocess.run(["grep", "-rL", "sorry", str(leandir)],
                            capture_output=True, text=True)
        n_sf = sum(1 for p in r.stdout.splitlines() if p.endswith(".lean"))
    except Exception:
        n_sf = None
    add("3.2_state", "sorry_free_lean", "Sorry-free authored .lean files",
        n_sf, "files", "meta", "C", "ztare_proofs/ZtareProofs/**",
        "A→C: NON-VACUITY NOT AUDITED. Vacuous / trivially-true sorry-free "
        "files = formal-output theatre = monotone-count laundering. The "
        "non-vacuity caveat is primary, not parenthetical.")

# ───────────────────────── §3.3 INSIGHT (self-measured) ─────────────
# Prefer the canonical (ledger-derived, full-history, rater-segregated)
# series over the sample-scoped aggregate. The sample aggregate only
# describes "this week's sample"; the recursive-gain read needs the
# full week-over-week curve. See reflexive_mining_methodology.md §5c.
tw_canonical = _load("analytics/public/queries/taste/taste_canonical_series.json")
tw_sample = _load("analytics/public/queries/taste/taste_weighted_insight.json")
tw = tw_canonical or tw_sample
tw_source = ("analytics/public/queries/taste/taste_canonical_series.json"
             if tw_canonical else
             "analytics/public/queries/taste/taste_weighted_insight.json")
if tw:
    ws = tw.get("weekly_stats", {})
    ks = sorted(ws)
    if ks:
        means = [ws[k]["mean_score"] for k in ks]
        add("3.3_insight", "contextualized_taste",
            "Contextualized taste — the PLATEAU is the headline",
            {"latest": means[-1], "min": min(means), "max": max(means),
             "weeks": len(ks), "shape": "plateau",
             "scope": tw.get("scope", "sample-scoped"),
             "rater": tw.get("rater", "")},
            "0-5", "out_of_loop", "C",
            tw_source,
            "B→C: circular (apparatus rating its own insight on an "
            "in-system rubric); the series splices pre/post-2026-05-16 "
            "rater RCA = two instruments. Report the PLATEAU, not "
            "'rising'. Needs an external/held-out human anchor to be B.")

g233 = REPO / "analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md"
if g233.exists():
    txt = g233.read_text(encoding="utf-8", errors="ignore")
    pos = len(re.findall(r"\|\s*positive\s*\|?\s*$", txt, re.M))
    sup = len(re.findall(r"\|\s*superseded-positive\s*\|?\s*$", txt, re.M))
    neg = len(re.findall(r"\|\s*negative\s*\|?\s*$", txt, re.M))
    add("3.3_insight", "gp233_decision_events",
        "GP-233 decision-change events (RAW counts, NOT a ratio)",
        {"positive": pos, "superseded_positive": sup, "negative": neg},
        "events", "meta", "C",
        "analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md",
        "B→C: NO real negative bucket + self-labeled + survivorship. The "
        "old 56:1 'ratio' was monotone-in-disguise. Show raw events only; "
        "a ratio is forbidden until a pre-committed +/-/null rubric AND "
        "an independent labeler AND a growable negative bucket exist.")

refg = _load("analytics/public/queries/reference_graph.json")
if refg:
    ws = refg.get("weekly_stats", {})
    ratios = [s.get("n_outbound_to_earlier_weeks", 0) /
              max(1, s.get("n_nodes", 1)) for s in ws.values()]
    add("3.3_insight", "compounding_ratio", "Compounding ratio (peak)",
        round(max(ratios), 2) if ratios else None, "ratio",
        "out_of_loop", "C", "analytics/public/queries/reference_graph.json",
        "B→C: node-cap (2000) makes late vs early incomparable; "
        "cross-referencing inflates it; unfalsifiable without a paired "
        "lagging outcome.")

# ───────────────────────── §3.4 RECURSIVE (self-measured) ─────────────
if cl.exists() and 'rows' in dir() and rows:
    idx = bif.get("indexed") if bif else None
    cats = sorted({r.get("category") for r in rows if r.get("category")})
    ratified = sum(1 for r in rows if r.get("ratified_at") or
                   r.get("status") == "ratified")
    add("3.4_recursive", "catch_rate_per_unit_work",
        "Catch-rate per unit work + category drift + ratified-fraction",
        {"catches": len(rows),
         "per_1k_artifacts": round(1000 * len(rows) / idx, 2) if idx else None,
         "distinct_categories": len(cats),
         "ratified_fraction": round(ratified / max(1, len(rows)), 3)},
        "rate", "meta", "B",
        "analytics/public/ledgers/catch/catch_ledger.jsonl",
        "primary recursive signal — HARDENED: false-negatives are "
        "invisible (rising rate is equally consistent with easy modes "
        "saturating while dangerous ones leak); 'new category' has the "
        "mirror 'prior blindness', no disambiguator; HARD pre/post "
        "2026-05-15 split (pre = unsound, validator dead-path-bugged); "
        "both numerator and denominator gameable. Read PAIRED with §3.1 "
        "operator-vs-apparatus or it self-congratulates.")

nyc("3.4_recursive", "time_to_catch_latency", "Time-to-catch latency",
    "meta", "B", "catch_ledger ts vs caught-artifact git date",
    "Catch ledger has ratified_at but no catch-created / "
    "artifact-introduced timestamp, and the tree is uncommitted (no git "
    "authorship dates). Not reliably computable until those exist.")

rgc = _load("analytics/public/queries/trajectory/recursive_gain_candidates.json")
if rgc:
    add("3.4_recursive", "dead_letter_rate",
        "Dead-letter rate (candidates surfaced vs ever-actioned)",
        {"surfaced": rgc.get("n_candidates"), "actioned": None},
        "rate", "meta", "B",
        "analytics/public/queries/trajectory/recursive_gain_candidates.json",
        "surfaced count is reliable; 'actioned' detection (candidate→"
        "seam/commit follow-through) needs a committed tree + a "
        "candidate→outcome link not yet wired. Honest partial.",
        status="partial")

# CONSUME GP-237 proof-health (Phase 2d) — the two adversary/Meta-Darwin
# survivors. The regression/rework rate is the non-accumulation,
# two-sided self-signal that CAN return "treadmilling" (replaces the old
# git-based not_yet_computable).
ph = _load("analytics/public/ledgers/reflexive/proof_health.json")
if ph and ph.get("status") == "ok":
    rr = ph.get("regression_rework", {})
    add("3.4_recursive", "regression_rework_rate",
        "Regression/rework rate (non-accumulation, two-sided, bad=UP)",
        {"rate": rr.get("rate"), "regressed": rr.get("regressed"),
         "prev_clean": rr.get("prev_clean"),
         "verdict": rr.get("verdict") or rr.get("status")},
        "rate", "meta", "B",
        "analytics/public/ledgers/reflexive/proof_health.json#regression_rework",
        "STRUCTURAL proxy (fingerprint-diff, not git, not a full kernel "
        "re-verify — a green decl broken by an upstream change with no "
        "local sorry is NOT caught; stated, not hidden). CAN return "
        "'treadmilling/regression' — the honest non-accumulation signal "
        "v1/v3/v4 could not. NOT a sophistication score.")
    tw = ph.get("laundering_tripwire", {})
    add("3.4_recursive", "laundering_tripwire",
        "Laundering tripwire (binary, per cycle)",
        {"introduced": tw.get("laundering_introduced"),
         "n_laundered": tw.get("n_laundered_decls"),
         "dup_fp_groups": tw.get("n_duplicate_fp_groups")},
        "bool", "meta", "B",
        "analytics/public/ledgers/reflexive/proof_health.json#laundering_tripwire",
        "F1-dogfooded (self-rejects with exit 3 if the gate is broken). "
        "Immune-system signal; conceptual triviality not detected "
        "(adversary's known limit, stated).")
elif ph and ph.get("status") == "not_computable":
    nyc("3.4_recursive", "regression_rework_rate",
        "Regression/rework rate", "meta", "B",
        "analytics/public/ledgers/reflexive/proof_health.json",
        "honest null this cycle: " + ph.get("reason", "ztare_proofs absent"))
else:
    nyc("3.4_recursive", "regression_rework_rate", "Regression / rework rate",
        "meta", "B", "proof_health.json (GP-237 Phase 2d)",
        "proof_health not yet generated this cycle.")

# Prediction/forecast metrics — all CONSUMED from the calibration
# track's stable p0_calibration block (pcal loaded in §3.1). The old
# prediction_ledger Brier (N=17/847) stays Excluded per §3.5; the
# per-period Brier below supersedes it.
if pcal:
    bpp = pcal.get("brier_per_period") or []
    if bpp:
        add("3.4_recursive", "brier_per_period",
            "Brier per period (CONSUMED; supersedes pooled N=17)",
            bpp, "brier", "meta", "B",
            "analytics/public/forecast_pool/p0_calibration.json#brier_per_period",
            "CONSUMED. Per-period with N visible — defeats the pooled-N "
            "kill. Honest limit: only 1 period (2026-W20, N=261, "
            "brier 0.16 < 0.25 baseline) — structure correct, trajectory "
            "needs multi-week accrual.", self_measured=False,
            owner="forecast_pool_track")
    rz = pcal.get("resolution")
    if rz:
        add("3.4_recursive", "prediction_resolution_rate",
            "Prediction resolution rate + latency (CONSUMED)",
            {"resolved": rz.get("resolved"),
             "total": rz.get("total_contracts"), "rate": rz.get("rate"),
             "voided": rz.get("voided"),
             "median_latency_days": rz.get("median_latency_days")},
            "rate", "meta", "C",
            "analytics/public/forecast_pool/p0_calibration.json#resolution",
            "CONSUMED. Survivorship exposed (voided + unresolved). "
            "median_latency ≈0.002d ≈ 3min reflects same-session rapid "
            "resolve, NOT a realistic forecasting horizon.",
            self_measured=False, owner="forecast_pool_track")
    ext = pcal.get("externalities")
    if ext:
        add("3.3_insight", "forecast_externalities",
            "Forecast externalities (CONSUMED — the honest calibration headline)",
            {"positive": ext.get("positive"), "negative": ext.get("negative"),
             "ratio_count": ext.get("ratio_count")},
            "ratio", "meta", "B",
            "analytics/public/forecast_pool/p0_calibration.json#externalities",
            "CONSUMED. Has a REAL negative bucket (211 pos : 95 neg "
            "distinct, ratio ~2.49) — Tier-B, the honest calibration "
            "headline ahead of GP-233 (no neg bucket) and the N=17 Brier. "
            "by_period honestly empty (externalities infra dormant this "
            "cycle — reported, not fabricated).", self_measured=False,
            owner="forecast_pool_track")

# Scientific frontier STATE — NOT a progress score (a score over
# honestly-stuck hard-math is the exact laundering the apparatus exists
# to catch). Status distribution only, NO project slugs (leak-safe).
fsd = REPO / "ztare_workspace" / "frontier_state"
if fsd.exists():
    import collections as _c
    dist = _c.Counter()
    newest = 0.0
    for fp in fsd.glob("*.json"):
        try:
            st = json.loads(fp.read_text(encoding="utf-8"))
            s = st.get("status") or st.get("state")
            if s:
                dist[str(s)] += 1
            newest = max(newest, fp.stat().st_mtime)
        except Exception:
            pass
    asof = (datetime.fromtimestamp(newest, timezone.utc).strftime("%Y-%m-%d")
            if newest else "unknown")
    add("3.2_state", "scientific_frontier_state",
        "Scientific frontier STATE (per-project status distribution)",
        dict(dist), "projects", "out_of_loop", "C",
        "ztare_workspace/frontier_state/*.json (status only, no slugs)",
        f"NOT a progress score (a score over honestly-stuck hard-math is "
        f"laundering). State only. STALE: newest file {asof}; daemon-"
        f"written and the VPS workers were not run this cycle. The "
        f"hard-math frontier is stuck per the terminal characterizations "
        f"(NS strict-margin atom open, gravity portability unearned, "
        f"neural law failed) — a flat/stuck distribution IS the honest "
        f"signal.", self_measured=False, status="partial")

roi = _load("analytics/public/queries/reflexive_primitive_roi.json")
if roi:
    bv = roi.get("by_verdict", {})
    add("3.4_recursive", "capability_engaged_count",
        "Capability engaged-count (weak observability only)",
        {"engaged": bv.get("engagement_high") or bv.get("engaged"),
         "dead": bv.get("dead"),
         "insufficient": bv.get("insufficient_data")},
        "count", "meta", "C",
        "analytics/public/queries/reflexive_primitive_roi.json",
        "bounded 28-day project-scope ROI artifact; primitives are mostly "
        "stable (operator) — observability ONLY, NO churn-as-gain framing.")

# ───────────────────────── EMIT ─────────────────────────
payload = {
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "spec": "research_areas/private/seams/apparatus/instrumentation/GP-236_p0_metrics_rollup_seam.md",
    "page_caveat": "Every metric except group 3.1_exogenous is "
                   "self-produced, self-labeled, self-ratified by the "
                   "apparatus it measures. A self-measured metrics page is "
                   "itself the Goodhart layer; only external review "
                   "catches spec-layer self-deception. No self-measured "
                   "metric is a standalone headline.",
    "group_order": ["3.1_exogenous", "3.2_state", "3.3_insight",
                    "3.4_recursive"],
    "status_counts": {
        s: sum(1 for m in M if m["status"] == s)
        for s in ("ok", "partial", "not_yet_computable")},
    "metrics": M,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=2))
print(f"wrote {len(M)} P0 metrics → {OUT.relative_to(REPO)}")
print(f"status: {payload['status_counts']}")

# ───────────────────────── HISTORY (append-only) ─────────────────────────
# One row per cycle, holding numeric headline values only. Lets the
# dashboard render week-over-week sparklines next to each scalar metric
# without re-walking every source ledger. Append-only: never rewrite
# prior rows (the recursive-gain claim's audit trail).
def _sparkable(metrics: list[dict]) -> dict:
    out: dict = {}
    for m in metrics:
        v = m["value"]
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[m["key"]] = v
        elif isinstance(v, dict):
            # Extract one obvious headline subfield from a breakdown so
            # the most interesting series (e.g. contextualized_taste.latest)
            # is still sparkable.
            for cand in ("latest", "rate", "mean_score", "mean", "share",
                         "operator_share", "ratio_count"):
                if cand in v and isinstance(v[cand], (int, float)) \
                        and not isinstance(v[cand], bool):
                    out[f"{m['key']}.{cand}"] = v[cand]
                    break
    return out

history_row = {
    "generated_utc": payload["generated_utc"],
    "values": _sparkable(M),
}
HISTORY.parent.mkdir(parents=True, exist_ok=True)
with HISTORY.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(history_row) + "\n")
print(f"appended history row → {HISTORY.relative_to(REPO)}  "
      f"({len(history_row['values'])} sparkable values)")
for m in M:
    v = m["value"] if m["status"] == "ok" else f"[{m['status']}]"
    print(f"  [{m['tier']}|{m['lane']:11}|{m['group']}] {m['label']}: {v}")
