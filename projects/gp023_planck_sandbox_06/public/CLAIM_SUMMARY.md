# GP-023 Planck Sandbox 06 — Public Claim Summary

> **What this file is.** The public-evidence surface for a sealed sandbox
> whose full working directory is private. This summary is the canonical
> public artifact cited by the corresponding entry in
> [`docs/public_claim_register.md`](../../../docs/public_claim_register.md)
> under *Vocabulary-Escape Calibration (Planck Sandbox)*. The working
> directory at `projects/gp023_planck_sandbox_06/` is gitignored; the
> SHA-256-fingerprinted file manifest below makes the underlying artifacts
> citable without exposing them.

## One-line claim

Under the sealed nine-gate decomposed apparatus, a general-purpose LLM
mutator converged from a naive monotonic power-law seed onto an
operator-authored non-elementary transcendental ground-truth functional
form — the Bose-Einstein geometric-series occupancy shape — in ≤10
iterations, with all nine deterministic gates passing at machine precision.

## What was tested

The mutator was given visible evidence for a two-variable curve `I(φ, ψ)`
under cold variable names, with no domain labels, and asked to recover a
parsimonious closed-form model that passes a charter-committed gate
battery: hidden global residual, peak-location at three ψ values,
high-φ decay ratio, farther-tail global residual at the same three ψ
values, and three terminal-value residuals.

The operator-authored ground truth (the mutator was not shown this) is:

```
I(φ, ψ) = A · φ^p / (exp((γ·φ/ψ)^q) − 1) + offset
```

with `A = 0.95, p = 2.30, γ = 0.72, q = 1.30, offset = 0.06`. This is the
Planck / Bose-Einstein geometric-series occupancy shape, not in the
mutator's typical regression-toolbox repertoire.

## Recovered form

The mutator recovered the exact functional form with all five parameters
matched to machine precision.

## Gate verdicts

From the frozen `latest_eval_results.json`,
`score_contract.deterministic_charter_gates.results`:

| Gate | Threshold | Actual |
|---|---|---|
| `hidden_global_residual` | 0.05 | 5.95e-06 |
| `hidden_peak_location_psi_0_60` | 0.15 | 0.0 |
| `hidden_peak_location_psi_1_00` | 0.15 | 0.0 |
| `hidden_peak_location_psi_1_80` | 0.15 | 0.0 |
| `hidden_high_phi_decay_ratio` | 0.1 | 5.4e-05 |
| `farther_tail_global_residual` | 0.01 | 3.27e-06 |
| `farther_tail_terminal_value_psi_0_60` | 0.005 | 7.22e-07 |
| `farther_tail_terminal_value_psi_1_00` | 0.005 | 7.22e-07 |
| `farther_tail_terminal_value_psi_1_80` | 0.005 | 7.22e-07 |

Criterion score: 100/100 on the latest iteration; final apparatus-internal
score 83 (capped by a meta-judge soft-cap on narrative grounding of
"microscopic branching angles" inside the thesis prose — flagged
`quarantine_legitimate: false` by the eval itself). **The cap is
judge-layer, not apparatus-layer**: the apparatus cleared at machine
precision and the judge soft-capped on narrative-grounding grounds the
apparatus did not require.

## Honest framing — what this is, and what it is not

This is **vocabulary-escape recovery of an operator-committed
non-elementary target under a sealed apparatus**. The cage was strong
enough to force the mutator out of its regression-toolbox prior onto a
Planck shape. That is a **calibration result**, not a discovery claim.

It is *not* a demonstration of open-ended scientific discovery. The
ground-truth functional form and coefficients were authored by the
operator in `raw/generate_curve_v3.py` (SHA-256 fingerprinted below)
**before** the mutator ran. The mutator solved a very difficult
curve-fitting problem under extreme external constraint and recovered the
exact hidden form; it did not derive a physical law from first principles
against an unknown target.

The result proves the cage is strong enough to force vocabulary escape
**when the operator knows the answer**. It does *not* prove the cage is
strong enough to force convergence on a correct form when the operator
does not.

## Retest tag and caveat

*Successor-run partial demotion (axis-specific).* Sandbox_06 is the
calibration baseline. Successor sandboxes on the *eml-only vocabulary
axis* (sandbox_07, sandbox_08) closed at score 0 under the standard
vocabulary — establishing that the convergence does not trivially
generalize when the mutator's vocabulary is restricted. Sandbox_08
post-mortem identified a feature-bag completeness gap (the mutator
systematically avoided nesting a power operator inside `eml(...)` across
12 failed candidates). Sandbox_09 was scaffolded as a clean blind re-run
on the eml-only axis with a live negative-space extractor. Sandbox_09 v2
and sandbox_10 confirmed the continuous-residual unfalsifiability
finding (INS-011) twice.

The frozen sandbox_06 result itself stands, with the explicit caveat that
its successor-axis runs have not reproduced the convergence under
restricted vocabularies.

## File manifest with SHA-256 fingerprints (sealed 2026-04-14)

These are the underlying artifacts. They are part of the private working
directory; the SHA-256 fingerprints make the result citable and
verifiable for any reader who is granted local access.

| File | SHA-256 | Purpose |
|---|---|---|
| `latest_eval_results.json` | `d1047b4e864519e63231d21ce6956ace1f8e7d387d77c105250d049d463b6fbf` | Latest-iteration eval (score 83, criterion 100, all gates pass, recovered form in `probability_dag.nodes[N3]`) |
| `champion_eval_results.json` | `d34d623ab14750270cddc0e989dae305363a47d9a762de3b14758f64ecb339e4` | Champion eval (score 83, criterion 86, criterion 7 fail on Weibull mention, all gates pass) |
| `project_charter.md` | `796f20ec3e0b0e536bb8d477fbab66203a0fc36d3fe49ed53be59fc9d61cdd84` | Nine gates + asymptotic contract + farther-tail contract, committed pre-run |
| `raw/generate_curve_v3.py` | `8983d0192b7d445370d89d7df28dfc9d16516ad50e67d98a68878382dc340a77` | v3 reparameterized generator (γ = α/β collapse fix); contains `_self_check_equivalence_to_v1` equivalence assertion |
| `thesis.md` | `9e9a55b4b380873c8094fce5712df70fa131442cea0201b866650bde11ac423d` | Final thesis at closure (best_iteration tagged 1776201692_iter9_score_83) |
| `test_model.py` | `8b7f281cc82c761a227af9ee9e5987aff0a0d2c4b57b66c03fb2058334c7f100` | Final closed-form model at closure |
| `GP-023_sandbox06_identifiability_hardening_seam.md` | `39e39d4a80d6458234f1e19e52d9e63a419e7ef78efb1833a37d1e55c35fc44a` | Hardening seam R1–R6 that governed the run |

Regime fingerprint: `b9d8adf10ff4c4f8`
Evidence fingerprint: `5c42891df802828d`
Rubric fingerprint: `08a9b0a8d51c1d7b`

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Vocabulary-Escape Calibration (Planck Sandbox)*.
- Working directory (private):
  `projects/gp023_planck_sandbox_06/_frozen_reference/`.
- Successor runs:
  `projects/gp023_planck_sandbox_07/` through `_10/` (all private).
- Next falsifier: promote vocabulary-escape recovery from sandbox_06
  (operator-authored target) to a blinded-oracle successor (unknown
  target, operator-oracle coupling removed). The H-SP2-04 thread.
