"""Batch CEGIS over irreducible compound implications.

One solver witness is evaluated against the whole surviving implication pool.
The solver chooses a countermodel; the host only chooses which implication to
ask next and measures the witness's realized elimination yield.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from ztare.common.information_yield_pricing import price_experiment
from ztare.leanmill.finite_model import FiniteModel, evaluate_axiom, validate_model
from ztare.leanmill.finite_table_model_finder import (
    FiniteModelSearchReceipt,
    find_finite_countermodel,
)
from ztare.leanmill.theory_conflict_ledger import theory_implication_signature
from ztare.leanmill.theory_context import TheoryLandscapeContext
from ztare.leanmill.theory_ir import content_hash


CountermodelFn = Callable[..., FiniteModelSearchReceipt]


@dataclass(frozen=True)
class CompoundImplication:
    candidate_id: str
    premise_formula_ids: tuple[str, ...]
    target_formula_id: str

    def to_json(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "premise_formula_ids": list(self.premise_formula_ids),
            "target_formula_id": self.target_formula_id,
        }


def enumerate_compound_implications(
    context: TheoryLandscapeContext,
    *,
    maximum_presentation_size: int = 2,
) -> tuple[CompoundImplication, ...]:
    """Enumerate unique joint-only implication coordinates in one chart."""

    if maximum_presentation_size < 2:
        raise ValueError("compound implications require presentation width at least two")
    rows: dict[str, CompoundImplication] = {}
    for node in context.generated_theory_nodes(
        max_presentation_size=maximum_presentation_size,
        semantic_quotient=True,
    ):
        for generator in node.minimal_generators:
            premises = tuple(sorted(str(row) for row in generator))
            if len(premises) < 2:
                continue
            for target in context.synergy_ids(premises):
                candidate_id = theory_implication_signature(
                    context.signature.content_hash, premises, target
                )
                rows[candidate_id] = CompoundImplication(
                    candidate_id, premises, str(target)
                )
    return tuple(rows[key] for key in sorted(rows))


def witness_eliminations(
    context: TheoryLandscapeContext,
    candidates: Sequence[CompoundImplication],
    model: FiniteModel,
) -> tuple[str, ...]:
    validate_model(context.signature, model)
    if not all(
        evaluate_axiom(context.signature, axiom, model)
        for axiom in context.base_axioms
    ):
        raise ValueError("sieve witness violates the frozen base theory")
    axioms = {row.formula_id: row.axiom for row in context.formula_profiles}
    truth = {
        formula_id: evaluate_axiom(context.signature, axiom, model)
        for formula_id, axiom in axioms.items()
    }
    return tuple(
        row.candidate_id
        for row in candidates
        if not truth[row.target_formula_id]
        and all(truth[premise] for premise in row.premise_formula_ids)
    )


def run_compound_implication_sieve(
    context: TheoryLandscapeContext,
    *,
    sort_sizes: Mapping[str, int],
    max_solver_queries: int,
    timeout_ms: int = 30_000,
    maximum_presentation_size: int = 2,
    candidate_ids: Sequence[str] | None = None,
    seed_witnesses: Sequence[FiniteModel] = (),
    prior_state: Mapping[str, Any] | None = None,
    countermodel_fn: CountermodelFn = find_finite_countermodel,
) -> dict[str, Any]:
    """Eliminate a candidate pool with shared countermodels, resumably."""

    if max_solver_queries < 0 or timeout_ms < 1:
        raise ValueError("sieve query and timeout bounds are invalid")
    if not context.complete:
        raise ValueError("compound implication sieve requires an exact source chart")
    all_candidates = enumerate_compound_implications(
        context, maximum_presentation_size=maximum_presentation_size
    )
    all_by_id = {row.candidate_id: row for row in all_candidates}
    if candidate_ids is not None:
        requested = tuple(dict.fromkeys(str(row) for row in candidate_ids))
        unknown_candidates = set(requested) - set(all_by_id)
        if not requested or unknown_candidates:
            raise ValueError("compound sieve candidate funnel is empty or stale")
        candidates = tuple(all_by_id[row] for row in requested)
    else:
        candidates = all_candidates
    by_id = {row.candidate_id: row for row in candidates}
    candidate_universe_sha256 = content_hash(sorted(by_id))
    prior = dict(prior_state or {})
    if prior:
        prior_core = {
            key: value for key, value in prior.items() if key != "receipt_sha256"
        }
        if (
            prior.get("receipt_sha256") != content_hash(prior_core)
            or prior.get("schema") != "leanmill.compound_implication_sieve.v1"
            or prior.get("context_hash") != context.context_hash
            or dict(prior.get("sort_sizes") or {}) != dict(sort_sizes)
            or prior.get("candidate_universe_sha256", candidate_universe_sha256)
            != candidate_universe_sha256
        ):
            raise ValueError("prior sieve state belongs to another experiment")
    eliminated = {
        str(row) for row in prior.get("eliminated_candidate_ids") or ()
    }
    queried = {str(row) for row in prior.get("queried_candidate_ids") or ()}
    fixed_size_survivors = {
        str(row) for row in prior.get("fixed_size_survivor_ids") or ()
    }
    vacuous = {str(row) for row in prior.get("vacuous_candidate_ids") or ()}
    unknown = {str(row) for row in prior.get("unknown_candidate_ids") or ()}
    if (eliminated | queried | fixed_size_survivors | vacuous | unknown) - set(by_id):
        raise ValueError("prior sieve state contains unknown candidate identities")
    query_receipts = list(prior.get("query_receipts") or ())
    witness_effects = [
        dict(row)
        for row in prior.get("witness_effects") or ()
        if isinstance(row, Mapping)
    ]
    witness_ids = {
        str(row.get("witness_sha256") or "")
        for row in witness_effects
        if isinstance(row, Mapping)
    }

    def apply_witness(model: FiniteModel, *, source_ref: str) -> dict[str, Any]:
        before = [row for row in candidates if row.candidate_id not in eliminated]
        witness_id = content_hash(model.to_json())
        refuted = set(witness_eliminations(context, candidates, model))
        killed = refuted - eliminated
        pricing = price_experiment(
            before,
            lambda row: row.candidate_id in killed,
            lambda row: len(row.premise_formula_ids) + 1,
            novel_context=witness_id not in witness_ids,
        )
        eliminated.update(killed)
        witness_ids.add(witness_id)
        effect = {
            "witness_sha256": witness_id,
            "source_ref": source_ref,
            "candidate_count_before": len(before),
            "eliminated_count": len(killed),
            "candidate_count_after": len(before) - len(killed),
            "refuted_candidate_ids": sorted(refuted),
            "yield": {
                "identification": round(pricing.identification, 8),
                "compression_gain": round(pricing.compression_gain, 8),
                "novelty": round(pricing.novelty, 8),
            },
        }
        witness_effects.append(effect)
        return effect

    for model in seed_witnesses:
        witness_id = content_hash(model.to_json())
        if witness_id not in witness_ids:
            apply_witness(model, source_ref="seed_witness")
            continue
        for effect in witness_effects:
            if (
                effect.get("witness_sha256") == witness_id
                and "refuted_candidate_ids" not in effect
            ):
                effect["refuted_candidate_ids"] = sorted(
                    witness_eliminations(context, candidates, model)
                )
                break

    axioms = {row.formula_id: row.axiom for row in context.formula_profiles}
    queries_used = 0
    while queries_used < max_solver_queries:
        eligible = [
            row
            for row in candidates
            if row.candidate_id not in eliminated
            and row.candidate_id not in queried
        ]
        if not eligible:
            break
        target_frequency = Counter(row.target_formula_id for row in eligible)
        target_attempts: Counter[str] = Counter()
        target_yield: Counter[str] = Counter()
        for row in query_receipts:
            candidate = by_id.get(str(row.get("candidate_id") or ""))
            if candidate is None:
                continue
            target_attempts[candidate.target_formula_id] += 1
            before = int(row.get("candidate_count_before") or 0)
            if before:
                target_yield[candidate.target_formula_id] += (
                    int(row.get("realized_eliminated_count") or 0) / before
                )
        selected = min(
            eligible,
            key=lambda row: (
                target_attempts[row.target_formula_id],
                -(
                    target_yield[row.target_formula_id]
                    / max(1, target_attempts[row.target_formula_id])
                ),
                -target_frequency[row.target_formula_id],
                len(row.premise_formula_ids),
                row.candidate_id,
            ),
        )
        queried.add(selected.candidate_id)
        receipt = countermodel_fn(
            context.signature,
            tuple(axioms[row] for row in selected.premise_formula_ids),
            axioms[selected.target_formula_id],
            sort_sizes=sort_sizes,
            base_axioms=tuple(context.base_axioms),
            timeout_ms=timeout_ms,
        )
        queries_used += 1
        receipt_json = receipt.to_json()
        query_row = {
            "candidate_id": selected.candidate_id,
            "target_formula_id": selected.target_formula_id,
            "target_family_visits_before": target_attempts[
                selected.target_formula_id
            ],
            "target_cluster_upper_bound": target_frequency[
                selected.target_formula_id
            ],
            "candidate_count_before": len(eligible),
            "realized_eliminated_count": 0,
            "search": receipt_json,
        }
        if receipt.status == "countermodel_found":
            assert receipt.witness is not None
            effect = apply_witness(
                receipt.witness,
                source_ref=str(receipt_json["receipt_sha256"]),
            )
            query_row["realized_eliminated_count"] = effect["eliminated_count"]
        elif receipt.status == "no_countermodel_at_fixed_size":
            fixed_size_survivors.add(selected.candidate_id)
        elif receipt.status == "no_premise_model_at_fixed_size":
            vacuous.add(selected.candidate_id)
        else:
            unknown.add(selected.candidate_id)
        query_receipts.append(query_row)

    surviving = [row for row in candidates if row.candidate_id not in eliminated]
    surviving_target_frequency = Counter(row.target_formula_id for row in surviving)
    target_attempts = Counter()
    target_yield: Counter[str] = Counter()
    for row in query_receipts:
        candidate = by_id.get(str(row.get("candidate_id") or ""))
        if candidate is None:
            continue
        target_attempts[candidate.target_formula_id] += 1
        before = int(row.get("candidate_count_before") or 0)
        if before:
            target_yield[candidate.target_formula_id] += (
                int(row.get("realized_eliminated_count") or 0) / before
            )
    frontier = sorted(
        surviving,
        key=lambda row: (
            target_attempts[row.target_formula_id],
            -(
                target_yield[row.target_formula_id]
                / max(1, target_attempts[row.target_formula_id])
            ),
            -surviving_target_frequency[row.target_formula_id],
            len(row.premise_formula_ids),
            row.candidate_id,
        ),
    )[:16]
    core = {
        "schema": "leanmill.compound_implication_sieve.v1",
        "context_hash": context.context_hash,
        "signature_sha256": context.signature.content_hash,
        "sort_sizes": dict(sort_sizes),
        "maximum_presentation_size": maximum_presentation_size,
        "candidate_universe_sha256": candidate_universe_sha256,
        "candidate_count": len(candidates),
        "eliminated_candidate_ids": sorted(eliminated),
        "surviving_candidate_ids": [row.candidate_id for row in surviving],
        "next_query_frontier": [
            {
                **row.to_json(),
                "same_target_elimination_upper_bound": surviving_target_frequency[
                    row.target_formula_id
                ],
                "target_family_visits": target_attempts[row.target_formula_id],
                "target_family_realized_yield": round(
                    target_yield[row.target_formula_id]
                    / max(1, target_attempts[row.target_formula_id]),
                    8,
                ),
            }
            for row in frontier
        ],
        "queried_candidate_ids": sorted(queried),
        "fixed_size_survivor_ids": sorted(fixed_size_survivors),
        "vacuous_candidate_ids": sorted(vacuous),
        "unknown_candidate_ids": sorted(unknown),
        "query_receipts": query_receipts,
        "witness_effects": witness_effects,
        "queries_used_this_call": queries_used,
        "status": (
            "seed_witnesses_applied"
            if max_solver_queries == 0
            else "query_budget_exhausted"
            if queries_used == max_solver_queries and any(
                row.candidate_id not in queried for row in surviving
            )
            else "fixed_size_frontier_classified"
        ),
        "selection_policy": (
            "target-family reachability, then realized batch elimination yield, "
            "then same-target elimination upper bound; witness yield priced by "
            "ztare.common.information_yield_pricing.price_experiment"
        ),
        "claim_boundary": (
            "fixed finite size only; target frequency is an upper bound, not an "
            "elimination guarantee"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


__all__ = [
    "CompoundImplication",
    "enumerate_compound_implications",
    "run_compound_implication_sieve",
    "witness_eliminations",
]
