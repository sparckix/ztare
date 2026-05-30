# GP-216 OOD Mining and Residual Feedback Spec

## Status

Active — opened 2026-05-14

## Seam

- `research_areas/seams/engine/meta/GP-216_theory_building_operations_seam.md`
- `research_areas/seams/engine/meta/GP-219_pde_estimate_craft_sister_vocabulary.md`

## Decision

Keep the open problem and paper-facing uncertainty in seams. Use this spec as
the runnable protocol once the work touches multiple domains, multiple agents,
and downstream consumers.

Concretely:

- GP-216 seam records the theory-builder / problem-solver / v5 language problem;
- GP-219 seam records the PDE estimate-craft residual and NS-specific examples;
- this spec governs OOD mining, calibrating-agent procedure, residual feedback
  schema, and promotion criteria.

If this protocol changes a paper claim, gate, or reusable vocabulary, update the
relevant seam with the result. If a seam discovers a new recurring consumer
failure mode, update this spec before treating the rule as reusable.

## Problem

The current GP-216 evidence is strong enough to motivate a paper, but not strong
enough to justify universal-language rhetoric. The risky failure mode is mixing
three different questions:

- does v5 recognize recurring structural research moves?
- does v5 cover OOD domains outside mathematics and business?
- does a recognized move have a crisp enough contract to mechanize?

Those questions need different evidence channels. Without a protocol, agents can
inflate coverage by force-fitting residuals, promote domain nouns as operations,
or treat a vocabulary hit as research progress. This spec separates recognition,
residual logging, vocabulary extension, and gate promotion.

## Scope

This spec governs the method for extending GP-216 v5 beyond its current math + business evidence base and for logging consumer residuals when the language is used in research work.

In scope:

- OOD corpus selection across multiple MECE domains;
- blind move enumeration before exposure to v5;
- cross-walk tagging against frozen v5 plus optional sister vocabularies;
- multiple calibrating model families;
- residual clustering and anti-rename attack;
- consumer residual feedback schema;
- promotion criteria for new operations, sister vocabularies, and deterministic gates.

Out of scope:

- claiming a complete universal ontology;
- changing `VOCABULARY_V5` during an active OOD campaign;
- treating a language hit as proof progress;
- using consumer residual logs as publication-grade evidence without audit.

## Eigenquestion

Can GP-216 v5 act as a portable structural-research language across non-math OOD domains, while preserving a disciplined residual channel for moves it does not cover?

## Current Evidence Boundary

Established evidence:

- math: strong cross-subfield evidence from 8-subfield mining;
- business: small positive OOD control, 6 arcs, 57.9% shared-plus-broadly coverage;
- sparse 2026 specialist math papers: 75.2% shared-plus-broadly coverage;
- PDE/analysis: v5 alone is incomplete; v5 + GP-219 performs better, and Candidate G remains an extension candidate.
- PDE/analysis consumer use can expose post-campaign residuals; such residuals
  may update GP-219 only when they name a mechanism that cannot be represented
  by an existing op without losing the next action. These updates are
  operational until the next frozen OOD campaign revalidates them.

Not yet established:

- medicine/clinical;
- biology/life science;
- materials/physical systems;
- legal/institutional systems;
- engineered systems outside ZTARE's own apparatus.

## MECE OOD Domain Grid

Domains are partitioned by primary object of inquiry:

| Domain family | Object | Evidence role |
|---|---|---|
| `formal_systems` | proofs, programs, formal languages | calibration |
| `physical_systems` | materials, chemistry, climate, physics | OOD test |
| `living_systems` | genes, cells, organisms, ecology | OOD test |
| `clinical_systems` | patients, trials, endpoints, interventions | OOD test |
| `engineered_systems` | software, robots, chips, infrastructure | OOD test |
| `institutional_systems` | law, policy, markets, governance | OOD test |

Business remains an OOD positive control under `institutional_systems / organizational`.

## Mining Methodology

### Phase 0 — Freeze

Before a campaign begins:

- freeze comparator: `src/ztare/research_director/universal_research_ops.py::VOCABULARY_V5`;
- freeze sister vocabularies visible to taggers, e.g. GP-219 for PDE/analysis only;
- record source manifest and source URLs;
- record model/agent roster and budgets.

No op may be added or renamed mid-campaign.

Outside a frozen campaign, a consumer-residual update to a sister vocabulary
must update the relevant seam, the Python registry, and generated structural
language catalog. If the update is only a substrate label or example, do not add
a new op; put it in the substrate profile or artifact.

### Phase 1 — Source Acquisition

For each OOD domain:

- choose 4-6 arcs;
- prefer primary papers, trial reports, datasets, standards, or court/regulatory sources;
- include at least one recent/post-cutoff arc when possible;
- record why each arc is structurally diagnostic.

Output:

- `ood_source_manifest.json`

Source-scout gate:

- if the source scout returns `kill_switch_reason_if_any`, do not proceed to
  cross-walk until the named protocol gap is resolved;
- source-scout kill switches create methods debt, not negative coverage
  evidence;
- if enumeration has already run, keep it as a smoke artifact but do not score
  it.

### Phase 2 — Blind Move Enumeration

Enumerators must not see the v5 vocabulary. They receive only:

- source metadata;
- short source context or permitted excerpts;
- instruction to extract 10-20 natural-language research moves per arc.

Required move fields:

- `arc`
- `name`
- `signature`
- `anchor`
- `blind_enumerator`
- `unit_admissibility`: optional but recommended, one of
  `research_generation_move`, `execution_step`, `source_inference`, `unclear`

Output:

- `raw_moves_<domain>_<agent>.json`

### Phase 3 — Cross-Walk Tagging

Taggers see frozen v5 and the raw moves.

Required tag fields:

- `primary_op`: one of `core_*`, `broad_*`, `spec_*`, or `null`;
- `op_tags`: list, multiple tags allowed;
- `residual_label`: required if no `core_*` or `broad_*` tag applies;
- `confidence`: `high | medium | low`;
- `why_not_existing_op`: required for residuals.

Use at least two calibrating models:

- one Codex CLI run;
- one Claude Code CLI run.

Add a third family or human/domain expert for any paper-facing claim.

This explicit multi-rater/adversarial harness is a new 2026-05-14 hardening
layer for the OOD extension campaign. Do not retroactively describe the
original GP-216 evidence as having used this protocol; the older result had
saved outputs, controls, and some adversarial checks, but not the rater-stance
aggregation defined here.

Recommended rater stances:

- `strict`: prefer residual/null unless the mechanism is explicitly present;
- `permissive`: allow domain-vocabulary translation when mechanism is clear;
- `adversarial`: try to kill every fit as rename/domain noun/outcome label;
- `neutral`: literal rubric application.

Runtime bound:

- default CLI timeout: 10 minutes per role/arc/rater;
- every rater output must include a compact `checkpoints` array with stage,
  completed items, unresolved items, and kill-switch reason if the task should
  be stopped or rerun smaller;
- because current `claude -p` and `codex exec` runs do not provide a stable
  mid-run structured checkpoint file, live inspection is by process runtime and
  post-run stdout/stderr artifacts until a streaming runner is added.

Output:

- `crosswalk_<domain>_<agent>.json`
- scored summary via `score_gp216_ood_manual.py`
- disagreement-preserving aggregate via `gp216_ood_aggregate_raters.py`

### Phase 4 — Residual Clustering

Cluster only residual moves. Clusters must be mechanism-level, not domain-jargon labels.

A residual cluster is eligible for anti-rename only if:

- it has at least 3 instances;
- it appears in at least 2 arcs;
- it changes interpretation or next action;
- it cannot be represented by a v5 op without losing decision-relevant content.

### Phase 5 — Anti-Rename Attack

Every residual candidate must survive an attack asking:

- Is this just a narrower instance of an existing v5 op?
- Is this a domain noun attached to an existing move?
- Is this an outcome type, not an operation?
- Is this a methodological stance, not a move?
- Would adding it improve held-out coverage or only explain this corpus?

If a candidate fails, record the existing op it aliases to and do not promote.

### Phase 6 — Held-Out Validation

Promote only after held-out validation:

- same-domain held-out arcs;
- one cross-domain stress corpus;
- independent model/human audit for publication claims.

### Phase 7 — Reviewer Adjudication

Reviewer adjudication is required before any OOD result is summarized in the
paper or used to propose vocabulary changes.

A priori reviewer packet:

- frozen source manifest;
- frozen v5 summary and any admitted sister vocabularies;
- blind enumerator output;
- all cross-walk rater outputs;
- disagreement-preserving aggregate;
- this reviewer procedure.

Reviewer constraints:

- the reviewer may not create a new operation;
- the reviewer may not rename an existing operation;
- the reviewer may not edit rater outputs;
- the reviewer may only assign adjudication labels, cluster residuals, and
  decide whether a residual enters quarantine/watchlist;
- if the reviewer needs a new category to make sense of the data, the output is
  `reviewer_protocol_gap`, not a promoted op.

Adjudication labels are assigned move-by-move:

| Label | A priori rule | Paper treatment |
|---|---|---|
| `clean_hit` | all raters mark v5-covered and agree on primary op | may count as clean coverage |
| `covered_with_partial_residual` | all raters mark v5-covered, but at least one rater records an uncovered residual dimension | count as covered only with residual caveat; add/update ledger if repeated |
| `covered_boundary_dispute` | all raters mark v5-covered but disagree on primary op | count separately; evidence of transfer plus boundary ambiguity |
| `residual_dispute` | at least one rater marks v5-covered and at least one marks residual/null | adjudication required; not clean coverage |
| `confirmed_residual` | all raters mark residual/null, or residual labels are mechanism-equivalent after spelling normalization | residual watchlist; no promotion yet |
| `invalid_or_source_gap` | move is not a research operation, source context is too thin, or anchor is unsupported | exclude from denominator with reason |
| `reviewer_protocol_gap` | reviewer cannot classify without inventing a new rule | update spec before using result |

Decision hierarchy:

- a single adversarial residual vote does not veto coverage, but it forces
  `residual_dispute`;
- a single permissive coverage vote does not rescue a residual, but it prevents
  `confirmed_residual`;
- a covered primary op with a non-empty residual label is not a clean hit;
- op-choice disagreement among covered votes is not residual evidence by itself;
- source insufficiency beats all semantic labels.

Unit admissibility rule:

- routine execution steps should not become vocabulary gaps;
- if a unit is mainly assay execution, manufacturing, monitoring, dosing, or
  follow-up, classify as `invalid_or_source_gap` unless the reviewer can state
  the research-generation move being made;
- metadata-inferred moves may be used for smoke tests, but paper-grade scoring
  requires source support from primary excerpts or equivalent artifacts.

Domain-specific reviewer preconditions:

- legal/institutional arcs involving precedent, admissibility, or authority
  require an authority-move adjudication note before cross-walk;
- otherwise v5 may misclassify legitimate legal authority operations as weak
  evidence, or overfit them as generic constraint propagation.

Reviewer output must include:

- per-move adjudication label;
- one-sentence rationale;
- whether the move stays in the coverage numerator;
- whether the move enters residual quarantine;
- candidate residual cluster name, if any;
- exact evidence pointers to rater outputs.

### Phase 8 — Residual Ledger Update

Every `confirmed_residual` and every repeated `residual_dispute` must be logged
to the residual ledger before it is used in discussion.

Active campaign ledger:

- `workingpapers/epistemic-generation/evidence/gp216_residual_ledger.jsonl`

Ledger placement rule:

- working-paper/OOD campaign residuals live in the working paper evidence
  bundle while validation is exploratory;
- residuals that become general apparatus vocabulary candidates should be
  promoted to a public `research_areas/` registry with an E/F-row pointer;
- specs define schema and promotion rules, not the full growing ledger.

Required ledger fields:

```json
{
  "residual_id": "stable slug",
  "status": "watchlist | repeated | promotion_candidate | rejected_alias | promoted",
  "first_seen_date": "YYYY-MM-DD",
  "domain_family": "clinical_systems",
  "candidate_cluster": "short mechanism label",
  "aliases": ["surface label variants"],
  "mechanism_hypothesis": "what operation may be missing",
  "nearest_existing_ops": ["core_06"],
  "anti_rename_status": "untested | disputed | survived_one_probe | failed_alias | survived_heldout",
  "instances": [
    {
      "arc": "arc_id",
      "move_key": "move name",
      "adjudication_label": "residual_dispute",
      "evidence_pointer": "aggregate path"
    }
  ],
  "decision_value": "why this changed or may change action",
  "promotion_blockers": ["needs >=3 instances", "needs >=2 arcs"],
  "next_match_rule": "what future raters should look for"
}
```

Future matching rule:

- exact label match is insufficient;
- match by mechanism hypothesis plus failure of nearest existing ops;
- if a future residual uses new domain nouns but has the same mechanism, append
  it to the existing residual ID rather than creating a new ID;
- if it only matches by domain noun, create no ledger entry.

## Consumer Residual Feedback Schema

Every GP-216/GP-219 fingerprint or gate report that influences a typed research action should emit or preserve:

```json
{
  "residual_class": "none_closed | theorem_or_domain_gap | gate_contract_not_crisp | vocabulary_gap | new_channel_or_residual_measure_needed | apparatus_or_source_mismatch",
  "residual_summary": "specific obstruction left after language/gate pass",
  "did_language_change_next_action": true,
  "evidence_pointer": "gate report, F-row, source packet, Lean declaration, forecast contract",
  "next_lever": "math | apparatus | vocabulary | source_audit | human_review",
  "consumer_context": "where the language was used",
  "candidate_extension": null
}
```

This schema is canonical. The GP-219 seam's consumer residual note is the PDE-specific example, not the general contract.

Domain-specific aliases are allowed only at the edge. For example,
`theorem_or_pde_gap` in GP-219 is the PDE/NS alias of canonical
`theorem_or_domain_gap`. Aggregators and paper evidence should normalize the
alias back to `theorem_or_domain_gap`.

## Promotion Criteria

| Candidate | Minimum evidence | Destination |
|---|---|---|
| existing v5 op applies | cross-walk agreement | no new op; cite existing op |
| wording broadening | repeated low-friction aliasing; no new gate needed | edit op definition with evidence note |
| sister-vocabulary op | residual cluster, anti-rename pass, held-out support | domain sister vocabulary registry |
| deterministic gate | sister/v5 op plus crisp pass/fail contract and field-test value | `src/ztare/gates/` |

Consumer-residual extensions are allowed as operational proto-ops when they
change the next action and pass nearest-op comparison, but they remain
paper-provisional until revalidated under the frozen campaign protocol above.
| paper claim | saved-output verification plus methods, baselines, and independent audit | working paper / public paper |

## Coverage Semantics

Coverage is a diagnostic, not an optimization target.

Do not add operations to maximize coverage. A higher coverage score can be worse
evidence if it comes from force-fitting or vocabulary inflation. Report at
least four numbers:

- unanimous v5 coverage;
- majority v5 coverage;
- residual-any rate;
- adjudication-needed rate.

A residual becomes a promotion candidate only when it survives the residual
clustering and anti-rename tests above. Until then, residuals remain in a
watchlist/quarantine state.

Recommended adjudication labels:

- `clean_hit`: raters agree on v5 coverage and primary op;
- `covered_boundary_dispute`: raters agree covered, but disagree on op;
- `residual_dispute`: at least one rater marks residual and at least one marks covered;
- `confirmed_residual`: raters agree no existing v5 op fits;
- `invalid_or_source_gap`: input was too thin, source was wrong, or move was not a research operation.

## Logging Discipline

Consumer residual logs are not optional if the language changes action.

Log to the nearest artifact:

- NS/PDE: gate report and GP-233/F-row closure;
- OOD campaign: cross-walk result JSON and residual cluster file;
- paper work: `workingpapers/epistemic-generation/evidence/`;
- code consumers: report JSON field named `consumer_residual_feedback`.

## Failure Modes

- **Vocabulary laundering:** force-fitting residuals into v5 to inflate coverage.
- **Rename inflation:** promoting domain-specific nouns as new operations.
- **Model-mediated self-confirmation:** enumerator and tagger share model family or prompt context.
- **Consensus laundering:** averaging multiple raters into one score while hiding which moves had strict/adversarial disagreement.
- **Gate overreach:** turning fuzzy recognition into deterministic enforcement.
- **Publication overclaim:** using "universal" without the tested-domain qualifier.

## Current Implementation Pointers

- Campaign protocol: `workingpapers/epistemic-generation/ood_extension_campaign.md`
- Source queue: `workingpapers/epistemic-generation/ood_source_manifest.json`
- Manual scoring: `workingpapers/epistemic-generation/evidence/reproducers/score_gp216_ood_manual.py`
- Structural fingerprint: `src/ztare/research_director/structural_fingerprint.py`
- NS gate consumer: `scripts/public/projects/ns/ns_gate_check.py`
