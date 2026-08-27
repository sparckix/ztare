"""Prospective evaluation of exact household paper-implementation rivals."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.evaluation import EvaluationScore, conservative_paired_survivor_set

from .contracts import canonical_timestamp, require_finite, timestamp_key
from .golden_store import GoldenEdge, GoldenLeaf, GoldenStore
from .household_allocation_scenario import HOUSEHOLD_ALLOCATION_SCENARIO_SCHEMA
from .portfolio_policy import _price_series
from .prospective_return_window import (
    RETURN_WINDOW_BINDING_SCHEMA,
    bind_prospective_return_window,
    compile_prospective_return_window,
    settle_prospective_return_window,
)


HOUSEHOLD_POLICY_RUN_SCHEMA = "jaggedthoughts-household-policy-tournament-run-v1"
HOUSEHOLD_POLICY_SETTLEMENT_SCHEMA = (
    "jaggedthoughts-household-policy-tournament-settlement-v1"
)
HOUSEHOLD_POLICY_STATUS_SCHEMA = "jaggedthoughts-household-policy-tournament-status-v1"
PRIMARY_HORIZON_DAYS = 365
MINIMUM_INFERENCE_BLOCKS = 8
_IMPLEMENTATION_SCHEMA = "jaggedthoughts-household-paper-implementation-rivals-v1"
_PRICE_IDENTITY = "adjusted_close_total_return_proxy"
_POLICY_VERSION = "same-sleeve-signal-v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return value if isinstance(value, dict) else None


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _signed(payload: Mapping[str, Any], field: str, schema: str) -> dict[str, Any]:
    body = dict(payload)
    digest = str(body.pop(field, ""))
    if body.get("schema") != schema or not digest or stable_sha256(body) != digest:
        raise ValueError(f"invalid {schema} identity")
    return {**body, field: digest}


def _policies(
    implementation: Mapping[str, Any], *, require_distinct_decisions: bool = True,
) -> list[dict[str, Any]]:
    if (
        implementation.get("capital_authority") is not False
        or implementation.get("order_routing_allowed") is not False
    ):
        raise ValueError("household tournament accepts paper-only implementations")
    policies = []
    starting_wealth: float | None = None
    for raw in implementation.get("proposals") or ():
        body = dict(raw)
        digest = str(body.pop("proposal_sha256", ""))
        if not digest or stable_sha256(body) != digest:
            raise ValueError("invalid household paper proposal identity")
        proposal = {**body, "proposal_sha256": digest}
        if proposal.get("order_routing_allowed") is not False:
            raise ValueError("household tournament accepts paper-only proposals")
        if proposal.get("expected_return_claim") is not False:
            raise ValueError("household tournament accepts hypothesis-labeled proposals only")
        if proposal.get("policy_rule_version") != _POLICY_VERSION:
            raise ValueError("household proposal policy-rule version is unsupported")
        selection_signal = proposal.get("selection_signal")
        if selection_signal is not None:
            selection_signal = dict(selection_signal)
            if (
                selection_signal.get("expected_realized_return_claim") is not False
                or not str(selection_signal.get("signal_class") or "")
                or not str(selection_signal.get("candidate_metric") or "")
                or selection_signal.get("comparison") != "same_sleeve_broad_proxy"
                or selection_signal.get("current_action") not in {
                    "replace_broad_proxy_with_selected_security", "abstain_to_broad_proxy",
                }
            ):
                raise ValueError("household selection signal requires a same-sleeve hypothesis")
            selected_values = {
                str(position.get("entity_id") or "").upper(): require_finite(
                    position.get("selection_signal_value"),
                    f"{position.get('entity_id')}.selection_signal_value",
                )
                for position in proposal.get("positions") or ()
                if position.get("entity_kind") != "broad_sleeve_proxy"
            }
            if not selected_values and selection_signal["current_action"] != "abstain_to_broad_proxy":
                raise ValueError("household selection signal requires a selected security")
            if selected_values and selection_signal["current_action"] != "replace_broad_proxy_with_selected_security":
                raise ValueError("household abstention signal cannot carry selected securities")
            selection_signal["selected_values"] = dict(sorted(selected_values.items()))
        weights: dict[str, float] = {}
        for position in proposal.get("positions") or ():
            entity_id = str(position.get("entity_id") or "").upper()
            weight = require_finite(position.get("target_weight"), f"{entity_id}.target_weight")
            if not entity_id or weight <= 0 or entity_id in weights:
                raise ValueError("household proposal positions require unique positive identities")
            weights[entity_id] = weight
        total = sum(weights.values())
        declared_total = require_finite(proposal.get("total_weight"), "proposal total_weight")
        decision_equivalence_id = str(proposal.get("decision_equivalence_id") or "")
        wealth = require_finite(
            proposal.get("starting_investable_wealth_base"), "starting investable wealth",
        )
        starting_wealth = wealth if starting_wealth is None else starting_wealth
        if (
            wealth <= 0 or not math.isclose(wealth, starting_wealth, rel_tol=0.0, abs_tol=1e-9)
            or proposal.get("selection_status") != "unselected_paper_rival"
            or decision_equivalence_id != stable_sha256(dict(sorted(weights.items())))
            or not math.isclose(total, declared_total, rel_tol=0.0, abs_tol=1e-9)
            or not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9)
        ):
            raise ValueError("household paper proposal weights must sum to one")
        body = {
            "policy_id": str(proposal.get("proposal_id") or ""),
            "version": str(proposal["policy_rule_version"]),
            "method": str(proposal.get("method") or ""),
            "weights": dict(sorted(weights.items())),
            "decision_equivalence_id": decision_equivalence_id,
            "proposal_sha256": proposal["proposal_sha256"],
            "selection_signal": selection_signal,
            "expected_return_claim": False,
            "authority": "prospective_shadow",
            "capital_authority": False,
        }
        if not body["policy_id"] or not body["method"] or not body["decision_equivalence_id"]:
            raise ValueError("household proposal requires policy, method, and decision equivalence")
        policies.append({**body, "policy_sha256": stable_sha256(body)})
    ids = [row["policy_id"] for row in policies]
    decisions = {row["decision_equivalence_id"] for row in policies}
    if (
        not policies or len(ids) != len(set(ids)) or "broad_sleeve_control" not in ids
        or (require_distinct_decisions and (len(policies) < 2 or len(decisions) < 2))
    ):
        raise ValueError("household tournament requires one control and at least one distinct decision")
    return policies


def validate_household_policy_implementation(
    implementation: Mapping[str, Any], *, require_distinct_decisions: bool = True,
) -> list[dict[str, Any]]:
    """Return the verified paper policies encoded by one implementation menu."""

    return _policies(
        implementation, require_distinct_decisions=require_distinct_decisions,
    )


def _trial_family(policies: list[Mapping[str, Any]], horizon_days: int, cost_bps: float) -> dict[str, Any]:
    body = {
        "schema": "jaggedthoughts-household-policy-trial-family-v1",
        "allocation_identity": "complete_household_implementation_rivals",
        "control_policy_id": "broad_sleeve_control",
        "policy_versions": {
            str(row["policy_id"]): str(row["version"]) for row in policies
        },
        "horizon_days": int(horizon_days),
        "price_identity": _PRICE_IDENTITY,
        "transaction_cost_bps": float(cost_bps),
        "score": "incremental_total_return_after_cost_vs_broad_sleeve_control",
    }
    return {**body, "trial_family_id": stable_sha256(body)}


def open_household_policy_tournament(
    root: Path,
    *,
    owner: str,
    store_path: Path,
    scenario: Mapping[str, Any],
    horizon_days: int = PRIMARY_HORIZON_DAYS,
    transaction_cost_bps: float = 10.0,
    opened_at: str | None = None,
    sealed_at: str | None = None,
) -> dict[str, Any]:
    """Freeze the displayed complete-policy rivals before observing later returns."""

    scenario = _signed(scenario, "scenario_sha256", HOUSEHOLD_ALLOCATION_SCENARIO_SCHEMA)
    if scenario.get("capital_authority") is not False or scenario.get("policy_authority") is not False:
        raise ValueError("household tournament accepts assumption-labeled paper scenarios only")
    implementation = _signed(
        scenario.get("paper_implementation") or {}, "implementation_sha256",
        _IMPLEMENTATION_SCHEMA,
    )
    policies = _policies(implementation)
    if not 7 <= int(horizon_days) <= 730:
        raise ValueError("household policy horizon_days must be in [7, 730]")
    opened = canonical_timestamp(opened_at or _utc_now(), "household policy opened_at")
    sealed = canonical_timestamp(sealed_at or opened, "household policy sealed_at")
    if timestamp_key(sealed) < timestamp_key(opened):
        raise ValueError("household policy seal cannot precede opening")
    entity_ids = sorted({entity_id for row in policies for entity_id in row["weights"]})
    window = compile_prospective_return_window(
        sealed_at=sealed, horizon_days=int(horizon_days), entity_ids=entity_ids,
        transaction_cost_bps=float(transaction_cost_bps), price_identity=_PRICE_IDENTITY,
    )
    family = _trial_family(policies, int(horizon_days), float(transaction_cost_bps))
    base = root / "portfolio_policy" / "household"
    scenario_path = base / "scenarios" / f"{scenario['scenario_sha256']}.json"
    run_identity = {
        "scenario_sha256": scenario["scenario_sha256"],
        "implementation_sha256": implementation["implementation_sha256"],
        "horizon_days": int(horizon_days),
        "policy_sha256s": [row["policy_sha256"] for row in policies],
        "return_window_sha256": window["return_window_sha256"],
    }
    run_id = f"household-policy-{stable_sha256(run_identity)[:20]}"
    end_at = (
        datetime.fromisoformat(sealed.replace("Z", "+00:00"))
        + timedelta(days=int(horizon_days))
    ).isoformat(timespec="seconds").replace("+00:00", "Z")
    superseded: list[dict[str, Any]] = []
    for path in sorted((base / "runs").glob("*.json")):
        prior = _read(path)
        if (
            not prior or int(prior.get("horizon_days") or 0) != int(horizon_days)
            or (base / "settlements" / f"{prior.get('run_id')}.json").is_file()
            or (base / "supersessions" / f"{prior.get('run_id')}.json").is_file()
        ):
            continue
        if (
            prior.get("run_id") == run_id
            or (
                prior.get("scenario_sha256") == scenario["scenario_sha256"]
                and prior.get("implementation_sha256") == implementation["implementation_sha256"]
                and float((prior.get("score_contract") or {}).get("transaction_cost_bps") or 0.0)
                == float(transaction_cost_bps)
            )
        ):
            return {**prior, "ok": True, "replayed": True, "activation_status": "already_open"}
        envelope = _read(base / "return_windows" / f"{prior.get('run_id')}.json") or {}
        if (envelope.get("binding") or {}).get("status") == "bound":
            return {**prior, "ok": True, "replayed": True, "activation_status": "blocked_overlap"}
        superseded.append(prior)
    body = {
        "schema": HOUSEHOLD_POLICY_RUN_SCHEMA,
        "run_id": run_id,
        "status": "pending_outcome",
        "opened_at": opened,
        "sealed_at": sealed,
        "end_at": end_at,
        "horizon_days": int(horizon_days),
        "estimand_role": (
            "primary_household_policy_evidence"
            if int(horizon_days) == PRIMARY_HORIZON_DAYS else "diagnostic_only"
        ),
        "inference_block_id": stable_sha256({"sealed_date": sealed[:10], "horizon_days": horizon_days}),
        "scenario_sha256": scenario["scenario_sha256"],
        "scenario_path": scenario_path.relative_to(root).as_posix(),
        "implementation_sha256": implementation["implementation_sha256"],
        "allocation_identity": "complete_household_implementation_rivals",
        "control_policy_id": "broad_sleeve_control",
        "starting_investable_wealth_base": float(
            implementation["proposals"][0]["starting_investable_wealth_base"]
        ),
        "base_currency": str(scenario["base_currency"]),
        "policies": policies,
        "observed_entity_ids": entity_ids,
        "prospective_return_window": window,
        "trial_family": family,
        "score_contract": {
            "primary_outcome": "incremental_total_return_after_cost_vs_broad_sleeve_control",
            "transaction_cost_bps": float(transaction_cost_bps),
            "cost_application": "round_trip_once_per_frozen_position",
            "minimum_inference_blocks": MINIMUM_INFERENCE_BLOCKS,
            "rank_used_as_return_or_weight": False,
        },
        "automatic_policy_change": False,
        "policy_authority": False,
        "brokerage_authority": False,
        "order_routing_allowed": False,
        "capital_authority": False,
    }
    run = {**body, "run_sha256": stable_sha256(body)}
    path = base / "runs" / f"{run_id}.json"
    _write(scenario_path, scenario)
    _write(path, run)
    scenario_time = canonical_timestamp(
        scenario.get("as_of") or opened, "household scenario as_of",
    )
    scenario_leaf = GoldenLeaf(
        owner=owner, object_kind="household_allocation_scenario",
        object_id=scenario["scenario_sha256"], epoch=scenario["scenario_sha256"],
        occurred_at=scenario_time, available_at=scenario_time, payload=scenario,
        source_refs=(
            f"household-goal-surface:{scenario.get('goal_surface_sha256')}",
            f"capital-market-basis:{scenario.get('basis_sha256')}",
        ),
    )
    leaf = GoldenLeaf(
        owner=owner, object_kind="household_policy_tournament_run", object_id=run_id,
        epoch=run["run_sha256"], occurred_at=opened, available_at=sealed, payload=run,
        source_refs=(
            f"household-scenario:{scenario['scenario_sha256']}",
            f"household-implementation:{implementation['implementation_sha256']}",
        ),
    )
    GoldenStore(store_path).append_bundle(
        (scenario_leaf, leaf),
        (GoldenEdge(leaf.leaf_sha256, scenario_leaf.leaf_sha256, "derived_from"),),
        make_heads=True,
    )
    for prior in superseded:
        supersession_body = {
            "schema": "jaggedthoughts-household-policy-tournament-supersession-v1",
            "prior_run_id": prior["run_id"], "prior_run_sha256": prior["run_sha256"],
            "successor_run_id": run_id, "successor_run_sha256": run["run_sha256"],
            "recorded_at": sealed,
            "reason": "displayed_household_scenario_changed_before_entry_binding",
            "capital_authority": False,
        }
        supersession = {**supersession_body, "supersession_sha256": stable_sha256(supersession_body)}
        _write(base / "supersessions" / f"{prior['run_id']}.json", supersession)
    return {
        **run, "ok": True, "replayed": False,
        "activation_status": "prospective_comparison_open",
        "run_path": path.relative_to(root).as_posix(),
        "golden_leaf_sha256": leaf.leaf_sha256,
        "superseded_run_ids": [row["run_id"] for row in superseded],
    }


def settle_household_policy_tournaments(
    root: Path, *, owner: str, store_path: Path, as_of: str | None = None,
) -> dict[str, Any]:
    """Bind and settle due household implementation rivals from cached prices."""

    evaluated = canonical_timestamp(as_of or _utc_now(), "household policy settlement as_of")
    base = root / "portfolio_policy" / "household"
    runs = [row for path in sorted((base / "runs").glob("*.json")) if (row := _read(path))]
    scope = {
        str(entity_id).upper() for run in runs for entity_id in run.get("observed_entity_ids") or ()
    }
    prices = _price_series(root, evaluated, scope)
    settled, pending = [], []
    for run in runs:
        run = _signed(run, "run_sha256", HOUSEHOLD_POLICY_RUN_SCHEMA)
        run_id = str(run["run_id"])
        if (base / "supersessions" / f"{run_id}.json").is_file():
            continue
        settlement_path = base / "settlements" / f"{run_id}.json"
        if prior := _read(settlement_path):
            settled.append(_signed(prior, "settlement_sha256", HOUSEHOLD_POLICY_SETTLEMENT_SCHEMA))
            continue
        contract = run["prospective_return_window"]
        points = {entity_id: prices.get(entity_id, ()) for entity_id in contract["entity_ids"]}
        binding_path = base / "return_windows" / f"{run_id}.json"
        envelope = _read(binding_path) or {}
        binding = envelope.get("binding")
        if not isinstance(binding, Mapping):
            binding = bind_prospective_return_window(contract, points=points, as_of=evaluated)
            if binding["status"] == "bound":
                _write(binding_path, {"contract": contract, "binding": binding})
        elif (
            binding.get("schema") != RETURN_WINDOW_BINDING_SCHEMA
            or binding.get("return_window_sha256") != contract["return_window_sha256"]
        ):
            raise ValueError(f"household policy binding identity mismatch: {run_id}")
        if binding["status"] != "bound":
            pending.append({"run_id": run_id, "reason": "entry_price_unavailable"})
            continue
        window = settle_prospective_return_window(
            contract, binding, points=points, as_of=evaluated,
        )
        if window["status"] != "settled":
            pending.append({
                "run_id": run_id, "reason": window["status"],
                "scheduled_exit_at": binding["scheduled_exit_at"],
                "missing_entity_ids": list(window.get("missing_entity_ids") or ()),
            })
            continue
        control_id = str(run["control_policy_id"])
        after_cost = {key: float(value) for key, value in window["returns"].items()}
        before_cost = {key: float(value) for key, value in window["gross_returns"].items()}
        policy_scores = []
        for policy in run["policies"]:
            weights = {str(key): float(value) for key, value in policy["weights"].items()}
            gross = sum(weight * before_cost[key] for key, weight in weights.items())
            net = sum(weight * after_cost[key] for key, weight in weights.items())
            policy_scores.append({
                "policy_id": policy["policy_id"], "policy_sha256": policy["policy_sha256"],
                "method": policy["method"],
                "selection_signal": policy.get("selection_signal"),
                "expected_return_claim": False,
                "portfolio_return_before_cost": gross,
                "portfolio_return_after_cost": net,
                "transaction_cost_drag": gross - net,
            })
        by_id = {str(row["policy_id"]): row for row in policy_scores}
        control = by_id[control_id]
        control_weights = next(
            row["weights"] for row in run["policies"] if row["policy_id"] == control_id
        )
        for score in policy_scores:
            policy = next(row for row in run["policies"] if row["policy_id"] == score["policy_id"])
            rows = []
            for entity_id in sorted(set(control_weights) | set(policy["weights"])):
                delta = float(policy["weights"].get(entity_id, 0.0)) - float(
                    control_weights.get(entity_id, 0.0)
                )
                if abs(delta) > 1e-12:
                    rows.append({
                        "entity_id": entity_id, "delta_weight_vs_control": delta,
                        "return_after_cost": after_cost[entity_id],
                        "incremental_contribution_after_cost": delta * after_cost[entity_id],
                    })
            incremental = float(score["portfolio_return_after_cost"]) - float(
                control["portfolio_return_after_cost"]
            )
            residual = incremental - sum(row["incremental_contribution_after_cost"] for row in rows)
            if not math.isclose(residual, 0.0, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"household policy attribution failed to reconcile: {score['policy_id']}")
            score["incremental_total_return_after_cost_vs_broad_sleeve_control"] = incremental
            score["attribution"] = {"rows": rows, "accounting_residual": residual}
        body = {
            "schema": HOUSEHOLD_POLICY_SETTLEMENT_SCHEMA,
            "settlement_id": f"{run_id}::settlement", "run_id": run_id,
            "run_sha256": run["run_sha256"], "trial_family_id": run["trial_family"]["trial_family_id"],
            "inference_block_id": run["inference_block_id"], "horizon_days": run["horizon_days"],
            "estimand_role": run["estimand_role"], "evaluated_at": evaluated,
            "return_window_binding": dict(binding), "return_window_settlement": window,
            "policy_scores": policy_scores,
            "statistical_winner_is_capital_instruction": False,
            "automatic_policy_change": False, "capital_authority": False,
        }
        settlement = {**body, "settlement_sha256": stable_sha256(body)}
        _write(settlement_path, settlement)
        leaf = GoldenLeaf(
            owner=owner, object_kind="household_policy_tournament_settlement",
            object_id=body["settlement_id"], epoch=run["run_sha256"],
            occurred_at=evaluated, available_at=evaluated, payload=settlement,
            source_refs=tuple(sorted({
                str(point["source_ref"]) for point in window["exit_points"].values()
            })),
        )
        try:
            run_leaf = GoldenStore(store_path).head(owner, "household_policy_tournament_run", run_id)
            edges = (GoldenEdge(leaf.leaf_sha256, run_leaf["leaf_sha256"], "settles"),)
        except KeyError:
            edges = ()
        GoldenStore(store_path).append_bundle((leaf,), edges, make_heads=True)
        settled.append(settlement)
    return {
        "ok": True, "evaluated_at": evaluated, "settled": settled, "pending": pending,
        "status": household_policy_tournament_status(root), "capital_authority": False,
    }


def household_policy_price_refresh_entity_ids(
    root: Path, *, as_of: str | None = None,
) -> list[str]:
    """Return the exact identities needed to bind an entry or a due exit."""

    evaluated = canonical_timestamp(as_of or _utc_now(), "household price refresh as_of")
    base = root / "portfolio_policy" / "household"
    superseded = {
        str(row.get("prior_run_id") or "")
        for path in (base / "supersessions").glob("*.json") if (row := _read(path))
    }
    settled = {
        str(row.get("run_id") or "")
        for path in (base / "settlements").glob("*.json") if (row := _read(path))
    }
    entity_ids: set[str] = set()
    for path in sorted((base / "runs").glob("*.json")):
        raw = _read(path)
        if not raw or str(raw.get("run_id") or "") in superseded | settled:
            continue
        run = _signed(raw, "run_sha256", HOUSEHOLD_POLICY_RUN_SCHEMA)
        envelope = _read(base / "return_windows" / f"{run['run_id']}.json") or {}
        binding = envelope.get("binding")
        if (
            isinstance(binding, Mapping)
            and binding.get("status") == "bound"
            and timestamp_key(evaluated) < timestamp_key(str(binding["scheduled_exit_at"]))
        ):
            continue
        entity_ids.update(str(value).upper() for value in run["observed_entity_ids"])
    return sorted(entity_ids)


def household_policy_tournament_status(root: Path) -> dict[str, Any]:
    """Project the pending decisions and rule-family evidence earned so far."""

    base = root / "portfolio_policy" / "household"
    superseded = {
        str(row.get("prior_run_id") or "")
        for path in (base / "supersessions").glob("*.json") if (row := _read(path))
    }
    runs = [
        _signed(row, "run_sha256", HOUSEHOLD_POLICY_RUN_SCHEMA)
        for path in sorted((base / "runs").glob("*.json")) if (row := _read(path))
        and str(row.get("run_id") or "") not in superseded
    ]
    runs_by_id = {str(row["run_id"]): row for row in runs}
    settlements = [
        _signed(row, "settlement_sha256", HOUSEHOLD_POLICY_SETTLEMENT_SCHEMA)
        for path in sorted((base / "settlements").glob("*.json")) if (row := _read(path))
        and str(row.get("run_id") or "") in runs_by_id
    ]
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in settlements:
        by_family.setdefault(str(row["trial_family_id"]), []).append(row)
    reviews = []
    for family_id, episodes in sorted(by_family.items()):
        run = runs_by_id[str(episodes[0]["run_id"])]
        model_ids = sorted(row["policy_id"] for row in episodes[0]["policy_scores"])
        scores = [
            EvaluationScore(
                model_id=str(score["policy_id"]), episode_id=str(episode["run_id"]),
                inference_block_id=str(episode["inference_block_id"]),
                losses={"negative_portfolio_return_after_cost": -float(score["portfolio_return_after_cost"])},
            )
            for episode in episodes for score in episode["policy_scores"]
        ]
        survivor = conservative_paired_survivor_set(
            scores=scores, model_ids=model_ids,
            episode_ids=sorted(str(row["run_id"]) for row in episodes),
            dimensions=("negative_portfolio_return_after_cost",),
            min_inference_blocks=MINIMUM_INFERENCE_BLOCKS,
        )
        unique = survivor["survivor_model_ids"][0] if (
            survivor["inference_sufficient"] and len(survivor["survivor_model_ids"]) == 1
        ) else None
        reviews.append({
            "trial_family_id": family_id, "policy_ids": model_ids,
            "policy_rule_hypotheses": {
                str(policy["policy_id"]): {
                    "method": policy["method"],
                    "selection_signal_contract": {
                        key: value for key, value in (policy.get("selection_signal") or {}).items()
                        if key != "selected_values"
                    } or None,
                    "expected_return_claim": False,
                }
                for policy in run["policies"]
            },
            "episode_signal_values": [{
                "run_id": episode["run_id"],
                "policies": {
                    str(score["policy_id"]): score.get("selection_signal")
                    for score in episode["policy_scores"]
                },
            } for episode in episodes],
            "episode_count": len(episodes), "survivor_set": survivor,
            "statistical_survivor_for_operator_review": (
                unique if int(run["horizon_days"]) == PRIMARY_HORIZON_DAYS else None
            ),
            "automatic_policy_change": False, "capital_authority": False,
        })
    settled_ids = {str(row["run_id"]) for row in settlements}
    latest = max(runs, key=lambda row: str(row["opened_at"]), default=None)
    body = {
        "schema": HOUSEHOLD_POLICY_STATUS_SCHEMA,
        "run_count": len(runs), "settled_count": len(settlements),
        "pending_count": sum(str(row["run_id"]) not in settled_ids for row in runs),
        "superseded_count": len(superseded), "primary_horizon_days": PRIMARY_HORIZON_DAYS,
        "minimum_inference_blocks": MINIMUM_INFERENCE_BLOCKS,
        "latest_run": (
            None if latest is None else {
                **latest,
                "lifecycle_status": (
                    "settled" if str(latest["run_id"]) in settled_ids else "pending_outcome"
                ),
            }
        ),
        "next_activation": (
            "await_or_settle_frozen_household_policy_outcome" if latest and latest["run_id"] not in settled_ids
            else "freeze_displayed_household_policy_rivals"
        ),
        "automatic_policy_change": False, "capital_authority": False,
    }
    return {**body, "status_sha256": stable_sha256(body)}


__all__ = [
    "HOUSEHOLD_POLICY_RUN_SCHEMA", "HOUSEHOLD_POLICY_SETTLEMENT_SCHEMA",
    "HOUSEHOLD_POLICY_STATUS_SCHEMA", "open_household_policy_tournament",
    "settle_household_policy_tournaments", "household_policy_tournament_status",
    "household_policy_price_refresh_entity_ids",
    "validate_household_policy_implementation",
]
