from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ztare.common.science_output_policy import INVESTIGATED_STAGNATION_K
from ztare.validator.worldmodel_typed_payload import extract_worldmodel_control_receipts
from ztare.workspace.evidence_gaps import (
    LOCAL_VERIFICATION_RECOVERY_CHANNEL,
    LOCAL_VERIFICATION_RECOVERY_KIND,
)

__all__ = [
    "build_worldmodel_control_only_eval",
    "check_worldmodel_control_only_submission",
    "INVESTIGATED_STAGNATION_K",
]

# Visible episode is the ONLY provenance a witness may cite (contamination
# firewall, mirrors spec_nogood.py: episode_002 is the rollout holdout and a
# witness from it silently trains on the gate). Kept in sync with
# evidence_quotients.EVIDENCE_LOG_ALIASES.
_VISIBLE_EPISODE = "raw/episodes/episode_001.jsonl"
_HOLDOUT_EPISODE = "raw/episodes/episode_002.jsonl"


def _eliminated_signature(eliminated_hypothesis: Any) -> str:
    """Stable signature for an eliminated hypothesis class, keyed on its content
    so a restated elimination dedups against the visible nogood ledger."""
    payload = json.dumps(eliminated_hypothesis, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _validate_investigated_receipt(
    payload: dict[str, Any],
    *,
    project_dir: "Path | str | None",
    known_signatures: "set[str]",
) -> tuple[bool, str, "str | None"]:
    """Validate one INVESTIGATED receipt payload against the credit contract.

    Returns (credited, reason, signature). credited is True IFF the elimination
    is NEW (§1), the witness CHECKS OUT on visible evidence (§2), and the witness
    is VISIBLE-only (§3). A holdout witness RAISES (firewall) — a leaf may not
    even offer one. Any other failure returns credited=False with a loud reason
    for rejected-with-reason recording; the turn then falls back to no_candidate.
    """
    eliminated = payload.get("eliminated_hypothesis")
    if eliminated in (None, "", {}, []):
        return False, "investigated_missing_eliminated_hypothesis", None
    witness = payload.get("witness")
    if not isinstance(witness, dict):
        return False, "investigated_missing_witness", None

    # §3 FIREWALL — assert BEFORE anything else; a holdout witness must never be
    # silently tolerated. Raise, mirroring spec_nogood.assert_visible.
    for ref in payload.get("evidence_refs") or []:
        if _HOLDOUT_EPISODE in str(ref):
            raise ValueError(
                "investigated firewall: witness cites holdout evidence "
                f"{ref!r}; a leaf may only eliminate on visible episode evidence."
            )
    src = str(witness.get("source") or witness.get("episode") or "")
    if _HOLDOUT_EPISODE in src:
        raise ValueError(
            "investigated firewall: witness source is the holdout episode; "
            "eliminations must be witnessed on the visible episode."
        )

    signature = _eliminated_signature(eliminated)
    # §1 NEW — a duplicate elimination is rejected, not credited.
    if signature in known_signatures:
        return False, "investigated_duplicate_elimination", signature

    # §2 EVIDENCE-BACKED — load the visible episode, find (t, a), confirm the
    # observed cell matches payload.witness.observed and DIFFERS from predicted.
    try:
        t = int(witness["t"])
        a = int(witness["a"])
        cell = witness["cell"]
        row, col = int(cell[0]), int(cell[1])
        observed = int(witness["observed"])
        predicted = int(witness["predicted"])
    except (KeyError, TypeError, ValueError, IndexError):
        return False, "investigated_malformed_witness", signature
    if observed == predicted:
        # The hypothesis must genuinely predict wrong here, else nothing refuted.
        return False, "investigated_witness_not_refuting", signature
    if project_dir is None:
        return False, "investigated_no_project_for_witness_check", signature

    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.grid_dsl import grid_to_lists

    ep_path = Path(project_dir) / _VISIBLE_EPISODE
    if not ep_path.exists():
        return False, "investigated_visible_episode_missing", signature
    match = None
    for tr in EpisodeLog.read_jsonl(ep_path):
        if int(tr.t) == t and int(tr.a) == a:
            match = tr
            break
    if match is None:
        return False, "investigated_witness_transition_not_in_visible", signature
    grid = grid_to_lists(match.s_next)
    if not (0 <= row < len(grid) and 0 <= col < len(grid[0])):
        return False, "investigated_witness_cell_out_of_bounds", signature
    actual = int(grid[row][col])
    if actual != observed:
        # The cited transition does not show the claimed observation — the
        # leaf's own evidence does not support its elimination. Anti-gaming.
        return False, "investigated_witness_does_not_check_out", signature
    # observed == actual and observed != predicted: the hypothesis (which
    # predicts `predicted`) is genuinely refuted by visible evidence. CREDIT.
    return True, "investigated_credited", signature


def check_worldmodel_control_only_submission(
    wm_payload: dict[str, Any],
    *,
    raw_text: str,
) -> "dict[str, Any] | None":
    """Decide whether a parsed worldmodel typed-payload is a control-only turn.

    Returns a sentinel dict when the receipt family grants may_omit_candidate
    (INVESTIGATED, LOWERABILITY_BLOCKED, or registered workbench action) and the
    carrier (test_model_py) is empty. Returns None for normal candidate turns.

    This helper is the pure-function seam that _prepare_mutation_candidate delegates
    to, separated here so tests can import and cover it without pulling in the
    autoresearch_loop module (which exits on argparse at import time).
    """
    from ztare.common.candidate_first_policy import (
        candidate_first_empty_candidate_decision as _co_decision,
    )
    from ztare.validator.worldmodel_typed_payload import (
        _candidate_delta_blocked_by_receipts as _co_blocked,
    )

    wm_code = str(wm_payload.get("test_model_py") or "").strip()
    if wm_code:
        return None  # has a carrier — normal path

    receipts = wm_payload.get("control_receipts") or []
    receipt_types: set[str] = {
        str(r.get("type") or "").strip()
        for r in receipts
        if isinstance(r, dict)
    }
    co_dec = _co_decision(
        receipt_types,
        lowerability_blocked=_co_blocked(wm_payload),
    )
    if not co_dec.may_omit_candidate:
        return None

    return {
        "control_only": True,
        "reasons": list(co_dec.reasons),
        "thesis_text": raw_text,
    }


def build_worldmodel_control_only_eval(
    *,
    run_id: int,
    iteration: int,
    thesis_text: str,
    artifact_refs: list[str],
    timestamp: str | None = None,
    project_dir: "Path | str | None" = None,
) -> dict[str, Any]:
    """Build the durable eval row for a no-carrier worldmodel control move.

    A control-only turn is not a candidate failure to be paraphrased away. It is
    a boundary-CEGAR state transition. Persist the typed receipts and expose any
    lowerability blocker as a local-verification evidence gap so the next
    iteration can continue from the same control object.
    """

    control_receipts = extract_worldmodel_control_receipts(thesis_text or "")
    lowerability_payloads = [
        row.get("payload")
        for row in control_receipts
        if isinstance(row, dict)
        and str(row.get("type") or "") == "LOWERABILITY_BLOCKED"
        and isinstance(row.get("payload"), dict)
    ]
    evidence_gaps = [
        _lowerability_payload_to_evidence_gap(payload)
        for payload in lowerability_payloads
        if isinstance(payload, dict)
    ]
    apparatus_obstructions: list[dict[str, Any]] = []
    if project_dir is not None:
        from ztare.common.harness_weakness import (
            write_lowerability_harness_weakness_receipt,
        )

        for payload in lowerability_payloads:
            if not isinstance(payload, dict):
                continue
            receipt = write_lowerability_harness_weakness_receipt(
                project_dir=project_dir,
                blocker_payload=payload,
            )
            if receipt is not None:
                apparatus_obstructions.append(receipt)

    credited, rejected = _process_investigated_receipts(
        control_receipts, project_dir=project_dir
    )

    eval_row: dict[str, Any] = {
        "run_id": run_id,
        "iteration": iteration,
        "score": 0,
        "raw_judge_score": 0,
        "weakest_point": _control_weakest_point(lowerability_payloads),
        "score_cap_reason": "worldmodel_control_only_no_candidate",
        "control_receipts": control_receipts,
        "lowerability_blockers": lowerability_payloads,
        "evidence_gaps": evidence_gaps,
        "artifact_refs": [ref for ref in artifact_refs if str(ref or "").strip()],
        "timestamp": timestamp or datetime.now().isoformat(),
    }
    if apparatus_obstructions:
        eval_row["apparatus_obstructions"] = apparatus_obstructions
        if "workspace/latest_harness_weakness.json" not in eval_row["artifact_refs"]:
            eval_row["artifact_refs"].append("workspace/latest_harness_weakness.json")
    if rejected:
        # Fail loud: a rejected/duplicate/unbacked elimination is recorded with
        # its reason, never silently credited. The turn keeps the no_candidate
        # classification below.
        eval_row["investigated_rejections"] = rejected
    if credited:
        # Investigation that eliminated a NEW, evidence-backed hypothesis class
        # is PROGRESS, not a failed iteration. Classification carries the credit;
        # the numeric score stays 0 (an investigation is not a candidate score).
        eval_row["score_cap_reason"] = "worldmodel_investigated_residual_narrowed"
        eval_row["investigated_eliminations"] = [c["signature"] for c in credited]
        eval_row["investigated_credited"] = True
        eval_row["weakest_point"] = (
            "WORLD_MODEL_INVESTIGATED: probes eliminated "
            f"{len(credited)} new hypothesis class(es) from visible evidence; "
            "the residual narrowed. Continue from the pruned constraint DB."
        )
    return eval_row


def _process_investigated_receipts(
    control_receipts: list[dict[str, Any]],
    *,
    project_dir: "Path | str | None",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate INVESTIGATED receipts and, on credit, persist the eliminated
    hypothesis to the visible nogood ledger. Returns (credited, rejected).

    Dedup (§1) reads the ledger's existing visible signatures, so a restated
    elimination — even across turns — is rejected. Credited eliminations are
    written back to the same ledger so the next turn's search is pruned.
    """
    investigated = [
        row.get("payload")
        for row in control_receipts
        if isinstance(row, dict)
        and str(row.get("type") or "") == "INVESTIGATED"
        and isinstance(row.get("payload"), dict)
    ]
    if not investigated:
        return [], []

    ledger = None
    known: set[str] = set()
    if project_dir is not None:
        from ztare.worldmodel.spec_nogood import SpecNogoodLedger

        ledger = SpecNogoodLedger(project_dir)
        known = set(ledger.visible_clauses().keys())

    credited: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for payload in investigated:
        ok, reason, signature = _validate_investigated_receipt(
            payload, project_dir=project_dir, known_signatures=known
        )
        if ok and signature is not None:
            known.add(signature)  # de-dup within this same turn too
            if ledger is not None:
                _record_investigated_clause(ledger, signature, payload)
            credited.append({"signature": signature, "eliminated": payload.get("eliminated_hypothesis")})
        else:
            rejected.append({"reason": reason, "signature": signature})
    return credited, rejected


def _record_investigated_clause(ledger, signature: str, payload: dict[str, Any]) -> None:
    """Append a visible-provenance conflict clause for a credited elimination,
    mirroring SpecNogoodLedger.record_visible's row shape (evidence=='visible',
    so the firewall admits it and later turns can consult it for dedup)."""
    witness = payload.get("witness") or {}
    row = {
        "signature": signature,
        "witness_summary": (
            "investigated elimination "
            f"t={witness.get('t')} a={witness.get('a')} cell={witness.get('cell')} "
            f"observed={witness.get('observed')} refuted_prediction={witness.get('predicted')}"
        ),
        "provenance": {
            "source": "investigated_science_turn",
            "evidence": "visible",
            "eliminated_hypothesis": payload.get("eliminated_hypothesis"),
            "witness": witness,
            "evidence_refs": list(payload.get("evidence_refs") or []),
        },
    }
    ledger.path.parent.mkdir(parents=True, exist_ok=True)
    with ledger.path.open("a") as f:
        f.write(json.dumps(row) + "\n")


def _control_weakest_point(lowerability_payloads: list[Any]) -> str:
    if not lowerability_payloads:
        return (
            "WORLD_MODEL_CONTROL_ONLY: typed control submission ended without an "
            "executable candidate. Continue from the attached control_receipts; "
            "submit a transportable candidate if the visible receipt family admits "
            "lowering, otherwise preserve the typed obstruction."
        )
    payload = lowerability_payloads[0]
    if not isinstance(payload, dict):
        return "LOWERABILITY_BLOCKED: malformed payload persisted for audit."
    return (
        "LOWERABILITY_BLOCKED: "
        f"{str(payload.get('obstruction') or '').strip()} "
        f"missing={str(payload.get('missing_witness_or_sensor') or '').strip()} "
        f"next={str(payload.get('next_action') or '').strip()}"
    ).strip()


def _lowerability_payload_to_evidence_gap(payload: dict[str, Any]) -> dict[str, Any]:
    missing = str(payload.get("missing_witness_or_sensor") or "").strip()
    obstruction = str(payload.get("obstruction") or "").strip()
    evidence_refs = [
        str(ref).strip()
        for ref in (payload.get("evidence_refs") or [])
        if str(ref or "").strip()
    ]
    return {
        "gap_type": "lowerability_blocked",
        "description": obstruction or missing or "No gamma-lowerable candidate witness was produced.",
        "required_surface": missing or "gamma_lowerable_candidate_witness",
        "recovery_kind": LOCAL_VERIFICATION_RECOVERY_KIND,
        "recovery_channel": LOCAL_VERIFICATION_RECOVERY_CHANNEL,
        "in_loop_consumable": True,
        "can_public_fetch": False,
        "next_action": str(payload.get("next_action") or "").strip(),
        "evidence_refs": evidence_refs,
    }
