from ztare.common.guarded_skill_compiler import (
    GuardedActionTrace,
    GuardedTraceTransition,
    compile_guarded_execution_plan,
    compile_guarded_skill_library,
)
from ztare.common.partial_action_system import (
    PartialActionObservation,
    build_partial_action_system,
)
from ztare.common.predictive_quotient import compile_predictive_quotient


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


def _compiler_fixture():
    clean_one = GuardedActionTrace(
        trace_ref="trace-clean-1",
        transitions=(
            _step("clean-1", "a", "stage-1", "ea", "clean-1#0"),
            _step("stage-1", "b", "stage-2", "eb", "clean-1#1"),
            _step("stage-2", "c", "done", "ec", "clean-1#2"),
            _step("done", "x", "tail-1", "ex", "clean-1#3"),
        ),
    )
    clean_two = GuardedActionTrace(
        trace_ref="trace-clean-2",
        transitions=(
            _step("clean-2", "a", "stage-1", "ea", "clean-2#0"),
            _step("stage-1", "b", "stage-2", "eb", "clean-2#1"),
            _step("stage-2", "c", "done", "ec", "clean-2#2"),
            _step("done", "y", "tail-2", "ey", "clean-2#3"),
        ),
    )
    unsafe = GuardedActionTrace(
        trace_ref="trace-side-exit",
        transitions=(
            _step("unsafe", "a", "stage-1", "ea", "exit#0"),
            _step("stage-1", "b", "stage-2", "eb", "exit#1"),
            _step(
                "stage-2",
                "c",
                None,
                None,
                "exit#2",
                boundary_kind="typed_stop",
            ),
        ),
    )
    return clean_one, clean_two, unsafe


def _bounded_path_option_count():
    observations = []
    for suffix in ("one", "two"):
        observations.extend((
            PartialActionObservation(
                f"q0-{suffix}",
                "a",
                f"q1-{suffix}",
                f"graph-{suffix}#0",
            ),
            PartialActionObservation(
                f"q1-{suffix}",
                "b",
                f"q2-{suffix}",
                f"graph-{suffix}#1",
            ),
            PartialActionObservation(
                f"q2-{suffix}",
                "c",
                f"q3-{suffix}",
                f"graph-{suffix}#2",
            ),
        ))
    system = build_partial_action_system(
        observations,
        project=lambda state: state,
        effect=lambda _source, operation, _successor, *_keys: (
            "effect",
            operation,
        ),
        projection_id="guarded-skill-baseline",
    )
    quotient = compile_predictive_quotient(
        system,
        operations=("a", "b", "c"),
        max_option_length=3,
    )
    return len(quotient.options)


def test_compiler_selects_a_guarded_generator_not_every_path():
    traces = _compiler_fixture()

    library = compile_guarded_skill_library(
        traces,
        min_word_length=2,
        max_word_length=3,
        min_variant_support=2,
    )

    assert library.exact_reconstruction
    assert library.compression_gain > 0
    assert len(library.programs) == 1
    assert len(library.programs) < _bounded_path_option_count()

    program = library.programs[0]
    assert program.operations == ("a", "b", "c")
    assert len(program.encoding_occurrence_sha256s) == 2
    assert len(program.variants) == 1
    assert program.variants[0].support == 2
    assert len(program.side_exits) == 1
    assert program.side_exits[0].failed_step == 2
    assert program.side_exits[0].boundary_kind == "typed_stop"
    assert program.side_exits[0].matched_prefix == ("a", "b")

    assert program.decide("clean-1").status == "compiled"
    assert program.decide("clean-2").status == "compiled"
    unsafe = program.decide("unsafe")
    assert unsafe.status == "primitive_fallback"
    assert unsafe.reason == "guard_conflict"
    unseen = program.decide("never-observed")
    assert unseen.status == "primitive_fallback"
    assert unseen.reason == "guard_unwitnessed"


def test_compiler_is_invariant_to_trace_order():
    traces = _compiler_fixture()

    forward = compile_guarded_skill_library(
        traces,
        max_word_length=3,
    )
    reverse = compile_guarded_skill_library(
        reversed(traces),
        max_word_length=3,
    )

    assert forward.to_receipt() == reverse.to_receipt()


def test_overlap_cannot_manufacture_description_length_gain():
    trace = GuardedActionTrace(
        trace_ref="overlap",
        transitions=(
            _step("s0", "a", "s1", "e", "overlap#0"),
            _step("s1", "a", "s2", "e", "overlap#1"),
            _step("s2", "a", "s3", "e", "overlap#2"),
        ),
    )

    library = compile_guarded_skill_library(
        (trace,),
        min_word_length=2,
        max_word_length=2,
        min_variant_support=1,
    )

    assert library.programs == ()
    assert library.compression_gain == 0
    assert library.exact_reconstruction


def test_boundary_operation_remains_in_lossless_trace_encoding():
    traces = _compiler_fixture()

    library = compile_guarded_skill_library(
        traces,
        max_word_length=3,
    )
    reconstructed = dict(library.reconstructed_operations_by_trace)

    assert reconstructed["trace-side-exit"] == ("a", "b", "c")
    assert reconstructed == dict(library.source_operations_by_trace)


def test_guarded_plan_uses_only_commuting_admitted_skill_tokens():
    library = compile_guarded_skill_library(
        _compiler_fixture(),
        max_word_length=3,
    )
    relation = {
        ("clean-1", "a"): "stage-1",
        ("stage-1", "b"): "stage-2",
        ("stage-2", "c"): "done",
        ("done", "x"): "tail",
        ("new-start", "a"): "stage-1",
    }
    transition = lambda source, operation: relation.get((source, operation))

    compiled = compile_guarded_execution_plan(
        library,
        start_key="clean-1",
        operations=("a", "b", "c", "x"),
        transition=transition,
    )
    unseen = compile_guarded_execution_plan(
        library,
        start_key="new-start",
        operations=("a", "b", "c"),
        transition=transition,
    )

    assert compiled.status == "compiled_plan"
    assert compiled.exact_expansion
    assert compiled.skill_token_count == 1
    assert compiled.token_savings == 2
    assert compiled.final_key == "tail"
    assert [token.kind for token in compiled.tokens] == [
        "skill",
        "primitive",
    ]

    assert unseen.status == "primitive_plan"
    assert unseen.exact_expansion
    assert unseen.skill_token_count == 0


def test_guarded_plan_consumes_only_intrinsically_allowed_revisions():
    library = compile_guarded_skill_library(
        _compiler_fixture(),
        max_word_length=3,
    )
    relation = {
        ("clean-1", "a"): "stage-1",
        ("stage-1", "b"): "stage-2",
        ("stage-2", "c"): "done",
    }
    transition = lambda source, operation: relation.get((source, operation))

    blocked = compile_guarded_execution_plan(
        library,
        start_key="clean-1",
        operations=("a", "b", "c"),
        transition=transition,
        allowed_skill_sha256s=frozenset(),
    )
    admitted = compile_guarded_execution_plan(
        library,
        start_key="clean-1",
        operations=("a", "b", "c"),
        transition=transition,
        allowed_skill_sha256s=frozenset({
            library.programs[0].skill_sha256,
        }),
    )

    assert blocked.status == "primitive_plan"
    assert blocked.skill_token_count == 0
    assert admitted.status == "compiled_plan"
    assert admitted.skill_token_count == 1


def test_guarded_plan_fails_before_crossing_undefined_relation():
    library = compile_guarded_skill_library(
        _compiler_fixture(),
        max_word_length=3,
    )
    relation = {
        ("unsafe", "a"): "stage-1",
        ("stage-1", "b"): "stage-2",
    }

    plan = compile_guarded_execution_plan(
        library,
        start_key="unsafe",
        operations=("a", "b", "c"),
        transition=lambda source, operation: relation.get(
            (source, operation)
        ),
    )

    assert plan.status == "primitive_route_undefined"
    assert plan.failed_operation_index == 2
    assert plan.tokens == ()
