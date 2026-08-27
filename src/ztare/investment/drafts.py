"""Source-bound public-equity draft creation and explicit activation.

Draft generation converts a consumed public-data epoch into a complete,
compilable underwriting profile.  It never promotes the profile to the active
paper book: that is a separate operator transition after the thesis,
assumptions, rival mechanism, and falsifiers have been reviewed.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Mapping

import yaml

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite, require_text, timestamp_key
from .funnel import FunnelObjectRef, FunnelTransitionReceipt


PROFILE_SCHEMA = "jaggedthoughts-investment-profile-v1"
DRAFT_SCHEMA = "jaggedthoughts-public-equity-draft-v1"


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", require_text(value, "entity id").lower()).strip("-")
    if not slug:
        raise ValueError("entity id must contain a letter or number")
    return slug


def _read_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def _latest_rows(path: Path, *, as_of: str) -> dict[tuple[str, str], dict[str, str]]:
    cutoff = timestamp_key(canonical_timestamp(as_of, "draft as_of"))
    latest: dict[tuple[str, str], dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            available = timestamp_key(str(row.get("available_at") or ""))
            if available > cutoff:
                continue
            key = (str(row.get("entity_id") or ""), str(row.get("metric_id") or ""))
            rank = (available, timestamp_key(str(row.get("observed_at") or "")), str(row.get("observation_id") or ""))
            current = latest.get(key)
            if current is None:
                latest[key] = dict(row)
                continue
            current_rank = (
                timestamp_key(current["available_at"]), timestamp_key(current["observed_at"]),
                current["observation_id"],
            )
            if rank > current_rank:
                latest[key] = dict(row)
    return latest


def _need(rows: Mapping[tuple[str, str], Mapping[str, str]], entity: str, metric: str) -> Mapping[str, str]:
    try:
        return rows[(entity, metric)]
    except KeyError as error:
        raise ValueError(f"source-bound draft requires {entity}.{metric}; refresh/configure sources first") from error


def _memo(
    *, entity_id: str, entity_name: str, benchmark_id: str, thesis_claim: str,
    as_of: str, beta: float, base_growth: float, terminal_growth: float,
) -> str:
    return "\n".join([
        f"# {entity_name} ({entity_id}) — operator underwriting draft",
        "",
        f"Evidence epoch: `{as_of}`. Benchmark: `{benchmark_id}`.",
        "",
        "## Thesis supplied by the operator",
        "",
        thesis_claim,
        "",
        "## Declared assumptions requiring review",
        "",
        f"- Equity beta: {beta:.3f}.",
        f"- Explicit-period owner-earnings growth: {base_growth:.2%} base; 0.00% stress.",
        f"- Terminal growth: {terminal_growth:.2%} base; 2.00% stress.",
        "- The filing-derived owner-earnings proxy is operating cash flow less reported capital expenditure.",
        "- Industry structure, competitive advantage, capital allocation, concentration, and management quality remain qualitative residuals until sourced.",
        "",
        "## Activation gate",
        "",
        "Review the source receipts, edit these assumptions, state a specific rival view and decisive observation, then activate the profile for paper tracking. Activation does not create brokerage authority.",
        "",
    ])


def create_public_equity_draft(
    workspace: str | Path,
    *,
    entity_id: str,
    entity_name: str,
    benchmark_id: str = "SPY",
    benchmark_name: str = "S&P 500 ETF benchmark",
    thesis_claim: str,
    beta: float = 1.0,
    base_growth: float = 0.03,
    terminal_growth: float = 0.025,
    overwrite: bool = False,
    discovery_origin: Mapping[str, Any] | None = None,
    research_dossier_path: str | None = None,
) -> dict[str, Any]:
    """Materialize a compilable operator draft from the latest source run."""
    root = Path(workspace).expanduser().resolve()
    source_run_path = root / "data" / "latest_source_run.json"
    observations_path = root / "data" / "observations.csv"
    if not source_run_path.is_file() or not observations_path.is_file():
        raise ValueError("refresh public sources before creating an equity draft")
    source_run = _read_json(source_run_path)
    if not source_run.get("ok"):
        raise ValueError("latest public-source run is not usable")
    entity = require_text(entity_id, "entity_id").upper()
    benchmark = require_text(benchmark_id, "benchmark_id").upper()
    name = require_text(entity_name, "entity_name")
    benchmark_label = require_text(benchmark_name, "benchmark_name")
    claim = require_text(thesis_claim, "thesis_claim")
    beta_value = require_finite(beta, "beta")
    base_growth_value = require_finite(base_growth, "base_growth")
    terminal_growth_value = require_finite(terminal_growth, "terminal_growth")
    if beta_value <= 0 or not -0.20 < base_growth_value < 0.30 or not -0.05 < terminal_growth_value < 0.08:
        raise ValueError("draft beta/growth assumptions are outside the supported bounded range")
    as_of = canonical_timestamp(source_run.get("as_of"), "source run as_of")
    rows = _latest_rows(observations_path, as_of=as_of)
    required_entity_metrics = (
        "price", "normalized_owner_earnings", "excess_net_cash", "diluted_shares",
        "owner_earnings_yield", "cash_conversion", "return_on_assets",
        "cash_to_assets", "net_debt_to_owner_earnings",
    )
    for metric in required_entity_metrics:
        _need(rows, entity, metric)
    _need(rows, benchmark, "price")
    erp_row = _need(rows, "US-MARKET", "implied_equity_risk_premium")
    risk_free_row = _need(rows, "US-MARKET", "risk_free_rate")
    erp = float(erp_row["value"])
    risk_free = float(risk_free_row["value"])
    slug = _safe_slug(entity)
    profile_id = f"jaggedthoughts.public-equity.{slug}"
    decision_timestamp = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    decision_date = decision_timestamp.date().isoformat()
    decision_epoch = decision_timestamp.strftime("%Y%m%d-%H%M%S")
    decision_id = f"{slug}-value-quality-{decision_epoch}"
    memo_id = f"{slug}_operator_underwriting"
    profile_path = root / "profiles" / "drafts" / f"{slug}.yaml"
    legacy_profile_path = root / "profiles" / f"{slug}.yaml"
    memo_path = root / "sources" / f"{slug}_underwriting.md"
    if (profile_path.exists() or legacy_profile_path.exists() or memo_path.exists()) and not overwrite:
        raise FileExistsError(f"draft already exists for {entity}; pass overwrite only to replace the draft")
    if overwrite and legacy_profile_path.exists():
        legacy = yaml.safe_load(legacy_profile_path.read_text(encoding="utf-8"))
        lifecycle = legacy.get("lifecycle") if isinstance(legacy, Mapping) else None
        if isinstance(lifecycle, Mapping) and lifecycle.get("stage") == "draft":
            legacy_profile_path.unlink()
    receipts = [row for row in source_run.get("source_receipts", []) if isinstance(row, Mapping)]
    source_entries = [{"id": memo_id, "path": memo_path.relative_to(root).as_posix()}]
    for receipt in receipts:
        source_entries.append({"id": str(receipt["source_id"]), "path": str(receipt["raw_path"])})
    raw_source_ids = [str(row["source_id"]) for row in receipts]
    dossier_id = ""
    if research_dossier_path:
        dossier = (root / research_dossier_path).resolve()
        try:
            dossier.relative_to(root)
        except ValueError as error:
            raise ValueError("research dossier escapes the investment workspace") from error
        if not dossier.is_file():
            raise ValueError("research dossier does not exist")
        dossier_id = f"{slug}_candidate_research_dossier"
        source_entries.append({"id": dossier_id, "path": dossier.relative_to(root).as_posix()})
    filing_ref = next((str(row["source_ref"]) for key, row in rows.items() if key[0] == entity and key[1] == "operating_cash_flow_fy"), raw_source_ids[0])
    price_ref = str(_need(rows, entity, "price")["source_ref"])
    benchmark_ref = str(_need(rows, benchmark, "price")["source_ref"])
    erp_ref = str(erp_row["source_ref"])
    evidence_refs = sorted({memo_id, filing_ref, price_ref, benchmark_ref, erp_ref, *([dossier_id] if dossier_id else [])})
    profile: dict[str, Any] = {
        "schema": PROFILE_SCHEMA,
        "profile_id": profile_id,
        "lifecycle": {"data_class": "operator", "stage": "draft", "authority": "paper"},
        "decision": {
            "id": decision_id, "as_of": as_of, "owner": "operator-paper-book",
            "question": f"What bounded paper position policy is justified for {entity} under the declared value-quality play?",
        },
        "entity": {"id": entity, "kind": "public_equity", "name": name, "currency": "USD"},
        "benchmark": {"id": benchmark, "kind": "index", "name": benchmark_label, "currency": "USD"},
        "play": {
            "id": "value-quality-large", "version": "1", "entity_kind": "public_equity",
            "universe": "US large-cap public equities", "benchmark_id": benchmark,
            "horizon_days": 365, "min_weight": 0, "max_weight": 0.10,
            "allow_short": False, "transaction_cost_bps": 15,
        },
        "sources": source_entries,
        "observations_file": "data/observations.csv",
        "price_metric": "price",
        "fingerprint": {
            "version": "1",
            "metrics": [
                {"id": "owner_earnings_yield", "unit": "decimal", "direction": "higher", "floor": 0.02, "ceiling": 0.10, "weight": 0.28},
                {"id": "cash_conversion", "unit": "multiple", "direction": "higher", "floor": 0.70, "ceiling": 1.50, "weight": 0.20},
                {"id": "return_on_assets", "unit": "decimal", "direction": "higher", "floor": 0.00, "ceiling": 0.15, "weight": 0.20},
                {"id": "net_debt_to_owner_earnings", "unit": "multiple", "direction": "lower", "floor": -1.0, "ceiling": 6.0, "weight": 0.22},
                {"id": "cash_to_assets", "unit": "decimal", "direction": "higher", "floor": 0.00, "ceiling": 0.25, "weight": 0.10},
            ],
        },
        "market_state": {
            "id": f"us-equity-premium-{decision_date}",
            "estimates": [
                {"id": "current-implied-erp", "annualized_premium": erp, "downside_return": -0.30, "weight": 0.60, "source_refs": [erp_ref]},
                {"id": "operator-low-premium", "annualized_premium": max(0.0, erp - 0.015), "downside_return": -0.38, "weight": 0.20, "source_refs": [memo_id, erp_ref]},
                {"id": "operator-high-premium", "annualized_premium": erp + 0.015, "downside_return": -0.22, "weight": 0.20, "source_refs": [memo_id, erp_ref]},
            ],
        },
        "valuation": {
            "grammar_id": "jaggedthoughts.value-quality.valuation", "version": "1",
            "max_depth": 4, "max_programs": 5000,
            "owner_earnings_metric": "normalized_owner_earnings",
            "excess_net_cash_metric": "excess_net_cash", "shares_metric": "diluted_shares",
            "risk_free_rate": {"id": "current-us-treasury", "value": risk_free, "source_refs": [erp_ref]},
            "equity_betas": [{"id": "operator-beta", "value": beta_value, "source_refs": [memo_id]}],
            "forecast_growth_rates": [
                {"id": "stress-growth", "value": 0.0, "source_refs": [memo_id]},
                {"id": "base-growth", "value": base_growth_value, "source_refs": [memo_id]},
            ],
            "terminal_growth_rates": [
                {"id": "stress-terminal", "value": 0.02, "source_refs": [memo_id]},
                {"id": "base-terminal", "value": terminal_growth_value, "source_refs": [memo_id]},
            ],
            "horizons": [{"id": "horizon-10y", "years": 10, "source_refs": [memo_id]}],
            "cash_flow_scenarios": [
                {"id": "durable-owner-earnings", "mechanism_id": "durable_earnings", "assumption_ids": ["base-growth", "base-terminal"], "source_refs": evidence_refs},
                {"id": "owner-earnings-mean-reversion", "mechanism_id": "earnings_mean_reversion", "assumption_ids": ["stress-growth", "stress-terminal"], "source_refs": evidence_refs},
            ],
        },
        "thesis": {
            "id": f"{slug}-value-quality-thesis", "version": "1", "claim": claim,
            "mechanism_ids": ["durable_earnings", "earnings_mean_reversion"],
            "catalysts": ["Owner earnings compound without balance-sheet deterioration.", "The market revises the durability and reinvestment runway upward."],
            "falsifiers": ["Normalized owner earnings decline across two reporting periods without a temporary working-capital explanation.", "Net debt to owner earnings exceeds six times.", "The source-backed strategy review fails to identify reinforcing choices that protect earnings power."],
            "source_refs": evidence_refs,
        },
        "underwriting": {
            "id": f"{slug}-value-quality-underwriting",
            "outside_view_reference": "Large-cap companies with comparable starting yield, leverage, and cash conversion.",
            "outside_view_base_rate": 0.50,
            "failure_sequence": ["Current owner earnings prove cyclical or overstated.", "Reinvestment fails to preserve or expand normalized earnings power.", "The valuation-implied return falls below the hurdle.", "A superior benchmark or cash alternative dominates the bounded action."],
            "hurdle_rate": 0.05,
            "next_best_alternative": f"Keep the capital in cash or the existing {benchmark} sleeve.",
            "rival_view": "The observed owner-earnings yield compensates for structural stagnation and balance-sheet risk rather than mispricing.",
            "decisive_observation": "Two reporting periods show stable or rising normalized owner earnings, non-worsening leverage, and evidence of a reinforcing strategic choice system.",
            "action_condition_id": "price-implies-hurdle", "source_refs": evidence_refs,
        },
        "portfolio": {"id": "operator-paper-book", "currency": "USD", "cash": 100000, "positions": []},
        "actions": [
            {"id": "watch", "kind": "watch", "description": f"Retain {entity} at zero weight while requesting the missing strategy and industry evidence.", "target_weight": 0, "primitive_cost": 0.1, "irreversibility": 0, "evidence_refs": evidence_refs},
            {"id": "start-3", "kind": "start", "description": "Open a three-percent paper position.", "target_weight": 0.03, "primitive_cost": 1, "irreversibility": 0.1, "evidence_refs": evidence_refs},
            {"id": "build-8", "kind": "add", "description": "Build an eight-percent paper position only when both hurdle and thesis conditions survive.", "target_weight": 0.08, "primitive_cost": 2, "irreversibility": 0.3, "evidence_refs": evidence_refs},
        ],
        "policy": {
            "grammar_id": "jaggedthoughts.value-quality.position-policy", "version": "1", "max_depth": 2, "max_programs": 1000,
            "state": {"downside_risk": 0.28, "thesis_confidence": 0.45},
            "conditions": [
                {"id": "premium-supportive", "path": "firm.market_premium", "operator": "ge", "value": 0.03, "evidence_refs": [erp_ref]},
                {"id": "price-implies-hurdle", "path": "firm.valuation_price_implied_excess_return", "operator": "ge", "value": 0.05, "evidence_refs": evidence_refs},
            ],
            "objectives": [
                {"id": "excess-return", "path": "firm.expected_excess_return", "direction": "maximize", "scale": 0.15, "utility_weight": 0.45},
                {"id": "downside", "path": "firm.downside_risk", "direction": "minimize", "scale": 0.40, "utility_weight": 0.30},
                {"id": "confidence", "path": "firm.thesis_confidence", "direction": "maximize", "scale": 1.0, "utility_weight": 0.20},
                {"id": "cost", "path": "firm.implementation_cost", "direction": "minimize", "scale": 0.01, "utility_weight": 0.05},
            ],
        },
        "representation": {
            "id": f"{slug}-source-draft-representation", "status": "residual",
            "residuals": ["Industry structure and competitor reactions are not yet represented.", "Strategic choice reinforcement, management quality, concentration, and capital-allocation evidence require sourced operator review.", "Market prices and current ERP are retrieval-time inputs and cannot support earlier simulated decisions."],
        },
        "mechanisms": [
            {
                "id": "durable_earnings", "description": "Reported owner earnings persist through reinforcing strategic choices and disciplined reinvestment.", "description_units": 5, "evidence_refs": evidence_refs,
                "rules": [
                    {"id": "durable-watch", "actions": ["watch"], "effects": {"firm.expected_excess_return": -0.005, "firm.downside_risk": -0.02}, "evidence_refs": evidence_refs},
                    {"id": "durable-start", "actions": ["start-3"], "effects": {"firm.expected_excess_return": 0.025, "firm.downside_risk": 0.04, "firm.thesis_confidence": 0.08}, "evidence_refs": evidence_refs},
                    {"id": "durable-build", "actions": ["build-8"], "effects": {"firm.expected_excess_return": 0.045, "firm.downside_risk": 0.08, "firm.thesis_confidence": 0.12}, "evidence_refs": evidence_refs},
                ],
            },
            {
                "id": "earnings_mean_reversion", "description": "Owner earnings mean-revert while debt and strategic inertia constrain adaptation.", "description_units": 5, "evidence_refs": evidence_refs,
                "rules": [
                    {"id": "reversion-watch", "actions": ["watch"], "effects": {"firm.downside_risk": -0.03, "firm.thesis_confidence": -0.03}, "evidence_refs": evidence_refs},
                    {"id": "reversion-start", "actions": ["start-3"], "effects": {"firm.expected_excess_return": -0.005, "firm.downside_risk": 0.12, "firm.thesis_confidence": -0.10}, "evidence_refs": evidence_refs},
                    {"id": "reversion-build", "actions": ["build-8"], "effects": {"firm.expected_excess_return": -0.025, "firm.downside_risk": 0.20, "firm.thesis_confidence": -0.16}, "evidence_refs": evidence_refs},
                ],
            },
        ],
    }
    if discovery_origin is not None:
        origin = dict(discovery_origin)
        if origin.get("schema") != "jaggedthoughts-discovery-origin-v1":
            raise ValueError("draft discovery_origin has an unsupported schema")
        if str(origin.get("entity_id") or "").upper() != entity:
            raise ValueError("draft discovery_origin entity does not match the profile entity")
        profile["discovery_origin"] = origin
    if research_dossier_path:
        profile["research_dossier"] = {
            "source_id": dossier_id, "path": research_dossier_path,
        }
    _atomic_text(memo_path, _memo(
        entity_id=entity, entity_name=name, benchmark_id=benchmark, thesis_claim=claim,
        as_of=as_of, beta=beta_value, base_growth=base_growth_value,
        terminal_growth=terminal_growth_value,
    ))
    _atomic_text(profile_path, yaml.safe_dump(profile, sort_keys=False, allow_unicode=True))
    source_run_sha256 = require_text(source_run.get("run_sha256"), "source run hash")
    source_ref = FunnelObjectRef(
        object_kind="public_source_epoch",
        object_id=f"{entity}@{as_of}",
        sha256=source_run_sha256,
    )
    screen_payload = {
        "schema": "jaggedthoughts-public-equity-source-screen-v1",
        "entity_id": entity,
        "as_of": as_of,
        "required_metrics": list(required_entity_metrics),
        "observation_ids": sorted(
            str(_need(rows, entity, metric)["observation_id"])
            for metric in required_entity_metrics
        ),
    }
    screen_ref = FunnelObjectRef(
        object_kind="public_equity_source_screen",
        object_id=f"{entity}@{as_of}",
        sha256=stable_sha256(screen_payload),
    )
    draft_ref = FunnelObjectRef(
        object_kind="investment_profile_draft",
        object_id=profile_id,
        sha256=stable_sha256(profile),
    )
    transitions = (
        FunnelTransitionReceipt(
            transition_id=f"{entity}:{decision_date}:source-screen",
            from_state="observed",
            event="qualify",
            to_state="screened",
            occurred_at=as_of,
            predecessor=source_ref,
            successor=screen_ref,
            guard_refs=tuple(raw_source_ids),
            context={"required_metric_count": len(required_entity_metrics)},
        ),
        FunnelTransitionReceipt(
            transition_id=f"{entity}:{decision_date}:screen-draft",
            from_state="screened",
            event="draft",
            to_state="draft",
            occurred_at=as_of,
            predecessor=screen_ref,
            successor=draft_ref,
            guard_refs=tuple(evidence_refs),
            context={"profile_id": profile_id, "authority": "paper"},
        ),
    )
    return {
        "schema": DRAFT_SCHEMA, "ok": True, "profile_id": profile_id,
        "decision_id": decision_id, "stage": "draft", "entity_id": entity,
        "as_of": as_of, "profile_path": profile_path.relative_to(root).as_posix(),
        "memo_path": memo_path.relative_to(root).as_posix(),
        "required_operator_transition": "review_and_activate",
        "funnel_transitions": [row.to_dict() for row in transitions],
        "discovery_origin": dict(discovery_origin) if discovery_origin is not None else None,
    }


def activate_public_equity_profile(
    workspace: str | Path, *, profile_id: str, confirmation: str
) -> dict[str, Any]:
    """Move one reviewed operator profile from draft to active paper tracking."""
    root = Path(workspace).expanduser().resolve()
    expected = f"activate {require_text(profile_id, 'profile_id')} for paper tracking"
    if confirmation.strip() != expected:
        raise ValueError(f"activation confirmation must exactly equal: {expected}")
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((root / "profiles").glob("**/*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and str(payload.get("profile_id") or "") == profile_id:
            matches.append((path, payload))
    if len(matches) != 1:
        raise ValueError(f"expected one profile for {profile_id}, found {len(matches)}")
    path, payload = matches[0]
    draft_sha256 = stable_sha256(payload)
    lifecycle = payload.get("lifecycle")
    if not isinstance(lifecycle, dict) or lifecycle.get("data_class") != "operator":
        raise ValueError("only operator drafts can be activated")
    if lifecycle.get("stage") != "draft":
        raise ValueError("profile is not in the draft stage")
    activated_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    suffix = activated_at.replace("-", "").replace(":", "").replace("T", "-").removesuffix("Z")
    active_profile_id = f"{profile_id}.active.{suffix}"
    lifecycle["stage"] = "active"
    payload["profile_id"] = active_profile_id
    decision = payload.get("decision")
    if not isinstance(decision, dict):
        raise ValueError("profile decision block is absent")
    decision["id"] = f"{decision.get('id')}-active-{suffix}"
    payload["activation"] = {
        "source_profile_id": profile_id,
        "activated_at": activated_at,
        "confirmation": confirmation,
    }
    active_path = root / "profiles" / f"{_safe_slug(str((payload.get('entity') or {}).get('id') or profile_id))}.yaml"
    if active_path.exists():
        raise FileExistsError(f"an active profile already exists: {active_path.relative_to(root)}")
    active_sha256 = stable_sha256(payload)
    _atomic_text(active_path, yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    archive_path = root / "profiles" / "archive" / f"{_safe_slug(profile_id)}-{suffix}.yaml"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    path.replace(archive_path)
    transition = FunnelTransitionReceipt(
        transition_id=f"{profile_id}:activate:{suffix}",
        from_state="draft",
        event="activate_paper",
        to_state="active_paper",
        occurred_at=activated_at,
        predecessor=FunnelObjectRef(
            object_kind="investment_profile_draft",
            object_id=profile_id,
            sha256=draft_sha256,
        ),
        successor=FunnelObjectRef(
            object_kind="investment_profile_active",
            object_id=active_profile_id,
            sha256=active_sha256,
        ),
        guard_refs=(stable_sha256({"confirmation": confirmation}), profile_id),
        context={
            "authority": "paper",
            "source_profile_path": path.relative_to(root).as_posix(),
            "archived_profile_path": archive_path.relative_to(root).as_posix(),
        },
    )
    return {
        "schema": "jaggedthoughts-public-equity-profile-activation-v1", "ok": True,
        "source_profile_id": profile_id, "profile_id": active_profile_id,
        "stage": "active", "authority": "paper",
        "profile_path": active_path.relative_to(root).as_posix(),
        "source_profile_path": path.relative_to(root).as_posix(),
        "archived_profile_path": archive_path.relative_to(root).as_posix(),
        "funnel_transition": transition.to_dict(),
    }


__all__ = ["activate_public_equity_profile", "create_public_equity_draft"]
