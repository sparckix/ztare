# Review — AxiomPack (theory-induction program)

Scope: ~26,000 focus LOC in full (axiom_pack core 16,642; theory layer 9,221) + frontier_campaign_runner.py (9,873 lines; +1,420-line uncommitted hunk reviewed in structure, ~700 read), theory_ir canonicalization, all live receipts under analytics/public/. Two claims verified by execution.

## 1. Correctness

**Independence witnesses: genuinely certificate-backed — the strongest part of the system.** `certify_axiom_independence` (finite_model.py:1161) finds a finite model of base+others refuting the target; `_verify_independence_receipts` (finite_model.py:1691-1758) replays the witness semantically (background must hold, target must fail) — not hash checks. The SMT lane (finite_table_model_finder.py:583-589) host-replays every Z3 witness and raises on mismatch; Z3 never trusted raw. **Live tamper test: flipping one witness table cell is caught at three layers.** A finite countermodel is a valid non-implication witness at any size — no false-independence class here.

**Ratification: enforced fail-closed in the library, unreachable in practice.** `promote_axiom_pack` (axiom_pack.py:491) and `verify_ratification_receipt` (axiom_authority.py:690) require in-process replay of all finite witnesses, signed shadow-yield receipt, signed base-theory resolution, kernel-checked conditional Lean lowering with `contains_global_axiom == False` (axiom_lowering.py:129-195), role-separated signing keys. But **the verify half is wired while both evidence producers are cold**: `evaluate_shadow_ab` (axiom_yield.py) and `certify_conditional_lowering` (axiom_lowering.py:25) have zero production callers. No pack can ratify without out-of-band tooling — and none ever has.

**Cheap-filter screen structurally unable to certify its own demo domains.** `run_semantic_cheap_filters` (axiom_pack.py:579-609) uses the enumerative certifier at carrier size exactly 2 (`DEFAULT_CHEAP_FILTER_POLICY` semantic_min/max = 2, axiom_pack.py:45-53); the `max_finite_carrier_size: 5`/`7` knobs (axiom_pack.py:46, 1379) are **dead config — nothing reads them**. The priority-lattice pilot's own separations (distributive vs modular) need 5-element models (M3/N5); enumerative search at size 3 for that signature is ~1e11 interpretations. **Verified live: the pilot fails its own screen (1/4 independence witnesses, `stress ok: False`).** The SMT finder that could reach size 5 exists but is not routed into the pack screen.

**"Langlands" morphism layer: bookkeeping, not transport.** `propose_landscape_transport` (theory_landscape_morphism.py:91-138) maps each fingerprint component to itself with transform `"anonymous_structural_match"` and emits preservation obligations that are all `"pending"` — permanently; nothing discharges them. `test_compiled_landscape_mapping` (:141-160) accepts a caller-supplied boolean callable as the "target test". No signature-to-signature interpretation (sorts/ops → terms, axiom translation, obligation discharge) exists anywhere in the codebase. Zero production callers, zero run receipts. `theory_interpretation.py` is live but is provenance/literature binding (`advisory_pending_destination_replay`), the transportable constraint being prose fed to the LLM isomorphism engine — string-level, not certificate-backed. The only real cross-structure machinery: `classify_single_operation_equivalence` (finite_model.py:557) — an exact bounded relation ladder (isomorphism/coordinate/parastrophe/term-reduct) with honestly declared per-finite-algebra-pair scope.

**Dedup/triviality gates:** sound where they exist. IR identity alpha-invariant with eq-side sorting (theory_ir.py:539-553); conjecture_book dedups via the proof-cache normalizer; nontriviality requires carrier > 1; the sieve tracks vacuous candidates (`no_premise_model_at_fixed_size`) separately from refuted.

## 2. End-to-end liveness — two disjoint systems share the name "AxiomPack"

- **axiom_pack.py contract lane (quarantine → stress → ratify → promote): COLD.** One live eval ever (~2026-07-09), produced under an older schema — its cheap receipts lack `leanmill.axiom_pack_semantic_dimension.v1`; its downstream_yield status (`shadow_replay_only`) no longer exists in the code; today's validator would reject them. **Promoted packs: 0. Proposals: 2 quarantined cached-fixture packs + 3 codex candidates from the one live eval.** Every `promotion_status` in analytics/public is `"quarantined"` (17 occurrences). The "axiom_pack lane audit" (control_plane_audit.py:394-466) is a **token-presence grep over files, not an execution audit** — the dead-instrument class.
- **Frontier campaign "axiompack" lane (cli.py `campaign`, frontier_campaign_runner.py): LIVE and fresh.** Compound-implication sieve wired with budget ledger + conflict-ledger clause learning (frontier_campaign_runner.py:4029-4075); governed Lean consequence at :6581. Receipts: 88 solver attempts, 20 Lean closure certs, **18 kernel-ratified AxiomPack-derived theorems** through 2026-07-16T02:56Z. But the RD tick (TICK670, 2026-07-10) was retired unclosed (`pre_lifecycle_bypass_debt`), both forecast contracts never resolved, and conjecture_book.jsonl has **zero** AxiomPack entries.
- **Morphism transport: zero receipts ever.**

Live at the theorem level, dead at the pack-promotion level, nonexistent at the transport level.

## 3. Novelty verdict (from mechanics)

Not currently a Langlands program — no functorial transport with proof obligations. What the mechanics genuinely add over standard equational ATP / Knuth-Bendix / Mace4-style conjecturing:

1. **Batch CEGIS with witness amortization and information pricing** (compound_implication_sieve.py): one countermodel evaluated against the entire surviving implication pool; query selection is a target-family bandit on realized elimination yield; every elimination becomes a learned conflict clause.
2. **Kernel-checked premise attribution** (lean_consequence_bridge.py:234-271): identical proof bytes replayed under full/empty/leave-one-out premise arms; "proved_attributed" requires the negatives to fail. Certifies that a consequence actually *depends on* the pack — the claim conjecturing systems normally assert, here mechanized. **The genuinely novel seam.**
3. **Receipted residual-interest pricing** (theory_interest.py): a consequence scores only after subtracting what receipted cheap baselines already reach. Semantic, not string-similarity.
4. **Zero-trust certificate discipline throughout**: every solver output host-replayed; every receipt content-hashed and replayable.

**Missing to sharpen the novelty:** the transport glue is unbuilt, not the capability. A checked interpretation (source ops → target terms, axiom translation) could discharge obligations with tools that already exist — `certify_implication`/SMT finder for finite obligations, the consequence bridge for Lean-level ones. theory_landscape_morphism.py as-is should be deleted or rebuilt on that seam.

## 4. Key findings

Crash/wedge bugs in the LIVE lane (uncommitted diff introduces the first):
- **theory_navigator.py:1435 + :439-472** — new rejection reason `theory_program_boundary_target_not_residual` matches no branch in `_receipted_reject_all`; a later `reject_all` (:1725) or budget exhaustion (:1892) raises uncaught ValueError, killing the navigation wave instead of the receipted no-candidate outcome.
- **theory_lineage_synthesis.py:130** — reads `formula_id` from rows carrying `prediction_formula_id` (theory_interest.py:649); "unresolved" never decays → `proceed_boundary` stays available after review; the leaf can loop on already-reviewed boundaries.
- **theory_navigator.py:292-341** — evidence-currency gate only checks receipts named in `evidence_refs`; a leaf citing only non-selection receipts bypasses the superseded-baseline check silently.
- **explore_axiom_space.py:2237** — `theory_task_requested` accepted and passed (frontier_campaign_runner.py:9572) but never read in `_boundary_completion_covers`: a completion built while the theory-task executor was unavailable is returned as final later when the executor exists.
- **explore_axiom_space.py:2560/2654** — supersession archiver raises on archive/root mismatch before retry logic; conflicting keying schemes (:2725 boundary-digest vs :2543 completion-digest) can hard-livelock a directory.
- **exploration_budget.py:1084-1096** — roll-forward carve-out reads base caps while surrounding admission math uses extension-aware snapshots; a `resources_extended` grant is invisible to the carve-out.

Trust/receipt weaknesses:
- **axiom_yield.py:414-509** — `verify_candidate_dependency_receipt` replays only receipt *shape*; the `compiled` bits behind "indispensable axiom" are caller-asserted (moot while the producer is cold; the soft link the day it's wired).
- **generative_representation.py:260-267** — read-path roundtrip validation copies the payload's own contract string into `expected`: self-attested.
- **axiom_pack.py:1668-1670** — a live isomorphism run with zero candidates silently falls back to cached fixture templates (they fail lint, but the receipt looks live).
- **equational_baseline.py:861** — shallow-lane saturation lost when later lanes exhaust; a target can be priced as residual when the baseline was inconclusive.

Domain leakage / dead code:
- **contracts/axiom_pack_transport.py:174-181** — generically named `AxiomPackTransportContract` hardcodes band words (`mul`, sort `B`); non-band reuse silently decodes into band axioms.
- **theory_ir.py:1107-1112** — anonymization scrubs `"relation"` keys but relation formulas serialize as `{"kind":"rel","name":...}`; relation names leak into the "anonymous" leaf profile (latent).
- **Dead:** theory_landscape_morphism.py (all), `certify_conditional_lowering`, `evaluate_shadow_ab`, `compare_independent_theory_programs` (theory_program.py:282), two equational_baseline wrappers (:790, :864), the `max_finite_carrier_size`/`filter_budget_k` knobs.

Diff quality: disciplined (hash-verified state recovery; a genuine binder-surface fix in lean_consequence_bridge.py:157-166 so solver proof bytes replay; v5 temporal literature-coverage gate) but introduces the navigator crash and the evidence-gate bypass, and grows frontier_campaign_runner.py to 9.8k lines — the same monolith class as the solver_core backlog.

## Top 3 remediations

1. **Close the produce/verify split or delete the contract.** Wire `certify_conditional_lowering` + `evaluate_shadow_ab` into the live campaign lane so a pack can actually reach ratification — or retire axiom_pack.py's promotion machinery and move the gate to the campaign lane that already kernel-ratifies theorems. Replace the control_plane_audit string-grep with an execution receipt check.
2. **Fix the two live-lane loop breakers before the next wave:** the `_receipted_reject_all` ValueError (theory_navigator.py:439-472) and the `prediction_formula_id` key mismatch (theory_lineage_synthesis.py:130).
3. **Make transport real at the existing seams:** route pack independence screening through the SMT finder (making the size-5/7 knobs live so the demo domains can certify), and replace theory_landscape_morphism with one checked signature interpretation whose obligations are discharged by `certify_implication` + the consequence bridge — that single piece of glue turns "Langlands-style" from aspiration into the system's actual differentiator, because the obligation dischargers already exist and are sound.
