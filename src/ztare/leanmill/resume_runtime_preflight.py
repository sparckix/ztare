"""Provider-free import and schema preflight for resumable LeanMill campaigns."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ztare.leanmill.theory_ir import content_hash


def resume_runtime_preflight() -> dict[str, Any]:
    # Import the complete transition surface whose partial deployment caused
    # prior resume failures.  Missing modules or symbols fail before launch.
    from ztare.common.task_discharge import bind_task_discharge_receipt
    from ztare.leanmill.adapter_forge import execute_adapter_forge_attempt
    from ztare.leanmill.axiompack_leaf_workbench import (
        navigator_decision_output_schema,
    )
    from ztare.leanmill.explore_axiom_space import execute_frontier_boundaries
    from ztare.leanmill.formal_task_campaign_executor import (
        make_formalization_campaign_task_executor,
    )
    from ztare.leanmill.frontier_agent_runtime import _validate_codex_strict_schema
    from ztare.leanmill.frontier_campaign_runner import drive_frontier_campaign

    symbols = {
        "bind_task_discharge_receipt": bind_task_discharge_receipt,
        "execute_adapter_forge_attempt": execute_adapter_forge_attempt,
        "execute_frontier_boundaries": execute_frontier_boundaries,
        "make_formalization_campaign_task_executor": (
            make_formalization_campaign_task_executor
        ),
        "drive_frontier_campaign": drive_frontier_campaign,
    }
    if not all(callable(value) for value in symbols.values()):
        raise TypeError("LeanMill resume runtime contains a non-callable transition")
    schema = navigator_decision_output_schema()
    _validate_codex_strict_schema(schema)
    source_root = Path(__file__).resolve().parent
    source_names = (
        "adapter_forge.py",
        "axiompack_leaf_workbench.py",
        "explore_axiom_space.py",
        "external_science_admission.py",
        "formal_task_campaign_executor.py",
        "frontier_campaign_runner.py",
    )
    sources = {
        name: content_hash({"source": (source_root / name).read_text(encoding="utf-8")})
        for name in source_names
    }
    core = {
        "schema": "leanmill.resume_runtime_preflight.v1",
        "status": "passed",
        "callable_symbols": sorted(symbols),
        "navigator_output_schema_sha256": content_hash(schema),
        "source_sha256s": sources,
        "provider_calls": 0,
        "authority": "deterministic_host_preflight",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def main() -> int:
    print(json.dumps(resume_runtime_preflight(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
