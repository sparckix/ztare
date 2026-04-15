import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.ztare.common import utils
from src.ztare.common.llm_runtime import LLMRuntime, LLMRuntimeError, MODEL_MAP
from src.ztare.common.paths import PROJECTS_DIR, PROMPTS_DIR, RENDERERS_DIR, REPO_ROOT


ROOT_DIR = REPO_ROOT

SYNTHESIS_DIRNAME = "synthesis"
CONTEXT_FILENAME = "context.json"
LEDGER_FILENAME = "ledger.json"
BRIEF_FILENAME = "brief.json"
HISTORY_SUMMARY_FILENAME = "history_summary.json"
QA_FILENAME = "qa.json"
CANDIDATE_REPORT_FILENAME = "Report.candidate.md"
FINAL_REPORT_FILENAME = "Report.md"
BEST_ITERATION_RE = re.compile(r"best_iteration:\s*([A-Za-z0-9_.-]+)")
HISTORY_FAMILY_RE = re.compile(r"^\d+_iter\d+_score_[^_]+_(.+)$")

DEFAULT_QA_THRESHOLD = 85
ACTIVE_LLM: Optional["LLMClient"] = None
ACTIVE_QA_LLM: Optional["LLMClient"] = None
ACTIVE_QA_THRESHOLD = DEFAULT_QA_THRESHOLD
DEBUG = False

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
        "renderer_type": "research_note",
        "audience": "policy analyst",
        "tone": "plainspoken, scenario-oriented",
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
            response = self.runtime.call_text(
                prompt,
                model_id=self.model_id,
                retries=retries,
                timeout_seconds=300,
                request_label="synthesis request",
                progress_printer=dbg,
                transient_wait_seconds=5,
                timeout_wait_seconds=2,
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
            note = (
                f" Renderer suggestion '{sniffed_renderer_type}' ignored; "
                f"defaulted to '{default_renderer_type}' unless --renderer-type is provided."
            )
            merged["reason"] = f"{merged['reason']}{note}".strip()

    merged["history_mode"] = history_mode_override or default_history_mode(merged["renderer_type"])
    merged["history_source_paths"] = [str(path) for path in all_relevant_history_paths(project_dir, project_type)]
    merged["artifact_paths"] = select_artifact_paths(project_dir, project_type, merged["history_mode"], merged["renderer_type"])
    merged["history_summary_prompt_hash"] = prompt_hash(PROMPTS_DIR / "summarize_history.md")
    merged["ledger_prompt_hash"] = prompt_hash(PROMPTS_DIR / "extract_ledger.md")

    out_paths = renderer_scoped_paths(project_dir, merged["renderer_type"])
    merged["output_paths"] = {key: str(path) for key, path in out_paths.items()}
    merged["history_summary_path"] = str(synthesis_paths(project_dir)["history_summary"])

    prompt_path = RENDERERS_DIR / f"{merged['renderer_type']}.md"
    if not prompt_path.exists():
        suggest_renderer_template(project_dir, merged, ACTIVE_LLM)
        raise RuntimeError(
            f"Renderer template missing for '{merged['renderer_type']}'. "
            f"A suggested template was written to {prompt_path}. Review it, then rerun."
        )

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
    return [str(path) for path in cached_paths] == [str(path) for path in context.get("artifact_paths", [])]


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
    prompt_body = load_prompt(PROMPTS_DIR / "extract_ledger.md")
    prompt = "\n\n".join(
        [
            prompt_body,
            f"Project name: {context['project_name']}",
            f"Project type: {context['project_type']}",
            "Artifacts:",
            artifact_bundle,
        ]
    )
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
    ledger["_meta"] = {
        "project_name": context["project_name"],
        "project_type": context["project_type"],
        "artifact_paths": context["artifact_paths"],
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


def derive_project_domain(project_name: str) -> str:
    # Cheap heuristic: collapse a project name to a coarse domain bucket so the
    # provenance counter can compute "distinct domains" for Confirmed promotion.
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
        domain = derive_project_domain(project_name)
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
        domain = derive_project_domain(project_name)
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


def render_artifact(ledger: Dict[str, Any], brief: Dict[str, Any], context: Dict[str, Any]) -> str:
    if ACTIVE_LLM is None:
        raise RuntimeError("ACTIVE_LLM is not configured.")
    project_dir = Path(context["project_dir"])
    renderer_prompt = load_prompt(RENDERERS_DIR / f"{context['renderer_type']}.md")
    # Provide a stable "today" anchor to prevent the renderer from fabricating dates.
    run_date = time.strftime("%B %d, %Y")
    dbg(f"Render artifact: renderer_type={context['renderer_type']} run_date={run_date}")
    history_summary = load_history_summary_for_context(context) or {}
    aggregated_corpus = context.get("aggregated_corpus")
    prompt_parts = [
        renderer_prompt,
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
    ]
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
    prompt = "\n\n".join(
        [
            load_prompt(prompt_path),
            f"Audience: {context['audience']}",
            f"Tone: {context['tone']}",
            f"Project type: {context['project_type']}",
            "Planning brief JSON:",
            json.dumps(brief, indent=2, sort_keys=True),
            "Insight ledger JSON:",
            json.dumps(ledger, indent=2, sort_keys=True),
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
    qa_parts = [
        load_prompt(PROMPTS_DIR / "qa_artifact.md"),
        f"Renderer type: {context['renderer_type']}",
        "Planning brief JSON:",
        json.dumps(brief, indent=2, sort_keys=True),
        "Insight ledger JSON:",
        json.dumps(ledger, indent=2, sort_keys=True),
        "History summary JSON:",
        json.dumps(history_summary, indent=2, sort_keys=True),
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
    }

    if qa.get("faithful") and int(qa.get("score", 0)) >= ACTIVE_QA_THRESHOLD:
        write_text(final_path, report)
        qa["_meta"]["report_written"] = True
    else:
        qa["_meta"]["report_written"] = False

    write_json(qa_output_path, qa)
    return qa


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


def run_multi_project_field_manual(project_names: List[str], args: argparse.Namespace) -> int:
    """Multi-project aggregation path for the field_manual renderer.

    Resolves each project, ensures each has a history_summary.json (running
    summarize_history if not), aggregates the tagged failures into a unioned
    payload with a provenance table, then runs render_artifact + qa_artifact
    once with the aggregated payload attached to the context.

    Output is written to research_areas/private/distribution/field_manual_auto.md
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

    qa = qa_artifact(ledger, brief, report, context)

    distribution_path = REPO_ROOT / "research_areas" / "private" / "distribution" / "field_manual_auto.md"
    if qa.get("faithful") and int(qa.get("score", 0)) >= ACTIVE_QA_THRESHOLD:
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

    qa = qa_artifact(ledger, brief, report, context)
    final_path = Path(context["output_paths"]["final_report"])
    if qa.get("faithful") and int(qa.get("score", 0)) >= ACTIVE_QA_THRESHOLD:
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

    'hormuz_oil_shock_2026' -> title='Hormuz Oil Shock 2026', stem='hormuz-oil-shock-2026'
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
    args = parser.parse_args()

    global ACTIVE_LLM, ACTIVE_QA_LLM, ACTIVE_QA_THRESHOLD
    global DEBUG
    DEBUG = bool(args.debug)
    ACTIVE_LLM = LLMClient(args.model)
    ACTIVE_QA_LLM = LLMClient(args.qa_model or args.model)
    ACTIVE_QA_THRESHOLD = args.qa_threshold
    dbg(f"Models: model={args.model} qa_model={args.qa_model or args.model} qa_threshold={args.qa_threshold}")

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
            memo_qa = qa_artifact(ledger, memo_brief, memo_report, memo_context)

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
            appendix_qa = qa_artifact(ledger, appendix_brief, appendix_report, appendix_context)

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
        qa = qa_artifact(ledger, brief, report, context)

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
