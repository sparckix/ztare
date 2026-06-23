"""Graph focus receipt briefing provider.

Carries graph-carrier decisions that belong inside the autoresearch loop into
the mutator prompt. Public-source recovery remains out-of-loop prep and is not
rendered here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider
from ztare.research_director.graph_carrier_actions import graph_carrier_action_rows
from ztare.scaffold.substrate_queue import load_project_packet, validate_project_packet
from ztare.validator.probability_dag_carrier import (
    build_probability_dag_graph_carrier,
    summarize_probability_dag_graph_carrier,
)
from ztare.validator.source_claim_graph_carrier import (
    build_source_claim_graph_carrier,
    summarize_source_claim_graph_carrier,
)
from ztare.workspace.evidence_gaps import (
    LOCAL_VERIFICATION_RECOVERY_KIND,
    apply_evidence_gap_recovery_policy,
    evidence_gap_fingerprint,
    evidence_gap_recovery_contract,
)


LOCAL_VERIFIER_RECEIPTS = (
    ("project_packet_falsifier", "packet_falsifier_receipt.json"),
)


class GraphFocusReceiptProvider(BriefingProvider):
    name = "graph_focus_receipt"
    priority = 115

    def _actions(self, ctx: BriefingContext) -> list[dict[str, str]]:
        carriers: list[dict[str, Any]] = []
        intake_gap_contracts, intake_source, _intake_rows = _intake_gap_contracts(ctx)
        intake_policy = _intake_gap_policy(ctx)
        probability_carrier = build_probability_dag_graph_carrier(
            project_dir=ctx.project_dir,
            workspace_dir=ctx.workspace_dir,
            rubric_data=ctx.rubric,
        )
        if probability_carrier is not None:
            carriers.append(summarize_probability_dag_graph_carrier(probability_carrier))
        source_carrier = build_source_claim_graph_carrier(
            project_dir=ctx.project_dir,
            workspace_dir=ctx.workspace_dir,
            repo=_repo_for_project(ctx.project_dir),
            intake_gap_contracts=intake_gap_contracts,
            intake_gap_contract_source=intake_source,
            intake_gap_recovery_policy=intake_policy,
        )
        if source_carrier is not None:
            carriers.append(summarize_source_claim_graph_carrier(source_carrier))
        if not carriers:
            return []
        return [
            action
            for action in graph_carrier_action_rows(carriers)
            if action.get("action_type") == "in_loop_focus_receipt"
        ]

    def _local_gap_details(self, ctx: BriefingContext) -> list[dict[str, str]]:
        _contracts, _source, intake_rows = _intake_gap_contracts(ctx)
        intake_policy = _intake_gap_policy(ctx)
        gaps_path = ctx.workspace_dir / "latest_evidence_gaps.json"
        if not gaps_path.exists():
            return intake_rows
        try:
            payload = json.loads(gaps_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return intake_rows
        gaps = payload.get("evidence_gaps")
        if not isinstance(gaps, list):
            return intake_rows
        details: list[dict[str, str]] = []
        seen_targets: set[str] = set()
        for gap in gaps:
            if not isinstance(gap, dict):
                continue
            gap = apply_evidence_gap_recovery_policy(
                gap,
                intake_policy,
                project_dir=ctx.project_dir,
            )
            contract = evidence_gap_recovery_contract(gap, project_dir=ctx.project_dir)
            if contract.get("recovery_kind") != LOCAL_VERIFICATION_RECOVERY_KIND:
                continue
            if not contract.get("in_loop_consumable", False):
                continue
            explicit_gap_id = str(gap.get("id") or "").strip()
            details.append(
                {
                    "gap_id": explicit_gap_id or f"gap:{evidence_gap_fingerprint(gap)[:12]}",
                    "target": str(gap.get("target") or gap.get("applies_to") or "").strip(),
                    "severity": str(gap.get("severity") or "").strip(),
                    "description": str(gap.get("description") or "").strip(),
                    "producer": str(gap.get("producer") or "").strip(),
                    "producer_rationale": str(gap.get("producer_rationale") or "").strip(),
                    "recovery_kind": str(contract.get("recovery_kind") or "").strip(),
                    "required_surface": str(contract.get("required_surface") or "").strip(),
                }
            )
            seen_targets.add(str(contract.get("target") or "").strip())
        for row in intake_rows:
            target = str(row.get("target") or "").strip()
            if not target or target in seen_targets:
                continue
            details.append(row)
            seen_targets.add(target)
        return details

    def _local_verifier_receipts(self, ctx: BriefingContext) -> list[dict[str, Any]]:
        receipts: list[dict[str, Any]] = []
        for receipt_type, filename in LOCAL_VERIFIER_RECEIPTS:
            path = ctx.workspace_dir / filename
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            enforced_by = [
                str(item).strip()
                for item in payload.get("enforced_by", [])
                if str(item).strip()
            ]
            receipts.append(
                {
                    "receipt_type": receipt_type,
                    "path": f"workspace/{filename}",
                    "status": str(payload.get("status") or "").strip(),
                    "command": str(payload.get("command") or "").strip(),
                    "remove_ref": str(payload.get("remove_ref") or "").strip(),
                    "removed_ref": str(payload.get("removed_ref") or "").strip(),
                    "expected_failure": str(
                        payload.get("expected_failure")
                        or payload.get("expected_error_fragment")
                        or ""
                    ).strip(),
                    "enforced_by": enforced_by[:6],
                    "path_safety": (
                        payload.get("path_safety")
                        if isinstance(payload.get("path_safety"), dict)
                        else {}
                    ),
                }
            )
        return receipts

    def applies(self, ctx: BriefingContext) -> bool:
        return bool(self._actions(ctx))

    def fragment(self, ctx: BriefingContext) -> str:
        actions = self._actions(ctx)
        if not actions:
            return ""
        lines = [
            "\n    ### GRAPH FOCUS RECEIPT (prior trace carrier)\n",
            "    The source/evidence graph produced an in-loop focus receipt.",
            "    Treat it as the next local verifier target, not as public-source fetching.\n",
        ]
        for action in actions:
            reason = str(action.get("reason") or "").strip()
            graph_id = str(action.get("graph_id") or "").strip()
            lines.append(f"    - {graph_id}: {reason}")
        details = self._local_gap_details(ctx)
        if details:
            lines.append("\n    Local verifier gaps to close in the candidate artifact:")
            for detail in details[:5]:
                gap_id = detail.get("gap_id") or "unidentified_gap"
                target = detail.get("target") or "unspecified_target"
                severity = detail.get("severity") or "unknown"
                description = detail.get("description") or "no description"
                producer = detail.get("producer") or "unknown_producer"
                rationale = detail.get("producer_rationale") or "no producer rationale"
                recovery_kind = detail.get("recovery_kind") or LOCAL_VERIFICATION_RECOVERY_KIND
                required_surface = detail.get("required_surface") or "local_verifier_or_fixture"
                lines.append(
                    "    - "
                    f"gap_id={gap_id}; target={target}; severity={severity}; "
                    f"recovery_kind={recovery_kind}; required_surface={required_surface}; "
                    f"producer={producer}; "
                    f"description={description}; rationale={rationale}"
                )
            receipts = self._local_verifier_receipts(ctx)
            if receipts:
                lines.append("\n    Local verifier receipts available to consume:")
                for receipt in receipts[:3]:
                    enforced_by = ", ".join(receipt.get("enforced_by") or [])
                    lines.append(
                        "    - "
                        f"type={receipt.get('receipt_type')}; path={receipt.get('path')}; "
                        f"status={receipt.get('status')}; command={receipt.get('command')}; "
                        f"remove_ref={receipt.get('remove_ref')}; "
                        f"expected_failure={receipt.get('expected_failure')}"
                    )
                    if enforced_by:
                        lines.append(f"      enforced_by={enforced_by}")
                    path_safety = receipt.get("path_safety")
                    if isinstance(path_safety, dict) and path_safety:
                        lines.append(
                            "      path_safety="
                            f"absolute_local_refs_allowed={path_safety.get('absolute_local_refs_allowed')}; "
                            f"parent_traversal_allowed={path_safety.get('parent_traversal_allowed')}; "
                            f"symlink_escape_allowed={path_safety.get('symlink_escape_allowed')}"
                        )
            lines.append(
                "    Required response: encode a local discriminator in test_model.py "
                "or mark the target UNRESOLVED. If a local verifier receipt applies, "
                "assert its machine fields rather than naming the receipt file alone; "
                "keep untested parser/symlink robustness explicitly unresolved."
            )
        return "\n".join(lines) + "\n"

    def structured_records(self, ctx: BriefingContext) -> list[dict[str, Any]]:
        return [
            {
                "record_type": "graph_focus_receipt",
                **action,
                "local_gap_details": self._local_gap_details(ctx),
                "local_verifier_receipts": self._local_verifier_receipts(ctx),
            }
            for action in self._actions(ctx)
        ]


def _repo_for_project(project_dir: Path) -> Path | None:
    if project_dir.parent.name == "projects":
        return project_dir.parent.parent
    return None


def _rel(path: Path, repo: Path | None) -> str:
    if repo is None:
        return str(path)
    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path)


def _packet_candidates(ctx: BriefingContext) -> list[Path]:
    project_slug = ctx.project_dir.name
    return [
        ctx.project_dir / "project_packet.json",
        ctx.project_dir / f"{project_slug}_packet.json",
    ]


def _intake_gap_contracts(
    ctx: BriefingContext,
) -> tuple[list[dict[str, Any]], str, list[dict[str, str]]]:
    repo = _repo_for_project(ctx.project_dir)
    if isinstance(ctx.project_packet, dict) and ctx.project_packet:
        from_context = _validated_packet_contracts(
            ctx.project_packet,
            path_hint=str(ctx.project_packet.get("_ztare_packet_path") or ""),
            repo=repo,
            base_dir=ctx.project_dir,
        )
        if from_context[0]:
            return from_context
    for path in _packet_candidates(ctx):
        if not path.exists():
            continue
        try:
            payload = load_project_packet(path)
        except SystemExit:
            continue
        contracts, source, detail_rows = _validated_packet_contracts(
            payload,
            path_hint=_rel(path, repo),
            repo=repo,
            base_dir=path.parent,
        )
        if contracts:
            return contracts, source, detail_rows
    return [], "", []


def _validated_packet_contracts(
    payload: dict[str, Any],
    *,
    path_hint: str,
    repo: Path | None,
    base_dir: Path,
) -> tuple[list[dict[str, Any]], str, list[dict[str, str]]]:
    validation = validate_project_packet(
        payload,
        base_dir=base_dir,
        repo_root=repo,
        require_source_preflight=False,
    )
    contracts = [
        contract
        for contract in validation.get("evidence_gap_contracts") or []
        if isinstance(contract, dict)
    ]
    if not validation.get("ok") or not contracts:
        return [], "", []
    raw_rows = [
        row
        for row in payload.get("evidence_gap_contracts") or []
        if isinstance(row, dict)
    ]
    detail_rows: list[dict[str, str]] = []
    for idx, contract in enumerate(contracts):
        if contract.get("recovery_kind") != LOCAL_VERIFICATION_RECOVERY_KIND:
            continue
        if not contract.get("in_loop_consumable", False):
            continue
        raw = raw_rows[idx] if idx < len(raw_rows) else {}
        target = str(contract.get("target") or raw.get("target") or "").strip()
        detail_rows.append(
            {
                "gap_id": str(raw.get("id") or f"intake_gap_contract_{idx + 1}"),
                "target": target,
                "severity": str(raw.get("severity") or "degrading"),
                "description": str(raw.get("description") or "").strip(),
                "producer": str(raw.get("producer") or "project_intake").strip(),
                "producer_rationale": str(
                    raw.get("producer_rationale") or "declared by project intake"
                ).strip(),
                "recovery_kind": str(contract.get("recovery_kind") or "").strip(),
                "required_surface": str(contract.get("required_surface") or "").strip(),
            }
        )
    return contracts, path_hint, detail_rows


def _intake_gap_policy(ctx: BriefingContext) -> dict[str, Any]:
    if isinstance(ctx.project_packet, dict):
        policy = ctx.project_packet.get("evidence_gap_recovery_policy")
        if isinstance(policy, dict):
            return policy
    for path in _packet_candidates(ctx):
        if not path.exists():
            continue
        try:
            payload = load_project_packet(path)
        except SystemExit:
            continue
        policy = payload.get("evidence_gap_recovery_policy")
        if isinstance(policy, dict):
            return policy
    return {}
