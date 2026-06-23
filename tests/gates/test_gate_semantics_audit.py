from pathlib import Path

from ztare.gates.gate_semantics_audit import audit_gate_file


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "example_gate.py"
    path.write_text(text, encoding="utf-8")
    return path


def _kinds(findings: list[dict]) -> set[str]:
    return {finding["kind"] for finding in findings}


def test_audit_flags_falsey_startswith_tuple(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
def _present(value):
    lowered = value.strip().lower()
    return not lowered.startswith(("missing", "absent"))
""",
    )

    findings = audit_gate_file(path)

    assert "prefix_falsey_matching" in _kinds(findings)


def test_audit_accepts_exact_falsey_and_advisory_weak_policy(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
WEAK_SUBSTITUTES = ("label_only",)

def _present(value):
    lowered = value.strip().lower()
    false_exact_matches = {"missing", "absent", "unknown", "todo", "none", "null", "false"}
    return lowered not in false_exact_matches

def run(receipt, enforce_block=False):
    weak_present = [field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))]
    violations = []
    if weak_present:
        violations.append({"severity": "advisory", "weak_substitutes": weak_present})
    complete = True
    return {"passed": True, "complete": complete, "violations": violations}
""",
    )

    findings = audit_gate_file(path)

    assert "prefix_falsey_matching" not in _kinds(findings)
    assert "weak_substitute_semantics_implicit" not in _kinds(findings)
    assert "weak_substitute_blocks_completeness" not in _kinds(findings)


def test_audit_flags_weak_substitute_completeness_blocking(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
WEAK_SUBSTITUTES = ("label_only",)

def run(receipt):
    weak_present = [field for field in WEAK_SUBSTITUTES if receipt.get(field)]
    missing = []
    hard_present = []
    complete = (
        not missing
        and not hard_present
        and not weak_present
    )
    return {"complete": complete}
""",
    )

    findings = audit_gate_file(path)

    assert "weak_substitute_blocks_completeness" in _kinds(findings)


def test_audit_accepts_single_mode_blocking_weak_policy(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
WEAK_SUBSTITUTES = ("label_only",)

def run(receipt):
    weak_present = [field for field in WEAK_SUBSTITUTES if receipt.get(field)]
    violations = []
    if weak_present:
        violations.append({"type": "weak_substitute", "fields": weak_present})
    return {"passed": not violations, "complete": True, "violations": violations}
""",
    )

    findings = audit_gate_file(path)

    assert "weak_substitute_semantics_implicit" not in _kinds(findings)


def test_audit_accepts_explicit_hard_fail_semantics(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
def run(receipt):
    violations = []
    passed = not violations
    return {"passed": passed, "hard_fail": not passed}
""",
    )

    findings = audit_gate_file(path)

    assert "hard_by_default_passed_semantics" not in _kinds(findings)
