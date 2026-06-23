from __future__ import annotations

from ztare.gates.cross_class_extrapolation_gate import dispatch_r10_r11_from_harness_json


def test_dispatch_skips_qualitative_substrate_without_feature_key_warning(tmp_path):
    project = tmp_path / "project"
    (project / "workspace").mkdir(parents=True)

    result = dispatch_r10_r11_from_harness_json(
        project,
        {
            "cage_meta": {"class": "writing_quality"},
            "require_i_model_in_submission": False,
        },
        iter_index=1,
    )

    assert result["error"] is None
    assert result["gate_aliases"] == {
        "r10": "cross_class_extrapolation_diagnostic",
        "r11": "per_class_holdout_ceiling",
    }
    assert result["r10_engaged"] is False
    assert result["r11_engaged"] is False
    assert "skipped_reason" in result


def test_dispatch_still_requires_feature_keys_for_nd_features(tmp_path):
    project = tmp_path / "project"
    (project / "workspace").mkdir(parents=True)

    result = dispatch_r10_r11_from_harness_json(
        project,
        {"cage_meta": {"class": "nd_features"}},
        iter_index=1,
    )

    assert result["error"] == (
        "cross-class diagnostic requires framer_primary_feature_key "
        "and substrate_class_key in rubric"
    )
