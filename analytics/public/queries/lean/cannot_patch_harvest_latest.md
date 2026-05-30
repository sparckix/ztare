# Missing Primitives Backlog

Aggregated from CANNOT-PATCH diagnoses across all apparatus runs.
Generated: 2026-05-06T23:43:22.949956

## Summary
- total CANNOT-PATCH events: 7
- by category: {'missing_inequality': 3, 'missing_constructor': 4}

## Most-mentioned named objects (likely missing primitives)

- **generated_quartic_survival_projection** — referenced in 5 CANNOT-PATCH events
- **below_wall_profit_cap** — referenced in 4 CANNOT-PATCH events
- **QuarticSurvivalProjectionReceipt** — referenced in 3 CANNOT-PATCH events
- **TrackBProfileLipschitzControlObligation** — referenced in 3 CANNOT-PATCH events
- **threshold_defect_of_family_no_arbitrage** — referenced in 2 CANNOT-PATCH events
- **quartic_survival_projection_of_lipschitz_bridge** — referenced in 1 CANNOT-PATCH events
- **above_wall_defect_profit_cap** — referenced in 1 CANNOT-PATCH events
- **generated_quartic_survival_projection_of_amplitude_receipts** — referenced in 1 CANNOT-PATCH events
- **TrackBProfileDecompositionObligation** — referenced in 1 CANNOT-PATCH events

## Targets with CANNOT-PATCH events

- TrackBProfileLipschitzControlObligation: 4
- TrackBProfileDecompositionObligation: 1
- TrackBProfileDecompositionObligation_threshold_defect_of_family_no_arbitrage_source: 1
- TrackBProfileLipschitzControlObligation_generated_quartic_survival_projection_source: 1

## Diagnoses by category

### missing_inequality (3)

- **TrackBProfileLipschitzControlObligation::generated_quartic_survival_projection** (source_provenance_bridge, failure_log)
  > The requested `SOURCE PROVENANCE BRIDGE` patch class expects a theorem demonstrating an inequality bound (`≤`) between two numerical fields of a parent structure. However, the target field `generated_quartic_survival_projection` is of type `∀ (U : NSEvolution) (n : ℕ), QuarticSurvivalProjectionRecei
  named: generated_quartic_survival_projection, below_wall_profit_cap

- **TrackBProfileDecompositionObligation::threshold_defect_of_family_no_arbitrage** (source_provenance_bridge, failure_log)
  > The required SOURCE PROVENANCE BRIDGE patch class mandates producing an inequality theorem of the form `s.threshold_defect_of_family_no_arbitrage ≤ s.<bound_field>`. However, the target field `threshold_defect_of_family_no_arbitrage` is a logical implication (a dependent function type returning the 
  named: threshold_defect_of_family_no_arbitrage

- **TrackBProfileDecompositionObligation_threshold_defect_of_family_no_arbitrage_source::provenance** (bridge, analytics/queries/typed_endpoint_runs/Tr)
  > The required SOURCE PROVENANCE BRIDGE patch class mandates producing an inequality theorem of the form `s.threshold_defect_of_family_no_arbitrage ≤ s.<bound_field>`. However, the target field `threshold_defect_of_family_no_arbitrage` is a logical implication (a dependent function type returning the 
  named: threshold_defect_of_family_no_arbitrage, TrackBProfileDecompositionObligation

### missing_constructor (4)

- **TrackBProfileLipschitzControlObligation::generated_quartic_survival_projection** (instance_with_evidence, failure_log)
  > The resolved set lacks a construction of `QuarticSurvivalProjectionReceipt` (such as `quartic_survival_projection_of_lipschitz_bridge` or any other domain-specific lemma returning this receipt). Without an available constructor or the underlying analytic inequalities needed to manually build the str
  named: QuarticSurvivalProjectionReceipt, quartic_survival_projection_of_lipschitz_bridge, below_wall_profit_cap, above_wall_defect_profit_cap, generated_quartic_survival_projection

- **TrackBProfileLipschitzControlObligation::generated_quartic_survival_projection** (instance_with_evidence, failure_log)
  > To fulfill the `generated_quartic_survival_projection` field of `TrackBProfileLipschitzControlObligation`, we must construct a `QuarticSurvivalProjectionReceipt` for the corresponding ledger block. However, the resolved set lacks any constructor or theorem that produces this receipt. Specifically, w
  named: generated_quartic_survival_projection, TrackBProfileLipschitzControlObligation, QuarticSurvivalProjectionReceipt, below_wall_profit_cap

- **TrackBProfileLipschitzControlObligation::generated_quartic_survival_projection** (instance_with_evidence, failure_log)
  > The target structure `TrackBProfileLipschitzControlObligation` is missing from the resolved type constructors. While the target field `generated_quartic_survival_projection` is known and we have constructors to produce its type (`generated_quartic_survival_projection_of_amplitude_receipts`), the obl
  named: TrackBProfileLipschitzControlObligation, generated_quartic_survival_projection, generated_quartic_survival_projection_of_amplitude_receipts

- **TrackBProfileLipschitzControlObligation_generated_quartic_survival_projection_source::provenance** (bridge, analytics/queries/typed_endpoint_runs/Tr)
  > The requested `SOURCE PROVENANCE BRIDGE` patch class expects a theorem demonstrating an inequality bound (`≤`) between two numerical fields of a parent structure. However, the target field `generated_quartic_survival_projection` is of type `∀ (U : NSEvolution) (n : ℕ), QuarticSurvivalProjectionRecei
  named: generated_quartic_survival_projection, below_wall_profit_cap, TrackBProfileLipschitzControlObligation, QuarticSurvivalProjectionReceipt

---

## Codex action: missing-primitive backlog

For each high-frequency named object, decide:
- `add_to_spine` — write the missing constructor/lemma in Lean
- `import_from_mathlib` — exists in mathlib, just needs import
- `wrong_diagnosis` — apparatus misread the gap
- `out_of_scope` — closure doesn't actually need this