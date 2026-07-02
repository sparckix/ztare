from ztare.workspace import report_actions, source_actions


def test_workspace_action_json_parser_returns_outermost_latest_object() -> None:
    output = (
        "command output\n"
        "{\"first\": true}\n"
        "{\n"
        "  \"status\": \"attention\",\n"
        "  \"nested\": {\"status\": \"fresh\"}\n"
        "}\n"
    )

    expected = {"status": "attention", "nested": {"status": "fresh"}}
    assert report_actions.extract_last_json_object(output) == expected
    assert source_actions.extract_last_json_object(output) == expected
