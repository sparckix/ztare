from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path

from ztare.strategy.jaggedthoughts import (
    CandidateEvaluation,
    ClaimDisposition,
    FrontierScope,
    Neighborhood,
    OperatorGrammar,
    ProgramInterpretation,
    RepresentationAudit,
    StrategicClaim,
    TypedOperator,
    TypedTerminal,
    TypedValue,
    compile_jaggedthoughts_frontier,
    enumerate_typed_programs,
    interpret_program,
)
from ztare.strategy.profile import compile_profile, compile_profile_file, load_profile
from ztare.strategy.representation import challenge_representation
from ztare.strategy.report import render_strategy_report


DEMO = Path("examples/jaggedthoughts/integrated_option_demo.yaml")


def test_recursive_enumeration_is_typed_deterministic_and_budgeted() -> None:
    base = compile_profile_file(DEMO).grammar
    grammar = OperatorGrammar(
        base.grammar_id,
        base.version,
        base.terminals,
        base.operators + (
            TypedOperator("reposition", ("StrategyOption",), "StrategyOption"),
            TypedOperator("ill-typed", ("MissingType",), "StrategyOption"),
        ),
    )
    first = enumerate_typed_programs(grammar, max_depth=2, max_programs=100)
    replay = enumerate_typed_programs(grammar, max_depth=2, max_programs=100)
    targets = first.programs_of_type("StrategyOption")

    assert first.enumeration_digest == replay.enumeration_digest
    assert len(targets) == 16
    assert {program.depth for program in targets} == {1, 2}
    assert all(program.operator_id != "ill-typed" for program in targets)

    option = next(program for program in targets if program.depth == 1)
    interpretation = ProgramInterpretation(
        "fixture-semantics",
        grammar.grammar_digest,
        {
            terminal.terminal_id: TypedValue(
                terminal.output_type,
                terminal.terminal_id,
            )
            for terminal in grammar.terminals
        },
        {
            "integrate-option": lambda values: TypedValue(
                "StrategyOption",
                tuple(value.value for value in values),
            ),
        },
    )
    assert interpret_program(
        option,
        grammar=grammar,
        interpretation=interpretation,
    ).value_type == "StrategyOption"

    cut = enumerate_typed_programs(grammar, max_depth=2, max_programs=7)
    assert cut.exhausted_within_scope is False
    assert cut.residuals[0].kind == "program_budget_exhausted"

    versioned = enumerate_typed_programs(
        replace(grammar, version="2"),
        max_depth=2,
        max_programs=100,
    )
    assert {program.program_id for program in first.programs}.isdisjoint(
        {program.program_id for program in versioned.programs}
    )


def test_demo_compiles_jagged_peaks_and_keeps_representation_debt_visible() -> None:
    first = compile_profile_file(DEMO)
    replay = compile_profile_file(DEMO)

    assert first.summary() == {
        "profile_id": "jaggedthoughts.demo.integrated-option",
        "title": "Integrated service-packaging decision",
        "decision_question": (
            "Which packaging architecture remains non-dominated across the "
            "base case and a distribution disruption?"
        ),
        "owner": "Strategy team",
        "as_of": "2026-08-08",
        "grammar_digest": first.grammar.grammar_digest,
        "enumeration_digest": first.enumeration.enumeration_digest,
        "certificate_sha256": first.certificate.certificate_sha256,
        "target_program_count": 8,
        "frontier_count": 3,
        "local_peak_count": 3,
        "residual_program_count": 0,
        "scope_closed": True,
        "decision_closed": False,
        "representation_status": "unassessed",
        "source_count": 1,
        "bound_evidence_count": 8,
        "evaluation_kind": "factor_graph",
        "exploration_probe_count": 10,
        "pivotal_probe_count": 7,
    }
    assert first.certificate.certificate_sha256 == (
        replay.certificate.certificate_sha256
    )
    certificate = first.certificate
    partition = (
        set(certificate.frontier_program_ids)
        | {w.dominated_program_id for w in certificate.dominated}
        | {w.program_id for w in certificate.infeasible}
        | {w.program_id for w in certificate.equivalent}
        | set(certificate.residual_program_ids)
    )
    assert partition == set(certificate.target_program_ids)
    report = render_strategy_report(first)
    assert "Scenario breakdown for frontier options" in report
    assert "Next-question agenda" in report
    assert "sources/demo_assumptions.md" in report


def _claim_fixture(status: str, audit: RepresentationAudit):
    claim = StrategicClaim("claim.demand", "external", "Demand clears the floor.")
    grammar = OperatorGrammar(
        "jt.claim-fixture",
        "1",
        (
            TypedTerminal("arena", "Arena", (claim.claim_id,)),
            TypedTerminal("channel", "Channel"),
        ),
        (TypedOperator("integrate", ("Arena", "Channel"), "Option"),),
    )
    enumeration = enumerate_typed_programs(grammar, max_depth=1, max_programs=10)
    program = enumeration.programs_of_type("Option")[0]
    neighborhood = Neighborhood("single", ())
    scope = FrontierScope(
        grammar.grammar_id,
        grammar.version,
        grammar.grammar_digest,
        "Option",
        1,
        10,
        "model",
        "fixed",
        "epoch",
        ("value",),
        neighborhood.neighborhood_id,
    )
    evaluation = CandidateEvaluation(
        program.program_id,
        (1.0,),
        ("behavior",),
        ("fixture://evaluation",),
    )
    return compile_jaggedthoughts_frontier(
        scope=scope,
        enumeration=enumeration,
        claims=(claim,),
        claim_dispositions=(ClaimDisposition(
            claim.claim_id,
            status,
            f"fixture://claim/{status}",
        ),),
        evaluations=(evaluation,),
        neighborhood=neighborhood,
        representation_audit=audit,
    )


def test_claim_and_representation_boundaries_control_the_two_closures() -> None:
    passed = RepresentationAudit("audit", "passed", evidence_refs=("audit://1",))
    unresolved = _claim_fixture("unresolved", passed)
    refuted = _claim_fixture("refuted", passed)
    unassessed = _claim_fixture("supported", RepresentationAudit("audit.open"))
    complete = _claim_fixture("supported", passed)

    assert unresolved.scope_closed is False
    assert unresolved.residual_program_ids
    assert refuted.scope_closed is True and refuted.infeasible
    assert unassessed.scope_closed is True and unassessed.decision_closed is False
    assert complete.scope_closed is True and complete.decision_closed is True


def test_challenger_grammar_exposes_only_novel_union_frontier_behavior() -> None:
    baseline = compile_profile_file(DEMO)
    payload = copy.deepcopy(dict(load_profile(DEMO)))
    payload["profile_id"] = "jaggedthoughts.demo.expanded"
    payload["grammar"]["version"] = "2"
    payload["grammar"]["terminals"].append({
        "id": "arena.platform",
        "type": "Arena",
        "description": "A platform-mediated arena.",
    })
    for scenario in payload["evaluation"]["scenarios"]:
        evidence_ref = scenario["evidence_refs"][0]
        scenario["factors"].append({
            "id": f"{scenario['id']}.platform-direct-subscription",
            "requires": [
                "arena.platform",
                "channel.direct",
                "economics.subscription",
            ],
            "delta": [20, 20],
            "evidence_refs": [evidence_ref],
        })
    challenge = challenge_representation(
        challenge_id="fixture-expanded-grammar",
        baseline=baseline,
        challenger=compile_profile(payload, source_root=DEMO.parent),
    )

    assert challenge.summary()["novel_behavior_count"] == 4
    assert challenge.summary()["material_frontier_behavior_count"] == 1
    assert challenge.representation_status == "residual"
    assert challenge.to_representation_audit().status == "residual"
