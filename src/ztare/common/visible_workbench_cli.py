from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from ztare.common.visible_workbench_actions import (
    route_visible_workbench_action_request,
    visible_workbench_capability_routes,
    visible_workbench_action_routes,
    visible_workbench_in_turn_routes,
    visible_workbench_parent_kernel_routes,
)
from ztare.common.activity_meter import summarize_activity_spend
from ztare.common.leaf_workbench_python import run_visible_json_probe
from ztare.common.worldmodel_carrier_purity import (
    carrier_contract_error,
    project_dynamics_assumption,
)


SCHEMA = "ztare-visible-workbench-cli-receipt-v1"

# These capabilities return bounded derived receipts over large, prompt-visible
# evidence.  The artifact may be withheld from the staged cwd only because of
# its byte size; the registered handler still needs the authority-side bytes.
# This is an evidence service, not a general filesystem bridge.
_AUTHORITY_DERIVED_ACTIONS = frozenset(
    {
        "inspect_worldmodel_event_timeline",
        "contrast_worldmodel_episodes",
    }
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare-workbench",
        description="Run bounded visible-workbench diagnostics over staged artifacts.",
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Visible workbench root. Defaults to the current working directory.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("manifest", help="Print available visible-workbench commands.")

    probe = sub.add_parser(
        "probe-json",
        help="Run bounded pure Python over explicitly staged JSON artifacts.",
    )
    probe.add_argument("--artifact", action="append", default=[], help="Artifact ref relative to project-dir.")
    probe.add_argument(
        "--probe-stdin",
        action="store_true",
        help="Read probe Python from stdin. Without this, the default summarizer runs.",
    )
    probe.add_argument(
        "--max-output-chars",
        type=int,
        default=3000,
        help="Maximum result_summary characters.",
    )

    carrier = sub.add_parser(
        "check-worldmodel-carrier",
        help="Check a candidate carrier for pure transition and temporal-admissibility violations.",
    )
    carrier.add_argument(
        "--source",
        default="-",
        help="Candidate source file relative to project-dir, or '-' for stdin.",
    )

    score_candidate = sub.add_parser(
        "score-worldmodel-candidate",
        help="Score a candidate source against the staged worldmodel verifier aggregate.",
    )
    score_candidate.add_argument(
        "--source",
        default="-",
        help="Candidate source file relative to project-dir, or '-' for stdin.",
    )

    receipt = sub.add_parser(
        "check-receipt",
        help="Check visible receipt/payload syntax and admissibility without running truth gates.",
    )
    receipt.add_argument(
        "--kind",
        choices=["auto", "worldmodel-payload", "leaf-workbench", "strategy-discharge"],
        default="auto",
        help="Receipt family to validate. auto inspects the submitted text.",
    )
    receipt.add_argument(
        "--source",
        default="-",
        help="Receipt source file relative to project-dir, or '-' for stdin.",
    )

    route = sub.add_parser(
        "route-action",
        help="Route a visible workbench action request to in-turn CLI or parent kernel.",
    )
    route.add_argument(
        "--source",
        default="-",
        help="Action-request source file relative to project-dir, or '-' for stdin.",
    )

    run_action = sub.add_parser(
        "run-action",
        help="Execute a registered in-turn workbench action over staged visible artifacts.",
    )
    run_action.add_argument(
        "--source",
        default="-",
        help="Action-request source file relative to project-dir, or '-' for stdin.",
    )
    rank_next = sub.add_parser(
        "rank-next-morphisms",
        help="Optionally summarize leaf-local visible morphisms for scratch planning.",
    )
    rank_next.add_argument(
        "--source",
        default="",
        help="Optional draft payload/receipt source relative to project-dir, or '-' for stdin.",
    )

    args = parser.parse_args(argv)
    project = Path(args.project_dir).resolve()
    started = time.monotonic()

    try:
        if args.command == "manifest":
            payload = _manifest(project)
        elif args.command == "probe-json":
            payload = _probe_json(
                project=project,
                artifact_refs=[str(ref) for ref in args.artifact],
                probe_py=sys.stdin.read() if args.probe_stdin else "",
                max_output_chars=max(1, int(args.max_output_chars)),
            )
        elif args.command == "check-worldmodel-carrier":
            payload = _check_worldmodel_carrier(project=project, source_ref=str(args.source))
        elif args.command == "score-worldmodel-candidate":
            payload = _score_worldmodel_candidate(project=project, source_ref=str(args.source))
        elif args.command == "check-receipt":
            payload = _check_receipt(
                project=project,
                source_ref=str(args.source),
                kind=str(args.kind),
            )
        elif args.command == "route-action":
            payload = _route_action(project=project, source_ref=str(args.source))
        elif args.command == "run-action":
            payload = _run_action(project=project, source_ref=str(args.source))
        elif args.command == "rank-next-morphisms":
            payload = _rank_next_morphisms(project=project, source_ref=str(args.source))
        else:  # pragma: no cover - argparse enforces this.
            raise ValueError(f"unsupported command: {args.command}")
    except Exception as exc:  # noqa: BLE001
        payload = {
            "schema": SCHEMA,
            "status": "error",
            "command": args.command,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        payload.setdefault("duration_ms", round((time.monotonic() - started) * 1000, 3))
        _attach_persistent_receipt(project=project, payload=payload)
        print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
        return 1

    payload.setdefault("duration_ms", round((time.monotonic() - started) * 1000, 3))
    _attach_persistent_receipt(project=project, payload=payload)
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
    return 0 if payload.get("status") in {"ok", "pass"} else 1


def _attach_persistent_receipt(*, project: Path, payload: dict[str, Any]) -> None:
    command = str(payload.get("command") or payload.get("capability_id") or "receipt")
    if command == "manifest":
        return
    try:
        base = dict(payload)
        base.pop("persistent_receipt", None)
        data = json.dumps(base, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        safe_command = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in command)[:80] or "receipt"
        rel = Path("workspace") / "visible_cli_receipts" / f"{safe_command}_{digest[:16]}.json"
        path = project / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json.dumps(base, indent=2, sort_keys=True, default=str).encode("utf-8") + b"\n")
        persistent = {
            "ref": str(rel),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "content_sha256": digest,
            "bytes": path.stat().st_size,
        }
        payload.setdefault("activity_meter", summarize_activity_spend([base]))
        payload["persistent_receipt"] = persistent
        nested = payload.get("receipt")
        nested_payload = nested.get("payload") if isinstance(nested, dict) else None
        if isinstance(nested_payload, dict):
            input_hashes = nested_payload.setdefault("input_hashes", {})
            if isinstance(input_hashes, dict):
                input_hashes.setdefault("receipt_ref", persistent["ref"])
                input_hashes.setdefault("receipt_sha256", persistent["sha256"])
            nested_payload.setdefault("output_ref", persistent["ref"])
            nested_payload.setdefault("output_sha256", persistent["sha256"])
    except OSError:
        payload["persistent_receipt"] = {
            "status": "unavailable",
            "reason": "receipt_path_not_writable",
        }


def _manifest(project: Path | None = None) -> dict[str, Any]:
    return manifest_payload(project=project)


def manifest_payload(*, project: Path | None = None) -> dict[str, Any]:
    routes = visible_workbench_capability_routes()
    in_turn_routes = visible_workbench_action_routes()
    parent_routes = visible_workbench_parent_kernel_routes()
    task_scope: frozenset[str] = frozenset()
    task: dict[str, Any] = {}
    if project is not None:
        from ztare.common.leaf_workbench_executor import (
            active_workbench_task_capability_scope,
            workbench_task_operational_exit_capability_ids,
        )

        task_scope, task = active_workbench_task_capability_scope(project)
    if task_scope:
        operational = set(workbench_task_operational_exit_capability_ids())
        allowed = set(task_scope) | operational
        routes = {key: value for key, value in routes.items() if key in allowed}
        in_turn_routes = {
            key: value for key, value in in_turn_routes.items() if key in allowed
        }
        parent_routes = {
            key: value for key, value in parent_routes.items() if key in allowed
        }
    payload = {
        "schema": SCHEMA,
        "status": "ok",
        "commands": [
            {
                "command": "probe-json",
                "authority": "pure_diagnostic",
                "secret_policy": "public_only",
                "input": ["--artifact <visible-json-ref>", "--probe-stdin"],
                "output": "JSON receipt with artifact hashes and result_summary",
            },
            {
                "command": "check-worldmodel-carrier",
                "authority": "pure_diagnostic",
                "secret_policy": "public_only",
                "input": ["--source <visible-file-or-stdin>"],
                "output": "JSON receipt for carrier purity and replay-index admissibility",
            },
            {
                "command": "score-worldmodel-candidate",
                "authority": "scorer",
                "secret_policy": "sealed_aggregate_only",
                "input": ["--source <visible-file-or-stdin>"],
                "output": "JSON receipt with aggregate candidate-delta preflight result",
            },
            {
                "command": "check-receipt",
                "authority": "pure_diagnostic",
                "secret_policy": "public_only",
                "input": ["--kind auto|worldmodel-payload|leaf-workbench|strategy-discharge", "--source <visible-file-or-stdin>"],
                "output": "JSON receipt with compatibility errors and repair hints",
            },
            {
                "command": "route-action",
                "authority": "pure_diagnostic",
                "secret_policy": "public_only",
                "input": ["--source <visible-file-or-stdin>"],
                "output": (
                    "JSON route: in_turn_cli for leaf-local diagnostics, "
                    "parent_kernel for registered authority actions, "
                    "capability_proposal for meta-tool work, or "
                    "invalid_action_request with repair hint"
                ),
            },
            {
                "command": "run-action",
                "authority": "registered_action_declared_by_adapter",
                "secret_policy": "contract_declared",
                "input": ["--source <visible-file-or-stdin>"],
                "output": "JSON receipt for registered local adapter actions only",
            },
        ],
        "capability_routes": routes,
        "in_turn_capability_routes": in_turn_routes,
        "parent_kernel_capability_routes": parent_routes,
        "authority_boundary": (
            "This CLI reads only staged visible artifacts or stdin. Hidden holdout, "
            "promotion gates, and live environment actions remain outside this surface."
        ),
        "persistent_receipts": (
            "Every non-manifest command also writes a content-addressed JSON receipt under "
            "workspace/visible_cli_receipts/ and returns persistent_receipt.ref. "
            "Use those refs as probe-json artifacts when composing visible evidence locally."
        ),
    }
    if task_scope:
        payload["active_task_scope"] = {
            "task_id": str(task.get("task_id") or ""),
            "admissible_evidence_capability_ids": sorted(task_scope),
            "operational_exit_capability_ids": sorted(
                set(routes).intersection(operational)
            ),
        }
        payload["commands"] = [
            row
            for row in payload["commands"]
            if row["command"] != "probe-json"
            or "run_visible_json_probe" in task_scope
        ]
    return payload


def _active_task_scope_error(project: Path, capability_id: str) -> str | None:
    from ztare.common.leaf_workbench_executor import (
        active_workbench_task_scope_error,
    )

    return active_workbench_task_scope_error(project, capability_id)


def _probe_json(
    *,
    project: Path,
    artifact_refs: list[str],
    probe_py: str,
    max_output_chars: int,
) -> dict[str, Any]:
    scope_error = _active_task_scope_error(project, "run_visible_json_probe")
    if scope_error:
        raise ValueError(scope_error)
    result = run_visible_json_probe(
        project_dir=project,
        artifact_refs=artifact_refs,
        probe_py=probe_py,
        max_output_chars=max_output_chars,
    )
    return {
        "schema": SCHEMA,
        "status": "ok",
        "capability_id": "run_visible_json_probe",
        "authority": "pure_diagnostic",
        "secret_policy": "public_only",
        "input_hashes": {
            "artifact_hashes": result.get("artifact_hashes") or {},
            "probe_sha256": result.get("probe_sha256") or "",
        },
        "result_summary": result.get("result_summary") or "",
        "result": result.get("result"),
        "receipt": {
            "type": "LEAF_WORKBENCH_RECEIPT",
            "payload": {
                "capability_id": "run_visible_json_probe",
                "input_hashes": {
                    "artifact_hashes": result.get("artifact_hashes") or {},
                    "probe_sha256": result.get("probe_sha256") or "",
                },
                "output_summary": result.get("result_summary") or "",
                "claim_bindings": ["visible CLI probe over staged artifacts"],
            },
        },
    }


def _check_worldmodel_carrier(*, project: Path, source_ref: str) -> dict[str, Any]:
    source, label = _read_source(project=project, source_ref=source_ref)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    try:
        authority_project = _authority_project_for_aggregate(project)
    except ValueError:
        authority_project = project
    dynamics_assumption = project_dynamics_assumption(authority_project)
    error = carrier_contract_error(
        source,
        dynamics_assumption=dynamics_assumption,
    )
    status = "pass" if error is None else "fail"
    return {
        "schema": SCHEMA,
        "status": status,
        "capability_id": "check_worldmodel_carrier_contract",
        "authority": "pure_diagnostic",
        "secret_policy": "public_only",
        "input_hashes": {
            "source_ref": label,
            "source_sha256": digest,
            "dynamics_assumption": dynamics_assumption or "markovian",
            "authority_project_ref": str(authority_project),
        },
        "output_summary": "carrier contract passed" if error is None else error,
        "error": error,
        "receipt": {
            "type": "LEAF_WORKBENCH_RECEIPT",
            "payload": {
                "capability_id": "check_worldmodel_carrier_contract",
                "input_hashes": {
                    "source_ref": label,
                    "source_sha256": digest,
                    "dynamics_assumption": dynamics_assumption or "markovian",
                    "authority_project_ref": str(authority_project),
                },
                "output_summary": "carrier contract passed" if error is None else error,
                "claim_bindings": ["visible CLI carrier contract check"],
            },
        },
    }


def _score_worldmodel_candidate(*, project: Path, source_ref: str) -> dict[str, Any]:
    source, label = _read_source(project=project, source_ref=source_ref)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    try:
        authority_project = _authority_project_for_aggregate(project)
        receipt = _score_worldmodel_candidate_against_project(
            visible_project=project,
            authority_project=authority_project,
            source=source,
            source_ref=label,
            source_sha256=digest,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "schema": SCHEMA,
            "status": "fail",
            "capability_id": "score_worldmodel_candidate_delta",
            "authority": "scorer",
            "secret_policy": "sealed_aggregate_only",
            "input_hashes": {
                "source_ref": label,
                "source_sha256": digest,
            },
            "output_summary": f"candidate scoring failed: {type(exc).__name__}: {exc}",
            "error": str(exc),
        }
    return {
        "schema": SCHEMA,
        "status": "ok",
        "capability_id": "score_worldmodel_candidate_delta",
        "authority": "scorer",
        "secret_policy": "sealed_aggregate_only",
        "input_hashes": {
            "source_ref": label,
            "source_sha256": digest,
        },
        "output_summary": str(receipt.get("output_summary") or ""),
        "receipt": {"type": "LEAF_WORKBENCH_RECEIPT", "payload": receipt},
    }


def _authority_project_for_aggregate(visible_project: Path) -> Path:
    manifest = _load_visible_manifest(visible_project)
    raw = str(manifest.get("authority_project_path") or "").strip()
    if raw:
        path = Path(raw).resolve()
        if (path / "gate_harness.py").exists():
            return path
    source_repo = str(manifest.get("source_repo_path") or "").strip()
    project_ref = str(manifest.get("authority_project_ref") or "").strip()
    if source_repo and project_ref:
        path = (Path(source_repo) / project_ref).resolve()
        if (path / "gate_harness.py").exists():
            return path
    if (visible_project / "gate_harness.py").exists():
        return visible_project
    raise ValueError(
        "visible workbench is not bound to an authority project with gate_harness.py"
    )


def _load_visible_manifest(visible_project: Path) -> dict[str, Any]:
    for name in ("MANIFEST.json", "visible_manifest.json"):
        path = visible_project / name
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8") or "{}")
        if isinstance(payload, dict):
            return payload
    return {}


def _score_worldmodel_candidate_against_project(
    *,
    visible_project: Path,
    authority_project: Path,
    source: str,
    source_ref: str,
    source_sha256: str,
) -> dict[str, Any]:
    from ztare.worldmodel.leaf_workbench import (
        WORLD_MODEL_LEAF_WORKBENCH_CONTRACT,
        score_worldmodel_candidate_delta,
    )

    with tempfile.TemporaryDirectory(prefix="ztare_visible_candidate_score_") as tmp:
        candidate_path = Path(tmp) / f"{source_sha256}.py"
        candidate_path.write_text(source, encoding="utf-8")
        summary = score_worldmodel_candidate_delta(
            authority_project,
            candidate_path,
            candidate_sha256=source_sha256,
            include_diagnostics=True,
            workspace_cache_dir=(
                visible_project / "workspace" / "gate_result_cache"
            ),
        )
    for key in ("candidate_regression_receipt", "counterexample_trace"):
        if key in summary:
            summary[key] = _bounded_json_object(summary[key])
    return {
        "capability_id": "score_worldmodel_candidate_delta",
        "claim_bindings": ["visible CLI candidate-delta score"],
        "contract_sha256": WORLD_MODEL_LEAF_WORKBENCH_CONTRACT.fingerprint(),
        "input_hashes": {
            "source_ref": source_ref,
            "source_sha256": source_sha256,
            "authority_project_ref": str(authority_project),
            "gate_harness_sha256": hashlib.sha256(
                (authority_project / "gate_harness.py").read_bytes()
            ).hexdigest(),
        },
        "output_summary": json.dumps(summary, sort_keys=True, separators=(",", ":"), default=str),
    }


def _bounded_json_object(value: Any, *, max_chars: int | None = None) -> Any:
    if not isinstance(value, dict):
        return {}
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    if max_chars is None:
        max_chars = _visible_cli_max_embedded_json_chars()
    if len(text) > max_chars:
        return {
            "truncated": True,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "preview": text[:max_chars],
        }
    return value


def _visible_cli_max_embedded_json_chars() -> int:
    raw = os.environ.get("ZTARE_VISIBLE_CLI_MAX_EMBEDDED_JSON_CHARS", "200000")
    try:
        parsed = int(raw)
    except ValueError:
        return 200_000
    return max(1, parsed)


def _json_object(raw: Any) -> Any:
    if isinstance(raw, (dict, list)):
        return raw
    if not isinstance(raw, str):
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _check_receipt(*, project: Path, source_ref: str, kind: str) -> dict[str, Any]:
    source, label = _read_source(project=project, source_ref=source_ref)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    detected = _detect_receipt_kind(source, preferred=kind)
    errors: list[str] = []
    repair_hints: list[str] = []
    normalized: Any = None
    validator = ""

    try:
        if detected == "worldmodel-payload":
            from ztare.validator.worldmodel_typed_payload import (
                parse_worldmodel_typed_payload_text,
                render_worldmodel_typed_payload,
            )

            parsed = parse_worldmodel_typed_payload_text(source)
            errors.extend(worldmodel_payload_context_errors(project, parsed))
            validator = "worldmodel_typed_payload"
            normalized = {
                "payload_keys": sorted(parsed.keys()),
                "rendered_sha256": hashlib.sha256(
                    render_worldmodel_typed_payload(parsed).encode("utf-8")
                ).hexdigest(),
                "validator": validator,
            }
        elif detected == "leaf-workbench":
            from ztare.common.leaf_workbench_contract import (
                validate_leaf_workbench_receipt,
            )

            payload = _extract_receipt_payload(source, "LEAF_WORKBENCH_RECEIPT:")
            normalized = validate_leaf_workbench_receipt(payload)
        elif detected == "strategy-discharge":
            payload = _extract_receipt_payload(source, "STRATEGY_CARD_DISCHARGE:")
            errors.extend(_strategy_discharge_errors(payload))
            normalized = payload
        else:
            errors.append("Unable to detect receipt kind.")
            repair_hints.append(
                "Pass --kind worldmodel-payload, --kind leaf-workbench, or --kind strategy-discharge."
            )
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))

    if errors and not repair_hints:
        repair_hints.extend(_repair_hints_for_errors(errors, detected))
    status = "pass" if not errors else "fail"
    return {
        "schema": SCHEMA,
        "status": status,
        "capability_id": "check_receipt_compatibility",
        "authority": "pure_diagnostic",
        "secret_policy": "public_only",
        "input_hashes": {
            "source_ref": label,
            "source_sha256": digest,
            "kind": detected,
        },
        "output_summary": "receipt compatibility passed" if not errors else "; ".join(errors)[:1000],
        "errors": errors,
        "error_classes": _error_classes(errors),
        "repair_hints": repair_hints,
        "normalized": normalized,
        "validator": validator or detected,
        "receipt": {
            "type": "LEAF_WORKBENCH_RECEIPT",
            "payload": {
                "capability_id": "check_receipt_compatibility",
                "input_hashes": {
                    "source_ref": label,
                    "source_sha256": digest,
                    "kind": detected,
                },
                "output_summary": "receipt compatibility passed" if not errors else "; ".join(errors)[:1000],
                "claim_bindings": ["visible CLI receipt compatibility check"],
            },
        },
    }


def _rank_next_morphisms(*, project: Path, source_ref: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    source_sha256 = ""
    source_label = ""
    parse_error = ""
    if source_ref:
        source, source_label = _read_source(project=project, source_ref=source_ref)
        source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
        try:
            from ztare.validator.worldmodel_typed_payload import (
                parse_worldmodel_typed_payload_text,
            )

            payload = parse_worldmodel_typed_payload_text(source)
        except Exception as exc:  # noqa: BLE001
            parse_error = str(exc)
            payload = {}
    frontier = _visible_morphism_frontier(payload)
    yield_signal = _latest_information_yield_signal(project)
    ranked: list[dict[str, Any]] = []
    candidate_score_ref = _latest_candidate_score_receipt_ref(project)
    for idx, cap in enumerate(frontier["untried_refinement_morphisms"], start=1):
        route = frontier["routes"].get(cap) or {}
        action_request = _suggested_refinement_action_request(
            capability_id=cap,
            candidate_score_ref=candidate_score_ref,
        )
        ranked.append(
            {
                "rank": idx,
                "capability_id": cap,
                "route": route.get("route") or "in_turn_cli",
                "authority": route.get("authority") or "",
                "secret_policy": route.get("secret_policy") or "",
                "suggested_command": route.get("suggested_command") or [],
                "selection_basis": "available_refinement_morphism_after_candidate_feedback"
                if frontier["candidate_feedback_observed"]
                else "available_refinement_morphism",
                "route_reason": route.get("reason") or "",
                "suggested_action_request": action_request,
            }
        )
    frontier_state = "optional_frontier_available" if ranked else "no_optional_frontier"
    return {
        "schema": SCHEMA,
        "status": "ok",
        "capability_id": "rank_next_morphisms",
        "authority": "pure_diagnostic",
        "secret_policy": "public_only",
        "input_hashes": {
            "source_ref": source_label,
            "source_sha256": source_sha256,
            "latest_information_yield_sha256": yield_signal.get("sha256") or "",
        },
        "frontier_state": frontier_state,
        "stopping_state": frontier_state,
        "candidate_feedback_observed": frontier["candidate_feedback_observed"],
        "candidate_score_ref": candidate_score_ref,
        "attempted_morphisms": sorted(frontier["attempted"]),
        "ranked_morphisms": ranked,
        "loop_information_yield": yield_signal.get("payload") or {},
        "parse_error": parse_error,
        "output_summary": (
            "optional local morphism frontier available"
            if ranked
            else "no optional local morphism frontier"
        ),
        "receipt": {
            "type": "LEAF_WORKBENCH_RECEIPT",
            "payload": {
                "capability_id": "rank_next_morphisms",
                "input_hashes": {
                    "source_ref": source_label,
                    "source_sha256": source_sha256,
                    "latest_information_yield_sha256": yield_signal.get("sha256") or "",
                },
                "output_summary": (
                    "optional local morphism frontier available"
                    if ranked
                    else "no optional local morphism frontier"
                ),
                "claim_bindings": ["visible CLI local morphism frontier"],
            },
        },
    }


def _latest_candidate_score_receipt_ref(project: Path) -> str:
    root = project / "workspace" / "visible_cli_receipts"
    if not root.is_dir():
        return ""
    candidates = sorted(
        root.glob("score_worldmodel_candidate_delta_*.json"),
        key=lambda path: path.stat().st_mtime if path.exists() else 0.0,
        reverse=True,
    )
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        summary = payload.get("output_summary")
        if isinstance(summary, str) and "candidate_regression_receipt" in summary:
            try:
                return str(path.relative_to(project))
            except ValueError:
                return str(path)
    return ""


def _suggested_refinement_action_request(
    *,
    capability_id: str,
    candidate_score_ref: str,
) -> dict[str, Any]:
    input_refs: dict[str, Any] = {}
    if candidate_score_ref and capability_id in {
        "inspect_worldmodel_counterexample_context",
        "mine_worldmodel_lowerable_selectors",
        "mine_worldmodel_separating_features",
    }:
        input_refs["score_receipt_ref"] = candidate_score_ref
        input_refs["latest_regression_ref"] = candidate_score_ref
    return {
        "type": "LEAF_WORKBENCH_ACTION_REQUEST",
        "payload": {
            "capability_id": capability_id,
            "input_refs": input_refs,
        },
    }


def _latest_information_yield_signal(project: Path) -> dict[str, Any]:
    candidates = [
        project / "workspace" / "latest_information_yield.json",
        project / "latest_information_yield.json",
    ]
    for path in candidates:
        if not path.exists() or not path.is_file():
            continue
        try:
            data = path.read_bytes()
            payload = json.loads(data.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        try:
            source_ref = str(path.relative_to(project))
        except ValueError:
            source_ref = str(path)
        return {
            "source_ref": source_ref,
            "sha256": hashlib.sha256(data).hexdigest(),
            "payload": payload,
        }
    return {}


def _visible_morphism_frontier(payload: dict[str, Any]) -> dict[str, Any]:
    attempted: set[str] = set()
    candidate_feedback_observed = False
    receipts = payload.get("control_receipts")
    if isinstance(receipts, list):
        for row in receipts:
            if not isinstance(row, dict):
                continue
            receipt_type = str(row.get("type") or "").strip()
            data = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            if receipt_type == "LOWERABILITY_BLOCKED":
                if data.get("candidate_family_attempted"):
                    candidate_feedback_observed = True
                visible = data.get("visible_capabilities_attempted")
                if isinstance(visible, list):
                    attempted.update(_capability_mentions(visible))
                    if "score_worldmodel_candidate_delta" in attempted:
                        candidate_feedback_observed = True
                ruled_out = data.get("ruled_out_visible_morphisms")
                if isinstance(ruled_out, list):
                    attempted.update(_capability_mentions(ruled_out))
            if receipt_type == "LEAF_WORKBENCH_RECEIPT":
                cap = str(data.get("capability_id") or "").strip()
                if cap:
                    attempted.add(cap)
                summary = _json_object(data.get("output_summary"))
                if isinstance(summary, dict):
                    if str(summary.get("status") or "") == "candidate_preflight_failed":
                        candidate_feedback_observed = True
                    if summary.get("candidate_delta_admissible") is False:
                        candidate_feedback_observed = True
    routes = visible_workbench_in_turn_routes()
    refinement = [
        cap for cap in sorted(routes) if _is_refinement_morphism(cap)
    ]
    return {
        "attempted": attempted,
        "routes": routes,
        "candidate_feedback_observed": candidate_feedback_observed,
        "untried_refinement_morphisms": [
            cap for cap in refinement if cap not in attempted
        ],
    }


def worldmodel_payload_context_errors(project: Path, payload: dict[str, Any]) -> list[str]:
    """Validate consumer-indexed evidence claims against typed input receipts."""

    source_refs = _visible_source_fiber_refs(project)
    errors: list[str] = []
    receipts = payload.get("control_receipts")
    if not isinstance(receipts, list):
        return errors
    for row in receipts:
        if not isinstance(row, dict) or str(row.get("type") or "").strip() != "LOWERABILITY_BLOCKED":
            continue
        data = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        refs = data.get("evidence_refs")
        if not isinstance(refs, list):
            continue
        bad_refs = [
            ref for ref in (str(item or "").strip() for item in refs)
            if ref and _is_source_fiber_ref(ref, source_refs)
        ]
        if bad_refs:
            errors.append(
                "LOWERABILITY_BLOCKED evidence_refs must cite observed receipts or visible evidence, "
                "not source-fiber files reserved for meta/tool proposals; "
                f"source_fiber_refs={','.join(bad_refs[:6])}"
            )
        consumed = {
            _canonical_evidence_ref(item.get("ref"))
            for item in data.get("evidence_statuses") or []
            if isinstance(item, dict)
            and str(item.get("status") or "") == "consumed_counterexample"
            and _canonical_evidence_ref(item.get("ref"))
        }
        analysis_refs = [
            _canonical_evidence_ref(ref)
            for ref in data.get("evidence_analysis_refs") or []
            if _canonical_evidence_ref(ref)
        ]
        bound_inputs: set[str] = set()
        for ref in analysis_refs:
            receipt = _read_context_artifact(project, ref)
            if isinstance(receipt, dict):
                bound_inputs.update(_typed_receipt_input_refs(receipt))
        unbound = sorted(consumed - bound_inputs)
        if unbound:
            errors.append(
                "LOWERABILITY_BLOCKED marks evidence as consumed without a cited "
                "analysis receipt whose typed input hashes bind it; "
                f"unbound_consumed_refs={','.join(unbound[:6])}"
            )
    return errors


def _canonical_evidence_ref(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/").split("#", 1)[0]


def _read_context_artifact(project: Path, ref: str) -> Any:
    roots = [project]
    try:
        roots.append(_authority_project_for_aggregate(project))
    except ValueError:
        pass
    for root in dict.fromkeys(path.resolve() for path in roots):
        path = (root / ref).resolve()
        try:
            path.relative_to(root)
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError, json.JSONDecodeError):
            continue
    return None


def _typed_receipt_input_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        hashes = value.get("input_hashes")
        if isinstance(hashes, dict):
            source_ref = _canonical_evidence_ref(hashes.get("source_ref"))
            if source_ref:
                refs.add(source_ref)
            artifact_hashes = hashes.get("artifact_hashes")
            if isinstance(artifact_hashes, dict):
                refs.update(
                    ref
                    for item in artifact_hashes
                    if (ref := _canonical_evidence_ref(item))
                )
        for item in value.values():
            refs.update(_typed_receipt_input_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.update(_typed_receipt_input_refs(item))
    return refs


def _visible_source_fiber_refs(project: Path) -> set[str]:
    refs: set[str] = set()
    for name in ("MANIFEST.json", "visible_manifest.json"):
        path = project / name
        if not path.is_file():
            continue
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        artifacts = manifest.get("visible_artifacts")
        if not isinstance(artifacts, list):
            continue
        for row in artifacts:
            if not isinstance(row, dict):
                continue
            if str(row.get("authority_level") or "") != "visible_diagnostic_tool_source":
                continue
            ref = str(row.get("ref") or "").strip()
            if ref:
                refs.add(ref)
    return refs


def _is_source_fiber_ref(ref: str, manifest_source_refs: set[str]) -> bool:
    normalized = ref.strip().replace("\\", "/")
    if normalized in manifest_source_refs:
        return True
    # Manifest absence should fail closed for repo-source citations in science
    # blockers: source files can guide meta proposals, but are not observations.
    return normalized.startswith("src/ztare/")


def _capability_mentions(values: list[Any]) -> set[str]:
    known = set(visible_workbench_capability_routes())
    mentions: set[str] = set()
    for value in values:
        text = str(value or "")
        for cap in known:
            if cap in text:
                mentions.add(cap)
        if text.startswith("score-worldmodel-candidate"):
            mentions.add("score_worldmodel_candidate_delta")
        elif text.startswith("check-worldmodel-carrier"):
            mentions.add("check_worldmodel_carrier_contract")
        elif text.startswith("probe-json"):
            mentions.add("run_visible_json_probe")
        elif text.startswith("check-receipt"):
            mentions.add("check_receipt_compatibility")
    return mentions


def _is_refinement_morphism(capability_id: str) -> bool:
    lowered = capability_id.lower()
    tokens = ("mine_", "_miner", "separating", "selector", "counterexample_context")
    return any(token in lowered for token in tokens)


def _error_classes(errors: list[str]) -> list[str]:
    classes: list[str] = []
    for error in errors:
        text = str(error)
        if "LEAF_WORKBENCH_CAPABILITY_PROPOSAL" in text:
            classes.append("malformed_capability_proposal")
        elif "LOWERABILITY_BLOCKED" in text:
            classes.append("malformed_lowerability_blocked")
        elif "LEAF_WORKBENCH_ACTION_REQUEST" in text:
            classes.append("malformed_action_request")
        elif "test_model_py" in text or "carrier" in text:
            classes.append("malformed_candidate_carrier")
        elif "STRATEGY_CARD_DISCHARGE" in text:
            classes.append("malformed_strategy_discharge")
        else:
            classes.append("unknown")
    return sorted(set(classes))


def _route_action(*, project: Path, source_ref: str) -> dict[str, Any]:
    source, label = _read_source(project=project, source_ref=source_ref)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    payload = _parse_action_request_source(source)
    route = route_visible_workbench_action_request(payload)
    scope_error = _active_task_scope_error(
        project,
        str(route.get("capability_id") or ""),
    )
    if scope_error:
        return {
            "schema": SCHEMA,
            "status": "fail",
            "capability_id": route.get("capability_id") or "",
            "authority": "pure_diagnostic",
            "secret_policy": "public_only",
            "input_hashes": {"source_ref": label, "source_sha256": digest},
            "output_summary": scope_error,
            "route": {**route, "route": "blocked_by_active_task_scope"},
        }
    return {
        "schema": SCHEMA,
        "status": route.get("status") or ("fail" if route.get("route") == "invalid_action_request" else "ok"),
        "capability_id": route["capability_id"],
        "authority": "pure_diagnostic",
        "secret_policy": "public_only",
        "input_hashes": {
            "source_ref": label,
            "source_sha256": digest,
        },
        "output_summary": f"{route['capability_id']} routes to {route['route']}: {route['reason']}",
        "route": route,
    }


def _run_action(*, project: Path, source_ref: str) -> dict[str, Any]:
    source, label = _read_source(project=project, source_ref=source_ref)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    payload = _parse_action_request_source(source)
    route = route_visible_workbench_action_request(payload)
    if route.get("route") != "in_turn_cli":
        return {
            "schema": SCHEMA,
            "status": "fail",
            "capability_id": route.get("capability_id") or "",
            "authority": "pure_diagnostic",
            "secret_policy": "public_only",
            "input_hashes": {
                "source_ref": label,
                "source_sha256": digest,
            },
            "output_summary": (
                f"action routes to {route.get('route')}: {route.get('reason')}; "
                "do not execute it in the visible CLI"
            ),
            "route": route,
        }
    req = _normalize_action_request_payload(payload)
    cap = str(req.get("capability_id") or "").strip()
    scope_error = _active_task_scope_error(project, cap)
    if scope_error:
        return {
            "schema": SCHEMA,
            "status": "fail",
            "capability_id": cap,
            "authority": "pure_diagnostic",
            "secret_policy": "public_only",
            "input_hashes": {
                "source_ref": label,
                "source_sha256": digest,
            },
            "output_summary": scope_error,
            "route": {**route, "route": "blocked_by_active_task_scope"},
        }
    if cap in {
        "run_visible_json_probe",
        "check_worldmodel_carrier_contract",
        "check_receipt_compatibility",
        "score_worldmodel_candidate_delta",
    }:
        return {
            "schema": SCHEMA,
            "status": "fail",
            "capability_id": cap,
            "authority": "pure_diagnostic",
            "secret_policy": "public_only",
            "input_hashes": {
                "source_ref": label,
                "source_sha256": digest,
            },
            "output_summary": (
                f"{cap} has a dedicated CLI command; use manifest for the exact command"
            ),
            "route": route,
        }
    try:
        from ztare.worldmodel.leaf_workbench import worldmodel_leaf_workbench_action_environment

        env = worldmodel_leaf_workbench_action_environment()
        local_cli_actions = {str(item) for item in (env.get("local_cli_actions") or ()) if str(item)}
        handlers = env.get("action_handlers") or {}
        contract = env["contract"]
        if cap not in local_cli_actions or cap not in handlers:
            raise ValueError(f"{cap} is not registered for visible local execution")
        action_project = project
        authority_binding: dict[str, Any] = {}
        if cap in _AUTHORITY_DERIVED_ACTIONS:
            action_project, authority_binding = _authority_project_for_derived_action(
                visible_project=project,
                capability_id=cap,
                request=req,
            )
        receipt = handlers[cap](action_project, req, None, contract)
        if authority_binding:
            receipt.setdefault("input_hashes", {}).update(authority_binding)
    except Exception as exc:  # noqa: BLE001
        return {
            "schema": SCHEMA,
            "status": "fail",
            "capability_id": cap,
            "authority": "pure_diagnostic",
            "secret_policy": "public_only",
            "input_hashes": {
                "source_ref": label,
                "source_sha256": digest,
            },
            "output_summary": f"{cap} local execution failed: {type(exc).__name__}: {exc}",
            "route": route,
        }
    receipt.setdefault("capability_id", cap)
    receipt.setdefault("claim_bindings", req.get("claim_bindings") or [f"visible local action {cap}"])
    receipt.setdefault("contract_sha256", contract.fingerprint())
    return {
        "schema": SCHEMA,
        "status": "ok",
        "capability_id": cap,
        "authority": route.get("authority") or "registered_action",
        "secret_policy": route.get("secret_policy") or "contract_declared",
        "input_hashes": {
            "source_ref": label,
            "source_sha256": digest,
        },
        "output_summary": str(receipt.get("output_summary") or ""),
        "route": route,
        "receipt": {"type": "LEAF_WORKBENCH_RECEIPT", "payload": receipt},
    }


def _authority_project_for_derived_action(
    *,
    visible_project: Path,
    capability_id: str,
    request: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    """Bind a registered derived query to manifest-visible authority bytes.

    Large evidence can be withheld from physical staging without becoming
    hidden evidence.  Only refs declared visible (or withheld solely for size)
    may cross this bridge; the registered handler returns a bounded receipt.
    """
    manifest = _load_visible_manifest(visible_project)
    authority_project = _authority_project_for_aggregate(visible_project)
    allowed = _manifest_visible_evidence_refs(manifest)
    requested = _derived_action_evidence_refs(capability_id, request)
    refs = request.get("input_refs") if isinstance(request.get("input_refs"), dict) else {}
    requested_holdout_role = capability_id == "contrast_worldmodel_episodes" and any(
        str(refs.get(key) or default).strip() == "holdout"
        for key, default in (("episode_ref_a", "visible"), ("episode_ref_b", "holdout"))
    )
    if requested_holdout_role:
        raise ValueError("derived action requested the withheld evidence role: holdout")
    denied = sorted(ref for ref in requested if _canonical_manifest_ref(ref) not in allowed)
    if denied:
        raise ValueError(
            "derived action requested evidence outside the manifest-visible set: "
            + ", ".join(denied)
        )
    manifest_path = visible_project / "MANIFEST.json"
    return authority_project, {
        "evidence_execution_mode": "authority_derived_query",
        "visible_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "authority_project_ref": str(manifest.get("authority_project_ref") or ""),
        "manifest_visible_evidence_refs": sorted(requested),
    }


def _manifest_visible_evidence_refs(manifest: dict[str, Any]) -> set[str]:
    allowed: set[str] = set()
    roles = manifest.get("episode_roles")
    roles = roles if isinstance(roles, dict) else {}
    holdout_refs = {
        _canonical_manifest_ref(str(ref))
        for ref in (
            roles.get("holdout"),
            manifest.get("holdout_episode"),
        )
        if ref
    }
    artifacts = manifest.get("visible_artifacts")
    if not isinstance(artifacts, list):
        return allowed
    for row in artifacts:
        if not isinstance(row, dict):
            continue
        visible = row.get("visible_status") == "visible"
        size_only = row.get("status") == "withheld" and row.get("reason") == "too_large"
        if not (visible or size_only):
            continue
        ref = _canonical_manifest_ref(str(row.get("ref") or ""))
        if ref and ref not in holdout_refs:
            allowed.add(ref)
    return allowed


def _canonical_manifest_ref(ref: str) -> str:
    text = str(ref or "").strip().split(":", 1)[0]
    aliases = {
        "visible": "raw/episodes/episode_001.jsonl",
        "holdout": "raw/episodes/episode_002.jsonl",
    }
    return aliases.get(text, text)


def _derived_action_evidence_refs(
    capability_id: str,
    request: dict[str, Any],
) -> set[str]:
    refs = request.get("input_refs") if isinstance(request.get("input_refs"), dict) else {}
    if capability_id == "inspect_worldmodel_counterexample_context":
        return {
            _canonical_manifest_ref(
                str(
                    refs.get("latest_regression_ref")
                    or refs.get("regression_ref")
                    or "workspace/latest_patch_base_regression.json"
                )
            ),
            "raw/episodes/episode_001.jsonl",
        }
    if capability_id in {
        "mine_worldmodel_separating_features",
        "mine_worldmodel_lowerable_selectors",
    }:
        return {
            _canonical_manifest_ref(
                str(
                    refs.get("latest_regression_ref")
                    or refs.get("regression_ref")
                    or "workspace/latest_patch_base_regression.json"
                )
            ),
            _canonical_manifest_ref(
                str(refs.get("episode_log_ref") or "raw/episodes/episode_001.jsonl")
            ),
        }
    if capability_id == "inspect_worldmodel_event_timeline":
        return {_canonical_manifest_ref(str(refs.get("episode_ref") or "visible"))}
    if capability_id == "contrast_worldmodel_episodes":
        return {
            _canonical_manifest_ref(str(refs.get("episode_ref_a") or "visible")),
            _canonical_manifest_ref(str(refs.get("episode_ref_b") or "holdout")),
        }
    return set()


def _normalize_action_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("type") == "LEAF_WORKBENCH_ACTION_REQUEST":
        nested = payload.get("payload")
        if not isinstance(nested, dict):
            raise ValueError("LEAF_WORKBENCH_ACTION_REQUEST requires object payload.")
        return dict(nested)
    return dict(payload)


def _parse_action_request_source(source: str) -> dict[str, Any]:
    text = source.strip()
    marker = "LEAF_WORKBENCH_ACTION_REQUEST:"
    if marker in text:
        text = text.split(marker, 1)[1].strip()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("LEAF_WORKBENCH_ACTION_REQUEST requires a JSON object.")
    return payload


def _detect_receipt_kind(source: str, *, preferred: str) -> str:
    if preferred != "auto":
        return preferred
    stripped = source.lstrip()
    if "STRATEGY_CARD_DISCHARGE:" in source:
        return "strategy-discharge"
    if "LEAF_WORKBENCH_RECEIPT:" in source:
        return "leaf-workbench"
    if stripped.startswith("{") and (
        "control_receipts" in source or "test_model_py" in source or "thesis_markdown" in source
    ):
        return "worldmodel-payload"
    return "unknown"


def _extract_receipt_payload(source: str, marker: str) -> dict[str, Any]:
    text = source.strip()
    if marker in text:
        text = text.split(marker, 1)[1].strip()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError(f"{marker.rstrip(':')} requires a JSON object.")
    return payload


def _strategy_discharge_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not str(payload.get("failure_family_sha") or payload.get("card_ref") or "").strip():
        errors.append("STRATEGY_CARD_DISCHARGE requires failure_family_sha or card_ref.")
    outcome = str(payload.get("outcome") or "").strip()
    if outcome not in {"satisfied", "refuted", "blocked"}:
        errors.append("STRATEGY_CARD_DISCHARGE outcome must be satisfied|refuted|blocked.")
    refs = payload.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        errors.append("STRATEGY_CARD_DISCHARGE requires non-empty evidence_refs list.")
    if outcome == "blocked" and not str(payload.get("blocker_kind") or "").strip():
        errors.append("blocked STRATEGY_CARD_DISCHARGE requires blocker_kind.")
    return errors


def _repair_hints_for_errors(errors: list[str], kind: str) -> list[str]:
    joined = " ".join(errors)
    hints: list[str] = []
    if "requires `capability_id`" in joined:
        hints.append("Add capability_id from the registered workbench capability that produced the receipt.")
    if "input_hashes" in joined:
        hints.append("Add input_hashes with visible artifact/ref hashes; do not use prose provenance only.")
    if "claim_bindings" in joined:
        hints.append("Add claim_bindings naming the exact candidate claim supported by the receipt.")
    if "output_ref" in joined or "output_summary" in joined:
        hints.append("Add output_ref for a persisted artifact or output_summary for the visible diagnostic result.")
    if "STRATEGY_CARD_DISCHARGE" in joined or kind == "strategy-discharge":
        hints.append("Use outcome satisfied|refuted|blocked plus evidence_refs; blocked receipts also need blocker_kind.")
    if not hints:
        hints.append("Normalize to the typed payload schema before final submission.")
    return hints


def _read_source(*, project: Path, source_ref: str) -> tuple[str, str]:
    if source_ref == "-":
        return sys.stdin.read(), "stdin"
    path = (project / source_ref).resolve()
    try:
        path.relative_to(project.resolve())
    except ValueError as exc:
        raise ValueError(f"source path escapes visible workbench: {source_ref}") from exc
    if not path.is_file():
        raise ValueError(f"source path does not exist: {source_ref}")
    return path.read_text(encoding="utf-8"), source_ref


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
