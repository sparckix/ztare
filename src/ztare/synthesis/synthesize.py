import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ztare.common import utils
from ztare.common.dispatch_model import dispatch_call_text
from ztare.common.llm_runtime import LLMRuntime, LLMRuntimeError, MODEL_MAP
from ztare.common.paths import PROJECTS_DIR, PROMPTS_DIR, RENDERERS_DIR, REPO_ROOT, RUBRICS_DIR


ROOT_DIR = REPO_ROOT

SYNTHESIS_DIRNAME = "synthesis"
CONTEXT_FILENAME = "context.json"
LEDGER_FILENAME = "ledger.json"
BRIEF_FILENAME = "brief.json"
HISTORY_SUMMARY_FILENAME = "history_summary.json"
QA_FILENAME = "qa.json"
CANDIDATE_REPORT_FILENAME = "Report.candidate.md"
FINAL_REPORT_FILENAME = "Report.md"
AUTORESEARCH_REVIEW_CONTEXT_FILENAME = "autoresearch_review_context.json"
REPORT_SUPPORT_CONTRACT_FILENAME = "report_support_contract.json"
BEST_ITERATION_RE = re.compile(r"best_iteration:\s*([A-Za-z0-9_.-]+)")
HISTORY_FAMILY_RE = re.compile(r"^\d+_iter\d+_score_[^_]+_(.+)$")

DEFAULT_QA_THRESHOLD = 85
DEFAULT_QA_REPAIR_ATTEMPTS = 2
ACTIVE_LLM: Optional["LLMClient"] = None
# User-provided, natural-language report direction (e.g. "lead with the downside case; keep it under one
# page; emphasise the unit economics"). Injected as a high-priority directive into the render + refine
# prompts, for BOTH templated and dynamic renderers. It steers STYLE/EMPHASIS/STRUCTURE-within-template,
# never the facts — the support contract still bounds every claim.
USER_INSTRUCTIONS: str = ""
ACTIVE_QA_LLM: Optional["LLMClient"] = None
ACTIVE_QA_THRESHOLD = DEFAULT_QA_THRESHOLD
ACTIVE_QA_REPAIR_ATTEMPTS = DEFAULT_QA_REPAIR_ATTEMPTS
DEBUG = False

QA_BLOCKING_ISSUE_TYPES = {
    "unsupported_addition",
    "unsupported_action",
    "unsupported_claim",
    "unsupported_metadata",
    "distortion",
    "overclaim",
    "generic_advice",
    "fabrication",
    "hallucination",
    "contradiction",
}

PROJECT_TYPE_DEFAULTS = {
    "startup": {
        "renderer_type": "founder_memo",
        "audience": "startup founder",
        "tone": "direct, founder-friendly",
    },
    "engine_architecture": {
        "renderer_type": "architectural_memo",
        "audience": "technical builder",
        "tone": "direct, technically rigorous",
    },
    "research_hypothesis": {
        "renderer_type": "research_note",
        "audience": "technical researcher",
        "tone": "concise, research-oriented",
    },
    "investment_thesis": {
        "renderer_type": "founder_memo",
        "audience": "investment-oriented operator",
        "tone": "concise, diligence-oriented",
    },
    "policy_scenario": {
        "renderer_type": "policy_essay",
        "audience": "policy analyst or decision-maker",
        "tone": "plainspoken, recommendation-oriented",
    },
    "general_analysis": {
        "renderer_type": "research_note",
        "audience": "technical reader",
        "tone": "concise, analytical",
    },
}

RENDERER_OVERRIDES = {
    "decision_brief": {
        "audience": "decision-maker",
        "tone": "compressed, decision-forcing",
    },
    "field_manual": {
        "audience": "case-method instructor or executive",
        "tone": "boardroom-plain, scannable, non-technical",
    },
    "teaching_note": {
        "audience": "case-method instructor preparing a single class",
        "tone": "operational, instructor-facing, project-specific",
    },
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_prompt(path: Path) -> str:
    return read_text(path).strip()


def prompt_hash(path: Path) -> str:
    return hashlib.sha1(read_text(path).encode("utf-8")).hexdigest()


def dbg(msg: str) -> None:
    if not DEBUG:
        return
    ts = time.strftime("%H:%M:%S")
    print(f"[synthesize {ts}] {msg}", file=sys.stderr)


def fmt_paths(paths: List[str], limit: int = 40) -> str:
    shown = paths[:limit]
    out = []
    for p in shown:
        try:
            size = Path(p).stat().st_size
            out.append(f"- {p} ({size} bytes)")
        except Exception:  # noqa: BLE001
            out.append(f"- {p}")
    if len(paths) > limit:
        out.append(f"- … ({len(paths) - limit} more)")
    return "\n".join(out)


def sidecar_text_path(path: Path, label: str) -> Path:
    return path.with_name(f"{path.stem}.{label}.txt")


def load_json_if_valid(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        payload = json.loads(read_text(path))
    except Exception:  # noqa: BLE001
        return None
    return payload if isinstance(payload, dict) else None


def repair_json_payload(raw_text: str, step: str) -> str:
    if ACTIVE_LLM is None:
        raise RuntimeError("ACTIVE_LLM is not configured.")
    prompt = "\n\n".join(
        [
            "You repair malformed JSON.",
            "Return strict valid JSON only.",
            "Do not add commentary, markdown fences, or explanation.",
            "Preserve the original keys, values, and structure as faithfully as possible.",
            "Only make the minimum syntax repairs needed to produce valid JSON.",
            f"Stage: {step}",
            "Malformed JSON:",
            raw_text,
        ]
    )
    return ACTIVE_LLM.call(prompt, retries=2).strip()


def parse_json_step_response(
    raw_text: str,
    *,
    step: str,
    output_path: Path,
    failure_message: str,
    cache_validator: Optional[Callable[[Dict[str, Any]], bool]] = None,
) -> Dict[str, Any]:
    try:
        return utils.parse_llm_json(raw_text)
    except Exception as initial_exc:  # noqa: BLE001
        raw_path = sidecar_text_path(output_path, "raw")
        write_text(raw_path, raw_text)
        dbg(f"{step}: saved malformed JSON payload to {raw_path}")

        repaired_path = sidecar_text_path(output_path, "repaired")
        repair_note = "no repaired payload was written"
        last_exc: Exception = initial_exc
        try:
            repaired = repair_json_payload(raw_text, step)
            write_text(repaired_path, repaired)
            repair_note = f"repair attempt saved to {repaired_path}"
            dbg(f"{step}: attempting repaired JSON payload from {repaired_path}")
            return utils.parse_llm_json(repaired)
        except Exception as repair_exc:  # noqa: BLE001
            last_exc = repair_exc

        if cache_validator is not None:
            cached = load_json_if_valid(output_path)
            if cached is not None and cache_validator(cached):
                dbg(f"{step}: repaired parse failed; reusing cached JSON at {output_path}")
                return cached

        raise SynthesisStepError(
            step,
            (
                f"{failure_message}: {last_exc}. "
                f"Malformed model output saved to {raw_path}; "
                f"{repair_note}."
            ),
            output_path=output_path,
        ) from last_exc


def normalize_qa_payload(qa: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(qa)
    faithful = bool(normalized.get("faithful"))
    issues = normalized.get("issues")
    if not isinstance(issues, list):
        issues = []
        normalized["issues"] = issues

    score_raw = normalized.get("score")
    try:
        score = int(score_raw)
    except (TypeError, ValueError):
        score = 100 if faithful and not issues else 0

    # Guard against internally inconsistent model output such as:
    # faithful=true, issues=[], glowing summary, but score=0.
    if faithful and not issues and score == 0:
        score = 100
        normalized.setdefault("_normalization_note", "Adjusted inconsistent QA score from 0 to 100.")

    normalized["score"] = score
    return normalized


def qa_blocking_issues(qa: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = qa.get("issues")
    if not isinstance(issues, list):
        return []
    blocking: List[Dict[str, Any]] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        issue_type = str(issue.get("type") or "").strip().lower()
        severity = str(issue.get("severity") or "").strip().lower()
        if issue_type in QA_BLOCKING_ISSUE_TYPES or severity in {"fatal", "blocking", "high"}:
            blocking.append(issue)
    return blocking


def qa_passes_for_report_write(qa: Dict[str, Any], *, threshold: int) -> bool:
    if not qa.get("faithful"):
        return False
    try:
        score = int(qa.get("score", 0))
    except (TypeError, ValueError):
        return False
    if score < threshold:
        return False
    return not qa_blocking_issues(qa)


def resolve_project_dir(project_arg: str) -> Path:
    candidate = Path(project_arg)
    if candidate.exists():
        return candidate.resolve()
    fallback = PROJECTS_DIR / project_arg
    if fallback.exists():
        return fallback.resolve()
    raise FileNotFoundError(f"Project not found: {project_arg}")


def synthesis_paths(project_dir: Path) -> Dict[str, Path]:
    synth_dir = project_dir / SYNTHESIS_DIRNAME
    return {
        "dir": synth_dir,
        "context": synth_dir / CONTEXT_FILENAME,
        "ledger": synth_dir / LEDGER_FILENAME,
        "brief": synth_dir / BRIEF_FILENAME,
        "history_summary": synth_dir / HISTORY_SUMMARY_FILENAME,
        "qa": synth_dir / QA_FILENAME,
        "candidate_report": synth_dir / CANDIDATE_REPORT_FILENAME,
        "final_report": project_dir / FINAL_REPORT_FILENAME,
        "autoresearch_review_context": synth_dir / AUTORESEARCH_REVIEW_CONTEXT_FILENAME,
        "report_support_contract": synth_dir / REPORT_SUPPORT_CONTRACT_FILENAME,
    }


def renderer_tag(renderer_type: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", (renderer_type or "unknown")).strip("_")
    return safe or "unknown"


def renderer_scoped_paths(project_dir: Path, renderer_type: str) -> Dict[str, Path]:
    """
    Renderer-scoped paths prevent clobbering when generating multiple artifacts (memo + appendix, etc.).
    Keep ledger/history_summary shared; scope brief, QA, context, and candidate report.
    """
    base = synthesis_paths(project_dir)
    tag = renderer_tag(renderer_type)
    scoped = dict(base)
    scoped["context"] = base["dir"] / f"context.{tag}.json"
    scoped["brief"] = base["dir"] / f"brief.{tag}.json"
    scoped["qa"] = base["dir"] / f"qa.{tag}.json"
    scoped["candidate_report"] = base["dir"] / f"Report.{tag}.candidate.md"
    scoped["final_report"] = final_report_path(project_dir, renderer_type)
    return scoped


def final_report_path(project_dir: Path, renderer_type: str) -> Path:
    # Preserve backwards compatibility: founder memo remains the default Report.md.
    if renderer_type in {"founder_memo", "", None}:
        return project_dir / FINAL_REPORT_FILENAME
    # Avoid clobbering the founder memo when generating other artifact types.
    # Example: Report.decision_brief.md
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", renderer_type).strip("_")
    if "appendix" in safe.lower():
        return project_dir / f"Appendix.{safe}.md"
    return project_dir / f"Report.{safe}.md"


def multi_project_scope_id(project_names: List[str]) -> str:
    normalized = ",".join(sorted(project_names))
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]


def multi_project_scoped_paths(project_dir: Path, renderer_type: str, project_names: List[str]) -> Dict[str, Path]:
    base = synthesis_paths(project_dir)
    renderer_safe = renderer_tag(renderer_type)
    scope_id = multi_project_scope_id(project_names)
    suffix = f"multi_project.{renderer_safe}.{scope_id}"
    final_name = f"Report.{suffix}.md"
    if "appendix" in renderer_safe.lower():
        final_name = f"Appendix.{suffix}.md"
    return {
        "dir": base["dir"],
        "context": base["dir"] / f"context.{suffix}.json",
        "ledger": base["dir"] / f"ledger.{suffix}.json",
        "brief": base["dir"] / f"brief.{suffix}.json",
        "history_summary": base["dir"] / f"history_summary.{suffix}.json",
        "qa": base["dir"] / f"qa.{suffix}.json",
        "candidate_report": base["dir"] / f"Report.{suffix}.candidate.md",
        "final_report": project_dir / final_name,
        "aggregated_corpus": base["dir"] / f"aggregated_corpus.{suffix}.json",
    }


def latest_history_files(project_dir: Path, limit: int) -> List[Path]:
    history_dir = project_dir / "history"
    if not history_dir.exists():
        return []
    return sorted(history_dir.glob("*.md"), reverse=True)[:limit]


def latest_debate_logs(project_dir: Path, limit: int) -> List[Path]:
    return sorted(project_dir.glob("debate_log_iter_*.md"), reverse=True)[:limit]


def history_files(project_dir: Path) -> List[Path]:
    return sorted((project_dir / "history").glob("*.md")) if (project_dir / "history").exists() else []


def history_family_from_path(path: Path) -> Optional[str]:
    match = HISTORY_FAMILY_RE.match(path.stem)
    if not match:
        return None
    return match.group(1)


def best_iteration_family(project_dir: Path) -> Optional[str]:
    for artifact_name in ("thesis.md", "current_iteration.md"):
        path = project_dir / artifact_name
        if not path.exists():
            continue
        match = BEST_ITERATION_RE.search(read_text(path))
        if not match:
            continue
        stem = Path(match.group(1)).stem
        family_match = HISTORY_FAMILY_RE.match(stem)
        if family_match:
            return family_match.group(1)
    return None


def core_artifact_paths(project_dir: Path) -> List[str]:
    paths = []
    for name in ("thesis.md", "current_iteration.md", "evidence.txt"):
        path = project_dir / name
        if path.exists():
            paths.append(str(path))
    return paths


def history_meta(path: Path) -> Dict[str, Any]:
    meta_path = path.with_name(f"{path.stem}_meta.json")
    if not meta_path.exists():
        return {}
    try:
        return json.loads(read_text(meta_path))
    except Exception:  # noqa: BLE001
        return {}


def best_iteration_rubric(project_dir: Path) -> Optional[str]:
    for artifact_name in ("thesis.md", "current_iteration.md"):
        path = project_dir / artifact_name
        if not path.exists():
            continue
        match = BEST_ITERATION_RE.search(read_text(path))
        if not match:
            continue
        best_stem = Path(match.group(1)).stem
        meta_path = project_dir / "history" / f"{best_stem}_meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(read_text(meta_path))
                rubric = meta.get("rubric")
                if rubric:
                    return str(rubric)
            except Exception:  # noqa: BLE001
                pass
        family_match = HISTORY_FAMILY_RE.match(best_stem)
        if family_match:
            return family_match.group(1)
    return None


def project_arg_for_trace(project_dir: Path) -> str:
    try:
        return str(project_dir.resolve().relative_to(PROJECTS_DIR.resolve()))
    except ValueError:
        return str(project_dir)


def default_rubric_for_trace(project_dir: Path) -> Optional[str]:
    rubric = best_iteration_rubric(project_dir)
    if rubric:
        return rubric
    direct = RUBRICS_DIR / f"{project_dir.name}.json"
    if direct.exists():
        return project_dir.name
    return None


def default_project_intake_path(project_dir: Path) -> Optional[Path]:
    candidates = [
        project_dir / f"{project_dir.name}_intake.json",
        project_dir / f"{project_dir.name}_packet.json",
    ]
    candidates.extend(sorted(project_dir.glob("*_intake.json")))
    candidates.extend(sorted(project_dir.glob("*_packet.json")))
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


def compact_graph_actions_for_synthesis(actions: Any) -> List[Dict[str, Any]]:
    compact: List[Dict[str, Any]] = []
    if not isinstance(actions, list):
        return compact
    for action in actions:
        if not isinstance(action, dict):
            continue
        compact.append(
            {
                "action_type": action.get("action_type"),
                "work_mode": action.get("work_mode"),
                "recommended_actor": action.get("recommended_actor"),
                "targets": action.get("targets"),
                "reason": action.get("reason"),
            }
        )
    return compact


def compact_next_actions_for_synthesis(commands: Any) -> List[Dict[str, str]]:
    compact: List[Dict[str, str]] = []
    if not isinstance(commands, list):
        return compact
    for command in commands[:8]:
        item = str(command or "").strip()
        if not item:
            continue
        if "--preflight-only" in item:
            label = "Run the model-free launch preflight."
        elif " autoresearch run " in f" {item} ":
            label = "Run the bounded in-loop validation."
        elif " autoresearch projection " in f" {item} ":
            label = "Inspect the projection over prior loop results."
        elif " autoresearch health " in f" {item} ":
            label = "Inspect autoresearch health."
        else:
            label = "Inspect or repair the next trace surface."
        compact.append({"label": label, "command": item})
    return compact


def compact_autoresearch_trace_for_synthesis(report: Dict[str, Any]) -> Dict[str, Any]:
    kernel_entry = report.get("kernel_entry") or {}
    recent_loop = report.get("recent_loop") or {}
    surfaces = report.get("surfaces") or {}
    evidence_replay = surfaces.get("evidence_replay")
    evidence_replay_required = (
        bool(evidence_replay.get("required")) if isinstance(evidence_replay, dict) else False
    )
    evidence_replay_ok = (
        bool(evidence_replay.get("ok")) if evidence_replay_required else True
    )
    evidence_readiness_status = "fresh"
    for surface_name in (
        "source_index_freshness",
        "evidence_compile_freshness",
        "evidence_output_binding",
    ):
        surface = surfaces.get(surface_name)
        if isinstance(surface, dict) and str(surface.get("status") or "") not in {
            "",
            "fresh",
        }:
            evidence_readiness_status = "blocked"
    if evidence_replay_required and not evidence_replay_ok:
        evidence_readiness_status = "blocked"
    return {
        "schema": "ztare-synthesis-autoresearch-review-context-v1",
        "project": report.get("project"),
        "readiness": report.get("readiness_canonical") or report.get("readiness"),
        "status": report.get("status"),
        "missing": report.get("missing", []),
        "blocking_missing": report.get("blocking_missing", []),
        "review_artifacts": report.get("review_artifacts", []),
        "kernel_entry": {
            "status": kernel_entry.get("status"),
            "can_enter_kernel": kernel_entry.get("can_enter_kernel"),
            "blockers": kernel_entry.get("blockers", []),
        },
        "recent_loop": {
            "available": recent_loop.get("available"),
            "latest_iteration": recent_loop.get("latest_iteration"),
            "latest_iteration_score": recent_loop.get("latest_score"),
            "run_final_score": recent_loop.get("latest_run_final_score"),
            "latest_run_exit_reason": recent_loop.get("latest_run_exit_reason"),
            "latest_information_yield_rationale": recent_loop.get("latest_information_yield_rationale"),
            "latest_failed_gate_ids": recent_loop.get("latest_failed_gate_ids", []),
            "latest_provider_failure_observed": recent_loop.get("latest_provider_failure_observed"),
            "provider_failure_observed": recent_loop.get("provider_failure_observed"),
        },
        "surfaces": {
            "raw_file_count": surfaces.get("raw_file_count"),
            "evidence_exists": surfaces.get("evidence_exists"),
            "evidence_readiness": {
                "status": evidence_readiness_status,
                "source_index_status": _surface_status(surfaces.get("source_index_freshness")),
                "compile_provenance_status": _surface_status(
                    surfaces.get("evidence_compile_freshness")
                ),
                "output_binding_status": _surface_status(
                    surfaces.get("evidence_output_binding")
                ),
                "replay_required": evidence_replay_required,
                "replay_status": _surface_status(evidence_replay),
                "replay_ok": evidence_replay_ok,
            },
            "evidence_compile_freshness": surfaces.get("evidence_compile_freshness"),
            "evidence_output_binding": surfaces.get("evidence_output_binding"),
            "evidence_replay": surfaces.get("evidence_replay"),
            "claim_support": surfaces.get("claim_support"),
            "workspace_source_count": surfaces.get("workspace_source_count"),
            "source_index_count": surfaces.get("source_index_count"),
            "source_index_freshness": surfaces.get("source_index_freshness"),
            "source_preflight_ok": surfaces.get("source_preflight_ok"),
            "source_preflight_blocking": surfaces.get("source_preflight_blocking", []),
            "launch_preflight_ok": surfaces.get("launch_preflight_ok"),
            "launch_preflight_errors": surfaces.get("launch_preflight_errors", []),
            "eval_history_exists": surfaces.get("eval_history_exists"),
            "eval_history_rows": surfaces.get("eval_history_rows"),
            "confirmed_constraint_count": surfaces.get("confirmed_constraint_count"),
            "provisional_constraint_count": surfaces.get("provisional_constraint_count"),
        },
        "projection": report.get("projection", {}),
        "graph_rd_actions": compact_graph_actions_for_synthesis(report.get("graph_rd_actions", [])),
        "health_evidence_gaps": report.get("health_evidence_gaps", []),
        "recovery_actions": report.get("recovery_actions", []),
        "next_actions": compact_next_actions_for_synthesis(report.get("next_commands", [])),
    }


def maybe_write_autoresearch_review_context(project_dir: Path) -> Optional[Path]:
    workspace = project_dir / "workspace"
    has_autoresearch_surface = any(
        path.exists()
        for path in (
            workspace / "eval_history.jsonl",
            workspace / "iteration_telemetry.jsonl",
            workspace / "latest_evidence_gaps.json",
            project_dir / "latest_eval_results.json",
        )
    )
    packet_path = default_project_intake_path(project_dir)
    rubric = default_rubric_for_trace(project_dir)
    if not has_autoresearch_surface and packet_path is None:
        return None
    try:
        from ztare.reports.autoresearch_trace import build_autoresearch_trace

        report = build_autoresearch_trace(
            project=project_arg_for_trace(project_dir),
            rubric=rubric,
            packet=str(packet_path) if packet_path else None,
            full_health=False,
        )
        out = synthesis_paths(project_dir)["autoresearch_review_context"]
        write_json(out, compact_autoresearch_trace_for_synthesis(report))
        return out
    except Exception as exc:  # noqa: BLE001
        dbg(f"Autoresearch review context unavailable: {type(exc).__name__}: {exc}")
        return None


def startup_history_files(project_dir: Path, limit: int) -> List[Path]:
    all_history = latest_history_files(project_dir, limit=50)
    if not all_history:
        return []

    active_family = best_iteration_rubric(project_dir) or best_iteration_family(project_dir)
    if active_family:
        matching = [
            path
            for path in all_history
            if history_meta(path).get("rubric") == active_family or history_family_from_path(path) == active_family
        ]
        if matching:
            return matching[:limit]

    # Fallback: use only the newest history slice rather than the full mixed archive.
    return all_history[:limit]


def all_relevant_history_paths(project_dir: Path, project_type: str) -> List[Path]:
    if project_type in {"startup", "investment_thesis"}:
        return history_files(project_dir)
    history = history_files(project_dir)
    debates = sorted(project_dir.glob("debate_log_iter_*.md"))
    if history or debates:
        return history + debates
    return []


def focused_history_paths(project_dir: Path, project_type: str, limit: int = 5) -> List[Path]:
    if project_type == "startup":
        return startup_history_files(project_dir, limit=limit)
    if project_type in {"engine_architecture", "research_hypothesis", "policy_scenario"}:
        return latest_debate_logs(project_dir, limit=limit)
    if project_type == "investment_thesis":
        return latest_history_files(project_dir, limit=limit)
    return latest_history_files(project_dir, limit=limit)


def default_history_mode(renderer_type: str) -> str:
    # Audience-facing artifacts should default to focused history to avoid mixed-rubric contamination.
    if renderer_type in {"founder_memo", "decision_brief", "quantitative_appendix"}:
        return "focused"
    return "full"


def selected_history_paths(
    project_dir: Path,
    project_type: str,
    history_mode: str,
    renderer_type: str,
) -> List[Path]:
    if history_mode == "full":
        return all_relevant_history_paths(project_dir, project_type)
    # Audience-facing founder memos are especially sensitive to rubric cross-talk. In focused mode,
    # rely on the canonical thesis/current_iteration plus patterns from history_summary.json, not raw history.
    if renderer_type in {"founder_memo", "decision_brief"}:
        return []
    return focused_history_paths(project_dir, project_type, limit=5)


def select_artifact_paths(
    project_dir: Path,
    project_type: str,
    history_mode: str,
    renderer_type: str,
) -> List[str]:
    base = core_artifact_paths(project_dir)
    review_context = maybe_write_autoresearch_review_context(project_dir)
    if review_context is not None:
        base.append(str(review_context))
    for review_artifact in (
        project_dir / "public" / "CLAIM_SUMMARY.md",
        project_dir / "README.md",
    ):
        if review_artifact.exists():
            base.append(str(review_artifact))
    selected_history = [str(path) for path in selected_history_paths(project_dir, project_type, history_mode, renderer_type)]
    paths = list(base)
    paths.extend(selected_history)
    return paths


def heuristic_project_type(project_dir: Path, preview_text: str) -> str:
    lowered = f"{project_dir.name} {preview_text}".lower()
    if any(token in lowered for token in ["startup", "member", "cohort", "referral", "cac", "ltv", "pre-seed", "pmf"]):
        return "startup"
    if any(token in lowered for token in ["epistemic engine", "axiom", "predictor", "architecture", "calibration", "llm guidance"]):
        return "engine_architecture"
    if any(token in lowered for token in ["investment", "diligence", "equity", "valuation"]):
        return "investment_thesis"
    if any(token in lowered for token in ["policy", "regulation", "scenario", "geopolitics", "government"]):
        return "policy_scenario"
    if any(token in lowered for token in ["hypothesis", "paper", "research", "scientific"]):
        return "research_hypothesis"
    return "general_analysis"


class LLMClient:
    def __init__(self, model_family: str):
        if model_family not in MODEL_MAP:
            raise ValueError(f"Unsupported model family: {model_family}")
        self.model_family = model_family
        self.model_id = MODEL_MAP[model_family]
        self.runtime = LLMRuntime()

    def call(self, prompt: str, retries: int = 3) -> str:
        try:
            dbg(f"LLM call: family={self.model_family} model={self.model_id} retries={retries}")
            # Route through the ONE transport door (dispatch_call_text): API by default, subscription
            # CLI worker when ZTARE_AGENT_DISPATCH[_SYNTHESIS]=agent — the same door autoresearch uses.
            # No bespoke synth transport flag.
            response = dispatch_call_text(
                "synthesis",
                prompt,
                llm_response_call=lambda p: self.runtime.call_text(
                    p,
                    model_id=self.model_id,
                    retries=retries,
                    timeout_seconds=300,
                    request_label="synthesis request",
                    progress_printer=dbg,
                    transient_wait_seconds=5,
                    timeout_wait_seconds=2,
                ),
                repo=REPO_ROOT,
                agent_id="synthesis_report",
            )
            return response.text
        except LLMRuntimeError as exc:
            raise RuntimeError(f"LLM call failed after {retries} attempts: {exc}") from exc


class SynthesisStepError(RuntimeError):
    def __init__(
        self,
        step: str,
        message: str,
        *,
        output_path: Optional[Path] = None,
        can_retry: bool = True,
    ) -> None:
        super().__init__(message)
        self.step = step
        self.output_path = output_path
        self.can_retry = can_retry


def build_context_preview(project_dir: Path) -> str:
    snippets = []
    for name in ("evidence.txt", "thesis.md", "current_iteration.md"):
        path = project_dir / name
        if path.exists():
            snippets.append(f"## {name}\n{read_text(path)[:3000]}")
    if not snippets:
        snippets.append("No primary artifacts found.")
    return "\n\n".join(snippets)


def sniff_context(
    project_dir: Path,
    renderer_override: Optional[str] = None,
    history_mode_override: Optional[str] = None,
) -> Dict[str, Any]:
    if ACTIVE_LLM is None:
        raise RuntimeError("ACTIVE_LLM is not configured.")
    # Per-project renderer pin: read synthesis_renderer from rubric JSON if present.
    if not renderer_override:
        rubric_name = best_iteration_rubric(project_dir)
        if rubric_name:
            rubric_path = RUBRICS_DIR / f"{rubric_name}.json"
            if rubric_path.exists():
                try:
                    rubric_data = json.loads(rubric_path.read_text(encoding="utf-8"))
                    pinned = rubric_data.get("synthesis_renderer", "")
                    if pinned:
                        renderer_override = pinned
                        dbg(f"Renderer pinned by rubric '{rubric_name}': '{pinned}'")
                except Exception:
                    pass
    project_name = project_dir.name
    preview = build_context_preview(project_dir)
    available_renderers = sorted(path.stem for path in RENDERERS_DIR.glob("*.md"))

    heuristic_type = heuristic_project_type(project_dir, preview)
    defaults = PROJECT_TYPE_DEFAULTS[heuristic_type]

    prompt = "\n\n".join(
        [
            load_prompt(PROMPTS_DIR / "sniff_context.md"),
            f"Project name: {project_name}",
            f"Available renderer types: {', '.join(available_renderers)}",
            f"Heuristic project type: {heuristic_type}",
            "Project preview:",
            preview,
        ]
    )

    try:
        sniffed = utils.parse_llm_json(ACTIVE_LLM.call(prompt))
    except Exception:  # noqa: BLE001
        sniffed = {
            "project_type": heuristic_type,
            "audience": defaults["audience"],
            "tone": defaults["tone"],
            "renderer_type": defaults["renderer_type"],
            "reason": "Fallback heuristic classification due to context-sniffer failure.",
        }
        dbg("Context sniffing failed; using fallback heuristic classification.")

    project_type = sniffed.get("project_type", heuristic_type)
    if project_type not in PROJECT_TYPE_DEFAULTS:
        project_type = heuristic_type

    default_renderer_type = PROJECT_TYPE_DEFAULTS[project_type]["renderer_type"]

    merged = {
        "project_name": project_name,
        "project_dir": str(project_dir),
        "project_type": project_type,
        "audience": sniffed.get("audience") or PROJECT_TYPE_DEFAULTS[project_type]["audience"],
        "tone": sniffed.get("tone") or PROJECT_TYPE_DEFAULTS[project_type]["tone"],
        "renderer_type": default_renderer_type,
        "reason": sniffed.get("reason", ""),
    }

    if renderer_override:
        merged["renderer_type"] = renderer_override
        override_defaults = RENDERER_OVERRIDES.get(renderer_override, {})
        if override_defaults.get("audience"):
            merged["audience"] = override_defaults["audience"]
        if override_defaults.get("tone"):
            merged["tone"] = override_defaults["tone"]
    else:
        sniffed_renderer_type = sniffed.get("renderer_type")
        if sniffed_renderer_type and sniffed_renderer_type != default_renderer_type:
            sniffed_path = RENDERERS_DIR / f"{sniffed_renderer_type}.md"
            if sniffed_path.exists():
                merged["renderer_type"] = sniffed_renderer_type
                dbg(f"Using LLM-sniffed renderer '{sniffed_renderer_type}' (exists on disk).")
            else:
                note = (
                    f" Renderer suggestion '{sniffed_renderer_type}' not on disk; "
                    f"using default '{default_renderer_type}'."
                )
                merged["reason"] = f"{merged['reason']}{note}".strip()

    merged["history_mode"] = history_mode_override or default_history_mode(merged["renderer_type"])
    merged["history_source_paths"] = [str(path) for path in all_relevant_history_paths(project_dir, project_type)]
    merged["artifact_paths"] = select_artifact_paths(project_dir, project_type, merged["history_mode"], merged["renderer_type"])
    merged["artifact_input_binding"] = build_artifact_input_binding(merged["artifact_paths"])
    merged["history_summary_prompt_hash"] = prompt_hash(PROMPTS_DIR / "summarize_history.md")
    merged["ledger_prompt_hash"] = prompt_hash(PROMPTS_DIR / "extract_ledger.md")

    out_paths = renderer_scoped_paths(project_dir, merged["renderer_type"])
    merged["output_paths"] = {key: str(path) for key, path in out_paths.items()}
    merged["history_summary_path"] = str(synthesis_paths(project_dir)["history_summary"])

    prompt_path = RENDERERS_DIR / f"{merged['renderer_type']}.md"
    if not prompt_path.exists():
        dbg(f"Renderer '{merged['renderer_type']}' missing — auto-generating template.")
        suggest_renderer_template(project_dir, merged, ACTIVE_LLM)
        if not prompt_path.exists():
            raise RuntimeError(
                f"Renderer template missing for '{merged['renderer_type']}' and auto-generation failed."
            )
        dbg(f"Auto-generated renderer written to {prompt_path}; proceeding without manual review.")

    # Write both:
    # - renderer-scoped context (stable for packs)
    # - default context.json (points at the latest run, for convenience)
    write_json(Path(merged["output_paths"]["context"]), merged)
    write_json(synthesis_paths(project_dir)["context"], merged)
    dbg(
        "Context:\n"
        f"- project_dir={merged['project_dir']}\n"
        f"- project_type={merged['project_type']}\n"
        f"- renderer_type={merged['renderer_type']}\n"
        f"- history_mode={merged['history_mode']}\n"
        f"- artifact_paths ({len(merged['artifact_paths'])}):\n{fmt_paths(list(merged['artifact_paths']))}"
    )
    return merged


def load_artifact_bundle(artifact_paths: List[str]) -> str:
    sections = []
    for artifact in artifact_paths:
        path = Path(artifact)
        if not path.exists():
            continue
        sections.append(f"# Artifact: {path.name}\n\n{read_text(path)}")
    return "\n\n".join(sections)


def artifact_file_binding(path: Path) -> Dict[str, Any]:
    """Return a portable content binding for one synthesis input artifact."""
    row: Dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
    }
    if not path.exists() or not path.is_file():
        row["sha256"] = None
        row["size_bytes"] = None
        return row
    data = path.read_bytes()
    row["sha256"] = hashlib.sha256(data).hexdigest()
    row["size_bytes"] = len(data)
    return row


def build_artifact_input_binding(artifact_paths: List[str]) -> Dict[str, Any]:
    artifacts = [artifact_file_binding(Path(str(path))) for path in artifact_paths]
    payload = {
        "schema": "ztare-synthesis-artifact-input-binding-v1",
        "artifacts": artifacts,
    }
    payload["digest"] = hashlib.sha256(
        json.dumps(payload["artifacts"], sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def artifact_input_binding_for_context(context: Dict[str, Any]) -> Dict[str, Any]:
    return build_artifact_input_binding([str(path) for path in context.get("artifact_paths", [])])


def summarize_history(project_dir: Path, context: Dict[str, Any]) -> Dict[str, Any]:
    if ACTIVE_LLM is None:
        raise RuntimeError("ACTIVE_LLM is not configured.")

    history_source_paths = context.get("history_source_paths", [])
    summary_path = synthesis_paths(project_dir)["history_summary"]
    summary_prompt_hash = context.get("history_summary_prompt_hash") or prompt_hash(PROMPTS_DIR / "summarize_history.md")
    dbg(f"Summarize history: sources={len(history_source_paths)} -> {summary_path}")

    # Skip re-summarization only when the cache matches the current history mode, sources, and prompt.
    cached = load_json_if_valid(summary_path)
    cached_meta = cached.get("_meta") if isinstance(cached, dict) else None
    if (
        cached
        and isinstance(cached_meta, dict)
        and cached.get("recurring_failures_tagged") is not None
        and cached_meta.get("history_mode") == context["history_mode"]
        and cached_meta.get("source_paths") == history_source_paths
        and cached_meta.get("prompt_hash") == summary_prompt_hash
    ):
        dbg(f"Summarize history: using cached summary with {len(cached['recurring_failures_tagged'])} tagged failures")
        return cached

    if not history_source_paths:
        summary = {
            "_meta": {
                "project_name": context["project_name"],
                "project_type": context["project_type"],
                "history_mode": context["history_mode"],
                "source_paths": [],
                "prompt_hash": summary_prompt_hash,
            },
            "summary_scope": "No historical artifacts available.",
            "major_pivots": [],
            "recurring_survivors": [],
            "recurring_failures": [],
            "retired_assumptions": [],
            "cross_run_patterns": [],
            "historical_noise_to_ignore": [],
        }
        write_json(summary_path, summary)
        return summary

    artifact_bundle = load_artifact_bundle(history_source_paths)
    dbg(f"Summarize history: bundle_chars={len(artifact_bundle)}")
    prompt_body = load_prompt(PROMPTS_DIR / "summarize_history.md")
    prompt = "\n\n".join(
        [
            prompt_body,
            f"Project name: {context['project_name']}",
            f"Project type: {context['project_type']}",
            f"History mode: {context['history_mode']}",
            "Historical artifacts:",
            artifact_bundle,
        ]
    )
    try:
        raw_response = ACTIVE_LLM.call(prompt)
        summary = parse_json_step_response(
            raw_response,
            step="summarize_history",
            output_path=summary_path,
            failure_message="Could not summarize history",
            cache_validator=lambda _cached: True,
        )
    except SynthesisStepError as exc:
        if summary_path.exists():
            try:
                cached = json.loads(read_text(summary_path))
                dbg(f"Summarize history failed; reusing cached history summary at {summary_path}")
                return cached
            except Exception:  # noqa: BLE001
                pass
        raise exc
    summary["_meta"] = {
        "project_name": context["project_name"],
        "project_type": context["project_type"],
        "history_mode": context["history_mode"],
        "source_paths": history_source_paths,
        "prompt_hash": summary_prompt_hash,
    }
    write_json(summary_path, summary)
    return summary


def refresh_context_artifacts(project_dir: Path, context: Dict[str, Any]) -> Dict[str, Any]:
    updated = dict(context)
    updated["artifact_paths"] = select_artifact_paths(
        project_dir,
        updated["project_type"],
        updated["history_mode"],
        updated["renderer_type"],
    )
    updated["artifact_input_binding"] = build_artifact_input_binding(updated["artifact_paths"])
    # Keep both renderer-scoped and latest-run context pointers updated.
    scoped_context = Path(updated.get("output_paths", {}).get("context") or synthesis_paths(project_dir)["context"])
    write_json(scoped_context, updated)
    write_json(synthesis_paths(project_dir)["context"], updated)
    return updated


def cached_ledger_matches_context(cached: Dict[str, Any], context: Dict[str, Any]) -> bool:
    meta = cached.get("_meta")
    if not isinstance(meta, dict):
        return False
    cached_paths = meta.get("artifact_paths")
    if not isinstance(cached_paths, list):
        return False
    if meta.get("prompt_hash") != context.get("ledger_prompt_hash"):
        return False
    if [str(path) for path in cached_paths] != [str(path) for path in context.get("artifact_paths", [])]:
        return False
    current_binding = artifact_input_binding_for_context(context)
    return meta.get("artifact_input_digest") == current_binding.get("digest")


def cached_multi_project_ledger_matches_context(cached: Dict[str, Any], context: Dict[str, Any]) -> bool:
    meta = cached.get("_meta")
    if not isinstance(meta, dict):
        return False
    if meta.get("project_names") != context.get("multi_project_names", []):
        return False
    if meta.get("renderer_type") != context.get("renderer_type"):
        return False
    if meta.get("prompt_hash") != context.get("ledger_prompt_hash"):
        return False
    expected_digest = aggregated_corpus_digest(context.get("aggregated_corpus") or {})
    return meta.get("aggregated_corpus_digest") == expected_digest


def extract_ledger(project_dir: Path, context: Dict[str, Any]) -> Dict[str, Any]:
    if ACTIVE_LLM is None:
        raise RuntimeError("ACTIVE_LLM is not configured.")
    artifact_bundle = load_artifact_bundle(context["artifact_paths"])
    dbg(f"Extract ledger: artifact_paths={len(context['artifact_paths'])} bundle_chars={len(artifact_bundle)}")
    # Use project-type-specific ledger prompt if available, else generic.
    project_type = context.get("project_type", "")
    typed_prompt_path = PROMPTS_DIR / f"extract_ledger_{project_type}.md"
    ledger_prompt_path = typed_prompt_path if typed_prompt_path.exists() else PROMPTS_DIR / "extract_ledger.md"
    prompt_body = load_prompt(ledger_prompt_path)
    dbg(f"Extract ledger: using prompt {ledger_prompt_path.name}")
    prompt_parts = [
        prompt_body,
        f"Project name: {context['project_name']}",
        f"Project type: {context['project_type']}",
        "Artifacts:",
        artifact_bundle,
    ]
    # Inject charter so ledger extraction knows required content structure.
    charter_path = project_dir / "project_charter.md"
    if charter_path.exists():
        charter_text = charter_path.read_text(encoding="utf-8").strip()
        if charter_text:
            prompt_parts.append(
                "Project charter (extract all required content elements — credit column, debit column, "
                "distributional breakdown, irreversibility items, policy mechanism):\n" + charter_text
            )
    prompt = "\n\n".join(prompt_parts)
    ledger_output_path = synthesis_paths(project_dir)["ledger"]
    raw_response = ACTIVE_LLM.call(prompt)
    ledger = parse_json_step_response(
        raw_response,
        step="extract_ledger",
        output_path=ledger_output_path,
        failure_message="Could not extract insight ledger",
        cache_validator=lambda cached: cached_ledger_matches_context(cached, context),
    )
    dbg("Extract ledger: parsed ledger.json")
    artifact_binding = artifact_input_binding_for_context(context)
    ledger["_meta"] = {
        "project_name": context["project_name"],
        "project_type": context["project_type"],
        "artifact_paths": context["artifact_paths"],
        "artifact_input_binding": artifact_binding,
        "artifact_input_digest": artifact_binding.get("digest"),
        "prompt_hash": context.get("ledger_prompt_hash"),
    }
    # Ledger is canonical and shared across renderers for the same project snapshot.
    write_json(ledger_output_path, ledger)
    return ledger


def extract_multi_project_ledger(project_dir: Path, context: Dict[str, Any]) -> Dict[str, Any]:
    if ACTIVE_LLM is None:
        raise RuntimeError("ACTIVE_LLM is not configured.")
    aggregated_corpus = context.get("aggregated_corpus") or {}
    prompt_body = load_prompt(PROMPTS_DIR / "extract_ledger_multi_project.md")
    prompt = "\n\n".join(
        [
            prompt_body,
            f"Anchor project: {context['project_name']}",
            f"Project type: {context['project_type']}",
            f"Renderer type: {context['renderer_type']}",
            "Aggregated multi-project corpus JSON:",
            json.dumps(aggregated_corpus, indent=2, sort_keys=True),
        ]
    )
    ledger_output_path = Path(context["output_paths"]["ledger"])
    raw_response = ACTIVE_LLM.call(prompt)
    ledger = parse_json_step_response(
        raw_response,
        step="extract_multi_project_ledger",
        output_path=ledger_output_path,
        failure_message="Could not extract multi-project insight ledger",
        cache_validator=lambda cached: cached_multi_project_ledger_matches_context(cached, context),
    )
    ledger["_meta"] = {
        "multi_project": True,
        "project_name": context["project_name"],
        "project_type": context["project_type"],
        "project_names": context["multi_project_names"],
        "renderer_type": context["renderer_type"],
        "aggregated_corpus_digest": aggregated_corpus_digest(aggregated_corpus),
        "prompt_hash": context.get("ledger_prompt_hash"),
    }
    write_json(ledger_output_path, ledger)
    return ledger


def derive_brief(project_dir: Path, ledger: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    if ACTIVE_LLM is None:
        raise RuntimeError("ACTIVE_LLM is not configured.")

    renderer_type = context["renderer_type"]
    prompt_path = PROMPTS_DIR / f"derive_brief_{renderer_type}.md"
    dbg(f"Derive brief: renderer_type={renderer_type} prompt={prompt_path}")
    history_summary: Optional[Dict[str, Any]] = None
    history_summary_path = Path(context.get("history_summary_path", ""))
    if history_summary_path and history_summary_path.exists():
        try:
            history_summary = json.loads(read_text(history_summary_path))
        except Exception:  # noqa: BLE001
            history_summary = None
    if not prompt_path.exists():
        brief = {
            "_meta": {
                "renderer_type": renderer_type,
                "derived_from": "ledger_passthrough",
            },
            "opening_judgment": ledger.get("hardest_conclusion", {}).get("claim")
            or ledger.get("core_question", {}).get("question")
            or "",
            "sequence": [],
            "core_tradeoff": "",
            "prerequisite_action": "",
            "main_experiment": ledger.get("next_decisive_test", {}).get("test", ""),
            "do_not_do_yet": [item.get("area", "") for item in ledger.get("premature_focus_areas", []) if item.get("area")],
            "decision_rule_plain": ledger.get("decision_rule", {}).get("if_negative")
            or ledger.get("decision_rule", {}).get("if_positive")
            or "",
            "tone_guardrails": {
                "avoid_alarmism": True,
                "avoid_jargon": True,
                "keep_business_language": True,
            },
        }
        write_json(Path(context["output_paths"]["brief"]), brief)
        return brief

    memo_brief_payload: Optional[Dict[str, Any]] = None
    memo_brief_path = context.get("memo_brief_path")
    if renderer_type == "quantitative_appendix" and memo_brief_path:
        try:
            memo_brief_payload = json.loads(read_text(Path(memo_brief_path)))
        except Exception:  # noqa: BLE001
            memo_brief_payload = None

    prompt = "\n\n".join(
        [
            load_prompt(prompt_path),
            f"Audience: {context['audience']}",
            f"Tone: {context['tone']}",
            f"Project type: {context['project_type']}",
            "Founder memo planning brief JSON (scope constraints; not new evidence):",
            json.dumps(memo_brief_payload or {}, indent=2, sort_keys=True),
            "History summary JSON (patterns only; not new evidence):",
            json.dumps(history_summary or {}, indent=2, sort_keys=True),
            "Insight ledger JSON:",
            json.dumps(ledger, indent=2, sort_keys=True),
        ]
    )
    brief_output_path = Path(context["output_paths"]["brief"])
    raw_response = ACTIVE_LLM.call(prompt)
    brief = parse_json_step_response(
        raw_response,
        step="derive_brief",
        output_path=brief_output_path,
        failure_message=f"Could not derive planning brief for renderer '{renderer_type}'",
    )
    brief["_meta"] = {
        "renderer_type": renderer_type,
        "audience": context["audience"],
        "tone": context["tone"],
    }
    write_json(brief_output_path, brief)
    return brief


def _normalize_domain_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = value.strip().lower()
    if not cleaned:
        return ""
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")
    return cleaned[:80]


def _domain_from_project_metadata(project_dir: Path) -> str:
    metadata_path = project_dir / "project_metadata.json"
    if not metadata_path.exists():
        return ""
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return ""
    if not isinstance(metadata, dict):
        return ""
    for key in ("project_domain", "domain", "research_domain", "application_domain"):
        label = _normalize_domain_label(metadata.get(key))
        if label:
            return label
    return ""


def _domain_from_rubric(project_dir: Path) -> str:
    rubric_names = [best_iteration_rubric(project_dir), project_dir.name]
    for rubric_name in rubric_names:
        if not rubric_name:
            continue
        rubric_path = RUBRICS_DIR / f"{rubric_name}.json"
        if not rubric_path.exists():
            continue
        try:
            rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(rubric, dict):
            continue
        for key in ("project_domain", "domain", "research_domain", "application_domain"):
            label = _normalize_domain_label(rubric.get(key))
            if label:
                return label
    return ""


def _domain_from_project_charter(project_dir: Path) -> str:
    charter_path = project_dir / "project_charter.md"
    if not charter_path.exists():
        return ""
    try:
        text = charter_path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return ""
    for pattern in (
        r"(?im)^\s*\*\*Domain:\*\*\s*(.+?)\s*$",
        r"(?im)^\s*Domain:\s*(.+?)\s*$",
    ):
        match = re.search(pattern, text)
        if match:
            label = _normalize_domain_label(match.group(1))
            if label:
                return label
    return ""


def derive_project_domain(project_name: str, project_dir: Optional[Path] = None) -> str:
    """Return the synthesis domain bucket for cross-project promotion checks.

    Explicit project metadata wins. Slug heuristics are only a fallback, so a
    project name used as an example cannot silently define the domain taxonomy.
    """
    if project_dir is not None:
        for resolver in (
            _domain_from_project_metadata,
            _domain_from_rubric,
            _domain_from_project_charter,
        ):
            label = resolver(project_dir)
            if label:
                return label

    # Fallback: collapse a project name to a coarse bucket so the provenance
    # counter can compute "distinct domains" for Confirmed promotion.
    # Anything not matched falls back to the first underscore-separated token.
    name = project_name.lower()
    if name.startswith("eu_") or "european" in name or "_eu_" in name:
        return "eu_political_economy"
    if name.startswith("central_station") or "startup" in name or "founder" in name:
        return "startup_diligence"
    if "tsmc" in name or "semiconductor" in name:
        return "geopolitical_supply_chain"
    if "ai_inference" in name or "inference_collapse" in name:
        return "ai_market_structure"
    if "climate" in name or "energy" in name:
        return "climate_policy"
    return name.split("_", 1)[0] or "misc"


def aggregated_corpus_digest(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


def dedupe_strings(items: List[str], limit: int = 12) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def build_multi_project_history_summary(project_payloads: List[Dict[str, Any]]) -> Dict[str, Any]:
    cross_project_patterns: List[str] = []
    recurring_survivors: List[str] = []
    recurring_failures: List[str] = []
    major_pivots: List[str] = []
    projects: List[Dict[str, Any]] = []
    project_names: List[str] = []

    for payload in project_payloads:
        project_name = payload.get("project", "")
        project_names.append(project_name)
        history_summary = payload.get("history_summary") or {}
        projects.append(
            {
                "project": project_name,
                "domain": payload.get("domain", ""),
                "summary_scope": history_summary.get("summary_scope", ""),
                "cross_run_patterns": history_summary.get("cross_run_patterns") or [],
                "recurring_survivors": history_summary.get("recurring_survivors") or [],
                "recurring_failures": history_summary.get("recurring_failures") or [],
                "major_pivots": history_summary.get("major_pivots") or [],
            }
        )
        cross_project_patterns.extend(history_summary.get("cross_run_patterns") or [])
        recurring_survivors.extend(history_summary.get("recurring_survivors") or [])
        recurring_failures.extend(history_summary.get("recurring_failures") or [])
        major_pivots.extend(history_summary.get("major_pivots") or [])

    return {
        "_meta": {
            "mode": "multi_project_history_summary",
            "project_count": len(project_payloads),
            "project_names": project_names,
        },
        "summary_scope": f"Combined synthesis across {', '.join(project_names)}.",
        "projects": projects,
        "cross_project_patterns": dedupe_strings(cross_project_patterns),
        "recurring_survivors": dedupe_strings(recurring_survivors),
        "recurring_failures": dedupe_strings(recurring_failures),
        "major_pivots": dedupe_strings(major_pivots),
    }


def aggregate_multi_project_corpus(
    project_dirs: List[Path],
    renderer_type: str,
    history_mode: Optional[str],
) -> Dict[str, Any]:
    projects_payload: List[Dict[str, Any]] = []
    for project_dir in project_dirs:
        project_name = project_dir.name
        domain = derive_project_domain(project_name, project_dir)
        project_context = sniff_context(
            project_dir,
            renderer_override=renderer_type,
            history_mode_override=history_mode,
        )
        history_summary = summarize_history(project_dir, project_context)
        project_context = refresh_context_artifacts(project_dir, project_context)
        ledger = extract_ledger(project_dir, project_context)
        projects_payload.append(
            {
                "project": project_name,
                "domain": domain,
                "project_type": project_context.get("project_type"),
                "audience": project_context.get("audience"),
                "tone": project_context.get("tone"),
                "artifact_paths": project_context.get("artifact_paths", []),
                "history_summary": history_summary,
                "ledger": ledger,
            }
        )

    project_types = sorted(
        {
            payload.get("project_type")
            for payload in projects_payload
            if isinstance(payload.get("project_type"), str) and payload.get("project_type")
        }
    )
    return {
        "_meta": {
            "mode": "multi_project_renderer",
            "renderer_type": renderer_type,
            "project_count": len(projects_payload),
            "project_types": project_types,
        },
        "projects": projects_payload,
    }


def aggregate_field_manual_corpus(project_dirs: List[Path]) -> Dict[str, Any]:
    """Build a multi-project aggregated corpus for the field_manual renderer.

    For each project, ensures a history_summary.json exists (running summarize_history
    if needed), unions the recurring_failures_tagged arrays, and computes a provenance
    table mapping each canonical family to the list of distinct projects (and domains)
    in which it was observed.
    """
    projects_payload: List[Dict[str, Any]] = []
    union: List[Dict[str, Any]] = []
    family_to_projects: Dict[str, set] = {}
    family_to_domains: Dict[str, set] = {}

    for project_dir in project_dirs:
        project_name = project_dir.name
        domain = derive_project_domain(project_name, project_dir)
        history_summary_path = synthesis_paths(project_dir)["history_summary"]

        if not history_summary_path.exists():
            dbg(f"Aggregation: history_summary missing for {project_name}; running summarize_history")
            tmp_context = sniff_context(project_dir, renderer_override="field_manual")
            summarize_history(project_dir, tmp_context)

        if not history_summary_path.exists():
            dbg(f"Aggregation: history_summary still missing for {project_name}; skipping")
            continue

        try:
            history_summary = json.loads(read_text(history_summary_path))
        except Exception:  # noqa: BLE001
            dbg(f"Aggregation: failed to parse history_summary for {project_name}; skipping")
            continue

        tagged = history_summary.get("recurring_failures_tagged") or []
        projects_payload.append(
            {
                "project": project_name,
                "domain": domain,
                "recurring_failures": history_summary.get("recurring_failures") or [],
                "recurring_failures_tagged": tagged,
                "cross_run_patterns": history_summary.get("cross_run_patterns") or [],
                "major_pivots": history_summary.get("major_pivots") or [],
                "recurring_survivors": history_summary.get("recurring_survivors") or [],
                "summary_scope": history_summary.get("summary_scope") or "",
            }
        )

        for entry in tagged:
            if not isinstance(entry, dict):
                continue
            family = (entry.get("canonical_family") or "").strip()
            if not family:
                continue
            enriched = dict(entry)
            enriched["project"] = project_name
            enriched["domain"] = domain
            union.append(enriched)
            if family != "unmapped":
                family_to_projects.setdefault(family, set()).add(project_name)
                family_to_domains.setdefault(family, set()).add(domain)

    provenance_table: Dict[str, Dict[str, Any]] = {}
    for family, project_set in family_to_projects.items():
        domains = family_to_domains.get(family, set())
        if len(project_set) >= 3 and len(domains) >= 2:
            tag = "Confirmed"
        elif len(project_set) >= 2:
            tag = "Probable"
        else:
            tag = "Tentative"
        provenance_table[family] = {
            "projects": sorted(project_set),
            "domains": sorted(domains),
            "project_count": len(project_set),
            "domain_count": len(domains),
            "provenance_tag": tag,
        }

    return {
        "_meta": {
            "mode": "multi_project_field_manual",
            "project_count": len(projects_payload),
        },
        "projects": projects_payload,
        "recurring_failures_tagged": union,
        "provenance_table": provenance_table,
    }


def load_history_summary_for_context(context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    history_summary_path = Path(context.get("history_summary_path", ""))
    if history_summary_path and history_summary_path.exists():
        try:
            return json.loads(read_text(history_summary_path))
        except Exception:  # noqa: BLE001
            return None
    return None


def load_autoresearch_review_context_for_context(context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Load the compact autoresearch trace context selected for this render."""
    candidates: List[Path] = []
    for artifact in context.get("artifact_paths", []):
        path = Path(str(artifact))
        if path.name == AUTORESEARCH_REVIEW_CONTEXT_FILENAME:
            candidates.append(path)
    project_dir_raw = context.get("project_dir")
    if project_dir_raw:
        candidates.append(synthesis_paths(Path(project_dir_raw))["autoresearch_review_context"])

    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except Exception:  # noqa: BLE001
            resolved = candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        payload = load_json_if_valid(candidate)
        if payload is not None:
            return payload
    return None


def _compact_list(value: Any, limit: int = 8) -> List[Any]:
    if not isinstance(value, list):
        return []
    return value[:limit]


def _claim_rows(rows: Any, *, limit: int = 5) -> List[Dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        claim = str(row.get("claim") or "").strip()
        if not claim:
            continue
        out.append(
            {
                "claim": claim,
                "confidence": row.get("confidence"),
                "evidence_summary": row.get("evidence_summary"),
            }
        )
        if len(out) >= limit:
            break
    return out


def _surface_status(surface: Any) -> Optional[str]:
    if not isinstance(surface, dict):
        return None
    status = str(surface.get("status") or "").strip()
    return status or None


def _compact_text(value: Any, *, limit: int = 360) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _compact_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _compact_claim_support_row(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    return {
        "claim_id": row.get("claim_id"),
        "claim": row.get("claim"),
        "field": row.get("field"),
        "support_status": row.get("support_status"),
        "source_context_status": row.get("source_context_status"),
        "source_ids": _compact_list(row.get("source_ids"), 6),
        "source_paths": _compact_list(row.get("source_paths"), 6),
        "missing_source_ids": _compact_list(row.get("missing_source_ids"), 6),
        "reason": row.get("reason"),
    }


def _claim_support_summary(claim_support: Dict[str, Any]) -> Dict[str, Any]:
    rows = claim_support.get("rows") if isinstance(claim_support.get("rows"), list) else []
    source_supported_statuses = {
        "direct_source_support",
        "synthesized_source_support",
        "synthesized_across_sources",
    }
    problem_rows: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        support_status = str(row.get("support_status") or "").strip()
        source_context_status = str(row.get("source_context_status") or "").strip()
        if (
            support_status not in source_supported_statuses
            or source_context_status in {"blocked", "stale", "unverified"}
            or row.get("missing_source_ids")
        ):
            compact = _compact_claim_support_row(row)
            if compact:
                problem_rows.append(compact)
    sample_rows = [
        compact
        for compact in (_compact_claim_support_row(row) for row in rows[:8])
        if compact
    ]
    return {
        "status": claim_support.get("status"),
        "ok": claim_support.get("ok"),
        "claim_count": _compact_int(claim_support.get("claim_count")),
        "weak_or_unsourced_count": _compact_int(
            claim_support.get("weak_or_unsourced_count")
        ),
        "source_context_blocked_count": _compact_int(
            claim_support.get("source_context_blocked_count")
        ),
        "status_counts": claim_support.get("status_counts", {}),
        "source_context_status_counts": claim_support.get(
            "source_context_status_counts",
            {},
        ),
        "sample_rows": sample_rows,
        "problem_rows": problem_rows[:8],
    }


def _stable_action_id(prefix: str, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}:{digest}"


def _append_action_row(
    rows: List[Dict[str, Any]],
    *,
    text: Any,
    source: str,
    action_type: str,
    condition: Optional[str] = None,
) -> None:
    label = _compact_text(text)
    if not label:
        return
    row = {
        "action_id": _stable_action_id(action_type, f"{source}\n{condition or ''}\n{label}"),
        "action_type": action_type,
        "source": source,
        "label": label,
    }
    if condition:
        row["condition"] = _compact_text(condition)
    rows.append(row)


def _report_action_authority(
    *,
    ledger: Dict[str, Any],
    brief: Dict[str, Any],
    graph_actions: List[Any],
    next_actions: List[Any],
    unsupported: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a typed action surface for report renderers.

    This is a read model, not an executor. It gives renderers and QA a compact
    list of what can be recommended now, what is only conditional, what should
    be deferred, and what must not be upgraded.
    """
    allowed_now: List[Dict[str, Any]] = []
    conditional: List[Dict[str, Any]] = []
    deferred: List[Dict[str, Any]] = []
    forbidden_upgrades: List[Dict[str, Any]] = []

    _append_action_row(
        allowed_now,
        text=brief.get("prerequisite_action"),
        source="planning_brief.prerequisite_action",
        action_type="allowed_now",
    )
    _append_action_row(
        allowed_now,
        text=brief.get("main_test_or_choice"),
        source="planning_brief.main_test_or_choice",
        action_type="allowed_now",
    )

    for item in _compact_list(next_actions, 12):
        _append_action_row(
            allowed_now,
            text=item,
            source="support_contract.next_actions",
            action_type="allowed_now",
        )

    for action in graph_actions:
        if isinstance(action, dict):
            label = action.get("reason") or action.get("targets") or action.get("action_type")
            _append_action_row(
                allowed_now,
                text=label,
                source="trace.graph_rd_actions",
                action_type=str(action.get("action_type") or "graph_action"),
            )

    decision_rule = brief.get("decision_rule_plain")
    if isinstance(decision_rule, dict):
        for condition, text in decision_rule.items():
            _append_action_row(
                conditional,
                text=text,
                source="planning_brief.decision_rule_plain",
                action_type="conditional_action",
                condition=str(condition),
            )

    ledger_decision_rule = ledger.get("decision_rule")
    if isinstance(ledger_decision_rule, dict):
        for condition, text in ledger_decision_rule.items():
            _append_action_row(
                conditional,
                text=text,
                source="ledger.decision_rule",
                action_type="conditional_action",
                condition=str(condition),
            )

    for item in _compact_list(brief.get("what_to_defer"), 10):
        _append_action_row(
            deferred,
            text=item,
            source="planning_brief.what_to_defer",
            action_type="deferred_action",
        )
    for item in _compact_list(ledger.get("premature_focus_areas"), 10):
        if isinstance(item, dict):
            text = item.get("area") or item.get("claim") or item.get("why_premature")
        else:
            text = item
        _append_action_row(
            deferred,
            text=text,
            source="ledger.premature_focus_areas",
            action_type="deferred_action",
        )

    for row in unsupported[:12]:
        if not isinstance(row, dict):
            continue
        _append_action_row(
            forbidden_upgrades,
            text=row.get("claim"),
            source="support_contract.unsupported_or_unresolved",
            action_type="forbidden_upgrade",
        )

    for value in (
        ledger.get("confirmation_status"),
        ledger.get("forecast_status"),
        ledger.get("epistemic_note"),
    ):
        if value:
            _append_action_row(
                forbidden_upgrades,
                text=value,
                source="ledger.claim_strength_boundary",
                action_type="forbidden_upgrade",
            )

    return {
        "schema": "ztare-report-action-authority-v1",
        "policy": (
            "A report may recommend allowed_now rows, may present conditional "
            "rows only under their stated condition, may name deferred rows only "
            "as deferred, and must not turn forbidden_upgrades into supported "
            "claims or recommendations."
        ),
        "allowed_now": allowed_now,
        "conditional": conditional,
        "deferred": deferred,
        "forbidden_upgrades": forbidden_upgrades,
    }


def _synthesis_input_binding_status(
    ledger: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    artifact_paths = [str(path) for path in context.get("artifact_paths", [])]
    current_binding = build_artifact_input_binding(artifact_paths)
    meta = ledger.get("_meta") if isinstance(ledger.get("_meta"), dict) else {}
    ledger_paths = meta.get("artifact_paths") if isinstance(meta, dict) else None
    ledger_digest = meta.get("artifact_input_digest") if isinstance(meta, dict) else None
    status = "fresh"
    reason = "Ledger artifact binding matches the current synthesis inputs."
    ok = True
    if not artifact_paths:
        status = "not_applicable"
        reason = "No artifact paths were supplied for this support contract."
    elif not meta or not ledger_paths or not ledger_digest:
        status = "unbound"
        ok = False
        reason = (
            "Ledger has no content-hash binding for the artifact inputs; regenerate "
            "synthesis before treating the report as current."
        )
    elif [str(path) for path in ledger_paths] != artifact_paths:
        status = "path_mismatch"
        ok = False
        reason = "Ledger artifact path set differs from the current synthesis context."
    elif ledger_digest != current_binding.get("digest"):
        status = "digest_mismatch"
        ok = False
        reason = "Ledger artifact content hash differs from the current synthesis inputs."
    return {
        "schema": "ztare-synthesis-input-binding-status-v1",
        "ok": ok,
        "status": status,
        "reason": reason,
        "current_digest": current_binding.get("digest"),
        "ledger_digest": ledger_digest,
        "artifact_count": len(artifact_paths),
    }


def build_report_support_contract(
    *,
    ledger: Dict[str, Any],
    brief: Dict[str, Any],
    context: Dict[str, Any],
    history_summary: Optional[Dict[str, Any]] = None,
    autoresearch_review_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Deterministic read-model that constrains post-iteration reports.

    The renderer remains free to write well, but this contract carries the
    authority boundary: what may be stated as supported, what must be caveated,
    and which trace facts are operational readiness rather than substantive
    evidence.
    """
    review_status = ledger.get("review_status")
    if not isinstance(review_status, dict):
        review_status = {}
    trace = autoresearch_review_context if isinstance(autoresearch_review_context, dict) else {}
    trace_recent_loop = trace.get("recent_loop") if isinstance(trace.get("recent_loop"), dict) else {}
    trace_surfaces = trace.get("surfaces") if isinstance(trace.get("surfaces"), dict) else {}
    latest_provider_failure = bool(trace_recent_loop.get("latest_provider_failure_observed"))

    runtime_risks: List[Any] = []
    runtime_caveats: List[Any] = []
    for item in _compact_list(review_status.get("runtime_risks"), 8):
        text = str(item or "")
        if "budget exhausted" in text.lower():
            runtime_caveats.append(
                "Iteration budget ended on recent runs; treat conclusions as bounded by the configured iteration count."
            )
        elif (
            not latest_provider_failure
            and ("provider" in text.lower() or "timeout" in text.lower())
        ):
            runtime_caveats.append(item)
        else:
            runtime_risks.append(item)
    latest_exit_reason = str(trace_recent_loop.get("latest_run_exit_reason") or "").strip()
    if latest_exit_reason == "budget_exhausted":
        runtime_caveats.append(
            "Latest loop ended at the configured iteration budget; this is a run-scope caveat, not a provider failure."
        )
    if latest_provider_failure:
        runtime_risks.append("Provider/runtime failure observed in the latest autoresearch trace; do not treat an incomplete run as substantive falsification.")
    elif trace_recent_loop.get("provider_failure_observed"):
        runtime_caveats.append(
            "Historical provider/runtime failures exist in the run history; separate those rows from the current trace before drawing substantive conclusions."
        )
    runtime_risks.extend(_compact_list(trace_surfaces.get("launch_preflight_errors"), 5))
    evidence_compile_status = _surface_status(trace_surfaces.get("evidence_compile_freshness"))
    evidence_output_status = _surface_status(trace_surfaces.get("evidence_output_binding"))
    evidence_replay = trace_surfaces.get("evidence_replay")
    evidence_replay_status = _surface_status(evidence_replay)
    evidence_replay_required = (
        bool(evidence_replay.get("required")) if isinstance(evidence_replay, dict) else False
    )
    evidence_replay_ok = (
        bool(evidence_replay.get("ok")) if evidence_replay_required else True
    )
    evidence_readiness_status = "fresh"
    if evidence_compile_status in {"stale", "unverified", "missing_provenance"}:
        evidence_readiness_status = "blocked"
    if evidence_output_status in {"stale", "unverified", "unverified_missing_output_hash"}:
        evidence_readiness_status = "blocked"
    if evidence_replay_required and not evidence_replay_ok:
        evidence_readiness_status = "blocked"
    evidence_readiness = {
        "status": evidence_readiness_status,
        "compile_provenance_status": evidence_compile_status,
        "output_binding_status": evidence_output_status,
        "replay_required": evidence_replay_required,
        "replay_status": evidence_replay_status,
        "replay_ok": evidence_replay_ok,
    }
    claim_support = (
        trace_surfaces.get("claim_support")
        if isinstance(trace_surfaces.get("claim_support"), dict)
        else {}
    )
    if evidence_compile_status in {"stale", "unverified", "missing_provenance"}:
        runtime_risks.append(
            f"Compiled-evidence provenance is {evidence_compile_status}; do not treat the rendered report evidence as fresh."
        )
    if evidence_output_status in {"stale", "unverified", "unverified_missing_output_hash"}:
        runtime_risks.append(
            f"Compiled-evidence output binding is {evidence_output_status}; do not present the rendered evidence as a fresh replay."
        )
    if evidence_replay_required and evidence_replay_status != "ok":
        runtime_risks.append(
            "Evidence readiness is blocked: compiled-evidence replay is "
            f"{evidence_replay_status or 'missing'}."
        )
    synthesis_input_binding = _synthesis_input_binding_status(ledger, context)
    if not synthesis_input_binding["ok"]:
        runtime_risks.append(synthesis_input_binding["reason"])

    blockers = list(_compact_list(review_status.get("blockers"), 8))
    kernel_entry = trace.get("kernel_entry") if isinstance(trace.get("kernel_entry"), dict) else {}
    blockers.extend(_compact_list(kernel_entry.get("blockers"), 8))
    blockers.extend(_compact_list(trace.get("blocking_missing"), 8))
    if evidence_replay_required and evidence_replay_status != "ok":
        blockers.append(
            {
                "id": "evidence_readiness",
                "surface": "evidence_replay",
                "status": evidence_replay_status or "missing",
                "reason": (
                    "Evidence readiness is blocked because compiled evidence "
                    "replay is required but not verified."
                ),
            }
        )
    if not synthesis_input_binding["ok"]:
        blockers.append(
            {
                "id": "synthesis_input_binding",
                "status": synthesis_input_binding["status"],
                "reason": synthesis_input_binding["reason"],
            }
        )

    next_actions = list(_compact_list(review_status.get("next_actions"), 8))
    for action in _compact_list(trace.get("next_actions"), 8):
        if isinstance(action, dict):
            command = str(action.get("command") or "").strip()
            label = str(action.get("label") or "").strip()
            if command:
                next_actions.append(f"{label}: {command}" if label else command)
        elif action:
            next_actions.append(action)

    unsupported = []
    for row in _compact_list(ledger.get("unsupported_narratives"), 8):
        if isinstance(row, dict):
            unsupported.append(
                {
                    "claim": row.get("claim"),
                    "why_unsupported": row.get("why_unsupported"),
                    "confidence": row.get("confidence"),
                }
            )
    for claim in _compact_list(ledger.get("overclaim_boundary"), 10):
        unsupported.append({"claim": claim, "why_unsupported": "Listed as an overclaim boundary."})

    graph_actions = _compact_list(trace.get("graph_rd_actions"), 8)
    health_gaps = _compact_list(trace.get("health_evidence_gaps"), 8)
    recovery_actions = _compact_list(trace.get("recovery_actions"), 8)
    action_authority = _report_action_authority(
        ledger=ledger,
        brief=brief,
        graph_actions=graph_actions,
        next_actions=next_actions,
        unsupported=unsupported,
    )
    compact_blockers = _compact_list(blockers, 12)
    compact_runtime_risks = _compact_list(runtime_risks, 12)
    compact_runtime_caveats = _compact_list(runtime_caveats, 12)
    weak_or_unsourced_count = _compact_int(claim_support.get("weak_or_unsourced_count"))
    source_context_blocked_count = _compact_int(
        claim_support.get("source_context_blocked_count")
    )
    source_claim_support = _claim_support_summary(claim_support)
    status_reasons: list[str] = []
    if compact_blockers:
        status_reasons.append("report_blockers_present")
    if evidence_readiness_status != "fresh":
        status_reasons.append(f"evidence_readiness_{evidence_readiness_status}")
    if not synthesis_input_binding["ok"]:
        status_reasons.append(f"synthesis_input_binding_{synthesis_input_binding['status']}")
    if compact_runtime_risks:
        status_reasons.append("runtime_risks_present")
    if weak_or_unsourced_count:
        status_reasons.append("weak_or_unsourced_claim_support_present")
    if source_context_blocked_count:
        status_reasons.append("claim_support_source_context_blocked")
    trace_status = str(trace.get("status") or "").strip()
    if trace_status and trace_status not in {"ok", "ready", "complete_trace"}:
        status_reasons.append(f"trace_status_{trace_status}")
    status = "ready"
    if compact_blockers:
        status = "blocked"
    elif status_reasons:
        status = "attention"
    return {
        "schema": "ztare-synthesis-report-support-contract-v1",
        "ok": status != "blocked",
        "status": status,
        "status_reasons": status_reasons,
        "project": context.get("project_name"),
        "renderer_type": context.get("renderer_type"),
        "trace_status": trace_status or None,
        "trace_readiness": trace.get("readiness"),
        "synthesis_input_binding": synthesis_input_binding,
        "evidence_readiness_status": evidence_readiness_status,
        "source_claim_support": source_claim_support,
        "source_artifact_paths": context.get("artifact_paths", []),
        "claim_strength": {
            "confirmation_status": ledger.get("confirmation_status"),
            "forecast_status": ledger.get("forecast_status"),
            "epistemic_note": ledger.get("epistemic_note"),
        },
        "supported_claims": _claim_rows(ledger.get("supported_hypotheses")),
        "hardest_conclusion": ledger.get("hardest_conclusion"),
        "unsupported_or_unresolved": unsupported,
        "review_readiness": {
            "ledger_readiness": review_status.get("readiness"),
            "trace_readiness": trace.get("readiness"),
            "trace_status": trace.get("status"),
            "kernel_entry": trace.get("kernel_entry"),
            "source_preflight_ok": trace_surfaces.get("source_preflight_ok"),
            "source_preflight_blocking": trace_surfaces.get("source_preflight_blocking", []),
            "evidence_readiness": evidence_readiness,
            "claim_support": {
                "status": source_claim_support["status"],
                "claim_count": source_claim_support["claim_count"],
                "weak_or_unsourced_count": source_claim_support[
                    "weak_or_unsourced_count"
                ],
                "source_context_blocked_count": source_claim_support[
                    "source_context_blocked_count"
                ],
                "status_counts": source_claim_support["status_counts"],
                "source_context_status_counts": source_claim_support[
                    "source_context_status_counts"
                ],
            },
            "launch_preflight_ok": trace_surfaces.get("launch_preflight_ok"),
            "eval_history_rows": trace_surfaces.get("eval_history_rows"),
        },
        "blockers": compact_blockers,
        "runtime_risks": compact_runtime_risks,
        "runtime_caveats": compact_runtime_caveats,
        "graph_and_gap_actions": {
            "graph_rd_actions": graph_actions,
            "health_evidence_gaps": health_gaps,
            "recovery_actions": recovery_actions,
        },
        "report_action_authority": action_authority,
        "next_actions": _compact_list(next_actions, 12),
        "history_scope": (history_summary or {}).get("summary_scope"),
        "required_report_rules": [
            "Only present ledger-supported claims as supported.",
            "Mention unresolved blockers or source-preflight failures when they affect interpretation.",
            "Mention runtime/provider failures as execution caveats, not as evidence against the substantive claim.",
            "Treat normal iteration-budget exhaustion as run scope, not as a provider failure.",
            "Mention stale or unbound synthesis inputs before presenting a generated report as current.",
            "Mention blocked evidence readiness before making evidence-backed conclusions.",
            "Mention weak or unsourced claim-support rows before presenting a claim as source-backed.",
            "Mention stale or unverified claim-support source context before presenting a claim as source-backed.",
            "Treat trace readiness, kernel-entry status, graph actions, and health gaps as review metadata, not proof of the thesis.",
            "Demote or omit any claim listed in unsupported_or_unresolved.",
            "Preserve tense and epistemic status: do not convert historical facts into future recommendations, and do not upgrade directional or deferred findings into completion or proof.",
            "Only recommend actions authorized by report_action_authority.allowed_now or conditionally authorized under report_action_authority.conditional.",
            "Preserve the next decisive test or next action when the claim remains unresolved.",
        ],
    }


def write_report_support_contract(
    project_dir: Path,
    *,
    ledger: Dict[str, Any],
    brief: Dict[str, Any],
    context: Dict[str, Any],
    history_summary: Optional[Dict[str, Any]] = None,
    autoresearch_review_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    contract = build_report_support_contract(
        ledger=ledger,
        brief=brief,
        context=context,
        history_summary=history_summary,
        autoresearch_review_context=autoresearch_review_context,
    )
    write_json(synthesis_paths(project_dir)["report_support_contract"], contract)
    return contract


def render_artifact(ledger: Dict[str, Any], brief: Dict[str, Any], context: Dict[str, Any]) -> str:
    if ACTIVE_LLM is None:
        raise RuntimeError("ACTIVE_LLM is not configured.")
    project_dir = Path(context["project_dir"])
    renderer_prompt = load_prompt(RENDERERS_DIR / f"{context['renderer_type']}.md")
    # Provide a stable "today" anchor to prevent the renderer from fabricating dates.
    run_date = time.strftime("%B %d, %Y")
    dbg(f"Render artifact: renderer_type={context['renderer_type']} run_date={run_date}")
    history_summary = load_history_summary_for_context(context) or {}
    autoresearch_review_context = load_autoresearch_review_context_for_context(context)
    report_support_contract = write_report_support_contract(
        project_dir,
        ledger=ledger,
        brief=brief,
        context=context,
        history_summary=history_summary,
        autoresearch_review_context=autoresearch_review_context,
    )
    aggregated_corpus = context.get("aggregated_corpus")
    prompt_parts = [renderer_prompt]
    # User direction (highest-priority STYLE/EMPHASIS/STRUCTURE steer; never overrides the support
    # contract's factual boundaries below). Placed near the top so the renderer weights it.
    if USER_INSTRUCTIONS:
        prompt_parts.append(
            "USER DIRECTION (follow this for emphasis, length, structure-within-template, and voice — but "
            "NEVER assert anything the support contract below does not license):\n" + USER_INSTRUCTIONS
        )
    prompt_parts += [
        f"Run date: {run_date}",
        f"Audience: {context['audience']}",
        f"Tone: {context['tone']}",
        f"Project type: {context['project_type']}",
        "Planning brief JSON:",
        json.dumps(brief, indent=2, sort_keys=True),
        "Insight ledger JSON:",
        json.dumps(ledger, indent=2, sort_keys=True),
        "History summary JSON:",
        json.dumps(history_summary, indent=2, sort_keys=True),
        "Report support contract JSON (deterministic authority boundary; obey this when it is stricter than the prose prompt):",
        json.dumps(report_support_contract, indent=2, sort_keys=True),
    ]
    # Inject project charter so the renderer knows the required output structure.
    charter_path = project_dir / "project_charter.md"
    if charter_path.exists():
        charter_text = charter_path.read_text(encoding="utf-8").strip()
        if charter_text:
            prompt_parts.append(
                "Project charter (required content — your report MUST address every required element, though section structure follows the renderer template):\n"
                + charter_text
            )
    if aggregated_corpus is not None:
        prompt_parts.append("Aggregated corpus JSON (multi-project mode):")
        prompt_parts.append(json.dumps(aggregated_corpus, indent=2, sort_keys=True))
    prompt = "\n\n".join(prompt_parts)
    try:
        report = ACTIVE_LLM.call(prompt).strip()
    except Exception as exc:  # noqa: BLE001
        raise SynthesisStepError(
            "render_artifact",
            f"Could not render artifact for renderer '{context['renderer_type']}': {exc}",
            output_path=Path(context["output_paths"]["candidate_report"]),
        ) from exc
    refined = refine_artifact(report, ledger, brief, context)
    write_text(Path(context["output_paths"]["candidate_report"]), refined)
    return refined


def refine_artifact(report: str, ledger: Dict[str, Any], brief: Dict[str, Any], context: Dict[str, Any]) -> str:
    if ACTIVE_LLM is None:
        raise RuntimeError("ACTIVE_LLM is not configured.")
    renderer_type = context["renderer_type"]
    prompt_path = PROMPTS_DIR / f"refine_{renderer_type}.md"
    if not prompt_path.exists():
        return report
    dbg(f"Refine artifact: renderer_type={renderer_type} prompt={prompt_path}")
    project_dir = Path(context["project_dir"])
    report_support_contract = load_json_if_valid(synthesis_paths(project_dir)["report_support_contract"]) or {}
    prompt = "\n\n".join(
        [
            load_prompt(prompt_path),
            *(["USER DIRECTION (honour for emphasis/length/structure/voice; never beyond the support contract):\n" + USER_INSTRUCTIONS] if USER_INSTRUCTIONS else []),
            f"Audience: {context['audience']}",
            f"Tone: {context['tone']}",
            f"Project type: {context['project_type']}",
            "Planning brief JSON:",
            json.dumps(brief, indent=2, sort_keys=True),
            "Insight ledger JSON:",
            json.dumps(ledger, indent=2, sort_keys=True),
            "Report support contract JSON:",
            json.dumps(report_support_contract, indent=2, sort_keys=True),
            "Draft artifact:",
            report,
        ]
    )
    try:
        return ACTIVE_LLM.call(prompt).strip()
    except Exception as exc:  # noqa: BLE001
        raise SynthesisStepError(
            "refine_artifact",
            f"Could not refine artifact for renderer '{renderer_type}': {exc}",
            output_path=Path(context["output_paths"]["candidate_report"]),
        ) from exc


def qa_artifact(ledger: Dict[str, Any], brief: Dict[str, Any], report: str, context: Dict[str, Any]) -> Dict[str, Any]:
    if ACTIVE_QA_LLM is None:
        raise RuntimeError("ACTIVE_QA_LLM is not configured.")
    project_dir = Path(context["project_dir"])
    dbg(f"QA artifact: renderer_type={context['renderer_type']} threshold={ACTIVE_QA_THRESHOLD}")
    history_summary = load_history_summary_for_context(context) or {}
    aggregated_corpus = context.get("aggregated_corpus")
    report_support_contract = load_json_if_valid(synthesis_paths(project_dir)["report_support_contract"])
    if report_support_contract is None:
        report_support_contract = write_report_support_contract(
            project_dir,
            ledger=ledger,
            brief=brief,
            context=context,
            history_summary=history_summary,
            autoresearch_review_context=load_autoresearch_review_context_for_context(context),
        )
    qa_parts = [
        load_prompt(PROMPTS_DIR / "qa_artifact.md"),
        f"Renderer type: {context['renderer_type']}",
        "Planning brief JSON:",
        json.dumps(brief, indent=2, sort_keys=True),
        "Insight ledger JSON:",
        json.dumps(ledger, indent=2, sort_keys=True),
        "History summary JSON:",
        json.dumps(history_summary, indent=2, sort_keys=True),
        "Report support contract JSON:",
        json.dumps(report_support_contract, indent=2, sort_keys=True),
    ]
    if aggregated_corpus is not None:
        qa_parts.append("Aggregated corpus JSON (multi-project mode):")
        qa_parts.append(json.dumps(aggregated_corpus, indent=2, sort_keys=True))
    qa_parts.append("Rendered artifact:")
    qa_parts.append(report)
    prompt = "\n\n".join(qa_parts)
    qa_output_path = Path(context["output_paths"]["qa"])
    raw_response = ACTIVE_QA_LLM.call(prompt)
    qa = normalize_qa_payload(
        parse_json_step_response(
            raw_response,
            step="qa_artifact",
            output_path=qa_output_path,
            failure_message=f"Could not QA artifact for renderer '{context['renderer_type']}'",
        )
    )
    final_path = Path(context.get("output_paths", {}).get("final_report") or synthesis_paths(project_dir)["final_report"])
    qa["_meta"] = {
        "qa_threshold": ACTIVE_QA_THRESHOLD,
        "candidate_report_path": str(Path(context["output_paths"]["candidate_report"])),
        "final_report_path": str(final_path),
        "report_support_contract_status": report_support_contract.get("status"),
        "report_support_contract_ok": report_support_contract.get("ok"),
        "report_support_contract_status_reasons": report_support_contract.get("status_reasons", []),
    }

    blocking_issues = qa_blocking_issues(qa)
    qa["_meta"]["blocking_issue_count"] = len(blocking_issues)
    if blocking_issues:
        qa["_meta"]["blocking_issues"] = blocking_issues

    contract_allows_write = report_support_contract.get("ok") is not False
    if qa_passes_for_report_write(qa, threshold=ACTIVE_QA_THRESHOLD) and contract_allows_write:
        write_text(final_path, report)
        qa["_meta"]["report_written"] = True
        qa["_meta"]["existing_final_report_unmodified"] = False
    else:
        qa["_meta"]["report_written"] = False
        qa["_meta"]["existing_final_report_unmodified"] = final_path.exists()
        if not contract_allows_write:
            qa["_meta"]["report_write_blocked_by_support_contract"] = True

    write_json(qa_output_path, qa)
    return qa


def repair_artifact_after_qa(
    *,
    report: str,
    qa: Dict[str, Any],
    ledger: Dict[str, Any],
    brief: Dict[str, Any],
    context: Dict[str, Any],
) -> str:
    if ACTIVE_LLM is None:
        raise RuntimeError("ACTIVE_LLM is not configured.")
    project_dir = Path(context["project_dir"])
    report_support_contract = load_json_if_valid(synthesis_paths(project_dir)["report_support_contract"]) or {}
    prompt = "\n\n".join(
        [
            "Revise the rendered artifact so it passes the QA verdict.",
            "Return the complete revised artifact only. Do not add commentary.",
            "Preserve the renderer structure and reader-facing tone.",
            "Fix every QA issue directly; do not merely add vague caveats.",
            "Obey the report support contract when it is stricter than the planning brief.",
            "Do not introduce any new claims, dates, actions, thresholds, or mechanisms.",
            "If QA flags an unsupported action, remove it unless the inputs explicitly support it.",
            f"Renderer type: {context['renderer_type']}",
            f"Audience: {context['audience']}",
            f"Tone: {context['tone']}",
            "QA verdict JSON:",
            json.dumps(qa, indent=2, sort_keys=True),
            "Planning brief JSON:",
            json.dumps(brief, indent=2, sort_keys=True),
            "Insight ledger JSON:",
            json.dumps(ledger, indent=2, sort_keys=True),
            "Report support contract JSON:",
            json.dumps(report_support_contract, indent=2, sort_keys=True),
            "Artifact to revise:",
            report,
        ]
    )
    try:
        return ACTIVE_LLM.call(prompt).strip()
    except Exception as exc:  # noqa: BLE001
        raise SynthesisStepError(
            "repair_artifact_after_qa",
            f"Could not repair artifact after QA for renderer '{context['renderer_type']}': {exc}",
            output_path=Path(context["output_paths"]["candidate_report"]),
        ) from exc


def qa_artifact_with_repair(
    ledger: Dict[str, Any],
    brief: Dict[str, Any],
    report: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    repair_attempts = max(0, int(ACTIVE_QA_REPAIR_ATTEMPTS))
    current_report = report
    qa = qa_artifact(ledger, brief, report, context)
    if qa_passes_for_report_write(qa, threshold=ACTIVE_QA_THRESHOLD):
        qa["_meta"]["qa_repair_attempted"] = False
        qa["_meta"]["qa_repair_attempts"] = 0
        qa["_meta"]["qa_repair_attempt_limit"] = repair_attempts
        write_json(Path(context["output_paths"]["qa"]), qa)
        return qa

    repair_history: List[Dict[str, Any]] = []
    previous_qa = qa
    for attempt in range(1, repair_attempts + 1):
        repair_history.append(
            {
                "attempt": attempt,
                "source_score": previous_qa.get("score"),
                "source_issue_count": len(
                    previous_qa.get("issues") if isinstance(previous_qa.get("issues"), list) else []
                ),
                "source_blocking_issue_count": len(qa_blocking_issues(previous_qa)),
            }
        )
        current_report = repair_artifact_after_qa(
            report=current_report,
            qa=previous_qa,
            ledger=ledger,
            brief=brief,
            context=context,
        )
        write_text(Path(context["output_paths"]["candidate_report"]), current_report)
        previous_qa = qa_artifact(ledger, brief, current_report, context)
        previous_qa["_meta"]["qa_repair_attempted"] = True
        previous_qa["_meta"]["qa_repair_attempts"] = attempt
        previous_qa["_meta"]["qa_repair_attempt_limit"] = repair_attempts
        previous_qa["_meta"]["qa_repair_history"] = repair_history
        write_json(Path(context["output_paths"]["qa"]), previous_qa)
        if qa_passes_for_report_write(previous_qa, threshold=ACTIVE_QA_THRESHOLD):
            return previous_qa

    return previous_qa


def suggest_renderer_template(project_dir: Path, context: Dict[str, Any], llm: LLMClient) -> None:
    prompt_path = RENDERERS_DIR / f"{context['renderer_type']}.md"
    if prompt_path.exists():
        return

    generation_prompt = "\n\n".join(
        [
            "You are designing a hardcoded renderer prompt for a synthesis system.",
            "Write a reusable renderer prompt in markdown for the requested renderer type.",
            "The prompt must instruct a model to transform a structured insight ledger JSON into a concise artifact.",
            "The prompt must include:",
            "- no mention of logs, engines, scores, simulations, JSON, or internal process",
            "- no new insights beyond the ledger",
            "- epistemic honesty",
            "- a clear section structure appropriate for the artifact type",
            "Return markdown only.",
            f"Requested renderer type: {context['renderer_type']}",
            f"Project type: {context['project_type']}",
            f"Audience: {context['audience']}",
            f"Tone: {context['tone']}",
        ]
    )

    try:
        rendered_prompt = llm.call(generation_prompt).strip()
    except Exception:  # noqa: BLE001
        rendered_prompt = "\n".join(
            [
                "You are an elite advisor writing a concise artifact from a structured insight ledger in JSON.",
                "",
                "Important rules:",
                "- Do not mention the engine, logs, scores, simulations, JSON, or internal process.",
                "- Do not add any new insights not present in the JSON.",
                "- Write in plain language.",
                "- Be high conviction, but epistemically honest.",
                "",
                "Use a concise structure appropriate to the artifact type.",
            ]
        )

    write_text(prompt_path, rendered_prompt)


def print_status(label: str, path: Path) -> None:
    print(f"{label}: {path}")


def write_consolidated_report(project_dir: Path, memo_path: Path, appendix_path: Path) -> Path:
    consolidated = project_dir / "report_consolidated.md"
    memo = read_text(memo_path).strip()
    appendix = read_text(appendix_path).strip()
    content = "\n\n".join([memo, "---", appendix, ""])
    write_text(consolidated, content)
    return consolidated


def _load_support_contract_context(project_dir: Path, renderer_type: Optional[str]) -> Optional[Dict[str, Any]]:
    candidates: List[Path] = []
    if renderer_type:
        candidates.append(renderer_scoped_paths(project_dir, renderer_type)["context"])
    candidates.append(synthesis_paths(project_dir)["context"])
    candidates.extend(sorted((project_dir / SYNTHESIS_DIRNAME).glob("context.*.json")))
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except Exception:  # noqa: BLE001
            resolved = candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        payload = load_json_if_valid(candidate)
        if payload is not None:
            return payload
    return None


def run_support_contract_only(args: argparse.Namespace) -> int:
    if args.projects:
        print("--support-contract-only is only supported with --project.", file=sys.stderr)
        return 2
    if args.pack:
        print("--support-contract-only is not supported with --pack.", file=sys.stderr)
        return 2
    project_dir = resolve_project_dir(args.project)
    paths = synthesis_paths(project_dir)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    maybe_write_autoresearch_review_context(project_dir)
    context = _load_support_contract_context(project_dir, args.renderer_type)
    if context is None:
        print(
            "No synthesis context found. Run make synth once, then use --support-contract-only "
            "to refresh the deterministic report authority check.",
            file=sys.stderr,
        )
        return 2
    context = refresh_context_artifacts(project_dir, context)
    ledger_path = Path(context.get("output_paths", {}).get("ledger") or paths["ledger"])
    ledger = load_json_if_valid(ledger_path)
    if ledger is None:
        print(f"No usable ledger found at {ledger_path}.", file=sys.stderr)
        return 2
    brief_path = Path(context.get("output_paths", {}).get("brief") or paths["brief"])
    brief = load_json_if_valid(brief_path) or {}
    history_summary = load_history_summary_for_context(context)
    autoresearch_review_context = load_autoresearch_review_context_for_context(context)
    contract = write_report_support_contract(
        project_dir,
        ledger=ledger,
        brief=brief,
        context=context,
        history_summary=history_summary,
        autoresearch_review_context=autoresearch_review_context,
    )
    print(json.dumps(
        {
            "status": contract.get("status"),
            "ok": contract.get("ok"),
            "status_reasons": contract.get("status_reasons", []),
            "synthesis_input_binding": contract.get("synthesis_input_binding"),
            "report_support_contract": str(paths["report_support_contract"]),
        },
        indent=2,
        sort_keys=True,
    ))
    return 0 if contract.get("ok") else 1


def run_multi_project_field_manual(project_names: List[str], args: argparse.Namespace) -> int:
    """Multi-project aggregation path for the field_manual renderer.

    Resolves each project, ensures each has a history_summary.json (running
    summarize_history if not), aggregates the tagged failures into a unioned
    payload with a provenance table, then runs render_artifact + qa_artifact
    once with the aggregated payload attached to the context.

    Output is written to [internal-ref]
    so the v0 hand-crafted artifact remains as the comparison baseline.
    """
    project_dirs = [resolve_project_dir(name) for name in project_names]
    dbg(f"Multi-project field manual: projects={project_names}")

    aggregated = aggregate_field_manual_corpus(project_dirs)
    if not aggregated["projects"]:
        print("No projects with usable history_summary.json found.", file=sys.stderr)
        return 2

    # Use the first project as the anchor for context resolution (audience/tone, output paths).
    anchor_dir = project_dirs[0]
    anchor_paths = synthesis_paths(anchor_dir)
    anchor_paths["dir"].mkdir(parents=True, exist_ok=True)

    context = sniff_context(
        anchor_dir,
        renderer_override="field_manual",
        history_mode_override=args.history_mode,
    )
    context["aggregated_corpus"] = aggregated
    context["multi_project"] = True
    context["multi_project_names"] = project_names

    # Persist the aggregated corpus alongside the anchor project for inspection.
    aggregated_path = anchor_paths["dir"] / "field_manual_aggregated_corpus.json"
    write_json(aggregated_path, aggregated)
    dbg(f"Aggregated corpus written to {aggregated_path}")

    # Build a minimal brief and ledger for the renderer call. The field manual
    # renderer is instructed to use aggregated_corpus as the source of truth in
    # multi-project mode, so the brief and ledger are intentionally lightweight.
    brief = {
        "_meta": {
            "derived_from": "multi_project_aggregation",
            "renderer_type": "field_manual",
            "project_names": project_names,
        },
    }
    ledger = {
        "_meta": {
            "derived_from": "multi_project_aggregation",
            "project_count": len(aggregated["projects"]),
        },
    }

    try:
        report = render_artifact(ledger, brief, context)
    except SynthesisStepError as exc:
        print(f"Multi-project render failed: {exc}", file=sys.stderr)
        return 2

    qa = qa_artifact_with_repair(ledger, brief, report, context)

    distribution_path = REPO_ROOT / "research_areas" / "private" / "distribution" / "field_manual_auto.md"
    if qa_passes_for_report_write(qa, threshold=ACTIVE_QA_THRESHOLD):
        write_text(distribution_path, report)
        print(f"Multi-project field manual: QA passed with score {qa.get('score')}.")
        print(f"Written to: {distribution_path}")
        print(f"Aggregated corpus: {aggregated_path}")
        return 0

    print(
        f"Multi-project field manual: QA failed (score {qa.get('score')}, threshold {ACTIVE_QA_THRESHOLD}).",
        file=sys.stderr,
    )
    print(f"Candidate report kept at: {context['output_paths']['candidate_report']}", file=sys.stderr)
    print(f"Aggregated corpus: {aggregated_path}", file=sys.stderr)
    return 1


def run_multi_project_renderer(project_names: List[str], args: argparse.Namespace) -> int:
    project_dirs = [resolve_project_dir(name) for name in project_names]
    renderer_type = args.renderer_type or "research_note"
    anchor_dir = project_dirs[0]
    chosen_history_mode = args.history_mode or "focused"
    dbg(f"Multi-project renderer: projects={project_names} renderer={renderer_type}")

    context = sniff_context(
        anchor_dir,
        renderer_override=renderer_type,
        history_mode_override=chosen_history_mode,
    )
    aggregated = aggregate_multi_project_corpus(project_dirs, renderer_type, chosen_history_mode)
    context["multi_project"] = True
    context["multi_project_names"] = project_names
    context["aggregated_corpus"] = aggregated
    context["project_name"] = f"multi_project::{','.join(project_names)}"
    context["history_mode"] = chosen_history_mode
    context["history_summary_prompt_hash"] = prompt_hash(PROMPTS_DIR / "summarize_history.md")
    context["ledger_prompt_hash"] = prompt_hash(PROMPTS_DIR / "extract_ledger_multi_project.md")
    if len(set(aggregated.get("_meta", {}).get("project_types", []))) > 1:
        context["project_type"] = "general_analysis"
    scoped_paths = multi_project_scoped_paths(anchor_dir, renderer_type, project_names)
    context["output_paths"] = {key: str(path) for key, path in scoped_paths.items()}
    context["history_summary_path"] = str(scoped_paths["history_summary"])

    write_json(Path(context["output_paths"]["context"]), context)
    write_json(Path(context["output_paths"]["aggregated_corpus"]), aggregated)

    merged_history_summary = build_multi_project_history_summary(aggregated.get("projects", []))
    write_json(Path(scoped_paths["history_summary"]), merged_history_summary)

    try:
        ledger = extract_multi_project_ledger(anchor_dir, context)
        brief = derive_brief(anchor_dir, ledger, context)
        report = render_artifact(ledger, brief, context)
    except SynthesisStepError as exc:
        print(f"Multi-project render failed: {exc}", file=sys.stderr)
        return 2

    qa = qa_artifact_with_repair(ledger, brief, report, context)
    final_path = Path(context["output_paths"]["final_report"])
    if qa_passes_for_report_write(qa, threshold=ACTIVE_QA_THRESHOLD):
        write_text(final_path, report)
        print(f"Multi-project render: QA passed with score {qa.get('score')}.")
        print(f"Written to: {final_path}")
        print(f"Aggregated corpus: {context['output_paths']['aggregated_corpus']}")
        return 0

    print(
        f"Multi-project render: QA failed (score {qa.get('score')}, threshold {ACTIVE_QA_THRESHOLD}).",
        file=sys.stderr,
    )
    print(f"Candidate report kept at: {context['output_paths']['candidate_report']}", file=sys.stderr)
    print(f"Aggregated corpus: {context['output_paths']['aggregated_corpus']}", file=sys.stderr)
    return 1


def _humanize_project_name(project_name: str) -> str:
    """Convert project directory name to a short readable title and filename stem.

    'sample_research_project' -> title='Sample Research Project', stem='sample-research-project'
    """
    words = project_name.replace("-", "_").split("_")
    title = " ".join(w.capitalize() for w in words)
    stem = project_name.replace("_", "-")
    return title, stem


def generate_pdf(report_path: Path, project_name: str) -> bool:
    """Run pandoc to convert a Report.md to a styled PDF via eisvogel + xelatex.

    Returns True on success, False on failure (non-fatal).
    """
    title, stem = _humanize_project_name(project_name)
    date_str = time.strftime("%B %Y")
    pdf_path = report_path.parent / f"{stem}.pdf"

    cmd = [
        "pandoc", str(report_path),
        "-o", str(pdf_path),
        "--from", "markdown",
        "--template", "eisvogel",
        "--pdf-engine=xelatex",
        "-M", "graphics=true",
        "-V", "mainfont=Helvetica",
        "-V", f"title={title}",
        "-V", "author=Generated by ZTARE",
        "-V", f"date={date_str}",
        "-V", "titlepage=true",
        "-V", "titlepage-color=6C3082",
        "-V", "titlepage-text-color=FFFFFF",
        "-V", "titlepage-rule-color=FFFFFF",
        "-V", "titlepage-rule-height=2",
        "-V", "fontsize=12pt",
        "-V", "geometry:margin=1.2in",
        "-V", "colorlinks=true",
    ]

    print(f"\nGenerating PDF: {pdf_path.name}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"pandoc failed (exit {result.returncode}):", file=sys.stderr)
            if result.stderr:
                print(result.stderr.strip(), file=sys.stderr)
            print("PDF not generated. Install pandoc + eisvogel template + xelatex to enable.", file=sys.stderr)
            return False
        print(f"PDF written: {pdf_path}")
        return True
    except FileNotFoundError:
        print("pandoc not found — install pandoc to enable PDF generation.", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize a project into a ledger, report, and QA gate.")
    project_group = parser.add_mutually_exclusive_group(required=True)
    project_group.add_argument("--project", help="Project name under projects/ or a direct project path.")
    project_group.add_argument(
        "--projects",
        help="Comma-separated list of project names for multi-project aggregation. Requires --renderer-type.",
    )
    parser.add_argument(
        "--model",
        default="gemini",
        choices=sorted(MODEL_MAP.keys()),
        help="Model family to use for context sniffing, extraction, rendering, and QA.",
    )
    parser.add_argument(
        "--qa-model",
        default=None,
        choices=sorted(MODEL_MAP.keys()),
        help="Optional separate model family to use for QA. Defaults to --model.",
    )
    parser.add_argument(
        "--qa-threshold",
        type=int,
        default=DEFAULT_QA_THRESHOLD,
        help="Minimum QA score required to write the final Report.md.",
    )
    parser.add_argument(
        "--qa-repair-attempts",
        type=int,
        default=DEFAULT_QA_REPAIR_ATTEMPTS,
        help=(
            "Maximum number of QA-guided repair attempts before failing closed. "
            "Set to 0 to disable repair."
        ),
    )
    parser.add_argument(
        "--renderer-type",
        default=None,
        help="Optional renderer override, e.g. founder_memo or decision_brief.",
    )
    parser.add_argument(
        "--pack",
        default=None,
        choices=["founder"],
        help="Run a preconfigured artifact pack. 'founder' generates a founder memo plus a quantitative appendix.",
    )
    parser.add_argument(
        "--history-mode",
        default=None,
        choices=["focused", "full"],
        help="Optional history selection mode. Defaults by renderer type: focused for audience-facing memos, full for research-style artifacts.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging to stderr (selected artifacts, step boundaries, and retry errors).",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Generate a styled PDF from the final report using pandoc + eisvogel. Requires pandoc and xelatex.",
    )
    parser.add_argument(
        "--instructions",
        default=None,
        help=(
            "Optional natural-language direction for how to write the report (style, emphasis, length, "
            "structure-within-template). Applies to templated and dynamic renderers. Steers presentation "
            "only — the support contract still bounds every factual claim. Env: ZTARE_REPORT_INSTRUCTIONS."
        ),
    )
    parser.add_argument(
        "--support-contract-only",
        "--contract-only",
        dest="support_contract_only",
        action="store_true",
        help=(
            "Refresh synthesis/report_support_contract.json from existing synthesis "
            "artifacts without model calls or report rendering."
        ),
    )
    args = parser.parse_args()

    if args.support_contract_only:
        return run_support_contract_only(args)

    global ACTIVE_LLM, ACTIVE_QA_LLM, ACTIVE_QA_THRESHOLD, ACTIVE_QA_REPAIR_ATTEMPTS
    global DEBUG, USER_INSTRUCTIONS
    DEBUG = bool(args.debug)
    USER_INSTRUCTIONS = str(args.instructions or os.environ.get("ZTARE_REPORT_INSTRUCTIONS") or "").strip()
    ACTIVE_LLM = LLMClient(args.model)
    ACTIVE_QA_LLM = LLMClient(args.qa_model or args.model)
    ACTIVE_QA_THRESHOLD = args.qa_threshold
    ACTIVE_QA_REPAIR_ATTEMPTS = max(0, int(args.qa_repair_attempts))
    dbg(
        "Models: "
        f"model={args.model} qa_model={args.qa_model or args.model} "
        f"qa_threshold={args.qa_threshold} qa_repair_attempts={ACTIVE_QA_REPAIR_ATTEMPTS}"
    )

    if args.projects:
        if args.pack:
            print("--pack is not supported with --projects.", file=sys.stderr)
            return 2
        if not args.renderer_type:
            print("--projects requires --renderer-type (for example research_note or decision_brief).", file=sys.stderr)
            return 2
        project_names = [p.strip() for p in args.projects.split(",") if p.strip()]
        if not project_names:
            print("--projects must contain at least one project name.", file=sys.stderr)
            return 2
        if args.renderer_type == "field_manual":
            return run_multi_project_field_manual(project_names, args)
        return run_multi_project_renderer(project_names, args)

    if args.renderer_type == "field_manual":
        print(
            "--renderer-type field_manual requires --projects (multi-project aggregation). "
            "Use: --projects p1,p2,p3 --renderer-type field_manual",
            file=sys.stderr,
        )
        return 2

    project_dir = resolve_project_dir(args.project)
    base_paths = synthesis_paths(project_dir)
    base_paths["dir"].mkdir(parents=True, exist_ok=True)
    dbg(f"Start: project={args.project} project_dir={project_dir}")

    try:
        if args.pack == "founder":
            # Step 1: Founder memo
            memo_context = sniff_context(
                project_dir,
                renderer_override="founder_memo",
                history_mode_override=args.history_mode,
            )
            summarize_history(project_dir, memo_context)
            memo_context = refresh_context_artifacts(project_dir, memo_context)
            ledger = extract_ledger(project_dir, memo_context)
            memo_brief = derive_brief(project_dir, ledger, memo_context)
            memo_report = render_artifact(ledger, memo_brief, memo_context)
            memo_qa = qa_artifact_with_repair(ledger, memo_brief, memo_report, memo_context)

            # Step 2: Quantitative appendix, scoped by the memo brief.
            appendix_context = sniff_context(
                project_dir,
                renderer_override="quantitative_appendix",
                history_mode_override=args.history_mode,
            )
            appendix_context["memo_brief_path"] = memo_context["output_paths"]["brief"]
            summarize_history(project_dir, appendix_context)
            appendix_context = refresh_context_artifacts(project_dir, appendix_context)
            ledger = extract_ledger(project_dir, appendix_context)
            appendix_brief = derive_brief(project_dir, ledger, appendix_context)
            appendix_report = render_artifact(ledger, appendix_brief, appendix_context)
            appendix_qa = qa_artifact_with_repair(ledger, appendix_brief, appendix_report, appendix_context)

            print_status("Memo", Path(memo_context["output_paths"]["final_report"]))
            print_status("Appendix", Path(appendix_context["output_paths"]["final_report"]))
            consolidated_path = write_consolidated_report(
                project_dir,
                Path(memo_context["output_paths"]["final_report"]),
                Path(appendix_context["output_paths"]["final_report"]),
            )
            print_status("Consolidated", consolidated_path)

            if memo_qa.get("_meta", {}).get("report_written") and appendix_qa.get("_meta", {}).get("report_written"):
                print(f"QA passed (memo={memo_qa.get('score')}, appendix={appendix_qa.get('score')}).")
                return 0

            print("Pack failed QA; see renderer-scoped qa.*.json files under synthesis/.")
            return 1

        # Single-renderer mode.
        context = sniff_context(
            project_dir,
            renderer_override=args.renderer_type,
            history_mode_override=args.history_mode,
        )
        summarize_history(project_dir, context)
        context = refresh_context_artifacts(project_dir, context)
        ledger = extract_ledger(project_dir, context)
        brief = derive_brief(project_dir, ledger, context)
        report = render_artifact(ledger, brief, context)
        qa = qa_artifact_with_repair(ledger, brief, report, context)

        print_status("Context", Path(context["output_paths"]["context"]))
        print_status("History summary", base_paths["history_summary"])
        print_status("Ledger", base_paths["ledger"])
        print_status("Brief", Path(context["output_paths"]["brief"]))
        print_status("QA", Path(context["output_paths"]["qa"]))
        print_status("Candidate report", Path(context["output_paths"]["candidate_report"]))

        if qa["_meta"]["report_written"]:
            final_path = Path(context["output_paths"]["final_report"])
            print_status("Final report", final_path)
            print(f"QA passed with score {qa.get('score')}.")
            if args.pdf:
                generate_pdf(final_path, project_dir.name)
            return 0

        print(f"QA failed or scored below threshold ({args.qa_threshold}). Final report was not written.")
        return 1
    except SynthesisStepError as exc:
        print(
            f"Synthesis stopped during '{exc.step}': {exc}",
            file=sys.stderr,
        )
        if exc.output_path is not None:
            print(f"Last relevant output path: {exc.output_path}", file=sys.stderr)
        print(
            "No final report was written. Partial artifacts under synthesis/ were preserved. "
            "Retry the same command, switch --model/--qa-model, or rerun later if the provider is under load.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
