"""Budgeted autonomous enrichment and agent-ready research jobs.

This module selects *research acquisitions*, never investments.  The ranking
proxy is inspectable and explicitly uncalibrated until prospective job and
paper outcomes exist.  Durable queue ownership is delegated to the existing
SQLite lease bus; investment identity, selection receipts, and research
handoffs remain owned here.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Mapping, Sequence

import yaml
from scipy.stats import bootstrap, permutation_test

from ztare.common.control_state_machine import ControlStateChart, ControlTransition
from ztare.common.equivariance import stable_sha256
from ztare.leanmill import work_queue
from ztare.motion.set_distance import jaccard_distance

from .contracts import canonical_timestamp, require_finite, require_text, timestamp_key
from .learning_credit import learning_credit_allows
from .research_question_policy_outcome import (
    compile_research_question_policy_outcome_contract,
)
from .research_questions import (
    RESEARCH_QUESTION_FRONTIER_SCHEMA,
    compile_research_question_frontier,
)


ENRICHMENT_POLICY_SCHEMA = "jaggedthoughts-autonomous-enrichment-policy-v1"
ENRICHMENT_CYCLE_SCHEMA = "jaggedthoughts-autonomous-enrichment-cycle-v1"
ENRICHMENT_JOB_SCHEMA = "jaggedthoughts-enrichment-job-v1"
RESEARCH_REQUEST_SCHEMA = "jaggedthoughts-agent-research-request-v1"
RESEARCH_DOSSIER_SCHEMA = "jaggedthoughts-candidate-research-dossier-v1"
RESEARCH_LEARNING_SCHEMA = "jaggedthoughts-research-acquisition-learning-v1"
ENRICHMENT_JOB_KIND = "jaggedthoughts_public_market_enrichment"
RESEARCH_POLICY_ASSIGNMENT_SCHEMA = "jaggedthoughts-research-question-policy-assignment-v2"
RESEARCH_ROUTING_DECISION_SCHEMA = "jaggedthoughts-research-question-routing-decision-v1"
_RESEARCH_POLICY_EXPERIMENT = "coverage-vs-disagreement-itt-v2"
_RESEARCH_POLICY_ARMS = ("coverage_first", "disagreement_first")


def validated_research_request_basis_sha256(request: Mapping[str, Any]) -> str:
    """Return the request's candidate-bound qualitative basis, or fail closed."""

    if request.get("schema") != RESEARCH_REQUEST_SCHEMA:
        raise ValueError("research basis authority requires a research request")
    declared = str(request.get("request_sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", declared) or declared != stable_sha256({
        key: value for key, value in request.items() if key != "request_sha256"
    }):
        raise ValueError("research request content hash mismatch")
    basis = request.get("qualitative_research_basis")
    basis_sha = str(request.get("qualitative_research_basis_sha256") or "")
    if (
        not isinstance(basis, Mapping)
        or not re.fullmatch(r"[0-9a-f]{64}", basis_sha)
        or stable_sha256(basis) != basis_sha
        or any(
            str(basis.get(field) or "") != str(request.get(field) or "")
            for field in ("candidate_id", "entity_id", "entity_kind")
        )
    ):
        raise ValueError("research request qualitative basis is invalid")
    return basis_sha


def _independent_randomization_inference(
    treatment: Sequence[float], control: Sequence[float], *, seed: int,
    confidence_level: float,
) -> dict[str, Any]:
    if len(treatment) < 5 or len(control) < 5:
        return {
            "n_treatment": len(treatment), "n_control": len(control),
            "observed_delta": None, "p_value": None,
            "note": "insufficient independent observations (minimum 5 per arm)",
        }
    statistic = lambda left, right: float(left.mean() - right.mean())
    inference = permutation_test(
        (treatment, control), statistic, permutation_type="independent",
        vectorized=False, n_resamples=5_000, random_state=seed,
    )
    interval = bootstrap(
        (treatment, control), statistic, paired=False, vectorized=False,
        confidence_level=confidence_level, n_resamples=5_000,
        method="percentile", random_state=seed,
    ).confidence_interval
    return {
        "n_treatment": len(treatment), "n_control": len(control),
        "observed_delta": round(float(inference.statistic), 4),
        "ci_lo": round(float(interval.low), 4),
        "ci_hi": round(float(interval.high), 4),
        "p_value": round(float(inference.pvalue), 4),
    }


class ResearchEvidenceTimestampError(ValueError):
    """A source publication value cannot support point-in-time admission."""

    def __init__(self, *, label: str, value: Any, source: Mapping[str, Any]) -> None:
        self.label = label
        self.raw_value = str(value or "").strip()
        self.source_id = str(source.get("id") or "")
        self.source_url = str(source.get("url") or "")
        self.dossier_body_sha256: str | None = None
        match = re.search(r"sources\[(\d+)\]", label)
        self.source_index = int(match.group(1)) if match else None
        super().__init__(
            f"{label} must be an ISO-8601 date or timezone timestamp"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason_code": "ambiguous_or_invalid_publication_time",
            "field": self.label,
            "source_index": self.source_index,
            "source_id": self.source_id or None,
            "source_url": self.source_url or None,
            "raw_value": self.raw_value,
            "publication_time_inferred": False,
        }


def _canonical_publication_time(
    value: Any, *, label: str, source: Mapping[str, Any],
) -> tuple[str, str]:
    """Return canonical source form and its earliest possible publication time."""
    try:
        text = require_text(value, label)
    except ValueError as error:
        raise ResearchEvidenceTimestampError(
            label=label, value=value, source=source,
        ) from error
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            canonical_date = date.fromisoformat(text).isoformat()
        except ValueError as error:
            raise ResearchEvidenceTimestampError(
                label=label, value=value, source=source,
            ) from error
        return canonical_date, f"{canonical_date}T00:00:00Z"
    try:
        timestamp = canonical_timestamp(text, label)
    except ValueError as error:
        raise ResearchEvidenceTimestampError(
            label=label, value=value, source=source,
        ) from error
    return timestamp, timestamp


RESEARCH_JOB_LIFECYCLE = ControlStateChart(
    schema="jaggedthoughts-research-job-state-chart-v1",
    transitions=(
        ControlTransition("proposed", "enqueue", "queued", "selection receipt and budgets are frozen"),
        ControlTransition("queued", "lease", "leased", "one worker owns an unexpired compare-and-set lease"),
        ControlTransition("leased", "start", "enriching", "job identity and source budget still match"),
        ControlTransition("enriching", "evidence_ready", "evidence_ready", "source epoch and discovery leaf exist"),
        ControlTransition("enriching", "block", "blocked", "failure and retry boundary are recorded"),
        ControlTransition("blocked", "repair_evidence", "evidence_ready", "a later source epoch repairs the typed block and binds a new candidate leaf"),
        ControlTransition("evidence_ready", "supersede", "superseded", "a later discovery identity owns the entity"),
        ControlTransition("evidence_ready", "submit_dossier", "researched", "typed dossier binds the candidate leaf"),
        ControlTransition("researched", "create_draft", "drafted", "qualified public equity passes the kernel handoff"),
        ControlTransition("drafted", "activate_paper", "paper_active", "operator confirmation exists"),
        ControlTransition("paper_active", "settle", "settled", "later outcome binds the frozen decision"),
        ControlTransition("settled", "learn", "learned", "outcome changes a policy or calibration record"),
        ControlTransition("blocked", "retry", "queued", "retry budget and cooldown permit another attempt"),
    ),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def validated_discovery_research_handoff(
    workspace: str | Path, run: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return the completed queue handoff bound to one discovery identity."""
    root = Path(workspace).expanduser().resolve()
    handoff_path = root / "state" / "discovery_research_handoff.json"
    if not handoff_path.is_file():
        return None
    try:
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    handoff_body = {
        key: value for key, value in handoff.items() if key != "handoff_sha256"
    }
    if (
        handoff.get("schema") != "jaggedthoughts-discovery-research-handoff-v1"
        or handoff.get("handoff_sha256") != stable_sha256(handoff_body)
        or handoff.get("status") != "complete"
        or handoff.get("discovery_run_id") != run.get("run_id")
        or handoff.get("discovery_run_sha256") != run.get("run_sha256")
    ):
        return None
    return handoff


def latest_discovery_candidate_index(
    workspace: str | Path, *, allow_pending_handoff: bool = False,
) -> dict[str, dict[str, Any]]:
    """Index the current discovery identities that may still accept research."""
    root = Path(workspace).expanduser().resolve()
    try:
        run = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
        record = json.loads((root / "discovery" / "latest_record.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if (
        run.get("run_id") != record.get("run_id")
        or run.get("run_sha256") != record.get("run_sha256")
    ):
        return {}
    if not allow_pending_handoff and not validated_discovery_research_handoff(root, run):
        return {}
    leaves = record.get("candidate_leaves") if isinstance(record, Mapping) else {}
    learned_by_candidate: dict[str, Mapping[str, Any]] = {}
    try:
        book = json.loads(
            (root / "opportunity_books" / "latest.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        book = {}
    if (
        book.get("schema") == "jaggedthoughts-opportunity-book-v1"
        and book.get("discovery_run_id") == run.get("run_id")
        and book.get("discovery_run_sha256") == run.get("run_sha256")
        and book.get("book_sha256") == stable_sha256({
            key: value for key, value in book.items() if key != "book_sha256"
        })
    ):
        learned_by_candidate = {
            str(row["candidate_id"]): row
            for row in book.get("candidates") or ()
            if isinstance(row, Mapping) and row.get("candidate_id")
        }
    research_bases_by_identity: dict[tuple[str, str], set[str]] = {}
    for path in sorted((root / "research_jobs" / "requests").glob("*.json")):
        try:
            request = json.loads(path.read_text(encoding="utf-8"))
            basis_sha = validated_research_request_basis_sha256(request)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        candidate_leaf = str(request.get("candidate_leaf") or "")
        candidate_id = str(request.get("candidate_id") or "")
        if candidate_leaf and candidate_id:
            research_bases_by_identity.setdefault(
                (candidate_id, candidate_leaf), set()
            ).add(basis_sha)
    candidates = {}
    for row in run.get("candidates", ()):
        if not isinstance(row, Mapping) or not row.get("candidate_id"):
            continue
        candidate_id = str(row["candidate_id"])
        learned = learned_by_candidate.get(candidate_id) or {}
        if learned.get("candidate_sha256") != row.get("candidate_sha256"):
            learned = {}
        candidates[candidate_id] = {
            "candidate_id": row["candidate_id"],
            "discovery_run_id": run.get("run_id"),
            "candidate_sha256": row.get("candidate_sha256"),
            "candidate_leaf": (leaves or {}).get(str(row["candidate_id"])),
            "entity_id": row.get("entity_id"),
            "entity_kind": row.get("entity_kind"),
            "screen_status": row.get("screen_status"),
            "rank": row.get("rank"),
            "research_rank": row.get("research_rank"),
            "potential_rank": row.get("potential_rank"),
            "rank_score": row.get("rank_score"),
            "learned_research_rank": learned.get("learned_research_rank"),
            "learned_potential_rank": learned.get("learned_potential_rank"),
            "learned_research_priority_score": learned.get(
                "learned_research_priority_score"
            ),
            "research_priority_routing_source": ({
                "opportunity_book_sha256": book.get("book_sha256"),
                "law_policy_influence_sha256": (
                    book.get("law_policy_influence") or {}
                ).get("influence_sha256"),
                "causal_law_influence_set_sha256": (
                    book.get("causal_law_target_influence") or {}
                ).get("influence_set_sha256"),
                "authority": "paper_research_priority_only",
                "capital_authority": False,
            } if learned else None),
            "as_of": row.get("as_of"),
            "qualitative_research_basis_sha256": next(iter(bases)) if len(
                bases := research_bases_by_identity.get((
                    candidate_id,
                    str((leaves or {}).get(candidate_id) or ""),
                ), set())
            ) == 1 else None,
        }
    return candidates


def research_request_currency(
    request: Mapping[str, Any], candidate_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare one immutable request with the current candidate identity."""
    current = candidate_index.get(str(request.get("candidate_id") or ""))
    is_current = bool(
        current
        and current.get("candidate_sha256") == request.get("candidate_sha256")
        and current.get("candidate_leaf") == request.get("candidate_leaf")
    )
    try:
        request_basis = validated_research_request_basis_sha256(request)
    except ValueError:
        request_basis = ""
    current_basis = str((current or {}).get("qualitative_research_basis_sha256") or "")
    compatible_successor = bool(
        current and not is_current and request_basis and request_basis == current_basis
    )
    return {
        "known": current is not None,
        "is_current": is_current,
        "admissible": is_current or compatible_successor,
        "currency": (
            "exact" if is_current else
            "compatible_successor" if compatible_successor else
            "superseded"
        ),
        "qualitative_research_current": is_current or compatible_successor,
        "compatible_successor": compatible_successor,
        "request_qualitative_research_basis_sha256": request_basis or None,
        "current_qualitative_research_basis_sha256": current_basis or None,
        "current_candidate_sha256": (current or {}).get("candidate_sha256"),
        "current_candidate_leaf": (current or {}).get("candidate_leaf"),
        "current_discovery_run_id": (current or {}).get("discovery_run_id"),
        "current_rank": (current or {}).get("rank"),
        "current_research_rank": (current or {}).get("research_rank"),
        "current_potential_rank": (current or {}).get("potential_rank"),
        "current_screen_status": (current or {}).get("screen_status"),
        "current_rank_score": (current or {}).get("rank_score"),
        "current_as_of": (current or {}).get("as_of"),
    }


def default_enrichment_policy() -> dict[str, Any]:
    """Return a bounded starter policy whose automatic authority ends at evidence."""
    return {
        "schema": ENRICHMENT_POLICY_SCHEMA,
        "enabled": True,
        "auto_enroll": True,
        "auto_fetch_public_data": True,
        "lease_seconds": 3600,
        "max_attempts": 2,
        "retry_cooldown_hours": 168,
        "source_refresh": {
            "core_source_ids": [],
            "always_adapters": ["damodaran_current_erp", "fred_series"],
            "include_active_profile_entities": True,
            "include_research_request_entities": True,
            "reserved_maintenance_source_calls": 2,
            "max_maintenance_source_calls": 8,
        },
        "fund_lookthrough": {
            "enabled": True,
            "max_source_calls": 10,
        },
        "budgets": {
            "max_equities": 3,
            "max_funds": 2,
            "max_incremental_source_calls": 13,
            "max_total_source_calls": 48,
            "max_estimated_research_minutes": 180,
            "max_equities_per_sector": 1,
        },
        "cost_model": {
            "public_equity": {"incremental_source_calls": 3, "research_minutes": 40},
            "public_fund": {"incremental_source_calls": 2, "research_minutes": 25},
            "sec_registry_batch_source_calls": 1,
        },
        "score_weights": {
            "measurement_value_proxy": 0.35,
            "request_specificity": 0.20,
            "identity_coverage": 0.15,
            "liquidity": 0.10,
            "source_efficiency": 0.20,
        },
        "diversity_weight": 0.25,
        "minimum_priority": 0.20,
        "activation_boundary": (
            "Automation may enroll bounded public sources, refresh evidence, run deep screens, "
            "and emit agent research requests. A separate capital-cycle policy may enroll only "
            "fully gated zero-weight paper watches; portfolio admission and brokerage execution "
            "remain separate transitions."
        ),
        "agent_research": {
            "enabled": False,
            "runtime": "codex",
            "model": "account-default",
            "reasoning_effort": "high",
            "timeout_seconds": 1200,
            "lease_seconds": 1800,
            "poll_seconds": 60,
            "max_attempts": 3,
            "max_dispatches_per_day": 1,
        },
    }


def load_enrichment_policy(path: str | Path) -> Mapping[str, Any]:
    payload = yaml.safe_load(Path(path).expanduser().resolve().read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema") != ENRICHMENT_POLICY_SCHEMA:
        raise ValueError(f"enrichment policy schema must be {ENRICHMENT_POLICY_SCHEMA}")
    _validated_policy(payload)
    return payload


def _validated_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    budgets = policy.get("budgets")
    costs = policy.get("cost_model")
    weights = policy.get("score_weights")
    if not isinstance(budgets, Mapping) or not isinstance(costs, Mapping) or not isinstance(weights, Mapping):
        raise ValueError("enrichment policy requires budgets, cost_model, and score_weights objects")
    normalized_budgets: dict[str, int] = {}
    for key in (
        "max_equities", "max_funds", "max_incremental_source_calls",
        "max_total_source_calls", "max_estimated_research_minutes",
        "max_equities_per_sector",
    ):
        value = budgets.get(key)
        if isinstance(value, bool) or int(value) < 0:
            raise ValueError(f"enrichment budget {key} must be a nonnegative integer")
        normalized_budgets[key] = int(value)
    normalized_costs: dict[str, dict[str, int]] = {}
    for kind in ("public_equity", "public_fund"):
        row = costs.get(kind)
        if not isinstance(row, Mapping):
            raise ValueError(f"enrichment cost_model requires {kind}")
        normalized_costs[kind] = {}
        for key in ("incremental_source_calls", "research_minutes"):
            value = row.get(key)
            if isinstance(value, bool) or int(value) < 0:
                raise ValueError(f"enrichment {kind}.{key} must be a nonnegative integer")
            normalized_costs[kind][key] = int(value)
    registry_calls = int(costs.get("sec_registry_batch_source_calls", 1))
    if registry_calls < 0:
        raise ValueError("sec_registry_batch_source_calls cannot be negative")
    normalized_weights = {
        key: require_finite(weights.get(key, 0), f"enrichment score weight {key}")
        for key in (
            "measurement_value_proxy", "request_specificity", "identity_coverage",
            "liquidity", "source_efficiency",
        )
    }
    if any(value < 0 for value in normalized_weights.values()) or sum(normalized_weights.values()) <= 0:
        raise ValueError("enrichment score weights must be nonnegative with a positive sum")
    minimum = require_finite(policy.get("minimum_priority", 0), "minimum_priority")
    diversity = require_finite(policy.get("diversity_weight", 0), "diversity_weight")
    if not 0 <= minimum <= 2 or diversity < 0:
        raise ValueError("enrichment priority bounds are invalid")
    return {
        "budgets": normalized_budgets,
        "costs": normalized_costs,
        "registry_calls": registry_calls,
        "weights": normalized_weights,
        "minimum_priority": minimum,
        "diversity_weight": diversity,
        "lease_seconds": max(60, int(policy.get("lease_seconds", 3600))),
        "max_attempts": max(1, int(policy.get("max_attempts", 2))),
        "retry_cooldown_hours": max(0, int(policy.get("retry_cooldown_hours", 168))),
    }


@dataclass(frozen=True, slots=True)
class EnrichmentCost:
    incremental_source_calls: int
    research_minutes: int

    def to_dict(self) -> dict[str, int]:
        return {
            "incremental_source_calls": self.incremental_source_calls,
            "research_minutes": self.research_minutes,
        }


def _intent_specificity(intent: Mapping[str, Any]) -> float:
    fields = (
        bool(intent.get("capitalization")), bool(intent.get("styles")),
        bool(intent.get("theme_terms") or intent.get("themes")),
        bool(intent.get("countries")), bool(intent.get("direct_symbols")),
    )
    return sum(fields) / len(fields)


def _identity_coverage(candidate: Mapping[str, Any]) -> float:
    keys = (
        ("symbol", "name", "last_price", "volume", "market_cap", "sector", "industry")
        if candidate.get("entity_kind") == "public_equity"
        else ("symbol", "name", "last_price", "volume", "one_year_return")
    )
    return sum(candidate.get(key) not in {None, ""} for key in keys) / len(keys)


def _feature_set(candidate: Mapping[str, Any]) -> set[str]:
    values = {
        f"kind:{candidate.get('entity_kind')}",
        f"sector:{str(candidate.get('sector') or 'unknown').lower()}",
        f"industry:{str(candidate.get('industry') or 'unknown').lower()}",
    }
    values.update(f"intent:{value}" for value in candidate.get("intent_ids") or ())
    values.update(f"style:{value}" for value in candidate.get("styles") or ())
    values.update(f"objective:{value}" for value in candidate.get("requested_measurements") or ())
    return values


def _marginal_diversity(candidate: Mapping[str, Any], selected: Sequence[Mapping[str, Any]]) -> float:
    if not selected:
        return 1.0
    features = _feature_set(candidate)
    return min(jaccard_distance(features, _feature_set(row)) for row in selected)


def _research_question(arm_id: str, entity_kind: str) -> str:
    if arm_id == "disagreement_first":
        subject = "strategy and earnings-power" if entity_kind == "public_equity" else "exposure, cost, and implementation"
        return f"Which public evidence most sharply discriminates the {subject} thesis from its strongest rival?"
    return "Which primary-source facts most change the durability, valuation, risk, and implementation assessment?"


def _research_policy_assignment(
    *, arm_id: str, entity_kind: str, assignment_unit_id: str,
    issue_batch_sha256: str, randomization_sha256: str,
    assigned_at: str, economic_outcome_horizon_days: int,
    eligible: bool = True, routing_mode: str = "balanced_audit",
    routing_decision_sha256: str | None = None,
) -> dict[str, Any]:
    outcome_due_at = (
        timestamp_key(assigned_at) + timedelta(days=economic_outcome_horizon_days)
    ).isoformat(timespec="seconds").replace("+00:00", "Z")
    body = {
        "schema": RESEARCH_POLICY_ASSIGNMENT_SCHEMA,
        "experiment_id": _RESEARCH_POLICY_EXPERIMENT,
        "eligible": eligible,
        "arm_id": arm_id,
        "research_question": _research_question(arm_id, entity_kind),
        "assignment_unit_id": assignment_unit_id,
        "assignment_probability": 0.5 if eligible else 1.0,
        "issue_batch_sha256": issue_batch_sha256,
        "randomization_sha256": randomization_sha256,
        "assigned_at": assigned_at,
        "economic_outcome": "incremental_return_vs_no_action",
        "economic_outcome_horizon_days": economic_outcome_horizon_days,
        "outcome_due_at": outcome_due_at,
        "routing_mode": routing_mode,
        "stratum": {"entity_kind": entity_kind},
        "common_output_contract": RESEARCH_DOSSIER_SCHEMA,
        "capital_authority": False,
    }
    if routing_decision_sha256:
        body["routing_decision_sha256"] = routing_decision_sha256
    return {**body, "assignment_sha256": stable_sha256(body)}


def _learned_research_arm(
    decision: Mapping[str, Any] | None,
    learning_credit_assignment: Mapping[str, Any] | None,
    current_research_learning: Mapping[str, Any] | None,
) -> tuple[str, str] | None:
    if not isinstance(decision, Mapping):
        return None
    body = dict(decision)
    declared = str(body.pop("decision_sha256", ""))
    arm = str(body.get("recommended_arm") or "")
    if (
        body.get("schema") != RESEARCH_ROUTING_DECISION_SCHEMA
        or not body.get("routing_change_allowed")
        or arm not in _RESEARCH_POLICY_ARMS
        or stable_sha256(body) != declared
    ):
        return None
    learning = dict(current_research_learning or {})
    learning_sha = str(learning.pop("learning_sha256", ""))
    current_decision = (
        (learning.get("research_question_policy_experiment") or {}).get(
            "routing_decision"
        )
        if isinstance(learning.get("research_question_policy_experiment"), Mapping)
        else None
    )
    if (
        learning.get("schema") != RESEARCH_LEARNING_SCHEMA
        or stable_sha256(learning) != learning_sha
        or current_decision != decision
    ):
        return None
    try:
        admitted = learning_credit_allows(
            learning_credit_assignment or {},
            component_id="research_question_policy",
            use="future_research_question_routing",
            source_ref=declared,
        ) and learning_credit_allows(
            learning_credit_assignment or {},
            component_id="research_question_policy",
            use="future_research_question_routing",
            source_ref=learning_sha,
        )
    except ValueError:
        return None
    if not admitted:
        return None
    return arm, declared


def assign_research_question_policies(
    selected: Sequence[dict[str, Any]], *, source_run_ids: Sequence[str], completed_at: str,
    routing_decision: Mapping[str, Any] | None = None,
    learning_credit_assignment: Mapping[str, Any] | None = None,
    current_research_learning: Mapping[str, Any] | None = None,
    economic_outcome_horizon_days: int = 365,
) -> None:
    """Freeze candidate-level Bernoulli assignments for an append-only ITT census."""
    if (
        isinstance(economic_outcome_horizon_days, bool)
        or economic_outcome_horizon_days < 1
    ):
        raise ValueError("economic_outcome_horizon_days must be a positive integer")
    assigned_at = canonical_timestamp(completed_at, "research policy completed_at")
    learned = _learned_research_arm(
        routing_decision, learning_credit_assignment, current_research_learning,
    )
    for entity_kind in ("public_equity", "public_fund"):
        rows = [row for row in selected if row.get("entity_kind") == entity_kind]
        issue_batch_sha256 = stable_sha256({
            "source_run_ids": list(source_run_ids),
            "completed_at": assigned_at,
        })
        for row in rows:
            assignment_unit_id = _assignment_unit_id(row)
            randomization_sha256 = stable_sha256({
                "experiment_id": _RESEARCH_POLICY_EXPERIMENT,
                "assignment_unit_id": assignment_unit_id,
            })
            audit_assignment = learned is None or (
                int(randomization_sha256[8:16], 16) % 2 == 0
            )
            arm_id = (
                _RESEARCH_POLICY_ARMS[
                    int(randomization_sha256[:8], 16) % len(_RESEARCH_POLICY_ARMS)
                ]
                if audit_assignment else learned[0]
            )
            row["research_policy_assignment"] = _research_policy_assignment(
                arm_id=arm_id,
                entity_kind=entity_kind,
                assignment_unit_id=assignment_unit_id,
                issue_batch_sha256=issue_batch_sha256,
                randomization_sha256=randomization_sha256,
                assigned_at=assigned_at,
                economic_outcome_horizon_days=economic_outcome_horizon_days,
                eligible=audit_assignment,
                routing_mode=(
                    "balanced_audit" if audit_assignment else "learned_operational"
                ),
                routing_decision_sha256=learned[1] if learned else None,
            )


def _assignment_unit_id(row: Mapping[str, Any]) -> str:
    for key in ("candidate_leaf", "candidate_id", "security_id", "entity_id", "symbol"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    raise ValueError("research policy assignment requires a stable candidate identity")


def _prior_attempts(
    prior_jobs: Sequence[Mapping[str, Any]], security_id: str, *, current: datetime,
    cooldown_hours: int,
) -> tuple[int, bool]:
    attempts = 0
    cooldown_active = False
    cutoff = current - timedelta(hours=cooldown_hours)
    for row in prior_jobs:
        payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
        if str(payload.get("security_id") or "") != security_id:
            continue
        attempts += int(row.get("attempts") or 0)
        updated = row.get("updated_at")
        if updated is not None:
            try:
                when = datetime.fromtimestamp(int(updated), tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                continue
            cooldown_active = cooldown_active or when >= cutoff
    return attempts, cooldown_active


def _candidate_rows(scout_runs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for scout in scout_runs:
        intent = scout.get("intent") if isinstance(scout.get("intent"), Mapping) else {}
        intent_id = str(scout.get("scheduled_intent_id") or intent.get("intent_sha256") or scout.get("run_id"))
        for raw in scout.get("candidates") or ():
            if not isinstance(raw, Mapping):
                continue
            security_id = require_text(raw.get("security_id"), "scout candidate security_id")
            row = grouped.setdefault(security_id, {
                **dict(raw),
                "security_id": security_id,
                "intent_ids": [],
                "scout_run_ids": [],
                "scout_run_paths": [],
                "styles": [],
                "requested_measurements": [],
                "intent_specificities": [],
            })
            row["intent_ids"].append(intent_id)
            row["scout_run_ids"].append(str(scout.get("run_id") or ""))
            row["scout_run_paths"].append(str(scout.get("run_path") or ""))
            row["styles"].extend(str(value) for value in intent.get("styles") or ())
            row["requested_measurements"].extend(
                str(value) for value in raw.get("requested_measurements") or ()
            )
            row["intent_specificities"].append(_intent_specificity(intent))
            if scout.get("potential_scope_only") and raw.get("base_priority") is not None:
                priority = require_finite(
                    raw["base_priority"], "potential-scoped scout base_priority",
                )
                row["investment_potential_priority"] = max(
                    priority, float(row.get("investment_potential_priority") or 0.0),
                )
    for row in grouped.values():
        for key in (
            "intent_ids", "scout_run_ids", "scout_run_paths", "styles",
            "requested_measurements",
        ):
            row[key] = sorted(set(value for value in row[key] if value))
        values = row.pop("intent_specificities")
        row["request_specificity"] = max(values) if values else 0.0
    return sorted(grouped.values(), key=lambda row: str(row["security_id"]))


def compile_enrichment_cycle(
    *,
    scout_runs: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
    enrolled_security_ids: Iterable[str],
    prior_jobs: Sequence[Mapping[str, Any]] = (),
    enabled_source_count: int,
    completed_at: str | None = None,
) -> dict[str, Any]:
    """Compile one immutable, budget-feasible acquisition batch."""
    if policy.get("schema") != ENRICHMENT_POLICY_SCHEMA:
        raise ValueError(f"enrichment policy schema must be {ENRICHMENT_POLICY_SCHEMA}")
    parsed = _validated_policy(policy)
    completed = canonical_timestamp(completed_at or _utc_now(), "enrichment cycle completed_at")
    current = timestamp_key(completed)
    enrolled = set(str(value) for value in enrolled_security_ids)
    candidates = _candidate_rows(scout_runs)
    max_measurements = max((len(row["requested_measurements"]) for row in candidates), default=1)
    max_log_volume = max(
        (math.log1p(max(0.0, float(row.get("volume") or 0.0))) for row in candidates),
        default=1.0,
    ) or 1.0
    weight_total = sum(parsed["weights"].values())
    scored: list[dict[str, Any]] = []
    for row in candidates:
        kind = str(row.get("entity_kind") or "")
        if kind not in parsed["costs"]:
            continue
        cost = EnrichmentCost(**parsed["costs"][kind])
        measurement = (
            math.log1p(len(row["requested_measurements"])) / math.log1p(max_measurements)
            if max_measurements else 0.0
        )
        liquidity = math.log1p(max(0.0, float(row.get("volume") or 0.0))) / max_log_volume
        source_efficiency = 1.0 / max(1, cost.incremental_source_calls)
        components = {
            "measurement_value_proxy": measurement,
            "request_specificity": float(row["request_specificity"]),
            "identity_coverage": _identity_coverage(row),
            "liquidity": liquidity,
            "source_efficiency": source_efficiency,
        }
        acquisition_proxy = sum(
            parsed["weights"][key] * value for key, value in components.items()
        ) / weight_total
        potential_priority = row.get("investment_potential_priority")
        base_priority = (
            float(potential_priority)
            if potential_priority is not None else acquisition_proxy
        )
        attempts, cooldown_active = _prior_attempts(
            prior_jobs, str(row["security_id"]), current=current,
            cooldown_hours=parsed["retry_cooldown_hours"],
        )
        scored.append({
            **row,
            "cost": cost.to_dict(),
            "score_components": {key: round(value, 8) for key, value in components.items()},
            "base_priority": round(base_priority, 8),
            "base_priority_source": (
                "deterministic_investment_potential"
                if potential_priority is not None else "acquisition_convenience_proxy"
            ),
            "prior_attempts": attempts,
            "retry_cooldown_active": cooldown_active,
            "selection_status": "eligible",
            "selection_reason": "",
        })

    budgets = parsed["budgets"]
    usage = {
        "equities": 0,
        "funds": 0,
        "incremental_source_calls": 0,
        "estimated_research_minutes": 0,
        "baseline_refresh_source_calls": max(0, int(enabled_source_count)),
        "sec_registry_batch_source_calls": 0,
    }
    sector_counts: Counter[str] = Counter()
    selected: list[dict[str, Any]] = []
    pending = sorted(scored, key=lambda row: (-float(row["base_priority"]), str(row["security_id"])))
    while pending:
        for row in pending:
            diversity = _marginal_diversity(row, selected)
            row["marginal_diversity"] = round(diversity, 8)
            row["acquisition_priority"] = round(
                float(row["base_priority"]) + parsed["diversity_weight"] * diversity,
                8,
            )
        pending.sort(key=lambda row: (-float(row["acquisition_priority"]), str(row["security_id"])))
        row = pending.pop(0)
        security_id = str(row["security_id"])
        kind = str(row["entity_kind"])
        cost = row["cost"]
        reason = ""
        if security_id in enrolled:
            reason = "already_enrolled"
        elif (row.get("source_activation") or {}).get("status") == "blocked":
            reason = "source_capability_unavailable"
        elif row["retry_cooldown_active"]:
            reason = "retry_cooldown"
        elif float(row["acquisition_priority"]) < parsed["minimum_priority"]:
            reason = "below_minimum_priority"
        elif kind == "public_equity" and usage["equities"] >= budgets["max_equities"]:
            reason = "equity_budget"
        elif kind == "public_fund" and usage["funds"] >= budgets["max_funds"]:
            reason = "fund_budget"
        sector = str(row.get("sector") or "").strip().lower()
        if (
            not reason and kind == "public_equity" and sector
            and sector_counts[sector] >= budgets["max_equities_per_sector"]
        ):
            reason = "sector_concentration_budget"
        next_incremental = usage["incremental_source_calls"] + int(cost["incremental_source_calls"])
        registry = parsed["registry_calls"] if (
            kind == "public_equity" and usage["sec_registry_batch_source_calls"] == 0
        ) else 0
        next_total = (
            usage["baseline_refresh_source_calls"] + next_incremental
            + usage["sec_registry_batch_source_calls"] + registry
        )
        if not reason and next_incremental > budgets["max_incremental_source_calls"]:
            reason = "incremental_source_call_budget"
        elif not reason and next_total > budgets["max_total_source_calls"]:
            reason = "total_source_call_budget"
        elif (
            not reason
            and usage["estimated_research_minutes"] + int(cost["research_minutes"])
            > budgets["max_estimated_research_minutes"]
        ):
            reason = "research_time_budget"
        if reason:
            row["selection_status"] = "not_selected"
            row["selection_reason"] = reason
            continue
        row["selection_status"] = "selected"
        row["selection_reason"] = "highest_budget_feasible_marginal_priority"
        row["selection_rank"] = len(selected) + 1
        selected.append(row)
        if kind == "public_equity":
            usage["equities"] += 1
            if sector:
                sector_counts[sector] += 1
            if usage["sec_registry_batch_source_calls"] == 0:
                usage["sec_registry_batch_source_calls"] = parsed["registry_calls"]
        else:
            usage["funds"] += 1
        usage["incremental_source_calls"] += int(cost["incremental_source_calls"])
        usage["estimated_research_minutes"] += int(cost["research_minutes"])

    selected_ids = {str(row["security_id"]) for row in selected}
    all_rows = [*selected, *(row for row in scored if str(row["security_id"]) not in selected_ids)]
    all_rows.sort(key=lambda row: (
        row.get("selection_status") != "selected",
        int(row.get("selection_rank") or 10**9),
        -float(row.get("acquisition_priority") or row.get("base_priority") or 0),
        str(row["security_id"]),
    ))
    source_run_ids = sorted({
        str(scout.get("run_id") or "") for scout in scout_runs if scout.get("run_id")
    })
    body: dict[str, Any] = {
        "schema": ENRICHMENT_CYCLE_SCHEMA,
        "completed_at": completed,
        "authority": "public_data_acquisition_and_research_request_only",
        "policy_sha256": stable_sha256(policy),
        "source_scout_run_ids": source_run_ids,
        "candidate_count": len(scored),
        "selected_count": len(selected),
        "selected_security_ids": [str(row["security_id"]) for row in selected],
        "budget_limits": budgets,
        "budget_usage": {
            **usage,
            "estimated_total_source_calls": (
                usage["baseline_refresh_source_calls"]
                + usage["incremental_source_calls"]
                + usage["sec_registry_batch_source_calls"]
            ),
        },
        "score_contract": {
            "kind": (
                "deterministic_potential_then_acquisition_diversity"
                if any(
                    row["base_priority_source"] == "deterministic_investment_potential"
                    for row in scored
                ) else "uncalibrated_acquisition_priority_proxy"
            ),
            "weights": parsed["weights"],
            "diversity_weight": parsed["diversity_weight"],
            "priority_precedence": (
                "potential-scoped scout priority replaces the acquisition convenience proxy; "
                "diversity remains a bounded marginal adjustment"
            ),
            "meaning": (
                "The score prioritizes which public-data acquisition may expose useful evidence. "
                "It is neither expected return nor a calibrated probability of finding an investment."
            ),
            "calibration_status": "awaiting prospective job and paper outcomes",
        },
        "candidates": all_rows,
        "activation_boundary": policy.get("activation_boundary"),
    }
    return {**body, "cycle_sha256": stable_sha256(body)}


def job_payload(cycle: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    if candidate.get("selection_status") != "selected":
        raise ValueError("an enrichment job requires a selected candidate")
    work_id = (
        f"investment-enrichment:{str(cycle['cycle_sha256'])[:16]}:"
        f"{str(candidate['symbol']).lower()}"
    )
    body = {
        "schema": ENRICHMENT_JOB_SCHEMA,
        "work_id": work_id,
        "cycle_sha256": cycle["cycle_sha256"],
        "security_id": candidate["security_id"],
        "symbol": candidate["symbol"],
        "name": candidate["name"],
        "entity_kind": candidate["entity_kind"],
        "selection_rank": candidate["selection_rank"],
        "acquisition_priority": candidate["acquisition_priority"],
        "score_components": candidate["score_components"],
        "marginal_diversity": candidate["marginal_diversity"],
        "cost": candidate["cost"],
        "requested_measurements": candidate["requested_measurements"],
        "scout_run_ids": candidate["scout_run_ids"],
        "scout_run_paths": candidate["scout_run_paths"],
        "stage": "queued",
        "required_capability": "public_market_source_enrichment",
        "expected_exit": "evidence_ready_or_typed_block",
        "capital_authority": False,
    }
    return {**body, "job_sha256": stable_sha256(body)}


def enqueue_cycle_jobs(
    *, db_path: str | Path, events_path: str | Path, cycle: Mapping[str, Any],
    max_attempts: int,
) -> list[dict[str, Any]]:
    selected = [
        row for row in cycle.get("candidates") or ()
        if isinstance(row, Mapping) and row.get("selection_status") == "selected"
    ]
    jobs = [job_payload(cycle, row) for row in selected]
    connection = work_queue.connect(str(db_path))
    try:
        for job in jobs:
            work_queue.enqueue(
                connection, kind=ENRICHMENT_JOB_KIND,
                priority=int(round(float(job["acquisition_priority"]) * 100_000)),
                max_attempts=max_attempts, payload=dict(job),
            )
            work_queue.append_event(str(events_path), {
                "event_type": "investment_enrichment_job_enqueued",
                "payload": {"work_id": job["work_id"], "job_sha256": job["job_sha256"]},
            })
    finally:
        connection.close()
    return jobs


def ensure_qualified_research_job(
    *, db_path: str | Path, events_path: str | Path, request: Mapping[str, Any],
) -> None:
    """Materialize the evidence-ready parent for a direct research activation."""
    work_id = require_text(request.get("job_id"), "qualified research job id")
    if not work_id.startswith(("qualified-research:", "strategy-learning-research:")):
        return
    candidate_leaf = require_text(request.get("candidate_leaf"), "qualified candidate leaf")
    connection = work_queue.connect(str(db_path))
    try:
        matches = [
            row for row in work_queue.list_items(connection, limit=10_000)
            if row.get("work_id") == work_id
        ]
        if matches:
            payload = matches[0].get("payload") or {}
            if payload.get("candidate_leaf") != candidate_leaf:
                raise ValueError("qualified research job and request candidate leaves differ")
            return
        body = {
            "schema": (
                "jaggedthoughts-strategy-learning-research-activation-v1"
                if work_id.startswith("strategy-learning-research:") else
                "jaggedthoughts-qualified-research-activation-v1"
            ),
            "work_id": work_id,
            "request_id": request.get("request_id"),
            "request_sha256": request.get("request_sha256"),
            "candidate_leaf": candidate_leaf,
            "candidate_sha256": request.get("candidate_sha256"),
            "entity_id": request.get("entity_id"),
            "entity_kind": request.get("entity_kind"),
            "research_population": request.get("research_population"),
            "research_rank": request.get("research_rank"),
            "stage": "evidence_ready",
            "result_status": "evidence_ready",
            "completed_at": _utc_now(),
            "capital_authority": False,
        }
        work_queue.enqueue(
            connection, kind="jaggedthoughts_qualified_research_activation",
            priority=research_rank_priority(request),
            max_attempts=1, payload=body,
        )
        work_queue.update_status(
            connection, work_id=work_id, status="done", payload_update=body,
        )
        work_queue.append_event(str(events_path), {
            "event_type": "investment_qualified_research_evidence_ready",
            "payload": {"work_id": work_id, "candidate_leaf": candidate_leaf},
        })
    finally:
        connection.close()


def claim_cycle_jobs(
    *, db_path: str | Path, events_path: str | Path, jobs: Sequence[Mapping[str, Any]],
    worker_id: str, lease_seconds: int,
) -> list[dict[str, Any]]:
    claimed: list[dict[str, Any]] = []
    connection = work_queue.connect(str(db_path))
    try:
        for job in jobs:
            work_id = str(job["work_id"])
            if not work_queue.claim_specific(
                connection, work_id=work_id, worker_id=worker_id,
                lease_s=lease_seconds,
            ):
                continue
            if not work_queue.heartbeat(
                connection, work_id=work_id, worker_id=worker_id,
                lease_s=lease_seconds,
                payload_update={"stage": "enriching", "started_at": _utc_now()},
            ):
                continue
            claimed.append(dict(job))
            work_queue.append_event(str(events_path), {
                "event_type": "investment_enrichment_job_started",
                "payload": {"work_id": work_id, "worker_id": worker_id},
            })
    finally:
        connection.close()
    return claimed


def finish_claimed_job(
    *, db_path: str | Path, events_path: str | Path, job: Mapping[str, Any],
    worker_id: str, result: Mapping[str, Any], lease_seconds: int,
) -> None:
    work_id = str(job["work_id"])
    connection = work_queue.connect(str(db_path))
    try:
        if not work_queue.heartbeat(
            connection, work_id=work_id, worker_id=worker_id,
            lease_s=lease_seconds,
            payload_update={
                "stage": str(result.get("result_status") or "blocked"),
                "finished_at": str(result.get("completed_at") or _utc_now()),
                "result_status": result.get("result_status"),
                "result_sha256": result.get("result_sha256"),
                "result_path": result.get("result_path"),
                "research_request_path": result.get("research_request_path"),
                "research_request_leaf": result.get("research_request_leaf"),
                "candidate_leaf": result.get("candidate_leaf"),
                "candidate_sha256": result.get("candidate_sha256"),
                "error": result.get("error"),
            },
        ):
            raise RuntimeError(f"enrichment lease was lost before completion: {work_id}")
        if not work_queue.finish_specific(
            connection, work_id=work_id, worker_id=worker_id, done=True,
        ):
            raise RuntimeError(f"enrichment job could not be finalized: {work_id}")
        work_queue.append_event(str(events_path), {
            "event_type": "investment_enrichment_job_finished",
            "payload": {
                "work_id": work_id, "worker_id": worker_id,
                "result_status": result.get("result_status"),
                "result_sha256": result.get("result_sha256"),
            },
        })
    finally:
        connection.close()


def recover_completed_job(
    *, db_path: str | Path, events_path: str | Path, job: Mapping[str, Any],
    result: Mapping[str, Any],
) -> None:
    """Advance a previously blocked terminal projection after evidence repair."""
    work_id = require_text(job.get("work_id"), "recovered job work_id")
    connection = work_queue.connect(str(db_path))
    try:
        rows = [row for row in work_queue.list_items(connection, limit=10_000) if row.get("work_id") == work_id]
        if len(rows) != 1 or rows[0].get("status") != "done":
            raise ValueError(f"recovery requires one completed queue item: {work_id}")
        payload = rows[0].get("payload") or {}
        if payload.get("result_status") != "blocked":
            raise ValueError(f"recovery requires a blocked result projection: {work_id}")
        work_queue.update_status(
            connection, work_id=work_id, status="done",
            payload_update={
                "stage": "evidence_ready", "result_status": "evidence_ready",
                "recovered_at": result.get("completed_at"),
                "result_sha256": result.get("result_sha256"),
                "result_path": result.get("result_path"),
                "research_request_path": result.get("research_request_path"),
                "research_request_leaf": result.get("research_request_leaf"),
                "candidate_leaf": result.get("candidate_leaf"),
                "candidate_sha256": result.get("candidate_sha256"),
                "error": None,
            },
        )
        work_queue.append_event(str(events_path), {
            "event_type": "investment_enrichment_job_evidence_repaired",
            "payload": {
                "work_id": work_id, "result_sha256": result.get("result_sha256"),
                "candidate_leaf": result.get("candidate_leaf"),
            },
        })
    finally:
        connection.close()


def _require_research_parent_ready(
    connection: sqlite3.Connection, request: Mapping[str, Any],
) -> dict[str, Any]:
    work_id = require_text(request.get("job_id"), "research request job_id")
    candidate_leaf = require_text(request.get("candidate_leaf"), "research request candidate_leaf")
    rows = [
        row for row in work_queue.list_items(connection, limit=10_000)
        if row.get("work_id") == work_id
    ]
    if len(rows) != 1 or rows[0].get("status") != "done":
        raise ValueError(f"dossier submission requires one completed queue item: {work_id}")
    payload = rows[0].get("payload") or {}
    if payload.get("candidate_leaf") != candidate_leaf:
        raise ValueError("research job and dossier candidate leaves differ")
    stage = str(payload.get("stage") or payload.get("result_status") or "")
    if stage not in {"evidence_ready", "researched"}:
        raise ValueError(f"research job is not evidence-ready: {work_id} ({stage})")
    return dict(payload)


def require_research_parent_ready(
    *, db_path: str | Path, request: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail before durable dossier writes unless the exact parent is ready."""
    connection = work_queue.connect(str(db_path))
    try:
        return _require_research_parent_ready(connection, request)
    finally:
        connection.close()


def mark_job_researched(
    *, db_path: str | Path, events_path: str | Path,
    request: Mapping[str, Any], dossier_path: str, dossier_leaf: str,
    dossier_sha256: str,
) -> None:
    """Project a validated dossier submission onto its completed acquisition job."""
    work_id = require_text(request.get("job_id"), "research request job_id")
    candidate_leaf = require_text(request.get("candidate_leaf"), "research request candidate_leaf")
    connection = work_queue.connect(str(db_path))
    try:
        payload = _require_research_parent_ready(connection, request)
        stage = str(payload.get("stage") or payload.get("result_status") or "")
        if stage == "researched" and payload.get("dossier_sha256") != dossier_sha256:
            raise ValueError("research job already has a different dossier submission")
        if stage not in {"evidence_ready", "researched"}:
            raise ValueError(f"research job is not evidence-ready: {work_id} ({stage})")
        submitted_at = _utc_now()
        dossier_update = {
            "stage": "researched",
            "dossier_submitted_at": submitted_at,
            "dossier_path": require_text(dossier_path, "dossier path"),
            "dossier_leaf": require_text(dossier_leaf, "dossier leaf"),
            "dossier_sha256": require_text(dossier_sha256, "dossier sha256"),
        }
        if stage != "researched":
            work_queue.update_status(
                connection, work_id=work_id, status="done", payload_update=dossier_update,
            )
            work_queue.append_event(str(events_path), {
                "event_type": "investment_research_dossier_submitted",
                "payload": {
                    "work_id": work_id,
                    "request_sha256": request.get("request_sha256"),
                    "candidate_leaf": candidate_leaf,
                    "dossier_leaf": dossier_leaf,
                    "dossier_sha256": dossier_sha256,
                },
            })
        for row in work_queue.list_items(connection, limit=10_000):
            agent_payload = row.get("payload") or {}
            if (
                row.get("kind") == "jaggedthoughts_subscription_research"
                and row.get("status") == "queued"
                and agent_payload.get("request_sha256") == request.get("request_sha256")
            ):
                agent_work_id = str(row["work_id"])
                manual_worker = f"investment-dossier-submit:{os.getpid()}"
                if work_queue.claim_specific(
                    connection, work_id=agent_work_id, worker_id=manual_worker,
                    lease_s=60,
                ):
                    work_queue.heartbeat(
                        connection, work_id=agent_work_id, worker_id=manual_worker,
                        lease_s=60, payload_update={
                            **dossier_update, "completed_at": submitted_at,
                            "provider_called": False, "error": None,
                        },
                    )
                    work_queue.finish_specific(
                        connection, work_id=agent_work_id,
                        worker_id=manual_worker, done=True,
                    )
    finally:
        connection.close()


def research_job_snapshot(db_path: str | Path, *, limit: int = 500) -> dict[str, Any]:
    path = Path(db_path).expanduser().resolve()
    if not path.exists():
        return {
            "schema": "jaggedthoughts-research-job-queue-snapshot-v1",
            "path": str(path), "stats": {"total": 0, "by_status": {}, "by_kind": {}},
            "jobs": [],
        }
    connection = work_queue.connect(str(path))
    try:
        rows = [
            row for row in work_queue.list_items(connection, limit=limit)
            if row.get("kind") == ENRICHMENT_JOB_KIND
        ]
        counts = Counter(str(row.get("status") or "unknown") for row in rows)
    finally:
        connection.close()
    rows.sort(key=lambda row: (-int(row.get("updated_at") or 0), str(row.get("work_id") or "")))
    return {
        "schema": "jaggedthoughts-research-job-queue-snapshot-v1",
        "path": str(path),
        "stats": {
            "total": len(rows), "by_status": dict(sorted(counts.items())),
            "by_kind": {ENRICHMENT_JOB_KIND: len(rows)},
        },
        "jobs": rows,
    }


def compile_research_learning(
    *,
    research_requests: Sequence[Mapping[str, Any]],
    queue_jobs: Sequence[Mapping[str, Any]],
    generated_at: str | None = None,
    minimum_settled_pairs: int = 20,
    minimum_question_policy_units_per_arm: int = 20,
    minimum_useful_question_policy_return: float = 0.01,
) -> dict[str, Any]:
    """Join acquisition scores to downstream research and paper outcomes.

    The result is a selected-cohort learning surface. Pending requests are
    censored rather than labelled as failures, and no acquisition-policy refit
    is authorized until the declared economic-pair gate is met.
    """
    if isinstance(minimum_settled_pairs, bool) or minimum_settled_pairs < 1:
        raise ValueError("minimum_settled_pairs must be a positive integer")
    if (
        isinstance(minimum_question_policy_units_per_arm, bool)
        or minimum_question_policy_units_per_arm < 1
    ):
        raise ValueError(
            "minimum_question_policy_units_per_arm must be a positive integer"
        )
    minimum_useful_return = require_finite(
        minimum_useful_question_policy_return,
        "minimum useful question-policy return",
    )
    if minimum_useful_return < 0:
        raise ValueError("minimum useful question-policy return must be nonnegative")
    generated = canonical_timestamp(
        generated_at or _utc_now(), "research learning generated_at"
    )
    jobs = {
        str(row.get("work_id") or ""): row.get("payload") or {}
        for row in queue_jobs
        if isinstance(row, Mapping) and isinstance(row.get("payload"), Mapping)
    }
    rows: list[dict[str, Any]] = []
    for request in research_requests:
        if not isinstance(request, Mapping):
            continue
        job = jobs.get(str(request.get("job_id") or ""), {})
        stage = str(request.get("lifecycle_stage") or "evidence_ready")
        scorecard = request.get("settlement_scorecard")
        if not isinstance(scorecard, Mapping):
            scorecard = {}
        priority = job.get("acquisition_priority")
        if priority is not None:
            priority = require_finite(priority, "research acquisition priority")
        net_excess = scorecard.get("net_excess_return")
        if net_excess is not None:
            net_excess = require_finite(net_excess, "research settlement net excess return")
        incremental_return = scorecard.get("incremental_return_vs_no_action")
        if incremental_return is not None:
            incremental_return = require_finite(
                incremental_return,
                "research settlement incremental return versus no action",
            )
        cost = job.get("cost") if isinstance(job.get("cost"), Mapping) else {}
        assignment = (
            request.get("research_policy_assignment")
            if isinstance(request.get("research_policy_assignment"), Mapping) else {}
        )
        if incremental_return is not None and assignment.get("outcome_due_at"):
            observed_at = scorecard.get("observed_at")
            if (
                not observed_at
                or timestamp_key(str(observed_at))
                < timestamp_key(str(assignment["outcome_due_at"]))
            ):
                incremental_return = None
        assignment_body = dict(assignment)
        assignment_sha256 = str(assignment_body.pop("assignment_sha256", ""))
        assignment_valid = bool(
            assignment.get("schema") == RESEARCH_POLICY_ASSIGNMENT_SCHEMA
            and assignment.get("experiment_id") == _RESEARCH_POLICY_EXPERIMENT
            and assignment_sha256 == stable_sha256(assignment_body)
        )
        question_frontier = (
            request.get("research_question_frontier")
            if isinstance(request.get("research_question_frontier"), Mapping) else {}
        )
        question_program = (
            question_frontier.get("selected_program")
            if isinstance(question_frontier.get("selected_program"), Mapping) else {}
        )
        dossier_observations = (
            request.get("dossier_observations")
            if isinstance(request.get("dossier_observations"), Mapping) else {}
        )
        dossier_latency_days = None
        if dossier_observations.get("generated_at") and request.get("created_at"):
            dossier_latency_days = (
                timestamp_key(str(dossier_observations["generated_at"]))
                - timestamp_key(str(request["created_at"]))
            ).total_seconds() / 86_400
        rows.append({
            "request_id": request.get("request_id"),
            "job_id": request.get("job_id"),
            "candidate_leaf": request.get("candidate_leaf"),
            "entity_id": request.get("entity_id"),
            "entity_kind": request.get("entity_kind"),
            "research_population": request.get(
                "research_population", "capital_candidate",
            ),
            "created_at": request.get("created_at"),
            "lifecycle_stage": stage,
            "acquisition_priority": priority,
            "acquisition_score_components": dict(job.get("score_components") or {}),
            "estimated_research_minutes": cost.get("research_minutes"),
            "incremental_source_calls": cost.get("incremental_source_calls"),
            "research_policy_experiment": assignment.get("experiment_id"),
            "research_policy_assignment_schema": assignment.get("schema"),
            "research_policy_assignment_valid": assignment_valid,
            "research_policy_eligible": assignment_valid
            and bool(assignment.get("eligible"))
            and request.get("research_population", "capital_candidate")
            == "capital_candidate",
            "research_policy_arm": assignment.get("arm_id"),
            "research_policy_assignment_unit_id": assignment.get(
                "assignment_unit_id"
            ),
            "research_policy_randomization_sha256": assignment.get(
                "randomization_sha256"
            ),
            "research_policy_outcome_due_at": assignment.get("outcome_due_at"),
            "research_routing_mode": assignment.get("routing_mode"),
            "routing_decision_sha256": assignment.get("routing_decision_sha256"),
            "question_frontier_sha256": question_frontier.get("question_frontier_sha256"),
            "question_program_id": question_program.get("program_id"),
            "question_program_atoms": list(question_program.get("atom_ids") or ()),
            "research_question": question_program.get("question") or assignment.get("research_question"),
            "dossier_submitted": bool(request.get("dossier_path")),
            "prior_dossier_coverage_reused": bool(request.get("research_coverage")),
            "research_coverage_leaf": (request.get("research_coverage") or {}).get(
                "coverage_leaf"
            ),
            "dossier_latency_days": dossier_latency_days,
            "dossier_source_count": dossier_observations.get("source_count"),
            "dossier_primary_source_count": dossier_observations.get("primary_source_count"),
            "dossier_falsifier_count": dossier_observations.get("falsifier_count"),
            "question_atom_count": dossier_observations.get("question_atom_count"),
            "question_resolved_atom_count": dossier_observations.get(
                "question_resolved_atom_count"
            ),
            "question_resolution_rate": dossier_observations.get(
                "question_resolution_rate"
            ),
            "question_primary_evidence_rate": dossier_observations.get(
                "question_primary_evidence_rate"
            ),
            "question_rival_signal_count": dossier_observations.get(
                "question_rival_signal_count"
            ),
            "draft_created": stage in {"drafted", "paper_active", "settled", "learned"},
            "paper_activated": stage in {"paper_active", "settled", "learned"},
            "paper_settled": bool(scorecard),
            "decision_id": request.get("decision_id"),
            "paper_target_weight": request.get("paper_target_weight"),
            "net_excess_return": net_excess,
            "incremental_return_vs_no_action": incremental_return,
            "economic_outcome_observed_at": scorecard.get("observed_at"),
            "learning_status": request.get("learning_status"),
        })
    rows.sort(
        key=lambda row: (
            str(row.get("created_at") or ""), str(row.get("request_id") or "")
        )
    )
    request_count = len(rows)
    dossier_count = sum(bool(row["dossier_submitted"]) for row in rows)
    coverage_reuse_count = sum(bool(row["prior_dossier_coverage_reused"]) for row in rows)
    draft_count = sum(bool(row["draft_created"]) for row in rows)
    active_count = sum(bool(row["paper_activated"]) for row in rows)
    settled_rows = [
        row
        for row in rows
        if row["paper_settled"]
        and row.get("acquisition_priority") is not None
        and row.get("net_excess_return") is not None
    ]
    distinct_scores = len({row["acquisition_priority"] for row in settled_rows})
    outcome_signs = {float(row["net_excess_return"]) > 0 for row in settled_rows}
    refit_allowed = (
        len(settled_rows) >= minimum_settled_pairs
        and distinct_scores >= 2
        and len(outcome_signs) >= 2
    )
    if refit_allowed:
        status = "economic_pair_gate_met_review_required"
        next_activation = "review_frozen_cohort_before_policy_refit"
    elif settled_rows:
        status = "descriptive_economic_pairs_below_refit_gate"
        next_activation = "collect_more_request_bound_settlements"
    elif dossier_count:
        status = "research_yield_observed_economic_outcomes_pending"
        next_activation = "advance_qualified_dossiers_to_paper_or_monitor"
    else:
        status = "prospective_requests_pending_research"
        next_activation = "submit_request_bound_dossiers"
    rate = lambda count: (count / request_count if request_count else None)
    policy_units: list[dict[str, Any]] = []
    unit_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        unit_id = row.get("research_policy_assignment_unit_id")
        if row["research_policy_eligible"] and unit_id:
            unit_groups.setdefault(str(unit_id), []).append(row)
    invalid_policy_units = 0
    for unit_id, members in sorted(unit_groups.items()):
        arms = {str(row.get("research_policy_arm") or "") for row in members}
        randomizations = {
            str(row.get("research_policy_randomization_sha256") or "")
            for row in members
        }
        due_values = {
            str(row.get("research_policy_outcome_due_at") or "") for row in members
        }
        if (
            len(arms) != 1 or not arms.issubset(set(_RESEARCH_POLICY_ARMS))
            or len(randomizations) != 1 or "" in randomizations
            or len(due_values) != 1 or "" in due_values
        ):
            invalid_policy_units += 1
            continue
        arm = next(iter(arms))
        dossier_complete = any(row["dossier_submitted"] for row in members)
        question_contract_complete = any(
            row.get("question_atom_count")
            and row.get("question_resolution_rate") is not None
            for row in members
        )
        outcome_due_at = next(iter(due_values))
        outcome_due = timestamp_key(outcome_due_at) <= timestamp_key(generated)
        observed = {
            float(row["incremental_return_vs_no_action"])
            for row in members
            if row.get("incremental_return_vs_no_action") is not None
        }
        activated = any(
            abs(float(row["paper_target_weight"])) > 1e-12
            if row.get("paper_target_weight") is not None
            else bool(row["paper_activated"] or row.get("decision_id"))
            for row in members
        )
        economic_outcome = (
            next(iter(observed)) if outcome_due and len(observed) == 1 else
            0.0 if outcome_due and not observed and not activated else None
        )
        economic_complete = economic_outcome is not None
        policy_units.append({
            "assignment_unit_id": unit_id,
            "entity_kind": members[0]["entity_kind"],
            "arm_id": arm,
            "randomization_sha256": next(iter(randomizations)),
            "request_ids": sorted(str(row["request_id"]) for row in members),
            "issue_count": len(members),
            "dossier_complete": dossier_complete,
            "question_contract_complete": question_contract_complete,
            "outcome_due_at": outcome_due_at,
            "outcome_due": outcome_due,
            "economic_complete": economic_complete,
            "incremental_return_vs_no_action": economic_outcome,
            "economic_outcome_status": (
                "settled_action" if economic_complete and observed else
                "settled_verified_no_action" if economic_complete else
                "due_censored" if outcome_due else "not_due"
            ),
        })
    complete_dossier_units = [row for row in policy_units if row["dossier_complete"]]
    complete_question_contract_units = [
        row for row in policy_units if row["question_contract_complete"]
    ]
    settled_itt_units = [row for row in policy_units if row["economic_complete"]]
    due_itt_units = [row for row in policy_units if row["outcome_due"]]
    censored_due_units = [row for row in due_itt_units if not row["economic_complete"]]
    settled_by_arm = {
        arm: sorted(
            (row for row in settled_itt_units if row["arm_id"] == arm),
            key=lambda row: (row["outcome_due_at"], row["randomization_sha256"]),
        )
        for arm in _RESEARCH_POLICY_ARMS
    }
    review_units_per_arm = (
        min(len(rows) for rows in settled_by_arm.values())
        // minimum_question_policy_units_per_arm
        * minimum_question_policy_units_per_arm
    )
    review_units = {
        arm: settled_by_arm[arm][:review_units_per_arm] for arm in _RESEARCH_POLICY_ARMS
    }
    review_index = (
        review_units_per_arm // minimum_question_policy_units_per_arm - 1
        if review_units_per_arm else None
    )
    look_alpha = 0.05 / 2 ** (review_index + 1) if review_index is not None else 0.05
    randomization_inference = _independent_randomization_inference(
        [row["incremental_return_vs_no_action"] for row in review_units["disagreement_first"]],
        [row["incremental_return_vs_no_action"] for row in review_units["coverage_first"]],
        seed=int(stable_sha256(review_units)[:8], 16),
        confidence_level=1.0 - look_alpha,
    )
    observed_delta = randomization_inference.get("observed_delta")
    ci_lo = randomization_inference.get("ci_lo")
    ci_hi = randomization_inference.get("ci_hi")
    p_value = randomization_inference.get("p_value")
    question_policy_change_allowed = (
        review_units_per_arm >= minimum_question_policy_units_per_arm
        and not censored_due_units
        and p_value is not None and float(p_value) <= look_alpha
        and ci_lo is not None and ci_hi is not None
        and (
            float(ci_lo) > minimum_useful_return
            or float(ci_hi) < -minimum_useful_return
        )
        and observed_delta is not None and float(observed_delta) != 0
    )
    recommended_arm = None
    if question_policy_change_allowed:
        recommended_arm = (
            "disagreement_first" if float(observed_delta) > 0 else "coverage_first"
        )
    routing_body = {
        "schema": RESEARCH_ROUTING_DECISION_SCHEMA,
        "experiment_id": _RESEARCH_POLICY_EXPERIMENT,
        "observed_through": generated,
        "unit_set_sha256": stable_sha256(review_units),
        "status": (
            "randomized_itt_winner" if question_policy_change_allowed
            else "balanced_exploration"
        ),
        "recommended_arm": recommended_arm,
        "routing_change_allowed": question_policy_change_allowed,
        "minimum_settled_units_per_arm": minimum_question_policy_units_per_arm,
        "reviewed_units_per_arm": review_units_per_arm,
        "due_itt_unit_count": len(due_itt_units),
        "censored_due_unit_count": len(censored_due_units),
        "randomization_inference": randomization_inference,
        "minimum_useful_incremental_return": minimum_useful_return,
        "look_alpha": look_alpha,
        "review_index": review_index,
        "audit_share": 0.5,
        "authority": "research_question_routing_only",
        "capital_authority": False,
    }
    routing_decision = {
        **routing_body, "decision_sha256": stable_sha256(routing_body),
    }
    body: dict[str, Any] = {
        "schema": RESEARCH_LEARNING_SCHEMA,
        "generated_at": generated,
        "status": status,
        "selected_cohort": True,
        "counts": {
            "requests": request_count,
            "dossiers": dossier_count,
            "drafts": draft_count,
            "paper_activations": active_count,
            "settled_score_pairs": len(settled_rows),
        },
        "evidence_compounding": {
            "prior_dossier_coverage_reuse_count": coverage_reuse_count,
            "scope": "qualitative_strategy_industry_and_durable_earnings_only",
        },
        "descriptive_rates": {
            "dossier_submission_rate": rate(dossier_count),
            "draft_progression_rate": rate(draft_count),
            "paper_activation_rate": rate(active_count),
            "settled_pair_coverage": rate(len(settled_rows)),
        },
        "calibration_gate": {
            "score_identity": "uncalibrated_acquisition_priority_proxy",
            "research_yield_observation": "request_bound_dossier_submission",
            "economic_outcome": "benchmark_relative_net_excess_return",
            "minimum_settled_pairs": minimum_settled_pairs,
            "observed_settled_pairs": len(settled_rows),
            "requires_score_variation": True,
            "requires_outcome_sign_variation": True,
            "policy_refit_allowed": refit_allowed,
            "boundary": (
                "Pending rows are censored and cannot be counted as failures. "
                "This selected-cohort surface is descriptive until a frozen prospective "
                "cohort supplies enough request-bound paper settlements."
            ),
        },
        "research_question_policy_experiment": {
            "experiment_id": _RESEARCH_POLICY_EXPERIMENT,
            "arms": list(_RESEARCH_POLICY_ARMS),
            "assignment": (
                "pre-outcome candidate-leaf Bernoulli assignment from an experiment-fixed "
                "hash; request order, batch membership, run id, and issue time cannot change it"
            ),
            "estimand": (
                "intent_to_treat_incremental_return_vs_no_action_for_every_due_assignment"
            ),
            "common_output_contract": RESEARCH_DOSSIER_SCHEMA,
            "assigned_counts": dict(sorted(Counter(
                str(row["research_policy_arm"]) for row in rows
                if row["research_policy_eligible"]
            ).items())),
            "valid_assignment_unit_count": len(policy_units),
            "invalid_assignment_unit_count": invalid_policy_units,
            "duplicate_issue_count": sum(
                max(0, int(row["issue_count"]) - 1) for row in policy_units
            ),
            "complete_dossier_unit_count": len(complete_dossier_units),
            "complete_question_contract_unit_count": len(
                complete_question_contract_units
            ),
            "settled_itt_unit_count": len(settled_itt_units),
            "due_itt_unit_count": len(due_itt_units),
            "censored_due_unit_count": len(censored_due_units),
            "short_horizon_contract": {
                "identity": "source_bound_selected_question_atom_resolution",
                "role": "research_routing_surrogate_only",
                "validated_as_economic_surrogate": False,
                "allowed_use": (
                    "Compare evidence coverage, rival discrimination, and latency by arm; "
                    "do not infer investment performance or change capital policy."
                ),
            },
            "minimum_settled_units_per_arm": minimum_question_policy_units_per_arm,
            "minimum_useful_incremental_return": minimum_useful_return,
            "reviewed_units_per_arm": review_units_per_arm,
            "economic_randomization_inference": randomization_inference,
            "question_policy_change_allowed": question_policy_change_allowed,
            "routing_decision": routing_decision,
            "boundary": (
                "Source counts and latency are process observations, not research quality. "
                "Only independently randomized, fully observed due ITT cohorts may change "
                "the question policy; a missing due outcome blocks routing credit."
            ),
            "assignment_units": policy_units,
        },
        "next_activation": next_activation,
        "rows": rows,
    }
    return {**body, "learning_sha256": stable_sha256(body)}


def _research_policy_benchmark_id(
    discovery_run: Mapping[str, Any], candidate_id: str,
) -> str | None:
    rank_input = discovery_run.get("rank_program_input")
    rank_input = rank_input if isinstance(rank_input, Mapping) else {}
    for lane in rank_input.get("lanes") or ():
        if not isinstance(lane, Mapping):
            continue
        if any(
            isinstance(row, Mapping) and row.get("candidate_id") == candidate_id
            for row in lane.get("candidates") or ()
        ):
            benchmark = str(lane.get("benchmark_id") or "").upper()
            return benchmark if benchmark and benchmark != "UNBOUND" else None
    return None


def compile_research_request(
    *, job: Mapping[str, Any], candidate: Mapping[str, Any], candidate_leaf: str,
    discovery_run: Mapping[str, Any], created_at: str | None = None,
    research_basis_sources: Iterable[Mapping[str, Any]] = (),
    routing_decision: Mapping[str, Any] | None = None,
    learning_credit_assignment: Mapping[str, Any] | None = None,
    current_research_learning: Mapping[str, Any] | None = None,
    strategy_frontier: Mapping[str, Any] | None = None,
    strategy_event_trigger: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind one completed acquisition job to the current immutable candidate leaf."""
    created = canonical_timestamp(created_at or _utc_now(), "research request created_at")
    entity_kind = require_text(candidate.get("entity_kind"), "research request entity_kind")
    if entity_kind not in {"public_equity", "public_fund"}:
        raise ValueError("research requests support public equities and funds")
    digest = require_text(candidate_leaf, "research request candidate leaf")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("research request candidate_leaf must be a SHA-256 digest")
    research_population = str(job.get("research_population") or "capital_candidate")
    if research_population not in {"capital_candidate", "strategy_learning"}:
        raise ValueError("research request has an unsupported research population")
    assignment_row = {
        "candidate_leaf": digest,
        "candidate_id": candidate["candidate_id"],
        "entity_kind": entity_kind,
    }
    issue_batch = stable_sha256({
        "source_run_id": discovery_run.get("run_id") or job.get("cycle_sha256"),
        "created_at": created,
    })
    benchmark_id = _research_policy_benchmark_id(
        discovery_run, str(candidate["candidate_id"]),
    )
    if research_population == "capital_candidate" and benchmark_id:
        assign_research_question_policies(
            [assignment_row],
            source_run_ids=(
                str(discovery_run.get("run_id") or job.get("cycle_sha256")),
            ),
            completed_at=created,
            routing_decision=routing_decision,
            learning_credit_assignment=learning_credit_assignment,
            current_research_learning=current_research_learning,
        )
        assignment = assignment_row["research_policy_assignment"]
    elif research_population == "capital_candidate":
        assignment = _research_policy_assignment(
            arm_id="coverage_first", entity_kind=entity_kind,
            assignment_unit_id=digest, issue_batch_sha256=issue_batch,
            randomization_sha256=stable_sha256({
                "experiment_id": _RESEARCH_POLICY_EXPERIMENT,
                "assignment_unit_id": digest,
            }),
            assigned_at=created, economic_outcome_horizon_days=365,
            eligible=False, routing_mode="economic_outcome_benchmark_unbound",
        )
    else:
        assignment = _research_policy_assignment(
            arm_id="coverage_first", entity_kind=entity_kind,
            assignment_unit_id=digest, issue_batch_sha256=issue_batch,
            randomization_sha256=stable_sha256({
                "experiment_id": _RESEARCH_POLICY_EXPERIMENT,
                "assignment_unit_id": digest,
            }),
            assigned_at=created, economic_outcome_horizon_days=365,
            eligible=False, routing_mode="outside_capital_candidate_experiment",
        )
    question_frontier = compile_research_question_frontier(
        candidate, arm_id=str(assignment["arm_id"]),
        strategy_frontier=strategy_frontier,
    )
    research_mode = (
        "company_strategy_industry_durable_earnings_and_valuation"
        if entity_kind == "public_equity"
        else "fund_exposure_fees_holdings_mechanics_and_aggregate_valuation"
    )
    source_snapshot = sorted(({
        "source_id": require_text(row.get("source_id"), "research basis source_id"),
        "content_sha256": row.get("content_sha256"),
        "receipt_sha256": row.get("receipt_sha256"),
        "retrieved_at": row.get("retrieved_at"),
        "canonical_url": row.get("canonical_url"),
    } for row in research_basis_sources), key=lambda row: row["source_id"])
    event_trigger = None
    if strategy_event_trigger:
        trigger = dict(strategy_event_trigger)
        if trigger.get("entity_id") != candidate.get("entity_id"):
            raise ValueError("strategy event trigger and research candidate differ")
        event_trigger = {
            "entity_id": candidate["entity_id"],
            "accession_number": require_text(
                trigger.get("accession_number"), "strategy event accession number",
            ),
            "occurred_at": canonical_timestamp(
                trigger.get("occurred_at"), "strategy event occurred_at",
            ),
            "available_at": canonical_timestamp(
                trigger.get("available_at"), "strategy event available_at",
            ),
            "move_observation_sha256": require_text(
                trigger.get("move_observation_sha256"), "strategy move observation hash",
            ),
            "event_research_request_sha256": require_text(
                trigger.get("research_request_sha256"), "strategy event request hash",
            ),
            "strategy_path_shadow_sha256": require_text(
                trigger.get("strategy_path_shadow_sha256"), "strategy path shadow hash",
            ),
            "phenotype": dict(trigger.get("phenotype") or {}),
            "research_priority_rank": int(trigger.get("research_priority_rank") or 0),
            "operating_model_disagreement": require_finite(
                trigger.get("operating_model_disagreement"),
                "strategy event operating model disagreement",
            ),
            "operating_direction_disagreement": bool(
                trigger.get("operating_direction_disagreement")
            ),
            "return_model_disagreement": require_finite(
                trigger.get("return_model_disagreement"),
                "strategy event return model disagreement",
            ),
            "return_direction_disagreement": bool(
                trigger.get("return_direction_disagreement")
            ),
            "selection_use": "evidence_acquisition_only",
            "capital_authority": False,
        }
        if (
            event_trigger["research_priority_rank"] < 1
            or event_trigger["operating_model_disagreement"] < 0
            or event_trigger["return_model_disagreement"] < 0
        ):
            raise ValueError("strategy event research priority is invalid")
        if any(
            not re.fullmatch(r"[0-9a-f]{64}", str(event_trigger[field]))
            for field in (
                "move_observation_sha256", "event_research_request_sha256",
                "strategy_path_shadow_sha256",
            )
        ):
            raise ValueError("strategy event trigger hashes must be SHA-256 digests")
    selected_program = question_frontier["selected_program"]
    research_basis = {
        "schema": "jaggedthoughts-qualitative-research-basis-v1",
        "candidate_id": candidate["candidate_id"],
        "entity_id": candidate["entity_id"],
        "entity_kind": entity_kind,
        "research_mode": research_mode,
        "question_policy_arm": assignment["arm_id"],
        "question_program_id": selected_program["program_id"],
        "question_atom_ids": sorted(selected_program.get("atom_ids") or ()),
        "material_sources": [
            {"source_id": row["source_id"], "content_sha256": row["content_sha256"]}
            for row in source_snapshot
        ],
    }
    if event_trigger:
        research_basis["strategy_event_trigger"] = event_trigger
    research_basis_sha = stable_sha256(research_basis)
    body: dict[str, Any] = {
        "schema": RESEARCH_REQUEST_SCHEMA,
        "request_id": f"research:{str(candidate['candidate_id'])}:{str(candidate['candidate_sha256'])[:16]}",
        "created_at": created,
        "job_id": job["work_id"],
        "job_sha256": job["job_sha256"],
        "cycle_sha256": job["cycle_sha256"],
        "candidate_leaf": digest,
        "candidate_sha256": candidate["candidate_sha256"],
        "candidate_id": candidate["candidate_id"],
        "entity_id": candidate["entity_id"],
        "entity_kind": entity_kind,
        "as_of": candidate["as_of"],
        "screen_status": candidate["screen_status"],
        "rank": candidate.get("rank"),
        "research_rank": candidate.get("research_rank"),
        "potential_rank": candidate.get("potential_rank"),
        "rank_score": candidate.get("rank_score"),
        "requested_measurements": list(job.get("requested_measurements") or ()),
        "source_refs": list(candidate.get("source_refs") or ()),
        "discovery_run_id": discovery_run["run_id"],
        "discovery_run_sha256": discovery_run["run_sha256"],
        "required_skill": "jaggedthoughts-capital-research",
        "required_output_schema": "jaggedthoughts-candidate-research-dossier-v1",
        "research_mode": research_mode,
        "research_population": research_population,
        "qualitative_research_basis": research_basis,
        "qualitative_research_basis_sha256": research_basis_sha,
        "research_basis_source_snapshot": source_snapshot,
        "research_policy_assignment": assignment,
        "research_question_frontier": question_frontier,
        "strategy_event_trigger": event_trigger,
        "next_activation": candidate.get("next_activation"),
        "capital_authority": False,
        "activation_boundary": (
            "Strategy-learning research may update the business-mechanism library but cannot "
            "create a paper proposal or capital position."
            if research_population == "strategy_learning" else
            "The research agent may write a typed dossier but cannot activate it. Only the "
            "paper activation kernel, under manual or standing operator policy, may admit an "
            "exact current proposal as a zero-weight watch."
        ),
        "learning_contract": {
            "prospective_identity": digest,
            "later_events": [
                "dossier_submitted", "draft_created", "paper_activated", "paper_settled",
            ],
            "selection_score_role": "acquisition routing only",
            "calibration_target": (
                "whether the job produced decision-changing evidence and, only after a paper "
                "decision exists, its settled benchmark-relative consequence"
            ),
            "question_policy_experiment": assignment["experiment_id"],
            "question_policy_arm": assignment["arm_id"],
            "question_policy_assignment_unit_id": assignment["assignment_unit_id"],
            "question_frontier_sha256": question_frontier["question_frontier_sha256"],
            "question_program_id": question_frontier["selected_program"]["program_id"],
            "qualitative_research_basis_sha256": research_basis_sha,
            "research_population": research_population,
        },
    }
    if research_population == "capital_candidate":
        body["research_policy_outcome_contract"] = (
            compile_research_question_policy_outcome_contract(
                assignment=assignment,
                request_basis_sha256=stable_sha256(body),
                candidate_leaf=digest,
                entity_id=str(candidate["entity_id"]),
                benchmark_id=benchmark_id,
            )
        )
    return {**body, "request_sha256": stable_sha256(body)}


def research_rank_priority(request: Mapping[str, Any]) -> int:
    """Prioritize admitted survivors and current strategy-learning questions."""
    try:
        research_rank = int(
            request.get("learned_research_rank") or request.get("research_rank") or 0
        )
    except (TypeError, ValueError):
        research_rank = 0
    if research_rank > 0:
        priority = max(900_000, 1_000_000 - 1_000 * research_rank)
    else:
        try:
            fallback_rank = int(request.get("rank") or 0)
        except (TypeError, ValueError):
            fallback_rank = 0
        priority = max(0, 900_000 - 1_000 * fallback_rank) if fallback_rank > 0 else 0
    frontier = request.get("research_question_frontier")
    strategy = frontier.get("strategy_context") if isinstance(frontier, Mapping) else None
    if (
        isinstance(strategy, Mapping)
        and strategy.get("selection_status") == "selected"
        and strategy.get("gap") in {
            "verify_operational_adoption",
            "sharpen_implementation_interval",
            "freeze_operating_outcome_contract",
        }
    ):
        priority = max(priority, 1_025_000)
    event_trigger = request.get("strategy_event_trigger")
    if isinstance(event_trigger, Mapping):
        try:
            event_rank = int(event_trigger.get("research_priority_rank") or 0)
        except (TypeError, ValueError):
            event_rank = 0
        if event_rank > 0:
            priority = max(priority, 1_050_000 - min(event_rank, 50) * 1_000)
    return priority


def validate_research_dossier(
    dossier: Mapping[str, Any], *, expected_identity: Mapping[str, Any],
    request: Mapping[str, Any] | None = None, accepted_at: str | None = None,
    materialized_at: str | None = None,
    question_program_override: Mapping[str, Any] | None = None,
    question_frontier_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and content-address one candidate-leaf-bound research dossier."""
    body = dict(dossier)
    declared = str(body.pop("dossier_sha256", "") or "")
    source_digest = stable_sha256(body)
    if declared and declared != source_digest:
        raise ValueError("candidate dossier content hash mismatch")
    preserve_signed_source_form = bool(declared) and accepted_at is None
    if body.get("schema") != RESEARCH_DOSSIER_SCHEMA:
        raise ValueError(f"candidate dossier schema must be {RESEARCH_DOSSIER_SCHEMA}")
    expected = {
        "candidate_leaf": expected_identity.get("candidate_leaf"),
        "candidate_sha256": expected_identity.get("candidate_sha256"),
        "entity_id": str(expected_identity.get("entity_id") or "").upper(),
        "as_of": expected_identity.get("as_of"),
    }
    observed = {
        "candidate_leaf": body.get("candidate_leaf"),
        "candidate_sha256": body.get("candidate_sha256"),
        "entity_id": str(body.get("entity_id") or "").upper(),
        "as_of": body.get("as_of"),
    }
    if observed != expected:
        raise ValueError("candidate dossier identity does not match its candidate leaf")
    if request is not None:
        if request.get("schema") != RESEARCH_REQUEST_SCHEMA:
            raise ValueError("candidate dossier targets an unsupported research request")
        request_identity = {
            key: request.get(key) for key in (
                "candidate_leaf", "candidate_sha256", "entity_id", "as_of",
            )
        }
        if request_identity != expected:
            raise ValueError("research request and candidate dossier identities differ")
        body_request = {
            "request_id": body.get("request_id"),
            "request_sha256": body.get("request_sha256"),
        }
        expected_request = {
            "request_id": request.get("request_id"),
            "request_sha256": request.get("request_sha256"),
        }
        if body_request != expected_request:
            raise ValueError("candidate dossier does not bind the selected research request")

    required_sections = (
        "generated_at", "thesis", "rival_view", "decisive_observation",
        "falsifiers", "catalysts", "strategy", "industry",
        "durable_earnings_bridge", "valuation_assumptions", "sources",
    )
    missing = [name for name in required_sections if name not in body]
    if missing:
        raise ValueError(f"candidate dossier is missing required sections: {missing}")
    generated_at = canonical_timestamp(body.get("generated_at"), "candidate dossier generated_at")
    if accepted_at is not None:
        generated_at = canonical_timestamp(accepted_at, "candidate dossier accepted_at")
    materialized = (
        canonical_timestamp(materialized_at, "candidate dossier materialized_at")
        if materialized_at is not None else None
    )
    if timestamp_key(generated_at) < timestamp_key(str(expected["as_of"])):
        raise ValueError("candidate dossier generated_at precedes its candidate evidence epoch")
    if materialized is not None and timestamp_key(generated_at) > timestamp_key(materialized):
        raise ValueError("candidate dossier generated_at follows its materialization time")
    if not preserve_signed_source_form:
        body["generated_at"] = generated_at
    for section in (
        "thesis", "rival_view", "decisive_observation", "strategy",
        "industry", "durable_earnings_bridge", "valuation_assumptions",
    ):
        if not isinstance(body.get(section), Mapping) or not body[section]:
            raise ValueError(f"candidate dossier {section} must be a nonempty object")
    for section in ("falsifiers", "catalysts", "sources"):
        if not isinstance(body.get(section), list):
            raise ValueError(f"candidate dossier {section} must be a list")
    body["sources"] = [dict(source) if isinstance(source, Mapping) else source for source in body["sources"]]
    if not body["falsifiers"] or len(body["sources"]) < 2:
        raise ValueError("candidate dossier requires at least one falsifier and two sources")
    thesis = body["thesis"]
    require_text(thesis.get("claim"), "candidate dossier thesis.claim")
    require_text(thesis.get("mechanism"), "candidate dossier thesis.mechanism")
    confidence = require_finite(thesis.get("confidence"), "candidate dossier thesis.confidence")
    if not 0 <= confidence <= 1:
        raise ValueError("candidate dossier thesis.confidence must be between zero and one")
    source_ids: set[str] = set()
    primary_source_count = 0
    source_kinds = {"filing", "issuer", "regulator", "government", "research"}
    for index, source in enumerate(body["sources"]):
        if not isinstance(source, Mapping):
            raise ValueError(f"candidate dossier sources[{index}] must be an object")
        source_id = require_text(source.get("id"), f"candidate dossier sources[{index}].id")
        if source_id in source_ids:
            raise ValueError(f"candidate dossier source id is duplicated: {source_id}")
        source_ids.add(source_id)
        for field in ("title", "url", "publisher", "accessed_at", "source_kind"):
            require_text(source.get(field), f"candidate dossier sources[{index}].{field}")
        if source.get("source_kind") not in source_kinds:
            raise ValueError(f"candidate dossier sources[{index}].source_kind is unsupported")
        if source.get("source_kind") in {"filing", "issuer", "regulator", "government"}:
            primary_source_count += 1
        if not str(source["url"]).startswith("https://"):
            raise ValueError(f"candidate dossier sources[{index}].url must use https")
        publication_label = f"candidate dossier sources[{index}].published_at"
        try:
            published_at, publication_interval_start = _canonical_publication_time(
                source.get("published_at"), label=publication_label, source=source,
            )
        except ResearchEvidenceTimestampError as error:
            error.dossier_body_sha256 = source_digest
            raise
        accessed_at = (
            generated_at if accepted_at is not None else canonical_timestamp(
                source.get("accessed_at"),
                f"candidate dossier sources[{index}].accessed_at",
            )
        )
        if not preserve_signed_source_form:
            source["published_at"] = published_at
            source["accessed_at"] = accessed_at
        if timestamp_key(publication_interval_start) > timestamp_key(accessed_at):
            raise ValueError("candidate dossier source was accessed before publication")
        if materialized is not None and timestamp_key(accessed_at) > timestamp_key(materialized):
            raise ValueError("candidate dossier source access follows dossier materialization")
        supports = source.get("supports")
        if not isinstance(supports, list) or not supports:
            raise ValueError(f"candidate dossier sources[{index}].supports must be a nonempty list")
    if primary_source_count < 1:
        raise ValueError("candidate dossier requires at least one primary source")
    event_trigger = (
        request.get("strategy_event_trigger")
        if request is not None and isinstance(request.get("strategy_event_trigger"), Mapping)
        else None
    )
    event_assessment = body.get("strategy_event_assessment")
    if event_trigger is None and event_assessment is not None:
        raise ValueError("candidate dossier has an unassigned strategy event assessment")
    if event_trigger is not None:
        if not isinstance(event_assessment, Mapping):
            raise ValueError("candidate dossier must assess its frozen strategy event")
        expected_event = {
            "move_observation_sha256": event_trigger.get("move_observation_sha256"),
            "event_research_request_sha256": event_trigger.get(
                "event_research_request_sha256"
            ),
        }
        if {
            key: event_assessment.get(key) for key in expected_event
        } != expected_event:
            raise ValueError("candidate dossier crossed its strategy event identity")
        if event_assessment.get("status") not in {
            "supports_thesis", "supports_rival", "mixed", "unresolved",
        }:
            raise ValueError("candidate dossier strategy event status is unsupported")
        for field in (
            "finding", "durable_earnings_implication", "valuation_implication",
        ):
            require_text(
                event_assessment.get(field), f"candidate dossier strategy event {field}",
            )
        event_refs = list(map(str, event_assessment.get("evidence_refs") or ()))
        if not event_refs or not set(event_refs) <= source_ids:
            raise ValueError("candidate dossier strategy event has invalid evidence refs")
        event_token = f"strategy_event:{event_trigger['move_observation_sha256']}"
        sources_by_id = {
            str(row["id"]): row for row in body["sources"] if isinstance(row, Mapping)
        }
        if any(
            event_token not in set(map(str, sources_by_id[ref].get("supports") or ()))
            for ref in event_refs
        ):
            raise ValueError("candidate dossier strategy event lacks exact source support")
    question_frontier = (
        request.get("research_question_frontier")
        if request is not None and isinstance(request.get("research_question_frontier"), Mapping)
        else {}
    )
    if question_frontier_override is not None:
        override_frontier = dict(question_frontier_override)
        declared_frontier = str(
            override_frontier.pop("question_frontier_sha256", "") or ""
        )
        if (
            override_frontier.get("schema") != RESEARCH_QUESTION_FRONTIER_SCHEMA
            or stable_sha256(override_frontier) != declared_frontier
            or override_frontier.get("entity_id") != expected["entity_id"]
            or override_frontier.get("candidate_sha256")
            != expected["candidate_sha256"]
        ):
            raise ValueError("research question frontier override crossed candidate identity")
        question_frontier = {
            **override_frontier,
            "question_frontier_sha256": declared_frontier,
        }
    selected_program = (
        question_frontier.get("selected_program")
        if isinstance(question_frontier.get("selected_program"), Mapping) else {}
    )
    if question_program_override is not None:
        override = dict(question_program_override)
        allowed_programs = [selected_program] + [
            row for row in question_frontier.get("frontier_programs") or ()
            if isinstance(row, Mapping)
        ]
        if not any(
            row.get("program_id") == override.get("program_id")
            and list(row.get("atom_ids") or ()) == list(override.get("atom_ids") or ())
            for row in allowed_programs
        ):
            raise ValueError("research question override is outside the frozen frontier")
        selected_program = override
    selected_atoms = [str(value) for value in selected_program.get("atom_ids") or ()]
    outcomes = body.get("research_question_outcomes")
    if selected_atoms:
        if not isinstance(outcomes, list):
            raise ValueError("candidate dossier requires research question outcomes")
        by_atom: dict[str, Mapping[str, Any]] = {}
        for index, outcome in enumerate(outcomes):
            if not isinstance(outcome, Mapping):
                raise ValueError(
                    f"candidate dossier research_question_outcomes[{index}] must be an object"
                )
            atom_id = require_text(
                outcome.get("atom_id"),
                f"candidate dossier research_question_outcomes[{index}].atom_id",
            )
            if atom_id in by_atom:
                raise ValueError(f"candidate dossier research question atom is duplicated: {atom_id}")
            if outcome.get("status") not in {
                "supports_thesis", "supports_rival", "mixed", "unresolved",
            }:
                raise ValueError("candidate dossier research question outcome status is unsupported")
            require_text(
                outcome.get("finding"),
                f"candidate dossier research_question_outcomes[{index}].finding",
            )
            refs = outcome.get("evidence_refs")
            if not isinstance(refs, list) or not refs:
                raise ValueError("candidate dossier research question outcome requires evidence refs")
            unknown_refs = sorted(set(str(value) for value in refs) - source_ids)
            if unknown_refs:
                raise ValueError(
                    "candidate dossier research question outcome has unknown evidence refs: "
                    f"{unknown_refs}"
                )
            for ref in refs:
                source = next(row for row in body["sources"] if row["id"] == ref)
                if atom_id not in {str(value) for value in source.get("supports") or ()}:
                    raise ValueError(
                        f"candidate dossier source {ref} does not bind research atom {atom_id}"
                    )
            contract = outcome.get("outcome_contract_candidate")
            if contract is not None:
                if not atom_id.startswith("strategy_option_evidence:"):
                    raise ValueError(
                        "an outcome contract candidate requires a strategy-option research atom"
                    )
                if not isinstance(contract, Mapping):
                    raise ValueError("outcome contract candidate must be an object")
                for field in (
                    "metric_id", "unit", "direction", "measurement_start_at",
                    "comparator", "outcome_role", "acquisition_mode",
                    "minimum_effect_basis", "minimum_effect_rationale",
                ):
                    require_text(contract.get(field), f"outcome contract candidate {field}")
                if contract.get("direction") not in {"increase", "decrease"}:
                    raise ValueError("outcome contract candidate direction is unsupported")
                if contract.get("comparator") not in {
                    "pre_move_baseline", "matched_peer", "industry_baseline",
                }:
                    raise ValueError("outcome contract candidate comparator is unsupported")
                if contract.get("outcome_role") not in {
                    "leading_operating", "terminal_operating",
                }:
                    raise ValueError("outcome contract candidate role is unsupported")
                if contract.get("acquisition_mode") not in {
                    "point_in_time_observation", "subscription_primary_document",
                }:
                    raise ValueError("outcome contract candidate acquisition mode is unsupported")
                horizon = int(contract.get("horizon_days") or 0)
                minimum_effect = require_finite(
                    contract.get("minimum_effect"), "outcome contract candidate minimum_effect",
                )
                if not 30 <= horizon <= 3650 or minimum_effect < 0:
                    raise ValueError("outcome contract candidate horizon or effect is invalid")
                measurement_start = canonical_timestamp(
                    contract.get("measurement_start_at"),
                    "outcome contract candidate measurement_start_at",
                )
                if (
                    timestamp_key(measurement_start) > timestamp_key(generated_at)
                    or timestamp_key(measurement_start) + timedelta(days=horizon)
                    <= timestamp_key(generated_at)
                ):
                    raise ValueError(
                        "outcome contract candidate must start by the dossier epoch and mature later"
                    )
                basis = str(contract.get("minimum_effect_basis"))
                if basis not in {"directional_zero", "analyst_forecast", "source_disclosed"}:
                    raise ValueError("outcome contract candidate threshold basis is unsupported")
                if basis == "directional_zero" and minimum_effect != 0:
                    raise ValueError("directional-zero outcome contracts require zero effect")
                contract_refs = contract.get("source_refs")
                if not isinstance(contract_refs, list) or not contract_refs:
                    raise ValueError("outcome contract candidate requires source refs")
                if not set(map(str, contract_refs)).issubset(set(map(str, refs))):
                    raise ValueError(
                        "outcome contract candidate sources must bind its research outcome"
                    )
            by_atom[atom_id] = outcome
        if set(by_atom) != set(selected_atoms):
            raise ValueError("candidate dossier research question outcomes do not match selected atoms")
    strategy = body["strategy"]
    if len(strategy.get("choices") or ()) > 8:
        raise ValueError("candidate dossier strategy grammar permits at most eight choices")
    choice_ids: set[str] = set()
    for section in ("choices", "reinforcing_edges"):
        rows = strategy.get(section)
        if not isinstance(rows, list):
            raise ValueError(f"candidate dossier strategy.{section} must be a list")
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                raise ValueError(f"candidate dossier strategy.{section}[{index}] must be an object")
            if section == "choices":
                choice_id = require_text(
                    row.get("id"), f"candidate dossier strategy.choices[{index}].id",
                )
                require_text(
                    row.get("description"),
                    f"candidate dossier strategy.choices[{index}].description",
                )
                if choice_id in choice_ids:
                    raise ValueError(f"candidate dossier strategy choice id is duplicated: {choice_id}")
                choice_ids.add(choice_id)
            refs = row.get("evidence_refs")
            if not isinstance(refs, list) or not refs:
                raise ValueError(
                    f"candidate dossier strategy.{section}[{index}].evidence_refs must be nonempty"
                )
            unknown_refs = sorted(set(str(value) for value in refs) - source_ids)
            if unknown_refs:
                raise ValueError(
                    f"candidate dossier strategy.{section}[{index}] has unknown evidence refs: {unknown_refs}"
                )
            if section == "reinforcing_edges":
                endpoints = {str(row.get("from") or ""), str(row.get("to") or "")}
                if not endpoints <= choice_ids:
                    raise ValueError(
                        "candidate dossier reinforcing edges must use exact strategy choice ids"
                    )
    constraints = strategy.get("feasibility_constraints")
    if constraints is not None:
        if not isinstance(constraints, Mapping):
            raise ValueError("candidate dossier feasibility_constraints must be an object")
        constraint_ids: set[str] = set()
        sources_by_id = {
            str(row.get("id")): row for row in body.get("sources") or ()
            if isinstance(row, Mapping)
        }
        for kind in ("incompatibilities", "prerequisites", "resources"):
            rows = constraints.get(kind)
            if not isinstance(rows, list):
                raise ValueError(f"candidate dossier feasibility_constraints.{kind} must be a list")
            for index, row in enumerate(rows):
                if not isinstance(row, Mapping):
                    raise ValueError(f"candidate dossier {kind}[{index}] must be an object")
                constraint_id = require_text(row.get("constraint_id"), f"{kind} constraint_id")
                if constraint_id in constraint_ids:
                    raise ValueError(f"candidate dossier constraint id is duplicated: {constraint_id}")
                constraint_ids.add(constraint_id)
                refs = row.get("evidence_refs")
                if not isinstance(refs, list) or not refs or not set(map(str, refs)) <= source_ids:
                    raise ValueError(f"candidate dossier {constraint_id} has invalid evidence refs")
                token = f"strategy_constraint:{constraint_id}"
                if any(token not in set(map(str, sources_by_id[str(ref)].get("supports") or ())) for ref in refs):
                    raise ValueError(f"candidate dossier {constraint_id} lacks exact source support")
                if kind == "incompatibilities":
                    option_ids = list(map(str, row.get("option_ids") or ()))
                    if len(option_ids) != 2 or len(set(option_ids)) != 2 or not set(option_ids) <= choice_ids:
                        raise ValueError(f"candidate dossier {constraint_id} has invalid option ids")
                elif kind == "prerequisites":
                    option_id = str(row.get("option_id") or "")
                    required = list(map(str, row.get("requires") or ()))
                    if option_id not in choice_ids or not required or option_id in required or not set(required) <= choice_ids:
                        raise ValueError(f"candidate dossier {constraint_id} has invalid prerequisites")
                else:
                    uses = row.get("uses")
                    require_text(row.get("resource_id"), f"{constraint_id} resource_id")
                    require_text(row.get("unit"), f"{constraint_id} unit")
                    limit = require_finite(row.get("limit"), f"{constraint_id} limit")
                    if (
                        limit < 0 or not isinstance(uses, list) or not uses
                    ):
                        raise ValueError(f"candidate dossier {constraint_id} has invalid resource bound")
                    use_ids = [str(use.get("option_id") or "") for use in uses if isinstance(use, Mapping)]
                    if len(use_ids) != len(uses) or len(use_ids) != len(set(use_ids)) or not set(use_ids) <= choice_ids:
                        raise ValueError(f"candidate dossier {constraint_id} has invalid resource uses")
                    if any(
                        require_finite(use.get("amount"), f"{constraint_id} resource amount") < 0
                        for use in uses
                    ):
                        raise ValueError(f"candidate dossier {constraint_id} has invalid resource amount")
    challenge = strategy.get("constraint_challenge_examples")
    if challenge is not None:
        if not isinstance(challenge, Mapping):
            raise ValueError("candidate dossier constraint_challenge_examples must be an object")
        for key in ("admitted_bundles", "excluded_bundles", "implication_pairs"):
            if not isinstance(challenge.get(key), list):
                raise ValueError(f"candidate dossier constraint_challenge_examples.{key} must be a list")
        if (
            challenge.get("excluded_bundles") or challenge.get("implication_pairs")
        ) and not challenge.get("admitted_bundles"):
            raise ValueError("constraint challenge examples require an admitted bundle")
        sources_by_id = {
            str(row.get("id")): row for row in body.get("sources") or ()
            if isinstance(row, Mapping)
        }
        seen_example_ids: set[str] = set()
        bundle_dispositions: dict[tuple[str, ...], str] = {}
        for kind in ("admitted_bundles", "excluded_bundles", "implication_pairs"):
            for index, row in enumerate(challenge[kind]):
                if not isinstance(row, Mapping):
                    raise ValueError(f"candidate dossier {kind}[{index}] must be an object")
                example_id = require_text(row.get("example_id"), f"{kind} example_id")
                if example_id in seen_example_ids:
                    raise ValueError(f"constraint challenge example id is duplicated: {example_id}")
                seen_example_ids.add(example_id)
                option_fields = (
                    ("antecedent_option_ids", "required_option_ids")
                    if kind == "implication_pairs" else ("option_ids",)
                )
                normalized_fields = []
                for field in option_fields:
                    values = list(map(str, row.get(field) or ()))
                    if (
                        not values or len(values) != len(set(values))
                        or not set(values) <= choice_ids
                    ):
                        raise ValueError(f"constraint challenge {example_id} has invalid {field}")
                    normalized_fields.append(set(values))
                if kind == "implication_pairs" and normalized_fields[0] & normalized_fields[1]:
                    raise ValueError(f"constraint challenge {example_id} overlaps implication sides")
                if kind != "implication_pairs":
                    bundle = tuple(sorted(normalized_fields[0]))
                    disposition = "admitted" if kind == "admitted_bundles" else "excluded"
                    prior = bundle_dispositions.get(bundle)
                    if prior and prior != disposition:
                        raise ValueError("a constraint challenge bundle has conflicting dispositions")
                    bundle_dispositions[bundle] = disposition
                refs = list(map(str, row.get("evidence_refs") or ()))
                if not refs or not set(refs) <= source_ids:
                    raise ValueError(f"constraint challenge {example_id} has invalid evidence refs")
                token = f"strategy_constraint_example:{example_id}"
                if any(
                    token not in set(map(str, sources_by_id[ref].get("supports") or ()))
                    or sources_by_id[ref].get("source_kind")
                    not in {"filing", "issuer", "regulator", "government"}
                    for ref in refs
                ):
                    raise ValueError(
                        f"constraint challenge {example_id} lacks exact primary-source support"
                    )
    digest = source_digest if preserve_signed_source_form else stable_sha256(body)
    return {**body, "dossier_sha256": digest}


def materialize_cycle(
    workspace: str | Path, cycle: Mapping[str, Any], jobs: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    root = Path(workspace).expanduser().resolve()
    stamp = timestamp_key(str(cycle["completed_at"])).strftime("%Y%m%d%H%M%S")
    path = root / "research_jobs" / "enrichment" / "runs" / (
        f"enrichment-cycle-{stamp}-{str(cycle['cycle_sha256'])[:8]}.json"
    )
    payload = {**dict(cycle), "jobs": [dict(row) for row in jobs]}
    _atomic_json(path, payload)
    _atomic_json(root / "research_jobs" / "enrichment" / "latest.json", payload)
    return {
        "cycle_path": path.relative_to(root).as_posix(),
        "latest_path": "research_jobs/enrichment/latest.json",
    }


def materialize_job_result(
    workspace: str | Path, *, job: Mapping[str, Any], result: Mapping[str, Any],
    research_request: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    safe_id = re.sub(r"[^a-z0-9_-]+", "-", str(job["work_id"]).lower()).strip("-")
    request_path = ""
    if research_request is not None:
        request_path_obj = root / "research_jobs" / "requests" / (
            f"{str(research_request['entity_id']).lower()}-"
            f"{str(research_request['candidate_sha256'])[:12]}-"
            f"{str(research_request['request_sha256'])[:12]}.json"
        )
        _atomic_json(request_path_obj, research_request)
        request_path = request_path_obj.relative_to(root).as_posix()
    body = {
        "schema": "jaggedthoughts-enrichment-job-result-v1",
        "work_id": job["work_id"],
        "job_sha256": job["job_sha256"],
        "cycle_sha256": job.get("cycle_sha256"),
        "security_id": job.get("security_id"),
        "symbol": job.get("symbol"),
        "entity_kind": job.get("entity_kind"),
        "completed_at": result.get("completed_at") or _utc_now(),
        "result_status": result.get("result_status") or "blocked",
        "candidate_leaf": result.get("candidate_leaf"),
        "candidate_sha256": result.get("candidate_sha256"),
        "discovery_run_id": result.get("discovery_run_id"),
        "source_run_sha256": result.get("source_run_sha256"),
        "research_request_path": request_path or None,
        "research_request_leaf": result.get("research_request_leaf"),
        "error": result.get("error"),
        "capital_authority": False,
    }
    payload = {**body, "result_sha256": stable_sha256(body)}
    result_path = root / "research_jobs" / "enrichment" / "results" / (
        f"{safe_id}-{str(payload['result_sha256'])[:12]}.json"
    )
    _atomic_json(result_path, payload)
    return {
        **payload,
        "result_path": result_path.relative_to(root).as_posix(),
        "research_request_path": request_path or None,
    }


__all__ = [
    "ENRICHMENT_CYCLE_SCHEMA", "ENRICHMENT_JOB_KIND", "ENRICHMENT_JOB_SCHEMA",
    "ENRICHMENT_POLICY_SCHEMA", "RESEARCH_DOSSIER_SCHEMA", "RESEARCH_JOB_LIFECYCLE", "RESEARCH_REQUEST_SCHEMA",
    "ResearchEvidenceTimestampError",
    "assign_research_question_policies", "claim_cycle_jobs", "compile_enrichment_cycle", "compile_research_request",
    "default_enrichment_policy", "enqueue_cycle_jobs", "ensure_qualified_research_job", "finish_claimed_job",
    "latest_discovery_candidate_index", "mark_job_researched", "recover_completed_job",
    "require_research_parent_ready",
    "job_payload", "load_enrichment_policy", "materialize_cycle",
    "materialize_job_result", "research_job_snapshot", "research_rank_priority",
    "validated_research_request_basis_sha256",
    "research_request_currency",
    "validated_discovery_research_handoff",
    "validate_research_dossier",
]
