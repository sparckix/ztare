"""Public command surface for the composable PDE kernel."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from ztare.pde.engine import (
    PDEEstimateSkeletonOptions,
    PDEEngineContextRequest,
    PDELeafWorkOrderOptions,
    build_pde_engine_context,
)
from ztare.pde.architecture_requirements import (
    pde_kernel_architecture_requirements,
    pde_kernel_requirement_status_counts,
)
from ztare.pde.currency import pde_currency_ledger_template
from ztare.pde.estimates import generate_pde_estimate_skeletons
from ztare.pde.formal_surface_status import (
    build_pde_formal_surface_map,
    render_pde_formal_surface_map,
)
from ztare.pde.knowledge_service import build_pde_knowledge_context
from ztare.pde.ops import (
    all_pde_ops,
    deployable_pde_ops,
    pde_execution_template_for_ops,
    pde_op_by_id,
    portable_receipt_pde_ops,
    render_pde_ops_summary,
)
from ztare.pde.receipts import all_pde_receipt_entries
from ztare.pde.readiness import build_pde_kernel_readiness_receipt
from ztare.pde.canary import (
    build_pde_canary_reingestion_receipt,
    write_pde_failure_memory_jsonl,
)
from ztare.pde.completion_audit import build_pde_kernel_completion_audit
from ztare.pde.registry import (
    all_pde_gate_entries,
    entries_for_op,
    entry_by_gate_id,
)
from ztare.pde.work_order import (
    build_pde_leaf_work_order,
    render_pde_leaf_work_order,
)
from ztare.pde.gate_runner import run_pde_gate, run_pde_leaf_work_order_gates
from ztare.pde.subkernel import build_pde_subkernel_status


def _json_loads_object(raw: str, *, field_name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(
            f"{field_name} must be valid JSON: {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise argparse.ArgumentTypeError(f"{field_name} must decode to a JSON object")
    return value


def _json_loads_any(raw: str, *, field_name: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(
            f"{field_name} must be valid JSON: {exc.msg}"
        ) from exc


def _read_json_object(path: str, *, field_name: str) -> dict[str, Any]:
    try:
        if path == "-":
            raw = sys.stdin.read()
        else:
            with open(path, encoding="utf-8") as handle:
                raw = handle.read()
    except OSError as exc:
        raise argparse.ArgumentTypeError(
            f"{field_name} could not be read: {exc}"
        ) from exc
    return _json_loads_object(raw, field_name=field_name)


def _read_json_any(path: str, *, field_name: str) -> Any:
    try:
        if path == "-":
            raw = sys.stdin.read()
        else:
            with open(path, encoding="utf-8") as handle:
                raw = handle.read()
    except OSError as exc:
        raise argparse.ArgumentTypeError(
            f"{field_name} could not be read: {exc}"
        ) from exc
    return _json_loads_any(raw, field_name=field_name)


def _print_json(payload: Any) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _load_optional_json_object(path: str, *, field_name: str) -> dict[str, Any] | None:
    if not path:
        return None
    return _read_json_object(path, field_name=field_name)


def _cmd_gates(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde gates",
        description="List PDE kernel gate registry entries.",
    )
    parser.add_argument("--op", help="Filter gates by GP-219 op id such as pec_l")
    parser.add_argument("--gate-id", help="Return one gate by stable gate id")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    if ns.gate_id:
        entry = entry_by_gate_id(ns.gate_id)
        if entry is None:
            print(f"ztare pde: unknown gate id {ns.gate_id!r}", file=sys.stderr)
            return 2
        entries = [entry]
    elif ns.op:
        entries = entries_for_op(ns.op)
    else:
        entries = all_pde_gate_entries()

    if ns.json:
        return _print_json({"schema": "pde-gate-registry-v1", "entries": entries})

    for entry in entries:
        ops = ",".join(entry.get("requires_ops") or ()) or "-"
        tags = ",".join(entry.get("tags") or ()) or "-"
        print(
            f"{entry.get('gate_id')}  flag={entry.get('workbench_flag')}  "
            f"ops={ops}  tags={tags}"
        )
    return 0


def _cmd_status(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde status",
        description="Report PDE subkernel readiness and service boundaries.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    status = build_pde_subkernel_status()
    if ns.json:
        return _print_json(status)
    marker = "ready" if status["ready"] else "not-ready"
    print(f"PDE subkernel: {marker}")
    print(f"gates: {status['gate_count']}")
    if status["runner_import_errors"]:
        print("runner import errors:")
        for row in status["runner_import_errors"]:
            print(f"  - {row.get('gate_id')}: {row.get('error')}")
    print("service boundaries:")
    for boundary, items in status["service_boundaries"].items():
        print(f"  {boundary}: {', '.join(items)}")
    counts = status.get("architecture_requirement_status_counts") or {}
    if counts:
        print("architecture requirements:")
        for key, value in sorted(counts.items()):
            print(f"  {key}: {value}")
    return 0 if status["ready"] else 1


def _cmd_completion_audit(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde completion-audit",
        description=(
            "Run the executable PDE-kernel completion audit over registry, "
            "receipts, readiness canary, bundle summary, and boundaries."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default="",
        help="Optional repo root for source-boundary checks.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    audit = build_pde_kernel_completion_audit(repo_root=ns.repo_root or None)
    if ns.json:
        return _print_json(audit)
    marker = "PASS" if audit["passed"] else "FAIL"
    print(f"PDE kernel completion audit: {marker}")
    for row in audit.get("checks") or []:
        status = "PASS" if row.get("passed") else "FAIL"
        print(f"  {status} {row.get('check_id')}")
        if row.get("failure"):
            print(f"    {row.get('failure')}")
    return 0 if audit["passed"] else 1


def _cmd_requirements(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde requirements",
        description="Emit the PDE kernel architecture requirement matrix.",
    )
    parser.add_argument(
        "--requirement-id",
        default="",
        help="Return one requirement row by id.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    rows = pde_kernel_architecture_requirements()
    if ns.requirement_id:
        rows = [
            row for row in rows
            if row.get("requirement_id") == ns.requirement_id
        ]
        if not rows:
            print(
                f"ztare pde: unknown requirement id {ns.requirement_id!r}",
                file=sys.stderr,
            )
            return 2
    payload = {
        "schema": "pde-architecture-requirements-v1",
        "status_counts": pde_kernel_requirement_status_counts(),
        "requirements": rows,
    }
    if ns.json:
        return _print_json(payload)
    print("PDE architecture requirements:")
    for row in rows:
        print(
            f"  - {row.get('requirement_id')}  "
            f"status={row.get('status')} owner={row.get('boundary_owner')}"
        )
    return 0


def _cmd_readiness(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde readiness",
        description=(
            "Emit one PDE kernel readiness receipt, including the TICK669 "
            "annular Riesz/PSD-trace canary work order."
        ),
    )
    parser.add_argument(
        "--target",
        default="annular_bandlimited_riesz_l1_psd_trace_payment",
    )
    parser.add_argument("--op", default="pec_l", dest="op_id")
    parser.add_argument(
        "--goal",
        default="audit projection/cancellation currency",
    )
    parser.add_argument("--given-json", default="{}")
    parser.add_argument(
        "--extra-gate",
        action="append",
        default=[],
        help=(
            "Override additional stable gate ids for the canary work order. "
            "May be repeated."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    try:
        given = _json_loads_object(ns.given_json, field_name="--given-json")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    kwargs: dict[str, Any] = {
        "target": ns.target,
        "op_id": ns.op_id,
        "goal": ns.goal,
    }
    if given:
        kwargs["given"] = given
    if ns.extra_gate:
        kwargs["extra_gate_ids"] = tuple(ns.extra_gate)
    receipt = build_pde_kernel_readiness_receipt(**kwargs)
    if ns.json:
        return _print_json(receipt)
    print(f"PDE kernel readiness: {'PASS' if receipt['ready'] else 'FAIL'}")
    print(f"target: {receipt['target']}")
    print(f"gates: {receipt['gate_count']}")
    print(f"receipts: {receipt['receipt_count']}")
    print("scoreboard:")
    for key, value in receipt["scoreboard"].items():
        print(f"  {key}: {'PASS' if value else 'FAIL'}")
    return 0 if receipt["ready"] else 1


def _cmd_ops(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde ops",
        description="List GP-219 PDE operation cards and execution templates.",
    )
    parser.add_argument("--op", help="Return one operation by id such as pec_l")
    parser.add_argument("--deployable", action="store_true")
    parser.add_argument("--portable-receipts", action="store_true")
    parser.add_argument(
        "--template-for",
        action="append",
        default=[],
        help="Operation id for an execution template. May be repeated.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    if ns.template_for:
        payload = {
            "schema": "pde-op-execution-template-v1",
            "template": pde_execution_template_for_ops(ns.template_for),
        }
    elif ns.op:
        op = pde_op_by_id(ns.op)
        if op is None:
            print(f"ztare pde: unknown op id {ns.op!r}", file=sys.stderr)
            return 2
        payload = {"schema": "pde-op-registry-v1", "entries": [op]}
    elif ns.deployable:
        payload = {"schema": "pde-op-registry-v1", "entries": deployable_pde_ops()}
    elif ns.portable_receipts:
        payload = {
            "schema": "pde-op-registry-v1",
            "entries": portable_receipt_pde_ops(),
        }
    else:
        payload = {"schema": "pde-op-registry-v1", "entries": all_pde_ops()}

    if ns.json:
        return _print_json(payload)
    if ns.template_for:
        templates = payload["template"].get("base_work_unit_templates") or {}
        for unit_type, unit in sorted(templates.items()):
            print(f"{unit_type}: {', '.join(unit.get('required_fields') or [])}")
        return 0
    if ns.op or ns.deployable or ns.portable_receipts:
        for entry in payload["entries"]:
            print(f"{entry.get('op_id')}  {entry.get('name')}  tier={entry.get('tier')}")
        return 0
    print(render_pde_ops_summary())
    return 0


def _cmd_currency(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde currency",
        description="Emit the PDE proof-currency ledger template.",
    )
    parser.add_argument("--target-currency", default="")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    payload = pde_currency_ledger_template(ns.target_currency or None)
    if ns.json:
        return _print_json(payload)
    print(f"PDE currency ledger: {payload.get('target_currency') or 'all'}")
    print("exchange-rate obligations:")
    for key in sorted((payload.get("exchange_rate_obligations") or {}).keys()):
        print(f"  - {key}")
    return 0


def _cmd_estimates(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde estimates",
        description="Generate PDE estimate skeletons through the kernel facade.",
    )
    parser.add_argument("--target", required=True)
    parser.add_argument("--field", default="")
    parser.add_argument("--gap-type", default="")
    parser.add_argument("--context-json", default="{}")
    parser.add_argument("--candidate-inequality", action="append", default=[])
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    try:
        context = _json_loads_object(ns.context_json, field_name="--context-json")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    skeletons = generate_pde_estimate_skeletons(
        target=ns.target,
        field=ns.field,
        gap_type=ns.gap_type,
        context=context,
        inequalities=ns.candidate_inequality,
    )
    payload = {
        "schema": "pde-estimate-skeletons-v1",
        "target": ns.target,
        "skeletons": skeletons,
    }
    if ns.json:
        return _print_json(payload)
    print(f"PDE estimate skeletons: {len(skeletons)}")
    for skeleton in skeletons:
        print(f"  - {skeleton.get('id')}: {skeleton.get('target')}")
    return 0


def _cmd_receipts(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde receipts",
        description="List PDE receipt registry entries.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    payload = {
        "schema": "pde-receipt-registry-v1",
        "entries": all_pde_receipt_entries(),
    }
    if ns.json:
        return _print_json(payload)
    for entry in payload["entries"]:
        print(f"{entry.get('receipt_id')}  kind={entry.get('kind')}")
    return 0


def _cmd_run_gate(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde run-gate",
        description="Run one PDE registry gate against a JSON payload.",
    )
    parser.add_argument("--gate-id", required=True)
    parser.add_argument(
        "--payload-json",
        required=True,
        help="Path to payload JSON, or - for stdin.",
    )
    parser.add_argument(
        "--theorem-db-json",
        default="",
        help="Optional theorem DB JSON for G-PDE-THEOREM-APPLICABILITY.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    try:
        payload = _read_json_object(ns.payload_json, field_name="--payload-json")
        theorem_db = _load_optional_json_object(
            ns.theorem_db_json,
            field_name="--theorem-db-json",
        )
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    result = run_pde_gate(ns.gate_id, payload, theorem_db=theorem_db)
    if ns.json:
        return _print_json(result)
    status = "PASS" if result["passed"] else "FAIL"
    print(f"{status} {result['gate_id']} complete={result['complete']}")
    if result.get("missing_fields"):
        print("missing_fields: " + ", ".join(result["missing_fields"]))
    if result.get("rejected_substitutes"):
        print("rejected_substitutes: " + ", ".join(result["rejected_substitutes"]))
    if result.get("error"):
        print("error: " + str(result["error"]))
    return 0 if result["passed"] else 1


def _cmd_work_order(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde work-order",
        description="Build one registry-backed PDE leaf work order.",
    )
    parser.add_argument("--target", required=True)
    parser.add_argument("--op", required=True, dest="op_id")
    parser.add_argument("--goal", default="")
    parser.add_argument("--given-json", default="{}")
    parser.add_argument(
        "--extra-gate",
        action="append",
        default=[],
        help="Additional stable gate id. May be repeated.",
    )
    parser.add_argument(
        "--only-gate",
        action="append",
        default=[],
        help=(
            "Use only these stable gate ids instead of all gates associated "
            "with --op. May be repeated."
        ),
    )
    parser.add_argument("--formal-feedback", action="store_true")
    parser.add_argument(
        "--require-process-contract",
        action="store_true",
        help="Require orchestration/action-contract and pencil artifact refs.",
    )
    parser.add_argument("--pattern-action-contract-ref", default="")
    parser.add_argument("--orchestration-contract-ref", default="")
    parser.add_argument("--pencil-artifact-ref", default="")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    try:
        given = _json_loads_object(ns.given_json, field_name="--given-json")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    work_order = build_pde_leaf_work_order(
        target=ns.target,
        op_id=ns.op_id,
        goal=ns.goal,
        given=given,
        only_gate_ids=ns.only_gate,
        extra_gate_ids=ns.extra_gate,
        formal_feedback_requested=ns.formal_feedback,
        require_process_contract=ns.require_process_contract,
        pattern_action_contract_ref=ns.pattern_action_contract_ref,
        orchestration_contract_ref=ns.orchestration_contract_ref,
        pencil_artifact_ref=ns.pencil_artifact_ref,
    )
    if ns.json:
        return _print_json(work_order)
    print(render_pde_leaf_work_order(work_order))
    return 0


def _cmd_run_work_order(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde run-work-order",
        description=(
            "Run all supplied gate payloads for a PDE leaf work order. "
            "The payload JSON must be an object keyed by gate id."
        ),
    )
    parser.add_argument("--work-order-json", required=True)
    parser.add_argument("--payloads-json", required=True)
    parser.add_argument(
        "--theorem-db-json",
        default="",
        help="Optional theorem DB JSON for theorem-applicability gates.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    try:
        work_order = _read_json_object(
            ns.work_order_json,
            field_name="--work-order-json",
        )
        payloads = _read_json_object(ns.payloads_json, field_name="--payloads-json")
        theorem_db = _load_optional_json_object(
            ns.theorem_db_json,
            field_name="--theorem-db-json",
        )
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    bundle = run_pde_leaf_work_order_gates(
        work_order,
        payloads,
        theorem_db=theorem_db,
    )
    if ns.json:
        return _print_json(bundle)
    status = "PASS" if bundle["passed"] else "FAIL"
    print(f"{status} {bundle.get('leaf_id', '')} complete={bundle['complete']}")
    summary = bundle.get("summary") if isinstance(bundle.get("summary"), dict) else {}
    if summary:
        print(
            "summary: "
            f"gates={summary.get('gate_count', 0)} "
            f"passed={len(summary.get('passed_gate_ids') or [])} "
            f"failed={len(summary.get('failed_gate_ids') or [])} "
            f"next={summary.get('next_required_work_unit_count', 0)}"
        )
        rejected = [
            str(item) for item in (summary.get("rejected_substitutes") or [])
            if str(item).strip()
        ]
        if rejected:
            print("rejected_substitutes: " + ", ".join(rejected))
    for result in bundle.get("results") or []:
        marker = "PASS" if result.get("passed") else "FAIL"
        line = f"  {marker} {result.get('gate_id')} complete={result.get('complete')}"
        if result.get("error"):
            line += f" error={result.get('error')}"
        print(line)
    next_units = [
        unit for unit in bundle.get("next_required_work_units") or []
        if isinstance(unit, dict)
    ]
    if next_units:
        print("next required work units:")
        for unit in next_units:
            print(
                f"  - {unit.get('gate_id')}: {unit.get('action')} "
                f"({unit.get('work_unit_type')})"
            )
    return 0 if bundle["passed"] else 1


def _cmd_context(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde context",
        description=(
            "Build PDE engine context with registry and optional leaf work order. "
            "Formal feedback and project profiles remain service inputs."
        ),
    )
    parser.add_argument("--target", required=True)
    parser.add_argument("--op", default="", dest="op_id")
    parser.add_argument("--goal", default="")
    parser.add_argument("--target-currency", default="")
    parser.add_argument("--estimate-field", default="")
    parser.add_argument("--estimate-gap-type", default="")
    parser.add_argument("--candidate-inequality", action="append", default=[])
    parser.add_argument("--given-json", default="{}")
    parser.add_argument(
        "--extra-gate",
        action="append",
        default=[],
        help="Additional stable gate id for the optional work order.",
    )
    parser.add_argument(
        "--require-process-contract",
        action="store_true",
        help="Require orchestration/action-contract and pencil artifact refs.",
    )
    parser.add_argument("--pattern-action-contract-ref", default="")
    parser.add_argument("--orchestration-contract-ref", default="")
    parser.add_argument("--pencil-artifact-ref", default="")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    try:
        given = _json_loads_object(ns.given_json, field_name="--given-json")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    request = PDEEngineContextRequest(
        target=ns.target,
        target_currency=ns.target_currency,
        estimate_skeletons=PDEEstimateSkeletonOptions(
            enabled=bool(ns.estimate_field or ns.estimate_gap_type or ns.candidate_inequality),
            field=ns.estimate_field,
            gap_type=ns.estimate_gap_type,
            context=given,
            inequalities=tuple(ns.candidate_inequality),
        ),
        leaf_work_order=PDELeafWorkOrderOptions(
            op_id=ns.op_id,
            goal=ns.goal,
            given=given,
            extra_gate_ids=tuple(ns.extra_gate),
            require_process_contract=ns.require_process_contract,
            pattern_action_contract_ref=ns.pattern_action_contract_ref,
            orchestration_contract_ref=ns.orchestration_contract_ref,
            pencil_artifact_ref=ns.pencil_artifact_ref,
        ),
    )
    context = build_pde_engine_context(request)
    if ns.json:
        return _print_json(context)
    print(f"PDE engine context: {context['target']}")
    print("service boundaries:")
    for boundary, items in context["service_boundaries"].items():
        print(f"  {boundary}: {', '.join(items)}")
    print(f"gates: {len(context['gate_registry'])}")
    print(f"ops: {len(context['op_registry'])}")
    print(f"receipts: {len(context['receipt_registry'])}")
    print(f"estimate skeletons: {len(context['estimate_skeletons'])}")
    if context.get("leaf_work_order"):
        print(render_pde_leaf_work_order(context["leaf_work_order"]))
    return 0


def _cmd_knowledge(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde knowledge",
        description=(
            "Build advisory PDE theorem/profile, LeanMill premise-shelf, "
            "proof-cache, and no-good context."
        ),
    )
    parser.add_argument("--target", required=True)
    parser.add_argument("--query", default="")
    parser.add_argument("--statement", default="")
    parser.add_argument("--context", default="")
    parser.add_argument("--source", default="")
    parser.add_argument("--lean-root", default="")
    parser.add_argument("--theorem-db-json", default="")
    parser.add_argument("--available-json", default="{}")
    parser.add_argument("--source-profile", default="unknown")
    parser.add_argument("--proof-cache-jsonl", default="")
    parser.add_argument("--no-good-jsonl", default="")
    parser.add_argument("--top-k-cards", type=int, default=8)
    parser.add_argument(
        "--top-k-mathlib",
        type=int,
        default=0,
        help="Semantic Mathlib premise hits. Default 0 avoids embedding calls.",
    )
    parser.add_argument(
        "--top-k-domain",
        type=int,
        default=0,
        help="Semantic domain-atlas premise hits. Default 0 avoids embedding calls.",
    )
    parser.add_argument(
        "--top-k-own",
        type=int,
        default=0,
        help="Semantic own-ledger premise hits. Default 0 avoids embedding calls.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    try:
        theorem_db = _load_optional_json_object(
            ns.theorem_db_json,
            field_name="--theorem-db-json",
        )
        available = _json_loads_object(ns.available_json, field_name="--available-json")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    context = build_pde_knowledge_context(
        target=ns.target,
        query=ns.query,
        theorem_db=theorem_db,
        available=available,
        source_profile=ns.source_profile,
        statement=ns.statement,
        context=ns.context,
        source=ns.source,
        lean_root=ns.lean_root or None,
        proof_cache_path=ns.proof_cache_jsonl or None,
        no_good_store_path=ns.no_good_jsonl or None,
        top_k_cards=ns.top_k_cards,
        top_k_mathlib=ns.top_k_mathlib,
        top_k_domain=ns.top_k_domain,
        top_k_own=ns.top_k_own,
    )
    if ns.json:
        return _print_json(context)
    print(f"PDE knowledge context: {context['target']}")
    print("recommended leaves:")
    for item in context.get("recommended_leaf_sequence") or []:
        print(f"  - {item}")
    print(f"theorem cards: {len(context.get('theorem_profile_cards') or [])}")
    memory = context.get("leanmill_memory") or {}
    no_good = memory.get("no_good_store") if isinstance(memory, dict) else {}
    proof_cache = memory.get("proof_cache") if isinstance(memory, dict) else {}
    print(f"proof cache hit: {bool(proof_cache.get('hit')) if isinstance(proof_cache, dict) else False}")
    print(f"no-good matches: {int(no_good.get('n_matches') or 0) if isinstance(no_good, dict) else 0}")
    return 0


def _cmd_formal_surface(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde formal-surface",
        description="Build a PDE formal-surface inventory map.",
    )
    parser.add_argument("--target", default="")
    parser.add_argument("--source-profile", default="unknown")
    parser.add_argument(
        "--record-json",
        action="append",
        default=[],
        help=(
            "Path to one formal-surface record JSON, a list of records, or an "
            "object with records/required_primitives. May be repeated."
        ),
    )
    parser.add_argument(
        "--required",
        action="append",
        default=[],
        help="Required primitive id expected in the map. May be repeated.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    records: list[dict[str, Any]] = []
    required = [str(item) for item in ns.required if str(item).strip()]
    try:
        for raw in ns.record_json:
            payload = _read_json_any(raw, field_name="--record-json")
            if isinstance(payload, list):
                for item in payload:
                    if not isinstance(item, dict):
                        parser.error("--record-json list entries must be objects")
                    records.append(item)
            elif isinstance(payload, dict):
                if isinstance(payload.get("records"), list):
                    for item in payload["records"]:
                        if not isinstance(item, dict):
                            parser.error("--record-json records entries must be objects")
                        records.append(item)
                    required.extend(
                        str(item) for item in payload.get("required_primitives", [])
                        if str(item).strip()
                    )
                else:
                    records.append(payload)
            else:
                parser.error("--record-json must be an object or list")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    surface_map = build_pde_formal_surface_map(
        records,
        target=ns.target,
        required_primitives=required,
        source_profile=ns.source_profile,
    )
    if ns.json:
        return _print_json(surface_map)
    print(render_pde_formal_surface_map(surface_map))
    return 0


def _cmd_canary_report(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare pde canary-report",
        description=(
            "Re-ingest a physical PDE canary gate bundle into next leaves, "
            "failure-memory rows, and formal-surface rows."
        ),
    )
    parser.add_argument("--readiness-json", required=True)
    parser.add_argument("--gate-run-json", required=True)
    parser.add_argument("--physical-receipt-json", default="")
    parser.add_argument("--formal-surface-json", action="append", default=[])
    parser.add_argument("--source-profile", default="tick669_c7_fresh_annular_same_source")
    parser.add_argument("--source-artifact", action="append", default=[])
    parser.add_argument(
        "--write-failure-memory-jsonl",
        default="",
        help="Optional project-local JSONL path for PDE failure-memory rows.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    ns = parser.parse_args(args)

    formal_surface_records: list[dict[str, Any]] = []
    try:
        readiness = _read_json_object(
            ns.readiness_json,
            field_name="--readiness-json",
        )
        gate_run = _read_json_object(
            ns.gate_run_json,
            field_name="--gate-run-json",
        )
        physical_receipt = (
            _read_json_object(ns.physical_receipt_json, field_name="--physical-receipt-json")
            if ns.physical_receipt_json else None
        )
        for path in ns.formal_surface_json:
            payload = _read_json_any(path, field_name="--formal-surface-json")
            if isinstance(payload, list):
                for item in payload:
                    if not isinstance(item, dict):
                        parser.error("--formal-surface-json list entries must be objects")
                    formal_surface_records.append(item)
            elif isinstance(payload, dict):
                rows = payload.get("records")
                if isinstance(rows, list):
                    for item in rows:
                        if not isinstance(item, dict):
                            parser.error("--formal-surface-json records entries must be objects")
                        formal_surface_records.append(item)
                else:
                    formal_surface_records.append(payload)
            else:
                parser.error("--formal-surface-json must be an object or list")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    receipt = build_pde_canary_reingestion_receipt(
        readiness_receipt=readiness,
        gate_run_bundle=gate_run,
        physical_receipt=physical_receipt,
        formal_surface_records=formal_surface_records or None,
        source_profile=ns.source_profile,
        source_artifacts=ns.source_artifact,
    )
    if ns.write_failure_memory_jsonl:
        n_written = write_pde_failure_memory_jsonl(
            receipt.get("failure_memory_rows") or [],
            ns.write_failure_memory_jsonl,
        )
        receipt["failure_memory_jsonl"] = {
            "path": ns.write_failure_memory_jsonl,
            "rows_written": n_written,
        }
    if ns.json:
        return _print_json(receipt)
    print(f"PDE canary reingestion: {'PASS' if receipt['kernel_loop_ready'] else 'FAIL'}")
    print("scoreboard:")
    for key, value in receipt["scoreboard"].items():
        print(f"  {key}: {'PASS' if value else 'FAIL'}")
    print("next leaves:")
    for unit in receipt.get("next_leaf_work_orders") or []:
        print(f"  - {unit.get('target')}: {unit.get('goal')}")
    return 0 if receipt["kernel_loop_ready"] else 1


_VERBS = {
    "status": _cmd_status,
    "completion-audit": _cmd_completion_audit,
    "requirements": _cmd_requirements,
    "readiness": _cmd_readiness,
    "ops": _cmd_ops,
    "currency": _cmd_currency,
    "estimates": _cmd_estimates,
    "receipts": _cmd_receipts,
    "gates": _cmd_gates,
    "run-gate": _cmd_run_gate,
    "work-order": _cmd_work_order,
    "run-work-order": _cmd_run_work_order,
    "context": _cmd_context,
    "knowledge": _cmd_knowledge,
    "formal-surface": _cmd_formal_surface,
    "canary-report": _cmd_canary_report,
}


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(
            "ztare pde <verb> [args...]\n\n"
            "Verbs:\n"
            "  status      report PDE subkernel readiness\n"
            "  requirements emit architecture requirement matrix\n"
            "  readiness   emit readiness receipt and TICK669 canary work order\n"
            "  ops         list GP-219 operation cards and execution templates\n"
            "  currency    emit proof-currency ledger templates\n"
            "  estimates   generate estimate skeletons\n"
            "  receipts    list receipt registry entries\n"
            "  gates       list registry-backed PDE gates\n"
            "  run-gate    run one registry-backed PDE gate\n"
            "  work-order  build an atomic PDE leaf work order\n"
            "  run-work-order run supplied gate payloads for a work order\n"
            "  context     build PDE engine context\n\n"
            "  knowledge   build PDE/LeanMill retrieval and memory context\n\n"
            "  formal-surface build formal-surface inventory map\n\n"
            "  canary-report re-ingest physical canary gate results\n\n"
            "For any verb's own options, run `ztare pde <verb> --help`."
        )
        return 0
    verb, *args = argv
    handler = _VERBS.get(verb)
    if handler is None:
        print(
            f"ztare pde: unknown verb {verb!r}. Known: {', '.join(_VERBS)}",
            file=sys.stderr,
        )
        return 2
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
