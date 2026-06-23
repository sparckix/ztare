from __future__ import annotations

from ztare.orchestrator.prompt import primitive_class_history_packet
from ztare.research_director.primitive_class_rotation import (
    cross_substrate_primitive_class_ledger_path,
    maybe_track_primitive_class_rotation,
    read_cross_substrate_primitive_classes,
    should_track_primitive_class_proposal,
    summarize_explored_primitive_classes,
)


def test_declaration_detection_is_case_tolerant_and_conservative():
    assert should_track_primitive_class_proposal("mechanism = propose_new_primitive_class")
    assert should_track_primitive_class_proposal("## Structural Mutation: ACRR")
    assert should_track_primitive_class_proposal("CATEGORY SWITCH: residual maps")
    assert should_track_primitive_class_proposal("## Primitive: collision sieve")
    assert should_track_primitive_class_proposal("## Architectural Primitive: receipt compiler")
    assert should_track_primitive_class_proposal("## Gate: residual boundary detector")
    assert should_track_primitive_class_proposal("## Decomposition: class factor split")
    assert should_track_primitive_class_proposal("## Scaling Law: sparse tail curve")
    assert not should_track_primitive_class_proposal(
        "we should perhaps consider a category switch later"
    )
    assert not should_track_primitive_class_proposal(
        "we might need a primitive or gate after this tactical patch"
    )
    assert not should_track_primitive_class_proposal("small tactical patch")


def test_disabled_tracking_does_not_write(tmp_path):
    result = maybe_track_primitive_class_rotation(
        rubric_data={"enable_primitive_class_rotation": False},
        project_dir=tmp_path,
        run_id="run-1",
        iter_index=1,
        thesis_text="## Structural Mutation: ACRR",
        score=10.0,
        use_llm=False,
    )

    assert result.reason == "disabled"
    assert result.tracked is False
    assert not (tmp_path / "workspace" / "explored_primitive_classes.jsonl").exists()


def test_enabled_without_declaration_does_not_write(tmp_path):
    result = maybe_track_primitive_class_rotation(
        rubric_data={"enable_primitive_class_rotation": True},
        project_dir=tmp_path,
        run_id="run-1",
        iter_index=1,
        thesis_text="A normal refinement pass.",
        score=10.0,
        use_llm=False,
    )

    assert result.reason == "no_primitive_class_declaration"
    assert result.should_track is False
    assert not (tmp_path / "workspace" / "explored_primitive_classes.jsonl").exists()


def test_structural_mutation_is_recorded_for_in_loop_and_rd_consumers(tmp_path):
    result = maybe_track_primitive_class_rotation(
        rubric_data={
            "enable_primitive_class_rotation": True,
            "cage_meta": {"class": "audit"},
        },
        project_dir=tmp_path,
        run_id="run-1",
        iter_index=2,
        thesis_text=(
            "## Structural Mutation: ACRR\n"
            "mechanism = propose_new_primitive_class\n"
        ),
        score=72.0,
        use_llm=False,
    )

    packet = primitive_class_history_packet(
        {"enable_primitive_class_rotation": True},
        project_dir=tmp_path,
    )
    summary = summarize_explored_primitive_classes(tmp_path)
    ledger = tmp_path / "workspace" / "explored_primitive_classes.jsonl"

    assert result.tracked is True
    assert result.class_name == "ACRR"
    assert ledger.exists()
    ledger_text = ledger.read_text()
    assert '"iter": 2' in ledger_text
    assert '"outcome": "judged_candidate"' in ledger_text
    assert "ACRR" in packet
    assert "best score 72.0" in packet
    assert "outcomes: judged_candidate=1" in packet
    assert summary["per_class"]["ACRR"]["count"] == 1
    assert summary["per_class"]["ACRR"]["best_score"] == 72.0
    assert summary["per_class"]["ACRR"]["outcomes"] == {"judged_candidate": 1}


def test_heading_only_primitive_class_move_is_recorded(tmp_path):
    result = maybe_track_primitive_class_rotation(
        rubric_data={
            "enable_primitive_class_rotation": True,
            "cage_meta": {"class": "audit"},
        },
        project_dir=tmp_path,
        run_id="run-heading",
        iter_index=4,
        thesis_text=(
            "## Gate: residual boundary detector\n"
            "Use a narrow residual-boundary check before proposing the next form.\n"
        ),
        score=53.0,
        use_llm=False,
    )

    ledger = tmp_path / "workspace" / "explored_primitive_classes.jsonl"
    summary = summarize_explored_primitive_classes(tmp_path)

    assert result.tracked is True
    assert result.should_track is True
    assert result.class_name == "residual boundary detector"
    assert ledger.exists()
    assert summary["per_class"]["residual boundary detector"]["best_score"] == 53.0


def test_marker_headings_extract_the_declared_class_name(tmp_path):
    category = maybe_track_primitive_class_rotation(
        rubric_data={
            "enable_primitive_class_rotation": True,
            "cage_meta": {"class": "audit"},
        },
        project_dir=tmp_path,
        run_id="run-category",
        iter_index=5,
        thesis_text="CATEGORY SWITCH: residual maps\nUse a different representation.",
        score=61.0,
        use_llm=False,
    )
    pivot = maybe_track_primitive_class_rotation(
        rubric_data={
            "enable_primitive_class_rotation": True,
            "cage_meta": {"class": "audit"},
        },
        project_dir=tmp_path,
        run_id="run-pivot",
        iter_index=6,
        thesis_text="STRUCTURAL PIVOT: evidence-carrier schema\nChange the receipt surface.",
        score=62.0,
        use_llm=False,
    )

    assert category.class_name == "residual maps"
    assert pivot.class_name == "evidence-carrier schema"
    summary = summarize_explored_primitive_classes(tmp_path)
    assert "residual maps" in summary["per_class"]
    assert "evidence-carrier schema" in summary["per_class"]


def test_tracking_records_candidate_outcome_for_negative_space(tmp_path):
    result = maybe_track_primitive_class_rotation(
        rubric_data={
            "enable_primitive_class_rotation": True,
            "cage_meta": {"class": "audit"},
        },
        project_dir=tmp_path,
        run_id="run-2",
        iter_index=3,
        thesis_text=(
            "## Structural Mutation: surplus_projection_gate\n"
            "mechanism = propose_new_primitive_class\n"
        ),
        score=41.0,
        outcome="non_improving_candidate",
        use_llm=False,
    )

    ledger = tmp_path / "workspace" / "explored_primitive_classes.jsonl"
    cross = cross_substrate_primitive_class_ledger_path(tmp_path)
    ledger_text = ledger.read_text()
    cross_text = cross.read_text()

    assert result.tracked is True
    assert '"outcome": "non_improving_candidate"' in ledger_text
    assert '"outcome": "non_improving_candidate"' in cross_text


def test_history_packet_surfaces_repeated_or_flat_classes_first(tmp_path):
    maybe_track_primitive_class_rotation(
        rubric_data={
            "enable_primitive_class_rotation": True,
            "cage_meta": {"class": "audit"},
        },
        project_dir=tmp_path,
        run_id="run-pressure",
        iter_index=1,
        thesis_text="## Structural Mutation: local_boundary_gate\n",
        score=80.0,
        outcome="judged_candidate",
        use_llm=False,
    )
    maybe_track_primitive_class_rotation(
        rubric_data={
            "enable_primitive_class_rotation": True,
            "cage_meta": {"class": "audit"},
        },
        project_dir=tmp_path,
        run_id="run-pressure",
        iter_index=2,
        thesis_text="## Structural Mutation: local_boundary_gate\n",
        score=79.0,
        outcome="non_improving_candidate",
        use_llm=False,
    )

    packet = primitive_class_history_packet(
        {"enable_primitive_class_rotation": True},
        project_dir=tmp_path,
    )

    pressure_pos = packet.index("Rotate away first:")
    full_history_pos = packet.index("Classes already proposed")
    assert pressure_pos < full_history_pos
    assert "'local_boundary_gate': repeats=1, rejected_or_flat=1" in packet


def test_cross_substrate_reader_uses_public_rd_ledger_and_legacy_fallback(tmp_path):
    canonical = cross_substrate_primitive_class_ledger_path(tmp_path)
    legacy = tmp_path.parent.parent / "analytics" / "queries" / "cross_substrate_explored_classes.jsonl"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    legacy.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text(
        '{"project_slug":"other","class_name":"ACRR","score":91}\n',
        encoding="utf-8",
    )
    legacy.write_text(
        '{"project_slug":"legacy","class_name":"PECVP","score":77}\n',
        encoding="utf-8",
    )

    rows = read_cross_substrate_primitive_classes(tmp_path)

    assert {row["class_name"] for row in rows} == {"ACRR", "PECVP"}
