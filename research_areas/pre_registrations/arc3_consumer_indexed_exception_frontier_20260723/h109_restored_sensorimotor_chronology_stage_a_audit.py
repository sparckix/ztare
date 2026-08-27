#!/usr/bin/env python3
"""Audit H109's exact prefix carrier without controller/environment contact."""

from __future__ import annotations

import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
PROBE_PATH = (
    ROOT / "scripts/public/control/arc3_causal_response_derivative_probe.py"
)
SPEC = importlib.util.spec_from_file_location("h109_probe", PROBE_PATH)
assert SPEC is not None and SPEC.loader is not None
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def args_for(
    output_dir: Path,
    *,
    transport: str,
    history_mode: str,
) -> argparse.Namespace:
    return argparse.Namespace(
        spec=str(BASE / "h97_causal_response_derivative_spec.json"),
        output_dir=str(output_dir),
        controller_transport=transport,
        initial_history_mode=history_mode,
        app_server_cwd=str(output_dir / "controller_cwd"),
        max_output_tokens=4096,
        timeout_seconds=300.0,
    )


def refuses(prefix: dict, mutation: str) -> bool:
    candidate = deepcopy(prefix)
    if mutation == "transition_action":
        candidate["transitions"][0]["action"] = 1
    elif mutation == "observation_content":
        candidate["observations"][0]["grid_rle_rows"][0] = "4x64"
    elif mutation == "transition_source":
        candidate["transitions"][0][
            "source_observation_sha256"
        ] = "0" * 64
    elif mutation == "transition_successor":
        candidate["transitions"][0][
            "successor_observation_sha256"
        ] = "0" * 64
    elif mutation == "observation_order":
        candidate["observations"][0], candidate["observations"][1] = (
            candidate["observations"][1],
            candidate["observations"][0],
        )
    elif mutation == "final_observation":
        candidate["final_observation"] = dict(
            candidate["observations"][-2]
        )
    elif mutation == "prefix_hash":
        candidate["sha256"] = "0" * 64
    else:
        raise ValueError(f"unknown mutation {mutation}")
    try:
        probe._compile_prefix_chronology_carrier(candidate)
    except ValueError:
        return True
    return False


def main() -> int:
    saved_responses_path = BASE / "h97_causal_response_derivative/manifest.json"
    saved_app_path = (
        BASE / "h97_causal_response_derivative_app_server/manifest.json"
    )
    exact_dir = BASE / "h109_restored_sensorimotor_chronology_app_server"
    with tempfile.TemporaryDirectory(prefix="ztare_h109_stage_a_") as raw:
        scratch = Path(raw)
        responses_args = args_for(
            scratch / "responses",
            transport=probe.RESPONSES_API_TRANSPORT,
            history_mode=probe.ENDPOINT_ONLY_HISTORY,
        )
        app_args = args_for(
            scratch / "app_server",
            transport=probe.CODEX_APP_SERVER_TRANSPORT,
            history_mode=probe.ENDPOINT_ONLY_HISTORY,
        )
        probe.run_preflight(responses_args)
        probe.run_preflight(app_args)
        fresh_responses = json.loads(
            (Path(responses_args.output_dir) / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        fresh_app = json.loads(
            (Path(app_args.output_dir) / "manifest.json").read_text(
                encoding="utf-8"
            )
        )

    saved_responses = json.loads(saved_responses_path.read_text(encoding="utf-8"))
    saved_app = json.loads(saved_app_path.read_text(encoding="utf-8"))
    exact_args = args_for(
        exact_dir,
        transport=probe.CODEX_APP_SERVER_TRANSPORT,
        history_mode=probe.EXACT_PREFIX_CHRONOLOGY,
    )
    context = probe._compile_live_context(exact_args)
    history = dict(context["initial_history_authority"])
    carrier = dict(history["chronology_carrier"])
    prefix = dict(context["prefix"])
    rendered = probe._initial_parent_input(
        context["grid"],
        levels_completed=int(context["observation"]["levels_completed"]),
        action_arity=int(prefix["action_arity"]),
        presentation=context["presentation"],
        prefix_action_count=len(prefix["actions"]),
        prefix=prefix,
        initial_history_mode=probe.EXACT_PREFIX_CHRONOLOGY,
        chronology_carrier=carrier,
    )
    content = rendered[0]["content"]
    decoded = [
        json.loads(row["text"])
        for row in content
        if row["type"] == "input_text"
    ]
    chronology_rows = [
        row
        for row in decoded
        if row.get("phase") == "restored_prefix_observation"
    ]

    endpoint_scope = saved_app["live_controller_scope_transport"]["target_scope"]
    exact_scope = context["scope"].to_receipt()
    preserved = (
        "task_sha256",
        "context_sha256",
        "choice_set_sha256",
        "action_vocabulary_sha256",
    )
    mutations = (
        "transition_action",
        "observation_content",
        "transition_source",
        "transition_successor",
        "observation_order",
        "final_observation",
        "prefix_hash",
    )
    checks = {
        "responses_endpoint_manifest_byte_equivalent": (
            fresh_responses == saved_responses
        ),
        "app_server_endpoint_manifest_byte_equivalent": fresh_app == saved_app,
        "source_prefix_hash_verified": (
            carrier["source_prefix_sha256"] == prefix["sha256"]
        ),
        "all_actions_rendered_in_order": (
            [row["following_action"] for row in chronology_rows[:-1]]
            == prefix["actions"]
        ),
        "all_observations_rendered_in_order": (
            [row["settled_observation"]["sha256"] for row in chronology_rows]
            == carrier["observation_sha256s"]
        ),
        "observation_image_count_exact": (
            sum(row["type"] == "input_image" for row in content) == 9
        ),
        "rendered_parent_input_hash_verified": (
            probe._sha({"input": rendered})
            == history["rendered_parent_input_sha256"]
        ),
        "endpoint_identity_verified": (
            carrier["endpoint_observation_sha256"]
            == context["observation"]["sha256"]
        ),
        "noncontroller_scope_coordinates_preserved": all(
            exact_scope[key] == endpoint_scope[key] for key in preserved
        ),
        "controller_coordinate_changed": (
            exact_scope["controller_sha256"]
            != endpoint_scope["controller_sha256"]
        ),
        "all_tampered_history_fixtures_refused": all(
            refuses(prefix, mutation) for mutation in mutations
        ),
    }
    core = {
        "schema": "ztare-h109-restored-sensorimotor-chronology-stage-a-v1",
        "hypothesis_id": (
            "H-GPSA-RESTORED-SENSORIMOTOR-CHRONOLOGY-20260806-109"
        ),
        "status": (
            "stage_a_supported"
            if all(checks.values())
            else "stage_a_rejected"
        ),
        "model_contact": False,
        "environment_contact": False,
        "checks": checks,
        "identities": {
            "source_prefix_sha256": prefix["sha256"],
            "chronology_carrier_sha256": carrier["sha256"],
            "initial_history_authority_sha256": history["sha256"],
            "h109_experiment_sha256": context["manifest"][
                "experiment_sha256"
            ],
            "endpoint_app_server_experiment_sha256": saved_app[
                "experiment_sha256"
            ],
            "endpoint_responses_experiment_sha256": saved_responses[
                "experiment_sha256"
            ],
        },
        "counts": {
            "actions": carrier["action_count"],
            "observations": carrier["observation_count"],
            "transitions": carrier["transition_count"],
            "rendered_observation_images": 8,
            "rendered_current_endpoint_images": 1,
            "negative_fixtures": len(mutations),
        },
        "claim_boundary": (
            "apparatus_identity_and_renderer_only; no controller or task "
            "effect measured"
        ),
    }
    result = {**core, "result_sha256": probe._sha(core)}
    output_path = BASE / "h109_restored_sensorimotor_chronology_stage_a_result.json"
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "stage_a_supported" else 1


if __name__ == "__main__":
    raise SystemExit(main())
