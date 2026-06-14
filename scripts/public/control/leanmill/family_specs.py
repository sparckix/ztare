#!/usr/bin/env python3
"""Load versioned LeanMill repair-family specs.

Family specs are the data-backed replacement for growing row-specific Python
template constants. The compiler may still keep legacy constants as bootstrap
fallback, but migrated families should live under
`analytics/public/leanmill/repair_families/`.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import yaml

from leanmill_paths import REPAIR_FAMILY_SPEC_DIR


DEFAULT_SPEC_DIR = REPAIR_FAMILY_SPEC_DIR
VALID_STATUSES = {
    "inventory_only",
    "seed_only",
    "seed_hold",
    "candidate_family",
    "validated_family",
    "superseded_family",
}
VALID_TEST_KINDS = {"positive", "negative_control"}
VALID_BACKENDS = {"subprocess", "repl", "repl_step", "repl_file"}
MAX_TIMEOUT_S = 300


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(errors="ignore")
        obj = yaml.safe_load(text)
    except Exception as exc:  # noqa: BLE001 - spec gates must emit typed blockers, not crash.
        return {
            "_path": str(path),
            "_parse_status": "fail",
            "_parse_error": str(exc),
            "family": path.stem,
            "templates": [],
        }
    if not isinstance(obj, dict):
        return {
            "_path": str(path),
            "_parse_status": "fail",
            "_parse_error": "spec root must be a mapping",
            "family": path.stem,
            "templates": [],
        }
    obj.setdefault("_path", str(path))
    obj.setdefault("_parse_status", "pass")
    return obj


def load_specs(spec_dir: str | Path = DEFAULT_SPEC_DIR) -> list[dict[str, Any]]:
    root = Path(spec_dir)
    if not root.exists():
        return []
    return [_read_yaml(path) for path in sorted(root.glob("*.yaml"))]


def _template_body(template: dict[str, Any]) -> list[str]:
    if "body" in template:
        body = str(template.get("body") or "")
        tid = str(template.get("id") or template.get("packet_id_suffix") or "family_spec_template")
        return [body if "::" in body else f"{tid}::{body}"]
    body_lines = template.get("body_lines") or []
    if isinstance(body_lines, str):
        body_lines = [body_lines]
    return [str(x) for x in body_lines]


HOLE_RE = re.compile(r"(?<![A-Za-z0-9_])\?_(?![A-Za-z0-9_])")


def _body_mentions_name(body: str, name: str) -> bool:
    if not body or not name:
        return False
    return re.search(r"(?<![A-Za-z0-9_'])" + re.escape(name) + r"(?![A-Za-z0-9_'])", body) is not None


def _raw_template_body_text(template: dict[str, Any]) -> str:
    if "body" in template:
        return str(template.get("body") or "")
    body_lines = template.get("body_lines") or []
    if isinstance(body_lines, str):
        return body_lines
    return "\n".join(str(x) for x in body_lines)


def _normalize_body_for_substance(template: dict[str, Any]) -> str:
    lines: list[str] = []
    for line in _raw_template_body_text(template).splitlines():
        if line.lstrip().startswith("--"):
            continue
        cut = line.find("--")
        if cut >= 0:
            line = line[:cut]
        line = " ".join(line.split())
        if line:
            lines.append(line)
    return "\n".join(lines)


def _template_key(path: str, family: str, template: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        path,
        family,
        str(template.get("row_id") or ""),
        str(template.get("id") or template.get("packet_id_suffix") or ""),
    )


def _iter_row_records(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if not isinstance(obj, dict):
        return []
    for key in ("rows", "candidates", "items", "selected_rows", "candidate_rows"):
        rows = obj.get(key)
        if isinstance(rows, list):
            return [x for x in rows if isinstance(x, dict)]
    return []


def _append_unique(values: list[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in values:
        values.append(text)


def target_names_from_row(row: dict[str, Any]) -> list[str]:
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    names: list[str] = []
    for key in ("target_theorem_name", "theorem_name", "decl_name", "declaration_name", "target_name"):
        _append_unique(names, row.get(key))
        _append_unique(names, source.get(key))
    # In generated Mathlib-corpus rows, source.mathlib_name is the gold declaration.
    # A positive template that cites it directly is oracle leakage, even when it is
    # not syntactically the local generated theorem name.
    _append_unique(names, source.get("mathlib_name"))
    return names


def target_names_by_row_from_context_paths(paths: list[str | Path]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for path in paths:
        p = Path(path)
        if not p.exists() or not p.is_file():
            continue
        try:
            obj = json.loads(p.read_text(errors="ignore"))
        except json.JSONDecodeError:
            continue
        for row in _iter_row_records(obj):
            row_id = str(row.get("row_id") or row.get("id") or row.get("target_id") or "")
            if not row_id:
                continue
            for name in target_names_from_row(row):
                out.setdefault(row_id, [])
                if name not in out[row_id]:
                    out[row_id].append(name)
    return out


OVERCLAIM_DISQUALIFYING_PUBLIC_LEMMA_RE = re.compile(r"\b(?:[A-Z][A-Za-z0-9_'.]*\.)?[a-zA-Z_][A-Za-z0-9_']*_[A-Za-z0-9_'.]*\b")
OVERCLAIM_GLUE_TOKENS = {"exact", "simpa", "simp", "rw", "rwa", "convert", "refine", "apply", "have", "show", "calc", "by", "using", "fun", "intro", "intros"}
OVERCLAIM_GENERIC_TOKENS = {"zero_lt_two", "two_ne_zero", "pow_pos", "pow_succ", "mul_two", "two_mul", "nsmul_eq_mul", "Nat.cast_pow", "Nat.cast_two"}


def _body_public_lemma_mentions(body: str, *, head_patterns: list[str] | None = None) -> list[str]:
    mentions: list[str] = []
    for token in OVERCLAIM_DISQUALIFYING_PUBLIC_LEMMA_RE.findall(body or ""):
        bare = token.split(".")[-1]
        if token in OVERCLAIM_GLUE_TOKENS or bare in OVERCLAIM_GLUE_TOKENS or token in OVERCLAIM_GENERIC_TOKENS or bare in OVERCLAIM_GENERIC_TOKENS:
            continue
        if token.startswith("MCB_"):
            continue
        if "_" not in bare:
            continue
        _append_unique(mentions, token)
    for pattern in head_patterns or []:
        pat = str(pattern or "").strip()
        bare = pat.split(".")[-1]
        if not pat or pat in OVERCLAIM_GENERIC_TOKENS or bare in OVERCLAIM_GENERIC_TOKENS:
            continue
        if "_" in bare and _body_mentions_name(body or "", pat):
            _append_unique(mentions, pat)
    return mentions


def overclaim_disqualification_findings(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for spec in specs:
        path = str(spec.get("_path") or "")
        family = str(spec.get("family") or "")
        match = spec.get("residual_match") if isinstance(spec.get("residual_match"), dict) else {}
        head_patterns = [str(x) for x in (match.get("head_patterns") or []) if str(x)]
        for template in spec.get("templates") or []:
            if not isinstance(template, dict) or str(template.get("test_kind") or "") != "positive":
                continue
            body = _raw_template_body_text(template)
            mentions = _body_public_lemma_mentions(body, head_patterns=head_patterns)
            body_has_gcongr = bool(re.search(r"(?<![A-Za-z0-9_'])gcongr(?![A-Za-z0-9_'])", body or ""))
            if not mentions and not body_has_gcongr:
                continue
            findings.append({
                "path": path,
                "family": family,
                "row_id": str(template.get("row_id") or ""),
                "template": str(template.get("id") or template.get("packet_id_suffix") or ""),
                "finding": (
                    "positive_template_public_lemma_wrapper_not_overclaim_grade"
                    if mentions else "positive_template_generic_tactic_floor_not_overclaim_grade"
                ),
                "anti_pattern": (
                    "paraphrase_of_named_gold_lemma_via_rewrite"
                    if mentions else "gcongr_floor_satisfiable"
                ),
                "overclaim_grade_eligible": False,
                "mechanism_evidence_only": True,
                "mentioned_public_lemmas": mentions[:12],
            })
    return findings


def overclaim_disqualification_summary(specs: list[dict[str, Any]]) -> dict[str, Any]:
    findings = overclaim_disqualification_findings(specs)
    by_family: dict[str, int] = {}
    for f in findings:
        family = str(f.get("family") or "")
        by_family[family] = by_family.get(family, 0) + 1
    return {
        "schema": "leanmill-overclaim-disqualification-summary-v1",
        "finding_count": len(findings),
        "family_count": len(by_family),
        "by_family": dict(sorted(by_family.items(), key=lambda kv: (-kv[1], kv[0]))),
        "interpretation": "findings are mechanism/calibration evidence only until prereg benchmark shows lift over public tools",
    }


def _template_quarantine_failures(
    path: str,
    family: str,
    templates: list[dict[str, Any]],
    target_names_by_row: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    by_row: dict[str, list[dict[str, Any]]] = {}
    for template in templates:
        if not isinstance(template, dict):
            continue
        row_id = str(template.get("row_id") or "")
        tid = str(template.get("id") or template.get("packet_id_suffix") or "")
        body_text = _raw_template_body_text(template)
        if HOLE_RE.search(body_text):
            failures.append({
                "path": path,
                "family": family,
                "row_id": row_id,
                "template": tid,
                "failure": "template_contains_placeholder_hole",
                "severity": "quarantine",
                "quarantinable": True,
            })
        target_names = (target_names_by_row or {}).get(row_id, [])
        for target_name in target_names:
            if target_name and _body_mentions_name(body_text, target_name):
                failures.append({
                    "path": path,
                    "family": family,
                    "row_id": row_id,
                    "template": tid,
                    "target_theorem_name": target_name,
                    "failure": (
                        "positive_template_references_target_theorem"
                        if str(template.get("test_kind") or "") == "positive"
                        else "negative_control_references_target_theorem"
                    ),
                    "severity": "quarantine",
                    "quarantinable": True,
                })
                break
        if row_id:
            by_row.setdefault(row_id, []).append(template)
    for row_id, row_templates in by_row.items():
        positives = [t for t in row_templates if str(t.get("test_kind") or "") == "positive"]
        negatives = [t for t in row_templates if str(t.get("test_kind") or "") == "negative_control"]
        positive_bodies = {b for b in (_normalize_body_for_substance(t) for t in positives) if b}
        seen_negative_bodies: dict[str, str] = {}
        for neg in negatives:
            tid = str(neg.get("id") or neg.get("packet_id_suffix") or "")
            neg_body = _normalize_body_for_substance(neg)
            if not neg_body:
                continue
            if neg_body in positive_bodies:
                failures.append({
                    "path": path,
                    "family": family,
                    "row_id": row_id,
                    "template": tid,
                    "failure": "negative_control_duplicates_positive",
                    "severity": "quarantine",
                    "quarantinable": True,
                })
            first_tid = seen_negative_bodies.get(neg_body)
            if first_tid:
                failures.append({
                    "path": path,
                    "family": family,
                    "row_id": row_id,
                    "template": tid,
                    "duplicate_of": first_tid,
                    "failure": "duplicate_negative_control_body",
                    "severity": "quarantine",
                    "quarantinable": True,
                })
            else:
                seen_negative_bodies[neg_body] = tid
    return failures


def templates_by_row(specs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for spec in specs:
        family = str(spec.get("family") or "")
        credit = spec.get("credit") or {}
        for template in spec.get("templates") or []:
            row_id = str(template.get("row_id") or "")
            if not row_id:
                continue
            out.setdefault(row_id, []).append({
                "packet_id_suffix": str(template.get("id") or template.get("packet_id_suffix") or ""),
                "repair_family": family,
                "test_kind": str(template.get("test_kind") or ""),
                "expected_outcome": str(template.get("expected_outcome") or ""),
                "backend": str(template.get("backend") or "repl_file"),
                "timeout": int(template.get("timeout") or 120),
                "extra_body": _template_body(template),
                "source_credit_eligible": bool(credit.get("source_credit_eligible", False)),
                "clean_solver_credit_eligible": bool(credit.get("clean_solver_credit_eligible", False)),
                "spec_path": str(spec.get("_path") or ""),
            })
    return out


def match_specs_for_residual(
    specs: list[dict[str, Any]],
    *,
    row_id: str,
    lane: str,
    residual_class: str,
    sample_tail: str = "",
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    hay = f"{row_id}\n{lane}\n{residual_class}\n{sample_tail}"
    for spec in specs:
        match = spec.get("residual_match") or {}
        row_ids = {str(x) for x in match.get("row_ids") or []}
        lanes = {str(x) for x in match.get("lanes") or []}
        residuals = {str(x) for x in match.get("residual_classes") or []}
        patterns = [str(x) for x in match.get("head_patterns") or []]
        if row_ids and row_id not in row_ids:
            continue
        if lanes and lane not in lanes:
            continue
        if residuals and residual_class not in residuals:
            continue
        if patterns and not any(p in hay for p in patterns):
            continue
        matches.append(spec)
    return matches


def validate_specs(
    specs: list[dict[str, Any]],
    registry: dict[str, Any] | None = None,
    *,
    target_names_by_row: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    registry_by_family = {str(f.get("family") or ""): f for f in (registry or {}).get("families") or []}
    for spec in specs:
        path = str(spec.get("_path") or "")
        family = str(spec.get("family") or "")
        status = str(spec.get("status") or "")
        templates = [t for t in list(spec.get("templates") or []) if isinstance(t, dict)]
        credit = spec.get("credit") or {}
        if str(spec.get("_parse_status") or "pass") != "pass":
            failures.append({
                "path": path,
                "family": family,
                "failure": "spec_yaml_parse_failed",
                "parse_error": spec.get("_parse_error"),
            })
            continue
        if not family:
            failures.append({"path": path, "failure": "missing_family"})
        if not isinstance(spec.get("version"), int):
            failures.append({"path": path, "family": family, "failure": "missing_integer_version"})
        if status not in VALID_STATUSES:
            failures.append({"path": path, "family": family, "failure": "invalid_status", "status": status})
        if "source_credit_eligible" not in credit or "clean_solver_credit_eligible" not in credit:
            failures.append({"path": path, "family": family, "failure": "missing_explicit_credit_boundary"})
        kinds = {str(t.get("test_kind") or "") for t in templates}
        if templates and "positive" not in kinds:
            failures.append({"path": path, "family": family, "failure": "missing_positive_template"})
        if templates and "negative_control" not in kinds:
            failures.append({"path": path, "family": family, "failure": "missing_negative_control"})
        for template in templates:
            row_id = str(template.get("row_id") or "")
            tid = str(template.get("id") or "")
            if not row_id:
                failures.append({"path": path, "family": family, "template": tid, "failure": "missing_row_id"})
            if not tid:
                failures.append({"path": path, "family": family, "row_id": row_id, "failure": "missing_template_id"})
            if str(template.get("test_kind") or "") not in VALID_TEST_KINDS:
                failures.append({"path": path, "family": family, "row_id": row_id, "failure": "invalid_test_kind"})
            if str(template.get("backend") or "repl_file") not in VALID_BACKENDS:
                failures.append({"path": path, "family": family, "row_id": row_id, "failure": "invalid_backend"})
            timeout = int(template.get("timeout") or 0)
            if timeout <= 0 or timeout > MAX_TIMEOUT_S:
                failures.append({"path": path, "family": family, "row_id": row_id, "failure": "invalid_timeout"})
            if not _template_body(template):
                failures.append({"path": path, "family": family, "row_id": row_id, "failure": "missing_body"})
        failures.extend(_template_quarantine_failures(path, family, templates, target_names_by_row))
        reg = registry_by_family.get(family) or {}
        if registry_by_family and status == "candidate_family":
            if not reg:
                failures.append({
                    "path": path,
                    "family": family,
                    "failure": "candidate_status_registry_family_absent",
                    "severity": "advisory",
                    "advisory": True,
                })
            elif int(reg.get("unique_ratified_rows") or 0) < 2 or int(reg.get("negative_controls_expected_fail") or 0) < 1:
                failures.append({"path": path, "family": family, "failure": "candidate_status_without_registry_evidence"})
        if registry_by_family and status == "validated_family":
            if not reg:
                failures.append({
                    "path": path,
                    "family": family,
                    "failure": "validated_status_registry_family_absent",
                    "severity": "advisory",
                    "advisory": True,
                })
            elif str(reg.get("status") or "") != "validated_family":
                failures.append({"path": path, "family": family, "failure": "validated_status_without_heldout_registry_evidence"})
    return failures


def failure_is_blocking(failure: dict[str, Any]) -> bool:
    return not (bool(failure.get("quarantinable")) or bool(failure.get("advisory")))


def _quarantined_template_keys(
    specs: list[dict[str, Any]],
    target_names_by_row: dict[str, list[str]] | None = None,
) -> set[tuple[str, str, str, str]]:
    keys: set[tuple[str, str, str, str]] = set()
    for spec in specs:
        path = str(spec.get("_path") or "")
        family = str(spec.get("family") or "")
        templates = [t for t in (spec.get("templates") or []) if isinstance(t, dict)]
        for failure in _template_quarantine_failures(path, family, templates, target_names_by_row):
            template_id = str(failure.get("template") or "")
            row_id = str(failure.get("row_id") or "")
            if template_id:
                keys.add((path, family, row_id, template_id))
    return keys


def usable_specs(
    specs: list[dict[str, Any]],
    *,
    target_names_by_row: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """Return specs with mechanically unsafe templates removed.

    Quarantine is intentionally template-scoped: a bad proof hole or copied
    negative control should not poison unrelated, well-formed family rows. Row
    groups still need at least one positive and one negative control to remain
    operational.
    """
    bad_keys = _quarantined_template_keys(specs, target_names_by_row)
    usable: list[dict[str, Any]] = []
    for spec in specs:
        clone = copy.deepcopy(spec)
        path = str(clone.get("_path") or "")
        family = str(clone.get("family") or "")
        templates = [t for t in (clone.get("templates") or []) if isinstance(t, dict)]
        kept = [t for t in templates if _template_key(path, family, t) not in bad_keys]
        groups: dict[str, list[dict[str, Any]]] = {}
        for template in kept:
            row_id = str(template.get("row_id") or "")
            if row_id:
                groups.setdefault(row_id, []).append(template)
        rows_with_controls = {
            row_id
            for row_id, row_templates in groups.items()
            if any(str(t.get("test_kind") or "") == "positive" for t in row_templates)
            and any(str(t.get("test_kind") or "") == "negative_control" for t in row_templates)
        }
        clone["templates"] = [t for t in kept if str(t.get("row_id") or "") in rows_with_controls]
        if clone["templates"]:
            usable.append(clone)
    return usable



def _row_kind_groups(templates: list[dict[str, Any]]) -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {}
    for template in templates:
        if not isinstance(template, dict):
            continue
        row_id = str(template.get("row_id") or "")
        if not row_id:
            continue
        groups.setdefault(row_id, set()).add(str(template.get("test_kind") or ""))
    return groups


def family_supply_quality(
    specs: list[dict[str, Any]],
    *,
    target_names_by_row: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """Heuristic supply-quality report for the intelligence layer.

    This is advisory, not a proof gate. The Family Spec Gate still owns hard
    schema/blocking failures; this report distinguishes broad replayable supply
    from shallow row-local inventory and quarantined dead supply.
    """
    usable_by_family = {str(spec.get("family") or ""): spec for spec in usable_specs(specs, target_names_by_row=target_names_by_row)}
    failures = validate_specs(specs, target_names_by_row=target_names_by_row)
    failures_by_family: dict[str, list[dict[str, Any]]] = {}
    for failure in failures:
        failures_by_family.setdefault(str(failure.get("family") or ""), []).append(failure)
    reports: list[dict[str, Any]] = []
    for spec in specs:
        family = str(spec.get("family") or "")
        templates = [t for t in (spec.get("templates") or []) if isinstance(t, dict)]
        usable_templates = [t for t in ((usable_by_family.get(family) or {}).get("templates") or []) if isinstance(t, dict)]
        row_groups = _row_kind_groups(templates)
        usable_groups = _row_kind_groups(usable_templates)
        usable_pair_rows = sum(1 for kinds in usable_groups.values() if "positive" in kinds and "negative_control" in kinds)
        raw_pair_rows = sum(1 for kinds in row_groups.values() if "positive" in kinds and "negative_control" in kinds)
        match = spec.get("residual_match") or {}
        family_failures = failures_by_family.get(family, [])
        quarantine_failures = [f for f in family_failures if not failure_is_blocking(f)]
        blocking_failures = [f for f in family_failures if failure_is_blocking(f)]
        head_patterns = [str(x) for x in (match.get("head_patterns") or []) if str(x)]
        lanes = [str(x) for x in (match.get("lanes") or []) if str(x)]
        residual_classes = [str(x) for x in (match.get("residual_classes") or []) if str(x)]
        status = str(spec.get("status") or "")
        score = 0
        score += min(35, usable_pair_rows * 5)
        score += min(15, len(lanes) * 5)
        score += min(15, len(residual_classes) * 5)
        score += min(15, len(head_patterns) * 2)
        if not quarantine_failures:
            score += 10
        if status in {"candidate_family", "validated_family"}:
            score += 10
        elif status == "validated_family_requires_true_holdout_check":
            score += 5
        if spec.get("next_probe_contract") or spec.get("sibling_or_heldout_constraints"):
            score += 5
        score = max(0, min(100, score - min(20, len(blocking_failures) * 10)))
        gaps: list[str] = []
        if blocking_failures:
            gaps.append("blocking_schema_debt")
        if quarantine_failures:
            gaps.append("quarantine_debt")
        if usable_pair_rows == 0:
            gaps.append("no_usable_positive_negative_pair")
        elif usable_pair_rows < 4:
            gaps.append("shallow_usable_supply")
        if len(lanes) < 1 or len(head_patterns) < 4:
            gaps.append("weak_residual_match_surface")
        if raw_pair_rows > usable_pair_rows:
            gaps.append("paired_rows_lost_to_quarantine")
        if score >= 65 and usable_pair_rows >= 4 and not blocking_failures:
            supply_class = "probe_ready_general"
        elif usable_pair_rows > 0 and not blocking_failures:
            supply_class = "probe_ready_with_debt"
        elif blocking_failures:
            supply_class = "blocked"
        else:
            supply_class = "not_probe_ready"
        reports.append({
            "family": family,
            "status": status,
            "supply_class": supply_class,
            "generality_score": score,
            "template_count": len(templates),
            "row_count": len(row_groups),
            "raw_pair_rows": raw_pair_rows,
            "usable_pair_rows": usable_pair_rows,
            "quarantine_failure_count": len(quarantine_failures),
            "blocking_failure_count": len(blocking_failures),
            "lane_count": len(lanes),
            "residual_class_count": len(residual_classes),
            "head_pattern_count": len(head_patterns),
            "gaps": gaps,
            "next_action": (
                "repair blocking schema failures" if blocking_failures else
                "repair or retire quarantined templates" if quarantine_failures else
                "add heldout/sibling positive-negative row pairs" if usable_pair_rows < 4 else
                "run family-spec probes and heldout promotion"
            ),
        })
    reports.sort(key=lambda r: (str(r.get("supply_class")), -int(r.get("generality_score") or 0), str(r.get("family") or "")))
    return reports


def supply_quality_summary(
    specs: list[dict[str, Any]],
    *,
    target_names_by_row: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    reports = family_supply_quality(specs, target_names_by_row=target_names_by_row)
    classes: dict[str, int] = {}
    gap_counts: dict[str, int] = {}
    for report in reports:
        classes[str(report.get("supply_class") or "")] = classes.get(str(report.get("supply_class") or ""), 0) + 1
        for gap in report.get("gaps") or []:
            gap_counts[str(gap)] = gap_counts.get(str(gap), 0) + 1
    return {
        "schema": "leanmill-family-spec-supply-quality-v1",
        "family_count": len(reports),
        "class_counts": dict(sorted(classes.items())),
        "gap_counts": dict(sorted(gap_counts.items())),
        "probe_ready_general_count": classes.get("probe_ready_general", 0),
        "probe_ready_with_debt_count": classes.get("probe_ready_with_debt", 0),
        "median_generality_score": sorted([int(r.get("generality_score") or 0) for r in reports])[len(reports)//2] if reports else 0,
        "weakest_families": sorted(reports, key=lambda r: (int(r.get("generality_score") or 0), -len(r.get("gaps") or []), str(r.get("family") or "")))[:8],
    }

def specs_summary(specs: list[dict[str, Any]]) -> dict[str, Any]:
    rows = templates_by_row(specs)
    return {
        "schema": "leanmill-family-spec-summary-v1",
        "spec_count": len(specs),
        "family_count": len({str(s.get("family") or "") for s in specs}),
        "parse_failure_count": sum(1 for s in specs if str(s.get("_parse_status") or "pass") != "pass"),
        "row_template_count": sum(len(v) for v in rows.values()),
        "row_count": len(rows),
        "families": sorted(str(s.get("family") or "") for s in specs),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--spec-dir", default=DEFAULT_SPEC_DIR)
    ap.add_argument("--registry")
    ap.add_argument("--row-context", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    registry = {}
    if args.registry and Path(args.registry).exists():
        registry = json.loads(Path(args.registry).read_text(errors="ignore"))
    specs = load_specs(args.spec_dir)
    target_names_by_row = target_names_by_row_from_context_paths(args.row_context or [])
    failures = validate_specs(specs, registry, target_names_by_row=target_names_by_row)
    blocking = [f for f in failures if failure_is_blocking(f)]
    quarantined = [f for f in failures if not failure_is_blocking(f)]
    payload = {
        **specs_summary(specs),
        "usable": specs_summary(usable_specs(specs, target_names_by_row=target_names_by_row)),
        "supply_quality": family_supply_quality(specs, target_names_by_row=target_names_by_row),
        "supply_quality_summary": supply_quality_summary(specs, target_names_by_row=target_names_by_row),
        "overclaim_disqualification_summary": overclaim_disqualification_summary(specs),
        "overclaim_disqualification_findings": overclaim_disqualification_findings(specs),
        "target_context_row_count": len(target_names_by_row),
        "failure_count": len(failures),
        "blocking_failure_count": len(blocking),
        "quarantine_failure_count": len(quarantined),
        "failures": failures,
    }
    print(json.dumps(payload, indent=2 if args.json else None, sort_keys=True))
    return 0 if not blocking else 1


if __name__ == "__main__":
    raise SystemExit(main())
