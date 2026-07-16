"""Project Workbench settings shared by CLI and D4."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from ztare.common.llm_runtime import MODEL_FAMILY_CHOICES
from ztare.common.paths import REPO_ROOT


WORKBENCH_ENV_PATH = ".env"
WORKBENCH_SETTINGS_SCHEMA = "ztare-forensic-workbench-settings-v1"


def model_option(value: str, label: str | None = None) -> dict[str, str]:
    return {"value": value, "label": label or value}


WORKBENCH_MODEL_OPTIONS = [
    model_option("", "Runtime default"),
    *[model_option(choice) for choice in MODEL_FAMILY_CHOICES],
]

WORKBENCH_SETTINGS_FIELDS = [
    {
        "key": "ZTARE_WORKBENCH_MODEL",
        "label": "Evidence model",
        "default": "",
        "kind": "select",
        "options": WORKBENCH_MODEL_OPTIONS,
        "help": "Optional model label passed as MODEL for evidence preparation and evidence fetch auto-compile. Leave blank to use the command/runtime default.",
        "affects": ["Prepare evidence", "Fetch evidence auto-compile"],
    },
    {
        "key": "ZTARE_EVIDENCE_SEARCH_BACKEND",
        "label": "Evidence search backend",
        "default": "auto",
        "kind": "select",
        "options": ["auto", "openai", "anthropic"],
        "help": "Web-search backend used by evidence fetch. auto follows the selected model family.",
        "affects": ["Fetch evidence"],
    },
    {
        "key": "ZTARE_WORKBENCH_REPORT_MODEL",
        "label": "Report model",
        "default": "",
        "kind": "select",
        "options": WORKBENCH_MODEL_OPTIONS,
        "help": "Model for full report synthesis AND the advisory trio — eigenquestion, isomorphism (“What is this like?”), and on-demand forecasts. Claude/GPT route via the subscription CLI; gemini/deepseek/kimi/grok via API. Blank = evidence model, then runtime default.",
        "affects": ["Report inputs"],
    },
    {
        "key": "ZTARE_WORKBENCH_FETCH_SEVERITY",
        "label": "Fetch severity",
        "default": "degrading",
        "kind": "select",
        "options": ["degrading", "enriching", "blocking"],
        "help": "Evidence-gap severity the workbench fetch action targets first.",
        "affects": ["Fetch evidence"],
    },
    {
        "key": "ZTARE_WORKBENCH_MAX_FETCHES",
        "label": "Max fetches",
        "default": "3",
        "kind": "number",
        "help": "Maximum active evidence gaps fetched in one confirmed action.",
        "affects": ["Fetch evidence"],
    },
    {
        "key": "ZTARE_WORKBENCH_AUTO_COMPILE",
        "label": "Auto-compile after fetch",
        "default": "1",
        "kind": "boolean",
        "help": "When enabled, evidence fetch runs source check, workspace update, and evidence compile after new files are collected.",
        "affects": ["Fetch evidence", "Prepare files"],
    },
    {
        "key": "ZTARE_WORKBENCH_RUN_MUTATOR_MODEL",
        "label": "Run draft model",
        "default": "",
        "kind": "select",
        "options": WORKBENCH_MODEL_OPTIONS,
        "help": "Optional model used to draft candidate project updates during a run. Leave blank to use the run default.",
        "affects": ["Start run"],
    },
    {
        "key": "ZTARE_WORKBENCH_RUN_JUDGE_MODEL",
        "label": "Run review model",
        "default": "",
        "kind": "select",
        "options": WORKBENCH_MODEL_OPTIONS,
        "help": "Optional model used to review and score candidate updates during a run. Leave blank to use the run default.",
        "affects": ["Start run", "Results"],
    },
    {
        "key": "ZTARE_WORKBENCH_RUN_INVERTER_MODEL",
        "label": "Run stress-test model",
        "default": "",
        "kind": "select",
        "options": WORKBENCH_MODEL_OPTIONS,
        "help": "Optional model used to look for objections, missing evidence, and ways the thesis could fail.",
        "affects": ["Start run", "Things to review"],
    },
    {
        "key": "ZTARE_WORKBENCH_RUN_COMMITTEE_MODEL",
        "label": "Committee panel model",
        "default": "",
        "kind": "select",
        "options": WORKBENCH_MODEL_OPTIONS,
        "help": "Optional model that generates the 3-reviewer panel when scoring with a committee. Leave blank to use the run default.",
        "affects": ["Start run"],
    },
    {
        "key": "ZTARE_WORKBENCH_RUN_TRANSPORT",
        "label": "Run engine",
        "default": "api",
        "kind": "select",
        "options": ["api", "subscription"],
        "help": (
            "Which engine a run uses for its model calls. 'api' calls the model provider's API directly "
            "(needs an API key). 'subscription' routes the run's draft, review, committee, and stress-test "
            "calls through your local Codex/Claude subscription CLI instead. It's one or the other per run, not both."
        ),
        "affects": ["Start run"],
    },
    {
        "key": "ZTARE_WORKBENCH_RUN_JUDGING",
        "label": "Who scores the run",
        "default": "single",
        "kind": "select",
        "options": ["single", "committee"],
        "help": (
            "'single' scores each iteration with one judge. 'committee' generates a 3-reviewer panel and "
            "scores by their combined view — harder to game, slower and more expensive."
        ),
        "affects": ["Start run", "Results"],
    },
    {
        "key": "ZTARE_WORKBENCH_RUN_RUBRIC_MODE",
        "label": "Rubric over the run",
        "default": "fixed",
        "kind": "select",
        "options": ["fixed", "rotating"],
        "help": (
            "'fixed' scores every iteration against the same scoring guide. 'rotating' lets the rubric "
            "auto-evolve once a claim scores well, so a high score has to survive a tougher guide — the "
            "anti-Goodhart check this project is built around."
        ),
        "affects": ["Start run", "Results"],
    },
    {
        "key": "ZTARE_WORKBENCH_RUN_CROSS_FAMILY",
        "label": "Mixed-model committee",
        "default": "0",
        "kind": "boolean",
        "help": (
            "When the committee is on, require its three reviewers to span different model families, so the "
            "panel isn't three views from the same model. Ignored when scoring with a single judge."
        ),
        "affects": ["Start run"],
    },
    {
        "key": "ZTARE_WORKBENCH_RUN_ITERS",
        "label": "Iterations",
        "default": "",
        "kind": "number",
        "help": "How many improve-and-score rounds the run does. Leave blank to use the project's default.",
        "affects": ["Start run"],
    },
    {
        "key": "ZTARE_WORKBENCH_AUTORESEARCH_LLM_TIMEOUT",
        "label": "Run timeout seconds",
        "default": "600",
        "kind": "number",
        "help": "Per-call timeout passed to bounded project runs.",
        "affects": ["Start run"],
    },
    {
        "key": "ZTARE_WORKBENCH_AUTORESEARCH_LLM_RETRIES",
        "label": "Run retries",
        "default": "3",
        "kind": "number",
        "help": "Retry count passed to bounded project runs.",
        "affects": ["Start run"],
    },
    {
        "key": "ZTARE_WORKBENCH_EVIDENCE_LLM_TIMEOUT",
        "label": "Evidence timeout seconds",
        "default": "300",
        "kind": "number",
        "help": "Timeout passed to evidence workspace update and evidence compile model calls.",
        "affects": ["Prepare evidence", "Fetch evidence auto-compile"],
    },
    {
        "key": "ZTARE_WORKBENCH_EVIDENCE_LLM_RETRIES",
        "label": "Evidence retries",
        "default": "4",
        "kind": "number",
        "help": "Retry count passed to evidence workspace update and evidence compile model calls.",
        "affects": ["Prepare evidence", "Fetch evidence auto-compile"],
    },
    {
        "key": "ZTARE_WORKBENCH_MODEL_FALLBACK",
        "label": "Allow model fallback",
        "default": "0",
        "kind": "boolean",
        "help": "0 keeps evidence and run calls on the configured model family; 1 allows the fallback chain when the model runtime permits it.",
        "affects": ["Prepare evidence", "Fetch evidence", "Start run"],
    },
]

# Per-project run config: the subset of settings a researcher can override for a single project,
# persisted in the project folder (web-only) instead of the global .env. These are exactly the
# fields that shape a run, declared once by their `affects` tag so this list never drifts.
PROJECT_RUN_CONFIG_KEYS = [
    str(field["key"]) for field in WORKBENCH_SETTINGS_FIELDS if "Start run" in (field.get("affects") or [])
]

PROJECT_RUN_CONFIG_FILENAME = "workbench_run_config.json"


def project_run_config_path(project_root: Path) -> Path:
    return Path(project_root) / PROJECT_RUN_CONFIG_FILENAME


def read_project_run_overrides(project_root: Path, *, storage: Any = None) -> dict[str, str]:
    """Return the normalized run-config overrides saved for one project (empty if none)."""
    path = project_run_config_path(project_root)
    if not path.exists():
        return {}
    try:
        raw = json.loads(_read_text(path, storage))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    values = raw.get("values") if isinstance(raw.get("values"), dict) else raw
    overrides: dict[str, str] = {}
    for key in PROJECT_RUN_CONFIG_KEYS:
        if key in values:
            try:
                overrides[key] = normalize_setting_value(key, values[key])
            except ValueError:
                continue
    return overrides


def save_project_run_overrides(
    project_root: Path,
    raw_values: Any,
    *,
    storage: Any = None,
) -> dict[str, str]:
    """Replace this project's run overrides with exactly the run-config keys submitted.

    The caller (workbench run-config panel) owns the override/inherit decision per field: it sends a
    key only when the project should override it. Omitting a key clears that override so the project
    follows the global setting again. The whole file is rewritten each save.
    """
    if not isinstance(raw_values, dict):
        raise ValueError("run config request must include a values object")
    overrides: dict[str, str] = {}
    for key in PROJECT_RUN_CONFIG_KEYS:
        if key in raw_values:
            overrides[key] = normalize_setting_value(key, raw_values[key])
    path = project_run_config_path(project_root)
    payload = {
        "schema": "ztare-forensic-workbench-run-config-v1",
        "values": overrides,
    }
    _write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n", storage)
    return overrides


WORKBENCH_SECRET_KEYS = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "KIMI_API_KEY",
    "MOONSHOT_API_KEY",
    "XAI_API_KEY",
    "GROK_API_KEY",
]


def env_file_path(*, root: Path = REPO_ROOT) -> Path:
    return root.resolve() / WORKBENCH_ENV_PATH


def parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return key, value


def _read_text(path: Path, storage: Any = None) -> str:
    if storage is not None and hasattr(storage, "read_text"):
        return storage.read_text(path)
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str, storage: Any = None) -> None:
    if storage is not None and hasattr(storage, "write_text"):
        storage.write_text(path, text)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_env_file_values(*, root: Path = REPO_ROOT, storage: Any = None) -> dict[str, str]:
    path = env_file_path(root=root)
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    try:
        for line in _read_text(path, storage).splitlines():
            parsed = parse_env_line(line)
            if parsed:
                values[parsed[0]] = parsed[1]
    except OSError:
        return {}
    return values


def setting_default(key: str) -> str:
    for field in WORKBENCH_SETTINGS_FIELDS:
        if field["key"] == key:
            return str(field["default"])
    return ""


def normalize_setting_value(key: str, value: Any) -> str:
    raw = str(value if value is not None else "").strip()
    default = setting_default(key)
    if not raw:
        return default
    field = next((row for row in WORKBENCH_SETTINGS_FIELDS if row["key"] == key), None)
    if field is None:
        raise ValueError(f"unknown workbench setting: {key}")
    if field.get("kind") == "select":
        options = {
            str(option.get("value", "")) if isinstance(option, dict) else str(option)
            for option in field.get("options") or []
        }
        if raw not in options:
            raise ValueError(f"{key} must be one of: {', '.join(sorted(options))}")
        return raw
    if field.get("kind") == "boolean":
        lowered = raw.lower()
        if lowered in {"1", "true", "yes", "on"}:
            return "1"
        if lowered in {"0", "false", "no", "off"}:
            return "0"
        raise ValueError(f"{key} must be 0 or 1")
    if field.get("kind") == "number":
        try:
            number = int(raw)
        except ValueError as exc:
            raise ValueError(f"{key} must be a whole number") from exc
        if number < 0:
            raise ValueError(f"{key} must be non-negative")
        if key == "ZTARE_WORKBENCH_MAX_FETCHES" and number < 1:
            raise ValueError(f"{key} must be at least 1")
        return str(number)
    if not re.fullmatch(r"[A-Za-z0-9_.:+/-]+", raw):
        raise ValueError(f"{key} contains unsupported characters")
    return raw


def normalize_provider_key_value(key: str, value: Any) -> str:
    if key not in WORKBENCH_SECRET_KEYS:
        raise ValueError(f"unknown provider key: {key}")
    raw = str(value if value is not None else "").strip()
    if not raw:
        return ""
    if "\n" in raw or "\r" in raw or "\x00" in raw:
        raise ValueError(f"{key} cannot contain line breaks")
    return raw


def workbench_settings_values(
    *,
    root: Path = REPO_ROOT,
    storage: Any = None,
    environ: dict[str, str] | None = None,
) -> dict[str, str]:
    env = os.environ if environ is None else environ
    env_values = read_env_file_values(root=root, storage=storage)
    values: dict[str, str] = {}
    for field in WORKBENCH_SETTINGS_FIELDS:
        key = str(field["key"])
        raw = env_values.get(key, env.get(key, field["default"]))
        values[key] = normalize_setting_value(key, raw)
    return values


def setting_was_explicit(
    key: str,
    *,
    root: Path = REPO_ROOT,
    storage: Any = None,
    environ: dict[str, str] | None = None,
) -> bool:
    env = os.environ if environ is None else environ
    return key in read_env_file_values(root=root, storage=storage) or key in env


def load_workbench_env(*, root: Path = REPO_ROOT, storage: Any = None) -> dict[str, str]:
    env = os.environ.copy()
    env.update(read_env_file_values(root=root, storage=storage))
    # Run transport is the single door for model routing. The autoresearch run flips it via
    # --agent-* flags; report synthesis has no such flag, so mirror 'subscription' onto the
    # synthesis dispatch door here. API (default) leaves it unset → direct provider calls.
    if env.get("ZTARE_WORKBENCH_RUN_TRANSPORT") == "subscription" and not env.get("ZTARE_AGENT_DISPATCH_SYNTHESIS"):
        env["ZTARE_AGENT_DISPATCH_SYNTHESIS"] = "agent"
    return env


def quote_env_value(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_.:+/-]*", value):
        return value
    return json.dumps(value)


def settings_write_boundary(*, storage: Any = None, saved: bool = False) -> dict[str, Any]:
    metadata = storage.metadata() if storage is not None and hasattr(storage, "metadata") else {
        "schema": "ztare-forensic-workbench-storage-v1",
        "backend": "file",
        "root": ".",
        "detachable": True,
        "write_mode": "local_filesystem",
    }
    return {
        "schema": "ztare-forensic-workbench-write-boundary-v1",
        "storage": metadata,
        "storage_backend": metadata.get("backend", "file"),
        "storage_write_mode": metadata.get("write_mode", "local_filesystem"),
        "detachable_storage": True,
        "writes_project_files": False,
        "writes_repo_files": True,
        "browser_writes": False,
        "write_paths": [WORKBENCH_ENV_PATH],
        "receipt_path": "",
        "latest_path": "",
        "no_change_boundary": (
            "Preview, refresh, validation failure, and failed saves write no files. "
            "Accepted settings saves can change only the local .env settings file."
            if saved
            else "Inspecting settings and checking provider-key presence write no files. Saving settings can change only the local .env settings file."
        ),
        "read_only_actions": ["inspect settings"] if saved else ["inspect settings", "check provider-key presence"],
    }


def settings_payload(
    *,
    root: Path = REPO_ROOT,
    storage: Any = None,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    env = os.environ if environ is None else environ
    values = workbench_settings_values(root=root, storage=storage, environ=env)
    env_values = read_env_file_values(root=root, storage=storage)
    fields = [
        {
            **field,
            "value": values[str(field["key"])],
            "source": "env_file" if str(field["key"]) in env_values else ("process_env" if str(field["key"]) in env else "default"),
        }
        for field in WORKBENCH_SETTINGS_FIELDS
    ]
    provider_keys = [
        {
            "key": key,
            "label": key.replace("_API_KEY", "").replace("_", " ").title(),
            "present": bool(env_values.get(key) or env.get(key)),
            "source": "env_file" if key in env_values else ("process_env" if key in env else "missing"),
            "value_hidden": True,
            "help": "Provider key used by model work. The workbench never displays the secret value.",
        }
        for key in WORKBENCH_SECRET_KEYS
    ]
    path = env_file_path(root=root)
    return {
        "schema": WORKBENCH_SETTINGS_SCHEMA,
        "ok": True,
        "env_file": WORKBENCH_ENV_PATH if not path.exists() else WORKBENCH_ENV_PATH,
        "env_file_exists": path.exists(),
        "fields": fields,
        "values": values,
        "provider_keys": provider_keys,
        "write_boundary": settings_write_boundary(storage=storage),
    }


def save_settings_payload(
    raw_values: Any,
    *,
    root: Path = REPO_ROOT,
    storage: Any = None,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not isinstance(raw_values, dict):
        raise ValueError("settings request must include a values object")
    allowed_settings = {str(field["key"]) for field in WORKBENCH_SETTINGS_FIELDS}
    settings_updates = {
        key: normalize_setting_value(key, value)
        for key, value in raw_values.items()
        if key in allowed_settings
    }
    provider_updates = {
        key: normalized
        for key, value in raw_values.items()
        if key in WORKBENCH_SECRET_KEYS
        for normalized in [normalize_provider_key_value(key, value)]
        if normalized
    }
    updates = {**settings_updates, **provider_updates}
    if not updates:
        raise ValueError("no supported workbench settings were provided")
    path = env_file_path(root=root)
    existing_lines = _read_text(path, storage).splitlines() if path.exists() else []
    remaining = dict(updates)
    output_lines: list[str] = []
    for line in existing_lines:
        parsed = parse_env_line(line)
        if parsed and parsed[0] in updates:
            key = parsed[0]
            output_lines.append(f"{key}={quote_env_value(updates[key])}")
            remaining.pop(key, None)
        else:
            output_lines.append(line)
    if remaining:
        if output_lines and output_lines[-1].strip():
            output_lines.append("")
        output_lines.append("# ZTARE Project Workbench settings")
        for key in sorted(remaining):
            output_lines.append(f"{key}={quote_env_value(remaining[key])}")
    _write_text(path, "\n".join(output_lines).rstrip() + "\n", storage)
    payload = settings_payload(root=root, storage=storage, environ=environ)
    payload.update(
        {
            "saved": True,
            "updated_keys": sorted(settings_updates),
            "updated_provider_keys": sorted(provider_updates),
            "write_boundary": settings_write_boundary(storage=storage, saved=True),
        }
    )
    return payload


def parse_key_values(pairs: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"setting must be KEY=VALUE: {pair}")
        key, value = pair.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def values_from_args(args: argparse.Namespace) -> dict[str, Any]:
    values: dict[str, Any] = {}
    values_path = getattr(args, "values_path", None)
    if values_path:
        loaded = json.loads(Path(values_path).read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("settings input file must contain a JSON object")
        values.update(loaded)
    values.update(parse_key_values(getattr(args, "pairs", [])))
    return values


def project_root(root: Path, project: str) -> Path:
    slug = str(project or "").strip()
    if not slug or "/" in slug or "\\" in slug or ".." in slug:
        raise ValueError("project must be a valid slug")
    path = root.resolve() / "projects" / slug
    if not path.is_dir():
        raise FileNotFoundError(f"project does not exist: projects/{slug}")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect or save Project Workbench settings.")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    sub = parser.add_subparsers(dest="cmd", required=True)
    get = sub.add_parser("get")
    get.add_argument("--repo", type=Path, default=REPO_ROOT)
    get.add_argument("--json", action="store_true")
    save = sub.add_parser("save")
    save.add_argument("--repo", type=Path, default=REPO_ROOT)
    save.add_argument("--set", dest="pairs", action="append", default=[], metavar="KEY=VALUE")
    save.add_argument("--from", dest="values_path", type=Path, help="JSON object of setting values.")
    save.add_argument("--json", action="store_true")
    project_get = sub.add_parser("project-get")
    project_get.add_argument("--repo", type=Path, default=REPO_ROOT)
    project_get.add_argument("--project", required=True)
    project_get.add_argument("--json", action="store_true")
    project_save = sub.add_parser("project-save")
    project_save.add_argument("--repo", type=Path, default=REPO_ROOT)
    project_save.add_argument("--project", required=True)
    project_save.add_argument("--set", dest="pairs", action="append", default=[], metavar="KEY=VALUE")
    project_save.add_argument("--from", dest="values_path", type=Path, help="JSON object of run-setting overrides.")
    project_save.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "get":
            payload = settings_payload(root=args.repo)
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(f"Settings file: {payload['env_file']} ({'exists' if payload['env_file_exists'] else 'not created yet'})")
            return 0
        if args.cmd == "project-get":
            root = project_root(args.repo, args.project)
            payload = {
                "schema": "ztare-forensic-workbench-run-config-v1",
                "ok": True,
                "project": args.project,
                "overrides": read_project_run_overrides(root),
                "config_path": project_run_config_path(root).resolve().relative_to(args.repo.resolve()).as_posix(),
            }
        elif args.cmd == "project-save":
            root = project_root(args.repo, args.project)
            overrides = save_project_run_overrides(root, values_from_args(args))
            payload = {
                "schema": "ztare-forensic-workbench-run-config-v1",
                "ok": True,
                "saved": True,
                "project": args.project,
                "overrides": overrides,
                "updated_keys": sorted(overrides),
                "config_path": project_run_config_path(root).resolve().relative_to(args.repo.resolve()).as_posix(),
            }
        else:
            payload = save_settings_payload(values_from_args(args), root=args.repo)
    except Exception as exc:  # noqa: BLE001 - concise CLI failure.
        print(f"ztare forensic-workbench settings: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if args.cmd == "project-get":
            print(f"Project run settings: {payload['config_path']}")
        elif args.cmd == "project-save":
            print(f"Saved project run settings: {payload['config_path']}")
        else:
            print(f"Saved settings: {payload['write_boundary']['write_paths'][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
