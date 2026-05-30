"""Manifest-driven runner for Research Director phase scripts.

The runner turns ad hoc `phase5*.py` scripts into auditable experiment packets:

* phase definition lives in a JSON registry before execution
* command is deterministic and repo-relative
* stdout/stderr are captured under `phase_runs/<phase>/<timestamp>/`
* expected artifacts are checked and hashed
* a closure-ready E-row draft is emitted

This is intentionally not part of `autoresearch_loop`. The ZTARE loop may
consume closed phase artifacts as substrates, but it should not freely execute
new science scripts without a Research Director manifest boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class PhaseSpec:
    phase_id: str
    hypothesis_id: str
    description: str
    command: list[str]
    cwd: Path
    expected_artifacts: list[Path]
    classifier_artifact: Path | None
    classifier_key: str | None
    closure_scope: str
    so_what: str


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_repo_path(raw: str, *, base: Path = REPO_ROOT) -> Path:
    path = (base / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
    try:
        path.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError(f"path escapes repo root: {raw}") from exc
    return path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_registry(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "phases" not in data or not isinstance(data["phases"], dict):
        raise ValueError("registry must contain object key `phases`")
    return data


def _phase_from_registry(registry: dict[str, Any], phase_id: str) -> PhaseSpec:
    phases = registry["phases"]
    if phase_id not in phases:
        raise KeyError(f"phase not found: {phase_id}")
    raw = phases[phase_id]
    command = raw.get("command")
    if not isinstance(command, list) or not command:
        raise ValueError(f"{phase_id}: command must be a non-empty list")
    if any(not isinstance(item, str) for item in command):
        raise ValueError(f"{phase_id}: command entries must be strings")

    cwd = _safe_repo_path(raw.get("cwd", "."))
    artifacts = [_safe_repo_path(p) for p in raw.get("expected_artifacts", [])]
    classifier = raw.get("classifier_artifact")
    return PhaseSpec(
        phase_id=phase_id,
        hypothesis_id=str(raw.get("hypothesis_id", "")),
        description=str(raw.get("description", "")),
        command=command,
        cwd=cwd,
        expected_artifacts=artifacts,
        classifier_artifact=_safe_repo_path(classifier) if classifier else None,
        classifier_key=raw.get("classifier_key"),
        closure_scope=str(raw.get("closure_scope", "")),
        so_what=str(raw.get("so_what", "")),
    )


def _resolve_command(command: list[str]) -> list[str]:
    """Resolve repo-relative script paths while preserving program names."""
    resolved: list[str] = []
    for idx, part in enumerate(command):
        if idx == 0:
            if part == "{python}":
                resolved.append(sys.executable)
            else:
                resolved.append(part)
            continue
        if part.endswith(".py") and not part.startswith("-"):
            resolved.append(str(_safe_repo_path(part)))
        else:
            resolved.append(part)
    return resolved


def validate_phase(spec: PhaseSpec) -> list[str]:
    errors: list[str] = []
    if not spec.hypothesis_id:
        errors.append("missing hypothesis_id")
    if not spec.description:
        errors.append("missing description")
    if not spec.cwd.exists():
        errors.append(f"cwd does not exist: {spec.cwd}")
    cmd = _resolve_command(spec.command)
    if len(cmd) >= 2 and cmd[1].endswith(".py") and not Path(cmd[1]).exists():
        errors.append(f"script does not exist: {cmd[1]}")
    for artifact in spec.expected_artifacts:
        parent = artifact.parent
        if not parent.exists():
            errors.append(f"artifact parent does not exist: {parent}")
    if spec.classifier_artifact and spec.classifier_artifact not in spec.expected_artifacts:
        errors.append("classifier_artifact must also appear in expected_artifacts")
    return errors


def _read_classifier(spec: PhaseSpec) -> Any:
    if not spec.classifier_artifact or not spec.classifier_artifact.exists():
        return None
    try:
        data = json.loads(spec.classifier_artifact.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"error": "classifier_artifact_not_json"}
    if not spec.classifier_key:
        return data
    cur: Any = data
    for part in spec.classifier_key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return {"error": "classifier_key_missing", "key": spec.classifier_key}
    return cur


def _artifact_status(paths: list[Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in paths:
        if path.exists():
            out.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "exists": True,
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
        else:
            out.append({"path": str(path.relative_to(REPO_ROOT)), "exists": False})
    return out


def _write_closure_draft(spec: PhaseSpec, run_dir: Path, telemetry: dict[str, Any]) -> Path:
    classifier = telemetry.get("classifier")
    status = "closed" if telemetry["returncode"] == 0 else "failed"
    missing = [a["path"] for a in telemetry["artifacts"] if not a["exists"]]
    lines = [
        f"# Closure Draft — {spec.phase_id}",
        "",
        "Paste or adapt this into `research_areas/EXPERIMENT_TRACK_RECORD.md` after review.",
        "",
        "```markdown",
        f"- **ID:** E-{spec.phase_id.upper()}",
        f"- **Recorded:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"- **Window:** {spec.description}",
        f"- **Hypothesis:** `{spec.hypothesis_id}`",
        f"- **Exit reason:** `{status}` (`returncode={telemetry['returncode']}`)",
        f"- **Result classification:** `{classifier}`",
        f"- **What changed:** {spec.closure_scope or 'TBD after artifact review.'}",
        f"- **So what:** {spec.so_what or 'TBD after artifact review.'}",
        f"- **Source pointers:** `{run_dir.relative_to(REPO_ROOT)}`, "
        + ", ".join(f"`{a['path']}`" for a in telemetry["artifacts"] if a["exists"]),
        "```",
        "",
    ]
    if missing:
        lines.extend(["Missing expected artifacts:", *[f"- `{m}`" for m in missing], ""])
    out = run_dir / "closure_draft.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def run_phase(registry_path: Path, phase_id: str, *, dry_run: bool = False) -> dict[str, Any]:
    registry = _load_registry(registry_path)
    spec = _phase_from_registry(registry, phase_id)
    errors = validate_phase(spec)
    command = _resolve_command(spec.command)
    if errors:
        return {"ok": False, "phase_id": phase_id, "errors": errors, "command": command}
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "phase_id": phase_id,
            "command": command,
            "cwd": str(spec.cwd.relative_to(REPO_ROOT)),
            "expected_artifacts": [str(p.relative_to(REPO_ROOT)) for p in spec.expected_artifacts],
        }

    runs_root = (registry_path.parent / "phase_runs" / phase_id / _utc_stamp()).resolve()
    runs_root.mkdir(parents=True, exist_ok=True)
    stdout_path = runs_root / "stdout.txt"
    stderr_path = runs_root / "stderr.txt"
    start = time.time()
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.run(
        command,
        cwd=spec.cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    telemetry = {
        "phase_id": phase_id,
        "hypothesis_id": spec.hypothesis_id,
        "description": spec.description,
        "command": command,
        "cwd": str(spec.cwd.relative_to(REPO_ROOT)),
        "returncode": proc.returncode,
        "wall_time_s": round(time.time() - start, 3),
        "stdout_path": str(stdout_path.relative_to(REPO_ROOT)),
        "stderr_path": str(stderr_path.relative_to(REPO_ROOT)),
        "artifacts": _artifact_status(spec.expected_artifacts),
        "classifier": _read_classifier(spec),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    telemetry_path = runs_root / "telemetry.json"
    telemetry_path.write_text(json.dumps(telemetry, indent=2) + "\n", encoding="utf-8")
    closure_path = _write_closure_draft(spec, runs_root, telemetry)
    event_path = registry_path.parent / "phase_run_events.jsonl"
    with event_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"phase_id": phase_id, "run_dir": str(runs_root.relative_to(REPO_ROOT)), **telemetry}) + "\n")
    return {
        "ok": proc.returncode == 0,
        "phase_id": phase_id,
        "run_dir": str(runs_root.relative_to(REPO_ROOT)),
        "telemetry": str(telemetry_path.relative_to(REPO_ROOT)),
        "closure_draft": str(closure_path.relative_to(REPO_ROOT)),
        "returncode": proc.returncode,
        "classifier": telemetry["classifier"],
    }


def cmd_list(args: argparse.Namespace) -> int:
    registry = _load_registry(Path(args.registry))
    rows = []
    for phase_id, raw in sorted(registry["phases"].items()):
        rows.append(
            {
                "phase_id": phase_id,
                "hypothesis_id": raw.get("hypothesis_id", ""),
                "description": raw.get("description", ""),
            }
        )
    print(json.dumps(rows, indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    registry = _load_registry(Path(args.registry))
    phase_ids = [args.phase] if args.phase else sorted(registry["phases"])
    out = {}
    any_errors = False
    for phase_id in phase_ids:
        spec = _phase_from_registry(registry, phase_id)
        errors = validate_phase(spec)
        out[phase_id] = {"ok": not errors, "errors": errors, "command": _resolve_command(spec.command)}
        any_errors = any_errors or bool(errors)
    print(json.dumps(out, indent=2))
    return 1 if any_errors else 0


def cmd_run(args: argparse.Namespace) -> int:
    result = run_phase(Path(args.registry), args.phase, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Research Director phase runner")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List registered phases")
    p_list.add_argument("--registry", required=True)
    p_list.set_defaults(func=cmd_list)

    p_validate = sub.add_parser("validate", help="Validate phase registry entries")
    p_validate.add_argument("--registry", required=True)
    p_validate.add_argument("--phase")
    p_validate.set_defaults(func=cmd_validate)

    p_run = sub.add_parser("run", help="Run one registered phase")
    p_run.add_argument("--registry", required=True)
    p_run.add_argument("--phase", required=True)
    p_run.add_argument("--dry-run", action="store_true")
    p_run.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
