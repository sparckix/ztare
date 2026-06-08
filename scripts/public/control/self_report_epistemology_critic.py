#!/usr/bin/env python3
"""Reflexive capability #3 — self-report epistemology critic.

Turns the GP-166 substrate noise-profile critic INWARD on the apparatus's own
self-reported metric series. The substrate critic refuses to trust a fit until it
measures heteroscedasticity / autocorrelation / non-Gaussianity / errors-in-X;
this points the SAME critic at ZTARE's own ledgers and asks, per series:

  is this self-reported number statistically trustworthy, or is it momentum /
  drift / a noisy rater dressed up as independent signal?

This is the mechanical answer to the "self-reported everything, observer bias
built into the measurement" critique: a deterministic flag, not a protestation.

Series tested (only those that EXIST as a series — a missing series is itself a
reported finding, not silently skipped):
  - catch ledger: daily ratified-catch counts (autocorrelation ⇒ clustering /
    momentum, NOT independent catches)
  - trajectory archive: per-iteration champion score (non-i.i.d. ⇒ the
    rater/judge drifts; a "score went up" claim inherits that drift)
  - reflexive p0 metrics: insight-density etc. — REPORTED MISSING if <2 snapshots

Exogenous carrier: the statistical properties of the series are objective; the
apparatus cannot narrate its way past a Durbin-Watson statistic.
"""
from __future__ import annotations
import json, sys
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "src"))
from ztare.diagnostics.noise_profile import classify_noise_profile

CATCH = REPO / "analytics/public/ledgers/catch/catch_ledger.jsonl"
P0HIST = REPO / "analytics/public/ledgers/reflexive/p0_metrics_history.jsonl"
TRAJ = REPO / "analytics/public/ledgers/trajectory/trajectory_archive.jsonl"


def _rows(p):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def _day(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
    except Exception:
        return None


def catch_series():
    rows = _rows(CATCH)
    days = [_day(r.get("ratified_at")) for r in rows if r.get("ratified_at")]
    days = [d for d in days if d]
    if not days:
        return None, "no ratified_at timestamps"
    lo, hi = min(days), max(days)
    span = (hi - lo).days + 1
    counts = Counter(days)
    # daily count series over the active window
    series = [({"x": i}, float(counts.get(lo.__class__.fromordinal(lo.toordinal() + i), 0)))
              for i in range(span)]
    return series, f"{len(rows)} catches over {span} days ({lo}→{hi})"


def traj_series(max_n=2000):
    rows = _rows(TRAJ)
    ys = [r.get("score") for r in rows if isinstance(r.get("score"), (int, float))]
    ys = ys[:max_n]
    if len(ys) < 20:
        return None, f"only {len(ys)} scored iterations"
    return [({"x": i}, float(y)) for i, y in enumerate(ys)], f"{len(ys)} scored iterations"


def report_series(name, series, desc):
    print(f"\n{'='*70}\n{name}\n  {desc}\n{'='*70}")
    if series is None:
        print(f"  ⚠ NO SERIES — {desc}. Trustworthiness UNVALIDATABLE; any trend "
              f"claim on this metric rests on too-few points.")
        return None
    prof = classify_noise_profile(series, primary_feature_key="x")
    print("  verdict:", prof.summary() if hasattr(prof, "summary") else prof)
    flags = []
    if getattr(prof, "needs_correlated", False): flags.append("AUTOCORRELATED (momentum/clustering, not independent)")
    if getattr(prof, "needs_weighted", False): flags.append("HETEROSCEDASTIC (variance regime-changes)")
    if getattr(prof, "needs_robust", False) or getattr(prof, "non_gaussian", False): flags.append("NON-GAUSSIAN residuals")
    if getattr(prof, "needs_errors_in_x", False): flags.append("ERRORS-IN-X (the predictor itself is noisy)")
    if flags:
        print("  ⚠ SELF-REPORT NOT i.i.d.:")
        for f in flags:
            print(f"      - {f}")
        print("  ⇒ treat aggregate counts/trends on this series as suspect; report with this caveat.")
    else:
        print("  ✓ i.i.d.-Gaussian OK — aggregate stats on this series are defensible.")
    return prof


def main():
    print("#"*70 + "\n# SELF-REPORT EPISTEMOLOGY CRITIC (GP-166 turned inward)\n" + "#"*70)
    cs, cd = catch_series(); report_series("CATCH LEDGER (daily ratified-catch count)", cs, cd)
    ts, td = traj_series(); report_series("TRAJECTORY (per-iteration champion score)", ts, td)
    p0 = _rows(P0HIST)
    report_series("REFLEXIVE P0 METRICS (insight-density etc.)", None if len(p0) < 2 else "exists",
                  f"{len(p0)} snapshot(s) in p0_metrics_history.jsonl")
    print(f"\n{'#'*70}\n# Done. A non-i.i.d. flag means the self-reported number carries a\n"
          f"# statistical pathology the apparatus must disclose, not assert past.\n{'#'*70}")


if __name__ == "__main__":
    main()
