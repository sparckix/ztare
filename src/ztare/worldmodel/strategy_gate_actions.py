from __future__ import annotations

import importlib.util
import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ztare.common.operator_proposal_contract import open_cards


@dataclass(frozen=True)
class StrategyGateAction:
    command: str
    purpose: str
    required_card_fields: tuple[str, ...]
    output_schema: str
    handler: Callable[[Path, dict[str, Any], dict[str, Any]], dict[str, Any]]


def registered_strategy_gate_actions() -> dict[str, StrategyGateAction]:
    return {
        "arc3_level_transfer_probe": StrategyGateAction(
            command="arc3_level_transfer_probe",
            purpose=(
                "Run the substrate adapter's bounded transfer probe declared "
                "by a Strategy card."
            ),
            required_card_fields=("action_plan.required_next_gate", "action_plan.seed_prerequisite.seed_path"),
            output_schema="ztare-leaf-workbench-strategy-gate-result-v1",
            handler=_run_arc3_level_transfer_probe,
        )
    }


def strategy_gate_action_summaries(project_dir: str | Path) -> list[dict[str, Any]]:
    project = Path(project_dir)
    rows: list[dict[str, Any]] = []
    actions = registered_strategy_gate_actions()
    for card in open_cards(project / "workspace" / "strategy_experiments.jsonl"):
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
        command = str(gate.get("command") or "").strip()
        action = actions.get(command)
        if not command or action is None:
            continue
        seed = plan.get("seed_prerequisite") if isinstance(plan.get("seed_prerequisite"), dict) else {}
        rows.append(
            {
                "failure_family_sha": str(card.get("failure_family_sha") or ""),
                "command": command,
                "source_ref": "workspace/strategy_experiments.jsonl",
                "source_sha": _shaish(project / "workspace" / "strategy_experiments.jsonl"),
                "summary": (
                    f"required_gate={command}; status={gate.get('success_status') or '?'}; "
                    f"seed={_project_relative_ref(project, str(seed.get('seed_path') or '?'))}"
                    f"{_latest_gate_receipt_summary(project, command)}"
                ),
            }
        )
    return rows


def run_strategy_required_gate_action(
    project_dir: str | Path,
    input_refs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    refs = input_refs if isinstance(input_refs, dict) else {}
    project = Path(project_dir)
    card = _select_strategy_card(project, refs)
    plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
    gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
    command = str(refs.get("command") or gate.get("command") or "").strip()
    action = registered_strategy_gate_actions().get(command)
    if action is None:
        raise ValueError(
            f"no registered Strategy gate action for command {command!r}; "
            "report the missing gate action inside LOWERABILITY_BLOCKED in science mode"
        )
    cache_key = _strategy_gate_cache_key(project, command, card, refs)
    cached = _load_strategy_gate_cache(project, cache_key)
    if cached is not None:
        return cached
    result = action.handler(project, card, refs)
    result = _materialize_strategy_gate_receipt(project, command, result)
    wrapped = {
        "schema": "ztare-leaf-workbench-strategy-gate-result-v1",
        "command": command,
        "failure_family_sha": str(card.get("failure_family_sha") or ""),
        "receipt_ref": result.get("receipt_ref") or "",
        "receipt_sha256": result.get("receipt_sha256") or "",
        "status": result.get("status"),
        "result": result,
    }
    _store_strategy_gate_cache(project, cache_key, wrapped)
    return wrapped


def _select_strategy_card(project: Path, refs: dict[str, Any]) -> dict[str, Any]:
    cards = open_cards(project / "workspace" / "strategy_experiments.jsonl")
    if not cards:
        raise ValueError("run_strategy_required_gate requires an open Strategy card")
    requested_sha = str(refs.get("failure_family_sha") or refs.get("strategy_card_sha") or "").strip()
    requested_command = str(refs.get("command") or "").strip()
    registered_commands = set(registered_strategy_gate_actions())
    matching = []
    for card in cards:
        if requested_sha and str(card.get("failure_family_sha") or "") != requested_sha:
            continue
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
        card_command = str(gate.get("command") or "")
        if requested_command:
            if card_command != requested_command:
                continue
        elif card_command not in registered_commands:
            continue
        matching.append(card)
    if len(matching) == 1:
        return matching[0]
    if not matching:
        raise ValueError("no open Strategy card matches the requested gate")
    raise ValueError("ambiguous Strategy gate request; provide failure_family_sha")


def _run_arc3_level_transfer_probe(
    project: Path,
    card: dict[str, Any],
    refs: dict[str, Any],
) -> dict[str, Any]:
    plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
    seed = plan.get("seed_prerequisite") if isinstance(plan.get("seed_prerequisite"), dict) else {}
    gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
    seed_ref = str(refs.get("seed_path") or refs.get("seed_ref") or seed.get("seed_path") or "").strip()
    if not seed_ref:
        raise ValueError("arc3_level_transfer_probe Strategy card requires seed_prerequisite.seed_path")
    game = str(refs.get("game") or gate.get("game") or _game_from_project_name(project.name)).strip()
    candidate_ref = str(refs.get("candidate_path") or refs.get("candidate_ref") or "test_model.py").strip()
    post_depth = _positive_int(
        refs.get("post_depth") or gate.get("post_depth") or plan.get("post_depth"),
        1,
    )
    max_first_diffs = _positive_int(
        refs.get("max_first_diffs")
        or gate.get("max_first_diffs")
        or plan.get("max_first_diffs"),
        12,
    )
    seed_path = _resolve_project_ref(project, seed_ref)
    candidate_path = _resolve_project_ref(project, candidate_ref)
    if not game:
        raise ValueError("arc3_level_transfer_probe requires game or arc3_<game> project naming")
    if not seed_path.exists():
        raise ValueError(f"arc3_level_transfer_probe missing seed_path {seed_path}")
    if not candidate_path.exists():
        raise ValueError(f"arc3_level_transfer_probe missing candidate_path {candidate_path}")
    root = Path(__file__).resolve().parents[3]
    script = root / "scripts" / "public" / "control" / "arc3_level_transfer_probe.py"
    spec = importlib.util.spec_from_file_location("arc3_level_transfer_probe", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {script}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    receipt = mod.run_probe(
        game=game,
        seed_path=seed_path,
        candidate_path=candidate_path,
        max_first_diffs=max_first_diffs,
        post_depth=post_depth,
    )
    latest = project / "workspace" / "latest_level_transfer_probe.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    local_transfer = receipt.get("local_transfer") if isinstance(receipt.get("local_transfer"), dict) else {}
    residue = receipt.get("local_residue_quotient") if isinstance(receipt.get("local_residue_quotient"), dict) else {}
    classes = residue.get("classes") if isinstance(residue.get("classes"), list) else []
    top_class = _compact_residue_class(classes[0]) if classes else {}
    return {
        "schema": "ztare-leaf-workbench-strategy-gate-arc3-level-transfer-v1",
        "receipt_ref": "workspace/latest_level_transfer_probe.json",
        "receipt_sha256": _shaish(latest),
        "status": receipt.get("status"),
        "game": receipt.get("game"),
        "seed_path": _project_relative_ref(project, str(receipt.get("seed_path") or seed_ref)),
        "candidate_path": _project_relative_ref(project, str(receipt.get("candidate_path") or candidate_ref)),
        "post_depth": receipt.get("post_depth"),
        "exact_actions": receipt.get("exact_actions"),
        "exact_steps": local_transfer.get("exact_steps"),
        "steps_tested": local_transfer.get("steps_tested"),
        "first_failed": local_transfer.get("first_failed"),
        "first_failed_after_first_step_repair": local_transfer.get("first_failed_after_first_step_repair"),
        "local_residue_status": residue.get("status"),
        "local_residue_class_count": residue.get("class_count"),
        "top_local_residue_class": top_class,
    }


def _strategy_gate_cache_path(project: Path) -> Path:
    return project / "workspace" / "strategy_gate_action_cache.json"


def _strategy_gate_cache_key(
    project: Path,
    command: str,
    card: dict[str, Any],
    refs: dict[str, Any],
) -> dict[str, Any]:
    plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
    seed = plan.get("seed_prerequisite") if isinstance(plan.get("seed_prerequisite"), dict) else {}
    gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
    seed_ref = str(refs.get("seed_path") or refs.get("seed_ref") or seed.get("seed_path") or "").strip()
    candidate_ref = str(refs.get("candidate_path") or refs.get("candidate_ref") or "test_model.py").strip()
    payload = {
        "schema": "ztare-strategy-gate-action-cache-key-v2",
        "command": command,
        "card_canonical_sha256": _json_sha(card),
        "strategy_ledger_sha256": _shaish(project / "workspace" / "strategy_experiments.jsonl"),
        "failure_family_sha": str(card.get("failure_family_sha") or ""),
        "required_status": gate.get("success_status"),
        "seed_ref": _project_relative_ref(project, seed_ref),
        "seed_sha256": _shaish(_resolve_project_ref(project, seed_ref)) if seed_ref else "",
        "candidate_ref": _project_relative_ref(project, candidate_ref),
        "candidate_sha256": _shaish(_resolve_project_ref(project, candidate_ref)) if candidate_ref else "",
        "params": {
            "game": str(refs.get("game") or gate.get("game") or _game_from_project_name(project.name)),
            "post_depth": _positive_int(
                refs.get("post_depth") or gate.get("post_depth") or plan.get("post_depth"),
                1,
            ),
            "max_first_diffs": _positive_int(
                refs.get("max_first_diffs")
                or gate.get("max_first_diffs")
                or plan.get("max_first_diffs"),
                12,
            ),
        },
        "handler_version": "strategy_gate_actions:v5",
        "handler_source_sha256": _shaish(Path(__file__).resolve()),
        "gate_script_sha256": _strategy_gate_script_sha256(command),
    }
    payload["key_sha256"] = _json_sha(payload)
    return payload


def _strategy_gate_script_sha256(command: str) -> str:
    if command == "arc3_level_transfer_probe":
        root = Path(__file__).resolve().parents[3]
        return _shaish(root / "scripts" / "public" / "control" / "arc3_level_transfer_probe.py")
    return ""


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return max(1, int(default))
    return parsed if parsed > 0 else max(1, int(default))


def _load_strategy_gate_cache(project: Path, key: dict[str, Any]) -> dict[str, Any] | None:
    try:
        payload = json.loads(_strategy_gate_cache_path(project).read_text(encoding="utf-8"))
    except Exception:
        return None
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, dict):
        return None
    row = entries.get(str(key.get("key_sha256") or ""))
    if not isinstance(row, dict):
        return None
    result = row.get("result")
    if not isinstance(result, dict):
        return None
    cached = dict(result)
    ref = str(cached.get("receipt_ref") or "").strip()
    expected = str(cached.get("receipt_sha256") or "").strip()
    if ref and expected:
        receipt_path = _resolve_project_ref(project, ref)
        if _shaish(receipt_path) != expected:
            return None
    cached["cache_hit"] = True
    cached["cache_key_sha256"] = key.get("key_sha256")
    return cached


def _store_strategy_gate_cache(project: Path, key: dict[str, Any], result: dict[str, Any]) -> None:
    path = _strategy_gate_cache_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {"schema": "ztare-strategy-gate-action-cache-v1", "entries": {}}
    if not isinstance(payload, dict):
        payload = {"schema": "ztare-strategy-gate-action-cache-v1", "entries": {}}
    entries = payload.setdefault("entries", {})
    if not isinstance(entries, dict):
        entries = {}
        payload["entries"] = entries
    key_sha = str(key.get("key_sha256") or "")
    if not key_sha:
        return
    row = dict(result)
    row.pop("cache_hit", None)
    row.pop("cache_key_sha256", None)
    entries[key_sha] = {
        "schema": "ztare-strategy-gate-action-cache-entry-v1",
        "key": key,
        "result": row,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _materialize_strategy_gate_receipt(
    project: Path,
    command: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Copy a gate receipt to a content-addressed path before caching it."""
    ref = str(result.get("receipt_ref") or "").strip()
    if not ref:
        return result
    source = _resolve_project_ref(project, ref)
    if not source.is_file():
        return result
    blob = source.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    safe_command = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in command) or "gate"
    receipt_dir = project / "workspace" / "strategy_gate_receipts" / safe_command
    receipt_dir.mkdir(parents=True, exist_ok=True)
    immutable = receipt_dir / f"{digest}.json"
    if not immutable.exists() or immutable.read_bytes() != blob:
        immutable.write_bytes(blob)
    row = dict(result)
    row["receipt_ref"] = _project_relative_ref(project, str(immutable))
    row["receipt_sha256"] = digest
    row["mutable_receipt_ref"] = _project_relative_ref(project, ref)
    return row


def _resolve_project_ref(project: Path, ref: str) -> Path:
    if not str(ref).strip():
        raise ValueError("empty project artifact reference")
    project_root = project.resolve()
    path = Path(ref)
    if path.is_absolute():
        resolved = path.resolve()
        if resolved != project_root and project_root not in resolved.parents:
            raise ValueError(f"project artifact reference escapes project: {ref}")
        return resolved
    parts = path.parts
    if project.name in parts:
        idx = parts.index(project.name)
        path = Path(*parts[idx + 1:]) if idx + 1 < len(parts) else Path(".")
    if ".." in path.parts:
        raise ValueError(f"project artifact reference escapes project: {ref}")
    resolved = (project_root / path).resolve()
    if resolved != project_root and project_root not in resolved.parents:
        raise ValueError(f"project artifact reference escapes project: {ref}")
    return resolved


def _project_relative_ref(project: Path, ref: str) -> str:
    path = Path(ref)
    parts = path.parts
    if project.name in parts:
        idx = parts.index(project.name)
        return str(Path(*parts[idx + 1:]))
    if not path.is_absolute():
        return ref
    try:
        return str(path.relative_to(project))
    except Exception:
        return str(path)


def _game_from_project_name(name: str) -> str:
    parts = name.split("_")
    if len(parts) >= 2 and parts[0] == "arc3":
        return parts[1]
    return ""


def _shaish(path: Path) -> str:
    try:
        import hashlib

        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return ""


def _json_sha(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _latest_gate_receipt_summary(project: Path, command: str) -> str:
    if command != "arc3_level_transfer_probe":
        return ""
    receipt = _read_json(project / "workspace" / "latest_level_transfer_probe.json")
    if not isinstance(receipt, dict):
        return ""
    local = receipt.get("local_transfer") if isinstance(receipt.get("local_transfer"), dict) else {}
    residue = receipt.get("local_residue_quotient") if isinstance(receipt.get("local_residue_quotient"), dict) else {}
    classes = residue.get("classes") if isinstance(residue.get("classes"), list) else []
    top = _compact_residue_class(classes[0]) if classes else {}
    top_bits = ""
    if top:
        top_bits = (
            f"; top_residue={top.get('relation')} "
            f"{top.get('before')}->{top.get('observed')} cells={top.get('cell_count')}"
        )
    return (
        f"; latest_receipt_status={receipt.get('status')}; "
        f"local_exact={local.get('exact_steps')}/{local.get('steps_tested')}; "
        f"local_after_first_step_repair={local.get('exact_steps_after_first_step_repair')}/"
        f"{local.get('steps_tested')}; local_residue_classes={residue.get('class_count')}"
        f"{top_bits}"
    )


def _compact_residue_class(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    return {
        "relation": row.get("relation"),
        "before": row.get("before"),
        "predicted": row.get("predicted"),
        "observed": row.get("observed"),
        "occurrences": row.get("occurrences"),
        "cell_count": row.get("cell_count"),
        "example_cells": row.get("example_cells"),
        "coordinate_contract": row.get("coordinate_contract"),
        "post_steps": row.get("post_steps"),
        "actions": row.get("actions"),
        "initial_actions": row.get("initial_actions"),
    }
