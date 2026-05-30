"""Audit receipt-gate semantics for advisory/blocking drift.

This is a lightweight static scanner for the gate failure modes that recur in
research receipt gates:

* prefix-based falsey string matching;
* hard-by-default ``passed = not violations`` gates without an explicit
  ``enforce_block`` split;
* weak-substitute lists whose blocking/advisory semantics are not explicit.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path("src/ztare/gates")


def _line_number(text: str, needle: str) -> int:
    index = text.find(needle)
    if index < 0:
        return 0
    return text.count("\n", 0, index) + 1


_FALSEY_PREFIX_RE = re.compile(
    r"\.startswith\s*\(\s*(?:"
    r"false\w*|FALSE\w*|"
    r"\(\s*['\"](?:missing|absent|unknown|todo|none|null|false|0)['\"]|"
    r"['\"](?:missing|absent|unknown|todo|none|null|false|0)['\"]"
    r")"
)


def _has_prefix_falsey_matching(text: str) -> bool:
    return bool(_FALSEY_PREFIX_RE.search(text))


def _weak_substitute_policy_is_explicit(text: str) -> bool:
    if (
        "WEAK_SUBSTITUTES" not in text
        and "weak_present" not in text
        and "weak_hits" not in text
    ):
        return True
    if "weak_substitute_policy" in text:
        return True
    start_candidates = [
        index for index in (text.find("if weak_present"), text.find("if weak_hits"))
        if index >= 0
    ]
    start = min(start_candidates) if start_candidates else -1
    if start < 0:
        return False
    window = text[start:start + 1800]
    explicit_severity = (
        '"severity": "advisory"' in window
        or '"severity": "blocking"' in window
        or '"severity": "blocking" if enforce_block else "advisory"' in window
        or '"severity": "advisory" if not enforce_block else "blocking"' in window
    )
    if explicit_severity:
        return True
    single_mode_blocks = (
        "violations.append" in window
        and (
            '"passed": not violations' in text
            or '"passed": not blocking' in text
            or "passed = not violations" in text
            or "passed = not blocking" in text
        )
    )
    return single_mode_blocks


def _hard_by_default_policy_is_explicit(text: str) -> bool:
    return (
        "hard_fail" in text
        or "hard-fail" in text.lower()
        or "fail-closed" in text.lower()
        or "blocking_active" in text
        or "enforce_block" in text
    )


def _complete_mentions_weak_present(text: str) -> bool:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "complete" not in line or "=" not in line:
            continue
        block = "\n".join(lines[i:i + 8])
        if "weak_present" in block:
            return True
    return False


def audit_gate_file(path: Path) -> list[dict[str, Any]]:
    if path.name == "gate_semantics_audit.py":
        return []
    text = path.read_text(encoding="utf-8")
    findings: list[dict[str, Any]] = []

    if "false_prefixes" in text or _has_prefix_falsey_matching(text):
        findings.append({
            "path": str(path),
            "line": _line_number(text, "false_prefixes")
            or _line_number(text, ".startswith"),
            "kind": "prefix_falsey_matching",
            "severity": "high",
            "reason": (
                "formal receipts should use exact falsey sentinels or a "
                "separate semantic evaluator; prefix matching rejects valid "
                "phrases such as 'missing because ...' by string shape"
            ),
        })

    if (
        "passed = not violations" in text
        and not _hard_by_default_policy_is_explicit(text)
    ):
        findings.append({
            "path": str(path),
            "line": _line_number(text, "passed = not violations"),
            "kind": "hard_by_default_passed_semantics",
            "severity": "medium",
            "reason": (
                "gate hard-fails whenever violations exist and has no explicit "
                "advisory/blocking split"
            ),
        })

    has_weak = "WEAK_SUBSTITUTES" in text or "weak_present" in text
    weak_in_complete = _complete_mentions_weak_present(text)
    weak_policy_explicit = _weak_substitute_policy_is_explicit(text)
    if has_weak and not (weak_in_complete or weak_policy_explicit):
        findings.append({
            "path": str(path),
            "line": _line_number(text, "weak_present") or _line_number(text, "WEAK_SUBSTITUTES"),
            "kind": "weak_substitute_semantics_implicit",
            "severity": "medium",
            "reason": (
                "weak-substitute fields are present, but the file does not make "
                "their complete/pass semantics explicit"
            ),
        })

    if has_weak and weak_in_complete:
        findings.append({
            "path": str(path),
            "line": _line_number(text, "complete"),
            "kind": "weak_substitute_blocks_completeness",
            "severity": "medium",
            "reason": (
                "weak substitutes appear in the complete calculation; either "
                "keep them advisory with a severity-only violation or promote "
                "the field into HARD_VIOLATIONS"
            ),
        })

    if (
        has_weak
        and weak_in_complete
        and not weak_policy_explicit
        and "enforce_block" not in text
    ):
        findings.append({
            "path": str(path),
            "line": _line_number(text, "weak_present"),
            "kind": "weak_substitute_blocking_without_mode",
            "severity": "medium",
            "reason": (
                "weak substitutes are blocking completeness, but the CLI/API "
                "does not expose advisory mode"
            ),
        })

    return findings


def audit_gate_tree(root: Path = DEFAULT_ROOT) -> list[dict[str, Any]]:
    return [
        finding
        for path in sorted(root.glob("*_gate.py"))
        for finding in audit_gate_file(path)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Gate files or directories to audit.")
    parser.add_argument("--fail-on", choices=("none", "medium", "high"), default="high")
    args = parser.parse_args(argv)

    targets = [Path(p) for p in args.paths] or [DEFAULT_ROOT]
    findings: list[dict[str, Any]] = []
    for target in targets:
        if target.is_dir():
            findings.extend(audit_gate_tree(target))
        else:
            findings.extend(audit_gate_file(target))

    print(json.dumps({"finding_count": len(findings), "findings": findings}, indent=2))

    order = {"none": 3, "medium": 1, "high": 2}
    threshold = order[args.fail_on]
    if args.fail_on != "none":
        severities = {"medium": 1, "high": 2}
        if any(severities.get(f["severity"], 0) >= threshold for f in findings):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
