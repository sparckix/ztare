#!/usr/bin/env python3
"""Compare primitive and learned-word search under two explicit clocks."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Callable


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ztare.common.equivariance import stable_sha256
from ztare.common.factored_search import (
    FactoredSearchMacro,
    search_factored,
)


HYPOTHESIS_ID = "H-GPSA-GENERATIVE-SKILL-EDGE-SEARCH-20260806-117"
CARRIER_SHA256 = "6" * 64
PROJECTION_SHA256 = "9" * 64


class ChainProblem:
    problem_id = "h117-chain"
    projection_sha256 = PROJECTION_SHA256
    factor_names = ("state",)
    terminal_factor_names = ("goal_edge",)
    feasibility_factor_names = ()
    availability_factor_names = ()
    evidence_refs = ("h117:chain",)
    exact_transition_identity = True

    @staticmethod
    def dominance_key(state: int) -> int:
        return state

    @staticmethod
    def dominance_vector(_state: int) -> tuple[()]:
        return ()

    @staticmethod
    def goal_edge(state: int, operation: str, time: int) -> bool:
        if state != time:
            raise RuntimeError("environment clock drifted from primitive depth")
        return state == 11 and operation == "advance"

    @staticmethod
    def admissible(state: int) -> bool:
        return state <= 12

    @staticmethod
    def estimate(_state: int) -> int:
        return 0


def _macro(**changes: Any) -> FactoredSearchMacro:
    values = {
        "skill_sha256": "7" * 64,
        "carrier_execution_sha256": CARRIER_SHA256,
        "projection_sha256": PROJECTION_SHA256,
        "operations": ("advance", "advance", "advance"),
        "evidence_refs": ("h117:settled-history-word",),
    }
    values.update(changes)
    return FactoredSearchMacro(**values)


def _predict(state: int, _operation: str, time: int) -> int | None:
    return state + 1 if state == time else None


def _receipt(result: Any) -> dict[str, Any]:
    return {
        "status": result.status,
        "actions": list(result.actions),
        "search_move_refs": list(result.search_move_refs),
        "generated": result.generated,
        "expanded": result.expanded,
        "deepest_deliberation_depth": result.deepest_depth,
        "deepest_primitive_depth": result.deepest_primitive_depth,
        "primitive_action_cost": result.primitive_action_cost,
        "macro_edges_attempted": result.macro_edges_attempted,
        "macro_edges_admitted": result.macro_edges_admitted,
    }


def _rejects(call: Callable[[], Any], fragment: str) -> bool:
    try:
        call()
    except ValueError as error:
        return fragment in str(error)
    return False


def run_audit() -> dict[str, Any]:
    baseline = search_factored(
        predict=_predict,
        start=0,
        interventions=("advance",),
        problem=ChainProblem(),
        max_depth=4,
        max_states=100,
        max_primitive_cost=12,
    )
    primitive_reference = search_factored(
        predict=_predict,
        start=0,
        interventions=("advance",),
        problem=ChainProblem(),
        max_depth=12,
        max_states=100,
        max_primitive_cost=12,
    )
    chunked = search_factored(
        predict=_predict,
        start=0,
        interventions=("advance",),
        problem=ChainProblem(),
        max_depth=4,
        max_states=100,
        macros=(_macro(),),
        max_primitive_cost=12,
        carrier_execution_sha256=CARRIER_SHA256,
    )

    class IntermediateGoal(ChainProblem):
        @staticmethod
        def goal_edge(state: int, operation: str, time: int) -> bool:
            if state != time:
                raise RuntimeError("intermediate clock drifted")
            return state == 1 and operation == "advance"

    intermediate = search_factored(
        predict=_predict,
        start=0,
        interventions=("advance",),
        problem=IntermediateGoal(),
        max_depth=1,
        max_states=10,
        macros=(_macro(),),
        max_primitive_cost=3,
        carrier_execution_sha256=CARRIER_SHA256,
    )
    undefined = search_factored(
        predict=lambda state, _operation, _time: (
            None if state == 1 else state + 1
        ),
        start=0,
        interventions=("advance",),
        problem=ChainProblem(),
        max_depth=4,
        max_states=20,
        macros=(_macro(),),
        max_primitive_cost=12,
        carrier_execution_sha256=CARRIER_SHA256,
    )
    mutations = {
        "action_vocabulary": _rejects(
            lambda: search_factored(
                predict=_predict,
                start=0,
                interventions=("advance",),
                problem=ChainProblem(),
                macros=(_macro(operations=("advance", "alien")),),
                carrier_execution_sha256=CARRIER_SHA256,
            ),
            "action vocabulary",
        ),
        "carrier_identity": _rejects(
            lambda: search_factored(
                predict=_predict,
                start=0,
                interventions=("advance",),
                problem=ChainProblem(),
                macros=(_macro(),),
                carrier_execution_sha256="5" * 64,
            ),
            "carrier identity",
        ),
        "projection_identity": _rejects(
            lambda: search_factored(
                predict=_predict,
                start=0,
                interventions=("advance",),
                problem=ChainProblem(),
                macros=(_macro(projection_sha256="4" * 64),),
                carrier_execution_sha256=CARRIER_SHA256,
            ),
            "projection identity",
        ),
    }
    checks = {
        "primitive_only_depth_bounded": (
            baseline.status == "depth_bound_exhausted"
            and baseline.deepest_depth == 4
        ),
        "primitive_reference_goal_found": (
            primitive_reference.status == "edge_found"
        ),
        "chunked_goal_found": chunked.status == "edge_found",
        "primitive_program_exact": chunked.actions == ("advance",) * 12,
        "primitive_cost_preserved": chunked.primitive_action_cost == 12,
        "deliberation_bound_preserved": chunked.deepest_depth <= 4,
        "primitive_horizon_extended": chunked.deepest_primitive_depth == 12,
        "deliberation_saved_at_equal_execution_cost": (
            primitive_reference.primitive_action_cost
            == chunked.primitive_action_cost
            and primitive_reference.deepest_depth > chunked.deepest_depth
        ),
        "search_expansions_reduced": (
            primitive_reference.expanded > chunked.expanded
        ),
        "skill_move_consumed": any(
            ref.startswith("skill:") for ref in chunked.search_move_refs
        ),
        "intermediate_goal_preserved": (
            intermediate.status == "edge_found"
            and intermediate.actions == ("advance", "advance")
        ),
        "undefined_macro_refused": (
            undefined.status == "projected_frontier_exhausted"
            and undefined.macro_edges_admitted == 0
        ),
        "all_identity_mutations_detected": all(mutations.values()),
    }
    core = {
        "schema": "ztare-h117-generative-skill-edge-search-v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "kernel_supported" if all(checks.values()) else "rejected",
        "environment_contact": False,
        "controller_contact": False,
        "identities": {
            "carrier_execution_sha256": CARRIER_SHA256,
            "projection_sha256": PROJECTION_SHA256,
            "skill_sha256": "7" * 64,
            "word": ["advance", "advance", "advance"],
        },
        "baseline": _receipt(baseline),
        "primitive_reference": _receipt(primitive_reference),
        "chunked": _receipt(chunked),
        "intermediate_goal": _receipt(intermediate),
        "undefined_carrier": _receipt(undefined),
        "checks": checks,
        "mutation_checks": mutations,
        "claim_boundary": (
            "Synthetic search-kernel chunking only; no ARC task benefit, "
            "task credit, cross-task transfer, catalytic acquisition, "
            "takeoff, or novelty claim."
        ),
    }
    return {**core, "sha256": stable_sha256(core)}


if __name__ == "__main__":
    print(json.dumps(run_audit(), indent=2, sort_keys=True))
