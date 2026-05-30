# Pattern bank — catastrophic_fit_failure

**Class:** `catastrophic_fit_failure`
**Source:** `analytics/queries/weakest_link_llm_subclasses_2026-05-04.json` (May 4 LLM classifier; mini-ztare-aligned redaction)
**Mining N (raw):** 6 records from 1 project (single-classifier; used as the seed bank entry pending broader recurrence)
**Cross-LLM stability (GP-149 §10 audit):** 0.538 three-way (highest among all classes; still below 0.60 GP-151 threshold)

## Mechanism

A candidate is in this class when the proposed law / theorem packet / test_model produces output that *fails to match the evidence at all* — not "fits poorly," but reproduces zero of the supplied data points. The pathology is structural: the candidate is analytically equivalent to a model that the evidence already falsifies (e.g. `f(n) = 0` while all evidence is positive; `2 × d(n)` while no row matches that). The judge does not need to compute fit metrics; the falsification is decisive on inspection.

## Why this matters at runtime

A mutator producing `catastrophic_fit_failure` is not iterating productively. It is shipping candidates that the next-judge call must reject by inspection. Each iteration in this regime costs the same as a real iteration but contributes only "this exact wrong direction is also wrong" — information already implied by the evidence.

## Killer question for the mutator (operator-injected when this pattern bank entry is active)

> Before submitting this candidate, simulate the candidate on the supplied evidence's first three rows. If every simulated value disagrees with the evidence — by sign, by magnitude, or by parity — STOP. The candidate is in `catastrophic_fit_failure` regime; no rubric weighting will rescue it. Restate the candidate so that at least the first row agrees, OR concede the candidate is wrong and request a CATEGORY_SWITCH primitive in the next iteration's grammar.

## Redacted exemplars

These are real critic verdicts from the May 4 mining run, redacted (project IDs and evidence specifics scrubbed; structure preserved).

1. The model produces `f(n) = 0` for all `n`, while every output in the evidence is a strictly positive integer between two-digit ranges. The exact-fit count is zero. The candidate is falsified by the first row of evidence.

2. The candidate's output is universally incorrect: zero observed matches to evidence. The judge does not need to score; the candidate is rejected by inspection.

3. The candidate's law is analytically equivalent to `2 × <named function>`, which matches zero of the supplied data points. It is falsified immediately and decisively. The candidate's grammar choice is not the bottleneck; the law is wrong by inspection.

## What an operator should do when injecting this entry

- Set `inject_pattern_bank: { class: "catastrophic_fit_failure", source: "analytics/queries/pattern_bank_redacted/" }` in the rubric.
- The autoresearch loop will append this file's content (minus this header) to the mutator's grounding payload, alongside the existing anti-pattern catalog if `inject_antipattern_catalog` is also set.
- The override log entry (`analytics/operator_overrides.jsonl`) records when the injection fired, on which iteration.
- After the run, compare apparent failure rate of `catastrophic_fit_failure` on iterations with vs. without injection. The Mode B experiment (per `GP-214_pattern_bank_kernel_injection_seam.md` §B) is the formal A/B.

## What this entry is NOT

- A guarantee the class label is correct on a given iteration. Cross-LLM stability is 0.538 — providers disagree on the boundaries of this class. Manual operator review of the runtime classifier's verdict is recommended before declaring a real failure.
- A complete enumeration of catastrophic_fit_failure cases. The 6 records are seeds; the bank entry refreshes on every mining run.
- A substitute for the rubric. The bank entry adds *exemplar grounding* on top of the rubric; it does not replace the rubric.
