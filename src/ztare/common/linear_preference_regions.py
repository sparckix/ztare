"""Exact preference regions for a finite multi-objective frontier."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
import math
from typing import Any, Mapping

from .equivariance import stable_sha256


SCHEMA = "ztare-linear-preference-regions-v1"


def _fraction(value: int | float | str | Decimal | Fraction) -> Fraction:
    if isinstance(value, bool):
        raise ValueError("objective values cannot be booleans")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("objective values must be finite")
    try:
        return Fraction(Decimal(str(value)))
    except Exception as error:
        raise ValueError(f"invalid objective value: {value!r}") from error


def _render(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _model_weights(z3: Any, model: Any, variables: list[Any], names: tuple[str, ...]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, variable in zip(names, variables, strict=True):
        value = model.eval(variable, model_completion=True)
        if not z3.is_rational_value(value):
            raise RuntimeError("QF_LRA preference witness was not rational")
        result[name] = _render(Fraction(value.numerator_as_long(), value.denominator_as_long()))
    return result


def _coordinate_bound(
    z3: Any,
    constraints: list[Any],
    variable: Any,
    *,
    maximize: bool,
) -> Fraction:
    optimizer = z3.Optimize()
    optimizer.add(*constraints)
    (optimizer.maximize if maximize else optimizer.minimize)(variable)
    if optimizer.check() != z3.sat:
        raise RuntimeError("Z3 could not derive a preference-region coordinate bound")
    value = optimizer.model().eval(variable, model_completion=True)
    if not z3.is_rational_value(value):
        raise RuntimeError("QF_LRA preference bound was not rational")
    return Fraction(value.numerator_as_long(), value.denominator_as_long())


def compile_linear_preference_regions(
    *,
    objective_names: tuple[str, ...],
    alternatives: Mapping[str, Mapping[str, int | float | str | Decimal | Fraction]],
) -> dict[str, Any]:
    """Partition the nonnegative unit weight simplex by the optimal alternative.

    Every objective is higher-is-better. Callers normalize direction and scale
    before entering this boundary. SAT yields an exact weight witness; UNSAT
    yields the competing inequalities that exclude an alternative.
    """
    import z3

    objectives = tuple(sorted(str(name).strip() for name in objective_names))
    if not objectives or any(not name for name in objectives) or len(set(objectives)) != len(objectives):
        raise ValueError("objective_names must be nonempty and unique")
    if not alternatives:
        raise ValueError("preference regions require alternatives")

    vectors: dict[str, tuple[Fraction, ...]] = {}
    for alternative_id, raw in sorted(alternatives.items()):
        identity = str(alternative_id).strip()
        if not identity or identity in vectors:
            raise ValueError("alternative IDs must be nonempty and unique")
        if set(raw) != set(objectives):
            raise ValueError(f"alternative {identity} does not match the objective universe")
        vectors[identity] = tuple(_fraction(raw[name]) for name in objectives)

    alternative_ids = tuple(vectors)
    weights = [z3.Real(f"preference_weight_{index}") for index in range(len(objectives))]
    base = [weight >= 0 for weight in weights]
    base.append(z3.Sum(weights) == 1)

    def score(alternative_id: str) -> Any:
        return z3.Sum([
            z3.Q(value.numerator, value.denominator) * weight
            for value, weight in zip(vectors[alternative_id], weights, strict=True)
        ])

    scores = {alternative_id: score(alternative_id) for alternative_id in alternative_ids}

    def canonical_model(*constraints: Any, maximize: Any | None = None) -> Any:
        optimizer = z3.Optimize()
        optimizer.set(priority="lex")
        optimizer.add(*constraints)
        if maximize is not None:
            optimizer.maximize(maximize)
        for weight in weights:
            optimizer.minimize(weight)
        if optimizer.check() != z3.sat:
            raise RuntimeError("Z3 could not construct a canonical preference witness")
        return optimizer.model()

    regions: list[dict[str, Any]] = []
    for index, alternative_id in enumerate(alternative_ids):
        solver = z3.Solver()
        solver.set(unsat_core=True)
        solver.add(*base)
        label_to_competitor: dict[str, str] = {}
        inequalities: list[dict[str, Any]] = []
        for competitor_index, competitor_id in enumerate(alternative_ids):
            if competitor_id == alternative_id:
                continue
            label_name = f"region_{index}_beats_{competitor_index}"
            label = z3.Bool(label_name)
            solver.assert_and_track(scores[alternative_id] >= scores[competitor_id], label)
            label_to_competitor[label_name] = competitor_id
            inequalities.append({
                "competitor_id": competitor_id,
                "coefficients": {
                    name: _render(left - right)
                    for name, left, right in zip(
                        objectives, vectors[alternative_id], vectors[competitor_id], strict=True
                    )
                },
                "relation": "weighted_sum_gte_zero",
            })
        verdict = solver.check()
        if verdict == z3.unknown:
            raise RuntimeError(f"Z3 could not decide preference region: {solver.reason_unknown()}")

        row: dict[str, Any] = {
            "alternative_id": alternative_id,
            "inequalities": inequalities,
            "supported": verdict == z3.sat,
        }
        if verdict == z3.sat:
            region_constraints = [
                scores[alternative_id] >= scores[competitor_id]
                for competitor_id in alternative_ids if competitor_id != alternative_id
            ]
            closed_region = [*base, *region_constraints]
            row["preference_witness"] = _model_weights(
                z3,
                canonical_model(*closed_region),
                weights,
                objectives,
            )
            row["coordinate_bounds"] = {
                name: {
                    "lower_exact": _render(_coordinate_bound(
                        z3, closed_region, weight, maximize=False,
                    )),
                    "upper_exact": _render(_coordinate_bound(
                        z3, closed_region, weight, maximize=True,
                    )),
                }
                for name, weight in zip(objectives, weights, strict=True)
            }
            strict = z3.Solver()
            strict.add(*base)
            strict.add(*[
                scores[alternative_id] > scores[competitor_id]
                for competitor_id in alternative_ids if competitor_id != alternative_id
            ])
            strict_verdict = strict.check()
            if strict_verdict == z3.unknown:
                raise RuntimeError(f"Z3 could not decide strict preference region: {strict.reason_unknown()}")
            row["strictly_supported"] = strict_verdict == z3.sat
            if strict_verdict == z3.sat:
                margin = z3.Real(f"strict_preference_margin_{index}")
                strict_model = canonical_model(
                    *base,
                    margin >= 0,
                    *[
                        scores[alternative_id] >= scores[competitor_id] + margin
                        for competitor_id in alternative_ids if competitor_id != alternative_id
                    ],
                    maximize=margin,
                )
                row["strict_preference_witness"] = _model_weights(
                    z3, strict_model, weights, objectives
                )
        else:
            row["strictly_supported"] = False
            row["unsat_core_competitor_ids"] = sorted({
                label_to_competitor[str(label)] for label in solver.unsat_core()
            })

        reversal = z3.Solver()
        reversal.add(*base)
        reversal.add(z3.Or(*[
            scores[competitor_id] > scores[alternative_id]
            for competitor_id in alternative_ids if competitor_id != alternative_id
        ]))
        reversal_verdict = reversal.check()
        if reversal_verdict == z3.unknown:
            raise RuntimeError(f"Z3 could not decide preference reversal: {reversal.reason_unknown()}")
        row["optimal_across_entire_preference_simplex"] = reversal_verdict == z3.unsat
        if reversal_verdict == z3.sat:
            margin = z3.Real(f"reversal_margin_{index}")
            model = canonical_model(
                *base,
                margin >= 0,
                z3.Or(*[
                    scores[competitor_id] >= scores[alternative_id] + margin
                    for competitor_id in alternative_ids if competitor_id != alternative_id
                ]),
                maximize=margin,
            )
            row["reversal_witness"] = _model_weights(z3, model, weights, objectives)
            row["reversal_competitor_ids"] = sorted(
                competitor_id for competitor_id in alternative_ids
                if competitor_id != alternative_id
                and z3.is_true(model.eval(scores[competitor_id] > scores[alternative_id], model_completion=True))
            )
        regions.append(row)

    body = {
        "schema": SCHEMA,
        "solver": {"name": "z3", "version": z3.get_version_string(), "logic": "QF_LRA"},
        "objective_names": list(objectives),
        "weight_domain": "nonnegative_unit_simplex",
        "alternative_vectors": {
            alternative_id: {
                name: _render(value)
                for name, value in zip(objectives, vectors[alternative_id], strict=True)
            }
            for alternative_id in alternative_ids
        },
        "regions": regions,
        "supported_alternative_ids": [row["alternative_id"] for row in regions if row["supported"]],
        "strictly_supported_alternative_ids": [
            row["alternative_id"] for row in regions if row["strictly_supported"]
        ],
        "use_boundary": (
            "This certificate varies declared objective priorities only. It does not estimate objective "
            "values, probabilities, causal effects, or expected returns."
        ),
    }
    return {**body, "preference_regions_sha256": stable_sha256(body)}


__all__ = ["SCHEMA", "compile_linear_preference_regions"]
