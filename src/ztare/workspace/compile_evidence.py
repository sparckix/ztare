import argparse
import copy
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.ztare.common import utils
from src.ztare.common.llm_runtime import LLMRuntime, LLMRuntimeError, MODEL_MAP
from src.ztare.common.paths import PROJECTS_DIR, PROMPTS_DIR, REPO_ROOT


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
        return payload, gap_path, warnings
    return None, None, warnings


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
    for gap in gaps:
        severity = str(gap.get("severity", "degrading") or "degrading").lower()
        grouped.setdefault(severity, []).append(gap)

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
    ]
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
            if producer:
                lines.append(f"  - Producer: {producer}")
            if producer_rationale:
                lines.append(f"  - Why evidence-boundary: {producer_rationale}")
            if fetch_query:
                lines.append(f"  - Suggested adversarial query: {fetch_query}")

    return "\n".join(lines).strip() + "\n"


def load_prompt(name: str) -> str:
    return read_text(PROMPTS_DIR / name).strip()


def resolve_project_dir(project_arg: str) -> Path:
    candidate = Path(project_arg)
    if candidate.exists():
        return candidate.resolve()
    fallback = PROJECTS_DIR / project_arg
    if fallback.exists():
        return fallback.resolve()
    raise FileNotFoundError(f"Project not found: {project_arg}")


class LLMClient:
    def __init__(self, model_family: str):
        if model_family not in MODEL_MAP:
            raise ValueError(f"Unsupported model family: {model_family}")
        self.model_family = model_family
        self.model_id = MODEL_MAP[model_family]
        self.runtime = LLMRuntime()

    def call(self, prompt: str, retries: int = 4) -> str:
        try:
            dbg(f"LLM call: family={self.model_family} model={self.model_id} retries={retries}")
            response = self.runtime.call_text(
                prompt,
                model_id=self.model_id,
                retries=retries,
                timeout_seconds=300,
                request_label="compile_evidence request",
                progress_printer=dbg,
                transient_wait_seconds=5,
                timeout_wait_seconds=2,
            )
            return response.text
        except LLMRuntimeError as exc:
            raise CompileEvidenceError(
                f"LLM call failed after {retries} attempts: {exc}",
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

    all_files = sorted(path for path in raw_dir.rglob("*") if path.is_file())
    supported_files = [path for path in all_files if path.suffix.lower() in TEXT_EXTENSIONS]
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
        if source_type == SOURCE_TYPE_UNTYPED:
            warnings.append(
                f"Source {path.relative_to(raw_dir)} has no valid source_type frontmatter; defaulting to untyped."
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

        source = {
            "source_id": f"S{idx:03d}",
            "path": str(path.relative_to(raw_dir)),
            "kind": path.suffix.lower().lstrip(".") or "text",
            "source_type": source_type,
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

    lines.extend(["", "# 2. NUMERICAL RANGES & CONSTRAINTS (LOAD-BEARING VARIABLES / CONSTRAINTS)"])
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
        raise FileNotFoundError(f"Workspace snapshot not found: {snapshot_path}")
    packet = read_json(snapshot_path)
    validate_packet_shape(packet)
    return packet


def compile_from_raw(
    *,
    project_dir: Path,
    raw_dir: Path,
    model: str,
    max_files: int,
    max_chars_per_file: int,
    max_total_chars: int,
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

    compiler_date = time.strftime("%B %d, %Y")
    prompt = build_prompt(project_dir.name, compiler_date, sources)
    dbg(f"Source count={len(sources)} prompt_chars={len(prompt)}")

    llm = LLMClient(model)
    raw_response = llm.call(prompt)
    packet = utils.parse_llm_json(raw_response)
    validate_packet_shape(packet)
    source_type_by_id, type_warnings = resolve_source_type_map(project_dir=project_dir, sources=sources)
    warnings.extend(type_warnings)
    warnings.extend(filter_packet_by_source_types(packet, source_type_by_id))

    manifest = {
        "project_dir": str(project_dir),
        "mode": "raw",
        "raw_dir": str(raw_dir),
        "model_family": model,
        "model_id": MODEL_MAP[model],
        "generated_on": compiler_date,
        "prompt_path": str(PROMPTS_DIR / "compile_evidence.md"),
        "source_count": len(sources),
        "sources": [{k: v for k, v in source.items() if k != "content"} for source in sources],
        "warnings": warnings,
    }
    evidence_text = render_evidence_markdown(packet, project_dir.name, compiler_date)
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
        "project_dir": str(project_dir),
        "mode": "workspace",
        "workspace_dir": str(workspace_dir),
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
        "project_dir": str(project_dir),
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
    parser.add_argument("--model", default="gemini", choices=sorted(MODEL_MAP.keys()))
    parser.add_argument(
        "--output",
        help="Optional explicit evidence output path. Defaults to <project>/compiled_evidence.txt.",
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
    parser.add_argument("--debug", action="store_true", help="Print debug details to stderr.")
    args = parser.parse_args()

    global DEBUG
    DEBUG = args.debug

    project_dir = resolve_project_dir(args.project)
    raw_dir = Path(args.raw_dir).resolve() if args.raw_dir else project_dir / "raw"
    workspace_dir = Path(args.workspace_dir).resolve() if args.workspace_dir else project_dir / "workspace"

    output_path = Path(args.output).resolve() if args.output else project_dir / "compiled_evidence.txt"
    packet_output_path = (
        Path(args.packet_output).resolve() if args.packet_output else project_dir / "compiled_evidence_packet.json"
    )
    provenance_output_path = (
        Path(args.provenance_output).resolve()
        if args.provenance_output
        else project_dir / "compiled_evidence_provenance.json"
    )

    use_workspace = False
    if args.mode == "workspace":
        use_workspace = True
    elif args.mode == "raw":
        use_workspace = False
    else:
        use_workspace = (workspace_dir / "workspace_snapshot.json").exists()

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
                model=args.model,
                max_files=args.max_files,
                max_chars_per_file=args.max_chars_per_file,
                max_total_chars=args.max_total_chars,
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
    write_json(packet_output_path, packet)
    compiler_manifest["output_path"] = str(output_path)
    compiler_manifest["packet_output_path"] = str(packet_output_path)

    gap_payload, gap_source_path, gap_warnings = load_active_evidence_gaps(workspace_dir)
    warnings = list(compiler_manifest.get("warnings", []))
    warnings.extend(gap_warnings)
    compiler_manifest["warnings"] = warnings
    if gap_payload:
        evidence_gap_brief_path = workspace_dir / "evidence_gap_brief.md"
        write_text(
            evidence_gap_brief_path,
            render_evidence_gap_brief(project_dir.name, gap_payload),
        )
        if gap_source_path is not None:
            compiler_manifest["evidence_gap_source_path"] = str(gap_source_path)
            compiler_manifest["evidence_gap_baseline"] = gap_payload.get("describes_baseline", "unknown")
        compiler_manifest["evidence_gap_brief_path"] = str(evidence_gap_brief_path)
        compiler_manifest["evidence_gap_count"] = len(gap_payload.get("evidence_gaps", []))

    write_json(provenance_output_path, compiler_manifest)

    print(f"Evidence: {output_path}")
    print(f"Evidence packet: {packet_output_path}")
    print(f"Compiler provenance: {provenance_output_path}")
    if gap_payload:
        print(f"Evidence gap brief: {workspace_dir / 'evidence_gap_brief.md'}")
    print(f"Mode: {'workspace' if use_workspace else 'raw'}")
    warnings = compiler_manifest.get("warnings", [])
    if warnings:
        print(f"Warnings: {len(warnings)}")
        for warning in warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
