import argparse
import copy
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ztare.common import utils
from ztare.common.llm_runtime import LLMRuntime, LLMRuntimeError, MODEL_MAP
from ztare.common.paths import PROJECTS_DIR, PROMPTS_DIR, REPO_ROOT
from ztare.workspace.evidence_gaps import (
    LOCAL_VERIFICATION_RECOVERY_KIND,
    PUBLIC_EVIDENCE_RECOVERY_KIND,
    canonicalize_evidence_gap_recovery_contract,
    evidence_gap_recovery,
)


ROOT_DIR = REPO_ROOT

TEXT_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".json",
    ".csv",
    ".tsv",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
    ".xml",
    ".py",
    ".js",
    ".ts",
}

DEBUG = False
COMPILE_FAILURE_ARTIFACT = "latest_compile_failure.json"
RAW_COMPILE_CACHE_INDEX = "compiled_evidence_cache_index.json"
LATEST_COMPILE_CACHE_HIT = "latest_compile_cache_hit.json"
RAW_COMPILE_CACHE_DIRNAME = "compiled_evidence_cache"
EVIDENCE_GAP_ACTION_FILENAME = "evidence_gap_action.json"
EVIDENCE_GAP_ACTION_SCHEMA = "ztare-evidence-gap-action-v1"
EVIDENCE_REPLAY_MANIFEST_FILENAME = "compiled_evidence_replay_manifest.json"
EVIDENCE_REPLAY_MANIFEST_SCHEMA = "ztare-evidence-replay-manifest-v1"
RAW_COMPILE_CACHE_SCHEMA_VERSION = 1
DEFAULT_EVIDENCE_LLM_RETRIES = 4
DEFAULT_EVIDENCE_LLM_TIMEOUT_SECONDS = 300
EVIDENCE_FETCH_SEVERITY_PRIORITY = ("blocking", "degrading", "enriching")

SOURCE_TYPE_EVIDENCE = "source_evidence"
SOURCE_TYPE_SEED = "seed_hypothesis"
SOURCE_TYPE_QUESTION = "research_question"
SOURCE_TYPE_TODO = "collection_todo"
SOURCE_TYPE_UNTYPED = "untyped"

SOURCE_TYPE_VALUES = {
    SOURCE_TYPE_EVIDENCE,
    SOURCE_TYPE_SEED,
    SOURCE_TYPE_QUESTION,
    SOURCE_TYPE_TODO,
    SOURCE_TYPE_UNTYPED,
}

SOURCE_TYPE_MAP_FILENAME = "source_type_map.json"


def repo_display_path(path: Path) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(candidate)


def load_source_type_map_with_warnings(raw_dir: Path) -> Tuple[Dict[str, str], List[str]]:
    """Load optional source_type_map.json from raw_dir.

    Maps filenames (or relative paths) to source_type strings. Used as a
    fallback for files that have no source_type frontmatter, so external
    documents can be typed without modifying their content.

    Example source_type_map.json::

        {
            "treatise_principles_of_epistemic_verification.md": "source_evidence"
        }
    """
    map_path = raw_dir / SOURCE_TYPE_MAP_FILENAME
    if not map_path.exists():
        return {}, []
    try:
        raw = json.loads(map_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {}, [f"{SOURCE_TYPE_MAP_FILENAME} is not valid JSON: {exc}"]
    if not isinstance(raw, dict):
        return {}, [f"{SOURCE_TYPE_MAP_FILENAME} must be a JSON object"]

    normalized: Dict[str, str] = {}
    warnings: List[str] = []
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            warnings.append(f"{SOURCE_TYPE_MAP_FILENAME} entries must map string path to string source_type")
            continue
        source_type = normalize_source_type(value)
        if source_type == SOURCE_TYPE_UNTYPED and value.strip().lower() != SOURCE_TYPE_UNTYPED:
            warnings.append(f"{SOURCE_TYPE_MAP_FILENAME} maps {key!r} to invalid source_type {value!r}")
        normalized[key] = source_type
    return normalized, warnings


def load_source_type_map(raw_dir: Path) -> Dict[str, str]:
    source_type_map, _warnings = load_source_type_map_with_warnings(raw_dir)
    return source_type_map

IMMUTABLE_ELIGIBLE_SOURCE_TYPES = {SOURCE_TYPE_EVIDENCE}
CONSTRAINT_ELIGIBLE_SOURCE_TYPES = {SOURCE_TYPE_EVIDENCE}
CONTRADICTION_ELIGIBLE_SOURCE_TYPES = {SOURCE_TYPE_EVIDENCE}
CLAIM_ELIGIBLE_SOURCE_TYPES = {SOURCE_TYPE_EVIDENCE, SOURCE_TYPE_SEED, SOURCE_TYPE_QUESTION}
VOID_ELIGIBLE_SOURCE_TYPES = SOURCE_TYPE_VALUES - {SOURCE_TYPE_TODO}


def dbg(msg: str) -> None:
    if not DEBUG:
        return
    ts = time.strftime("%H:%M:%S")
    print(f"[compile_evidence {ts}] {msg}", file=sys.stderr)


class CompileEvidenceError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        phase: str,
        model_family: str | None = None,
        model_id: str | None = None,
        transient: bool = False,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.phase = phase
        self.model_family = model_family
        self.model_id = model_id
        self.transient = transient
        self.status_code = status_code


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_json_sha256(payload: Any) -> str:
    return sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def parse_source_frontmatter(raw_text: str) -> Tuple[Dict[str, str], str]:
    if not raw_text.startswith("---\n"):
        return {}, raw_text
    match = re.match(r"^---\n(.*?)\n---\n?", raw_text, flags=re.DOTALL)
    if not match:
        return {}, raw_text
    block = match.group(1)
    metadata: Dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    stripped = raw_text[match.end():]
    return metadata, stripped


def normalize_source_type(value: str | None) -> str:
    if not value:
        return SOURCE_TYPE_UNTYPED
    normalized = value.strip().lower()
    if normalized not in SOURCE_TYPE_VALUES:
        return SOURCE_TYPE_UNTYPED
    return normalized


def read_typed_source(path: Path) -> Tuple[str, str, bool]:
    raw_text = read_text(path)
    metadata, stripped = parse_source_frontmatter(raw_text)
    source_type = normalize_source_type(metadata.get("source_type"))
    had_invalid_type = "source_type" in metadata and source_type == SOURCE_TYPE_UNTYPED and metadata.get("source_type", "").strip().lower() != SOURCE_TYPE_UNTYPED
    return stripped, source_type, had_invalid_type


def _all_source_ids_have_allowed_types(
    source_ids: List[str],
    source_type_by_id: Dict[str, str],
    allowed_types: set[str],
) -> bool:
    if not source_ids:
        return False
    return all(source_type_by_id.get(source_id, SOURCE_TYPE_UNTYPED) in allowed_types for source_id in source_ids)


def annotate_provenance_source_types(
    packet: Dict[str, Any],
    source_type_by_id: Dict[str, str],
) -> None:
    for item in packet.get("provenance", []):
        source_id = item.get("source_id")
        if source_id and not item.get("source_type"):
            item["source_type"] = source_type_by_id.get(source_id, SOURCE_TYPE_UNTYPED)


def filter_packet_by_source_types(
    packet: Dict[str, Any],
    source_type_by_id: Dict[str, str],
) -> List[str]:
    warnings: List[str] = []
    annotate_provenance_source_types(packet, source_type_by_id)

    original_ground_truth = packet.get("immutable_ground_truth", [])
    packet["immutable_ground_truth"] = [
        item
        for item in original_ground_truth
        if _all_source_ids_have_allowed_types(item.get("source_ids", []), source_type_by_id, IMMUTABLE_ELIGIBLE_SOURCE_TYPES)
    ]
    if len(packet["immutable_ground_truth"]) != len(original_ground_truth):
        warnings.append(
            "Dropped immutable ground-truth entries sourced from non-evidence files."
        )

    original_constraints = packet.get("numerical_ranges_and_constraints", [])
    packet["numerical_ranges_and_constraints"] = [
        item
        for item in original_constraints
        if _all_source_ids_have_allowed_types(item.get("source_ids", []), source_type_by_id, CONSTRAINT_ELIGIBLE_SOURCE_TYPES)
    ]
    if len(packet["numerical_ranges_and_constraints"]) != len(original_constraints):
        warnings.append(
            "Dropped range/constraint entries sourced from non-evidence files."
        )

    original_contradictions = packet.get("identified_contradictions", [])
    packet["identified_contradictions"] = [
        item
        for item in original_contradictions
        if _all_source_ids_have_allowed_types(item.get("source_ids_a", []), source_type_by_id, CONTRADICTION_ELIGIBLE_SOURCE_TYPES)
        and _all_source_ids_have_allowed_types(item.get("source_ids_b", []), source_type_by_id, CONTRADICTION_ELIGIBLE_SOURCE_TYPES)
    ]
    if len(packet["identified_contradictions"]) != len(original_contradictions):
        warnings.append(
            "Dropped contradiction entries that relied on non-evidence files."
        )

    original_claims = packet.get("candidate_claims_to_test", [])
    packet["candidate_claims_to_test"] = [
        item
        for item in original_claims
        if _all_source_ids_have_allowed_types(item.get("source_ids", []), source_type_by_id, CLAIM_ELIGIBLE_SOURCE_TYPES)
    ]
    if len(packet["candidate_claims_to_test"]) != len(original_claims):
        warnings.append(
            "Dropped candidate claims with unsupported source types."
        )

    original_voids = packet.get("epistemic_voids", [])
    filtered_voids: List[Dict[str, Any]] = []
    for item in original_voids:
        source_ids = item.get("source_ids", [])
        if not source_ids or _all_source_ids_have_allowed_types(source_ids, source_type_by_id, VOID_ELIGIBLE_SOURCE_TYPES):
            filtered_voids.append(item)
    packet["epistemic_voids"] = filtered_voids
    if len(packet["epistemic_voids"]) != len(original_voids):
        warnings.append(
            "Dropped epistemic void entries sourced only from collection TODO files."
        )

    untyped_sources = sorted(source_id for source_id, source_type in source_type_by_id.items() if source_type == SOURCE_TYPE_UNTYPED)
    if untyped_sources:
        warnings.append(
            f"Untyped sources present ({', '.join(untyped_sources)}). Untyped files are excluded from immutable facts and constraints."
        )

    return warnings


def resolve_source_type_map(
    *,
    project_dir: Path,
    sources: List[Dict[str, Any]],
) -> Tuple[Dict[str, str], List[str]]:
    source_type_by_id: Dict[str, str] = {}
    warnings: List[str] = []
    raw_dir = project_dir / "raw"
    source_type_overrides = load_source_type_map(raw_dir)

    for source in sources:
        source_id = source.get("source_id")
        if not source_id:
            continue
        source_type = normalize_source_type(source.get("source_type"))
        if source_type != SOURCE_TYPE_UNTYPED:
            source_type_by_id[source_id] = source_type
            continue
        relative_path = source.get("path")
        if relative_path:
            # Check source_type_map.json override before re-reading the file
            filename = Path(relative_path).name
            override = source_type_overrides.get(filename) or source_type_overrides.get(relative_path)
            if override and override != SOURCE_TYPE_UNTYPED:
                source_type_by_id[source_id] = override
                continue
            raw_path = raw_dir / relative_path
            if raw_path.exists():
                _, inferred_type, had_invalid_type = read_typed_source(raw_path)
                source_type_by_id[source_id] = inferred_type
                if had_invalid_type:
                    warnings.append(
                        f"Source {relative_path} declared an invalid source_type; defaulting to untyped."
                    )
                elif inferred_type == SOURCE_TYPE_UNTYPED:
                    warnings.append(
                        f"Source {relative_path} has no source_type frontmatter; defaulting to untyped."
                    )
                continue
        source_type_by_id[source_id] = SOURCE_TYPE_UNTYPED
        warnings.append(
            f"Could not infer source_type for {source_id} ({relative_path or 'unknown path'}); defaulting to untyped."
        )

    return source_type_by_id, warnings


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(read_text(path))


def load_active_evidence_gaps(workspace_dir: Path) -> Tuple[Optional[Dict[str, Any]], Optional[Path], List[str]]:
    candidate_paths = [
        workspace_dir / "champion_evidence_gaps.json",
        workspace_dir / "latest_evidence_gaps.json",
    ]
    warnings: List[str] = []
    for gap_path in candidate_paths:
        if not gap_path.exists():
            continue
        try:
            payload = read_json(gap_path)
        except Exception as exc:  # pragma: no cover - defensive path
            warnings.append(f"Could not parse {gap_path.name}: {exc}")
            continue

        gaps = payload.get("evidence_gaps")
        if not isinstance(gaps, list):
            warnings.append(f"{gap_path.name} exists but does not contain an evidence_gaps list.")
            continue
        project_dir = workspace_dir.parent
        active_gaps: list[dict[str, Any]] = []
        recovery_kind_counts: dict[str, int] = {}
        for gap in gaps:
            if not isinstance(gap, dict):
                continue
            recovery = evidence_gap_recovery(gap, project_dir=project_dir)
            if not recovery.get("active"):
                continue
            annotated_gap = canonicalize_evidence_gap_recovery_contract(
                gap,
                project_dir=project_dir,
            )
            recovery_kind = str(annotated_gap.get("recovery_kind") or "unknown")
            recovery_kind_counts[recovery_kind] = recovery_kind_counts.get(recovery_kind, 0) + 1
            active_gaps.append(annotated_gap)
        if not active_gaps:
            warnings.append(f"{gap_path.name} contains no active evidence gaps.")
            continue
        active_payload = dict(payload)
        active_payload["evidence_gaps"] = active_gaps
        active_payload["active_evidence_gap_count"] = len(active_gaps)
        active_payload["inactive_evidence_gap_count"] = len(gaps) - len(active_gaps)
        active_payload["recovery_kind_counts"] = recovery_kind_counts
        return active_payload, gap_path, warnings
    return None, None, warnings


def _evidence_fetch_model_hint(model_label: str) -> str:
    """Return a copy-pasteable Make MODEL alias for evidence recovery."""
    label = str(model_label or "").strip().lower()
    if not label or label == "unknown":
        return "gemini"
    if label.startswith("gemini"):
        return "gemini"
    if label.startswith("claude-opus"):
        return "claude-opus"
    if label.startswith("claude"):
        return "claude"
    if label.startswith("gpt-4.1-mini"):
        return "gpt4.1-mini"
    if label.startswith("gpt-4.1"):
        return "gpt4.1"
    if label.startswith("gpt-4o"):
        return "gpt4o"
    if label.startswith("kimi"):
        return "kimi"
    if label.startswith("grok"):
        return "grok"
    if label.startswith("deepseek"):
        return "deepseek"
    return label


def _evidence_gap_target(gap: Dict[str, Any]) -> str:
    return str(gap.get("target") or gap.get("gap_type") or "unspecified_target").strip()


def _evidence_gap_action_label(gap: Dict[str, Any]) -> str:
    severity = str(gap.get("severity") or "degrading").strip().lower()
    recovery_kind = str(gap.get("recovery_kind") or "unknown").strip()
    target = _evidence_gap_target(gap)
    return f"{severity}:{recovery_kind}:{target}"


def _select_next_evidence_gap(gaps: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    for severity in EVIDENCE_FETCH_SEVERITY_PRIORITY:
        public = [
            gap
            for gap in gaps
            if str(gap.get("severity") or "degrading").strip().lower() == severity
            and str(gap.get("recovery_kind") or "").strip() == PUBLIC_EVIDENCE_RECOVERY_KIND
        ]
        if public:
            return public[0]
    for severity in EVIDENCE_FETCH_SEVERITY_PRIORITY:
        local = [
            gap
            for gap in gaps
            if str(gap.get("severity") or "degrading").strip().lower() == severity
            and str(gap.get("recovery_kind") or "").strip() == LOCAL_VERIFICATION_RECOVERY_KIND
        ]
        if local:
            return local[0]
    for severity in EVIDENCE_FETCH_SEVERITY_PRIORITY:
        fallback = [
            gap
            for gap in gaps
            if str(gap.get("severity") or "degrading").strip().lower() == severity
        ]
        if fallback:
            return fallback[0]
    return gaps[0] if gaps else None


def build_evidence_gap_action_contract(
    project_name: str,
    gap_payload: Dict[str, Any],
) -> Dict[str, Any]:
    gaps = gap_payload.get("evidence_gaps", [])
    if not isinstance(gaps, list):
        gaps = []
    judge_model = str(gap_payload.get("judge_model", "") or "unknown")
    model_hint = _evidence_fetch_model_hint(judge_model)
    recovery_kind_counts: dict[str, int] = {
        PUBLIC_EVIDENCE_RECOVERY_KIND: 0,
        LOCAL_VERIFICATION_RECOVERY_KIND: 0,
    }
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        recovery_kind = str(gap.get("recovery_kind") or "unknown").strip()
        recovery_kind_counts[recovery_kind] = recovery_kind_counts.get(recovery_kind, 0) + 1

    next_gap = _select_next_evidence_gap([gap for gap in gaps if isinstance(gap, dict)])
    if next_gap is None:
        return {
            "schema": EVIDENCE_GAP_ACTION_SCHEMA,
            "project": project_name,
            "active_evidence_gap_count": 0,
            "recovery_kind_counts": recovery_kind_counts,
            "next_action": {
                "action_type": "none",
                "reason": "current evidence-gap rows are resolved, justified, inactive, or absent",
                "command": None,
                "selected_gap": None,
            },
        }

    severity = str(next_gap.get("severity") or "degrading").strip().lower()
    recovery_kind = str(next_gap.get("recovery_kind") or "unknown").strip()
    selected_gap = {
        "label": _evidence_gap_action_label(next_gap),
        "severity": severity,
        "recovery_kind": recovery_kind,
        "target": _evidence_gap_target(next_gap),
        "gap_type": next_gap.get("gap_type"),
        "required_surface": next_gap.get("required_surface"),
        "fetch_query": next_gap.get("fetch_query"),
        "recovery_channel": next_gap.get("recovery_channel"),
        "recovery_contract": next_gap.get("recovery_contract"),
    }
    if recovery_kind == PUBLIC_EVIDENCE_RECOVERY_KIND:
        command = (
            f"make evidence-fetch PROJECT={project_name} "
            f"SEVERITY={severity} MAX_FETCHES=3 "
            f"MODEL={model_hint} EVIDENCE_SEARCH_BACKEND=auto"
        )
        next_action = {
            "action_type": "public_source_recovery",
            "command": command,
            "boundary": "may fetch public evidence; does not run the autoresearch loop",
            "selected_gap": selected_gap,
        }
    elif recovery_kind == LOCAL_VERIFICATION_RECOVERY_KIND:
        command = f"ztare autoresearch trace --project {project_name} --rubric <rubric> --brief"
        next_action = {
            "action_type": "local_verification",
            "command": command,
            "boundary": "requires local verifier, fixture, preflight, receipt, or in-loop focus; do not use evidence-fetch",
            "selected_gap": selected_gap,
        }
    else:
        next_action = {
            "action_type": "unknown_recovery_kind",
            "command": None,
            "boundary": "inspect the gap row and add recovery_kind before automation",
            "selected_gap": selected_gap,
        }

    return {
        "schema": EVIDENCE_GAP_ACTION_SCHEMA,
        "project": project_name,
        "active_evidence_gap_count": len(gaps),
        "recovery_kind_counts": recovery_kind_counts,
        "next_action": next_action,
    }


def render_evidence_gap_brief(project_name: str, gap_payload: Dict[str, Any]) -> str:
    generated_on = str(gap_payload.get("generated_on", "") or "unknown")
    judge_model = str(gap_payload.get("judge_model", "") or "unknown")
    described_baseline = str(gap_payload.get("describes_baseline", "") or "unknown")
    artifact_role = str(gap_payload.get("artifact_role", "") or described_baseline or "unknown")
    regime_fingerprint = str(gap_payload.get("score_regime_fingerprint", "") or "unknown")
    weakest_point = str(gap_payload.get("weakest_point", "") or "").strip()
    cap_reason = str(gap_payload.get("cap_reason", "") or "").strip()
    cap_reason_detail = str(gap_payload.get("cap_reason_detail", "") or "").strip()
    boundary_detected = bool(gap_payload.get("evidence_boundary_ceiling_detected", False))
    score = gap_payload.get("score")
    gaps = gap_payload.get("evidence_gaps", [])

    grouped: Dict[str, List[Dict[str, Any]]] = {
        "blocking": [],
        "degrading": [],
        "enriching": [],
    }
    recovery_kind_counts: dict[str, int] = {
        PUBLIC_EVIDENCE_RECOVERY_KIND: 0,
        LOCAL_VERIFICATION_RECOVERY_KIND: 0,
    }
    for gap in gaps:
        severity = str(gap.get("severity", "degrading") or "degrading").lower()
        grouped.setdefault(severity, []).append(gap)
        recovery_kind = str(gap.get("recovery_kind") or "").strip()
        if recovery_kind:
            recovery_kind_counts[recovery_kind] = recovery_kind_counts.get(recovery_kind, 0) + 1
    strongest_public_severity = ""
    for severity in EVIDENCE_FETCH_SEVERITY_PRIORITY:
        if any(
            str(gap.get("recovery_kind") or "").strip() == PUBLIC_EVIDENCE_RECOVERY_KIND
            for gap in grouped.get(severity, [])
        ):
            strongest_public_severity = severity
            break
    model_hint = _evidence_fetch_model_hint(judge_model)
    action_contract = build_evidence_gap_action_contract(project_name, gap_payload)
    next_gap = (action_contract.get("next_action") or {}).get("selected_gap")

    lines: List[str] = [
        f"# Evidence Gap Brief: {project_name}",
        "",
        f"- Generated on: {generated_on}",
        f"- Judge model: {judge_model}",
        f"- Artifact role: {artifact_role}",
        f"- Describes baseline: {described_baseline}",
        f"- Regime fingerprint: {regime_fingerprint}",
        f"- Last score: {score}",
        f"- Evidence boundary detected: {'yes' if boundary_detected else 'no'}",
        f"- Active evidence gaps: {len(gaps)}",
        f"- Public-source recovery gaps: {recovery_kind_counts.get(PUBLIC_EVIDENCE_RECOVERY_KIND, 0)}",
        f"- Local-verification gaps: {recovery_kind_counts.get(LOCAL_VERIFICATION_RECOVERY_KIND, 0)}",
    ]
    if isinstance(next_gap, dict):
        next_recovery_kind = str(next_gap.get("recovery_kind") or "unknown").strip()
        next_target = str(next_gap.get("target") or "unspecified_target").strip()
        next_required_surface = str(next_gap.get("required_surface") or "").strip()
        next_fetch_query = str(next_gap.get("fetch_query") or "").strip()
        next_action = action_contract.get("next_action") if isinstance(action_contract.get("next_action"), dict) else {}
        next_command = str(next_action.get("command") or "").strip()
        lines.extend(
            [
                "",
                "## Next Action",
                "",
                f"- Selected gap: {next_gap.get('label')}",
                f"- Target: {next_target}",
                f"- Recovery kind: {next_recovery_kind}",
            ]
        )
        if next_required_surface:
            lines.append(f"- Required surface: {next_required_surface}")
        if next_recovery_kind == PUBLIC_EVIDENCE_RECOVERY_KIND:
            lines.append(f"- Command: `{next_command}`")
            if next_fetch_query:
                lines.append(f"- Query to recover: {next_fetch_query}")
            lines.append(
                "- Boundary: public-source recovery may fetch new evidence; "
                "it does not run the autoresearch loop."
            )
        elif next_recovery_kind == LOCAL_VERIFICATION_RECOVERY_KIND:
            lines.append(f"- Command: `{next_command}`")
            lines.append(
                "- Boundary: local-verification gaps need a local verifier, "
                "fixture, preflight, receipt, or in-loop focus; do not send "
                "them to evidence-fetch."
            )
        else:
            lines.append(
                "- Boundary: recovery kind is unknown; inspect the gap row and "
                "add `recovery_kind` before using automation."
            )
    if strongest_public_severity:
        lines.append(f"- Strongest public-source severity: {strongest_public_severity}")
        lines.append(
            "- Next public-source command: "
            f"`make evidence-fetch PROJECT={project_name} "
            f"SEVERITY={strongest_public_severity} MAX_FETCHES=3 "
            f"MODEL={model_hint} EVIDENCE_SEARCH_BACKEND=auto`"
        )
    elif recovery_kind_counts.get(LOCAL_VERIFICATION_RECOVERY_KIND, 0):
        lines.append(
            "- Next recovery class: local verification; do not use evidence-fetch "
            "until the local verifier gap is resolved or justified."
        )
    if cap_reason and cap_reason != "none":
        lines.append(f"- Cap reason: {cap_reason}")
    if cap_reason_detail:
        lines.append(f"- Cap detail: {cap_reason_detail}")
    if weakest_point:
        lines.extend(["", "## Current weakest point", "", weakest_point])

    for severity in ("blocking", "degrading", "enriching"):
        items = grouped.get(severity, [])
        lines.extend(["", f"## {severity.title()} gaps", ""])
        if not items:
            lines.append("- None.")
            continue
        for gap in items:
            lines.append(
                f"- [{gap.get('gap_type', 'other')}] {gap.get('target', 'unspecified_target')}"
            )
            description = str(gap.get("description", "") or "").strip()
            producer = str(gap.get("producer", "") or "").strip()
            producer_rationale = str(gap.get("producer_rationale", "") or "").strip()
            fetch_query = str(gap.get("fetch_query", "") or "").strip()
            if description:
                lines.append(f"  - Description: {description}")
            recovery_kind = str(gap.get("recovery_kind", "") or "").strip()
            if recovery_kind:
                lines.append(f"  - Recovery kind: {recovery_kind}")
            recovery_channel = str(gap.get("recovery_channel", "") or "").strip()
            if recovery_channel:
                lines.append(f"  - Recovery channel: {recovery_channel}")
            required_surface = str(gap.get("required_surface", "") or "").strip()
            if required_surface:
                lines.append(f"  - Required surface: {required_surface}")
            if producer:
                lines.append(f"  - Producer: {producer}")
            if producer_rationale:
                lines.append(f"  - Why evidence-boundary: {producer_rationale}")
            if fetch_query:
                lines.append(f"  - Suggested adversarial query: {fetch_query}")

    return "\n".join(lines).strip() + "\n"


def render_no_active_evidence_gap_brief(
    project_name: str,
    *,
    warnings: List[str] | None = None,
) -> str:
    lines = [
        f"# Evidence Gap Brief: {project_name}",
        "",
        "- Active evidence gaps: 0",
        "- Public-source recovery gaps: 0",
        "- Local-verification gaps: 0",
        "- Next recovery class: none; current evidence-gap rows are resolved, justified, or inactive.",
    ]
    if warnings:
        lines.extend(["", "## Inactive Gap Notes", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines).strip() + "\n"


def _source_replay_rows(compiler_manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for source in compiler_manifest.get("sources", []):
        if not isinstance(source, dict):
            continue
        rows.append(
            {
                "source_id": source.get("source_id"),
                "path": source.get("path"),
                "kind": source.get("kind"),
                "source_type": source.get("source_type"),
                "full_sha256": source.get("full_sha256") or source.get("sha256"),
                "chars_used": source.get("chars_used"),
                "truncated": source.get("truncated"),
            }
        )
    return rows


def _evidence_support_projection(packet: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "project": packet.get("project"),
        "immutable_ground_truth": packet.get("immutable_ground_truth", []),
        "numerical_ranges_and_constraints": packet.get("numerical_ranges_and_constraints", []),
        "identified_contradictions": packet.get("identified_contradictions", []),
        "epistemic_voids": packet.get("epistemic_voids", []),
        "provenance": packet.get("provenance", []),
        "candidate_claims_to_test": packet.get("candidate_claims_to_test", []),
    }


def build_evidence_replay_manifest(
    *,
    project_dir: Path,
    workspace_dir: Path,
    packet: Dict[str, Any],
    compiler_manifest: Dict[str, Any],
    output_path: Path,
    audit_copy_path: Path,
    packet_output_path: Path,
    evidence_gap_action_path: Path,
) -> Dict[str, Any]:
    mode = str(compiler_manifest.get("mode") or "unknown")
    source_rows = _source_replay_rows(compiler_manifest)
    source_binding = {
        "source_count": len(source_rows),
        "sources": source_rows,
    }
    input_projection: Dict[str, Any] = {
        "mode": mode,
        "project": project_dir.name,
        "source_binding": source_binding,
    }
    if mode == "raw":
        input_projection.update(
            {
                "model_family": compiler_manifest.get("model_family"),
                "model_id": compiler_manifest.get("model_id"),
                "prompt_sha256": compiler_manifest.get("prompt_sha256"),
                "cache_key": compiler_manifest.get("cache_key"),
                "cache_schema_version": compiler_manifest.get("cache_schema_version"),
            }
        )
    else:
        snapshot_path = workspace_dir / "workspace_snapshot.json"
        input_projection["workspace_snapshot_path"] = repo_display_path(snapshot_path)
        input_projection["workspace_snapshot_sha256"] = (
            sha256_file(snapshot_path) if snapshot_path.exists() else None
        )

    support_projection = _evidence_support_projection(packet)
    replay_mode = (
        "raw_cache_replay"
        if mode == "raw"
        else "workspace_snapshot_replay"
        if mode == "workspace"
        else "unknown"
    )
    artifact_hashes: Dict[str, Any] = {
        "evidence_txt": sha256_file(output_path) if output_path.exists() else None,
        "audit_copy": sha256_file(audit_copy_path) if audit_copy_path.exists() else None,
        "packet_json": sha256_file(packet_output_path) if packet_output_path.exists() else None,
        "evidence_gap_action": (
            sha256_file(evidence_gap_action_path)
            if evidence_gap_action_path.exists()
            else None
        ),
    }
    if mode == "raw":
        cache_entry_dir = compiler_manifest.get("cache_entry_dir")
        artifact_hashes["raw_cache_packet"] = (
            sha256_file(Path(cache_entry_dir) / "packet.json")
            if cache_entry_dir and (Path(cache_entry_dir) / "packet.json").exists()
            else None
        )
        artifact_hashes["raw_cache_manifest"] = (
            sha256_file(Path(cache_entry_dir) / "manifest.json")
            if cache_entry_dir and (Path(cache_entry_dir) / "manifest.json").exists()
            else None
        )

    return {
        "schema": EVIDENCE_REPLAY_MANIFEST_SCHEMA,
        "project": project_dir.name,
        "mode": mode,
        "generated_on": compiler_manifest.get("generated_on"),
        "replay_mode": replay_mode,
        "replay_rule": (
            "Compare input_binding_sha256 and support_binding_sha256; rendered "
            "evidence markdown may include date metadata and should not be the "
            "only replay key."
        ),
        "input_binding_sha256": stable_json_sha256(input_projection),
        "source_binding_sha256": stable_json_sha256(source_binding),
        "packet_sha256": stable_json_sha256(packet),
        "support_binding_sha256": stable_json_sha256(support_projection),
        "input_projection": input_projection,
        "support_projection_counts": {
            "immutable_ground_truth": len(support_projection["immutable_ground_truth"]),
            "numerical_ranges_and_constraints": len(support_projection["numerical_ranges_and_constraints"]),
            "identified_contradictions": len(support_projection["identified_contradictions"]),
            "epistemic_voids": len(support_projection["epistemic_voids"]),
            "provenance": len(support_projection["provenance"]),
            "candidate_claims_to_test": len(support_projection["candidate_claims_to_test"]),
        },
        "artifact_hashes": artifact_hashes,
        "warnings": list(compiler_manifest.get("warnings", [])),
    }


def load_prompt(name: str) -> str:
    return read_text(PROMPTS_DIR / name).strip()


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected a positive integer, got {value!r}") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"expected a positive integer, got {value!r}")
    return parsed


def resolve_project_dir(project_arg: str) -> Path:
    candidate = Path(project_arg)
    if candidate.exists():
        return candidate.resolve()
    fallback = PROJECTS_DIR / project_arg
    if fallback.exists():
        return fallback.resolve()
    raise FileNotFoundError(f"Project not found: {project_arg}")


class LLMClient:
    def __init__(
        self,
        model_family: str,
        *,
        timeout_seconds: int = DEFAULT_EVIDENCE_LLM_TIMEOUT_SECONDS,
        retries: int = DEFAULT_EVIDENCE_LLM_RETRIES,
    ):
        if model_family not in MODEL_MAP:
            raise ValueError(f"Unsupported model family: {model_family}")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if retries <= 0:
            raise ValueError("retries must be positive")
        self.model_family = model_family
        self.model_id = MODEL_MAP[model_family]
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.runtime = LLMRuntime()

    def call(self, prompt: str, retries: Optional[int] = None) -> str:
        attempt_count = self.retries if retries is None else retries
        if attempt_count <= 0:
            raise ValueError("retries must be positive")
        try:
            dbg(
                f"LLM call: family={self.model_family} model={self.model_id} "
                f"retries={attempt_count} timeout_seconds={self.timeout_seconds}"
            )
            response = self.runtime.call_text(
                prompt,
                model_id=self.model_id,
                retries=attempt_count,
                timeout_seconds=self.timeout_seconds,
                request_label="compile_evidence request",
                progress_printer=dbg,
                transient_wait_seconds=5,
                timeout_wait_seconds=2,
            )
            return response.text
        except LLMRuntimeError as exc:
            raise CompileEvidenceError(
                f"LLM call failed after {attempt_count} attempts: {exc}",
                phase="llm_call",
                model_family=self.model_family,
                model_id=self.model_id,
                transient=exc.transient,
                status_code=exc.status_code,
            ) from exc


def collect_sources(
    raw_dir: Path,
    max_files: int,
    max_chars_per_file: int,
    max_total_chars: int,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    sources: List[Dict[str, Any]] = []
    total_chars = 0

    source_type_overrides, type_map_warnings = load_source_type_map_with_warnings(raw_dir)
    warnings.extend(type_map_warnings)

    all_files = sorted(path for path in raw_dir.rglob("*") if path.is_file())
    # Exclude source_type_map.json itself from ingest
    supported_files = [
        path for path in all_files
        if path.suffix.lower() in TEXT_EXTENSIONS and path.name != SOURCE_TYPE_MAP_FILENAME
    ]
    skipped_files = [path for path in all_files if path.suffix.lower() not in TEXT_EXTENSIONS]

    if skipped_files:
        warnings.append(
            f"Skipped {len(skipped_files)} non-text files. Convert PDFs/images to markdown or text before compiling evidence."
        )

    for idx, path in enumerate(supported_files[:max_files], start=1):
        raw_text, source_type, had_invalid_type = read_typed_source(path)
        raw_text = raw_text.strip()
        if not raw_text:
            warnings.append(f"Skipped empty file: {path.relative_to(raw_dir)}")
            continue

        # Apply source_type_map.json override for untyped files
        if source_type == SOURCE_TYPE_UNTYPED:
            relative = str(path.relative_to(raw_dir))
            override = source_type_overrides.get(path.name) or source_type_overrides.get(relative)
            if override and override != SOURCE_TYPE_UNTYPED:
                source_type = override
            elif had_invalid_type:
                warnings.append(
                    f"Source {relative} declared an invalid source_type; defaulting to untyped."
                )
            else:
                warnings.append(
                    f"Source {relative} has no source_type frontmatter; defaulting to untyped."
                )
        elif had_invalid_type:
            warnings.append(
                f"Source {path.relative_to(raw_dir)} declared an invalid source_type; defaulting to untyped."
            )

        remaining = max_total_chars - total_chars
        if remaining <= 0:
            warnings.append("Stopped ingest because max_total_chars budget was reached.")
            break

        trimmed = raw_text[: min(max_chars_per_file, remaining)]
        truncated = len(trimmed) < len(raw_text)
        if truncated:
            warnings.append(f"Truncated {path.relative_to(raw_dir)} to {len(trimmed)} characters.")

        source_hash = sha256_text(raw_text)
        source = {
            "source_id": f"S{idx:03d}",
            "path": str(path.relative_to(raw_dir)),
            "kind": path.suffix.lower().lstrip(".") or "text",
            "source_type": source_type,
            "sha256": source_hash,
            "full_sha256": source_hash,
            "chars_used": len(trimmed),
            "truncated": truncated,
            "content": trimmed,
        }
        sources.append(source)
        total_chars += len(trimmed)

    if len(supported_files) > max_files:
        warnings.append(
            f"Read only the first {max_files} supported files out of {len(supported_files)}. Increase --max-files if needed."
        )

    return sources, warnings


def enforce_raw_source_preflight(sources: List[Dict[str, Any]], warnings: List[str]) -> None:
    invalid_warning_markers = (
        "invalid source_type",
        f"{SOURCE_TYPE_MAP_FILENAME} is not valid JSON",
        f"{SOURCE_TYPE_MAP_FILENAME} must be a JSON object",
        f"{SOURCE_TYPE_MAP_FILENAME} entries must map",
    )
    invalid_type_warnings = [
        warning
        for warning in warnings
        if any(marker in warning for marker in invalid_warning_markers)
    ]
    if invalid_type_warnings:
        raise CompileEvidenceError(
            "source preflight failed: " + "; ".join(invalid_type_warnings),
            phase="source_preflight",
        )
    if not any(source.get("source_type") == SOURCE_TYPE_EVIDENCE for source in sources):
        raise CompileEvidenceError(
            "source preflight failed: no source_evidence file is present",
            phase="source_preflight",
        )


def build_prompt(project_name: str, compiler_date: str, sources: List[Dict[str, Any]]) -> str:
    sections = [load_prompt("compile_evidence.md"), f"Project name: {project_name}", f"Compiler date: {compiler_date}", "Raw sources:"]
    for source in sources:
        sections.extend(
            [
                f"### SOURCE {source['source_id']}",
                f"Path: {source['path']}",
                f"Kind: {source['kind']}",
                f"Source type: {source['source_type']}",
                f"Truncated: {'yes' if source['truncated'] else 'no'}",
                "Contents:",
                source["content"],
            ]
        )
    return "\n\n".join(sections)


def format_source_ids(source_ids: List[str]) -> str:
    cleaned = [sid for sid in source_ids if sid]
    return ", ".join(cleaned) if cleaned else "none"


def render_evidence_markdown(packet: Dict[str, Any], project_name: str, compiler_date: str) -> str:
    lines: List[str] = [
        f"{project_name.upper()} — COMPILED EVIDENCE ({compiler_date})",
        "",
        "This file is a structured evidence brief for adversarial validation.",
        "It preserves contradictions and unknowns instead of smoothing them away.",
        "",
        "# 1. IMMUTABLE GROUND TRUTH",
    ]

    ground_truth = packet.get("immutable_ground_truth", [])
    if ground_truth:
        for item in ground_truth:
            statement = item.get("statement", "").strip()
            strength = item.get("strength", "").strip()
            source_ids = format_source_ids(item.get("source_ids", []))
            if statement:
                lines.append(f"- {statement} [Strength: {strength}; Sources: {source_ids}]")
    else:
        lines.append("- None identified.")

    lines.extend(["", "# 2. NUMERICAL RANGES & CONSTRAINTS (KEY VARIABLES / CONSTRAINTS)"])
    constraints = packet.get("numerical_ranges_and_constraints", [])
    if constraints:
        for item in constraints:
            name = item.get("name", "").strip()
            value_or_range = item.get("value_or_range", "").strip()
            units = item.get("units", "").strip()
            kind = item.get("kind", "").strip()
            notes = item.get("notes", "").strip()
            source_ids = format_source_ids(item.get("source_ids", []))
            value_part = value_or_range or "unspecified"
            unit_part = f" {units}" if units and units not in {"n/a", "none"} else ""
            note_part = f" | Notes: {notes}" if notes else ""
            lines.append(f"- {name}: {value_part}{unit_part} | Kind: {kind} | Sources: {source_ids}{note_part}")
    else:
        lines.append("- None identified.")

    lines.extend(["", "# 3. IDENTIFIED CONTRADICTIONS"])
    contradictions = packet.get("identified_contradictions", [])
    if contradictions:
        for item in contradictions:
            topic = item.get("topic", "").strip()
            claim_a = item.get("claim_a", "").strip()
            claim_b = item.get("claim_b", "").strip()
            why_it_matters = item.get("why_it_matters", "").strip()
            src_a = format_source_ids(item.get("source_ids_a", []))
            src_b = format_source_ids(item.get("source_ids_b", []))
            lines.append(f"- {topic}")
            lines.append(f"  - Claim A: {claim_a} [Sources: {src_a}]")
            lines.append(f"  - Claim B: {claim_b} [Sources: {src_b}]")
            if why_it_matters:
                lines.append(f"  - Why it matters: {why_it_matters}")
    else:
        lines.append("- None identified.")

    lines.extend(["", "# 4. EPISTEMIC VOIDS (OPEN PROBLEMS / UNKNOWNS)"])
    voids = packet.get("epistemic_voids", [])
    if voids:
        for item in voids:
            unknown = item.get("unknown", "").strip()
            why_it_matters = item.get("why_it_matters", "").strip()
            blocking = item.get("blocking", "").strip()
            lines.append(f"- {unknown}")
            if why_it_matters:
                lines.append(f"  - Why it matters: {why_it_matters}")
            if blocking:
                lines.append(f"  - Blocking effect: {blocking}")
    else:
        lines.append("- None identified.")

    lines.extend(["", "# 5. PROVENANCE"])
    provenance = packet.get("provenance", [])
    if provenance:
        for item in provenance:
            source_id = item.get("source_id", "").strip()
            path = item.get("path", "").strip()
            kind = item.get("kind", "").strip()
            source_type = item.get("source_type", "").strip()
            summary = item.get("summary", "").strip()
            type_part = f" | {source_type}" if source_type else ""
            lines.append(f"- {source_id} | {path} | {kind}{type_part}")
            if summary:
                lines.append(f"  - Summary: {summary}")
    else:
        lines.append("- None identified.")

    lines.extend(["", "# 6. CANDIDATE CLAIMS TO TEST"])
    claims = packet.get("candidate_claims_to_test", [])
    if claims:
        for idx, item in enumerate(claims, start=1):
            claim = item.get("claim", "").strip()
            why_testable = item.get("why_testable", "").strip()
            depends_on = [dep for dep in item.get("depends_on", []) if dep]
            source_ids = format_source_ids(item.get("source_ids", []))
            priority = item.get("priority", "").strip()
            lines.append(f"{idx}. {claim}")
            if why_testable:
                lines.append(f"   Why testable: {why_testable}")
            if depends_on:
                lines.append(f"   Depends on: {', '.join(depends_on)}")
            lines.append(f"   Priority: {priority} | Sources: {source_ids}")
    else:
        lines.append("- None identified.")

    return "\n".join(lines).strip() + "\n"


def validate_packet_shape(packet: Dict[str, Any]) -> None:
    required_keys = [
        "project",
        "compiler_summary",
        "immutable_ground_truth",
        "numerical_ranges_and_constraints",
        "identified_contradictions",
        "epistemic_voids",
        "provenance",
        "candidate_claims_to_test",
    ]
    missing = [key for key in required_keys if key not in packet]
    if missing:
        raise ValueError(f"Compiled evidence is missing required keys: {', '.join(missing)}")


def load_workspace_packet(workspace_dir: Path) -> Dict[str, Any]:
    snapshot_path = workspace_dir / "workspace_snapshot.json"
    if not snapshot_path.exists():
        project_name = workspace_dir.parent.name
        raise FileNotFoundError(
            f"Workspace snapshot not found: {snapshot_path}\n"
            f"Run evidence-prepare (workspace-update + evidence-compile in one step):\n"
            f"  make evidence-prepare PROJECT={project_name} MODEL=<model>"
        )
    packet = read_json(snapshot_path)
    validate_packet_shape(packet)
    return packet


def build_raw_compile_cache_key(
    *,
    project_dir: Path,
    model: str,
    max_files: int,
    max_chars_per_file: int,
    max_total_chars: int,
    sources: List[Dict[str, Any]],
) -> str:
    prompt_hash = sha256_text(load_prompt("compile_evidence.md"))
    payload = {
        "schema_version": RAW_COMPILE_CACHE_SCHEMA_VERSION,
        "mode": "raw",
        "project_name": project_dir.name,
        "model_family": model,
        "model_id": MODEL_MAP[model],
        "prompt_sha256": prompt_hash,
        "max_files": max_files,
        "max_chars_per_file": max_chars_per_file,
        "max_total_chars": max_total_chars,
        "sources": [
            {
                "path": source["path"],
                "kind": source["kind"],
                "source_type": source["source_type"],
                "full_sha256": source["full_sha256"],
                "chars_used": source["chars_used"],
                "truncated": source["truncated"],
            }
            for source in sources
        ],
    }
    return sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def load_raw_compile_cache_index(workspace_dir: Path) -> Dict[str, Any]:
    index_path = workspace_dir / RAW_COMPILE_CACHE_INDEX
    if not index_path.exists():
        return {
            "schema_version": RAW_COMPILE_CACHE_SCHEMA_VERSION,
            "entries": {},
        }
    try:
        payload = read_json(index_path)
    except Exception:  # noqa: BLE001
        return {
            "schema_version": RAW_COMPILE_CACHE_SCHEMA_VERSION,
            "entries": {},
        }
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        return {
            "schema_version": RAW_COMPILE_CACHE_SCHEMA_VERSION,
            "entries": {},
        }
    return payload


def write_raw_compile_cache_index(workspace_dir: Path, payload: Dict[str, Any]) -> Path:
    index_path = workspace_dir / RAW_COMPILE_CACHE_INDEX
    write_json(index_path, payload)
    return index_path


def raw_compile_cache_entry_dir(workspace_dir: Path, cache_key: str) -> Path:
    return workspace_dir / RAW_COMPILE_CACHE_DIRNAME / cache_key


def load_raw_compile_cache_entry(
    *,
    workspace_dir: Path,
    cache_key: str,
) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    entry_dir = raw_compile_cache_entry_dir(workspace_dir, cache_key)
    packet_path = entry_dir / "packet.json"
    manifest_path = entry_dir / "manifest.json"
    if not packet_path.exists() or not manifest_path.exists():
        return None
    packet = read_json(packet_path)
    validate_packet_shape(packet)
    manifest = read_json(manifest_path)
    return packet, manifest


def persist_raw_compile_cache_entry(
    *,
    workspace_dir: Path,
    cache_key: str,
    packet: Dict[str, Any],
    manifest: Dict[str, Any],
    evidence_text: str,
) -> Path:
    entry_dir = raw_compile_cache_entry_dir(workspace_dir, cache_key)
    write_json(entry_dir / "packet.json", packet)
    write_json(entry_dir / "manifest.json", manifest)
    write_text(entry_dir / "evidence.txt", evidence_text)
    return entry_dir


def write_latest_compile_cache_hit(
    *,
    workspace_dir: Path,
    cache_key: str,
    entry_dir: Path,
    model: str,
    source_count: int,
    generated_on: str,
) -> Path:
    hit_path = workspace_dir / LATEST_COMPILE_CACHE_HIT
    write_json(
        hit_path,
        {
            "schema_version": RAW_COMPILE_CACHE_SCHEMA_VERSION,
            "mode": "raw",
            "cache_key": cache_key,
            "entry_dir": str(entry_dir),
            "model_family": model,
            "model_id": MODEL_MAP[model],
            "source_count": source_count,
            "reused_on": generated_on,
        },
    )
    return hit_path


def clear_latest_compile_cache_hit(workspace_dir: Path) -> None:
    hit_path = workspace_dir / LATEST_COMPILE_CACHE_HIT
    if hit_path.exists():
        hit_path.unlink()


def compile_from_raw(
    *,
    project_dir: Path,
    raw_dir: Path,
    workspace_dir: Path,
    model: str,
    max_files: int,
    max_chars_per_file: int,
    max_total_chars: int,
    llm_timeout_seconds: int = DEFAULT_EVIDENCE_LLM_TIMEOUT_SECONDS,
    llm_retries: int = DEFAULT_EVIDENCE_LLM_RETRIES,
) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw source directory not found: {raw_dir}")

    sources, warnings = collect_sources(
        raw_dir=raw_dir,
        max_files=max_files,
        max_chars_per_file=max_chars_per_file,
        max_total_chars=max_total_chars,
    )
    if not sources:
        raise RuntimeError(f"No supported text-like source files found in {raw_dir}")
    enforce_raw_source_preflight(sources, warnings)

    compiler_date = time.strftime("%B %d, %Y")
    workspace_dir.mkdir(parents=True, exist_ok=True)
    cache_key = build_raw_compile_cache_key(
        project_dir=project_dir,
        model=model,
        max_files=max_files,
        max_chars_per_file=max_chars_per_file,
        max_total_chars=max_total_chars,
        sources=sources,
    )
    cache_index = load_raw_compile_cache_index(workspace_dir)
    cached = load_raw_compile_cache_entry(workspace_dir=workspace_dir, cache_key=cache_key)
    if cached is not None:
        cached_packet, cached_manifest = cached
        cached_entry_dir = raw_compile_cache_entry_dir(workspace_dir, cache_key)
        write_latest_compile_cache_hit(
            workspace_dir=workspace_dir,
            cache_key=cache_key,
            entry_dir=cached_entry_dir,
            model=model,
            source_count=len(sources),
            generated_on=compiler_date,
        )
        manifest = copy.deepcopy(cached_manifest)
        manifest["generated_on"] = compiler_date
        manifest["cache_hit"] = True
        manifest["cache_key"] = cache_key
        manifest["cache_entry_dir"] = str(cached_entry_dir)
        manifest["cache_original_generated_on"] = cached_manifest.get("generated_on")
        evidence_text = render_evidence_markdown(cached_packet, project_dir.name, compiler_date)
        return cached_packet, manifest, evidence_text

    clear_latest_compile_cache_hit(workspace_dir)
    prompt = build_prompt(project_dir.name, compiler_date, sources)
    dbg(f"Source count={len(sources)} prompt_chars={len(prompt)} cache_key={cache_key}")

    llm = LLMClient(model, timeout_seconds=llm_timeout_seconds, retries=llm_retries)
    raw_response = llm.call(prompt)
    packet = utils.parse_llm_json(raw_response)
    validate_packet_shape(packet)
    source_type_by_id, type_warnings = resolve_source_type_map(project_dir=project_dir, sources=sources)
    warnings.extend(type_warnings)
    warnings.extend(filter_packet_by_source_types(packet, source_type_by_id))

    manifest = {
        "project_dir": repo_display_path(project_dir),
        "mode": "raw",
        "raw_dir": repo_display_path(raw_dir),
        "model_family": model,
        "model_id": MODEL_MAP[model],
        "generated_on": compiler_date,
        "prompt_path": repo_display_path(PROMPTS_DIR / "compile_evidence.md"),
        "prompt_sha256": sha256_text(load_prompt("compile_evidence.md")),
        "cache_schema_version": RAW_COMPILE_CACHE_SCHEMA_VERSION,
        "cache_hit": False,
        "cache_key": cache_key,
        "source_count": len(sources),
        "sources": [{k: v for k, v in source.items() if k != "content"} for source in sources],
        "warnings": warnings,
    }
    evidence_text = render_evidence_markdown(packet, project_dir.name, compiler_date)
    cache_entry_dir = persist_raw_compile_cache_entry(
        workspace_dir=workspace_dir,
        cache_key=cache_key,
        packet=packet,
        manifest=manifest,
        evidence_text=evidence_text,
    )
    cache_index.setdefault("entries", {})
    cache_index["schema_version"] = RAW_COMPILE_CACHE_SCHEMA_VERSION
    cache_index["entries"][cache_key] = {
        "cache_key": cache_key,
        "entry_dir": repo_display_path(cache_entry_dir),
        "generated_on": compiler_date,
        "model_family": model,
        "model_id": MODEL_MAP[model],
        "source_count": len(sources),
    }
    write_raw_compile_cache_index(workspace_dir, cache_index)
    manifest["cache_entry_dir"] = repo_display_path(cache_entry_dir)
    return packet, manifest, evidence_text


def compile_from_workspace(
    *,
    project_dir: Path,
    workspace_dir: Path,
) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    compiler_date = time.strftime("%B %d, %Y")
    packet = copy.deepcopy(load_workspace_packet(workspace_dir))

    meta_path = workspace_dir / "workspace_meta.json"
    source_index_path = workspace_dir / "source_index.json"
    manifest: Dict[str, Any] = {
        "project_dir": repo_display_path(project_dir),
        "mode": "workspace",
        "workspace_dir": repo_display_path(workspace_dir),
        "generated_on": compiler_date,
        "source_count": 0,
        "warnings": [],
    }
    if meta_path.exists():
        manifest["workspace_meta"] = read_json(meta_path)
    if source_index_path.exists():
        index_payload = read_json(source_index_path)
        sources = index_payload.get("sources", [])
        manifest["sources"] = sources
        manifest["source_count"] = len(sources)
    source_type_by_id, type_warnings = resolve_source_type_map(
        project_dir=project_dir,
        sources=manifest.get("sources", []),
    )
    manifest["warnings"] = type_warnings + filter_packet_by_source_types(packet, source_type_by_id)

    evidence_text = render_evidence_markdown(packet, project_dir.name, compiler_date)
    return packet, manifest, evidence_text


def compile_failure_payload(
    *,
    project_dir: Path,
    mode: str,
    model: str,
    error: Exception,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "project_dir": repo_display_path(project_dir),
        "mode": mode,
        "model_family": model,
        "model_id": MODEL_MAP.get(model, model),
        "failed_on": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "error_type": type(error).__name__,
        "message": str(error),
        "fail_closed": True,
    }
    if isinstance(error, CompileEvidenceError):
        payload["phase"] = error.phase
        payload["transient"] = error.transient
        if error.status_code is not None:
            payload["status_code"] = error.status_code
        if error.model_family:
            payload["model_family"] = error.model_family
        if error.model_id:
            payload["model_id"] = error.model_id
    return payload


def write_compile_failure_artifact(
    *,
    workspace_dir: Path,
    project_dir: Path,
    mode: str,
    model: str,
    error: Exception,
) -> Path:
    failure_path = workspace_dir / COMPILE_FAILURE_ARTIFACT
    write_json(
        failure_path,
        compile_failure_payload(
            project_dir=project_dir,
            mode=mode,
            model=model,
            error=error,
        ),
    )
    return failure_path


def clear_compile_failure_artifact(workspace_dir: Path) -> None:
    failure_path = workspace_dir / COMPILE_FAILURE_ARTIFACT
    if failure_path.exists():
        failure_path.unlink()


def print_compile_failure_summary(failure_path: Path, error: Exception) -> None:
    print("Compile evidence failed closed.")
    print(f"Failure artifact: {failure_path}")
    print(f"Reason: {error}")
    if isinstance(error, CompileEvidenceError):
        if error.transient:
            print("Transient provider failure detected. Retry later or switch model.")
        if error.status_code is not None:
            print(f"Status code: {error.status_code}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile raw sources or a workspace snapshot into a structured evidence.txt for ZTARE.")
    parser.add_argument("--project", required=True, help="Project name under projects/ or an explicit project path.")
    parser.add_argument("--raw-dir", help="Optional explicit raw source directory. Defaults to <project>/raw.")
    parser.add_argument("--workspace-dir", help="Optional explicit workspace directory. Defaults to <project>/workspace.")
    parser.add_argument(
        "--mode",
        choices=["auto", "workspace", "raw"],
        default="auto",
        help="Compilation mode. 'auto' prefers workspace/ when present, otherwise falls back to raw/.",
    )
    parser.add_argument("--model", default=os.environ.get("ZTARE_MODEL", ""), choices=("", *sorted(MODEL_MAP.keys())))
    parser.add_argument(
        "--output",
        help="Optional explicit evidence output path. Defaults to <project>/evidence.txt (compiled_evidence.txt kept as audit copy).",
    )
    parser.add_argument(
        "--packet-output",
        help="Optional explicit JSON packet output path. Defaults to <project>/compiled_evidence_packet.json.",
    )
    parser.add_argument(
        "--provenance-output",
        help="Optional explicit compiler provenance output path. Defaults to <project>/compiled_evidence_provenance.json.",
    )
    parser.add_argument("--max-files", type=int, default=25, help="Maximum number of raw files to ingest.")
    parser.add_argument(
        "--max-chars-per-file",
        type=int,
        default=12000,
        help="Maximum characters to read from each source file.",
    )
    parser.add_argument(
        "--max-total-chars",
        type=int,
        default=100000,
        help="Maximum total character budget across all ingested sources.",
    )
    parser.add_argument(
        "--llm-timeout-seconds",
        type=positive_int,
        default=DEFAULT_EVIDENCE_LLM_TIMEOUT_SECONDS,
        help="Per-call LLM timeout for raw compilation and automatic workspace update.",
    )
    parser.add_argument(
        "--llm-retries",
        type=positive_int,
        default=DEFAULT_EVIDENCE_LLM_RETRIES,
        help="Per-call retry budget for raw compilation and automatic workspace update.",
    )
    parser.add_argument("--debug", action="store_true", help="Print debug details to stderr.")
    args = parser.parse_args()

    global DEBUG
    DEBUG = args.debug

    project_dir = resolve_project_dir(args.project)
    raw_dir = Path(args.raw_dir).resolve() if args.raw_dir else project_dir / "raw"
    workspace_dir = Path(args.workspace_dir).resolve() if args.workspace_dir else project_dir / "workspace"

    output_path = Path(args.output).resolve() if args.output else project_dir / "evidence.txt"
    audit_copy_path = project_dir / "compiled_evidence.txt"
    packet_output_path = (
        Path(args.packet_output).resolve() if args.packet_output else project_dir / "compiled_evidence_packet.json"
    )
    provenance_output_path = (
        Path(args.provenance_output).resolve()
        if args.provenance_output
        else project_dir / "compiled_evidence_provenance.json"
    )
    replay_manifest_path = project_dir / EVIDENCE_REPLAY_MANIFEST_FILENAME

    use_workspace = False
    if args.mode == "workspace":
        use_workspace = True
    elif args.mode == "raw":
        use_workspace = False
    else:
        use_workspace = (workspace_dir / "workspace_snapshot.json").exists()

    if not args.model and (not use_workspace or not (workspace_dir / "workspace_snapshot.json").exists()):
        parser.error("--model or ZTARE_MODEL is required for raw compilation or automatic workspace update.")

    # Auto-run workspace update if workspace mode is selected but snapshot is missing.
    if use_workspace and not (workspace_dir / "workspace_snapshot.json").exists():
        print("Workspace snapshot not found — running workspace-update automatically...")
        import subprocess

        update_cmd = [
            sys.executable,
            "-m",
            "ztare.workspace.update_workspace",
            "--project",
            args.project,
            "--model",
            args.model,
            "--llm-timeout-seconds",
            str(args.llm_timeout_seconds),
            "--llm-retries",
            str(args.llm_retries),
        ]
        if args.debug:
            update_cmd.append("--debug")
        result = subprocess.run(update_cmd, capture_output=False)
        if result.returncode != 0:
            project_name = project_dir.name
            print(
                f"ERROR: workspace-update failed (exit {result.returncode}).\n"
                f"Fix the error above, then run:\n"
                f"  make evidence-prepare PROJECT={project_name} MODEL={args.model}",
                file=sys.stderr,
            )
            return 1
        print()  # blank line before compile output

    try:
        if use_workspace:
            packet, compiler_manifest, evidence_text = compile_from_workspace(
                project_dir=project_dir,
                workspace_dir=workspace_dir,
            )
        else:
            packet, compiler_manifest, evidence_text = compile_from_raw(
                project_dir=project_dir,
                raw_dir=raw_dir,
                workspace_dir=workspace_dir,
                model=args.model,
                max_files=args.max_files,
                max_chars_per_file=args.max_chars_per_file,
                max_total_chars=args.max_total_chars,
                llm_timeout_seconds=args.llm_timeout_seconds,
                llm_retries=args.llm_retries,
            )
    except Exception as error:  # noqa: BLE001
        failure_path = write_compile_failure_artifact(
            workspace_dir=workspace_dir,
            project_dir=project_dir,
            mode="workspace" if use_workspace else "raw",
            model=args.model,
            error=error,
        )
        print_compile_failure_summary(failure_path, error)
        return 1

    clear_compile_failure_artifact(workspace_dir)

    write_text(output_path, evidence_text)
    if output_path != audit_copy_path:
        write_text(audit_copy_path, evidence_text)
    write_json(packet_output_path, packet)
    compiler_manifest["output_path"] = repo_display_path(output_path)
    compiler_manifest["output_sha256"] = sha256_file(output_path)
    compiler_manifest["audit_copy_path"] = repo_display_path(audit_copy_path)
    compiler_manifest["audit_copy_sha256"] = sha256_file(audit_copy_path)
    compiler_manifest["packet_output_path"] = repo_display_path(packet_output_path)
    compiler_manifest["packet_output_sha256"] = sha256_file(packet_output_path)

    gap_payload, gap_source_path, gap_warnings = load_active_evidence_gaps(workspace_dir)
    warnings = list(compiler_manifest.get("warnings", []))
    warnings.extend(gap_warnings)
    compiler_manifest["warnings"] = warnings
    evidence_gap_brief_path = workspace_dir / "evidence_gap_brief.md"
    evidence_gap_action_path = workspace_dir / EVIDENCE_GAP_ACTION_FILENAME
    if gap_payload:
        evidence_gap_action = build_evidence_gap_action_contract(project_dir.name, gap_payload)
        write_json(evidence_gap_action_path, evidence_gap_action)
        write_text(
            evidence_gap_brief_path,
            render_evidence_gap_brief(project_dir.name, gap_payload),
        )
        if gap_source_path is not None:
            compiler_manifest["evidence_gap_source_path"] = repo_display_path(gap_source_path)
            compiler_manifest["evidence_gap_baseline"] = gap_payload.get("describes_baseline", "unknown")
        compiler_manifest["evidence_gap_count"] = len(gap_payload.get("evidence_gaps", []))
    else:
        evidence_gap_action = build_evidence_gap_action_contract(
            project_dir.name,
            {"evidence_gaps": []},
        )
        write_json(evidence_gap_action_path, evidence_gap_action)
        write_text(
            evidence_gap_brief_path,
            render_no_active_evidence_gap_brief(
                project_dir.name,
                warnings=gap_warnings,
            ),
        )
        compiler_manifest["evidence_gap_count"] = 0
    compiler_manifest["evidence_gap_brief_path"] = repo_display_path(evidence_gap_brief_path)
    compiler_manifest["evidence_gap_action_path"] = repo_display_path(evidence_gap_action_path)

    replay_manifest = build_evidence_replay_manifest(
        project_dir=project_dir,
        workspace_dir=workspace_dir,
        packet=packet,
        compiler_manifest=compiler_manifest,
        output_path=output_path,
        audit_copy_path=audit_copy_path,
        packet_output_path=packet_output_path,
        evidence_gap_action_path=evidence_gap_action_path,
    )
    write_json(replay_manifest_path, replay_manifest)
    compiler_manifest["evidence_replay_manifest_path"] = repo_display_path(replay_manifest_path)
    compiler_manifest["evidence_replay_manifest_sha256"] = sha256_file(replay_manifest_path)
    compiler_manifest["support_binding_sha256"] = replay_manifest["support_binding_sha256"]
    compiler_manifest["input_binding_sha256"] = replay_manifest["input_binding_sha256"]

    write_json(provenance_output_path, compiler_manifest)

    print(f"Evidence: {output_path}")
    print(f"Evidence packet: {packet_output_path}")
    print(f"Compiler provenance: {provenance_output_path}")
    print(f"Evidence gap brief: {workspace_dir / 'evidence_gap_brief.md'}")
    print(f"Evidence gap action: {workspace_dir / EVIDENCE_GAP_ACTION_FILENAME}")
    print(f"Evidence replay manifest: {replay_manifest_path}")
    print(f"Mode: {'workspace' if use_workspace else 'raw'}")
    if not use_workspace:
        print(f"Cache: {'hit' if compiler_manifest.get('cache_hit') else 'miss'}")
        if compiler_manifest.get("cache_key"):
            print(f"Cache key: {compiler_manifest['cache_key']}")
    warnings = compiler_manifest.get("warnings", [])
    if warnings:
        print(f"Warnings: {len(warnings)}")
        for warning in warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
