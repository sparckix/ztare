"""Cohort learning over valuation-grammar state-price residuals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_text
from .state_price_residuals import STATE_PRICE_RESIDUAL_SET_SCHEMA
from .valuation import valuation_grammar_contract


VALUATION_GRAMMAR_CONJECTURE_SCHEMA = "jaggedthoughts-valuation-grammar-revision-conjecture-v1"
VALUATION_GRAMMAR_LEARNING_SCHEMA = "jaggedthoughts-valuation-grammar-residual-learning-v1"

_REVISIONS = {
    "missing_state": {
        "revision_kind": "add_state_axis",
        "conjecture": (
            "A source-bound business-state axis may distinguish payoff mechanisms that the "
            "forecast-growth × terminal-growth grid collapses."
        ),
        "operators": ["project_owner_earnings", "present_value", "implied_growth", "implied_return"],
        "terminals": ["ForecastGrowth", "TerminalGrowth", "Horizon"],
        "proposed_surface": "typed BusinessState terminal bound to scenario-specific payoff mechanisms",
    },
    "overly_narrow_payoff_support": {
        "revision_kind": "widen_growth_or_payoff_support",
        "conjecture": (
            "The declared growth coordinates or payoff carrier may omit source-supported boundary cases."
        ),
        "operators": ["project_owner_earnings", "present_value", "implied_growth", "implied_return"],
        "terminals": ["ForecastGrowth", "TerminalGrowth"],
        "proposed_surface": "source-bound boundary terminals outside the current coordinate support",
    },
    "numeraire_mismatch": {
        "revision_kind": "change_numeraire_contract",
        "conjecture": (
            "The discount carrier may use a maturity, payoff unit, or compounding convention "
            "incompatible with the modeled equity horizon."
        ),
        "operators": ["cost_of_equity", "present_value"],
        "terminals": ["RiskFreeRate", "Horizon"],
        "proposed_surface": "explicit numeraire maturity, unit, payoff, and compounding contract",
    },
    "model_misspecification": {
        "revision_kind": "revise_terminal_payoff_mechanism",
        "conjecture": (
            "A perpetuity terminal carrier may omit a source-supported horizon payoff mechanism."
        ),
        "operators": ["present_value", "implied_growth", "implied_return"],
        "terminals": ["OwnerEarnings", "ForecastGrowth", "TerminalGrowth", "ExcessNetCash"],
        "proposed_surface": "versioned terminal mechanism operator with typed assumptions and payoff units",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _verified_set(raw: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(raw)
    if row.get("schema") != STATE_PRICE_RESIDUAL_SET_SCHEMA:
        raise ValueError(f"residual set requires {STATE_PRICE_RESIDUAL_SET_SCHEMA}")
    claimed = require_text(row.get("residual_set_sha256"), "residual_set_sha256")
    if claimed != stable_sha256({key: value for key, value in row.items() if key != "residual_set_sha256"}):
        raise ValueError("residual set digest does not match its payload")
    if row.get("capital_authority") is not False:
        raise ValueError("residual sets must deny capital authority")
    return row


def compile_valuation_grammar_residual_learning(
    residual_sets: Iterable[Mapping[str, Any]], *, compiled_at: str | None = None,
) -> dict[str, Any]:
    """Aggregate a frozen cohort into non-executable grammar conjectures."""

    at = canonical_timestamp(compiled_at or _now(), "compiled_at")
    rows = [_verified_set(raw) for raw in residual_sets]
    identities = [
        (str(row["entity_id"]), str(row["candidate_sha256"]), str(row["residual_set_sha256"]))
        for row in rows
    ]
    if len(identities) != len(set(identities)):
        raise ValueError("valuation grammar cohort contains duplicate residual-set identities")
    rows.sort(key=lambda row: (str(row["entity_id"]), str(row["candidate_sha256"])))
    grammar = valuation_grammar_contract()
    selection_sha256s = [str(row["residual_set_sha256"]) for row in rows]
    cohort_sha = stable_sha256(selection_sha256s)
    conjectures = []
    for residual_kind, revision in _REVISIONS.items():
        supporting = [
            row for row in rows
            if residual_kind in {
                str(request.get("residual_kind") or "") for request in row.get("requests") or ()
                if isinstance(request, Mapping)
            }
        ]
        if not supporting:
            continue
        counterexamples = [row for row in rows if row not in supporting]
        trigger_counts: dict[str, int] = {}
        for row in supporting:
            trigger = str(row.get("trigger") or "none")
            trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
        conjecture_identity = {
            "selection_cohort_sha256": cohort_sha,
            "valuation_grammar_contract_sha256": grammar["contract_sha256"],
            "residual_kind": residual_kind,
            "revision_kind": revision["revision_kind"],
        }
        conjecture_id = f"valuation-grammar:{revision['revision_kind']}:{stable_sha256(conjecture_identity)[:16]}"
        evaluation = {
            "mode": "paired_future_only_shadow",
            "not_before": at,
            "selection_residual_set_sha256s": selection_sha256s,
            "eligible_candidate_rule": (
                "candidate evidence epoch must be strictly later than not_before and absent from "
                "selection_residual_set_sha256s"
            ),
            "comparison": "frozen current grammar versus one explicitly versioned proposed grammar",
            "shared_inputs": [
                "candidate identity and evidence epoch", "spot observation", "payoff-state scope",
                "numeraire contract", "near-zero threshold",
            ],
            "minimum_future_candidates": max(4, len(supporting)),
            "success_condition": (
                f"the proposed grammar reduces `{residual_kind}` on the future cohort without "
                "creating additional infeasible-positive-state-price residuals"
            ),
            "counterexample_rule": (
                "retain every future candidate where the proposed grammar preserves or introduces "
                "the target residual"
            ),
            "historical_retrofit_allowed": False,
            "automatic_grammar_activation": False,
        }
        body = {
            "schema": VALUATION_GRAMMAR_CONJECTURE_SCHEMA,
            "conjecture_id": conjecture_id,
            "compiled_at": at,
            "status": "conjecture_awaiting_future_cohort",
            "residual_kind": residual_kind,
            "revision_kind": revision["revision_kind"],
            "conjecture": revision["conjecture"],
            "proposed_surface": revision["proposed_surface"],
            "valuation_grammar_contract_sha256": grammar["contract_sha256"],
            "affected_ast_operators": revision["operators"],
            "affected_ast_terminals": revision["terminals"],
            "support_count": len(supporting),
            "support_entity_count": len({str(row["entity_id"]) for row in supporting}),
            "support_semantics": (
                "routing support for a rival revision test; not evidence that the revision is correct"
            ),
            "supporting_candidates": [
                {
                    "entity_id": row["entity_id"],
                    "candidate_sha256": row["candidate_sha256"],
                    "residual_set_sha256": row["residual_set_sha256"],
                    "trigger": row.get("trigger"),
                }
                for row in supporting
            ],
            "support_by_trigger": dict(sorted(trigger_counts.items())),
            "counterexample_count": len(counterexamples),
            "counterexample_semantics": (
                "selection-cohort candidate where this residual request was absent; empirical "
                "counterexamples arise only under the future evaluation contract"
            ),
            "counterexamples": [
                {
                    "entity_id": row["entity_id"],
                    "candidate_sha256": row["candidate_sha256"],
                    "residual_set_sha256": row["residual_set_sha256"],
                    "reason": "target_residual_absent_under_current_grammar",
                }
                for row in counterexamples
            ],
            "future_evaluation_contract": evaluation,
            "auto_modifies_grammar": False,
            "security_ranking_use": False,
            "alpha_claim": False,
            "arbitrage_claim": False,
            "capital_authority": False,
        }
        conjectures.append({**body, "conjecture_sha256": stable_sha256(body)})
    body = {
        "schema": VALUATION_GRAMMAR_LEARNING_SCHEMA,
        "compiled_at": at,
        "selection_cohort_sha256": cohort_sha,
        "selection_cohort_count": len(rows),
        "selection_residual_set_sha256s": selection_sha256s,
        "valuation_grammar_contract_sha256": grammar["contract_sha256"],
        "conjecture_count": len(conjectures),
        "conjectures": conjectures,
        "status": "conjectures_awaiting_future_cohorts" if conjectures else "no_residual_support",
        "auto_modifies_grammar": False,
        "security_ranking_use": False,
        "alpha_claim": False,
        "arbitrage_claim": False,
        "capital_authority": False,
    }
    return {**body, "learning_sha256": stable_sha256(body)}


__all__ = [
    "VALUATION_GRAMMAR_CONJECTURE_SCHEMA",
    "VALUATION_GRAMMAR_LEARNING_SCHEMA",
    "compile_valuation_grammar_residual_learning",
]
