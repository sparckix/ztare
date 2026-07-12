"""Canonical prompt templates shared across LeanMill control-plane surfaces.

Proof-solver-only prompts remain in ``ztare.leanmill.solver.prompts``. Prompts
used by AxiomPack, campaign compilation, adapter synthesis, or other LeanMill
subsystems live here so those layers do not import the solver package.
"""
from __future__ import annotations


AXIOM_PACK_TYPED_PROPOSER_PROMPT = (
    "Return only JSON with a non-empty `typed_axiom_proposals` array. Each row has "
    "exactly `source_conjecture` and `typed_axiom_proposal`; the latter has a typed "
    "`axiom`, non-empty `nl_intent`, and non-empty `kill_condition`. Use only the "
    "frozen signature and constructors in the proposer view. Do not emit a semantic "
    "verdict, signature, proof, task reference, or explanation.\n\n"
    "PROPOSER VIEW:\n{proposer_view}"
)

AXIOM_PACK_BAND_WORD_PROPOSER_PROMPT = (
    "Return only the constrained transport object with exactly one "
    "`typed_axiom_proposals` row. The row has exactly `source_ref`, `axiom_name`, "
    "`lhs_word`, `rhs_word`, `nl_intent`, and `kill_condition`. `source_ref` must be "
    "one of the frozen references in the proposer view. `lhs_word` and `rhs_word` "
    "are lowercase variable words such as `xyx` and `xy`; LeanMill constructs the "
    "typed formula. Do not emit source bytes, hashes, signatures, a semantic verdict, "
    "proof, task reference, or explanation.\n\n"
    "PROPOSER VIEW:\n{proposer_view}"
)

AXIOM_PACK_SEMANTIC_CHECKER_PROMPT = (
    "Review whether this typed axiom matches its structural conjecture. "
    "Return only JSON with boolean `faithful`, non-empty string `rationale`, "
    "and non-empty list `evidence_refs`. Do not sign anything.\n\n"
    "CHECK INPUT:\n{check_input}"
)

FRONTIER_BLUEPRINT_COMPILER_PROMPT = (
    "Compile the research direction into one typed frontier-theory campaign draft. "
    "Return JSON only. In anonymous_signature_census mode do not propose candidate axioms, "
    "named axiom lists, target theories, or literature labels. Specify executable primitive "
    "semantics, a registered adapter, a finite formula grammar, model/observation strata, "
    "verification plan, deanchoring policy, budgets, and stop rule. If the brief carries a "
    "finite typed first-order or equational signature, prefer `generic_fol_finite.v1` over a "
    "family-named adapter. When raw table iteration is infeasible but the base theory is "
    "solver-executable, set `adapter_config.model_generation` to "
    "{{\"mode\":\"smt_exact\",\"max_canonical_models_per_stratum\":N,"
    "\"timeout_ms_per_stratum\":T}}`; this remains exact only if the host reaches final "
    "UNSAT and otherwise fails preparation. "
    "If the brief carries a "
    "minimum or exact number of formulas per candidate presentation, encode it as "
    "navigator_contract.presentation_size with integer minimum/maximum bounds no larger "
    "than pack_arity. Default navigator_contract.selection_mode to `theory_program`; use "
    "`compact_axiom_pack` only when the direction explicitly asks for minimal jointly "
    "necessary presentations. "
    "Set navigator_contract.host_isolated_lineages above 1 only when independent "
    "conjectural traces are scientifically useful and the provider-call budget can give "
    "each trace at least one turn; this is search diversification, not proof authority. "
    "Emit executable LeanMill IR, never a prose design schema. `signature` must have exactly "
    "`schema`, `name`, `sorts:[{name}]`, `operations:[{name,arg_sorts,result_sort}]`, and "
    "`relations:[{name,arg_sorts}]`. `primitive_semantics` must be an object with "
    "`operation_bindings` and `relation_bindings` maps keyed by those exact symbol names. "
    "`base_axioms` contains only `leanmill.axiom_formula.v1` objects; use `[]` with "
    "`base_theory_status=explicit_empty` when there are none. `collapse_controls` is an array. "
    "Do not invent alternate field names, semantic-constraint records, procedures, stages, or "
    "adapter schemas. For an anonymous single total binary operation with the canonical magma "
    "equation grammar, use registered adapter `magma_equational.v1`, operation name `op0`, sort "
    "name `S0`, and its declared grammar/config shapes. "
    "If the brief carries a delegated_stop_instruction, copy it "
    "exactly to stop_rule.user_instruction and lower it "
    "to a nonempty typed stop_rule.executable_condition over host-observable receipts. Required fields: "
    "{required_fields}\n\nBRIEF:\n{brief_json}"
)

AXIOMPACK_CAMPAIGN_BUDGET_COMPILER_PROMPT = (
    "Compile the user's campaign-budget preference into the exact user campaign schema below. "
    "Return one JSON object only; JSON is the structured transport and the host renders the canonical YAML. "
    "Choose a named preset as the base, then include explicit caps. Preserve any mathematical stopping "
    "condition verbatim in stop.when; do not invent a theorem, candidate axiom, success criterion, or larger "
    "budget. If no budget preference is stated, use the standard preset unchanged. model_transport must be "
    "subscription_agent_runtime. Required shape: "
    "{{\"schema\":\"leanmill.exploration_budget_user.v1\",\"preset\":\"standard\","
    "\"budget\":{{\"wall_clock\":\"2h\",\"provider_calls\":24,\"agent_turns\":30,"
    "\"input_tokens\":750000,\"output_tokens\":250000,\"metered_api_usd\":\"20\","
    "\"workbench_actions\":96,\"adapter_forge_attempts\":2,"
    "\"context\":{{\"models\":100000,\"truth_cells\":50000000}},"
    "\"boundary\":{{\"queries\":12,\"smt_calls\":12,\"smt_time\":\"1h\","
    "\"lean_attempts\":6,\"lean_time\":\"1h\"}}}},"
    "\"stop\":{{\"max_finalists\":8,\"low_yield_patience\":3,"
    "\"min_marginal_information_per_cost\":\"0.05\",\"coverage_target\":\"0.9\","
    "\"when\":null}},\"model_transport\":\"subscription_agent_runtime\"}}.\n\n"
    "CAMPAIGN DIRECTION / BUDGET PREFERENCE:\n{preference_text}"
)

FRONTIER_BLUEPRINT_SEMANTIC_REVIEW_PROMPT = (
    "Independently review a proposed frontier-theory blueprint against its research brief. "
    "Check that the typed signature and primitive semantics preserve the requested exploration "
    "surface, that the adapter semantics are adequate, and that a cold census contains no "
    "candidate laws, named axiom lists, hidden target theory, or literature labels. Return only "
    "JSON with `accepted` (boolean), `candidate_law_leakage` (boolean), non-empty `rationale`, "
    "and non-empty `evidence_refs`. If a delegated scientific stop instruction is present, also "
    "return `stop_rule_aligned` and set it true only when the lowering preserves the instruction "
    "and is executable from host receipts. Do not sign or mutate the draft.\n\nREVIEW INPUT:\n{review_json}"
)

ADAPTER_FORGE_PROMPT = (
    "Implement the missing TheorySubstrateAdapter in the staged workspace. Your deliverable is "
    "code, tests, a static manifest, and self-test receipts. Implement deterministic "
    "abstract/signature/context/lower/check_raw behavior against the frozen fixtures. You may not "
    "edit the live adapter registry, declare your own exactness, add a trust root, or propose "
    "candidate axioms. Run the acceptance tests before returning a JSON proposal containing "
    "source_paths, test_paths, manifest, and self_test_receipts.\n\nADAPTER GAP:\n{gap_json}"
)

ADAPTER_CAPABILITY_FORGE_PROMPT = (
    "Implement the missing theory-language capability in the staged workspace. Preserve the "
    "existing adapter identity. Write a Python module exposing "
    "`build_coordinates(context_snapshot, request)`, returning a JSON object keyed by every "
    "frozen object ID, plus focused checks. The coordinate may encode a quotient, "
    "observable, obstruction, or other requested interface; do not force it into an equation. "
    "Start from `context_fixture.json`, which contains the executable snapshot shape and sample "
    "models; use the full `formal_context.json` only for a bounded final check. Do not edit the "
    "live repository or registry, "
    "declare exactness, interpret the anonymous substrate, or propose axioms. Run your checks, "
    "then return one JSON object containing `source_paths`, `test_paths`, a `manifest` with "
    "`capability_source` equal to one entry in `source_paths`, "
    "`interface`=`leanmill.object_coordinates.v1`, `request_id`, and one to four "
    "`observable_paths` selecting scalar theory coordinates. Keep raw profiles, tables, model IDs, "
    "and counterexample details outside those observables. "
    "When the abstraction maps source models pointwise into another finite first-order "
    "structure, return an envelope with `coordinates` and `functor_image`; the latter has "
    "exactly `functor_id`, a standard TheorySignature `signature`, and `models` mapping each "
    "included source object ID to standard FiniteModel JSON. Omit that envelope when no "
    "pointwise finite-model image exists. The host owns validation, isomorphism quotienting, "
    "multiplicity, and context authority. "
    "`self_test_receipts`, and `registry_mutation`=false. Paths must be relative to the staged "
    "workspace.\n\nADAPTER GAP:\n{gap_json}"
)

ADAPTER_FORGE_REVIEW_PROMPT = (
    "Independently review this quarantined TheorySubstrateAdapter proposal against its typed gap and "
    "host-conformance receipts. Check semantic preservation, deterministic lowering/checking, fixture "
    "coverage, exact-versus-sampled claim boundaries, and cold-view leakage. Return one JSON object with "
    "`accepted` (boolean), non-empty `reviewer_ref`, `rationale`, and `evidence_refs`. Do not edit code, "
    "mutate the registry, or grant exactness authority. For a `capability_missing` gap, assess only the "
    "requested coordinate on the frozen context: acceptance quarantines code for later authority and does "
    "not certify all finite carriers, registry admission, or an unrestricted theorem.\n\n"
    "REVIEW PAYLOAD:\n{review_json}"
)

AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V1 = (
    "You are navigating an anonymous, typed theory landscape. Established theory names, literature "
    "labels, and sealed evaluation rows are unavailable. Use the registered workbench actions to inspect "
    "node pages, formula structure, minimal generators, joint-only consequences, and separation models. "
    "Seek small independent presentations with nonempty robust extents and consequences produced by the "
    "conjunction. Spend actions where they change which boundary question should be tested. Return exactly "
    "one JSON object in one of these forms: "
    "{{\"decision\":\"request\",\"capability_id\":\"...\",\"input_refs\":{{...}},\"rationale\":\"...\"}}; "
    "{{\"decision\":\"freeze\",\"formula_ids\":[\"...\",\"...\"],\"rationale\":\"...\"}}; or "
    "{{\"decision\":\"finish\",\"rationale\":\"...\"}}. Never invent a receipt or formula ID.\n\n"
    "Budget exhaustion does not promote a preview. The budget state displays the low-yield threshold and "
    "patience; the host records the candidate's actual information-per-cost and stops after the configured "
    "consecutive low-yield window rather than turning the threshold into a one-shot veto. `reject_all` remains "
    "reserved for host-receipted zero-residual candidates. Account for the exact remaining capacity shown below.\n\n"
    "BUDGET STATE:\n{budget_state_json}\n\nCOLD MANIFEST:\n{cold_manifest_json}\n\nWORKBENCH CONTRACT:\n{workbench_contract}\n\n"
    "CURRENT TRACE:\n{trace_json}"
)

AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V2 = (
    "You are navigating an anonymous, typed theory landscape. Established theory names, literature "
    "labels, and sealed evaluation rows are unavailable. Use the registered workbench actions to inspect "
    "node pages, formula structure, minimal generators, consequence residuals, and separation models. "
    "Choose a presentation only when the visible evidence justifies spending boundary-verification budget; "
    "the host reports which apparent consequences are already explained by a named cheap baseline, including "
    "finite-context constant/projection/full/empty structure templates. Treat a forced low-complexity template "
    "as an explanation to beat, not as residual discovery credit. It is "
    "legitimate to reject every inspected candidate after the host has emitted candidate-rejection receipts; "
    "use `reject_all` rather than nominating a weak candidate. When the seed grammar cannot express the next "
    "distinction, `propose_frontier_formula` is a legitimate request: author one typed equation with anonymous "
    "`sort_N`/`op_N` symbols and postfix term tokens. The host will typecheck it and, if semantically new, move "
    "the campaign to a new immutable context epoch; formula complexity is a cost, not a ban. Spend actions where they change which boundary "
    "question should be tested. Return exactly "
    "one JSON object with all five fields `decision`, `rationale`, `capability_id`, `input_refs`, and "
    "`formula_ids`. For a request, set the capability and its exact input object and set formula_ids to "
    "null. For a freeze, set capability_id to null, input_refs to {{}}, and formula_ids to the proposed "
    "IDs. For reject_all or finish, set capability_id and formula_ids to null and input_refs to {{}}. "
    "`reject_all` is accepted only after host-receipted candidate rejections; `finish` ends a run that already "
    "has a finalist. Never invent a "
    "receipt or formula ID.\n\n"
    "Budget exhaustion does not promote a preview; account for the exact remaining capacity shown below.\n\n"
    "BUDGET STATE:\n{budget_state_json}\n\nCOLD MANIFEST:\n{cold_manifest_json}\n\nWORKBENCH CONTRACT:\n{workbench_contract}\n\n"
    "CURRENT TRACE:\n{trace_json}"
)

AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V3 = (
    "You are navigating an anonymous, typed theory landscape. Established theory names, literature "
    "labels, and sealed evaluation rows are unavailable. The manifest exposes the frozen base equations "
    "with positional symbols; treat them as mathematical facts and use them to test short deductions or "
    "structural collapse. Use the registered workbench actions to inspect "
    "node pages, formula structure, minimal generators, consequence residuals, and separation models. "
    "Choose a presentation only when the visible evidence justifies spending boundary-verification budget; "
    "the host reports which apparent consequences are already explained by a named cheap baseline, including "
    "finite-context constant/projection/full/empty structure templates. Treat a forced low-complexity template "
    "as an explanation to beat, not as residual discovery credit. A nonempty finite residual is necessary "
    "for a boundary query but is not by itself a quality or novelty certificate. A state-cap-saturated "
    "cheap search is `baseline_inconclusive`, never positive residual evidence; pivot or expand rather than "
    "freeze it. It is "
    "legitimate to reject every inspected candidate after the host has emitted candidate-rejection receipts; "
    "use `reject_all` rather than nominating a weak candidate. The frozen formula grammar is an orientation "
    "seed, not the hypothesis horizon. When it cannot express a worthwhile structural conjecture, or its "
    "survivors are routine consequences of the visible base equations, "
    "`propose_frontier_formula` is legitimate: author one typed equation with anonymous `sort_N`/`op_N` "
    "symbols and postfix term tokens. The host typechecks it and rebuilds an immutable context epoch; the next "
    "view reveals whether its finite semantic profile adds a distinction. A syntactically different formula "
    "with an old profile earns no information, and complexity is charged as cost. Spend actions where they "
    "change which boundary question should be tested. A `select_theory_presentation` request is a diagnostic preview only and does "
    "not freeze anything; only a subsequent `decision=freeze` creates a finalist. Before freezing, use "
    "that preview to rank one or more `residual_synergy_formula_ids` as the expensive questions worth "
    "testing. In theory-program mode, `prediction_profile` reports each target's seed-chart status "
    "and leave-one-premise-out counterexamples; a refuted or vacuous prediction is feedback for the "
    "next move and cannot freeze as a finalist. "
    "Return exactly one JSON object with all six fields `decision`, `rationale`, `capability_id`, "
    "`input_refs`, `formula_ids`, and `boundary_target_ids`. For a request, set the capability and its exact "
    "input object and set formula_ids and boundary_target_ids to null. For a freeze, set capability_id to "
    "null, input_refs to {{}}, formula_ids to the proposed presentation, and boundary_target_ids to the "
    "ordered nonempty subset copied from the preview. For reject_all or finish, set capability_id, formula_ids, "
    "and boundary_target_ids to null and input_refs to {{}}. A frozen finalist alone is not a reason to "
    "finish while the remaining budget can materially test a different region or formula expansion. "
    "`reject_all` is accepted only after host-receipted candidate rejections; `finish` ends a run that already "
    "has a finalist. Never invent a "
    "receipt or formula ID.\n\n"
    "Budget exhaustion does not promote a preview; account for the exact remaining capacity shown below.\n\n"
    "BUDGET STATE:\n{budget_state_json}\n\nCOLD MANIFEST:\n{cold_manifest_json}\n\nWORKBENCH CONTRACT:\n{workbench_contract}\n\n"
    "CURRENT TRACE:\n{trace_json}"
)

AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V4 = AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V3.replace(
    "The frozen formula grammar is an orientation seed, not the hypothesis horizon. ",
    "When formula authorship is blind, `show_indistinguishable_objects` exposes "
    "anonymous same-stratum objects that agree on every current formula. Use a pair "
    "to invent a short typed equation and pass its IDs as `contrast_object_ids`; the "
    "host then checks whether the equation creates a new finite semantic coordinate. "
    "That witness is local to the current object panel and grants no cross-stratum, "
    "proof, or novelty credit. The frozen formula grammar is an orientation seed, not "
    "the hypothesis horizon. ",
)

AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V5 = AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V4.replace(
    "A frozen finalist alone is not a reason to finish while the remaining budget can "
    "materially test a different region or formula expansion. ",
    "A frozen finalist alone is not a reason to finish while the remaining budget can "
    "materially test another region in the current formula context. If formula expansion "
    "may matter, request it before the first freeze. A later formula proposal is receipted "
    "for a successor epoch and does not replace the frozen finalist. ",
)

AXIOMPACK_THEORY_NAVIGATOR_PROMPT = AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V5.replace(
    "Use a pair to invent a short typed equation and pass its IDs as `contrast_object_ids`; ",
    "Use a pair to invent a typed first-order coordinate and pass its IDs as "
    "`contrast_object_ids`; ",
).replace(
    "`propose_frontier_formula` is legitimate: author one typed equation with anonymous "
    "`sort_N`/`op_N` symbols and postfix term tokens. The host typechecks it and rebuilds an "
    "immutable context epoch; ",
    "`propose_frontier_formula` is legitimate. Use either the compact equation fields or a "
    "flat typed `formula_tokens` stack over anonymous `sort_N`, `op_N`, and `rel_N` symbols. "
    "The formula stack supports `eq`, Boolean connectives, and `forall:x`/`exists:x`; the "
    "stack is postfix: emit the complete formula first, then append its quantifier; never "
    "put a quantifier before its formula operand. The "
    "host typechecks it and rebuilds an immutable context epoch. The representation choice "
    "belongs to you. Optional `definitions` name local derived operations over the prior "
    "signature; the host expands them away before evaluation, so they can compress a useful "
    "representation but cannot add theory strength by themselves. If the needed distinction "
    "requires a new primitive, observable, quotient, or abstraction, use "
    "`propose_theory_language_expansion`; it freezes an outbound request for a new reviewed "
    "blueprint or adapter capability and cannot mutate this context; ",
).replace(
    "Before freezing, use that preview to rank one or more "
    "`residual_synergy_formula_ids` as the expensive questions worth testing. ",
    "Before freezing, follow the manifest's `selection_mode`. In "
    "`compact_axiom_pack`, copy an ordered subset of "
    "`residual_synergy_formula_ids`. In `theory_program`, author the predictions: "
    "choose one or more visible typed formula IDs outside the presentation, including "
    "targets that the current finite chart refutes, supports only vacuously, or does "
    "not price as residual. The host reports those chart relations as diagnostics; "
    "empty bounded extent, cheap-baseline coverage, and zero residual bits do not veto "
    "a theory program. Use `reject_candidate` with its hypotheses and predictions when "
    "you judge a program unworthy; that creates a host-assessed refusal which may later "
    "support `reject_all`. ",
).replace(
    "For a freeze, set capability_id to null, input_refs to {{}}, formula_ids to the "
    "proposed presentation, and boundary_target_ids to the ordered nonempty subset "
    "copied from the preview. For reject_all or finish, set capability_id, formula_ids, ",
    "For a freeze, set capability_id to null, input_refs to {{}}, formula_ids to the "
    "proposed presentation, and boundary_target_ids to the ordered nonempty compact "
    "residual subset or theory-program predictions. For `reject_candidate`, use the "
    "same hypothesis and prediction fields and put your kill reason in rationale. For "
    "reject_all or finish, set capability_id, formula_ids, ",
).replace(
    "base equations",
    "base formulas",
).replace(
    "checks whether the equation creates a new finite semantic coordinate",
    "checks whether the formula creates a new finite semantic coordinate",
)

AXIOMPACK_POST_FREEZE_LITERATURE_PROMPT = (
    "You are the post-freeze literature auditor for an anonymous AxiomPack result. "
    "The candidate and verification receipts were frozen before this call. Use web search now. "
    "Follow the source priorities in the packet and prefer primary mathematical or technical "
    "sources; use secondary sources only for routing. Match each displayed formula exactly or "
    "state that no exact identifier was located. Determine whether the displayed implication "
    "is already recorded, is an immediate published consequence, or was not located in this "
    "bounded review. Use `interpretation_context`, especially the frozen base formulas and primitive "
    "semantics, to identify the ambient theory before searching; do not search only the anonymous "
    "op_N rendering. Do not infer novelty from failed search and do not upgrade a bounded model "
    "result into a universal claim. Explain the candidate's key recombination only from the "
    "displayed proof, premise-attribution arms, finite/SMT receipts, and primary sources. Give each "
    "premise a functional role, name the invariant or obstruction crossed, and emit a domain-stripped "
    "transportable constraint fingerprint for later isomorphism search. Its evidence_refs must be "
    "receipt hashes present in the frozen packet. A transported resemblance remains advisory until a "
    "destination-side discriminator verifies it. Every claimed match needs a direct source URL and a "
    "concise description of what that source supports. Return only the requested JSON object.\n\n"
    "FROZEN RESULT PACKET:\n{result_packet_json}"
)

AXIOMPACK_LINEAGE_SYNTHESIS_PROMPT = (
    "You are the late synthesis navigator after host-isolated anonymous theory "
    "lineages have stopped. Their frozen requests are now visible together for "
    "the first time. You are the objective contract's late independent review; "
    "do not request another review of evidence already present in each frozen "
    "program's prediction_profile and residual_information_yield. If an "
    "objective_contract is present, distinguish inner "
    "success (a valid frozen program) from outer success (the supplied research "
    "objective). Choose `proceed_boundary` only when one or more supplied program "
    "IDs justify spending the next verification tier; otherwise choose "
    "`continue_search` and name the next discriminator. Choose "
    "`admit_formulas` to admit one or more "
    "signature-preserving formula requests into a rebuilt context; "
    "`escalate_language` for one or more requests that need a new primitive, "
    "observable, quotient, or abstraction; or `defer_all`. Select only supplied "
    "request IDs and partition every other ID into deferred_request_ids. Objective "
    "routes must defer every request. `proceed_boundary` must bind relevant frozen "
    "`program_ids`; `continue_search` must bind rejected programs when any exist and "
    "may leave `program_ids` empty when no lineage froze a program. "
    "A deferred request is not carried into the next search wave. If your next "
    "discriminator needs to evaluate or compose supplied formula requests, choose "
    "`admit_formulas` for those requests; use `continue_search` only when the next "
    "discriminator can run in the unchanged context without their contents. "
    "Declare the causal dependency in `next_discriminator_request_ids`: for "
    "`admit_formulas` or `escalate_language` it must contain exactly the selected "
    "request IDs; every other route must return an empty array. "
    "request routes must leave `program_ids` empty. You may "
    "select several formulas when their interaction is the conjecture. Judge by "
    "the next discriminating test and kill condition, without importing familiar "
    "theory labels or treating independent agreement as truth. You cannot admit a "
    "formula, alter the signature, certify novelty, or grant proof authority. "
    "Return only the requested JSON object.\n\nFROZEN LINEAGE REQUESTS:\n"
    "{synthesis_input_json}"
)

LEANMILL_EIGENQUESTION_REVIEW_PROMPT = (
    "Review candidate LeanMill research eigenquestions as an advisory critic. Rank each exactly once by "
    "information yield, novelty headroom, and harness readiness. For every question name the strongest "
    "fatal confounder, one discriminating test, a kill condition, and the minimum artifact needed before "
    "running it. Prefer a question that can distinguish apparatus weakness from mathematical scarcity. "
    "Do not solve the mathematics, invent evidence, infer novelty from missing literature, change budgets, "
    "or grant proof/promotion authority. The portfolio_sequence is the recommended execution order. Return "
    "only the requested JSON object.\n\nREVIEW PAYLOAD:\n{payload_json}"
)

__all__ = [
    "ADAPTER_FORGE_PROMPT", "ADAPTER_CAPABILITY_FORGE_PROMPT", "ADAPTER_FORGE_REVIEW_PROMPT",
    "AXIOMPACK_CAMPAIGN_BUDGET_COMPILER_PROMPT",
    "AXIOM_PACK_BAND_WORD_PROPOSER_PROMPT",
    "AXIOM_PACK_SEMANTIC_CHECKER_PROMPT", "AXIOM_PACK_TYPED_PROPOSER_PROMPT",
    "FRONTIER_BLUEPRINT_COMPILER_PROMPT", "FRONTIER_BLUEPRINT_SEMANTIC_REVIEW_PROMPT",
    "AXIOMPACK_THEORY_NAVIGATOR_PROMPT", "AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V1",
    "AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V2", "AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V3",
    "AXIOMPACK_POST_FREEZE_LITERATURE_PROMPT",
    "AXIOMPACK_LINEAGE_SYNTHESIS_PROMPT",
    "LEANMILL_EIGENQUESTION_REVIEW_PROMPT",
]
