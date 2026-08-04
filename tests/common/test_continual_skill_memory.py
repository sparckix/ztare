from dataclasses import replace

import pytest

from ztare.common.continual_skill_memory import (
    ContinualSkillMemory,
    IntrinsicLearningSignal,
    consumable_skill_revision_sha256s,
    decision_option_family_sha256,
    empty_continual_skill_memory,
    judge_decision_option_task_credit,
    judge_effect_option_task_credit,
    judge_intrinsic_revision,
    judge_process_prefix,
    load_continual_skill_memory,
    merge_guarded_skill_library,
    process_tokens_for_trace,
    propose_skill_transport,
    rehydrate_validated_skill_programs,
    record_library_quotient_transport,
    record_intrinsic_signal,
    record_task_decision_experience,
    record_task_choice_experience,
    record_task_experience,
    save_continual_skill_memory,
    validate_skill_transport,
)
from ztare.common.equivariance import stable_sha256
from ztare.common.guarded_skill_compiler import (
    GuardedActionTrace,
    GuardedTraceTransition,
    compile_guarded_execution_plan,
    compile_guarded_skill_library,
)


def _step(
    source,
    operation,
    successor,
    effect,
    evidence_ref,
    *,
    boundary_kind="",
):
    return GuardedTraceTransition(
        source=source,
        operation=operation,
        successor=successor,
        effect=effect,
        evidence_ref=evidence_ref,
        boundary_kind=boundary_kind,
    )


def _source_traces():
    clean_one = GuardedActionTrace(
        trace_ref="source-clean-1",
        transitions=(
            _step("one-0", "a", "stage-1", "ea", "one#0"),
            _step("stage-1", "b", "stage-2", "eb", "one#1"),
            _step("stage-2", "c", "done", "ec", "one#2"),
            _step("done", "x", "tail-1", "ex", "one#3"),
        ),
    )
    clean_two = GuardedActionTrace(
        trace_ref="source-clean-2",
        transitions=(
            _step("two-0", "a", "stage-1", "ea", "two#0"),
            _step("stage-1", "b", "stage-2", "eb", "two#1"),
            _step("stage-2", "c", "done", "ec", "two#2"),
            _step("done", "y", "tail-2", "ey", "two#3"),
        ),
    )
    side_exit = GuardedActionTrace(
        trace_ref="source-exit",
        transitions=(
            _step("bad-0", "a", "stage-1", "ea", "bad#0"),
            _step("stage-1", "b", "stage-2", "eb", "bad#1"),
            _step(
                "stage-2",
                "c",
                None,
                None,
                "bad#2",
                boundary_kind="typed_stop",
            ),
        ),
    )
    clean_three = GuardedActionTrace(
        trace_ref="source-clean-3",
        transitions=(
            _step("three-0", "a", "stage-1", "ea", "three#0"),
            _step("stage-1", "b", "stage-2", "eb", "three#1"),
            _step("stage-2", "c", "done", "ec", "three#2"),
            _step("done", "z", "tail-3", "ez", "three#3"),
        ),
    )
    return clean_one, clean_two, side_exit, clean_three


def _source_libraries():
    one, two, side_exit, three = _source_traces()
    first = compile_guarded_skill_library(
        (one, two, side_exit),
        max_word_length=3,
    )
    second = compile_guarded_skill_library(
        (one, two, side_exit, three),
        max_word_length=3,
    )
    assert len(first.programs) == 1
    assert len(second.programs) == 1
    assert first.programs[0].operations == ("a", "b", "c")
    assert second.programs[0].operations == ("a", "b", "c")
    return first, second


def _quotient_pass_signal(program, family_sha, context_key, epoch):
    return IntrinsicLearningSignal(
        family_sha256=family_sha,
        revision_sha256=program.skill_sha256,
        context_sha256=stable_sha256(context_key),
        evidence_epoch_sha256=epoch,
        kind="quotient_transport",
        disposition="supports_reuse",
        measure_before=1,
        measure_after=0,
        evidence_refs=(f"{epoch}:transport",),
    )


def test_intrinsic_judgment_compounds_across_revisions_without_identity_drift():
    first, second = _source_libraries()
    context = ("context", 1)
    memory = merge_guarded_skill_library(
        empty_continual_skill_memory(),
        first,
        operation_namespace="source-actions",
        context_key=context,
    )
    first_program = first.programs[0]
    family_sha = first_program.structural_sha256("source-actions")
    memory = record_intrinsic_signal(
        memory,
        _quotient_pass_signal(
            first_program,
            family_sha,
            context,
            "epoch-one",
        ),
    )
    admitted = judge_intrinsic_revision(
        memory,
        family_sha256=family_sha,
        revision_sha256=first_program.skill_sha256,
        context_key=context,
    )
    assert admitted.status == "reuse_admitted"

    counterexample = IntrinsicLearningSignal(
        family_sha256=family_sha,
        revision_sha256=first_program.skill_sha256,
        context_sha256=stable_sha256(context),
        evidence_epoch_sha256="epoch-one",
        kind="cegar_counterexample",
        disposition="requires_refinement",
        failed_step=1,
        evidence_refs=("cegar#1",),
    )
    memory = record_intrinsic_signal(memory, counterexample)
    refine = judge_intrinsic_revision(
        memory,
        family_sha256=family_sha,
        revision_sha256=first_program.skill_sha256,
        context_key=context,
        planned_total_steps=6,
    )
    assert refine.status == "refine_early"
    assert refine.failed_step == 1
    assert refine.avoided_tail_steps == 4

    memory = merge_guarded_skill_library(
        memory,
        second,
        operation_namespace="source-actions",
        context_key=context,
    )
    second_program = second.programs[0]
    assert second_program.skill_sha256 != first_program.skill_sha256
    assert (
        second_program.structural_sha256("source-actions")
        == family_sha
    )
    family = memory.family(family_sha)
    assert family is not None
    assert family.revision_sha256s == tuple(sorted((
        first_program.skill_sha256,
        second_program.skill_sha256,
    )))

    memory = record_intrinsic_signal(
        memory,
        _quotient_pass_signal(
            second_program,
            family_sha,
            context,
            "epoch-two",
        ),
    )
    repaired = judge_intrinsic_revision(
        memory,
        family_sha256=family_sha,
        revision_sha256=second_program.skill_sha256,
        context_key=context,
    )
    assert repaired.status == "reuse_admitted"
    assert (
        judge_intrinsic_revision(
            memory,
            family_sha256=family_sha,
            revision_sha256=first_program.skill_sha256,
            context_key=context,
        ).status
        == "refine_early"
    )


def test_commuting_quotient_admits_revision_and_cegar_revokes_consumption():
    first, _second = _source_libraries()
    program = first.programs[0]
    context = ("context", "consumer")
    namespace = "source-actions"
    memory = merge_guarded_skill_library(
        empty_continual_skill_memory(),
        first,
        operation_namespace=namespace,
        context_key=context,
    )

    class Quotient:
        passed_section = True
        passed_transport = True
        source_fiber_count = 9
        class_count = 4
        sha256 = "quotient-pass"

    memory, transport = record_library_quotient_transport(
        memory,
        first,
        operation_namespace=namespace,
        context_key=context,
        predictive_quotient=Quotient(),
    )
    allowed, receipt = consumable_skill_revision_sha256s(
        memory,
        first,
        operation_namespace=namespace,
        context_key=context,
    )
    assert transport["status"] == "admitted"
    assert allowed == frozenset({program.skill_sha256})
    assert receipt["admitted_revision_count"] == 1

    memory = record_intrinsic_signal(
        memory,
        IntrinsicLearningSignal(
            family_sha256=program.structural_sha256(namespace),
            revision_sha256=program.skill_sha256,
            context_sha256=stable_sha256(context),
            evidence_epoch_sha256="quotient-pass",
            kind="cegar_counterexample",
            disposition="requires_refinement",
            failed_step=1,
            evidence_refs=("runtime#counterexample",),
        ),
    )
    allowed, receipt = consumable_skill_revision_sha256s(
        memory,
        first,
        operation_namespace=namespace,
        context_key=context,
    )
    assert allowed == frozenset()
    assert receipt["judgments"][0]["status"] == "refine_early"


def test_external_outcome_only_calibrates_task_credit_after_matched_contrast():
    memory = empty_continual_skill_memory()
    positive_tokens = ("prepare", "skill:advance", "commit")
    memory = record_task_experience(
        memory,
        task_contract_sha256="task-one",
        trace_ref="positive",
        outcome="attained",
        process_tokens=positive_tokens,
        evidence_ref="authority#positive",
        context_key="context",
    )
    assert memory.credit_witnesses == ()
    assert judge_process_prefix(
        memory,
        task_contract_sha256="task-one",
        process_tokens=positive_tokens,
    ).status == "unknown"

    memory = record_task_experience(
        memory,
        task_contract_sha256="task-one",
        trace_ref="open",
        outcome="open",
        process_tokens=("prepare", "commit"),
        evidence_ref="authority#open",
        context_key="context",
    )
    progress = judge_process_prefix(
        memory,
        task_contract_sha256="task-one",
        process_tokens=positive_tokens,
    )
    assert progress.status == "progress_supported"
    assert progress.decisive_token == "skill:advance"
    credited = judge_effect_option_task_credit(
        memory,
        effect_option_family_sha256="effect-option-advance",
        task_contract_sha256="task-one",
        source_family_sha256s=("advance",),
    )
    assert credited.status == "uncredited"
    assert credited.enable_support == 0

    memory = record_task_experience(
        memory,
        task_contract_sha256="task-two",
        trace_ref="effect-positive",
        outcome="attained",
        process_tokens=(
            "prepare",
            "effect_option:effect-option-advance",
            "commit",
        ),
        evidence_ref="authority#effect-positive",
        context_key="context",
    )
    memory = record_task_experience(
        memory,
        task_contract_sha256="task-two",
        trace_ref="effect-open",
        outcome="open",
        process_tokens=("prepare", "commit"),
        evidence_ref="authority#effect-open",
        context_key="context",
    )
    effect_credited = judge_effect_option_task_credit(
        memory,
        effect_option_family_sha256="effect-option-advance",
        task_contract_sha256="task-two",
        source_family_sha256s=("advance",),
    )
    assert effect_credited.status == "task_credited"
    assert effect_credited.enable_support == 1
    assert effect_credited.to_receipt()["authority"] == (
        "matched_external_outcome_contrasts_only"
    )
    uncredited = judge_effect_option_task_credit(
        memory,
        effect_option_family_sha256="effect-option-other",
        task_contract_sha256="task-one",
        source_family_sha256s=("other",),
    )
    assert uncredited.status == "uncredited"

    memory = record_task_experience(
        memory,
        task_contract_sha256="task-one",
        trace_ref="failed",
        outcome="failed",
        process_tokens=(
            "prepare",
            "hazard:detour",
            "skill:advance",
            "commit",
        ),
        evidence_ref="authority#failed",
        context_key="context",
    )
    failure = judge_process_prefix(
        memory,
        task_contract_sha256="task-one",
        process_tokens=("prepare", "hazard:detour"),
        planned_total_steps=5,
    )
    assert failure.status == "fail_early"
    assert failure.decisive_index == 1
    assert failure.avoided_tail_steps == 3


def test_effect_credit_requires_same_context_and_accepts_one_substitution():
    memory = empty_continual_skill_memory()
    memory = record_task_experience(
        memory,
        task_contract_sha256="task-substitution",
        trace_ref="positive",
        outcome="attained",
        process_tokens=(
            "primitive:prepare",
            "effect_option:advance",
            "primitive:commit",
        ),
        evidence_ref="authority#positive",
        context_key=("same-context", 1),
    )
    memory = record_task_experience(
        memory,
        task_contract_sha256="task-substitution",
        trace_ref="contrast",
        outcome="open",
        process_tokens=(
            "primitive:prepare",
            "effect_option:detour",
            "primitive:commit",
        ),
        evidence_ref="authority#contrast",
        context_key=("same-context", 1),
    )

    assert judge_effect_option_task_credit(
        memory,
        effect_option_family_sha256="advance",
        task_contract_sha256="task-substitution",
        source_family_sha256s=("motor-a",),
    ).status == "task_credited"
    assert judge_effect_option_task_credit(
        memory,
        effect_option_family_sha256="detour",
        task_contract_sha256="task-substitution",
        source_family_sha256s=("motor-b",),
    ).status == "task_hazard"

    separated = empty_continual_skill_memory()
    separated = record_task_experience(
        separated,
        task_contract_sha256="task-context",
        trace_ref="positive",
        outcome="attained",
        process_tokens=("primitive:prepare", "effect_option:advance"),
        evidence_ref="authority#positive",
        context_key=("context", "left"),
    )
    separated = record_task_experience(
        separated,
        task_contract_sha256="task-context",
        trace_ref="contrast",
        outcome="open",
        process_tokens=("primitive:prepare",),
        evidence_ref="authority#contrast",
        context_key=("context", "right"),
    )

    assert separated.credit_witnesses == ()
    assert judge_effect_option_task_credit(
        separated,
        effect_option_family_sha256="advance",
        task_contract_sha256="task-context",
        source_family_sha256s=("motor-a",),
    ).status == "uncredited"


def test_choice_local_credit_requires_same_context_choice_set_and_controller(
    tmp_path,
):
    memory = empty_continual_skill_memory()
    shared = {
        "task_contract_sha256": "task-choice",
        "choice_context_sha256": "same-choice-context",
        "continuation_context_sha256": "same-controller",
        "available_effect_option_family_sha256s": (
            "advance",
            "detour",
        ),
    }
    memory = record_task_choice_experience(
        memory,
        **shared,
        trace_ref="positive",
        choice_index=0,
        outcome="attained",
        chosen_effect_option_family_sha256="advance",
        chosen_effect_option_variant_sha256="advance-red-context",
        evidence_ref="authority#positive",
    )
    memory = record_task_choice_experience(
        memory,
        **shared,
        trace_ref="contrast",
        choice_index=0,
        outcome="open",
        chosen_effect_option_family_sha256="detour",
        chosen_effect_option_variant_sha256="detour-red-context",
        evidence_ref="authority#contrast",
    )

    assert len(memory.task_choice_experiences) == 2
    assert judge_effect_option_task_credit(
        memory,
        effect_option_family_sha256="advance",
        task_contract_sha256="task-choice",
        source_family_sha256s=("motor-a",),
    ).status == "task_credited"
    assert judge_effect_option_task_credit(
        memory,
        effect_option_family_sha256="detour",
        task_contract_sha256="task-choice",
        source_family_sha256s=("motor-b",),
    ).status == "task_hazard"

    path = tmp_path / "choice-memory.json"
    save_continual_skill_memory(path, memory)
    assert load_continual_skill_memory(path) == memory

    separated = empty_continual_skill_memory()
    separated = record_task_choice_experience(
        separated,
        **shared,
        trace_ref="positive",
        choice_index=0,
        outcome="attained",
        chosen_effect_option_family_sha256="advance",
        chosen_effect_option_variant_sha256="advance-red-context",
        evidence_ref="authority#positive",
    )
    separated = record_task_choice_experience(
        separated,
        **{
            **shared,
            "continuation_context_sha256": "different-controller",
        },
        trace_ref="contrast",
        choice_index=0,
        outcome="open",
        chosen_effect_option_family_sha256="detour",
        chosen_effect_option_variant_sha256="detour-red-context",
        evidence_ref="authority#contrast",
    )
    assert separated.credit_witnesses == ()


def test_controller_decision_credit_is_exactly_scoped_and_persistent(
    tmp_path,
):
    namespace = "acquisition-protocols"
    advance = decision_option_family_sha256(namespace, "advance")
    detour = decision_option_family_sha256(namespace, "detour")
    available = tuple(sorted((advance, detour)))
    shared = {
        "task_contract_sha256": "task-decision",
        "decision_namespace": namespace,
        "choice_context_sha256": "same-choice-context",
        "continuation_context_sha256": "same-controller",
        "available_option_family_sha256s": available,
    }
    memory = record_task_decision_experience(
        empty_continual_skill_memory(),
        **shared,
        trace_ref="positive",
        choice_index=0,
        outcome="attained",
        chosen_option_family_sha256=advance,
        chosen_option_variant_sha256="advance-variant",
        evidence_ref="authority#positive",
    )
    untested = judge_decision_option_task_credit(
        memory,
        decision_namespace=namespace,
        option_family_sha256=detour,
        task_contract_sha256="task-decision",
        choice_context_sha256="same-choice-context",
        continuation_context_sha256="same-controller",
        available_option_family_sha256s=available,
    )
    assert untested.contrast_priority == 0
    memory = record_task_decision_experience(
        memory,
        **shared,
        trace_ref="contrast",
        choice_index=0,
        outcome="open",
        chosen_option_family_sha256=detour,
        chosen_option_variant_sha256="detour-variant",
        evidence_ref="authority#contrast",
    )

    common_judgment = {
        "memory": memory,
        "decision_namespace": namespace,
        "task_contract_sha256": "task-decision",
        "choice_context_sha256": "same-choice-context",
        "continuation_context_sha256": "same-controller",
        "available_option_family_sha256s": available,
    }
    assert judge_decision_option_task_credit(
        **common_judgment,
        option_family_sha256=advance,
    ).preference == 1
    assert judge_decision_option_task_credit(
        **common_judgment,
        option_family_sha256=detour,
    ).preference == -1
    assert judge_decision_option_task_credit(
        **{
            **common_judgment,
            "continuation_context_sha256": "different-controller",
        },
        option_family_sha256=advance,
    ).status == "uncredited"

    path = tmp_path / "decision-memory.json"
    save_continual_skill_memory(path, memory)
    assert load_continual_skill_memory(path) == memory

    unresolved = record_task_decision_experience(
        empty_continual_skill_memory(),
        **shared,
        trace_ref="open-first",
        choice_index=0,
        outcome="open",
        chosen_option_family_sha256=advance,
        chosen_option_variant_sha256="advance-open-variant",
        evidence_ref="authority#open",
    )
    assert judge_decision_option_task_credit(
        unresolved,
        decision_namespace=namespace,
        option_family_sha256=detour,
        task_contract_sha256="task-decision",
        choice_context_sha256="same-choice-context",
        continuation_context_sha256="same-controller",
        available_option_family_sha256s=available,
    ).contrast_priority == 1


def test_explicit_transport_needs_one_local_guard_witness_and_preserves_memory(
    tmp_path,
):
    first, _second = _source_libraries()
    source_program = first.programs[0]
    source_context = ("source", 1)
    memory = merge_guarded_skill_library(
        empty_continual_skill_memory(),
        first,
        operation_namespace="source-actions",
        context_key=source_context,
    )
    source_family = source_program.structural_sha256("source-actions")
    source_before = memory.family(source_family)

    proposal = propose_skill_transport(
        memory,
        source_program=source_program,
        source_operation_namespace="source-actions",
        target_operation_namespace="target-actions",
        operation_map={"a": "left", "b": "lift", "c": "release"},
    )
    assert proposal.status == "local_guard_validation_required"
    assert proposal.to_receipt()["task_outcome_transferred"] is False

    target_trace = GuardedActionTrace(
        trace_ref="target-one-shot",
        transitions=(
            _step("target-0", "left", "target-1", "te0", "target#0"),
            _step("target-1", "lift", "target-2", "te1", "target#1"),
            _step(
                "target-2",
                "release",
                "target-3",
                "te2",
                "target#2",
            ),
        ),
    )
    fresh_target = compile_guarded_skill_library(
        (target_trace,),
        min_variant_support=1,
        max_word_length=3,
    )
    assert fresh_target.programs == ()

    memory, validated = validate_skill_transport(
        memory,
        proposal,
        validation_trace=target_trace,
        context_key=("target", 1),
    )
    assert validated.admits("target-0")
    assert not validated.admits("unseen-target")
    assert validated.to_receipt()["task_outcome_transferred"] is False
    assert memory.family(source_family) == source_before
    target_family = memory.family(proposal.target_family_sha256)
    assert target_family is not None
    assert target_family.transferred_from_sha256s == (source_family,)
    assert target_family.independent_trace_support == 1
    assert memory.task_experiences == ()

    target_judgment = judge_intrinsic_revision(
        memory,
        family_sha256=target_family.family_sha256,
        revision_sha256=target_family.revision_sha256s[0],
        context_key=("target", 1),
    )
    assert target_judgment.status == "validated_transfer"

    path = tmp_path / "continual_skill_memory.json"
    save_continual_skill_memory(path, memory)
    restored = load_continual_skill_memory(path)
    assert restored.to_dict() == memory.to_dict()
    assert restored.memory_sha256 == memory.memory_sha256
    assert len(restored.skill_transports) == 1
    transport = restored.skill_transports[0]
    assert transport.source_revision_sha256 == source_program.skill_sha256
    assert transport.target_revision_sha256 == validated.program.skill_sha256

    rehydrated = rehydrate_validated_skill_programs(
        restored,
        (target_trace,),
        operation_namespace="target-actions",
        context_key=("target", 1),
    )
    assert rehydrated == (validated.program,)
    assert rehydrated[0].admission_authority == "validated_transport"
    allowed, receipt = consumable_skill_revision_sha256s(
        restored,
        fresh_target,
        operation_namespace="target-actions",
        context_key=("target", 1),
        additional_programs=rehydrated,
    )
    assert allowed == frozenset({validated.program.skill_sha256})
    assert receipt["transported_program_count"] == 1
    relation = {
        (transition.source, transition.operation): transition.successor
        for transition in target_trace.transitions
    }
    plan = compile_guarded_execution_plan(
        fresh_target,
        start_key="target-0",
        operations=target_trace.operations,
        transition=lambda source, operation: relation.get(
            (source, operation)
        ),
        allowed_skill_sha256s=allowed,
        additional_programs=rehydrated,
    )
    assert plan.status == "compiled_plan"
    assert plan.skill_token_count == 1
    assert plan.token_savings == 2
    assert plan.exact_expansion
    uncredited_plan = compile_guarded_execution_plan(
        fresh_target,
        start_key="target-0",
        operations=target_trace.operations,
        transition=lambda source, operation: relation.get(
            (source, operation)
        ),
        allowed_skill_sha256s=allowed,
        allowed_skill_invocations=frozenset(),
        additional_programs=rehydrated,
    )
    assert uncredited_plan.status == "primitive_plan"
    credited_plan = compile_guarded_execution_plan(
        fresh_target,
        start_key="target-0",
        operations=target_trace.operations,
        transition=lambda source, operation: relation.get(
            (source, operation)
        ),
        allowed_skill_sha256s=allowed,
        allowed_skill_invocations=frozenset({(
            validated.program.skill_sha256,
            stable_sha256("target-0"),
        )}),
        additional_programs=rehydrated,
    )
    assert credited_plan.skill_token_count == 1

    revoked = record_intrinsic_signal(
        restored,
        IntrinsicLearningSignal(
            family_sha256=target_family.family_sha256,
            revision_sha256=validated.program.skill_sha256,
            context_sha256=stable_sha256(("target", 1)),
            evidence_epoch_sha256="target-counterexample",
            kind="cegar_counterexample",
            disposition="requires_refinement",
            failed_step=0,
            evidence_refs=("target#counterexample",),
        ),
    )
    revoked_allowed, revoked_receipt = consumable_skill_revision_sha256s(
        revoked,
        fresh_target,
        operation_namespace="target-actions",
        context_key=("target", 1),
        additional_programs=rehydrated,
    )
    assert revoked_allowed == frozenset()
    assert revoked_receipt["judgments"][0]["status"] == "refine_early"
    fallback = compile_guarded_execution_plan(
        fresh_target,
        start_key="target-0",
        operations=target_trace.operations,
        transition=lambda source, operation: relation.get(
            (source, operation)
        ),
        allowed_skill_sha256s=revoked_allowed,
        additional_programs=rehydrated,
    )
    assert fallback.status == "primitive_plan"
    assert fallback.skill_token_count == 0
    assert fallback.token_savings == 0
    assert fallback.exact_expansion


def test_transport_rejects_operation_collapse_and_lineage_drift():
    first, _second = _source_libraries()
    source_program = first.programs[0]
    memory = merge_guarded_skill_library(
        empty_continual_skill_memory(),
        first,
        operation_namespace="source-actions",
        context_key=("source", 1),
    )
    with pytest.raises(ValueError, match="injective"):
        propose_skill_transport(
            memory,
            source_program=source_program,
            source_operation_namespace="source-actions",
            target_operation_namespace="target-actions",
            operation_map={
                "a": "collapsed",
                "b": "collapsed",
                "c": "release",
            },
        )

    proposal = propose_skill_transport(
        memory,
        source_program=source_program,
        source_operation_namespace="source-actions",
        target_operation_namespace="target-actions",
        operation_map={"a": "left", "b": "lift", "c": "release"},
    )
    target_trace = GuardedActionTrace(
        trace_ref="target-lineage-check",
        transitions=(
            _step("target-0", "left", "target-1", "te0", "target#0"),
            _step("target-1", "lift", "target-2", "te1", "target#1"),
            _step("target-2", "release", "target-3", "te2", "target#2"),
        ),
    )
    with pytest.raises(ValueError, match="source lineage"):
        validate_skill_transport(
            memory,
            replace(
                proposal,
                source_operation_namespace="drifted-source-actions",
            ),
            validation_trace=target_trace,
            context_key=("target", 1),
        )

    payload = memory.to_dict()
    payload["intrinsic_signals"][0]["revision_sha256"] = "orphan-revision"
    with pytest.raises(ValueError, match="intrinsic signal lineage"):
        ContinualSkillMemory.from_dict(payload)


def test_process_token_identity_survives_evidence_revision():
    first, second = _source_libraries()
    first_tokens = process_tokens_for_trace(
        first,
        trace_ref="source-clean-1",
        operation_namespace="source-actions",
    )
    second_tokens = process_tokens_for_trace(
        second,
        trace_ref="source-clean-1",
        operation_namespace="source-actions",
    )
    assert first_tokens == second_tokens
    assert first_tokens[0].startswith("skill:")
