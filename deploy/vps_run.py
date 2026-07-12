#!/usr/bin/env python3
"""Bounded VPS helper for RD/membrane operations.

This is intentionally a named-action client, not a generic remote shell.
`deploy/vps_run.sh` is kept as the stable approval-friendly entrypoint and
delegates here.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import difflib
import time
import uuid
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
LOCAL_REPO = SCRIPT_DIR.parent
VPS = os.environ.get("ZTARE_VPS_SSH")
KEY = Path(os.environ.get("ZTARE_VPS_KEY", ""))
REMOTE_REPO = os.environ.get("ZTARE_VPS_REPO", "/home/ztare/figs_activist_loop")
OWNER_DEFAULT = os.environ.get("RD_OWNER", "codex:RD")
REMOTE_LAKE = os.environ.get("ZTARE_VPS_LAKE", "lake")
FORECAST_DOMAIN_DEFAULT = os.environ.get("ZTARE_FORECAST_DOMAIN", "research_tick")
DEFAULT_REMOTE_PATH_PREFIXES = (
    "$REMOTE_REPO/venv/bin:"
    "$HOME/.elan/bin:"
    "$HOME/.local/bin:"
    "/usr/local/bin:"
    "/usr/bin:"
    "/bin"
)
SSH_CONTROL_PATH = os.environ.get(
    "ZTARE_VPS_SSH_CONTROL_PATH",
    f"/tmp/ztare-vps-{os.getuid()}-{os.getpid()}-%C",
)


USAGE = """\
Usage:
  bash deploy/vps_run.sh membrane-state <tick_id> <forecast_contract_id> [owner]
  bash deploy/vps_run.sh posttick-check [owner] [window_hours]
  bash deploy/vps_run.sh forecast-materialize [forecast_contract_id]
  bash deploy/vps_run.sh forecast-smoke
  bash deploy/vps_run.sh forecast-hash
  bash deploy/vps_run.sh forecast-consume-live <contract_id> [agent_id] [runtime]
  bash deploy/vps_run.sh forecast-init <macro|meso|micro> <contract_id> <task_type> <consumes_surfaced> <budget_minutes> <question> <objective_resolver> <success_threshold> <horizon> [owner]
  bash deploy/vps_run.sh forecast-init-micro <contract_id> <task_type> <consumes_surfaced> <budget_minutes> <question> <objective_resolver> <success_threshold> <horizon> [owner]
  bash deploy/vps_run.sh forecast-add-rd <contract_id> <p_success> <expected_minutes> <rationale> [failure_modes_json] [agent_id] [domain]
  bash deploy/vps_run.sh forecast-aggregate <contract_id>
  bash deploy/vps_run.sh forecast-decision-use <contract_id> <tick_id> <used_for> <true|false|none> <old_action|none> <new_action|none> <failure_modes_json> <notes> [owner]
  bash deploy/vps_run.sh forecast-resolve <contract_id> <true|false|void> <actual_minutes|none> <resolution_note> [realized_failure_modes_json] [externality_tags_json] [negative_externality_tags_json]
  bash deploy/vps_run.sh forecast-resolve-file <remote_json_path>
  bash deploy/vps_run.sh forecast-score <contract_id>
  bash deploy/vps_run.sh rd-brief [owner]
  bash deploy/vps_run.sh start-tick <tick_id> <forecast_contract_id> <substrate> <residual_target> <goal> [owner] [new_target_justification]
  bash deploy/vps_run.sh pretick <tick_id> <forecast_contract_id> <substrate> <residual_target> <universal_ops> <scopes> <anchor_files> <goal> [owner]
  bash deploy/vps_run.sh posttick <tick_id> <forecast_contract_id> <substrate> <goal> [owner] [artifact_path] [--decision-changed]
  bash deploy/vps_run.sh deploy-update [--dry-run]
  bash deploy/vps_run.sh toolchain-smoke
  bash deploy/vps_run.sh isabelle-smoke
  bash deploy/vps_run.sh transport-probe
  bash deploy/vps_run.sh subscription-runtime-smoke
  bash deploy/vps_run.sh codex-upgrade [version|latest]
  bash deploy/vps_run.sh sync-listed <repo-relative-file> [file...]
  bash deploy/vps_run.sh lean-check-file <allowlisted repo-relative .lean>
  bash deploy/vps_run.sh lean-build <Lake target>
  bash deploy/vps_run.sh lean-parity [--build <Lake target>] [--all-allowlisted] <allowlisted repo-relative-file> [file...]
  bash deploy/vps_run.sh leanmill-preflight <allowlisted campaign.md>
  bash deploy/vps_run.sh leanmill-source-fetch <https-url> <sha256> </tmp/leanmill_source_snapshots/file>
  bash deploy/vps_run.sh leanmill-campaign <allowlisted campaign.md> <remote-output-root> [--detach]
  bash deploy/vps_run.sh leanmill-latest <remote-output-root>
  bash deploy/vps_run.sh leanmill-agent-output <remote-attempt-dir> <blueprint_compiler|semantic_reviewer|navigator|lean_solver> <call-index> [stdout|stderr|call|result|schema|dispatch]
  bash deploy/vps_run.sh leanmill-agent-results <remote-attempt-dir> <blueprint_compiler|semantic_reviewer|navigator|lean_solver>
  bash deploy/vps_run.sh leanmill-status <remote-attempt-dir>
  bash deploy/vps_run.sh leanmill-inspect <remote-attempt-dir>
  bash deploy/vps_run.sh leanmill-verify <remote-attempt-dir> [--with-isabelle] [--with-lean] [--lean-root <remote-lean-root>]
  bash deploy/vps_run.sh leanmill-replay <remote-attempt-dir>
  bash deploy/vps_run.sh leanmill-resume <remote-attempt-dir> [--detach] [--delay-s <seconds>]
  bash deploy/vps_run.sh leanmill-continue-epoch <remote-attempt-dir>
  bash deploy/vps_run.sh leanmill-recover <remote-attempt-dir>
  bash deploy/vps_run.sh leanmill-recheck <remote-attempt-dir> --lean-root <remote-lean-root> [--timeout-s <seconds>]
  bash deploy/vps_run.sh leanmill-interpret <remote-attempt-dir> [--model <model>] [--reasoning-effort <low|medium|high|ultra>] [--retry-inconclusive] [--retry-failed]
  bash deploy/vps_run.sh leanmill-adapter-forge <remote-attempt-dir> [--model <model>] [--reasoning-effort <low|medium|high|ultra>]
  bash deploy/vps_run.sh leanmill-extend-budget <remote-attempt-dir> [--seconds <n>] [--phase <phase> --provider-calls <n> --agent-turns <n> --workbench-actions <n>] --authority-ref <ref> --reason <text>
  bash deploy/vps_run.sh leanmill-stop <remote-attempt-dir> <authority-ref>
  bash deploy/vps_run.sh leanmill-retire <remote-attempt-dir> <authority-ref> <reason>
  bash deploy/vps_run.sh tick-close-payload <tick_id> <forecast_contract_id> <remote_payload_dir> [owner]
  bash deploy/vps_run.sh rd-close <tick_id> <forecast_contract_id> <remote_payload_dir> [owner]
  bash deploy/vps_run.sh rd-close-local-payload <tick_id> <forecast_contract_id> <local_payload_dir> <remote_payload_dir> [owner]
"""


def die(msg: str, code: int = 2) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(code)


def usage() -> None:
    print(USAGE, file=sys.stderr)
    raise SystemExit(2)


def run(
    argv: list[str],
    *,
    capture: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        text=True,
        check=True,
        env=env,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def ssh_base() -> list[str]:
    if not VPS:
        die("ZTARE_VPS_SSH is required")
    if not KEY.is_file():
        die(f"ssh key not found: {KEY}")
    return [
        "ssh",
        "-i",
        str(KEY),
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=20",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ControlMaster=auto",
        "-o",
        "ControlPersist=300",
        "-o",
        f"ControlPath={SSH_CONTROL_PATH}",
        VPS,
    ]


def scp_base() -> list[str]:
    if not VPS:
        die("ZTARE_VPS_SSH is required")
    if not KEY.is_file():
        die(f"ssh key not found: {KEY}")
    return [
        "scp",
        "-i",
        str(KEY),
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=20",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ControlMaster=auto",
        "-o",
        "ControlPersist=300",
        "-o",
        f"ControlPath={SSH_CONTROL_PATH}",
    ]


def remote_shell(script: str, *, capture: bool = False) -> str:
    proc = run(ssh_base() + ["bash -lc " + shlex.quote(script)], capture=capture)
    return proc.stdout if capture else ""


def remote_path_entries(
    raw: str | None = None,
    *,
    remote_repo: str = REMOTE_REPO,
) -> list[str]:
    text = raw if raw is not None else os.environ.get(
        "ZTARE_VPS_REMOTE_PATH_PREFIXES",
        DEFAULT_REMOTE_PATH_PREFIXES,
    )
    entries: list[str] = []
    for raw_entry in text.split(":"):
        entry = raw_entry.strip()
        if not entry:
            continue
        entry = entry.replace("$REMOTE_REPO", remote_repo)
        if any(ch in entry for ch in "\n\r\t ;&|`'\"()<>\\"):
            die(f"unsafe remote PATH entry: {raw_entry}")
        if "$" in entry and not entry.startswith("$HOME/"):
            die(f"remote PATH entry may only use $HOME expansion: {raw_entry}")
        entries.append(entry)
    if not entries:
        die("remote PATH prefix list is empty")
    return entries


def remote_path_expr() -> str:
    parts: list[str] = []
    for entry in remote_path_entries():
        if entry.startswith("$HOME/"):
            suffix = entry.removeprefix("$HOME/")
            if not re.fullmatch(r"[A-Za-z0-9_@%+=,./-]+", suffix):
                die(f"unsafe remote $HOME PATH suffix: {entry}")
            parts.append("$HOME/" + suffix)
        else:
            parts.append(shlex.quote(entry))
    parts.append("$PATH")
    return ":".join(parts)


def remote_exports(
    *,
    owner: str | None = None,
    membrane: bool = False,
    official_store: bool = False,
) -> str:
    env = {
        "PYTHONPATH": "src",
        # Hetzner supplies the worker boundary, but its AppArmor profile blocks
        # bubblewrap UID maps.  Codex capability seals still disable shell/JS/
        # MCP as requested; only the unavailable nested process sandbox is
        # omitted by the shared subscription runtime.
        "ZTARE_CODEX_NESTED_SANDBOX": "0",
    }
    if membrane:
        env["ZTARE_MEMBRANE_OBSERVE"] = "0"
        env["ZTARE_OFFICIAL_STORE"] = "/srv/ztare_official_store"
        env["RD_OWNER"] = owner or OWNER_DEFAULT
    elif official_store:
        env["ZTARE_OFFICIAL_STORE"] = "/srv/ztare_official_store"
    return " ".join(
        [f"PATH={remote_path_expr()}"]
        + [f"{k}={shlex.quote(v)}" for k, v in env.items()]
    )


def remote_cmd(
    argv: list[str],
    *,
    cwd: str | None = REMOTE_REPO,
    owner: str | None = None,
    membrane: bool = False,
    official_store: bool = False,
    capture: bool = False,
) -> str:
    parts: list[str] = []
    if cwd:
        parts.append(f"cd {shlex.quote(cwd)}")
    parts.append(
        "export " + remote_exports(
            owner=owner,
            membrane=membrane,
            official_store=official_store,
        )
    )
    parts.append(shlex.join(argv))
    return remote_shell(" && ".join(parts), capture=capture)


def remote_chain(
    commands: list[list[str]],
    *,
    cwd: str | None = REMOTE_REPO,
    official_store: bool = False,
    capture: bool = False,
) -> str:
    parts: list[str] = []
    if cwd:
        parts.append(f"cd {shlex.quote(cwd)}")
    parts.append(
        "export " + remote_exports(official_store=official_store)
    )
    parts.extend(shlex.join(cmd) for cmd in commands)
    return remote_shell(" && ".join(parts), capture=capture)


def safe_repo_path(path: str) -> None:
    if not path:
        die("unsafe repo-relative path: empty")
    p = Path(path)
    if p.is_absolute() or path.startswith("~"):
        die(f"unsafe repo-relative path: {path}")
    if any(part in {"", ".", ".."} for part in p.parts):
        die(f"unsafe repo-relative path: {path}")
    if "\n" in path or "\x00" in path:
        die(f"unsafe repo-relative path: {path}")


def allowlist() -> set[str]:
    paths: set[str] = set()
    for line in (SCRIPT_DIR / "vps_sync_files.txt").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            paths.add(line)
    return paths


def _parse_inline_yaml_list(text: str) -> list[str]:
    body = text.strip()
    if body.startswith("["):
        body = body[1:]
    if body.endswith("]"):
        body = body[:-1]
    return [
        part.strip().strip("'\"")
        for part in body.split(",")
        if part.strip().strip("'\"")
    ]


def structural_anchor_targets(substrate: str) -> set[str]:
    registry = LOCAL_REPO / "org/structural_anchors/registry.yaml"
    if not registry.is_file():
        return set()
    try:
        import yaml  # type: ignore[import-not-found]

        data = yaml.safe_load(registry.read_text(encoding="utf-8")) or {}
        entry = data.get(substrate) or {}
        targets: set[str] = set()
        for target in entry.get("targets") or []:
            if not isinstance(target, dict):
                continue
            if target.get("id"):
                targets.add(str(target["id"]))
            for alias in target.get("aliases") or []:
                targets.add(str(alias))
        return targets
    except Exception:
        pass

    targets: set[str] = set()
    in_substrate = False
    in_targets = False
    collecting_aliases = False
    alias_buffer = ""
    for line in registry.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line and not line.startswith(" ") and not line.startswith("#"):
            key = line.split(":", 1)[0].strip()
            in_substrate = key == substrate
            in_targets = False
            collecting_aliases = False
            alias_buffer = ""
            continue
        if not in_substrate:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("targets:"):
            in_targets = True
            continue
        if not in_targets:
            continue
        if collecting_aliases:
            alias_buffer += " " + stripped
            if "]" in stripped:
                targets.update(_parse_inline_yaml_list(alias_buffer))
                collecting_aliases = False
                alias_buffer = ""
            continue
        if stripped.startswith("- id:"):
            value = stripped.split(":", 1)[1].strip().strip("'\"")
            if value:
                targets.add(value)
            continue
        if stripped.startswith("aliases:"):
            value = stripped.split(":", 1)[1].strip()
            if "[" in value and "]" not in value:
                collecting_aliases = True
                alias_buffer = value
            else:
                targets.update(_parse_inline_yaml_list(value))
    return targets


def validate_structural_residual_target(substrate: str, residual_target: str,
                                        *, allow_new: bool = False) -> None:
    targets = structural_anchor_targets(substrate)
    if not targets or residual_target in targets:
        return
    if allow_new:
        print(
            "WARN start-tick residual_target is not in structural anchor "
            f"registry for {substrate}: {residual_target}"
        )
        return
    suggestions = difflib.get_close_matches(
        residual_target, sorted(targets), n=5, cutoff=0.35
    )
    if not suggestions:
        suggestions = sorted(targets)[:5]
    raise SystemExit(
        "FAIL: residual_target is not in structural anchor registry for "
        f"{substrate}: {residual_target}. If this is a surfaced graph/source "
        "id, keep it on the forecast contract's consumes_surfaced field; "
        "start/pretick residual_target should be a registered structural "
        "target or a consciously justified new target. "
        f"Suggestions: {suggestions}"
    )


def is_sync_allowlisted(path: str) -> bool:
    return path in allowlist()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sync_one_allowlisted(path: str) -> None:
    safe_repo_path(path)
    if not is_sync_allowlisted(path):
        die(f"path is not allowlisted in deploy/vps_sync_files.txt: {path}")
    local = LOCAL_REPO / path
    if not local.is_file():
        die(f"local file missing: {path}")
    remote_dir = f"{REMOTE_REPO}/{Path(path).parent.as_posix()}"
    remote_shell(f"mkdir -p {shlex.quote(remote_dir)}")
    run(scp_base() + [str(local), f"{VPS}:{REMOTE_REPO}/{path}"])
    local_sha = sha256_file(local)
    remote_sha = remote_shell(
        f"sha256sum {shlex.quote(f'{REMOTE_REPO}/{path}')} | cut -d' ' -f1",
        capture=True,
    ).strip()
    if local_sha != remote_sha:
        die(f"hash mismatch after sync: {path} local={local_sha} remote={remote_sha}", 1)
    print(f"OK sync-listed {path} {local_sha}")


def validate_lake_target(target: str) -> None:
    if not target or re.search(r"[^A-Za-z0-9_.:-]", target):
        die(f"unsafe Lake target: {target}")


def validate_remote_tmp_or_repo(path: str, label: str) -> None:
    if not (path.startswith("/tmp/") or path.startswith(f"{REMOTE_REPO}/")):
        die(f"{label} must be under /tmp or the VPS repo: {path}")


def normalize_local_f_row_date(payload_dir: Path) -> None:
    path = payload_dir / "f_row.txt"
    text = path.read_text(encoding="utf-8")
    if re.search(r"(?m)^date:\s*`\d{4}-\d{2}-\d{2}`\s*$", text):
        return
    plain = re.search(r"(?m)^(date:\s*)(\d{4}-\d{2}-\d{2})\s*$", text)
    if not plain:
        die(
            "local close payload F-row needs a standalone date line in "
            "the form: date: `YYYY-MM-DD`"
        )
    text = re.sub(
        r"(?m)^(date:\s*)(\d{4}-\d{2}-\d{2})\s*$",
        lambda m: f"{m.group(1)}`{m.group(2)}`",
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")
    print(f"OK normalized close payload F-row date: {path}")


def _local_artifact_ref_error(ref: object, payload_dir: Path) -> str | None:
    if isinstance(ref, str):
        root_name = "payload"
        raw_path = ref
    elif isinstance(ref, dict):
        root_name = str(ref.get("root") or "payload")
        raw_path = str(ref.get("path") or "")
    else:
        return "artifact ref must be a string or object"
    text = raw_path.strip()
    if not text or "://" in text or "\n" in text or "\x00" in text:
        return "artifact path must be a local file path"
    if root_name == "store":
        return None
    if root_name == "payload":
        root = payload_dir
    elif root_name == "repo":
        root = LOCAL_REPO
    else:
        return "artifact root must be one of payload, repo, store"
    rel = Path(text)
    if rel.is_absolute():
        return "local close payload should use relative artifact paths"
    if any(part in {"", ".", ".."} for part in rel.parts):
        return "artifact path must not contain empty, '.', or '..' segments"
    if root_name == "repo" and rel.as_posix() not in allowlist():
        return (
            f"repo artifact is not in deploy/vps_sync_files.txt: {rel.as_posix()}. "
            "Use root=payload for per-tick receipts instead of syncing scratch output."
        )
    if not (root / rel).is_file():
        return f"artifact file not found: {text}"
    return None


def lint_local_close_payload(payload_dir: Path) -> None:
    normalize_local_f_row_date(payload_dir)
    declared_path = payload_dir / "declared.json"
    f_row_path = payload_dir / "f_row.txt"
    if declared_path.is_file() and f_row_path.is_file():
        try:
            declared = json.loads(declared_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            die(f"declared.json is not valid JSON: {exc}")
        try:
            sys.path.insert(0, str(LOCAL_REPO))
            from src.ztare.gates.commit_membrane_gate import evaluate
        except Exception as exc:  # pragma: no cover - import failure is fatal.
            die(f"cannot import commit_membrane_gate for local close lint: {exc}")
        verdict = evaluate(
            f_row_path.read_text(encoding="utf-8"),
            declared if isinstance(declared, dict) else {},
            transition_type="payload_preflight",
        )
        if not verdict.official:
            die("declared.json L1/L2/L3 preflight failed locally:\n"
                + verdict.as_json())
    research_done = payload_dir / "research_done.json"
    if not research_done.is_file():
        return
    try:
        raw = json.loads(research_done.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"research_done.json is not valid JSON: {exc}")
    data = raw.get("research_completion", raw) if isinstance(raw, dict) else {}
    loops = data.get("loops") if isinstance(data, dict) else None
    if not isinstance(loops, list):
        return
    for idx, loop in enumerate(loops, start=1):
        if not isinstance(loop, dict):
            continue
        for key in ("orientation_artifact", "stress_test_artifact", "verification_artifact"):
            error = _local_artifact_ref_error(loop.get(key), payload_dir)
            if error:
                die(f"research_done.json loop {idx} invalid {key}: {error}")


def remote_lean_check_file(path: str) -> None:
    safe_repo_path(path)
    if not path.startswith("ztare_proofs/") or not path.endswith(".lean"):
        die(f"lean-check-file expects repo-relative ztare_proofs/*.lean: {path}")
    if not is_sync_allowlisted(path):
        die(f"Lean file is not allowlisted in deploy/vps_sync_files.txt: {path}")
    lean_path = path.removeprefix("ztare_proofs/")
    remote_cmd([REMOTE_LAKE, "env", "lean", lean_path], cwd=f"{REMOTE_REPO}/ztare_proofs")


def action_membrane_state(args: list[str]) -> None:
    if len(args) < 2:
        usage()
    tick_id, contract_id = args[0], args[1]
    owner = args[2] if len(args) > 2 else OWNER_DEFAULT
    remote_cmd(
        [
            "python3",
            "scripts/public/control/membrane_state.py",
            "--tick-id",
            tick_id,
            "--contract-id",
            contract_id,
            "--owner",
            owner,
        ],
        owner=owner,
        membrane=True,
    )


def action_posttick_check(args: list[str]) -> None:
    owner = args[0] if args else OWNER_DEFAULT
    window = args[1] if len(args) > 1 else "24"
    remote_cmd(
        ["python3", "scripts/public/control/post_tick_check.py", "--window-hours", window],
        owner=owner,
        membrane=True,
    )


def action_forecast_materialize(args: list[str]) -> None:
    cmd = ["python3", "scripts/public/control/forecast/pool.py", "materialize-state"]
    if args and args[0]:
        cmd += ["--contract-id", args[0]]
    remote_chain(
        [["python3", "-m", "py_compile", "scripts/public/control/forecast/pool.py"], cmd],
        official_store=False,
    )


def action_forecast_smoke(_: list[str]) -> None:
    remote_chain(
        [
            ["python3", "-m", "py_compile", "scripts/public/control/forecast/pool.py"],
            ["python3", "scripts/public/control/forecast/pool.py", "smoke"],
        ]
    )


def action_forecast_hash(_: list[str]) -> None:
    remote_shell(
        " && ".join(
            [
                f"sha256sum {shlex.quote(f'{REMOTE_REPO}/scripts/public/control/forecast/pool.py')}",
                "sudo -n -u ztare_verify sha256sum /srv/ztare_gate/scripts/public/control/forecast/pool.py",
            ]
        )
    )


def action_forecast_consume_live(args: list[str]) -> None:
    if len(args) < 1:
        usage()
    contract_id = args[0]
    agent_id = args[1] if len(args) > 1 else "codex_forecaster"
    runtime = args[2] if len(args) > 2 else "codex"
    if runtime not in {"codex", "claude"}:
        die(f"runtime must be codex or claude: {runtime}")
    remote_cmd(
        [
            "python3",
            "scripts/public/control/forecast/pool.py",
            "warm-consumer-once",
            "--runtime",
            runtime,
            "--agent-id",
            agent_id,
            "--contract-id",
            contract_id,
            "--max-messages",
            "1",
            "--timeout-seconds",
            "900",
            "--mode",
            "live",
        ],
        official_store=True,
    )


def _action_forecast_init_layer(layer: str, args: list[str]) -> None:
    if layer not in {"macro", "meso", "micro"}:
        usage()
    if len(args) < 8:
        usage()
    contract_id, task_type, consumes_surfaced, budget_minutes = args[:4]
    question, resolver, threshold, horizon = args[4:8]
    owner = args[8] if len(args) > 8 else OWNER_DEFAULT
    remote_cmd(
        [
            "python3",
            "scripts/public/control/forecast/pool.py",
            "init-contract",
            "--contract-id",
            contract_id,
            "--created-by",
            owner,
            "--layer",
            layer,
            "--task-type",
            task_type,
            "--question",
            question,
            "--objective-resolver",
            resolver,
            "--success-threshold",
            threshold,
            "--horizon",
            horizon,
            "--budget-agent-minutes",
            budget_minutes,
            "--effort-prior-domain",
            task_type,
            "--value-if-success",
            "8",
            "--cost-penalty",
            "0.02",
            "--risk-penalty",
            "1.0",
            "--information-value",
            "6",
            "--void-conditions",
            "VPS membrane unavailable, resolver unavailable, or contract artifact missing.",
            "--baseline-action",
            "Execute the named RD tick with membrane-first lifecycle, pencil-first work, and bounded parity checks.",
            "--counterfactual-action",
            "Do not execute the tick; either de-anchor or choose a smaller residual if the forecasted failure modes dominate.",
            "--externality-hypotheses-json",
            "{}",
            "--emit-warm-wake",
            "--warm-forecasters",
            "codex:codex_forecaster:forecasting_agent",
            "--warm-min-forecasts",
            "1",
            "--consumes-surfaced",
            consumes_surfaced,
        ],
        official_store=True,
    )


def action_forecast_init(args: list[str]) -> None:
    if len(args) < 9:
        usage()
    layer = args[0]
    _action_forecast_init_layer(layer, args[1:])


def action_forecast_init_micro(args: list[str]) -> None:
    _action_forecast_init_layer("micro", args)


def action_forecast_add_rd(args: list[str]) -> None:
    if len(args) < 4:
        usage()
    contract_id, p_success, expected_minutes, rationale = args[:4]
    failure_modes = args[4] if len(args) > 4 else "{}"
    agent_id = args[5] if len(args) > 5 else "codex_rd"
    domain = args[6] if len(args) > 6 else FORECAST_DOMAIN_DEFAULT
    remote_cmd(
        [
            "python3",
            "scripts/public/control/forecast/pool.py",
            "add-forecast",
            "--contract-id",
            contract_id,
            "--agent-id",
            agent_id,
            "--domain",
            domain,
            "--p-success",
            p_success,
            "--expected-cost-agent-minutes",
            expected_minutes,
            "--p-regression",
            "0.10",
            "--p-dependency-issue",
            "0.30",
            "--p-needs-new-lemma",
            "0.55",
            "--failure-modes-json",
            failure_modes,
            "--forecast-externality-tags-json",
            '["failure_mode_preconditioning"]',
            "--rationale-short",
            rationale,
            "--read-only-attestation",
            "--allow-overwrite",
        ],
        official_store=True,
    )


def action_forecast_resolve_file(args: list[str]) -> None:
    if len(args) != 1:
        usage()
    validate_remote_tmp_or_repo(args[0], "resolve payload")
    remote_cmd(
        [
            "python3",
            "scripts/public/control/forecast/resolve_from_json.py",
            "--json",
            args[0],
        ],
        official_store=True,
    )


def _parse_success_token(token: str) -> tuple[bool | None, bool]:
    normalized = token.strip().lower()
    if normalized in {"true", "success", "1", "yes"}:
        return True, False
    if normalized in {"false", "failure", "0", "no"}:
        return False, False
    if normalized in {"void", "voided"}:
        return None, True
    die(f"success token must be true, false, or void: {token}")


def _parse_minutes(token: str) -> float | None:
    if token.strip().lower() in {"none", "null", "-"}:
        return None
    try:
        value = float(token)
    except ValueError:
        die(f"actual_minutes must be a number or none: {token}")
    if value < 0:
        die(f"actual_minutes must be nonnegative: {token}")
    return value


def _parse_json_list_token(token: str, label: str) -> list[str]:
    try:
        value = json.loads(token)
    except json.JSONDecodeError as exc:
        die(f"{label} must be JSON list: {exc}")
    if not isinstance(value, list):
        die(f"{label} must be JSON list")
    return [str(item) for item in value]


def action_forecast_resolve(args: list[str]) -> None:
    if len(args) < 4 or len(args) > 7:
        usage()
    contract_id, success_token, minutes_token, note = args[:4]
    success_bool, voided = _parse_success_token(success_token)
    realized = _parse_json_list_token(args[4], "realized_failure_modes_json") if len(args) > 4 else []
    externality = _parse_json_list_token(args[5], "externality_tags_json") if len(args) > 5 else []
    negative_externality = (
        _parse_json_list_token(args[6], "negative_externality_tags_json")
        if len(args) > 6 else []
    )
    payload = {
        "contract_id": contract_id,
        "success_bool": success_bool,
        "voided": voided,
        "actual_cost_agent_minutes": _parse_minutes(minutes_token),
        "resolution_note": note,
        "realized_failure_mode_ids": realized,
        "externality_tags": externality,
        "negative_externality_tags": negative_externality,
    }
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
        local_tmp = Path(fh.name)
    remote_tmp = f"/tmp/ztare_forecast_resolve_{os.getpid()}_{contract_id}.json"
    try:
        run(scp_base() + [str(local_tmp), f"{VPS}:{remote_tmp}"])
        action_forecast_resolve_file([remote_tmp])
    finally:
        try:
            local_tmp.unlink()
        except FileNotFoundError:
            pass
        remote_shell(f"rm -f {shlex.quote(remote_tmp)}")


def action_forecast_aggregate(args: list[str]) -> None:
    if len(args) != 1:
        usage()
    remote_cmd(
        [
            "python3",
            "scripts/public/control/forecast/pool.py",
            "aggregate",
            "--contract-id",
            args[0],
        ],
        official_store=True,
    )


def action_forecast_decision_use(args: list[str]) -> None:
    if len(args) < 8:
        usage()
    contract_id, tick_id, used_for, changed, old_action, new_action = args[:6]
    failure_modes, notes = args[6:8]
    owner = args[8] if len(args) > 8 else OWNER_DEFAULT
    if used_for not in {"run", "split", "defer", "kill", "ask_more", "ignore", "override"}:
        die(f"invalid used_for: {used_for}")
    cmd = [
        "python3",
        "scripts/public/control/forecast/pool.py",
        "record-decision-use",
        "--contract-id",
        contract_id,
        "--tick-id",
        tick_id,
        "--owner",
        owner,
        "--decision-stage",
        "pretick",
        "--used-for",
        used_for,
        "--failure-modes-adopted-json",
        failure_modes,
        "--notes",
        notes,
        "--dedupe",
    ]
    if changed != "none":
        if changed not in {"true", "false"}:
            die("decision_changed must be true, false, or none")
        cmd.append("--decision-changed-bool" if changed == "true" else "--no-decision-changed-bool")
    if old_action != "none":
        cmd.extend(["--old-action", old_action])
    if new_action != "none":
        cmd.extend(["--new-action", new_action])
    remote_cmd(cmd, official_store=True)


def action_forecast_score(args: list[str]) -> None:
    if len(args) != 1:
        usage()
    remote_cmd(
        [
            "python3",
            "scripts/public/control/forecast/pool.py",
            "score",
            "--contract-id",
            args[0],
        ],
        official_store=True,
    )


def action_rd_brief(args: list[str]) -> None:
    owner = args[0] if args else OWNER_DEFAULT
    remote_cmd(["python3", "scripts/public/control/rd_tick_brief.py", "--short"], owner=owner, membrane=True)


def action_start_tick(args: list[str]) -> None:
    if len(args) < 5:
        usage()
    tick_id, contract_id, substrate, residual_target, goal = args[:5]
    owner = args[5] if len(args) > 5 else OWNER_DEFAULT
    validate_structural_residual_target(
        substrate,
        residual_target,
        allow_new=bool(len(args) > 6 and args[6]),
    )
    cmd = [
        "python3",
        "scripts/public/control/start_tick.py",
        "--tick-id",
        tick_id,
        "--forecast-contract-id",
        contract_id,
        "--substrate",
        substrate,
        "--residual-target",
        residual_target,
        "--goal",
        goal,
    ]
    if len(args) > 6 and args[6]:
        cmd += ["--new-target-justification", args[6]]
    remote_cmd(cmd, owner=owner, membrane=True)


def action_pretick(args: list[str]) -> None:
    if len(args) < 8:
        usage()
    tick_id, contract_id, substrate, residual_target = args[:4]
    universal_ops, scopes, anchor_files, goal = args[4:8]
    owner = args[8] if len(args) > 8 else OWNER_DEFAULT
    validate_structural_residual_target(substrate, residual_target)
    remote_cmd(
        [
            "python3",
            "scripts/public/control/pretick_runner.py",
            "--tick-id",
            tick_id,
            "--contract-id",
            contract_id,
            "--substrate",
            substrate,
            "--residual-target",
            residual_target,
            "--universal-ops",
            universal_ops,
            "--scopes",
            scopes,
            "--anchor-files",
            anchor_files,
            "--owner",
            owner,
            "--goal",
            goal,
        ],
        owner=owner,
        membrane=True,
    )


def action_posttick(args: list[str]) -> None:
    decision_changed = False
    filtered: list[str] = []
    for arg in args:
        if arg == "--decision-changed":
            decision_changed = True
        else:
            filtered.append(arg)
    if len(filtered) < 4 or len(filtered) > 6:
        usage()
    tick_id, contract_id, substrate, goal = filtered[:4]
    owner = filtered[4] if len(filtered) > 4 else OWNER_DEFAULT
    artifact_path = filtered[5] if len(filtered) > 5 else ""
    cmd = [
        "python3",
        "scripts/public/control/posttick_runner.py",
        "--tick-id",
        tick_id,
        "--contract-id",
        contract_id,
        "--substrate",
        substrate,
        "--owner",
        owner,
        "--goal",
        goal,
    ]
    if artifact_path:
        safe_repo_path(artifact_path)
        cmd += ["--artifact-path", artifact_path]
    if decision_changed:
        cmd.append("--decision-changed")
    remote_cmd(cmd, owner=owner, membrane=True)


def action_deploy_update(args: list[str]) -> None:
    if len(args) > 1 or (args and args[0] != "--dry-run"):
        usage()
    env = os.environ.copy()
    env["ZTARE_VPS_SSH"] = VPS
    env["ZTARE_VPS_KEY"] = str(KEY)
    env["ZTARE_VPS_REPO"] = REMOTE_REPO
    run(["bash", str(SCRIPT_DIR / "vps_update.sh")] + args, env=env)


def action_toolchain_smoke(args: list[str]) -> None:
    if args:
        usage()
    remote_chain(
        [
            [
                "python3",
                "-c",
                (
                    "import os, shutil, sys; "
                    "print('python3', sys.executable); "
                    "print('PATH', os.environ.get('PATH', '')); "
                    "print('lake', shutil.which('lake'))"
                ),
            ],
            [REMOTE_LAKE, "env", "lean", "--version"],
        ],
        cwd=f"{REMOTE_REPO}/ztare_proofs",
    )


def action_isabelle_smoke(args: list[str]) -> None:
    if args:
        usage()
    remote_cmd(
        [
            "./venv/bin/python",
            "-m",
            "ztare.leanmill.solver.sledgehammer",
            "--live-theory-smoke",
        ]
    )


def action_transport_probe(args: list[str]) -> None:
    if args:
        usage()
    samples_ms: list[int] = []
    for _index in range(3):
        started = time.monotonic_ns()
        output = remote_cmd(
            ["python3", "-c", "print('ztare-transport-ok')"],
            capture=True,
        ).strip()
        if output != "ztare-transport-ok":
            die(f"unexpected transport probe output: {output!r}")
        samples_ms.append((time.monotonic_ns() - started) // 1_000_000)
    print(json.dumps({
        "schema": "ztare.vps_transport_probe.v1",
        "samples_ms": samples_ms,
        "cold_ms": samples_ms[0],
        "warm_mean_ms": sum(samples_ms[1:]) // 2,
    }, sort_keys=True))


def action_subscription_runtime_smoke(args: list[str]) -> None:
    if args:
        usage()
    remote_cmd(
        [
            "python3",
            "-c",
            (
                "import json,shutil,subprocess; rows={}; "
                "[(lambda n,p: rows.update({n:{'executable':p or '',"
                "'version':(subprocess.run([p,'--version'],capture_output=True,text=True).stdout.strip() if p else '')}}))"
                "(name,shutil.which(name)) for name in ('codex','claude','npm')]; "
                "print(json.dumps(rows,sort_keys=True))"
            ),
        ]
    )


def action_codex_upgrade(args: list[str]) -> None:
    if len(args) > 1:
        usage()
    version = args[0] if args else "latest"
    if version != "latest" and re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,2}", version) is None:
        die("codex-upgrade version must be numeric or latest")
    prefix = str(Path(REMOTE_REPO).parent / ".local")
    remote_cmd(
        [
            "npm",
            "install",
            "--global",
            "--prefix",
            prefix,
            f"@openai/codex@{version}",
        ]
    )
    remote_cmd(["codex", "--version"])


def action_sync_listed(args: list[str]) -> None:
    if not args:
        usage()
    for path in args:
        sync_one_allowlisted(path)


def action_lean_check_file(args: list[str]) -> None:
    if len(args) != 1:
        usage()
    remote_lean_check_file(args[0])


def action_lean_build(args: list[str]) -> None:
    if len(args) != 1:
        usage()
    validate_lake_target(args[0])
    remote_cmd([REMOTE_LAKE, "build", args[0]], cwd=f"{REMOTE_REPO}/ztare_proofs")


def action_lean_parity(args: list[str]) -> None:
    build_target = ""
    all_allowlisted = False
    paths: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--build":
            if i + 1 >= len(args):
                usage()
            build_target = args[i + 1]
            i += 2
        elif args[i] == "--all-allowlisted":
            all_allowlisted = True
            i += 1
        elif args[i].startswith("--"):
            die(f"unknown lean-parity option: {args[i]}")
        else:
            paths.append(args[i])
            i += 1
    if all_allowlisted:
        paths.extend(sorted(allowlist()))
    if not paths:
        usage()
    for path in paths:
        sync_one_allowlisted(path)
    lean_count = 0
    for path in paths:
        if path.startswith("ztare_proofs/") and path.endswith(".lean"):
            print(f"CHECK lean {path}")
            remote_lean_check_file(path)
            lean_count += 1
    if build_target:
        validate_lake_target(build_target)
        remote_cmd([REMOTE_LAKE, "build", build_target], cwd=f"{REMOTE_REPO}/ztare_proofs")
    print(f"OK lean-parity synced={len(paths)} lean_checks={lean_count} build={build_target or 'none'}")


def _campaign_metadata(campaign_path: str) -> dict:
    safe_repo_path(campaign_path)
    path = LOCAL_REPO / campaign_path
    if not path.is_file():
        die(f"local campaign file missing: {campaign_path}")
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    parts = text.split("---", 2)
    if len(parts) != 3:
        die(f"invalid campaign frontmatter: {campaign_path}")
    try:
        import yaml  # type: ignore[import-not-found]

        metadata = yaml.safe_load(parts[1]) or {}
    except Exception as exc:
        die(f"cannot parse campaign frontmatter: {exc}")
    if not isinstance(metadata, dict):
        die("campaign frontmatter must be an object")
    return metadata


def _campaign_input_paths(campaign_path: str) -> list[str]:
    """Return the campaign and the small, explicitly declared input files."""

    metadata = _campaign_metadata(campaign_path)

    declared = [campaign_path]
    typed = str(metadata.get("typed_blueprint") or "").strip()
    if typed:
        typed_path = Path(typed)
        if typed_path.is_absolute():
            try:
                typed_path = typed_path.relative_to(LOCAL_REPO)
            except ValueError:
                die("typed_blueprint must be inside the repository")
        elif len(typed_path.parts) == 1:
            typed_path = Path(campaign_path).parent / typed_path
        declared.append(typed_path.as_posix())

    frozen = metadata.get("frozen_context_ref") or {}
    if isinstance(frozen, dict) and str(frozen.get("path") or "").strip():
        snapshot_path = Path(str(frozen["path"]))
        if snapshot_path.is_absolute():
            try:
                snapshot_path = snapshot_path.relative_to(LOCAL_REPO)
            except ValueError:
                die("frozen context must be inside the repository")
        declared.append(snapshot_path.as_posix())

    ordered: list[str] = []
    for declared_path in declared:
        safe_repo_path(declared_path)
        if declared_path not in ordered:
            ordered.append(declared_path)
    return ordered


def action_leanmill_campaign(args: list[str]) -> None:
    detached = False
    if len(args) == 3 and args[-1] == "--detach":
        detached = True
        args = args[:-1]
    if len(args) != 2:
        usage()
    campaign_path, output_root = args
    if not campaign_path.endswith(".md"):
        die("leanmill-campaign expects a Markdown campaign")
    validate_remote_tmp_or_repo(output_root, "LeanMill output root")
    campaign_inputs = _campaign_input_paths(campaign_path)
    for path in campaign_inputs:
        sync_one_allowlisted(path)
    # Admission is provider-free and must run before a detached launch can
    # reserve any paid turn.  The campaign command repeats the check locally
    # on the VPS, but this gate makes a bad input fail at the transport door.
    if str(_campaign_metadata(campaign_path).get("typed_blueprint") or "").strip():
        remote_cmd(
            [
                "./venv/bin/python",
                "-m",
                "ztare.leanmill.cli",
                "preflight",
                campaign_path,
            ]
        )
    command = [
        "./venv/bin/python",
        "-m",
        "ztare.leanmill.cli",
        "campaign",
        campaign_path,
        "--output-root",
        output_root,
    ]
    prefix = (
        f"cd {shlex.quote(REMOTE_REPO)} && export {remote_exports()} "
        f"ZTARE_LEANMILL_CAMPAIGN_STATE_ROOT={shlex.quote(output_root)} && "
        f"mkdir -p {shlex.quote(output_root)} && "
    )
    if not detached:
        remote_shell(prefix + shlex.join(command))
        return
    launch_id = "launch-" + uuid.uuid4().hex
    log_path = f"{output_root.rstrip('/')}/{launch_id}.log"
    unit_name = "ztare-leanmill-" + launch_id.removeprefix("launch-")
    service_script = (
        f"export {remote_exports()} "
        f"ZTARE_LEANMILL_CAMPAIGN_STATE_ROOT={shlex.quote(output_root)}; "
        f"exec {shlex.join(command)} >{shlex.quote(log_path)} 2>&1"
    )
    detached_command = [
        "systemd-run",
        "--user",
        "--quiet",
        "--collect",
        f"--unit={unit_name}",
        f"--working-directory={REMOTE_REPO}",
        "--",
        "/bin/bash",
        "-lc",
        service_script,
    ]
    remote_shell(
        f"mkdir -p {shlex.quote(output_root)} && {shlex.join(detached_command)}"
    )
    print(json.dumps({
        "schema": "leanmill.campaign_launch.v1",
        "launch_id": launch_id,
        "unit_name": unit_name,
        "output_root": output_root,
        "log_path": log_path,
        "campaign_path": campaign_path,
        "status": "launched",
    }, sort_keys=True))


def action_leanmill_preflight(args: list[str]) -> None:
    if len(args) != 1:
        usage()
    campaign_path = args[0]
    if not campaign_path.endswith(".md"):
        die("leanmill-preflight expects a Markdown campaign")
    for path in _campaign_input_paths(campaign_path):
        sync_one_allowlisted(path)
    remote_cmd(
        [
            "./venv/bin/python",
            "-m",
            "ztare.leanmill.cli",
            "preflight",
            campaign_path,
        ]
    )


def action_leanmill_source_fetch(args: list[str]) -> None:
    """Fetch one digest-pinned campaign reference without a substrate-specific route."""

    if len(args) != 3:
        usage()
    url, expected_sha, destination = args
    if not re.fullmatch(r"https://[^\s'\"`;&|<>]+", url):
        die("leanmill-source-fetch requires one safe HTTPS URL")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        die("leanmill-source-fetch requires a lowercase SHA-256 digest")
    if not destination.startswith("/tmp/leanmill_source_snapshots/"):
        die("leanmill-source-fetch destination must be under /tmp/leanmill_source_snapshots")
    if any(part in {"", ".", ".."} for part in Path(destination).parts[3:]):
        die("leanmill-source-fetch destination contains unsafe path components")
    partial = destination + ".part"
    remote_cmd(["mkdir", "-p", str(Path(destination).parent)], cwd=None)
    remote_cmd(
        ["curl", "--fail", "--location", "--silent", "--show-error", "--output", partial, url],
        cwd=None,
    )
    actual = remote_cmd(["sha256sum", partial], cwd=None, capture=True).split()[0]
    if actual != expected_sha:
        die(
            "leanmill source digest mismatch: "
            f"expected={expected_sha} actual={actual}",
            1,
        )
    remote_cmd(["mv", partial, destination], cwd=None)
    print(f"OK leanmill-source-fetch {destination} {actual}")


def _leanmill_attempt_action(command: str, args: list[str]) -> None:
    if len(args) != 1:
        usage()
    attempt_dir = args[0]
    validate_remote_tmp_or_repo(attempt_dir, "LeanMill attempt directory")
    remote_cmd(
        ["./venv/bin/python", "-m", "ztare.leanmill.cli", command, attempt_dir]
    )


def action_leanmill_latest(args: list[str]) -> None:
    if len(args) != 1:
        usage()
    output_root = args[0]
    validate_remote_tmp_or_repo(output_root, "LeanMill output root")
    remote_cmd(
        [
            "python3",
            "-c",
            (
                "from pathlib import Path; import sys; "
                "root=Path(sys.argv[1]); "
                "rows=sorted([p for pat in ('attempt-*','formalize-*') for p in root.glob(pat) if p.is_dir()], "
                "key=lambda p:p.stat().st_mtime_ns); "
                "print(rows[-1] if rows else 'NONE')"
            ),
            output_root,
        ]
    )


def action_leanmill_agent_output(args: list[str]) -> None:
    if len(args) not in {3, 4}:
        usage()
    attempt_dir, role, index_text = args[:3]
    validate_remote_tmp_or_repo(attempt_dir, "LeanMill attempt directory")
    if role not in {
        "blueprint_compiler",
        "semantic_reviewer",
        "navigator",
        "lean_solver",
        "post_freeze_interpreter",
        "adapter_forge",
        "adapter_reviewer",
    }:
        die(f"unsupported LeanMill role: {role}")
    if not index_text.isdigit() or int(index_text) > 999:
        die(f"invalid LeanMill call index: {index_text}")
    kind = args[3] if len(args) == 4 else "stdout"
    suffixes = {
        "stdout": "stdout.txt",
        "stderr": "stderr.txt",
        "call": "call.json",
        "prompt": "prompt.txt",
        "result": "result.json",
        "schema": "schema.json",
        "dispatch": "dispatch.json",
    }
    if kind not in suffixes:
        die(f"unsupported LeanMill call artifact: {kind}")
    output_path = (
        f"{attempt_dir}/agent_calls/{role}/"
        f"{int(index_text):03d}.{suffixes[kind]}"
    )
    validate_remote_tmp_or_repo(output_path, "LeanMill agent output")
    remote_cmd(
        [
            "python3",
            "-c",
            (
                "from pathlib import Path; import sys; p=Path(sys.argv[1]); "
                "print(p.read_text(encoding='utf-8') if p.is_file() else 'MISSING')"
            ),
            output_path,
        ]
    )


def action_leanmill_agent_results(args: list[str]) -> None:
    if len(args) != 2:
        usage()
    attempt_dir, role = args
    validate_remote_tmp_or_repo(attempt_dir, "LeanMill attempt directory")
    if role not in {
        "blueprint_compiler",
        "semantic_reviewer",
        "navigator",
        "lean_solver",
        "post_freeze_interpreter",
    }:
        die(f"unsupported LeanMill role: {role}")
    role_dir = f"{attempt_dir}/agent_calls/{role}"
    remote_cmd(
        [
            "python3",
            "-c",
            (
                "from pathlib import Path; import json,sys; root=Path(sys.argv[1]); rows=[]; "
                "calls=sorted(root.glob('*.call.json')); "
                "[(lambda p,r: rows.append({'index':p.name.split('.')[0],"
                "'call':json.loads(p.read_text()),"
                "'result':json.loads(r.read_text()) if r.is_file() else None}))"
                "(p,p.parent/(p.name.split('.')[0]+'.result.json')) for p in calls]; "
                "print(json.dumps(rows,sort_keys=True))"
            ),
            role_dir,
        ]
    )


def action_leanmill_status(args: list[str]) -> None:
    _leanmill_attempt_action("status", args)


def action_leanmill_inspect(args: list[str]) -> None:
    _leanmill_attempt_action("inspect", args)


def action_leanmill_replay(args: list[str]) -> None:
    _leanmill_attempt_action("replay", args)


def action_leanmill_resume(args: list[str]) -> None:
    if not args:
        usage()
    attempt_dir = args[0]
    validate_remote_tmp_or_repo(attempt_dir, "LeanMill attempt directory")
    detached = "--detach" in args[1:]
    delay_s = 0
    extras = list(args[1:])
    if "--detach" in extras:
        extras.remove("--detach")
    if "--delay-s" in extras:
        index = extras.index("--delay-s")
        if index + 1 >= len(extras) or not extras[index + 1].isdigit():
            usage()
        delay_s = int(extras[index + 1])
        del extras[index : index + 2]
    if extras or (delay_s and not detached):
        usage()
    if not detached:
        _leanmill_attempt_action("resume", [attempt_dir])
        return
    launch_id = "resume-" + uuid.uuid4().hex
    unit_name = "ztare-leanmill-" + launch_id
    log_path = f"{attempt_dir.rstrip('/')}/{launch_id}.log"
    command = [
        "./venv/bin/python", "-m", "ztare.leanmill.cli", "resume", attempt_dir,
    ]
    service_script = (
        f"export {remote_exports()}; "
        f"exec {shlex.join(command)} >{shlex.quote(log_path)} 2>&1"
    )
    detached_command = [
        "systemd-run", "--user", "--quiet", "--collect",
        f"--unit={unit_name}",
        f"--working-directory={REMOTE_REPO}",
    ]
    if delay_s:
        detached_command.append(f"--on-active={delay_s}s")
    detached_command.extend(["--", "/bin/bash", "-lc", service_script])
    remote_shell(shlex.join(detached_command))
    print(json.dumps({
        "schema": "leanmill.campaign_resume_launch.v1",
        "launch_id": launch_id,
        "unit_name": unit_name,
        "attempt_dir": attempt_dir,
        "log_path": log_path,
        "delay_s": delay_s,
        "status": "scheduled" if delay_s else "launched",
    }, sort_keys=True))


def action_leanmill_continue_epoch(args: list[str]) -> None:
    _leanmill_attempt_action("continue-epoch", args)


def action_leanmill_recover(args: list[str]) -> None:
    _leanmill_attempt_action("recover", args)


def action_leanmill_recheck(args: list[str]) -> None:
    if len(args) not in {3, 5} or args[1] != "--lean-root":
        usage()
    attempt_dir, lean_root = args[0], args[2]
    validate_remote_tmp_or_repo(attempt_dir, "LeanMill attempt directory")
    validate_remote_tmp_or_repo(lean_root, "Lean root")
    command = [
        "./venv/bin/python",
        "-m",
        "ztare.leanmill.cli",
        "recheck",
        attempt_dir,
        "--lean-root",
        lean_root,
    ]
    if len(args) == 5:
        if args[3] != "--timeout-s" or not args[4].isdigit():
            usage()
        command.extend(args[3:])
    remote_cmd(command)


def action_leanmill_interpret(args: list[str]) -> None:
    if not args:
        usage()
    attempt_dir = args[0]
    validate_remote_tmp_or_repo(attempt_dir, "LeanMill attempt directory")
    command = [
        "./venv/bin/python", "-m", "ztare.leanmill.cli", "interpret", attempt_dir
    ]
    i = 1
    while i < len(args):
        if args[i] == "--model" and i + 1 < len(args):
            command.extend(args[i:i + 2])
            i += 2
        elif args[i] == "--reasoning-effort" and i + 1 < len(args):
            if args[i + 1] not in {"low", "medium", "high", "ultra"}:
                die("literature reasoning effort must be low, medium, high, or ultra")
            command.extend(args[i:i + 2])
            i += 2
        elif args[i] == "--retry-inconclusive":
            command.append(args[i])
            i += 1
        elif args[i] == "--retry-failed":
            command.append(args[i])
            i += 1
        else:
            die(f"unknown leanmill-interpret option: {args[i]}")
    remote_cmd(command)


def action_leanmill_adapter_forge(args: list[str]) -> None:
    if not args:
        usage()
    attempt_dir = args[0]
    validate_remote_tmp_or_repo(attempt_dir, "LeanMill attempt directory")
    command = [
        "./venv/bin/python", "-m", "ztare.leanmill.cli", "adapter-forge", attempt_dir
    ]
    i = 1
    while i < len(args):
        if args[i] == "--model" and i + 1 < len(args):
            command.extend(args[i:i + 2])
            i += 2
        elif args[i] == "--reasoning-effort" and i + 1 < len(args):
            if args[i + 1] not in {"low", "medium", "high", "ultra"}:
                die("AdapterForge reasoning effort must be low, medium, high, or ultra")
            command.extend(args[i:i + 2])
            i += 2
        else:
            die(f"unknown leanmill-adapter-forge option: {args[i]}")
    remote_cmd(command)


def action_leanmill_extend_budget(args: list[str]) -> None:
    if not args:
        usage()
    attempt_dir = args[0]
    validate_remote_tmp_or_repo(attempt_dir, "LeanMill attempt directory")
    command = [
        "./venv/bin/python",
        "-m",
        "ztare.leanmill.cli",
        "extend-budget",
        attempt_dir,
    ]
    i = 1
    while i < len(args):
        if args[i] in {
            "--seconds", "--phase", "--provider-calls", "--agent-turns",
            "--workbench-actions", "--adapter-forge-attempts",
            "--authority-ref", "--reason",
        } and i + 1 < len(args):
            command.extend(args[i:i + 2])
            i += 2
        else:
            die(f"unknown leanmill-extend-budget option: {args[i]}")
    remote_cmd(command)


def action_leanmill_verify(args: list[str]) -> None:
    if not args:
        usage()
    attempt_dir = args[0]
    validate_remote_tmp_or_repo(attempt_dir, "LeanMill attempt directory")
    command = [
        "./venv/bin/python",
        "-m",
        "ztare.leanmill.cli",
        "verify",
        attempt_dir,
    ]
    i = 1
    while i < len(args):
        if args[i] == "--with-isabelle":
            command.append("--with-isabelle")
            i += 1
        elif args[i] == "--with-lean":
            command.append("--with-lean")
            i += 1
        elif args[i] == "--lean-root" and i + 1 < len(args):
            lean_root = args[i + 1]
            validate_remote_tmp_or_repo(lean_root, "Lean root")
            command.extend(["--lean-root", lean_root])
            i += 2
        else:
            die(f"unknown leanmill-verify option: {args[i]}")
    remote_cmd(command)


def action_leanmill_stop(args: list[str]) -> None:
    if len(args) != 2:
        usage()
    attempt_dir, authority_ref = args
    validate_remote_tmp_or_repo(attempt_dir, "LeanMill attempt directory")
    remote_cmd(
        [
            "./venv/bin/python",
            "-m",
            "ztare.leanmill.cli",
            "stop",
            attempt_dir,
            "--authority-ref",
            authority_ref,
        ]
    )


def action_leanmill_retire(args: list[str]) -> None:
    if len(args) != 3:
        usage()
    attempt_dir, authority_ref, reason = args
    validate_remote_tmp_or_repo(attempt_dir, "LeanMill attempt directory")
    remote_cmd(
        [
            "./venv/bin/python",
            "-m",
            "ztare.leanmill.cli",
            "retire",
            attempt_dir,
            "--authority-ref",
            authority_ref,
            "--reason",
            reason,
        ]
    )


def action_tick_close_payload(args: list[str]) -> None:
    if len(args) < 3:
        usage()
    tick_id, contract_id, payload_dir = args[:3]
    owner = args[3] if len(args) > 3 else OWNER_DEFAULT
    # Legacy alias kept for operator muscle memory. Route through the same
    # preflight as `rd-close` so no normal wrapper bypasses research-sufficiency
    # or obligation-discharge checks.
    action_rd_close([tick_id, contract_id, payload_dir, owner])


def action_rd_close(args: list[str]) -> None:
    if len(args) < 3:
        usage()
    tick_id, contract_id, payload_dir = args[:3]
    owner = args[3] if len(args) > 3 else OWNER_DEFAULT
    validate_remote_tmp_or_repo(payload_dir, "payload dir")
    remote_cmd(
        [
            "python3",
            "scripts/public/control/rd_forecast_tick_close.py",
            "--tick-id",
            tick_id,
            "--contract-id",
            contract_id,
            "--payload-dir",
            payload_dir,
            "--owner",
            owner,
        ],
        owner=owner,
        membrane=True,
    )


def action_rd_close_local_payload(args: list[str]) -> None:
    if len(args) < 4:
        usage()
    tick_id, contract_id, local_payload_dir, remote_payload_dir = args[:4]
    owner = args[4] if len(args) > 4 else OWNER_DEFAULT
    local_dir = Path(local_payload_dir)
    if not local_dir.is_absolute():
        local_dir = LOCAL_REPO / local_dir
    if not local_dir.is_dir():
        die(f"local payload dir missing: {local_dir}")
    validate_remote_tmp_or_repo(remote_payload_dir, "payload dir")
    required = ["f_row.txt", "declared.json", "witnesses.json", "why_not.json"]
    for name in required:
        path = local_dir / name
        if not path.is_file():
            die(f"local payload missing: {path}")
    lint_local_close_payload(local_dir)
    remote_shell(f"mkdir -p {shlex.quote(remote_payload_dir)}")
    uploaded = 0
    for path in sorted(local_dir.rglob("*")):
        if path.is_symlink():
            die(f"local payload contains symlink: {path}")
        if not path.is_file():
            continue
        rel = path.relative_to(local_dir)
        if any(part in {"", ".", ".."} for part in rel.parts):
            die(f"unsafe local payload path: {rel}")
        remote_parent = f"{remote_payload_dir}/{rel.parent.as_posix()}"
        remote_shell(f"mkdir -p {shlex.quote(remote_parent)}")
        run(scp_base() + [str(path), f"{VPS}:{remote_payload_dir}/{rel.as_posix()}"])
        uploaded += 1
    print(f"OK rd-close-local-payload uploaded={uploaded}")
    action_rd_close([tick_id, contract_id, remote_payload_dir, owner])


ACTIONS = {
    "membrane-state": action_membrane_state,
    "posttick-check": action_posttick_check,
    "forecast-materialize": action_forecast_materialize,
    "forecast-smoke": action_forecast_smoke,
    "forecast-hash": action_forecast_hash,
    "forecast-consume-live": action_forecast_consume_live,
    "forecast-init": action_forecast_init,
    "forecast-init-micro": action_forecast_init_micro,
    "forecast-add-rd": action_forecast_add_rd,
    "forecast-aggregate": action_forecast_aggregate,
    "forecast-decision-use": action_forecast_decision_use,
    "forecast-resolve": action_forecast_resolve,
    "forecast-resolve-file": action_forecast_resolve_file,
    "forecast-score": action_forecast_score,
    "rd-brief": action_rd_brief,
    "start-tick": action_start_tick,
    "pretick": action_pretick,
    "posttick": action_posttick,
    "deploy-update": action_deploy_update,
    "toolchain-smoke": action_toolchain_smoke,
    "isabelle-smoke": action_isabelle_smoke,
    "transport-probe": action_transport_probe,
    "subscription-runtime-smoke": action_subscription_runtime_smoke,
    "codex-upgrade": action_codex_upgrade,
    "sync-listed": action_sync_listed,
    "lean-check-file": action_lean_check_file,
    "lean-build": action_lean_build,
    "lean-parity": action_lean_parity,
    "leanmill-preflight": action_leanmill_preflight,
    "leanmill-source-fetch": action_leanmill_source_fetch,
    "leanmill-campaign": action_leanmill_campaign,
    "leanmill-latest": action_leanmill_latest,
    "leanmill-agent-output": action_leanmill_agent_output,
    "leanmill-agent-results": action_leanmill_agent_results,
    "leanmill-status": action_leanmill_status,
    "leanmill-inspect": action_leanmill_inspect,
    "leanmill-verify": action_leanmill_verify,
    "leanmill-replay": action_leanmill_replay,
    "leanmill-resume": action_leanmill_resume,
    "leanmill-continue-epoch": action_leanmill_continue_epoch,
    "leanmill-recover": action_leanmill_recover,
    "leanmill-recheck": action_leanmill_recheck,
    "leanmill-interpret": action_leanmill_interpret,
    "leanmill-adapter-forge": action_leanmill_adapter_forge,
    "leanmill-extend-budget": action_leanmill_extend_budget,
    "leanmill-stop": action_leanmill_stop,
    "leanmill-retire": action_leanmill_retire,
    "tick-close-payload": action_tick_close_payload,
    "rd-close": action_rd_close,
    "rd-close-local-payload": action_rd_close_local_payload,
}


def main(argv: list[str]) -> int:
    if not argv:
        usage()
    action, rest = argv[0], argv[1:]
    handler = ACTIONS.get(action)
    if handler is None:
        usage()
    handler(rest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
