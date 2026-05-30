# Treatise Internal Review, Pre-Registration Spec

## Status

Draft, updated 2026-04-13 16:42:50 EDT; pre-registered and awaiting dry-run and seal

`legacy_combined`, pre-2026-04-13 combined artifact: retains a `## Debate Log` in-file. Per `research_areas/kernel/ztare_spec_format.md` (Migration Rule), older combined files may remain marked `legacy_combined`; the debate is split out only if this item is reopened for implementation.

## Scope

- defines the sealed experimental object for running the treatise `research_areas/[redacted]` through the autoresearch loop as an internal adversarial review
- fixes the attack surface (pair collapse, principle derivation, residual decomposition, scope-commitment honesty, self-reference integrity) before any run executes
- fixes the rubric (`rubrics/treatise_rule0_self_pass.json`) and the baseline falsification suite (`projects/treatise_rule0_self_pass/test_model.py`) before any run executes
- declares how a finding downgrades the treatise and how the project concludes

Does not cover:

- the GP-049 cross-system annotation study, which is a separate validation surface on historical iteration artifacts and runs on different objects
- quantitative claims about the treatise (throughput, automation ratio, cost), which the treatise explicitly defers
- the companion paper `papers/paper4/draft.md`, which has its own validation track
- promotion of the treatise to any external-circulation state; promotion is contingent on both this internal review and the GP-049 cross-system annotation study

## Decision

Adopt a sealed internal-review project that runs the treatise as a thesis object against a bespoke rubric and a pre-registered Boolean discriminator suite. The project is conceptually independent of GP-049: this spec tests whether the treatise as a single artifact withstands the apparatus it describes; the GP-049 cross-system annotation study tests whether the ten-operation / seven-principle decomposition is stable and distinguishable when annotated on historical artifacts. Both are necessary for external circulation; neither is sufficient.

The project seals before any run. Seal means: the thesis, project charter, evidence packet, rubric, and baseline test suite are all written, the test suite passes at baseline, the attack surface is declared, and the pass/fail semantics of each decisive variable are pre-registered. No edits to the rubric or to the baseline suite are permitted after seal except as responses to findings produced by the run itself.

## Problem

The treatise claims that epistemic verification decomposes into approximately ten named operations plus three residual commitments, under seven structural principles. A treatise that makes this claim and has never itself been run through the apparatus it describes risks the Chapter 1.3 Pattern 5 ("Defining Yourself Into Victory") pathology it warns against. This internal review is the corresponding self-application check. It is not optional for a self-referential claim about epistemic verification.

The failure mode this project most needs to catch is that the treatise's Front Matter scope commitments (qualitative not quantitative, single-system extraction, version zero, not obsolescing judgment) could be honest scope narrowings or pre-emptive gaming moves that foreclose criticism. The attacking process is specifically tasked with testing whether the treatise holds up mainly because of those narrowings (gaming) or whether the narrowings are honest statements of scope.

## Sealed Objects

The following artifacts are sealed before the run executes and may not be modified mid-run:

- `projects/treatise_rule0_self_pass/thesis.md`, the decisive claim, named discriminator (operation-by-operation distinction), secondary discriminator (principle independence), tertiary discriminator (residual irreducibility), and logic DAG
- `projects/treatise_rule0_self_pass/project_charter.md`, core question, three decisive sub-claims, kill criteria, scope-commitment-honesty anchor
- `projects/treatise_rule0_self_pass/evidence.txt`, internal corpus pointers to the treatise, the three-legs philosophy doc, the epistemic-supervision-principles doc, Paper 4, and the GP-049 seam
- `rubrics/treatise_rule0_self_pass.json`, bespoke rubric with philosopher-of-science persona hostile to pre-emptive scope narrowing and self-referential exemptions; five criteria summing to 100 points (operation distinction 30, principle independence 25, residual irreducibility 20, scope commitment honesty 15, self-reference integrity 10); bonus penalties for empirical-observable chasing (−20) and surface critique (−15); localized-weakness bonus (+10)
- `projects/treatise_rule0_self_pass/test_model.py`, pre-registered Boolean discriminator suite encoding the four decisive variables (`pair_collapse_count`, `principle_derivation_count`, `residual_decomposition_count`, `scope_commitment_honest`) as Python assertions that pass at baseline and fail only when the attacker produces concrete evidence for a specific collapse, derivation, decomposition, or scope-gaming finding

## Pre-Registered Decisive Variables

The suite encodes four variables. Each has an explicit pass condition and an explicit fail condition. Pass conditions are the baseline state. Fail conditions are declared before the run and may only flip when the attacker produces concrete named evidence.

| Variable | Pass | Fail | Evidence required to flip |
|---|---|---|---|
| `pair_collapse_count` | 0 | ≥1 | A named pair in the ten-operation list with a concrete case where the two operations are demonstrably the same move under different labels |
| `principle_derivation_count` | 0 | ≥1 | A derivation showing that a principle in the seven-principle list is entailed by a strict subset of the remaining six, using the apparatus the treatise describes |
| `residual_decomposition_count` | 0 | ≥1 | A structured input/output format proposal that makes one of the three residual commitments apparatus-performable without losing the commitment-not-operation property |
| `scope_commitment_honest` | `True` | `False` | A demonstration that the treatise only holds up because of a specific Front Matter narrowing and would fail attack if that narrowing were removed without the claim changing |

## Run Configuration

- project: `treatise_rule0_self_pass`
- rubric: `treatise_rule0_self_pass`
- falsification_mode: defaults to `numerical_proof` (no `falsification_mode` field set in the rubric, so the loader takes the safe legacy path)
- iterations: 3 (initial dry-run scope; extend only if findings warrant)
- mutator: `claude-opus`, substituted for Gemini due to sustained Gemini 503 outage (observed from ~08:00 EDT 2026-04-13, also blocking sandbox_04). The self-reference concern (Claude attacking a Claude-authored treatise) is accepted as a known limitation. The v4 hardened deterministic gates are the decisive anti-gaming layer; the LLM judge is the scoring surface, not the falsification surface. This is a fresh project with no prior Claude iterations, so there is no within-run continuation bias.
- judge: `claude-opus`, same rationale

## Kill Criteria

- if the attacking process produces a clean pairwise collapse of any two of the ten operations within the iteration window, the decomposition count is wrong and Chapter 1.2 must be rewritten before the project continues
- if the attacking process produces a derivation of any principle from the others within the iteration window, Chapter 2 is over-specified and must be reduced
- if the attacking process further decomposes any residual commitment, Chapter 3 is premature and must be rewritten
- if the attacking process demonstrates that a Front Matter scope commitment is decisive mainly as a shield against criticism rather than as an honest scope boundary, the treatise has committed the Pattern 5 pathology it warns against and must be rewritten with the scope commitments separated from the main argument
- if the attacking process cannot produce any counterexample across the full iteration window, the project does *not* conclude "the treatise is correct", it concludes "the apparatus failed to find a counterexample in the current window" and the operator decides whether to extend the window or declare the check complete

## Out of Scope

- quantitative claims about the treatise (throughput, cost, automation ratio, comparative efficiency)
- the distributional question (who benefits from the decomposition)
- the Taylor-moment framing claim (Conclusion), which is motivation rather than decisive inference
- any edit to the treatise itself except in response to a finding produced by this run

## Open Questions

- whether `numerical_proof` is the right falsification mode for a structural thesis, or whether the loader should be extended with a dedicated structural-discriminator mode, deferred, since the baseline suite is a valid `numerical_proof` artifact under the current loader contract
- whether the 3-iteration window is sufficient for this internal review where the attacker has access to the full treatise, the operator may extend after reviewing the first run

## References

- `research_areas/[redacted]`, the thesis under test
- `research_areas/[redacted]`, parent seam; Turn 7 authorizes this project, Turn 8 corrects earlier over-binding, Turn 9 records the corrections and clears the internal review run
- `research_areas/[redacted]`, internal philosophy doc aligned with the treatise's Chapter 2
- `docs/concepts/epistemic_principles.md`, external principles doc cross-referenced by Chapters 1.3 and 3.4
- `papers/paper4/draft.md` §3.2, §5.4, §5.7, companion paper sections the treatise depends on

## Debate Log

- 2026-04-13 19:35:04 UTC, pre-registered by Claude after Gemini review of the initial draft packet flagged (a) missing baseline `test_model.py`, (b) missing sealed pre-reg object, (c) timestamp/state hygiene, and (d) evidence packet drift from the revised treatise. All four findings folded into this spec and into the companion artifacts in the same pass.
- 2026-04-13 16:42:50 EDT, wording aligned to the revised treatise: less internal shorthand, less emphasis on "self-pass" terminology, and plainer description of the cross-system burden.
