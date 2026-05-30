"""Run the meta-cold-shot frontier script scaffold.

This is the execution layer around ``frontier_script_scaffold.py``:

1. assemble a bounded artifact packet from existing repo files;
2. call one LLM through ``LLMRuntime`` with workspace-local caching;
3. parse/validate the strict scaffold JSON;
4. write a scaffold artifact for Codex/operator review.

It intentionally does not write the proposed Python source and does not run the
proposed command. The output is an admissibility object, not execution.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from src.ztare.common.llm_cache import LLMCallCache
from src.ztare.orchestrator.frontier_script_scaffold import (
    FrontierScriptScaffold,
    build_frontier_script_scaffold_prompt,
    parse_frontier_script_scaffold_json,
)


DEFAULT_SCRIPT_PATTERNS = (
    "workspace/run_cold_shot_*.py",
    "workspace/report_*.py",
    "raw/**/run_cold_shot_*.py",
    "raw/**/report_*.py",
)


@dataclass(frozen=True)
class ArtifactPacket:
    project_dir: Path
    task: str
    allowed_roots: list[str]
    existing_scripts: list[str]
    context: str
    artifact_manifest: list[str]

    def to_prompt_context(self) -> str:
        return "\n\n".join(
            part
            for part in [
                f"Project: {self.project_dir}",
                "Artifact manifest:\n" + json.dumps(self.artifact_manifest, indent=2),
                self.context,
            ]
            if part.strip()
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "project_dir": str(self.project_dir),
            "task": self.task,
            "allowed_roots": self.allowed_roots,
            "existing_scripts": self.existing_scripts,
            "artifact_manifest": self.artifact_manifest,
            "context_chars": len(self.context),
        }


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _is_allowed_artifact(path: Path, *, repo_root: Path, allowed_roots: list[str]) -> bool:
    rel = _relative(path.resolve(), repo_root.resolve())
    allowed = [root.strip("/ ") for root in allowed_roots if root.strip("/ ")]
    if not allowed:
        return False
    return any(rel == root or rel.startswith(root + "/") for root in allowed)


def _read_truncated(path: Path, *, max_chars: int) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"### {path}\n<read_error {exc!r}>"
    truncated = text[:max_chars]
    suffix = "" if len(text) <= max_chars else f"\n\n<truncated {len(text) - max_chars} chars>"
    return f"### {path}\n{truncated}{suffix}"


def discover_existing_scripts(
    project_dir: Path,
    *,
    repo_root: Path,
    allowed_roots: list[str],
    extra: list[str] | None = None,
) -> list[str]:
    found: set[str] = set()
    for pattern in DEFAULT_SCRIPT_PATTERNS:
        for match in project_dir.glob(pattern):
            if match.is_file() and match.suffix == ".py":
                found.add(_relative(match, repo_root))
    for item in extra or []:
        path = Path(item)
        if not path.is_absolute():
            path = repo_root / path
        if (
            path.exists()
            and path.is_file()
            and _is_allowed_artifact(path, repo_root=repo_root, allowed_roots=allowed_roots)
        ):
            found.add(_relative(path, repo_root))
    return sorted(found)


def build_artifact_packet(
    *,
    project_dir: Path,
    task: str,
    allowed_roots: list[str],
    repo_root: Path | None = None,
    context_files: list[str] | None = None,
    artifact_globs: list[str] | None = None,
    existing_scripts: list[str] | None = None,
    max_files: int = 12,
    max_chars_per_file: int = 6000,
    max_total_chars: int = 30000,
) -> ArtifactPacket:
    repo = (repo_root or Path.cwd()).resolve()
    project = project_dir.resolve()
    manifest: list[str] = []
    chunks: list[str] = []
    files: list[Path] = []
    for item in context_files or []:
        path = Path(item)
        if not path.is_absolute():
            path = repo / path
        if path.exists() and path.is_file() and _is_allowed_artifact(path, repo_root=repo, allowed_roots=allowed_roots):
            files.append(path)
    for pattern in artifact_globs or []:
        full_pattern = str((repo / pattern).resolve()) if not Path(pattern).is_absolute() else pattern
        for match in glob.glob(full_pattern, recursive=True):
            path = Path(match)
            if path.is_file() and _is_allowed_artifact(path, repo_root=repo, allowed_roots=allowed_roots):
                files.append(path)
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in files:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(path)
    for path in deduped[:max_files]:
        rel = _relative(path, repo)
        manifest.append(rel)
        chunks.append(_read_truncated(path, max_chars=max_chars_per_file))
    context = "\n\n".join(chunks)
    if len(context) > max_total_chars:
        context = context[:max_total_chars] + f"\n\n<truncated packet to {max_total_chars} chars>"
    scripts = discover_existing_scripts(
        project,
        repo_root=repo,
        allowed_roots=allowed_roots,
        extra=existing_scripts,
    )
    return ArtifactPacket(
        project_dir=project,
        task=task,
        allowed_roots=allowed_roots,
        existing_scripts=scripts,
        context=context,
        artifact_manifest=manifest,
    )


def _usage_record(response: Any | None) -> dict[str, Any]:
    if response is None:
        return {}
    usage = response.usage
    return {
        "requested_model_id": response.requested_model_id,
        "effective_model_id": response.effective_model_id,
        "model_name": response.model_name,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read_input_tokens": usage.cache_read_input_tokens,
        "thinking_tokens": usage.thinking_tokens,
        "direct_cost_usd": usage.direct_cost_usd,
    }


def run_frontier_script_meta_cold_shot(
    *,
    project_dir: Path,
    task: str,
    allowed_roots: list[str],
    model_id: str,
    repo_root: Path | None = None,
    context_files: list[str] | None = None,
    artifact_globs: list[str] | None = None,
    existing_scripts: list[str] | None = None,
    forbidden_actions: list[str] | None = None,
    max_tokens: int = 5000,
    timeout_seconds: int = 600,
    force_refresh: bool = False,
    llm_call: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    repo = (repo_root or Path.cwd()).resolve()
    project = project_dir.resolve()
    packet = build_artifact_packet(
        project_dir=project,
        task=task,
        allowed_roots=allowed_roots,
        repo_root=repo,
        context_files=context_files,
        artifact_globs=artifact_globs,
        existing_scripts=existing_scripts,
    )
    prompt = build_frontier_script_scaffold_prompt(
        context=packet.to_prompt_context(),
        task=task,
        allowed_roots=allowed_roots,
        existing_scripts=packet.existing_scripts,
        forbidden_actions=forbidden_actions or [],
    )
    cache = LLMCallCache(
        callsite="frontier_script_scaffold",
        project_dir=project,
        prompt_template_version=2,
        force_refresh_flag="frontier_script_scaffold_force_refresh",
    )
    cache_inputs = {
        "model_id": model_id,
        "task": task,
        "allowed_roots": allowed_roots,
        "existing_scripts": packet.existing_scripts,
        "artifact_manifest": packet.artifact_manifest,
        "context": packet.context,
        "forbidden_actions": forbidden_actions or [],
        "prompt_template_version": 2,
    }
    key = cache.compute_key(cache_inputs)
    rubric_data = {"frontier_script_scaffold_force_refresh": force_refresh}
    hit = cache.lookup(key, rubric_data=rubric_data)
    response: LLMTextResponse | None = None
    if hit is not None:
        raw_text = str(hit.get("raw_text", ""))
        cache_status = "hit"
        usage = hit.get("usage", {})
    else:
        if llm_call is None:
            from src.ztare.common.llm_runtime import LLMRuntime

            runtime = LLMRuntime()
            response = runtime.call_text(
                prompt,
                model_id=model_id,
                fallback_model_ids=(),
                config={"reasoning_effort": "xhigh"} if model_id.startswith("gpt-5") else None,
                max_tokens=max_tokens,
                retries=1,
                timeout_seconds=timeout_seconds,
                request_label="frontier_script_scaffold",
            )
        else:
            response = llm_call(prompt)
        raw_text = response.text
        usage = _usage_record(response)
        cache_status = "miss"
    scaffold: FrontierScriptScaffold = parse_frontier_script_scaffold_json(
        raw_text,
        allowed_roots=allowed_roots,
    )
    if hit is None:
        cache.store(
            key,
            {"raw_text": raw_text, "usage": usage},
            model_id_used=response.effective_model_id or model_id if response is not None else model_id,
        )
    generated_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
    record = {
        "schema_version": 1,
        "generated_at": generated_at,
        "cache_status": cache_status,
        "cache_key": key,
        "model_id": model_id,
        "usage": usage,
        "packet": packet.to_record(),
        "prompt_chars": len(prompt),
        "raw_text": raw_text,
        "scaffold": scaffold.to_record(),
    }
    out_dir = project / "workspace"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = generated_at.replace(":", "").replace("+", "Z").replace("-", "")
    out_path = out_dir / f"frontier_script_scaffold_{stamp}.json"
    latest_path = out_dir / "frontier_script_scaffold_latest.json"
    out_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    latest_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return {
        "record": record,
        "out_path": str(out_path),
        "latest_path": str(latest_path),
    }


def main() -> int:
    from src.ztare.common.llm_runtime import MODEL_MAP, resolve_model_id

    parser = argparse.ArgumentParser(description="Run a cached meta-cold-shot frontier script scaffold.")
    parser.add_argument("--project-dir", required=True, type=Path)
    parser.add_argument("--task", required=True)
    parser.add_argument("--model", default="gpt5.5", help="Model family alias or canonical model id.")
    parser.add_argument("--allowed-root", action="append", default=[])
    parser.add_argument("--context-file", action="append", default=[])
    parser.add_argument("--artifact-glob", action="append", default=[])
    parser.add_argument("--existing-script", action="append", default=[])
    parser.add_argument("--forbidden-action", action="append", default=[])
    parser.add_argument("--max-tokens", type=int, default=5000)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--force-refresh", action="store_true")
    args = parser.parse_args()
    model_id = resolve_model_id(args.model) if args.model in MODEL_MAP else args.model
    if args.allowed_root:
        allowed_roots = args.allowed_root
    else:
        project_path = args.project_dir if not args.project_dir.is_absolute() else args.project_dir.resolve()
        try:
            allowed_roots = [project_path.relative_to(Path.cwd().resolve()).as_posix()]
        except ValueError:
            allowed_roots = [project_path.name]
    result = run_frontier_script_meta_cold_shot(
        project_dir=args.project_dir,
        task=args.task,
        allowed_roots=allowed_roots,
        model_id=model_id,
        context_files=args.context_file,
        artifact_globs=args.artifact_glob,
        existing_scripts=args.existing_script,
        forbidden_actions=args.forbidden_action,
        max_tokens=args.max_tokens,
        timeout_seconds=args.timeout_seconds,
        force_refresh=args.force_refresh,
    )
    scaffold = result["record"]["scaffold"]
    print(f"Wrote {result['out_path']}")
    print(f"Latest {result['latest_path']}")
    print(f"cache_status={result['record']['cache_status']}")
    print(f"script_family={scaffold['script_family']}")
    print(f"code_edit_mode={scaffold['code_edit_mode']}")
    print(f"target_script_path={scaffold['target_script_path']}")
    print(f"smoke_test_command={scaffold['smoke_test_command']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
