from __future__ import annotations

from dataclasses import dataclass

# K consecutive investigated-only turns (no carrier ever emitted) surface a
# stagnation pressure so investigation cannot become infinite stalling. Single
# source of truth: the loop reads it for the K-bound, the leaf surface reads it
# to show the remaining budget.
INVESTIGATED_STAGNATION_K = 3


@dataclass(frozen=True)
class ScienceOutputPolicy:
    """Shared projection for object-level skill-acquisition worker outputs."""

    contract_id: str = "science-candidate-action-lowerability-v2"
    allowed_outputs: tuple[str, ...] = (
        "candidate",
        "registered_workbench_action_request",
        "investigated",
        "lowerability_blocked",
    )

    def short_text(self) -> str:
        return (
            "Science output policy: submit one of candidate, registered workbench "
            "action request, INVESTIGATED, or LOWERABILITY_BLOCKED. Assume the "
            "current capability "
            "set is sufficient unless a typed lowerability/observability receipt "
            "proves otherwise. A tool/capability proposal may be attached as "
            "optional meta evidence, but it never satisfies the science turn by "
            "itself; report missing sensors or morphisms inside LOWERABILITY_BLOCKED "
            "for Strategy aggregation. In DISCOVERY, staged counterexamples are "
            "evidence for alpha/gamma repair; in EVALUATION, fresh verifier slices "
            "are promotion evidence. INVESTIGATION IS FIRST-CLASS SCIENCE: a turn "
            "may close as INVESTIGATED — not a failure — when your probes eliminate "
            "a hypothesis class from visible evidence (a refuted spec-behavior / "
            "conflict clause), measurably narrowing the residual for the next turn. "
            "This is credited only when the elimination is NEW and evidence-backed "
            "(cited probe receipts show the refuted behavior on visible data); "
            "restating a known refutation, or probing without eliminating anything, "
            "does NOT close the turn. Do not rush a carrier when the honest next "
            "step is to narrow the space. If the turn is stuck, the rider is one "
            "free-form line, not a JSON schema surface."
        )

    def investigated_text(self) -> str:
        return (
            "INVESTIGATED closes a science turn positively without a carrier when "
            "your probes narrowed the residual by eliminating a hypothesis class. "
            "Emit it as an object inside `control_receipts` with "
            "`payload.eliminated_hypothesis` (the spec-behavior / rule family your "
            "evidence refutes), `payload.witness` (the visible (t, a, cell, "
            "observed-vs-predicted) that refutes it), and `payload.evidence_refs` "
            "(the `workspace/visible_cli_receipts/*` probe receipts that establish "
            "it). Credit requires the eliminated hypothesis to be NEW to the "
            "visible conflict-clause ledger and its witness to check out on visible "
            "evidence; a duplicate or unbacked elimination is rejected, not "
            "credited. Each valid elimination prunes the next turn's search — that "
            "is the science advancing even when no carrier is ready."
        )

    def blocker_text(self) -> str:
        return (
            "Empty `test_model_py` is admissible only for a registered workbench "
            "action request or LOWERABILITY_BLOCKED carrying evidence that no "
            "gamma-lowerable candidate is currently justified after current "
            "visible evidence, local scratch analysis, visible tools, and a "
            "candidate family were attempted. In DISCOVERY, that blocker must "
            "account for available staged counterexample/holdout refs as consumed "
            "evidence, or state that no such refs are staged. Consumed evidence "
            "must point to a derived analysis artifact, visible diagnostic receipt, "
            "or scored candidate that used it; raw files plus a failed tool menu "
            "do not certify exhaustion. Treat blocking as a stopping problem: if "
            "the next visible local action is cheap, executable, and information-"
            "bearing, run it in the same turn instead of stopping. A blocker that "
            "consumed counterexamples must include `stopping_rationale` explaining "
            "why the next visible local action is not worth or not possible now, "
            "and `local_frontier_decision` listing available, attempted, and "
            "unattempted local actions with expected information. "
            "A direct capability proposal is optional meta evidence only and must "
            "not be treated as loop closure. If the turn is stuck, the exit rider "
            "is free-form text on one line; do not ask for or emit a schema. "
            "An impossibility claim about a missing state feature or selector is a "
            "verdict and requires search_receipts (workspace/visible_cli_receipts/* "
            "probe refs) demonstrating the feature was examined before declaring it absent."
        )

    def tool_gap_text(self) -> str:
        return (
            "Tool gaps are second-order: the science leaf may name the missing "
            "sensor/morphism, evidence refs, and proposed evaluator inside "
            "LOWERABILITY_BLOCKED. It may also attach a proposal skeleton, but "
            "Strategy Office aggregation decides whether the gap opens "
            "tool-synthesis work."
        )

    def visible_composition_text(self) -> str:
        return (
            "If visible receipts or staged counterexamples contain facts needed "
            "to combine, compare, or refute a candidate route, inspect them with "
            "local tools, write scratch analyses inside the staged workspace when "
            "useful, and cite the resulting artifact/receipt refs for claims that "
            "rely on them; local composition over visible receipts may justify "
            "authoring a candidate. Use `score-worldmodel-candidate` "
            "for candidate feedback when available. Local composition is not "
            "promotion authority; replay/holdout still decides the candidate."
        )

    def discovery_evidence_text(self) -> str:
        return (
            "In DISCOVERY, staged counterexample/holdout refs are consumable "
            "evidence for alpha/gamma repair, not fresh verifier proof. A "
            "LOWERABILITY_BLOCKED answer must record consumed counterexample refs "
            "in `evidence_statuses`, or state that no staged counterexample refs exist."
        )

    def local_stopping_text(self) -> str:
        return (
            "In visible-workbench mode, use local tools as useful for your own "
            "candidate search. Final claims must cite receipts for tool results "
            "they rely on; a blocker should name the attempted candidate family "
            "and the evidence-backed obstruction, not satisfy a fixed tool "
            "checklist. A failed registered morphism is diagnostic; it is not by "
            "itself evidence that visible counterexamples contain no lowerable "
            "law."
        )

    def final_contract_text(self) -> str:
        return (
            "Return only one raw JSON object. Do not use markdown fences.\n\n"
            "Required keys:\n"
            "- `control_receipts`: list of typed receipt/action objects.\n"
            "- `thesis_markdown`: concise explanation and unresolved boundary.\n"
            "- `test_model_py`: executable carrier source. Leave empty only for "
            "a registered workbench action request, `LOWERABILITY_BLOCKED`, or "
            "`INVESTIGATED`.\n"
            "`INVESTIGATED` must be an object inside `control_receipts` with "
            "`payload.eliminated_hypothesis`, `payload.witness`, and "
            "`payload.evidence_refs`; it is credited only when the elimination is "
            "new and its witness checks out on visible evidence.\n"
            "`LOWERABILITY_BLOCKED` must be an object inside `control_receipts` "
            "with `payload.visible_capabilities_attempted`, "
            "`payload.candidate_family_attempted`, `payload.obstruction`, "
            "`payload.missing_witness_or_sensor`, `payload.next_action`, and "
            "`payload.evidence_refs`. If it marks any evidence as "
            "`consumed_counterexample`, include `payload.evidence_analysis_refs` "
            "pointing to derived scratch artifacts, visible diagnostic receipts, "
            "or scored candidates that used those refs, plus "
            "`payload.stopping_rationale` explaining why no further visible local "
            "probe/candidate should be run in this turn, and "
            "`payload.local_frontier_decision` with `available_actions`, "
            "`attempted_actions`, `unattempted_actions`, `chosen`, `stop_reason`, "
            "`expected_info_note`, and `evidence_refs`. If "
            "`visible_capabilities_attempted` names "
            "visible tools, cite their `workspace/visible_cli_receipts/*` refs "
            "via `evidence_refs`/`visible_receipt_refs`, or include structured "
            "`visible_command_errors` rows. Tool attempts are receipt-bound, not "
            "self-attested. Science-turn stuck exits may use one free-form rider "
            "line; the prompt surface does not carry a JSON schema for that rider. "
            "If `obstruction` or `missing_witness_or_sensor` asserts a missing state "
            "feature or selector, include `search_receipts` — at least one "
            "workspace/visible_cli_receipts/* probe receipt showing the feature was "
            "examined; an unexamined impossibility claim is a typed R1 reject.\n"
        )


SCIENCE_OUTPUT_POLICY = ScienceOutputPolicy()


def science_output_policy_text() -> str:
    return SCIENCE_OUTPUT_POLICY.short_text()
