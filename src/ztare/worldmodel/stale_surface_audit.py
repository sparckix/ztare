"""Project-level stale-surface audit for worldmodel loops.

This is a producer, not a briefing provider. It may run the project-local
deterministic gate and update ledgers under existing receipt rules. Prompt
providers should read its receipt; they should not recreate the sweep.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.common.candidate_memory import admissible_candidate_memory_records
from ztare.common.strategy_card_roles import active_strategy_cards
from ztare.research_director.strategy_office import STRATEGY_LEDGER
from ztare.worldmodel.residual_repair import (
    reject_satisfied_seed_prerequisite_cards,
    sync_replay_residual_repair_card,
)

RECEIPT_SCHEMA = "ztare-worldmodel-stale-surface-audit-v1"
RECEIPT_PATH = "workspace/stale_surface_audit.json"


def _sha_path(path: Path) -> str:
    try:
        if path.exists() and path.is_file():
            return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:  # noqa: BLE001
        pass
    return ""


def _input_fingerprint(project: Path) -> dict[str, str]:
    out = {
        "test_model.py": _sha_path(project / "test_model.py"),
        "strategy_experiments.jsonl": _sha_path(project / "workspace" / STRATEGY_LEDGER),
        "candidate_memory.json": _sha_path(project / "workspace" / "candidate_memory.json"),
        "latest_eval_results.json": _sha_path(project / "latest_eval_results.json"),
    }
    try:
        from ztare.common.observation_chart import capture_project_evidence_epoch

        out["evidence_epoch"] = capture_project_evidence_epoch(project).epoch_sha256
    except Exception:  # noqa: BLE001
        # Missing evidence keeps the audit usable for project bootstrap.  Once
        # evidence exists, its content identity participates in every cache
        # comparison; a `latest` evaluation filename cannot stand in for it.
        out["evidence_epoch"] = ""
    for seed in sorted((project / "workspace").glob("*level*seed*.json")):
        out[f"boundary_seed:{seed.name}"] = _sha_path(seed)
    return out


def _load_cached(project: Path, fingerprint: dict[str, str]) -> dict[str, Any] | None:
    path = project / RECEIPT_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not stale_surface_receipt_is_current(
        project,
        payload,
        fingerprint=fingerprint,
    ):
        return None
    cached = dict(payload)
    cached["cached"] = True
    return cached


def stale_surface_receipt_is_current(
    project: str | Path,
    payload: object,
    *,
    fingerprint: dict[str, str] | None = None,
) -> bool:
    """Whether an audit receipt names the project's current input identity.

    Consumers must not infer currentness from the ``latest`` filename.  This is
    the same compatibility check used by the producer's cache path, exposed so
    read-only briefing consumers cannot revive a superseded carrier/evidence
    projection.
    """

    if not isinstance(payload, dict) or payload.get("schema") != RECEIPT_SCHEMA:
        return False
    current = fingerprint if fingerprint is not None else _input_fingerprint(Path(project))
    return bool(
        payload.get("input_fingerprint") == current
        or payload.get("input_fingerprint_after") == current
    )


def _write_receipt(project: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    path = project / RECEIPT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def _visible_diagnostics(gate_payload: dict[str, Any]) -> dict[str, Any]:
    gates = gate_payload.get("gates") or {}
    if isinstance(gates, list):
        gates = {
            str(g.get("name") or i): g
            for i, g in enumerate(gates)
            if isinstance(g, dict)
        }
    if not isinstance(gates, dict):
        return {}
    visible = gates.get("visible_replay_exact") or {}
    if not isinstance(visible, dict):
        return {}
    diagnostics = visible.get("diagnostics") or {}
    return diagnostics if isinstance(diagnostics, dict) else {}


def _run_gate(
    project: Path,
    *,
    timeout_seconds: int,
    candidate_path: Path | None = None,
) -> dict[str, Any] | None:
    harness = project / "gate_harness.py"
    if not harness.exists():
        return None
    cmd = [
        sys.executable,
        str(harness.resolve()),
        "--emit-deterministic-gates",
    ]
    if candidate_path is not None:
        cmd.extend(["--candidate-path", str(candidate_path.resolve())])
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        cwd=project,
    )
    if res.returncode != 0:
        raise RuntimeError(
            "gate_harness.py exited nonzero "
            f"({res.returncode}): {res.stderr.strip()[:500]}"
        )
    payload = json.loads(res.stdout or "{}")
    if not isinstance(payload, dict):
        raise TypeError("gate_harness.py emitted non-object JSON")
    return payload


def _best_candidate_memory_path(project: Path) -> tuple[dict[str, Any] | None, Path | None]:
    records = admissible_candidate_memory_records(project)
    if not records:
        return None, None

    def rank(rec: dict[str, Any]) -> tuple[int, int, float, int]:
        return (
            int(rec.get("visible_exact_rows") or 0),
            int(rec.get("holdout_depth") or 0),
            float(rec.get("gate_score") or 0.0),
            -int(rec.get("visible_wrong_cells") or 0),
        )

    for rec in sorted(records, key=rank, reverse=True):
        rel = str(rec.get("submission") or "").strip()
        if not rel:
            continue
        for path in (project / rel, project / "workspace" / rel):
            if path.exists() and path.is_file():
                return rec, path
    return None, None


def _diagnostics_rank(diagnostics: dict[str, Any]) -> tuple[int, int]:
    return (
        int(diagnostics.get("exact_rows") or 0),
        -int(diagnostics.get("wrong_cell_count") or 0),
    )


def _candidate_dominates_root(
    candidate_rec: dict[str, Any] | None,
    root_diagnostics: dict[str, Any],
) -> bool:
    if not isinstance(candidate_rec, dict) or not root_diagnostics:
        return False
    checked = int(root_diagnostics.get("checked_rows") or 0)
    cand_checked = int(candidate_rec.get("visible_checked_rows") or 0)
    if checked <= 0 or cand_checked < checked:
        return False
    candidate_rank = (
        int(candidate_rec.get("visible_exact_rows") or 0),
        -int(candidate_rec.get("visible_wrong_cells") or 0),
    )
    return candidate_rank > _diagnostics_rank(root_diagnostics)


def _open_card_summary(project: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for card in active_strategy_cards(project / "workspace" / STRATEGY_LEDGER):
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        residue = plan.get("residue_quotient") if isinstance(plan.get("residue_quotient"), dict) else {}
        gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
        out.append({
            "kind": card.get("kind"),
            "failure_family_sha": card.get("failure_family_sha"),
            "residue_class": residue.get("residue_class"),
            "next_gate": gate.get("command"),
            "next_status": gate.get("success_status"),
        })
    return out


def run_stale_surface_audit(
    project: str | Path,
    *,
    apply: bool = False,
    timeout_seconds: int = 120,
    force: bool = False,
    gate_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audit and optionally dispose stale worldmodel routing surfaces."""
    root = Path(project)
    fingerprint = _input_fingerprint(root)
    if not force:
        cached = _load_cached(root, fingerprint)
        if cached is not None:
            return cached

    actions: list[dict[str, Any]] = []
    errors: list[str] = []
    root_gate_payload: dict[str, Any] | None = None
    active_gate_payload: dict[str, Any] | None = None
    root_diagnostics: dict[str, Any] = {}
    diagnostics: dict[str, Any] = {}
    active_candidate_rec: dict[str, Any] | None = None
    active_candidate_path: Path | None = None
    carrier_source = "project_root"
    try:
        if isinstance(gate_payload, dict) and gate_payload:
            active_gate_payload = gate_payload
            diagnostics = _visible_diagnostics(gate_payload)
            carrier_source = "configured_system1_gate"
        else:
            root_gate_payload = _run_gate(root, timeout_seconds=timeout_seconds)
            root_diagnostics = _visible_diagnostics(root_gate_payload or {})
            diagnostics = root_diagnostics
            active_gate_payload = root_gate_payload
        candidate_rec, candidate_path = _best_candidate_memory_path(root)
        if gate_payload is None and _candidate_dominates_root(candidate_rec, root_diagnostics):
            try:
                candidate_gate = _run_gate(
                    root,
                    timeout_seconds=timeout_seconds,
                    candidate_path=candidate_path,
                )
                candidate_diagnostics = _visible_diagnostics(candidate_gate or {})
                if _diagnostics_rank(candidate_diagnostics) >= _diagnostics_rank(root_diagnostics):
                    active_gate_payload = candidate_gate
                    diagnostics = candidate_diagnostics
                    active_candidate_rec = candidate_rec
                    active_candidate_path = candidate_path
                    carrier_source = "candidate_memory"
            except Exception as exc:  # noqa: BLE001
                errors.append(f"candidate_memory_gate_error:{type(exc).__name__}:{exc}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"gate_harness_error:{type(exc).__name__}:{exc}")

    if apply:
        rejected_seed = reject_satisfied_seed_prerequisite_cards(root)
        if rejected_seed:
            actions.append({
                "action": "reject_satisfied_seed_prerequisite_cards",
                "count": len(rejected_seed),
                "shas": [r.get("failure_family_sha") for r in rejected_seed],
            })
        if diagnostics:
            sync = sync_replay_residual_repair_card(
                root,
                diagnostics,
                source_ref="workspace/stale_surface_audit.json:active_carrier_gate",
            )
            actions.append({
                "action": "sync_replay_residual_repair_card",
                "rejected_stale_cards": sync.get("rejected_stale_cards"),
                "rejected_candidate_dominated_cards": sync.get(
                    "rejected_candidate_dominated_cards"
                ),
                "cards_written": sync.get("cards_written"),
                "written_shas": [
                    row.get("failure_family_sha")
                    for row in sync.get("written", [])
                    if isinstance(row, dict)
                ],
            })

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "project": str(root),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "applied": bool(apply),
        "cached": False,
        "input_fingerprint": fingerprint,
        "gate": {
            "ran": active_gate_payload is not None,
            "harness_ok": bool((active_gate_payload or {}).get("harness_ok")),
            "gated_sha256": (active_gate_payload or {}).get("gated_sha256"),
        },
        "active_carrier": {
            "source": carrier_source,
            "candidate_submission": (
                str(active_candidate_rec.get("submission") or "")
                if active_candidate_rec else ""
            ),
            "candidate_sha": (
                str(active_candidate_rec.get("sha") or "")
                if active_candidate_rec else ""
            ),
            "candidate_path": str(active_candidate_path) if active_candidate_path else "",
        },
        "root_replay": {
            "checked_rows": root_diagnostics.get("checked_rows"),
            "exact_rows": root_diagnostics.get("exact_rows"),
            "wrong_rows": root_diagnostics.get("wrong_rows"),
            "wrong_cell_count": root_diagnostics.get("wrong_cell_count"),
            "top_mismatch_class": (
                root_diagnostics.get("mismatch_classes", [None])[0]
                if isinstance(root_diagnostics.get("mismatch_classes"), list)
                and root_diagnostics.get("mismatch_classes")
                else None
            ),
        },
        "current_replay": {
            "checked_rows": diagnostics.get("checked_rows"),
            "exact_rows": diagnostics.get("exact_rows"),
            "wrong_rows": diagnostics.get("wrong_rows"),
            "wrong_cell_count": diagnostics.get("wrong_cell_count"),
            "top_mismatch_class": (
                diagnostics.get("mismatch_classes", [None])[0]
                if isinstance(diagnostics.get("mismatch_classes"), list)
                and diagnostics.get("mismatch_classes")
                else None
            ),
        },
        "actions": actions,
        "open_cards_after": _open_card_summary(root),
        "errors": errors,
        "authority": (
            "audit may update routing ledgers from current deterministic "
            "receipts; candidate adoption still belongs to replay/holdout/"
            "terminal gates"
        ),
    }
    receipt["input_fingerprint_after"] = _input_fingerprint(root)
    return _write_receipt(root, receipt)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--timeout-seconds", type=int, default=120)
    args = ap.parse_args(argv)
    print(json.dumps(
        run_stale_surface_audit(
            args.project,
            apply=args.apply,
            timeout_seconds=args.timeout_seconds,
            force=args.force,
        ),
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
