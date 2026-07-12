from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ztare.common.operator_proposal_contract import open_cards, record_disposition
from ztare.common.worldmodel_carrier_purity import carrier_contract_error
from ztare.validator.core.pre_judge_gate import detect_patch_base_regression_preflight
from ztare.worldmodel.goal_abduction import predicate_from_spec
from ztare.worldmodel.refuted_experiments import RefutedExperimentsLedger


EXPERIMENT_LEDGER = "strategy_experiments.jsonl"
EXPERIMENT_EXECUTIONS = "strategy_experiment_executions.jsonl"
EXPERIMENT_PROBE_ROWS = "strategy_experiment_probe_rows.jsonl"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def _probe_registry() -> dict[str, set[str]]:
    return {
        "reachability_sweep_to_goal": {"goal_predicate_spec"},
        "targeted_action_path_probe": {"paths"},
        "coverage_gap_probe": {"paths"},
        "conjunction_activation_probe": {"goal_predicate_spec"},
        "horizon_exhaustion_probe": {"paths"},
        "carrier_repair_probe": {"repair_carrier", "target_residual_class"},
        "evidence_probe": {"probe_source"},
        # Battery-advertised kinds executed via separate codepaths (residual_repair,
        # briefing_providers, etc.); registered here so _lowerable_card passes them
        # through to _default_probe_runner which blocks gracefully via "no probe harness"
        # instead of silently producing rejected_unlowerable.
        # ponytail: add execution harnesses if/when these kinds need direct probe runs
        "compressed_counterexample_repair": {"source_receipt"},
        "disposition_backlog_review": {"paths"},
        "semantic_deanchor_receipt_compile": {"paths"},
        "scheduler_counterexample_review": {"paths"},
    }


def _lowerable_card(card: dict[str, Any]) -> bool:
    plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
    paths = plan.get("paths")
    if isinstance(paths, list) and paths:
        return True
    repair_carrier = plan.get("repair_carrier")
    if isinstance(repair_carrier, str) and repair_carrier.strip():
        residual = str(plan.get("target_residual_class") or "").strip()
        return bool(residual)
    repair_carrier_source = str(plan.get("repair_carrier_source") or plan.get("repair_carrier_src") or "").strip()
    if repair_carrier_source:
        residual = str(plan.get("target_residual_class") or "").strip()
        return bool(residual)
    # Observation sort: inline probe_source is lowerable on its own. Carrier
    # fields are checked first above, so a card carrying both routes (and
    # gates) as a carrier card — carrier wins.
    if str(plan.get("probe_source") or "").strip():
        return True
    pspec = plan.get("goal_predicate_spec")
    if isinstance(pspec, dict) and pspec:
        try:
            fn = predicate_from_spec(pspec, [[0]])
            return callable(fn)
        except Exception:
            return False
    kind = str(card.get("kind") or "").strip()
    probe_params = plan.get("probe_params") if isinstance(plan.get("probe_params"), dict) else {}
    if kind == "carrier_repair_probe":
        return bool(
            str(plan.get("target_residual_class") or "").strip()
            and (
                str(plan.get("repair_carrier") or "").strip()
                or str(plan.get("repair_carrier_source") or plan.get("repair_carrier_src") or "").strip()
            )
        )
    required = _probe_registry().get(kind)
    if not required:
        return False
    # Check probe_params first, then fall back to top-level action_plan fields
    # (battery-advertised kinds like compressed_counterexample_repair carry their
    # required fields directly in action_plan, not nested under probe_params).
    available = {k for k, v in probe_params.items() if v not in (None, "", [], {})}
    available |= {k for k, v in plan.items() if k != "probe_params" and v not in (None, "", [], {})}
    return bool(required.issubset(available))


def _sandboxed_carrier_path(project_dir: Path, plan: dict[str, Any]) -> tuple[Path, str]:
    repair_carrier = plan.get("repair_carrier")
    if isinstance(repair_carrier, str) and repair_carrier.strip():
        candidate_ref = repair_carrier.strip()
        candidate_path = (project_dir / candidate_ref).resolve()
        try:
            candidate_path.relative_to(project_dir.resolve())
        except ValueError as exc:
            raise ValueError(f"repair_carrier escapes project: {candidate_ref}") from exc
        if not candidate_path.is_file():
            raise ValueError(f"repair_carrier does not exist: {candidate_ref}")
        return candidate_path, candidate_ref
    inline_source = str(plan.get("repair_carrier_source") or plan.get("repair_carrier_src") or "").strip()
    if inline_source:
        if carrier_contract_error(inline_source) is not None:
            raise ValueError(carrier_contract_error(inline_source))
        digest = hashlib.sha256(inline_source.encode("utf-8")).hexdigest()
        rel = Path("workspace") / "strategy_experiment_carriers" / f"{digest}.py"
        carrier_path = (project_dir / rel).resolve()
        carrier_path.parent.mkdir(parents=True, exist_ok=True)
        carrier_path.write_text(inline_source + "\n", encoding="utf-8")
        return carrier_path, str(rel)
    raise ValueError("carrier_repair_probe requires repair_carrier or repair_carrier_source")


def _carrier_repair_probe_outcome(project_dir: Path, card: dict[str, Any]) -> dict[str, Any]:
    plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
    try:
        carrier_path, carrier_ref = _sandboxed_carrier_path(project_dir, plan)
    except ValueError as exc:
        # Receipt, not crash: name the defect so the next convene sees it,
        # and let the rest of the --all-open batch run.
        return {
            "schema": "ztare-strategy-experiment-probe-outcome-v1",
            "status": "blocked",
            "summary": f"carrier not runnable: {exc}",
            "live_rows": [],
            "observed_status": "carrier_unresolvable",
        }
    result = detect_patch_base_regression_preflight(
        enabled=True,
        project_dir=project_dir,
        candidate_path=carrier_path,
    )
    if result is None:
        return {
            "schema": "ztare-strategy-experiment-probe-outcome-v1",
            "status": "ok",
            "summary": "carrier survived strict-improvement gate",
            "live_rows": [
                {
                    "schema": "ztare-strategy-experiment-probe-row-v1",
                    "kind": "carrier_repair_probe",
                    "carrier_ref": carrier_ref,
                    "status": "survived",
                }
            ],
            "observed_status": "survived",
            "carrier_ref": carrier_ref,
        }
    receipt = result.regression_receipt
    trace = result.counterexample_trace
    summary = json.dumps(
        {
            "candidate_relation": receipt.get("candidate_relation"),
            "candidate_exact_rows": receipt.get("candidate_exact_rows"),
            "candidate_holdout_depth": receipt.get("candidate_holdout_depth"),
            "best_prior_exact_rows": receipt.get("best_prior_exact_rows"),
            "best_prior_holdout_depth": receipt.get("best_prior_holdout_depth"),
            "first_mismatch": receipt.get("first_mismatch"),
            "holdout_witness": receipt.get("holdout_witness") or trace.get("holdout_witness") or {},
        },
        sort_keys=True,
        default=str,
    )
    return {
        "schema": "ztare-strategy-experiment-probe-outcome-v1",
        "status": "blocked",
        "summary": summary,
        "live_rows": [
            {
                "schema": "ztare-strategy-experiment-probe-row-v1",
                "kind": "carrier_repair_probe",
                "carrier_ref": carrier_ref,
                "status": "killed",
                "counterexample_trace": trace,
            }
        ],
        "observed_status": "counterexample",
        "carrier_ref": carrier_ref,
        "counterexample": receipt,
        "counterexample_trace": trace,
    }


def _evidence_probe_outcome(project_dir: Path, probe_source: str) -> dict[str, Any]:
    from ztare.worldmodel.evidence_probe import run_evidence_probe

    receipt = run_evidence_probe(project_dir, probe_source)
    ok = str(receipt.get("status") or "") == "ok"
    row = {
        "schema": "ztare-strategy-experiment-probe-row-v1",
        "kind": "evidence_probe",
        "probe_sha": receipt.get("probe_sha"),
        "status": "observed" if ok else "probe_error",
        "receipt": receipt,
    }
    if ok:
        return {
            "schema": "ztare-strategy-experiment-probe-outcome-v1",
            "status": "ok",
            "summary": "evidence probe observed: "
            + json.dumps(receipt.get("payload"), sort_keys=True, default=str),
            "live_rows": [row],
            "observed_status": "observed",
            "probe_receipt": receipt,
        }
    return {
        "schema": "ztare-strategy-experiment-probe-outcome-v1",
        "status": "blocked",
        "summary": f"evidence probe error: {receipt.get('error')}",
        "live_rows": [row],
        "observed_status": "probe_error",
        "probe_receipt": receipt,
    }


def _default_probe_runner(project_dir: Path, card: dict[str, Any]) -> dict[str, Any]:
    plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
    kind = str(card.get("kind") or "").strip()
    # Dispatch by capability, not kind label: any card carrying a repair
    # carrier + target residual class routes to the carrier probe — the same
    # fields _lowerable_card accepts. Lowerable-but-unroutable must not exist.
    has_carrier = str(plan.get("repair_carrier") or "").strip() or str(
        plan.get("repair_carrier_source") or plan.get("repair_carrier_src") or ""
    ).strip()
    if kind == "carrier_repair_probe" or (
        has_carrier and str(plan.get("target_residual_class") or "").strip()
    ):
        return _carrier_repair_probe_outcome(project_dir, card)
    # Observation sort: any card carrying inline probe_source (and no carrier,
    # handled above) routes to the governed evidence probe.
    probe_source = str(plan.get("probe_source") or "").strip()
    if probe_source:
        return _evidence_probe_outcome(project_dir, probe_source)
    probe_path = project_dir / "workspace" / f"probe_{kind}.py"
    if not probe_path.exists():
        return {
            "schema": "ztare-strategy-experiment-probe-outcome-v1",
            "status": "blocked",
            "summary": f"no probe harness found for kind {kind}",
            "live_rows": [],
            "observed_status": "no_probe_harness",
        }
    spec = importlib.util.spec_from_file_location(f"probe_{kind}", probe_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load probe harness: {probe_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    runner = getattr(module, "run", None) or getattr(module, "execute", None) or getattr(module, "probe", None)
    if not callable(runner):
        raise RuntimeError(f"probe harness missing run/execute/probe: {probe_path}")
    return dict(runner(project_dir=project_dir, card=card, action_plan=plan))


def _execution_receipt(card: dict[str, Any], outcome: dict[str, Any], disposition: str) -> dict[str, Any]:
    blob = json.dumps({"card": card, "outcome": outcome}, sort_keys=True, default=str).encode("utf-8")
    # Record the kill-condition check itself so a "survived" is appealable:
    # same substring semantics as the disposition decision (recording only —
    # a semantic overhaul of the match is carded separately).
    kill_condition = str(card.get("kill_condition") or "")
    kill_condition_matched = bool(
        kill_condition and kill_condition in str(outcome.get("summary") or "")
    )
    return {
        "schema": "ztare-strategy-experiment-execution-v1",
        "executed_utc": datetime.now(timezone.utc).isoformat(),
        "failure_family_sha": card.get("failure_family_sha"),
        "kind": card.get("kind"),
        "disposition": disposition,
        "kill_condition": card.get("kill_condition"),
        "kill_condition_matched": kill_condition_matched,
        "outcome_summary": outcome.get("summary", ""),
        "outcome_status": outcome.get("status", ""),
        "outcome_sha256": hashlib.sha256(blob).hexdigest(),
        "attestation": {
            "card_sha": card.get("failure_family_sha"),
            "principal": "worldmodel_experiment_executor",
            "outcome": disposition,
        },
        "live_rows": list(outcome.get("live_rows") or []),
    }


def execute_experiments(
    project: "Path | str",
    *,
    card_sha: str | None = None,
    all_open: bool = False,
    probe_runner: Callable[[Path, dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    project_dir = Path(project)
    ledger = project_dir / "workspace" / EXPERIMENT_LEDGER
    if not ledger.exists():
        raise FileNotFoundError(
            f"experiment ledger not found: {ledger} — pass the project directory "
            f"(e.g. projects/<name>), not the bare project name"
        )
    cards = [card for card in open_cards(ledger) if isinstance(card, dict)]
    if card_sha:
        cards = [card for card in cards if str(card.get("failure_family_sha") or "") == str(card_sha)]
    elif not all_open:
        cards = cards[:1]
    runner = probe_runner or _default_probe_runner

    written: list[dict[str, Any]] = []
    probe_rows: list[dict[str, Any]] = []
    for card in cards:
        if not _lowerable_card(card):
            outcome = {
                "schema": "ztare-strategy-experiment-probe-outcome-v1",
                "status": "blocked",
                "summary": "card is not lowerable",
                "live_rows": [],
                "observed_status": "unlowerable",
            }
            disposition = "rejected_unlowerable"
        else:
            outcome = runner(project_dir, card)
            disposition = "survived"
            if str(outcome.get("observed_status") or "") == "observed":
                # Evidence probes are zero-credit observations: an observation
                # neither survives nor is killed.
                disposition = "observed"
            elif str(outcome.get("observed_status") or "") == "counterexample":
                # A probe that ran and produced a killing witness is killed,
                # even though its outcome status reads blocked.
                disposition = "killed"
            elif str(outcome.get("status") or "") == "blocked":
                # A probe that never ran proves nothing; never attest survived.
                disposition = "blocked"
            else:
                summary = str(outcome.get("summary") or "")
                kill_condition = str(card.get("kill_condition") or "")
                disposition = "killed" if kill_condition and kill_condition in summary else "survived"
        receipt = _execution_receipt(card, outcome, disposition)
        probe_rows.extend(list(outcome.get("live_rows") or []))
        written.append(receipt)
        _append_jsonl(project_dir / "workspace" / EXPERIMENT_EXECUTIONS, receipt)
        if disposition == "killed":
            # FEED the CDCL ledger: a killed card is a confirmed refutation. The
            # receipt (just persisted) IS the backing row; learn() surfaces it as
            # a ConflictClause carrying the counterexample witness so the office
            # mechanically prunes this failure_family from re-proposal.
            RefutedExperimentsLedger(project_dir).learn(receipt)
        for row in outcome.get("live_rows") or []:
            if isinstance(row, dict):
                _append_jsonl(project_dir / "workspace" / EXPERIMENT_PROBE_ROWS, row)
        record_disposition(ledger, {**card, "disposition": disposition}, attestation=receipt["attestation"])

    return {
        "schema": "ztare-strategy-experiment-executor-v1",
        "project": str(project_dir),
        "processed": len(written),
        "receipts": written,
        "probe_rows": probe_rows,
    }


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Execute open strategy-experiment cards.")
    ap.add_argument("--project", required=True)
    ap.add_argument("--card-sha", default=None)
    ap.add_argument("--all-open", action="store_true")
    args = ap.parse_args(argv)

    result = execute_experiments(
        args.project,
        card_sha=args.card_sha,
        all_open=args.all_open,
    )
    print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
