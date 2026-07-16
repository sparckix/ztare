"""Receipt-driven repair cards for level-boundary transfer residues.

This module does not patch a model. It converts a bounded level-transfer probe
receipt into a Strategy Office experiment card when the receipt contains a
compact residue and a sufficiency certificate. The card is a work order: repair
or explicitly waive the residue, then rerun the transfer probe.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ztare.common.operator_proposal_contract import (
    family_sha,
    open_cards,
    record_disposition,
)
from ztare.worldmodel.carrier_loader import (
    CarrierEvidenceIdentityError,
    require_current_carrier_evidence_binding,
    resolve_current_carrier_evidence_identity,
)
from ztare.research_director.strategy_decision_policy import (
    STRATEGY_LEDGER,
    StrategyCardBatchSubmission,
    submit_strategy_card_batch,
)
from ztare.research_director.strategy_office import STRATEGY_SCHEMA


def build_compressed_counterexample_repair_card(receipt: dict[str, Any]) -> dict | None:
    q = receipt.get("residue_quotient") or {}
    cert = receipt.get("repair_certificate") or {}
    residue_class = q.get("residue_class")
    if receipt.get("status") == "exact_first_step_transfer":
        return None
    if not residue_class or residue_class == "none":
        return None
    if not cert.get("sufficient_for_first_step"):
        return None

    seed_path = receipt.get("seed_path")
    seed_bound = bool(
        receipt.get("seed_sha256")
        or receipt.get("seed_snapshot_ref")
        or receipt.get("seed_snapshot_path")
    )
    seed_required = bool(seed_path and not seed_bound)
    success_status = (
        "exact_local_transfer_depth"
        if int(receipt.get("post_depth") or 1) > 1
        else "exact_first_step_transfer"
    )
    plan = {
        "source_receipt_schema": receipt.get("schema"),
        "source_receipt": "workspace/latest_level_transfer_probe.json",
        "carrier_evidence_identity": dict(
            receipt.get("carrier_evidence_identity") or {}
        ),
        "probe_kind": "level_boundary_first_step",
        "seed_prerequisite": {
            "seed_path": seed_path,
            "seed_bound": seed_bound,
            "status": (
                "replayable_seed_available"
                if not seed_required else "replayable_seed_missing"
            ),
            "next_action": (
                "recover or regenerate a replayable level-boundary seed before "
                "demanding same-seed transfer-probe exactness"
                if seed_required else ""
            ),
        },
        "residue_quotient": {
            "residue_class": residue_class,
            "cell_count": q.get("cell_count"),
            "all_action_invariant": q.get("all_action_invariant"),
            "all_predicted_equals_boundary": q.get("all_predicted_equals_boundary"),
            "cells": q.get("cells") or [],
        },
        "repair_certificate": {
            "repair_class": cert.get("repair_class"),
            "sufficient_for_first_step": bool(cert.get("sufficient_for_first_step")),
            "scope": cert.get("scope"),
            "repair_map": cert.get("repair_map") or [],
            "authority": cert.get("authority"),
        },
        "local_transfer": receipt.get("local_transfer") or {},
        "local_residue_quotient": receipt.get("local_residue_quotient") or {},
        "post_depth": receipt.get("post_depth", 1),
        "required_next_gate": {
            "command": (
                "recover_level_boundary_seed"
                if seed_required else "arc3_level_transfer_probe"
            ),
            "success_status": (
                "replayable_boundary_seed_available"
                if seed_required else success_status
            ),
            "expected_exact_actions": receipt.get("actions_tested"),
            "expected_exact_local_steps": (
                (receipt.get("local_transfer") or {}).get("steps_tested")
            ),
            "blocked_until": (
                "replayable_seed_available" if seed_required else ""
            ),
            "then_gate": (
                {
                    "command": "arc3_level_transfer_probe",
                    "success_status": success_status,
                }
                if seed_required else {}
            ),
            "adoption_authority": (
                "rerun probe exactness is necessary but not sufficient for "
                "canonical model adoption or level solve"
            ),
        },
    }
    family = f"compressed_counterexample_repair|{json.dumps(plan, sort_keys=True, default=str)}"
    return {
        "schema": STRATEGY_SCHEMA,
        "failure_family": family,
        "kind": "compressed_counterexample_repair",
        "rationale": (
            "level-boundary probe found a compact residue with a bounded "
            "sufficiency certificate"
            + (
                "; deeper local transfer shows the first-step repair is "
                "insufficient"
                if (receipt.get("local_transfer") or {}).get(
                    "first_step_repair_generalizes_to_depth"
                ) is False
                else ""
            )
        ),
        "falsifiable_prediction": (
            "after the replayable boundary seed prerequisite is available, "
            "repair or explicit waiver plus rerun of the level-transfer probe "
            "satisfies the transfer exactness gate"
            if seed_required else
            "after repair or explicit waiver, rerunning the level-transfer "
            "probe on the same seed satisfies the required_next_gate success_status"
        ),
        "action_plan": plan,
        "kill_condition": (
            "seed recovery fails or, after seed recovery, rerun still has a "
            "non-waived first-step mismatch, or the residue is no longer "
            "action-independent under the same seed"
            if seed_required else
            "rerun still has a non-waived first-step mismatch, or the residue "
            "is no longer action-independent under the same seed"
        ),
        "disposition": "open",
    }


def _local_has_refinement_hint(plan: dict) -> bool:
    local_q = plan.get("local_residue_quotient") or {}
    return any(
        isinstance(cls, dict) and isinstance(cls.get("refinement_hint"), dict)
        for cls in local_q.get("classes") or []
    )


def _local_refinement_hint_rank(plan: dict) -> int:
    local_q = plan.get("local_residue_quotient") or {}
    rank = 0
    for cls in local_q.get("classes") or []:
        if not isinstance(cls, dict):
            continue
        hint = cls.get("refinement_hint")
        if not isinstance(hint, dict):
            continue
        rank = max(rank, 1)
        if hint.get("candidate_class") == (
            "component_scoped_extremal_count_or_rate_refinement_candidate"
        ):
            rank = max(rank, 2)
    return rank


def _reject_superseded_narrow_cards(project: Path, new_card: dict) -> None:
    ledger = project / "workspace" / STRATEGY_LEDGER
    if not ledger.exists():
        return
    plan = new_card.get("action_plan") or {}
    if int(plan.get("post_depth") or 1) <= 1:
        return
    transfer = plan.get("local_transfer") or {}
    if transfer.get("first_step_repair_generalizes_to_depth") is not False:
        return
    rows = []
    for line in ledger.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    for row in rows:
        if row.get("kind") != "compressed_counterexample_repair":
            continue
        if row.get("failure_family_sha") == family_sha(new_card.get("failure_family")):
            continue
        old_plan = row.get("action_plan") or {}
        if old_plan.get("carrier_evidence_identity") != plan.get(
            "carrier_evidence_identity"
        ):
            continue
        if old_plan.get("source_receipt") != plan.get("source_receipt"):
            continue
        old_q = old_plan.get("residue_quotient") or {}
        new_q = plan.get("residue_quotient") or {}
        if old_q.get("residue_class") != new_q.get("residue_class"):
            continue
        new_seed = plan.get("seed_prerequisite") or {}
        old_seed = old_plan.get("seed_prerequisite") or {}
        if (
            new_seed.get("status") == "replayable_seed_missing"
            and old_seed.get("status") != "replayable_seed_missing"
        ):
            out = dict(row)
            out["disposition"] = "rejected"
            out["counterexample"] = (
                "superseded by seed-prerequisite-aware transfer receipt: "
                "same-seed transfer exactness cannot be demanded until a "
                "replayable boundary seed is available"
            )
            record_disposition(ledger, out)
            continue
        richer_local = bool(plan.get("local_residue_quotient"))
        older_local = bool(old_plan.get("local_residue_quotient"))
        old_depth = int(old_plan.get("post_depth") or 1)
        new_depth = int(plan.get("post_depth") or 1)
        old_hint_rank = _local_refinement_hint_rank(old_plan)
        new_hint_rank = _local_refinement_hint_rank(plan)
        old_gate = old_plan.get("required_next_gate") or {}
        new_gate = plan.get("required_next_gate") or {}
        same_receipt_clock = (
            old_plan.get("source_receipt") == plan.get("source_receipt")
            and old_gate.get("command") == new_gate.get("command")
            and old_gate.get("success_status") == new_gate.get("success_status")
        )
        if same_receipt_clock:
            out = dict(row)
            out["disposition"] = "rejected"
            out["counterexample"] = (
                "superseded by current level-transfer receipt on the same "
                "producer clock; keep only the latest quotient representative"
            )
            record_disposition(ledger, out)
            continue
        if old_depth > new_depth:
            continue
        if old_depth == new_depth and (old_hint_rank >= new_hint_rank) \
                and (older_local or not richer_local):
            continue
        out = dict(row)
        out["disposition"] = "rejected"
        out["counterexample"] = (
            "superseded by richer post-depth transfer receipt: first-step "
            "repair does not generalize to the probed local transfer depth"
        )
        record_disposition(ledger, out)


def _reactivate_current_card_if_closed(project: Path, card: dict) -> list[dict]:
    """Re-open a current receipt card that was closed by older routing evidence.

    The Strategy decision membrane is intentionally idempotent by family hash. Current
    receipt readers need one extra lifecycle move: if the latest typed receipt
    still demands the same work order, and the only matching ledger row is
    closed, the reader may restore it to open. This is routing only; it does not
    certify a model or weaken replay/holdout gates.
    """
    ledger = project / "workspace" / STRATEGY_LEDGER
    if any(
        row.get("failure_family_sha") == card.get("failure_family_sha")
        for row in open_cards(ledger)
    ):
        return []
    sha = card.get("failure_family_sha") or family_sha(card.get("failure_family"))
    latest: dict | None = None
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("failure_family_sha") == sha:
                latest = row
    if not latest or latest.get("disposition") == "open":
        return []
    reopened = dict(card)
    reopened["disposition"] = "open"
    reopened["reactivation"] = {
        "reason": "latest_level_transfer_receipt_still_demands_card",
        "previous_disposition": latest.get("disposition"),
        "previous_counterexample": latest.get("counterexample"),
        "authority": (
            "reactivates Strategy Office routing only; replay/holdout/live "
            "gates remain candidate authority"
        ),
    }
    return [record_disposition(ledger, reopened)]


def write_level_transfer_repair_card(project: str | Path) -> list[dict]:
    project = Path(project)
    receipt_path = project / "workspace" / "latest_level_transfer_probe.json"
    if not receipt_path.exists():
        return []
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict):
        return []
    try:
        current = resolve_current_carrier_evidence_identity(project)
        binding = require_current_carrier_evidence_binding(receipt, current)
    except (CarrierEvidenceIdentityError, OSError, TypeError, ValueError):
        # The file remains historical telemetry, but it cannot open or
        # reactivate a current-population Strategy Office work order.
        return []
    receipt = {**receipt, "carrier_evidence_identity": binding}
    card = build_compressed_counterexample_repair_card(receipt)
    if card is None:
        return []
    _reject_superseded_narrow_cards(project, card)
    written = list(submit_strategy_card_batch(StrategyCardBatchSubmission(
        project_dir=project,
        cards=[card],
        source_ref="level_transfer_repair:latest_level_transfer_probe",
    )).get("written_cards") or [])
    if written:
        return written
    return _reactivate_current_card_if_closed(project, card)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    args = ap.parse_args(argv)
    written = write_level_transfer_repair_card(Path(args.project))
    print(json.dumps({
        "schema": "ztare-level-transfer-repair-card-result-v1",
        "project": args.project,
        "cards_written": len(written),
        "written": written,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
