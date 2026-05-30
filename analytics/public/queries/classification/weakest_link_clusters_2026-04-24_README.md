# Weakest-Link Failure Taxonomy (2026-04-24)

Generated from 2608 iteration records across 128 projects.

Methodology: keyword-taxonomy with prioritized regex rules (see script docstring).

---

## Other / Unclustered (`other_unclustered`)

**Size:** 1258 iterations across 114 projects.

Iterations whose weakest_point text did not match any of the defined failure-family regex patterns. These may represent novel failure modes not yet captured in the taxonomy, or weakest_point strings that use unusual phrasing for a known failure family.

**Top keywords:** thesis, log, model, data, fit, law, non, finite, evidence, observed

## Harness / Test-Suite Defect (`harness_defect`)

**Size:** 302 iterations across 44 projects.

Iterations where the Level-3 falsification test suite itself failed to execute correctly -- runtime exceptions, assertion failures, timeouts, or crashes in the harness rather than substantive thesis weaknesses. These are infrastructure failures, not epistemic ones: the judge could not evaluate the thesis because the test machinery broke. Fixing harness defects is a prerequisite, not a scientific improvement.

**Top keywords:** thesis, falsification, level, suite, assertion, model, disproved, fail_assert, failure, unit

## Catastrophic / Load-Bearing Assumption (`catastrophic_assumption`)

**Size:** 245 iterations across 72 projects.

Iterations where the judge identified a single catastrophic or load-bearing assumption that the entire thesis rests on. If that assumption is wrong, the thesis collapses entirely. These are structural single-points-of-failure in the argument architecture.

**Top keywords:** assumption, catastrophic, thesis, data, law, log, observed, fit, model, finite

## Unverified Bound / Unproven Claim (`unverified_bound`)

**Size:** 155 iterations across 60 projects.

Iterations where a critical bound, derivation step, or quantitative claim was asserted without formal proof or constructive derivation. The judge identified a load-bearing assumption that the mutator treated as given but never justified.

**Top keywords:** unproven, thesis, assumption, claim, without, catastrophic, class, law, physical, data

## Tail / Extrapolation / Far-Field Generalization Failure (`tail_generalization`)

**Size:** 145 iterations across 31 projects.

Iterations where the thesis failed to generalize to the far tail of the data distribution -- good fits on observed/training data but catastrophic failure beyond the fitted range. The judge identified that asymptotic, large-n, or large-parameter behavior was assumed rather than derived, making extrapolation unreliable. This is the dominant failure mode in numerical-law-discovery tasks.

**Top keywords:** tail, farther, exponential, data, thesis, model, observed, form, catastrophic, assumption

## Null Weakest Point (`null_weakest_point`)

**Size:** 143 iterations across 50 projects.

Iterations where the weakest_point field was null or empty in the enriched archive. These are typically early-stage iterations where the judge output could not be parsed, or harness-level failures that prevented judge evaluation entirely.

**Top keywords:** 

## Exhaustiveness / Completeness Over-Claim (`exhaustiveness_claim`)

**Size:** 121 iterations across 31 projects.

Iterations where the thesis claimed completeness or exhaustiveness without providing a coverage proof. The mutator asserted 'all cases are handled' or 'every relevant scenario is addressed' but the judge found no argument that the enumeration is actually exhaustive.

**Top keywords:** completeness, thesis, claim, bound, exhaustive, assumption, guarantee, audit, catastrophic, class

## Circularity / Tautology / Self-Reference (`circularity`)

**Size:** 98 iterations across 28 projects.

Iterations where the thesis was flagged for circular reasoning, tautological structure, or hard self-reference -- the conclusion presupposes the premise, or the derivation assumes the result it claims to prove. Includes iterations where the structured semantic-gate derivation classified the proof as 'hard self-reference.' This is a structural logic error that requires architectural restructuring of the argument.

**Top keywords:** self, proof, derivation, reference, thesis, gate, hard, structured, semantic, classified

## Causal / Identification Assumption (`causal_assumption`)

**Size:** 44 iterations across 10 projects.

Iterations where a causal or identification assumption was flagged as unproven -- the thesis inferred causation from correlation, ignored confounders, relied on an untestable identification strategy, or failed to bound its counterfactual claims.

**Top keywords:** thesis, causal, norm, tech, claim, assumes, without, data, evidence, weight

## No Thesis / Placeholder Submission (`no_thesis_proposed`)

**Size:** 39 iterations across 28 projects.

Iterations where no actual thesis was submitted -- the mutator produced a placeholder, an 'intentionally wrong' baseline, or explicitly stated 'no model proposed yet.' These represent the cold-start phase before the mutator has enough signal to construct a substantive proposal.

**Top keywords:** thesis, placeholder, model, there, attempt, law, submission, theorem, proposal, proposed

## Over-Claim of Generalization (`generalization_overclaim`)

**Size:** 22 iterations across 14 projects.

Iterations where the thesis claimed broader applicability than the evidence supports -- out-of-sample collapse, inability to generalize beyond the training distribution, or single-dataset conclusions presented as universal.

**Top keywords:** finite, thesis, exponential, log, catastrophic, overclaim, overclaims, data, marginal, observed

## Model Class / Functional Form Restriction (`model_class_restriction`)

**Size:** 14 iterations across 10 projects.

Iterations where the thesis restricted itself to a specific functional form or model class without justifying why alternatives were excluded. The judge flagged that closed-form analytic expressions, single-logarithmic forms, or restricted algebraic compositions may misrepresent the underlying phenomenon.

**Top keywords:** analytic, form, catastrophic, assumption, smooth, thesis, integer, structure, irregular, evidence

## Finite-Data Inference / Unjustified Extrapolation (`finite_data_extrapolation`)

**Size:** 9 iterations across 7 projects.

Iterations where the thesis extrapolated from finite, limited, or localized data to make global or universal claims without theoretical grounding. The judge flagged that the fitted or observed data window is insufficient to support the scope of the conclusion.

**Top keywords:** finite, data, cannot, global, thesis, catastrophic, exponential, assumption, uniquely, structure

## Numerical Instability / Precision Issue (`numerical_instability`)

**Size:** 6 iterations across 5 projects.

Iterations where numerical precision, floating-point artifacts, or convergence failures were identified as the weakest link. The mathematical claim may be correct in theory but the computational implementation is unreliable.

**Top keywords:** numerical, system, analogy, log, error, ill, contamination, fitting, true, conditioned

## Fit Parameter / Over-Interpretation of Numerical Artifact (`fit_parameter_overclaim`)

**Size:** 4 iterations across 4 projects.

Iterations where the thesis over-interpreted a fitted parameter value, ratio, or delta -- treating a numerical coincidence or empirical artifact as evidence for a structural claim without deriving why that specific value is expected from the model.

**Top keywords:** log, tail, catastrophic, interpretation, rational, evidence, overinterpretation, algebraic, term, fit

## Incomplete Valuation / Quantification Gap (`valuation_incomplete`)

**Size:** 2 iterations across 2 projects.

Iterations where the thesis was structurally incomplete in its quantification -- key claims were made without explicit numerical benchmarks, bounds, or targets, leaving the argument unanchored.

**Top keywords:** exceptions, assumes, isolated, boundary, prime, powers, accidental, rather, potentially, essential

## Data Validity / Source Reliability Issue (`data_validity`)

**Size:** 1 iterations across 1 projects.

Iterations where the judge identified concerns about data source reliability, aggregation bias, ecological fallacy, or mismatched geographic/temporal granularity in the evidence supporting the thesis.

**Top keywords:** level, protocol, thesis, pivotal, reliance, regional, msa, occupational, wage, medians

