import argparse
from pathlib import Path

from src.ztare.common.paths import PROJECTS_DIR


MODE_DESCRIPTIONS = {
    "broad": "Use when the project has multiple plausible sub-questions or drift attractors.",
    "mechanism": "Use when the project tests one bounded causal or strategic mechanism.",
    "forecast": "Use when the project centers on an event boundary, horizon, and forecast discipline.",
    "probabilistic": "Use when the project explicitly targets a point probability for a defined event and horizon.",
}


MODE_HINTS = {
    "broad": {
        "core_question": (
            "What is the primary question this project must answer, without collapsing into one "
            "narrow sub-mechanism or a point forecast?"
        ),
        "out_of_scope": [
            "proving only one narrow mechanism as if it answers the whole project",
            "collapsing distinct end states into one rhetorical outcome",
            "making a point-probability forecast unless that is explicitly the project object",
        ],
        "success_states": [
            "state_a",
            "state_b",
            "state_c",
        ],
        "failure_states": [
            "single narrow seam presented as the whole answer",
            "laundry-list thesis with no ranking or discriminator",
            "forecast claims without explicit event boundary",
        ],
        "forecast_type": "none",
        "anchor_examples": [
            "proxy:classify_primary_state",
            "proxy:rank_load_bearing_factors",
            "test:test_current_state_classification",
            "test:test_rival_state_is_distinguishable",
            "test:test_missing_top_factor_blocks_transition",
        ],
    },
    "mechanism": {
        "core_question": (
            "What single mechanism is this project testing, under what conditions, and against what rival?"
        ),
        "out_of_scope": [
            "broad strategic conclusions not required to test the mechanism",
            "secondary forecasts or market sizing unless explicitly load-bearing",
            "adjacent mechanisms that are not needed for the core discriminator",
        ],
        "success_states": [
            "mechanism_supported",
            "mechanism_rejected",
        ],
        "failure_states": [
            "drift into generic industry commentary",
            "latent-variable explanation with no observable proxy",
            "test suite that only recomputes thesis-authored targets",
        ],
        "forecast_type": "none",
        "anchor_examples": [
            "proxy:compute_mechanism_score",
            "proxy:evaluate_rival_case",
            "test:test_mechanism_holds_on_current_evidence",
            "test:test_rival_case_breaks_when_mechanism_absent",
            "test:test_failure_boundary_is_not_counted_as_success",
        ],
    },
    "forecast": {
        "core_question": (
            "What event is being forecast, for what horizon, and what bounded directional claim should survive?"
        ),
        "out_of_scope": [
            "turning a mechanism project into a point forecast without explicit event boundaries",
            "claiming certainty or inevitability rather than bounded forecast tilt",
            "mixing multiple forecast horizons into one answer",
        ],
        "success_states": [
            "forecast_tilt_a",
            "forecast_tilt_b",
            "event_failure_boundary",
        ],
        "failure_states": [
            "undefined event boundary",
            "horizon slippage",
            "directional support presented as decisive forecast proof",
        ],
        "forecast_type": "directional_forecast",
        "anchor_examples": [
            "proxy:classify_event_boundary",
            "proxy:forecast_tilt_by_horizon",
            "test:test_current_evidence_supports_directional_tilt",
            "test:test_event_boundary_dominates_if_triggered",
            "test:test_forecast_is_horizon_bounded",
        ],
    },
    "probabilistic": {
        "core_question": (
            "What explicit event probability is being estimated, for what horizon, and from what reference class or model basis?"
        ),
        "out_of_scope": [
            "smuggling in a naked percentage without explicit event semantics",
            "using a probability DAG alone as justification for a point probability",
            "mixing directional mechanism claims with probabilistic output without calibration discipline",
        ],
        "success_states": [
            "event_occurs_by_horizon",
            "event_does_not_occur_by_horizon",
        ],
        "failure_states": [
            "undefined event ontology",
            "uncalibrated point probability theater",
            "probability claim unsupported by explicit modeling basis",
        ],
        "forecast_type": "probabilistic_forecast",
        "anchor_examples": [
            "proxy:estimate_event_probability",
            "proxy:classify_event_outcome",
            "test:test_probability_target_is_explicit",
            "test:test_event_boundary_is_horizon_bounded",
            "test:test_probability_model_changes_when_load_bearing_inputs_change",
        ],
    },
}


def resolve_project_dir(project_arg: str) -> Path:
    candidate = Path(project_arg)
    if candidate.exists():
        return candidate.resolve()
    fallback = PROJECTS_DIR / project_arg
    if fallback.exists():
        return fallback.resolve()
    raise FileNotFoundError(f"Project not found: {project_arg}")


def render_charter(mode: str) -> str:
    hints = MODE_HINTS[mode]
    out_of_scope = "\n".join(f"- {item}" for item in hints["out_of_scope"])
    success_states = "\n".join(f"- {item}" for item in hints["success_states"])
    failure_states = "\n".join(f"- {item}" for item in hints["failure_states"])
    anchor_examples = "\n".join(f"- {item}" for item in hints["anchor_examples"])
    return f"""# Project Charter

Mode: `{mode}`

Hint:
- {MODE_DESCRIPTIONS[mode]}

## Core Question
{hints["core_question"]}

## Out Of Scope
{out_of_scope}

## End States
### Success
The project should cleanly distinguish:
{success_states}

### Failure
The project has failed if it drifts into any of the following:
{failure_states}

## Forecast Type
- {hints["forecast_type"]}

## Inheritance
- none

## Anchor Proxies
{anchor_examples}
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a project_charter.md for a ZTARE project."
    )
    parser.add_argument("--project", required=True, help="Project name under projects/ or explicit project path.")
    parser.add_argument(
        "--mode",
        default="broad",
        choices=sorted(MODE_HINTS.keys()),
        help="Starting charter shape.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing project_charter.md.",
    )
    args = parser.parse_args()

    project_dir = resolve_project_dir(args.project)
    charter_path = project_dir / "project_charter.md"

    if charter_path.exists() and not args.force:
        raise SystemExit(
            f"Refusing to overwrite existing charter: {charter_path}. Use --force to replace it."
        )

    charter_path.write_text(render_charter(args.mode), encoding="utf-8")
    print(f"Project charter scaffolded: {charter_path}")
    print(f"Mode: {args.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
