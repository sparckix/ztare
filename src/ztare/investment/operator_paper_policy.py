"""Explicit operator selection of a household paper policy."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, timestamp_key
from .golden_store import GoldenEdge, GoldenLeaf, GoldenStore
from .household_allocation import (
    CAPITAL_MARKET_BASIS_SCHEMA,
    HOUSEHOLD_MANDATE_SCHEMA,
    compile_household_allocation_frontier,
    compile_household_mandate,
)
from .household_allocation_scenario import HOUSEHOLD_ALLOCATION_SCENARIO_SCHEMA
from .household_goal_surface import HOUSEHOLD_GOAL_SURFACE_SCHEMA
from .household_policy_tournament import (
    HOUSEHOLD_POLICY_RUN_SCHEMA,
    PRIMARY_HORIZON_DAYS,
    open_household_policy_tournament,
    validate_household_policy_implementation,
)


OPERATOR_PAPER_POLICY_SCHEMA = "jaggedthoughts-operator-paper-policy-v1"
OPERATOR_PAPER_POLICY_STATUS_SCHEMA = "jaggedthoughts-operator-paper-policy-status-v1"
_IMPLEMENTATION_SCHEMA = "jaggedthoughts-household-paper-implementation-rivals-v1"
_ATTESTATION = "paper_only_reviewed"
_COMPLETION_FIELDS = {
    "age", "tax_residence", "account_ids",
    "human_capital_exclusion_attestation", "liability_currency_attestation",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _signed(raw: Mapping[str, Any], schema: str, digest_field: str) -> dict[str, Any]:
    body = dict(raw)
    digest = str(body.pop(digest_field, ""))
    if body.get("schema") != schema or len(digest) != 64 or stable_sha256(body) != digest:
        raise ValueError(f"invalid {schema} identity")
    return {**body, digest_field: digest}


def _same_weights(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if set(left) != set(right):
        return False
    return all(math.isclose(float(left[key]), float(right[key]), rel_tol=0.0, abs_tol=1e-12)
               for key in left)


def _verified_policy(raw: Mapping[str, Any]) -> dict[str, Any]:
    policy = _signed(raw, OPERATOR_PAPER_POLICY_SCHEMA, "policy_sha256")
    decision_identity = stable_sha256({
        "mandate_sha256": policy.get("mandate_sha256"),
        "basis_sha256": policy.get("basis_sha256"),
        "scenario_sha256": policy.get("scenario_sha256"),
        "implementation_sha256": policy.get("implementation_sha256"),
        "selected_policy_sha256": policy.get("selected_policy_sha256"),
        "operator_id": policy.get("operator_id"),
        "attestation": policy.get("attestation"),
        "transaction_cost_bps": float(policy.get("transaction_cost_bps")),
    })
    if (
        policy.get("decision_identity_sha256") != decision_identity
        or policy.get("policy_id") != f"operator-paper-policy:{decision_identity[:20]}"
        or policy.get("paper_policy_authority") is not True
        or any(policy.get(field) is not False for field in (
            "automatic_policy_change", "capital_authority", "brokerage_authority",
            "order_routing_allowed",
        ))
    ):
        raise ValueError("invalid operator paper policy authority identity")
    return policy


def _current_policy(store: GoldenStore, owner: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    try:
        leaf = store.head(owner, "operator_paper_policy", "household")
    except KeyError:
        return None
    policy = _verified_policy(leaf.get("payload") or {})
    if (
        leaf.get("payload_sha256") != stable_sha256(policy)
        or leaf.get("epoch") != policy["policy_sha256"]
        or policy.get("owner") != owner
    ):
        raise ValueError("operator paper policy Golden leaf payload mismatch")
    run_id = policy.get("prospective_tournament_run_id")
    run_sha256 = policy.get("prospective_tournament_run_sha256")
    if run_id or run_sha256:
        run_leaf = store.identity(
            owner, "household_policy_tournament_run", str(run_id), str(run_sha256),
        )
        if run_leaf is None:
            raise ValueError("operator paper policy prospective tournament is absent")
        run = _signed(
            run_leaf.get("payload") or {}, HOUSEHOLD_POLICY_RUN_SCHEMA, "run_sha256",
        )
        if (
            run.get("scenario_sha256") != policy.get("scenario_sha256")
            or run.get("implementation_sha256") != policy.get("implementation_sha256")
            or int(run.get("horizon_days") or 0) != PRIMARY_HORIZON_DAYS
            or not math.isclose(
                float((run.get("score_contract") or {}).get("transaction_cost_bps") or -1),
                float(policy["transaction_cost_bps"]), rel_tol=0.0, abs_tol=1e-12,
            )
            or policy.get("selected_policy_sha256") not in {
                row.get("policy_sha256") for row in run.get("policies") or ()
            }
        ):
            raise ValueError("operator paper policy prospective tournament is incompatible")
    elif policy.get("prospective_comparison_status") != "no_distinct_implementation_decision":
        raise ValueError("operator paper policy prospective tournament identity is incomplete")
    return policy, leaf


def _projection(
    policy: Mapping[str, Any], leaf: Mapping[str, Any], *, replayed: bool,
) -> dict[str, Any]:
    return {
        **dict(policy), "ok": True, "replayed": replayed,
        "activation_status": "already_frozen" if replayed else "operator_paper_policy_frozen",
        "policy_path": (
            Path("portfolio_policy") / "operator" / "policies"
            / f"{policy['policy_sha256']}.json"
        ).as_posix(),
        "golden_leaf_sha256": leaf["leaf_sha256"],
    }


def compose_operator_household_mandate(
    *, goal_surface: Mapping[str, Any], scenario: Mapping[str, Any],
    completion: Mapping[str, Any],
) -> dict[str, Any]:
    """Lower known private facts plus explicit operator choices into one mandate."""

    surface = _signed(goal_surface, HOUSEHOLD_GOAL_SURFACE_SCHEMA, "surface_sha256")
    reviewed_scenario = _signed(
        scenario, HOUSEHOLD_ALLOCATION_SCENARIO_SCHEMA, "scenario_sha256",
    )
    if set(completion) != _COMPLETION_FIELDS:
        raise ValueError("operator mandate completion requires its exact typed fields")
    age = int(completion.get("age") or 0)
    if not 18 <= age <= 100:
        raise ValueError("operator age must be in [18, 100]")
    tax_residence = str(completion.get("tax_residence") or "").strip()
    account_ids = sorted({str(value).strip() for value in completion.get("account_ids") or ()
                          if str(value).strip()})
    if not tax_residence or not account_ids:
        raise ValueError("tax_residence and at least one account identity are required")
    if completion.get("human_capital_exclusion_attestation") != "exclude_from_paper_policy_reviewed":
        raise ValueError("human-capital treatment requires explicit paper-policy review")
    if completion.get("liability_currency_attestation") != "unhedged_liability_currency_risk_reviewed":
        raise ValueError("liability-currency treatment requires explicit paper-policy review")
    inputs = dict(reviewed_scenario.get("inputs") or {})
    balance = dict(surface.get("known_balance_sheet") or {})
    source_ref = f"household-intake:{surface['intake_sha256']}"
    property_ids = [
        str(row["asset_id"]) for row in balance.get("assets") or ()
        if row.get("kind") == "property"
    ]
    mandate_identity = stable_sha256({
        "surface_sha256": surface["surface_sha256"],
        "scenario_sha256": reviewed_scenario["scenario_sha256"],
        "completion": dict(completion),
    })
    raw = {
        "schema": HOUSEHOLD_MANDATE_SCHEMA,
        "mandate_id": f"operator-household:{mandate_identity[:20]}",
        "mandate_purpose": "operator_policy",
        "as_of": surface["as_of"],
        "base_currency": surface["base_currency"],
        "fx_to_base": dict(surface.get("fx_to_base") or {}),
        "person": {"age": age},
        "tax_residence": tax_residence,
        "accounts": [{"account_id": value} for value in account_ids],
        "assets": [{
            "asset_id": str(row["asset_id"]), "kind": str(row["kind"]),
            "value": float(row["value"]), "currency": str(row["currency"]),
            "liquid": row.get("kind") == "liquidity",
            "investable": row.get("kind") == "liquidity",
            "source_ref": source_ref,
        } for row in balance.get("assets") or ()],
        "liabilities": [{
            "liability_id": str(row["liability_id"]), "kind": str(row["kind"]),
            "balance": float(row["balance"]), "currency": str(row["currency"]),
            "annual_rate": float(row["annual_rate"]), "rate_kind": "operator_unresolved",
            "secured_by_asset_id": (
                property_ids[0] if row.get("kind") == "mortgage" and property_ids else None
            ),
            "source_ref": source_ref,
        } for row in balance.get("liabilities") or ()],
        "tax_policy": {"annual_return_haircuts": dict(inputs["annual_return_haircuts"])},
        "currency_policy": {
            "minimum_asset_weights": {},
            "liability_currency_treatment": completion["liability_currency_attestation"],
        },
        "goal": {
            "target_wealth": float(inputs["target_wealth"]),
            "currency": surface["base_currency"],
            "horizon_years": int(inputs["horizon_years"]),
            "annual_contribution": float(inputs["annual_contribution"]),
            "wealth_basis": "investable_wealth",
            "minimum_success_probability": float(inputs["minimum_success_probability"]),
        },
        "constraints": {
            "liquidity_reserve": float(inputs["liquidity_reserve"]),
            "max_risky_weight": float(inputs["max_risky_weight"]),
            "max_one_year_loss": float(inputs["max_one_year_loss"]),
            "max_effective_equity_exposure": float(inputs["max_effective_equity_exposure"]),
            "weight_step": float(inputs["weight_step"]),
        },
        "human_capital": {
            "included": False,
            "exclusion_attestation": completion["human_capital_exclusion_attestation"],
        },
        "source_refs": sorted({source_ref, *map(str, surface.get("fx_source_refs") or ())}),
    }
    compiled = compile_household_mandate(raw)
    if not compiled["readiness"]["complete"]:
        raise ValueError("operator mandate remains incomplete: " + ", ".join(compiled["readiness"]["missing"]))
    return raw


def freeze_operator_paper_policy(
    root: Path,
    *,
    owner: str,
    store_path: Path,
    mandate: Mapping[str, Any],
    capital_market_basis: Mapping[str, Any],
    scenario: Mapping[str, Any],
    selected_proposal_id: str,
    operator_id: str,
    attestation: str,
    reviewed_at: str | None = None,
    transaction_cost_bps: float = 10.0,
) -> dict[str, Any]:
    """Freeze one explicit paper-only choice and open its prospective comparator."""

    compiled_mandate = compile_household_mandate(mandate)
    basis = _signed(capital_market_basis, CAPITAL_MARKET_BASIS_SCHEMA, "basis_sha256")
    signed_scenario = _signed(
        scenario, HOUSEHOLD_ALLOCATION_SCENARIO_SCHEMA, "scenario_sha256",
    )
    if compiled_mandate.get("mandate_purpose") != "operator_policy":
        raise ValueError("operator paper policy requires an operator_policy mandate")
    if not compiled_mandate["readiness"]["complete"]:
        raise ValueError(
            "operator paper policy mandate is incomplete: "
            + ", ".join(compiled_mandate["readiness"]["missing"])
        )
    if (
        compiled_mandate.get("capital_authority") is not False
        or compiled_mandate.get("brokerage_authority") is not False
        or signed_scenario.get("capital_authority") is not False
    ):
        raise ValueError("operator paper policy cannot carry capital or brokerage authority")
    if attestation != _ATTESTATION:
        raise ValueError(f"attestation must be {_ATTESTATION}")
    if not str(operator_id).strip():
        raise ValueError("operator_id is required")
    if not str(selected_proposal_id).strip():
        raise ValueError("selected_proposal_id is required and is never inferred")
    if not (
        basis["as_of"] == signed_scenario["as_of"]
        and signed_scenario["basis_sha256"] == basis["basis_sha256"]
        and timestamp_key(compiled_mandate["as_of"]) <= timestamp_key(basis["as_of"])
    ):
        raise ValueError("mandate must be available by the scenario's public-basis epoch")

    allocation = compile_household_allocation_frontier(
        mandate=compiled_mandate,
        capital_market_basis=basis,
        simulation_paths=int((signed_scenario.get("simulation") or {}).get("paths") or 0),
        simulation_seed_identity=signed_scenario["mandate_sha256"],
    )
    if allocation.get("status") != "paper_policy_ready":
        raise ValueError("operator mandate did not compile to a paper policy")
    if not _same_weights(
        allocation["selected_policy"]["weights"],
        (signed_scenario.get("selected_policy") or {}).get("weights") or {},
    ):
        raise ValueError("operator mandate selects different sleeve weights than the reviewed scenario")

    implementation = _signed(
        signed_scenario.get("paper_implementation") or {},
        _IMPLEMENTATION_SCHEMA,
        "implementation_sha256",
    )
    policies = validate_household_policy_implementation(
        implementation, require_distinct_decisions=False,
    )
    scenario_wealth = float(implementation["proposals"][0]["starting_investable_wealth_base"])
    mandate_wealth = float(compiled_mandate["balance_sheet"]["portfolio_starting_wealth_base"])
    if not math.isclose(scenario_wealth, mandate_wealth, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError("operator mandate and reviewed implementation use different investable wealth")
    selected = next(
        (row for row in policies if row["policy_id"] == selected_proposal_id), None,
    )
    if selected is None:
        raise ValueError("selected_proposal_id is not in the reviewed implementation menu")

    decision_identity = stable_sha256({
        "mandate_sha256": compiled_mandate["mandate_sha256"],
        "basis_sha256": basis["basis_sha256"],
        "scenario_sha256": signed_scenario["scenario_sha256"],
        "implementation_sha256": implementation["implementation_sha256"],
        "selected_policy_sha256": selected["policy_sha256"],
        "operator_id": str(operator_id).strip(),
        "attestation": attestation,
        "transaction_cost_bps": float(transaction_cost_bps),
    })
    base = root / "portfolio_policy" / "operator"
    latest_path = base / "latest.json"
    store = GoldenStore(store_path)
    current = _current_policy(store, owner)
    if current and current[0].get("decision_identity_sha256") == decision_identity:
        result = _projection(current[0], current[1], replayed=True)
        _write(base / "policies" / f"{current[0]['policy_sha256']}.json", result)
        _write(latest_path, result)
        return result

    reviewed = canonical_timestamp(reviewed_at or _utc_now(), "operator policy reviewed_at")
    if timestamp_key(reviewed) < timestamp_key(basis["as_of"]):
        raise ValueError("operator policy review cannot precede its composite evidence epoch")
    if current and timestamp_key(reviewed) <= timestamp_key(current[0]["reviewed_at"]):
        raise ValueError("a changed operator paper policy requires a later review timestamp")
    distinct_decisions = {str(row["decision_equivalence_id"]) for row in policies}
    tournament = None
    run_leaf = None
    if len(distinct_decisions) >= 2:
        opened_tournament = open_household_policy_tournament(
            root,
            owner=owner,
            store_path=store_path,
            scenario=signed_scenario,
            horizon_days=PRIMARY_HORIZON_DAYS,
            transaction_cost_bps=float(transaction_cost_bps),
            opened_at=reviewed,
            sealed_at=reviewed,
        )
        if opened_tournament.get("activation_status") == "blocked_overlap":
            raise ValueError("the exact reviewed policy has no compatible prospective tournament")
        run_leaf = store.identity(
            owner, "household_policy_tournament_run",
            str(opened_tournament.get("run_id") or ""),
            str(opened_tournament.get("run_sha256") or ""),
        )
        if run_leaf is None:
            raise ValueError("prospective tournament lineage was not recorded")
        tournament = _signed(
            run_leaf.get("payload") or {}, HOUSEHOLD_POLICY_RUN_SCHEMA, "run_sha256",
        )
        if (
            tournament.get("scenario_sha256") != signed_scenario["scenario_sha256"]
            or tournament.get("implementation_sha256") != implementation["implementation_sha256"]
            or int(tournament.get("horizon_days") or 0) != PRIMARY_HORIZON_DAYS
            or not math.isclose(
                float((tournament.get("score_contract") or {}).get("transaction_cost_bps") or -1),
                float(transaction_cost_bps), rel_tol=0.0, abs_tol=1e-12,
            )
            or selected["policy_sha256"] not in {
                row.get("policy_sha256") for row in tournament.get("policies") or ()
            }
        ):
            raise ValueError("the exact reviewed policy has no compatible prospective tournament")
    body = {
        "schema": OPERATOR_PAPER_POLICY_SCHEMA,
        "policy_id": f"operator-paper-policy:{decision_identity[:20]}",
        "status": "reviewed_paper_policy",
        "reviewed_at": reviewed,
        "operator_id": str(operator_id).strip(),
        "owner": owner,
        "decision_identity_sha256": decision_identity,
        "decision_epoch": {
            "mandate_as_of": compiled_mandate["as_of"],
            "public_basis_as_of": basis["as_of"],
            "reviewed_at": reviewed,
        },
        "mandate_sha256": compiled_mandate["mandate_sha256"],
        "basis_sha256": basis["basis_sha256"],
        "scenario_sha256": signed_scenario["scenario_sha256"],
        "allocation_sha256": allocation["allocation_sha256"],
        "implementation_sha256": implementation["implementation_sha256"],
        "selected_proposal_id": selected["policy_id"],
        "selected_proposal_sha256": selected["proposal_sha256"],
        "selected_policy_sha256": selected["policy_sha256"],
        "selected_sleeve_weights": dict(allocation["selected_policy"]["weights"]),
        "selected_positions": dict(selected["weights"]),
        "prospective_comparison_status": (
            "distinct_implementation_trial_open" if tournament
            else "no_distinct_implementation_decision"
        ),
        "prospective_tournament_run_id": tournament["run_id"] if tournament else None,
        "prospective_tournament_run_sha256": tournament["run_sha256"] if tournament else None,
        "attestation": attestation,
        "transaction_cost_bps": float(transaction_cost_bps),
        "paper_policy_authority": True,
        "automatic_policy_change": False,
        "capital_authority": False,
        "brokerage_authority": False,
        "order_routing_allowed": False,
    }
    policy = {**body, "policy_sha256": stable_sha256(body)}
    policy_path = base / "policies" / f"{policy['policy_sha256']}.json"

    existing_mandate = store.identity(
        owner, "household_capital_mandate", compiled_mandate["mandate_id"],
        compiled_mandate["mandate_sha256"],
    )
    mandate_leaf = None if existing_mandate else GoldenLeaf(
        owner=owner, object_kind="household_capital_mandate",
        object_id=compiled_mandate["mandate_id"], epoch=compiled_mandate["mandate_sha256"],
        occurred_at=compiled_mandate["as_of"], available_at=reviewed,
        payload=compiled_mandate, source_refs=tuple(compiled_mandate["source_refs"]),
    )
    mandate_leaf_sha256 = (
        str(existing_mandate["leaf_sha256"]) if existing_mandate else mandate_leaf.leaf_sha256
    )
    policy_leaf = GoldenLeaf(
        owner=owner,
        object_kind="operator_paper_policy",
        object_id="household",
        epoch=policy["policy_sha256"],
        occurred_at=reviewed,
        available_at=reviewed,
        payload=policy,
        source_refs=tuple(filter(None, (
            f"household-mandate:{compiled_mandate['mandate_sha256']}",
            f"household-scenario:{signed_scenario['scenario_sha256']}",
            f"household-policy-run:{tournament['run_sha256']}" if tournament else None,
        ))),
    )
    scenario_leaf = store.identity(
        owner, "household_allocation_scenario",
        signed_scenario["scenario_sha256"], signed_scenario["scenario_sha256"],
    )
    if scenario_leaf is None or (tournament and run_leaf is None):
        raise ValueError("prospective tournament lineage was not recorded")
    edges = [
        GoldenEdge(policy_leaf.leaf_sha256, mandate_leaf_sha256, "derived_from"),
        GoldenEdge(policy_leaf.leaf_sha256, scenario_leaf["leaf_sha256"], "derived_from"),
    ]
    if run_leaf:
        edges.append(GoldenEdge(
            policy_leaf.leaf_sha256, run_leaf["leaf_sha256"], "selects",
            {"selected_proposal_id": selected["policy_id"],
             "selected_policy_sha256": selected["policy_sha256"]},
        ))
    if current:
        edges.append(GoldenEdge(
            policy_leaf.leaf_sha256, str(current[1]["leaf_sha256"]), "supersedes",
        ))
    store.append_bundle(
        tuple(row for row in (mandate_leaf, policy_leaf) if row is not None),
        edges, make_heads=True,
    )
    canonical = _current_policy(store, owner)
    if canonical is None or canonical[0]["policy_sha256"] != policy["policy_sha256"]:
        raise ValueError("operator paper policy was superseded by a concurrent later review")
    result = _projection(canonical[0], canonical[1], replayed=False)
    _write(policy_path, result)
    _write(latest_path, result)
    return result


def operator_paper_policy_status(
    root: Path, *, owner: str = "operator-paper-book", store_path: Path | None = None,
) -> dict[str, Any]:
    store = GoldenStore(store_path or root / "state" / "golden_store.sqlite3")
    current = _current_policy(store, owner)
    latest = _projection(current[0], current[1], replayed=True) if current else None
    body = {
        "schema": OPERATOR_PAPER_POLICY_STATUS_SCHEMA,
        "status": "frozen" if latest else "awaiting_complete_mandate_and_selection",
        "latest_policy": latest,
        "next_action": (
            "collect_prospective_policy_outcome" if latest
            else "complete_operator_mandate_and_select_one_reviewed_paper_proposal"
        ),
        "paper_policy_authority": bool(latest),
        "automatic_policy_change": False,
        "capital_authority": False,
        "brokerage_authority": False,
        "order_routing_allowed": False,
    }
    return {**body, "status_sha256": stable_sha256(body)}


__all__ = [
    "OPERATOR_PAPER_POLICY_SCHEMA",
    "OPERATOR_PAPER_POLICY_STATUS_SCHEMA",
    "freeze_operator_paper_policy",
    "compose_operator_household_mandate",
    "operator_paper_policy_status",
]
