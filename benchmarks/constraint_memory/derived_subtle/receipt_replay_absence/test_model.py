import json
import os

RECEIPT_PATH = "workspace/packet_falsifier_receipt.json"
EXPECTED_TYPE = "project_packet_falsifier"
EXPECTED_STATUS = "resolved"
EXPECTED_REMOVE_REF = "evidence_refs[1]"
EXPECTED_FAILURE_SUBSTR = "local path does not exist"
EXPECTED_ENFORCER_FRAMES = [
    "src/ztare/scaffold/substrate_queue.py::validate_project_packet_falsifier",
    "src/ztare/cli.py::ztare project packet falsify",
]
EXPECTED_PATH_SAFETY = {
    "absolute_local_refs_allowed": False,
    "parent_traversal_allowed": False,
    "symlink_escape_allowed": False,
}


def _load_receipt():
    if not os.path.exists(RECEIPT_PATH):
        raise FileNotFoundError(RECEIPT_PATH)
    with open(RECEIPT_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_receipt_machine_fields():
    receipt = _load_receipt()
    assert receipt.get("type") == EXPECTED_TYPE
    assert receipt.get("status") == EXPECTED_STATUS
    assert receipt.get("remove_ref") == EXPECTED_REMOVE_REF
    assert EXPECTED_FAILURE_SUBSTR in receipt.get("expected_failure", "")
    for frame in EXPECTED_ENFORCER_FRAMES:
        assert frame in receipt.get("enforced_by", [])
    for key, value in EXPECTED_PATH_SAFETY.items():
        assert receipt.get("path_safety", {}).get(key) is value


def test_forward_live_trace_structure():
    trace_path = "workspace/falsifier_cli.trace"
    if os.path.exists(trace_path):
        with open(trace_path, "r", encoding="utf-8") as handle:
            trace = handle.read()
        assert "validate_project_packet_falsifier" in trace
        assert "project_packet_falsifier_receipt" in trace
    else:
        pass
