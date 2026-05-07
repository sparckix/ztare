"""Execution-route classifier tests."""

from __future__ import annotations

from src.ztare.orchestration.execution_routing import infer_execution_route, render_route_contract


def test_explicit_route_only_blocks_live_work():
    route = infer_execution_route(
        frontmatter={
            "execution_route": "route_only",
            "ztare_allowed": False,
            "live_api_allowed": False,
            "gpu_allowed": False,
        },
        body="Decide whether this should become a substrate or a manual audit.",
        role_id="research_director",
    )
    assert route.route == "route_only"
    assert route.experiment_loop_allowed is False
    assert route.ztare_allowed is False
    assert route.live_api_allowed is False
    assert route.gpu_allowed is False
    assert "execution_route_decision" in route.required_first_artifact


def test_ztare_alias_maps_to_generic_experiment_loop():
    route = infer_execution_route(
        frontmatter={"execution_route": "ztare_loop"},
        body="",
        role_id="manager",
    )
    assert route.route == "experiment_loop"
    assert route.experiment_loop_allowed is True
    assert route.ztare_allowed is True


def test_research_director_cannot_silently_build_substrate():
    route = infer_execution_route(
        frontmatter={},
        body="Build a substrate with generate_substrate and then run ZTARE.",
        role_id="research_director",
    )
    assert route.route == "artifact_build"
    assert "authorized builder" in route.escalation
    assert "must produce a handoff spec" in route.rationale


def test_render_contract_contains_required_first_artifact():
    route = infer_execution_route(
        frontmatter={"execution_route": "expert_review"},
        body="Ask Gemini for an adversarial review.",
        role_id="research_director",
    )
    rendered = render_route_contract(route)
    assert "EXECUTION ROUTE CONTRACT" in rendered
    assert "expert_review_packet" in rendered
    assert "live_api_allowed: true" in rendered


def test_deanchored_meta_pattern_routes_to_synthesis_checkpoint():
    route = infer_execution_route(
        frontmatter={},
        body="De-anchor from local slicing and identify the big picture proof object hiding in plain sight.",
        role_id="research_director",
    )
    assert route.route == "synthesis_review"
    assert route.live_api_allowed is False
    assert route.gpu_allowed is False
    assert route.experiment_loop_allowed is False
    assert "deanchored_synthesis_checkpoint" in route.required_first_artifact
    assert "RD-1.10" in route.rationale
