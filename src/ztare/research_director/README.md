# `ztare.research_director`

Research Director (RD) reasoning surface. Separate from the ZTARE
mutator loop: the mutator proposes and compresses; the RD runs phase
scripts, records execution, and audits.

## What lives here

Roughly grouped:

| Concern | Modules |
|---|---|
| **Action contracts + tick discipline** | `pattern_action_contract`, `orchestration_contract_gate`, `orchestration_shadow_log`, `boundary_card_gate`, `boundary_card_repair_trace`, `primitive_operator_cards`, `primitive_tick_surface`, `phase_runner`, `pattern_bank_injector` |
| **Adversarial generation** | `adversarial_packet_generator`, `hostile_packet_suite`, `eigenquestion_generator`, `cognitive_gym_hooks` |
| **PDE / formal-method substrates** | `pde_currency_ledger`, `pde_estimate_craft_ops`, `pde_work_unit_gate`, `formalization_sequence`, `single_spend_carrier_audit`, `receipt_strength_audit`, `ns_l3a_workmap`, `meta_arc_acceptance`, `meta_arc_matcher` |
| **Discipline rails** | `scientific_amnesia`, `mathlib_semantic`, `pde_estimate_workbench`, `retirement_detector`, `prediction_logging_discriminator`, `gap_typing`, `residual_normal_form` |
| **Substrate routing** | `substrate_portfolio`, `substrate_recommender`, `semantic_feature_normalizer`, `structural_fingerprint`, `problem_solving_ops` |
| **Branch grids** | `branch_grids/` subpackage |


## Current Contract Gates

- `orchestration_contract_gate`: validates compact orchestration contracts before an RD executes them. It checks class/action/program-counter invariants, outside-handoff rules, deterministic lowering, and source-cue anchoring. Current evidence: H44.
- `orchestration_shadow_log`: validates/appends non-blocking shadow events for orchestration-menu decisions. Current evidence: H47/H50. Use it to collect drift/refusal/outcome data; do not use it as an enforcement gate.
- `boundary_card_gate`: validates paid/unpaid boundary cards before downstream action. It checks boundary state, required receipts, action order, terminal action, blocked broad claim, and source anchoring. Current evidence: H45. It is card-shape/action validation, not a full semantic verifier.
- `boundary_card_repair_trace`: validates/appends rejected-card repair-loop traces. Current evidence: H52. Use it to measure repair after gate rejection; do not treat it as broad auto-execution approval.
- `pde_work_unit_gate`: validates PDE execution payloads. It blocks premature terminal gaps and, for constructive-turn states, requires a positive constructor attempt before more obstruction-only continuation unless an explicit tested blocker exists. Current evidence: H46.

## Boundaries

- Reads from `research_areas/`, `analytics/public/queries/`, `org/`.
- Writes to `analytics/public/queries/rd/`,
  `analytics/public/ledgers/prediction/`, and the live tick state under
  the orchestrator's control.
- Does not own proof-value credit: the Governance Gate
  (`scripts/public/control/leanmill/governance_worker.py`) is the only
  ratifier. RD generates work and records audit; it does not promote.

## Spec

`research_areas/seams/engine/meta/GP-219_pde_estimate_craft_sister_vocabulary.md`
covers the PDE-side surface (seam only; no separate spec). `research_areas/seams/engine/GP-225_*` is
the LeanMill-side surface that consumes RD outputs.
