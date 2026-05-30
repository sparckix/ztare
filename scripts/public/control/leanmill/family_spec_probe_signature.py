#!/usr/bin/env python3
"""Shared signatures for LeanMill family-spec probe packets."""
from __future__ import annotations

import hashlib
import json
from typing import Any

DEFAULT_FAMILY_SPEC_PROBE_TIMEOUT_S = 120
DEFAULT_FAMILY_SPEC_PROBE_BACKEND = "repl_file"


def probe_signature(family: str, lane: str, tests: list[dict[str, Any]]) -> str:
    rows = []
    for test in tests:
        rows.append({
            "row_id": str(test.get("row_id") or ""),
            "candidate_name": str(test.get("candidate_name") or ""),
            "action_family": str(test.get("action_family") or ""),
            "test_kind": str(test.get("test_kind") or ""),
            "target_theorem_name": str(test.get("target_theorem_name") or ""),
            "target_line": int(test.get("target_line") or 0),
            "body_hash": hashlib.sha256("\n".join(str(x) for x in (test.get("extra_body") or [])).encode()).hexdigest()[:16],
        })
    material = json.dumps({"family": family, "lane": lane, "tests": sorted(rows, key=lambda r: json.dumps(r, sort_keys=True))}, sort_keys=True)
    return hashlib.sha256(material.encode()).hexdigest()


def family_spec_template_probe_test(
    *,
    family: str,
    template: dict[str, Any],
    body_lines: list[str],
    default_backend: str = DEFAULT_FAMILY_SPEC_PROBE_BACKEND,
    default_timeout_s: int = DEFAULT_FAMILY_SPEC_PROBE_TIMEOUT_S,
    family_spec_path: str = "",
) -> dict[str, Any]:
    row_id = str(template.get("row_id") or "")
    return {
        "packet_id": f"{family}:{row_id}:{template.get('id') or 'family_spec_template'}",
        "repair_family": family,
        "row_id": row_id,
        "candidate_name": None,
        "action_family": "manual_extra",
        "test_kind": str(template.get("test_kind") or "positive"),
        "expected_outcome": str(template.get("expected_outcome") or ""),
        "backend": str(template.get("backend") or default_backend),
        "timeout": int(template.get("timeout") or default_timeout_s),
        "max_candidates": 1,
        "max_actions": 1,
        "score_candidates": False,
        "require_positive_source_action": False,
        "source_credit_eligible": False,
        "clean_solver_credit_eligible": False,
        "credit_type": "repair_family_spec_probe",
        "static_filter": "",
        "extra_body": body_lines,
        "family_spec_path": family_spec_path,
    }


def family_spec_row_probe_signature(
    *,
    family: str,
    row_id: str,
    templates: list[dict[str, Any]],
    body_by_template_id: dict[str, list[str]],
    default_backend: str = DEFAULT_FAMILY_SPEC_PROBE_BACKEND,
    default_timeout_s: int = DEFAULT_FAMILY_SPEC_PROBE_TIMEOUT_S,
    family_spec_path: str = "",
) -> str:
    tests: list[dict[str, Any]] = []
    for template in templates:
        template_row_id = str(template.get("row_id") or "")
        if template_row_id != row_id:
            continue
        template_id = str(template.get("id") or "")
        tests.append(family_spec_template_probe_test(
            family=family,
            template=template,
            body_lines=body_by_template_id.get(template_id, []),
            default_backend=default_backend,
            default_timeout_s=default_timeout_s,
            family_spec_path=family_spec_path,
        ))
    return probe_signature(family, "family_spec", tests)
