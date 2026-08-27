"""Typed, deterministic signal derivation over point-in-time observations.

Signals are a small expression language over named metrics.  The interpreter
does not execute Python expressions and it never invents missing values.  Each
derived observation inherits the latest availability time of its inputs and
emits a receipt binding the formula to the exact source observations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.equivariance import stable_sha256

from .contracts import (
    MetricObservation,
    canonical_timestamp,
    require_finite,
    require_text,
)


SIGNAL_DEFINITION_SCHEMA = "jaggedthoughts-signal-definition-v1"
SIGNAL_RECEIPT_SCHEMA = "jaggedthoughts-signal-receipt-v1"
SIGNAL_OPERATOR_CONTRACT = (
    {"operator": "identity", "arity": 1, "type_rule": "preserve"},
    {"operator": "add", "arity": 2, "type_rule": "equal_units"},
    {"operator": "sum", "arity": "n", "type_rule": "equal_units"},
    {"operator": "mean", "arity": "n", "type_rule": "equal_units"},
    {"operator": "subtract", "arity": 2, "type_rule": "equal_units"},
    {"operator": "aligned_subtract", "arity": 2, "type_rule": "equal_units_and_observed_at"},
    {"operator": "min", "arity": "n", "type_rule": "equal_units"},
    {"operator": "max", "arity": "n", "type_rule": "equal_units"},
    {"operator": "multiply", "arity": "n", "type_rule": "declared_output_unit"},
    {"operator": "divide", "arity": 2, "type_rule": "declared_output_unit"},
    {"operator": "ratio", "arity": 2, "type_rule": "declared_output_unit"},
    {"operator": "yield", "arity": 2, "type_rule": "declared_output_unit"},
    {"operator": "reciprocal", "arity": 1, "type_rule": "multiple_to_decimal"},
    {"operator": "spread", "arity": 2, "type_rule": "declared_output_unit"},
    {"operator": "negative", "arity": 1, "type_rule": "preserve"},
    {"operator": "percent_change", "arity": 2, "type_rule": "equal_units_to_decimal"},
    {"operator": "cagr", "arity": 2, "type_rule": "equal_units_to_decimal"},
    {"operator": "clamp", "arity": 1, "type_rule": "preserve"},
    {"operator": "symmetric_bound", "arity": 1, "type_rule": "dimensionless_to_score"},
    {"operator": "log", "arity": 1, "type_rule": "dimensionless"},
    {"operator": "compound_rates", "arity": 2, "type_rule": "decimal_rates_to_decimal"},
)


@dataclass(frozen=True, slots=True)
class SignalArgument:
    """One metric reference or literal in a signal expression."""

    metric_id: str = ""
    value: float | None = None
    unit: str = ""
    entity_id: str = ""

    def __post_init__(self) -> None:
        metric = str(self.metric_id or "").strip()
        if bool(metric) == (self.value is not None):
            raise ValueError("signal argument must name exactly one metric or literal value")
        if metric:
            object.__setattr__(self, "metric_id", require_text(metric, "signal argument metric_id"))
            if self.entity_id:
                object.__setattr__(self, "entity_id", require_text(self.entity_id, "signal argument entity_id"))
        else:
            if self.entity_id:
                raise ValueError("literal signal argument cannot name an entity_id")
            object.__setattr__(self, "value", require_finite(self.value, "signal literal"))
            object.__setattr__(self, "unit", require_text(self.unit, "signal literal unit"))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SignalArgument":
        if "metric" in payload:
            return cls(
                metric_id=str(payload["metric"]), entity_id=str(payload.get("entity_id") or ""),
            )
        if "value" in payload:
            return cls(value=float(payload["value"]), unit=str(payload.get("unit") or "scalar"))
        raise ValueError("signal argument must contain metric or value")

    def to_dict(self) -> dict[str, Any]:
        return ({
            "metric": self.metric_id,
            **({"entity_id": self.entity_id} if self.entity_id else {}),
        } if self.metric_id else
                {"value": self.value, "unit": self.unit})


@dataclass(frozen=True, slots=True)
class SignalDefinition:
    signal_id: str
    entity_id: str
    metric_id: str
    operator: str
    arguments: tuple[SignalArgument, ...]
    unit: str
    description: str
    parameters: tuple[tuple[str, float], ...] = ()
    definition_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for attr in ("signal_id", "entity_id", "metric_id", "operator", "unit", "description"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"signal.{attr}"))
        arguments = tuple(self.arguments)
        if not arguments:
            raise ValueError("signal arguments must be nonempty")
        parameters = tuple(sorted(
            (require_text(name, "signal parameter"), require_finite(value, f"signal parameter {name}"))
            for name, value in self.parameters
        ))
        if len({name for name, _value in parameters}) != len(parameters):
            raise ValueError("signal parameter names must be unique")
        object.__setattr__(self, "arguments", arguments)
        object.__setattr__(self, "parameters", parameters)
        object.__setattr__(self, "definition_sha256", stable_sha256(self._payload()))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SignalDefinition":
        if payload.get("schema", SIGNAL_DEFINITION_SCHEMA) != SIGNAL_DEFINITION_SCHEMA:
            raise ValueError(f"signal schema must be {SIGNAL_DEFINITION_SCHEMA}")
        raw_args = payload.get("arguments")
        if not isinstance(raw_args, list):
            raise ValueError("signal arguments must be a list")
        raw_parameters = payload.get("parameters") or {}
        if not isinstance(raw_parameters, Mapping):
            raise ValueError("signal parameters must be a mapping")
        return cls(
            signal_id=str(payload.get("id") or payload.get("signal_id") or ""),
            entity_id=str(payload.get("entity_id") or ""),
            metric_id=str(payload.get("metric_id") or ""),
            operator=str(payload.get("operator") or ""),
            arguments=tuple(SignalArgument.from_dict(row) for row in raw_args if isinstance(row, Mapping)),
            unit=str(payload.get("unit") or ""),
            description=str(payload.get("description") or ""),
            parameters=tuple((str(name), float(value)) for name, value in raw_parameters.items()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIGNAL_DEFINITION_SCHEMA,
            "signal_id": self.signal_id,
            "entity_id": self.entity_id,
            "metric_id": self.metric_id,
            "operator": self.operator,
            "arguments": [row.to_dict() for row in self.arguments],
            "unit": self.unit,
            "description": self.description,
            "parameters": dict(self.parameters),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "definition_sha256": self.definition_sha256}


@dataclass(frozen=True, slots=True)
class SignalReceipt:
    definition: SignalDefinition
    observation: MetricObservation
    input_observation_ids: tuple[str, ...]
    input_source_refs: tuple[str, ...]
    receipt_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        ids = tuple(sorted({require_text(row, "input observation id") for row in self.input_observation_ids}))
        refs = tuple(sorted({require_text(row, "input source ref") for row in self.input_source_refs}))
        if not ids or not refs:
            raise ValueError("signal receipt requires source observations and refs")
        object.__setattr__(self, "input_observation_ids", ids)
        object.__setattr__(self, "input_source_refs", refs)
        object.__setattr__(self, "receipt_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIGNAL_RECEIPT_SCHEMA,
            "definition": self.definition.to_dict(),
            "observation": self.observation.to_dict(),
            "input_observation_ids": list(self.input_observation_ids),
            "input_source_refs": list(self.input_source_refs),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "receipt_sha256": self.receipt_sha256}


def _require_same_units(units: Sequence[str], operator: str) -> None:
    if len(set(units)) != 1:
        raise ValueError(f"signal operator {operator} requires equal input units, got {sorted(set(units))}")


def _evaluate(operator: str, values: Sequence[float], units: Sequence[str], parameters: Mapping[str, float]) -> float:
    """Interpret the bounded signal operator language."""
    if operator == "identity":
        if len(values) != 1:
            raise ValueError("identity requires one argument")
        return values[0]
    if operator in {"add", "sum", "mean", "subtract", "aligned_subtract", "min", "max"}:
        _require_same_units(units, operator)
    if operator in {"add", "sum"}:
        return sum(values)
    if operator == "mean":
        return sum(values) / len(values)
    if operator in {"subtract", "aligned_subtract"}:
        if len(values) != 2:
            raise ValueError(f"{operator} requires two arguments")
        return values[0] - values[1]
    if operator == "multiply":
        result = 1.0
        for value in values:
            result *= value
        return result
    if operator in {"divide", "ratio", "yield"}:
        if len(values) != 2:
            raise ValueError(f"{operator} requires two arguments")
        if values[1] == 0:
            raise ValueError(f"{operator} denominator is zero")
        return values[0] / values[1]
    if operator == "reciprocal":
        if len(values) != 1 or values[0] == 0:
            raise ValueError("reciprocal requires one nonzero argument")
        return 1.0 / values[0]
    if operator == "spread":
        if len(values) != 2:
            raise ValueError("spread requires two arguments")
        return values[0] - values[1]
    if operator == "negative":
        if len(values) != 1:
            raise ValueError("negative requires one argument")
        return -values[0]
    if operator == "percent_change":
        if len(values) != 2 or values[1] == 0:
            raise ValueError("percent_change requires current and nonzero base")
        return values[0] / values[1] - 1.0
    if operator == "cagr":
        if len(values) != 2 or values[0] <= 0 or values[1] <= 0:
            raise ValueError("cagr requires positive ending and starting values")
        years = parameters.get("years")
        if years is None or years <= 0:
            raise ValueError("cagr requires a positive years parameter")
        return (values[0] / values[1]) ** (1.0 / years) - 1.0
    if operator == "clamp":
        if len(values) != 1:
            raise ValueError("clamp requires one argument")
        lower = parameters.get("lower", -math.inf)
        upper = parameters.get("upper", math.inf)
        if lower > upper:
            raise ValueError("clamp lower cannot exceed upper")
        return min(upper, max(lower, values[0]))
    if operator == "symmetric_bound":
        if len(values) != 1 or units[0] not in {"decimal", "multiple", "score"}:
            raise ValueError("symmetric_bound requires one dimensionless argument")
        return values[0] / (1.0 + abs(values[0]))
    if operator == "log":
        if len(values) != 1 or values[0] <= 0:
            raise ValueError("log requires one positive argument")
        return math.log(values[0])
    if operator == "compound_rates":
        if len(values) != 2:
            raise ValueError("compound_rates requires two arguments")
        if set(units) != {"decimal"}:
            raise ValueError("compound_rates requires decimal rate inputs")
        return (1.0 + values[0]) * (1.0 + values[1]) - 1.0
    raise ValueError(f"unsupported signal operator: {operator}")


def _derive_signal_graph(
    observations: Iterable[MetricObservation],
    definitions: Iterable[SignalDefinition],
    *,
    as_of: str,
    tolerate_blocks: bool,
) -> tuple[tuple[MetricObservation, ...], tuple[SignalReceipt, ...], tuple[dict[str, str], ...]]:
    canonical_as_of = canonical_timestamp(as_of, "signals.as_of")
    pool = list(observations)
    definitions_by_output: dict[tuple[str, str], SignalDefinition] = {}
    for definition in definitions:
        key = (definition.entity_id, definition.metric_id)
        if key in definitions_by_output:
            raise ValueError(f"duplicate signal output: {key[0]}.{key[1]}")
        definitions_by_output[key] = definition
    # A configured signal is one current materialization. Recompute it from source
    # observations instead of retaining a prior formula when the current one blocks.
    pool = [
        row for row in pool
        if (row.entity_id, row.metric_id) not in definitions_by_output
        or not row.source_ref.startswith("signal:")
    ]
    latest_by_input: dict[tuple[str, str], MetricObservation] = {}
    for row in pool:
        if row.available_at > canonical_as_of:
            continue
        key = (row.entity_id, row.metric_id)
        current = latest_by_input.get(key)
        if current is None or (
            row.available_at, row.observed_at, row.observation_id
        ) > (
            current.available_at,
            current.observed_at,
            current.observation_id,
        ):
            latest_by_input[key] = row
    pending = dict(definitions_by_output)
    produced: dict[tuple[str, str], MetricObservation] = {}
    receipts: list[SignalReceipt] = []
    blocks: list[dict[str, str]] = []
    while pending:
        progress = False
        for key, definition in tuple(sorted(pending.items())):
            inputs: list[MetricObservation] = []
            values: list[float] = []
            units: list[str] = []
            unresolved = False
            missing_input = ""
            for argument in definition.arguments:
                if argument.metric_id:
                    input_entity_id = argument.entity_id or definition.entity_id
                    dependency = (input_entity_id, argument.metric_id)
                    if dependency in pending:
                        unresolved = True
                        break
                    if dependency in definitions_by_output:
                        row = produced.get(dependency)
                        if row is None:
                            missing_input = (
                                f"blocked current signal input: "
                                f"{input_entity_id}.{argument.metric_id}"
                            )
                            break
                    else:
                        row = latest_by_input.get(dependency)
                        if row is None:
                            if not tolerate_blocks:
                                raise KeyError(
                                    f"missing signal input: {input_entity_id}.{argument.metric_id}"
                                )
                            missing_input = (
                                f"missing signal input: {input_entity_id}.{argument.metric_id}"
                            )
                            break
                    inputs.append(row)
                    values.append(row.value)
                    units.append(row.unit)
                else:
                    values.append(float(argument.value))
                    units.append(argument.unit)
            if unresolved:
                continue
            if missing_input:
                blocks.append({
                    "signal_id": definition.signal_id,
                    "entity_id": definition.entity_id,
                    "metric_id": definition.metric_id,
                    "reason": missing_input,
                })
                del pending[key]
                progress = True
                continue
            try:
                if definition.operator == "aligned_subtract" and (
                    len(inputs) != 2 or len({row.observed_at for row in inputs}) != 1
                ):
                    epochs = sorted({row.observed_at for row in inputs})
                    raise ValueError(
                        "aligned_subtract requires two observations with the same "
                        f"observed_at, got {epochs}"
                    )
                value = _evaluate(definition.operator, values, units, dict(definition.parameters))
            except ValueError as error:
                if not tolerate_blocks:
                    raise
                blocks.append({
                    "signal_id": definition.signal_id,
                    "entity_id": definition.entity_id,
                    "metric_id": definition.metric_id,
                    "reason": str(error),
                })
                del pending[key]
                progress = True
                continue
            observed_at = max(row.observed_at for row in inputs)
            available_at = max(row.available_at for row in inputs)
            identity = stable_sha256({
                "definition": definition.definition_sha256,
                "inputs": [row.observation_id for row in inputs],
            })
            observation = MetricObservation(
                observation_id=f"signal:{definition.signal_id}:{identity[:16]}",
                entity_id=definition.entity_id,
                metric_id=definition.metric_id,
                value=value,
                unit=definition.unit,
                observed_at=observed_at,
                available_at=available_at,
                source_ref=f"signal:{definition.signal_id}:{definition.definition_sha256[:16]}",
            )
            receipt = SignalReceipt(
                definition=definition,
                observation=observation,
                input_observation_ids=tuple(row.observation_id for row in inputs),
                input_source_refs=tuple(row.source_ref for row in inputs),
            )
            pool.append(observation)
            produced[key] = observation
            latest_by_input[key] = observation
            receipts.append(receipt)
            del pending[key]
            progress = True
        if not progress:
            blocked = ", ".join(f"{entity}.{metric}" for entity, metric in sorted(pending))
            if not tolerate_blocks:
                raise ValueError(f"signal graph has a cycle or unresolved inputs: {blocked}")
            for key, definition in sorted(pending.items()):
                blocks.append({
                    "signal_id": definition.signal_id,
                    "entity_id": definition.entity_id,
                    "metric_id": definition.metric_id,
                    "reason": f"signal graph has a cycle or unresolved inputs: {blocked}",
                })
            pending.clear()
    current_epochs = {
        (entity_id, metric_id): (row.observed_at, row.available_at)
        for (entity_id, metric_id), row in produced.items()
    }
    if current_epochs:
        pool = [
            row for row in pool
            if (row.entity_id, row.metric_id) not in current_epochs
            or row is produced[(row.entity_id, row.metric_id)]
            or (row.observed_at, row.available_at) != current_epochs[(row.entity_id, row.metric_id)]
        ]
    return (
        tuple(sorted(pool, key=lambda row: (row.entity_id, row.metric_id, row.available_at, row.observation_id))),
        tuple(sorted(receipts, key=lambda row: row.definition.signal_id)),
        tuple(sorted(blocks, key=lambda row: (row["entity_id"], row["metric_id"], row["signal_id"]))),
    )


def derive_signals(
    observations: Iterable[MetricObservation],
    definitions: Iterable[SignalDefinition],
    *,
    as_of: str,
) -> tuple[tuple[MetricObservation, ...], tuple[SignalReceipt, ...]]:
    """Resolve an all-or-nothing signal DAG."""
    rows, receipts, _blocks = _derive_signal_graph(
        observations, definitions, as_of=as_of, tolerate_blocks=False,
    )
    return rows, receipts


def derive_signals_partial(
    observations: Iterable[MetricObservation],
    definitions: Iterable[SignalDefinition],
    *,
    as_of: str,
) -> tuple[tuple[MetricObservation, ...], tuple[SignalReceipt, ...], tuple[dict[str, str], ...]]:
    """Resolve the maximal derivable subgraph and type each isolated block."""
    return _derive_signal_graph(
        observations, definitions, as_of=as_of, tolerate_blocks=True,
    )


__all__ = [
    "SIGNAL_DEFINITION_SCHEMA",
    "SIGNAL_OPERATOR_CONTRACT",
    "SIGNAL_RECEIPT_SCHEMA",
    "SignalArgument",
    "SignalDefinition",
    "SignalReceipt",
    "derive_signals",
    "derive_signals_partial",
]
