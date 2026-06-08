---
id: RP-004
name: self_report_epistemology_critic
version: 1
status: active
leg_applied: "Invert + Adversarial Disagreement"
target: "The apparatus's own self-reported metric series (catch ledger, trajectory scores, reflexive p0 metrics)"
verdict: "B (PARTIALLY NOVEL)"
literature_scout: "novel SHAPE (a substrate data-epistemology critic pointed inward on the engine's own ledgers, not at a research substrate); cite-and-adopt components: the in-repo GP-166 noise-profile critic (src/ztare/diagnostics/noise_profile.py), Durbin-Watson autocorrelation, Breusch-Pagan heteroscedasticity."
dependencies:
  - scripts/public/control/self_report_epistemology_critic.py
  - src/ztare/diagnostics/noise_profile.py
  - analytics/public/ledgers/catch/catch_ledger.jsonl
  - analytics/public/ledgers/trajectory/trajectory_archive.jsonl
  - analytics/public/ledgers/reflexive/p0_metrics_history.jsonl
falsifier:
  test: "Positive+negative control on synthetic series: (a) on a synthetic i.i.d.-Gaussian series the critic MUST return i.i.d.-OK (no false alarm); (b) on a synthetic autocorrelated (AR(1), phi=0.6) series it MUST flag AUTOCORRELATED. If either control fails, the critic is miscalibrated and is demoted until fixed."
  monitoring_artifact: "analytics/public/ledgers/reflexive/self_report_critic_control.json (monthly positive+negative control run)"
  period: "2026-05-31 .. ongoing (monthly)"
anti_laundering_commitments:
  - "The critic flags statistical pathologies; it NEVER emits a 'trust score'. It can mark a self-number untrustworthy; it cannot bless one as trustworthy."
  - "A clean (i.i.d.) verdict means only 'no detected pathology at this N', not 'the claim is true'."
  - "If the positive/negative synthetic control fails, append a catch-ledger row of kind false_novelty_claim and set this primitive's status to demoted; do not silently delete."
---

# RP-004 — Self-Report Epistemology Critic

## What It Is

The GP-166 substrate noise-profile critic — which refuses to trust a substrate
fit until it measures the residual's statistics — turned **inward** on the
apparatus's own self-reported metric series. Per series it flags
autocorrelation (momentum), heteroscedasticity (regime change), non-Gaussianity,
and errors-in-X (a noisy rater), so a self-reported number that is statistically
untrustworthy is **disclosed, not asserted past**. The exogenous carrier is the
series' own Durbin-Watson / Breusch-Pagan statistic — the apparatus cannot
narrate its way around it.

## Why This Is Reflexive

It applies the engine's own data-epistemology gate to the engine's own
measurement output. It is the mechanical answer to "self-reported everything,
observer bias in the measurement": a deterministic flag, not a protestation.

## First-run findings (2026-05-31)

- Per-iteration champion-score series (n=2000): **non-i.i.d.** (autocorrelated +
  non-Gaussian) ⇒ aggregate "score improved" claims carry momentum/drift.
- Catch ledger: 147 ratified catches concentrated in an **11-day window** ⇒
  "triple-digit catches" is a batch-ratification artifact, not a sustained rate.
- Reflexive p0 metrics: **1 snapshot** ⇒ "recursive gain plateaued" is
  unvalidatable as a series.

These are now disclosed in `docs/public_claim_register.md`.

## Self-reference verification

`grep SELF-REPORT-EPISTEMOLOGY-CRITIC analytics/public/index/architecture_index.jsonl`
returns this primitive's row.
