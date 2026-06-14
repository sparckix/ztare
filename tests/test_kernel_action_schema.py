from src.ztare.common.kernel_action_schema import (
    KernelActionSchema,
    render_action_schema_prompt_lines,
    validate_kernel_action_schema,
)


def test_kernel_action_schema_validates_required_action_fields() -> None:
    action = KernelActionSchema(
        source_kind="test",
        action_family="primitive",
        action_name="demo",
        target_mapping="map source to target",
        nearest_confuser="nearby label-only analogy",
        falsifier="target check fails",
        verification_artifact="workspace/check.json",
    ).to_dict()

    ok, missing = validate_kernel_action_schema(action)

    assert ok is True
    assert missing == []
    rendered = "\n".join(render_action_schema_prompt_lines(action))
    assert "target_mapping=map source to target" in rendered


def test_kernel_action_schema_reports_missing_fields() -> None:
    action = KernelActionSchema(
        source_kind="test",
        action_family="primitive",
        action_name="demo",
        target_mapping="unset",
        nearest_confuser="label-only analogy",
        falsifier="target check fails",
        verification_artifact="workspace/check.json",
    ).to_dict()

    ok, missing = validate_kernel_action_schema(action)

    assert ok is False
    assert missing == ["target_mapping"]
