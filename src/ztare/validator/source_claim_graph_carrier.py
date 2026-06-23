"""Import-safe helpers for autoresearch source-claim graph carriers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ztare.common.graph_carrier import validate_graph_carrier
from ztare.scaffold.source_check import check_source_project
from ztare.validator.probability_dag_carrier import read_json_object
from ztare.workspace.evidence_gaps import (
    LOCAL_VERIFICATION_RECOVERY_KIND,
    PUBLIC_EVIDENCE_RECOVERY_KIND,
    apply_evidence_gap_recovery_policy,
    evidence_gap_fingerprint,
    evidence_gap_recovery_contract,
)
from ztare.workspace.claim_support import build_claim_support_audit
from ztare.workspace.source_freshness import (
    artifact_source_freshness,
    source_binding_contract_blocks_kernel,
)


def build_source_claim_graph_carrier(
    *,
    project_dir: Path,
    workspace_dir: Path | None = None,
    repo: Path | None = None,
    intake_gap_contracts: list[dict[str, Any]] | None = None,
    intake_gap_contract_source: str | None = None,
    intake_gap_recovery_policy: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build a source-claim graph carrier from autoresearch evidence artifacts."""
    workspace = workspace_dir or project_dir / "workspace"
    source_index_path = workspace / "source_index.json"
    evidence_path = project_dir / "evidence.txt"
    compiled_packet_path = project_dir / "compiled_evidence_packet.json"
    gaps_path = workspace / "latest_evidence_gaps.json"
    compile_provenance_path = _first_existing_path(
        [
            project_dir / "compiled_evidence_provenance.json",
            workspace / "evidence_compile_provenance.json",
        ]
    )
    source_artifacts = [
        path
        for path in [
            source_index_path,
            evidence_path,
            compiled_packet_path,
            gaps_path,
            compile_provenance_path,
        ]
        if path is not None and path.exists()
    ]
    if not source_artifacts and not intake_gap_contracts:
        return None
    source_artifact_refs = [_rel(path, repo) for path in source_artifacts]
    if intake_gap_contracts and intake_gap_contract_source:
        source_artifact_refs.append(intake_gap_contract_source)

    source_index = read_json_object(source_index_path)
    sources = source_index.get("sources")
    if not isinstance(sources, list):
        sources = []
    source_rows = [row for row in sources if isinstance(row, dict)]
    compile_provenance = (
        read_json_object(compile_provenance_path)
        if compile_provenance_path is not None
        else {}
    )
    compile_sources = compile_provenance.get("sources")
    if not isinstance(compile_sources, list):
        compile_sources = []
    compile_source_rows = [row for row in compile_sources if isinstance(row, dict)]
    repo_for_freshness = repo or _infer_repo(project_dir)
    source_preflight = _source_preflight_for_carrier(
        project_dir=project_dir,
        repo=repo_for_freshness,
    )
    source_index_freshness = artifact_source_freshness(
        source_preflight=source_preflight,
        artifact_sources=source_rows,
        artifact_name=_rel(source_index_path, repo),
        project_dir=project_dir,
        repo=repo_for_freshness,
    )
    compile_freshness = artifact_source_freshness(
        source_preflight=source_preflight,
        artifact_sources=compile_source_rows,
        artifact_name=(
            _rel(compile_provenance_path, repo)
            if compile_provenance_path is not None
            else "compiled_evidence_provenance.json"
        ),
        project_dir=project_dir,
        repo=repo_for_freshness,
    )
    claim_support = build_claim_support_audit(
        project_dir,
        evidence_readiness={
            "status": _carrier_evidence_readiness_status(
                source_index_freshness=source_index_freshness,
                compile_freshness=compile_freshness,
                source_index_exists=source_index_path.exists(),
                compile_provenance_exists=compile_provenance_path is not None,
            )
        },
    )

    gaps_payload = read_json_object(gaps_path)
    gaps = gaps_payload.get("evidence_gaps")
    if not isinstance(gaps, list):
        gaps = []
    gap_rows_from_latest = [
        apply_evidence_gap_recovery_policy(
            row,
            intake_gap_recovery_policy,
            project_dir=project_dir,
        )
        for row in gaps
        if isinstance(row, dict)
    ]
    gap_records = [
        {
            "row": row,
            "recovery_contract": evidence_gap_recovery_contract(
                row,
                project_dir=project_dir,
            ),
        }
        for row in gap_rows_from_latest
    ]
    gap_records = _merge_intake_gap_contracts(
        gap_records,
        intake_gap_contracts or [],
    )
    active_gap_records = [
        record
        for record in gap_records
        if record["recovery_contract"].get("active")
    ]
    gap_rows = [record["row"] for record in active_gap_records]
    local_verification_gaps = [
        record["row"]
        for record in active_gap_records
        if record["recovery_contract"].get("recovery_kind") == LOCAL_VERIFICATION_RECOVERY_KIND
        and record["recovery_contract"].get("in_loop_consumable") is True
    ]
    public_evidence_gaps = [
        record["row"]
        for record in active_gap_records
        if record["recovery_contract"].get("recovery_kind") == PUBLIC_EVIDENCE_RECOVERY_KIND
        and record["recovery_contract"].get("can_public_fetch") is True
    ]
    locally_resolved_gap_count = sum(
        1
        for record in gap_records
        if record["recovery_contract"].get("activity_status")
        in {"resolved_by_local_artifact", "resolved_by_local_verifier_receipt"}
    )

    source_keys = sorted({str(key) for row in source_rows for key in row})
    gap_keys = sorted({str(key) for row in gap_rows for key in row})
    claim_support_statuses = sorted(
        str(key)
        for key in (claim_support.get("status_counts") or {})
        if str(key).strip()
    )
    evidence_node_count = 1 if evidence_path.exists() else 0
    claim_node_count = int(claim_support.get("claim_count") or 0)
    claim_source_edge_count = sum(
        len(row.get("source_ids") or [])
        for row in claim_support.get("rows") or []
        if isinstance(row, dict)
    )
    node_count = len(source_rows) + len(gap_rows) + evidence_node_count + claim_node_count
    edge_count = 0
    if evidence_path.exists():
        edge_count += len(source_rows)
    edge_count += len(gap_rows)
    edge_count += claim_source_edge_count

    decision_receipt = _decision_receipt(
        source_preflight=source_preflight,
        source_count=len(source_rows),
        public_evidence_gap_count=len(public_evidence_gaps),
        local_verification_gap_count=len(local_verification_gaps),
        evidence_exists=evidence_path.exists(),
        source_index_exists=source_index_path.exists(),
        compile_provenance_exists=compile_provenance_path is not None,
        source_index_freshness=source_index_freshness,
        compile_freshness=compile_freshness,
        claim_support=claim_support,
        local_verification_gap_ids=[
            _gap_id(row) for row in local_verification_gaps
        ],
        local_verification_targets=[
            _gap_target(row) for row in local_verification_gaps
        ],
    )
    carrier = {
        "graph_id": f"{project_dir.name}:source_claim_graph",
        "graph_kind": "source_claim_graph",
        "producer": "workspace/source_index.json + compiled evidence artifacts + project-intake gap contracts",
        "source_artifacts": source_artifact_refs,
        "consumer": "autoresearch_trace.recovery_actions",
        "freshness_rule": "rerun after evidence-fetch, evidence-prepare, or compile-evidence",
        "node_count": node_count,
        "edge_count": edge_count,
        "node_vocabulary": (
            source_keys + gap_keys + claim_support_statuses or ["source_claim_node"]
        ),
        "edge_vocabulary": [
            "source_to_evidence_packet",
            "evidence_gap_to_recovery_action",
            "source_to_compiled_claim",
        ],
        "diagnostics": [
            {
                "method": "source_index_to_evidence_gap_coverage",
                "baseline": "evidence text or raw files without source-claim graph receipt",
                "result_summary": (
                    f"{len(source_rows)} source row(s), {len(gap_rows)} active evidence gap(s), "
                    f"evidence_exists={evidence_path.exists()}"
                ),
                "locally_resolved_gap_count": locally_resolved_gap_count,
                "public_evidence_gap_count": len(public_evidence_gaps),
                "local_verification_gap_count": len(local_verification_gaps),
                "recovery_kind_counts": {
                    PUBLIC_EVIDENCE_RECOVERY_KIND: len(public_evidence_gaps),
                    LOCAL_VERIFICATION_RECOVERY_KIND: len(local_verification_gaps),
                },
                "claim_support": {
                    "status": claim_support.get("status"),
                    "claim_count": claim_support.get("claim_count", 0),
                    "weak_or_unsourced_count": claim_support.get(
                        "weak_or_unsourced_count",
                        0,
                    ),
                    "status_counts": claim_support.get("status_counts", {}),
                    "source_context_blocked_count": claim_support.get(
                        "source_context_blocked_count",
                        0,
                    ),
                    "source_context_status_counts": claim_support.get(
                        "source_context_status_counts",
                        {},
                    ),
                },
                "source_preflight": {
                    "ok": bool(source_preflight.get("ok")),
                    "status": source_preflight.get("status"),
                    "blocking": list(source_preflight.get("blocking") or []),
                    "warnings": list(source_preflight.get("warnings") or []),
                },
                "source_index_freshness": source_index_freshness,
                "compile_freshness": compile_freshness,
            }
        ],
        "noise_filter": "ignore malformed source rows or evidence-gap rows",
        "decision_receipt": decision_receipt,
        "library_anchor": "standard library JSON plus local evidence provenance parser",
        "literature_anchor": "source-claim provenance graph and evidence-gap tracing",
    }
    validation = validate_graph_carrier(carrier)
    carrier["validation"] = {
        "ok": validation.ok,
        "errors": validation.errors,
        "warnings": validation.warnings,
    }
    return carrier


def summarize_source_claim_graph_carrier(carrier: dict[str, Any]) -> dict[str, Any]:
    """Return the compact carrier view used in trace reports."""
    return {
        "graph_id": carrier["graph_id"],
        "graph_kind": carrier["graph_kind"],
        "source_artifacts": carrier["source_artifacts"],
        "node_count": carrier["node_count"],
        "edge_count": carrier["edge_count"],
        "decision_receipt": carrier["decision_receipt"],
        "validation": carrier["validation"],
    }


def _decision_receipt(
    *,
    source_preflight: dict[str, Any],
    source_count: int,
    public_evidence_gap_count: int,
    local_verification_gap_count: int,
    evidence_exists: bool,
    source_index_exists: bool,
    compile_provenance_exists: bool,
    source_index_freshness: dict[str, Any],
    compile_freshness: dict[str, Any],
    claim_support: dict[str, Any],
    local_verification_gap_ids: list[str],
    local_verification_targets: list[str],
) -> dict[str, Any]:
    if not bool(source_preflight.get("ok")):
        blockers = [str(item) for item in source_preflight.get("blocking") or [] if str(item)]
        status = str(source_preflight.get("status") or "unknown")
        reason = (
            "source-claim graph source preflight is not satisfied "
            f"({status}); graph routing is blocked until source-check passes"
        )
        if blockers:
            reason += f": {'; '.join(blockers)}"
        return {
            "effect": "misleading_or_noise",
            "reason": reason,
        }
    source_status = str(source_index_freshness.get("status") or "")
    compile_status = str(compile_freshness.get("status") or "")
    if source_index_exists and source_binding_contract_blocks_kernel(source_index_freshness):
        return {
            "effect": "misleading_or_noise",
            "reason": (
                "source-claim graph source index does not verify current raw "
                f"sources ({source_status}); binding contract is not satisfied; "
                "refresh source-index before graph routing"
            ),
        }
    if compile_provenance_exists and source_binding_contract_blocks_kernel(compile_freshness):
        return {
            "effect": "misleading_or_noise",
            "reason": (
                "source-claim graph compile provenance does not verify current raw "
                f"sources ({compile_status}); binding contract is not satisfied; "
                "refresh evidence-prepare before graph routing"
            ),
        }
    if public_evidence_gap_count:
        return {
            "effect": "strategy_change",
            "route_change": (
                f"fetch or justify {public_evidence_gap_count} active evidence gap(s)"
            ),
        }
    if local_verification_gap_count:
        targets = ", ".join(target for target in local_verification_targets if target)
        suffix = f": {targets}" if targets else ""
        return {
            "effect": "strategy_change",
            "selected_next_discriminator": (
                f"resolve {local_verification_gap_count} local verification gap(s) "
                f"inside the autoresearch loop{suffix}"
            ),
            "selected_gap_ids": [gap_id for gap_id in local_verification_gap_ids if gap_id],
            "selected_targets": [target for target in local_verification_targets if target],
            "runtime_consumable": True,
        }
    source_context_blocked_count = int(
        claim_support.get("source_context_blocked_count") or 0
    )
    if source_context_blocked_count:
        return {
            "effect": "strategy_change",
            "selected_next_discriminator": (
                f"refresh or repair {source_context_blocked_count} stale or "
                "unverified source-context row(s) before report export"
            ),
        }
    weak_claim_count = int(claim_support.get("weak_or_unsourced_count") or 0)
    if weak_claim_count:
        return {
            "effect": "strategy_change",
            "selected_next_discriminator": (
                f"repair or demote {weak_claim_count} weak or unsourced compiled-evidence "
                "claim row(s) before report export"
            ),
        }
    if evidence_exists and not source_index_exists:
        return {
            "effect": "strategy_change",
            "route_change": "run evidence-prepare to bind evidence text to source rows",
        }
    if source_count == 0:
        return {
            "effect": "no_strategy_change",
            "reason": "no source rows or evidence gaps are available for graph routing",
        }
    return {
        "effect": "no_strategy_change",
        "reason": "source/evidence chain present with no active evidence gaps",
    }


def _carrier_evidence_readiness_status(
    *,
    source_index_freshness: dict[str, Any],
    compile_freshness: dict[str, Any],
    source_index_exists: bool,
    compile_provenance_exists: bool,
) -> str:
    if source_index_exists and source_binding_contract_blocks_kernel(source_index_freshness):
        return "blocked"
    if compile_provenance_exists and source_binding_contract_blocks_kernel(compile_freshness):
        return "blocked"
    return "fresh"


def _first_existing_path(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _merge_intake_gap_contracts(
    gap_records: list[dict[str, Any]],
    intake_gap_contracts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add intake-seeded gap contracts when workspace gaps do not supersede them."""
    merged = list(gap_records)
    seen_targets = {
        _target_key(record.get("recovery_contract", {}).get("target"))
        for record in merged
        if isinstance(record, dict)
    }
    for idx, contract in enumerate(intake_gap_contracts, start=1):
        if not isinstance(contract, dict):
            continue
        target = str(contract.get("target") or "").strip()
        target_keys = {_target_key(target)}
        aliases = contract.get("target_aliases")
        if isinstance(aliases, list):
            target_keys.update(_target_key(alias) for alias in aliases)
        target_keys.discard("")
        if not target or seen_targets.intersection(target_keys):
            continue
        row = {
            "id": f"intake_gap_contract_{idx}",
            "target": target,
            "gap_type": "project_intake_gap_contract",
            "severity": "degrading",
            "recovery_kind": contract.get("recovery_kind"),
            "recovery_channel": contract.get("recovery_channel"),
            "required_surface": contract.get("required_surface"),
            "can_public_fetch": contract.get("can_public_fetch"),
            "in_loop_consumable": contract.get("in_loop_consumable"),
            "description": "Project-intake declared evidence-gap recovery contract.",
            "contract_source": "project_intake",
        }
        merged.append(
            {
                "row": row,
                "recovery_contract": contract,
            }
        )
        seen_targets.update(target_keys)
    return merged


def _target_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    normalized = "".join(ch if ch.isalnum() else " " for ch in text)
    return " ".join(normalized.split())


def _rel(path: Path, repo: Path | None) -> str:
    if repo is None:
        return str(path)
    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path)


def _infer_repo(project_dir: Path) -> Path:
    if project_dir.parent.name == "projects":
        return project_dir.parent.parent
    return project_dir.parent


def _source_preflight_for_carrier(*, project_dir: Path, repo: Path) -> dict[str, Any]:
    try:
        return check_source_project(project=_rel(project_dir, repo), repo=repo)
    except Exception as exc:  # noqa: BLE001
        blocker = (
            "source preflight unavailable for graph carrier: "
            f"{type(exc).__name__}: {exc}"
        )
        return {
            "schema": "ztare-source-check-v1",
            "ok": False,
            "status": "unavailable_for_graph_carrier",
            "blocking": [blocker],
            "warnings": [],
            "sources": [],
            "source_evidence_count": 0,
            "untyped_source_count": 0,
        }


def _gap_target(gap: dict[str, Any]) -> str:
    return str(gap.get("target") or gap.get("applies_to") or "").strip()


def _gap_id(gap: dict[str, Any]) -> str:
    explicit_id = str(gap.get("id") or "").strip()
    if explicit_id:
        return explicit_id
    return f"gap:{evidence_gap_fingerprint(gap)[:12]}"
