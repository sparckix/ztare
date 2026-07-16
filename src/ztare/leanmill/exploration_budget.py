"""Host-owned resource and stopping contracts for frontier exploration."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
import json
from pathlib import Path
import re
import time
import uuid
from typing import Any, Callable, Mapping, Sequence

import yaml

from ztare.leanmill.common import append_jsonl_locked
from ztare.leanmill.campaign_profile import frontier_budget_preset_for_profile
from ztare.leanmill.theory_ir import content_hash


BUDGET_SCHEMA = "leanmill.exploration_budget.v1"
BUDGET_EVENT_SCHEMA = "leanmill.exploration_budget_event.v1"
STOP_RECEIPT_SCHEMA = "leanmill.budget_stop_receipt.v1"
USER_BUDGET_SCHEMA = "leanmill.exploration_budget_user.v1"

PHASES = (
    "compilation",
    "context",
    "navigation",
    "expansion",
    "boundary",
    "interpretation",
)
RESOURCE_KINDS = frozenset(
    {
        "provider_calls",
        "agent_turns",
        "input_tokens",
        "output_tokens",
        "metered_usd_micros",
        "workbench_actions",
        "adapter_forge_attempts",
        "context_models",
        "truth_cells",
        "boundary_queries",
        "smt_calls",
        "smt_millis",
        "formal_peer_attempts",
        "formal_peer_millis",
        "lean_attempts",
        "lean_millis",
    }
)
_LEGACY_OPTIONAL_RESOURCES = frozenset(
    {"formal_peer_attempts", "formal_peer_millis"}
)
_EXPANSION_AGENT_RESOURCES = frozenset(
    {
        "provider_calls",
        "agent_turns",
        "input_tokens",
        "output_tokens",
        "metered_usd_micros",
    }
)
_BOUNDARY_CALL_RESOURCES = frozenset({"provider_calls", "agent_turns"})


def _caps(**values: int) -> dict[str, int]:
    unknown = set(values) - RESOURCE_KINDS
    if unknown:
        raise ValueError(f"unknown budget resources: {sorted(unknown)}")
    return {key: int(values.get(key, 0)) for key in sorted(RESOURCE_KINDS)}


_PRESET_CAPS: dict[str, tuple[int, dict[str, int]]] = {
    "smoke_20m": (
        20 * 60,
        _caps(
            provider_calls=8, agent_turns=8, input_tokens=100_000,
            output_tokens=40_000, metered_usd_micros=2_000_000,
            workbench_actions=16, adapter_forge_attempts=1,
            context_models=25_000, truth_cells=10_000_000,
            boundary_queries=2, smt_calls=2, smt_millis=600_000,
            formal_peer_attempts=1, formal_peer_millis=180_000,
            lean_attempts=1, lean_millis=600_000,
        ),
    ),
    "quick": (
        20 * 60,
        _caps(
            provider_calls=12, agent_turns=14, input_tokens=250_000,
            output_tokens=80_000, metered_usd_micros=5_000_000,
            workbench_actions=32, adapter_forge_attempts=1,
            context_models=30_000, truth_cells=12_000_000,
            boundary_queries=4, smt_calls=4, smt_millis=900_000,
            formal_peer_attempts=2, formal_peer_millis=300_000,
            lean_attempts=2, lean_millis=900_000,
        ),
    ),
    "standard": (
        2 * 60 * 60,
        _caps(
            provider_calls=24, agent_turns=30, input_tokens=750_000,
            output_tokens=250_000, metered_usd_micros=20_000_000,
            workbench_actions=96, adapter_forge_attempts=2,
            context_models=100_000, truth_cells=50_000_000,
            boundary_queries=12, smt_calls=12, smt_millis=3_600_000,
            formal_peer_attempts=6, formal_peer_millis=1_800_000,
            lean_attempts=6, lean_millis=3_600_000,
        ),
    ),
    "deep": (
        6 * 60 * 60,
        _caps(
            provider_calls=72, agent_turns=90, input_tokens=2_500_000,
            output_tokens=800_000, metered_usd_micros=60_000_000,
            workbench_actions=288, adapter_forge_attempts=4,
            context_models=500_000, truth_cells=250_000_000,
            boundary_queries=36, smt_calls=36, smt_millis=10_800_000,
            formal_peer_attempts=18, formal_peer_millis=5_400_000,
            lean_attempts=18, lean_millis=10_800_000,
        ),
    ),
    "overnight": (
        12 * 60 * 60,
        _caps(
            provider_calls=144, agent_turns=180, input_tokens=5_000_000,
            output_tokens=1_600_000, metered_usd_micros=120_000_000,
            workbench_actions=576, adapter_forge_attempts=8,
            context_models=1_000_000, truth_cells=500_000_000,
            boundary_queries=72, smt_calls=72, smt_millis=21_600_000,
            formal_peer_attempts=36, formal_peer_millis=10_800_000,
            lean_attempts=36, lean_millis=21_600_000,
        ),
    ),
    "local_only": (
        2 * 60 * 60,
        _caps(
            provider_calls=0, agent_turns=0, input_tokens=0,
            output_tokens=0, metered_usd_micros=0,
            workbench_actions=96, adapter_forge_attempts=0,
            context_models=100_000, truth_cells=50_000_000,
            boundary_queries=12, smt_calls=12, smt_millis=3_600_000,
            formal_peer_attempts=12, formal_peer_millis=3_600_000,
            lean_attempts=0, lean_millis=0,
        ),
    ),
}


def _partition(total: int, weights: tuple[int, ...]) -> tuple[int, ...]:
    """Integer partition whose entries sum to total."""
    if total <= 0:
        return tuple(0 for _ in weights)
    denominator = sum(weights)
    numerators = [total * weight for weight in weights]
    values = [numerator // denominator for numerator in numerators]
    ranked = sorted(
        range(len(weights)),
        key=lambda index: (numerators[index] % denominator, weights[index], -index),
        reverse=True,
    )
    for index in ranked[: total - sum(values)]:
        values[index] += 1
    return tuple(values)


def _default_phase_caps(hard_caps: Mapping[str, int]) -> dict[str, dict[str, int]]:
    result = {phase: {key: 0 for key in sorted(RESOURCE_KINDS)} for phase in PHASES}
    for resource in ("provider_calls", "agent_turns", "input_tokens", "output_tokens", "metered_usd_micros"):
        shares = _partition(int(hard_caps[resource]), (3, 0, 4, 3, 3, 1))
        for phase, share in zip(PHASES, shares, strict=True):
            result[phase][resource] = share
    result["navigation"]["workbench_actions"] = int(hard_caps["workbench_actions"])
    result["expansion"]["adapter_forge_attempts"] = int(hard_caps["adapter_forge_attempts"])
    result["context"]["context_models"] = int(hard_caps["context_models"])
    result["context"]["truth_cells"] = int(hard_caps["truth_cells"])
    for resource in (
        "boundary_queries",
        "smt_calls",
        "smt_millis",
        "formal_peer_attempts",
        "formal_peer_millis",
        "lean_attempts",
        "lean_millis",
    ):
        result["boundary"][resource] = int(hard_caps[resource])
    return result


@dataclass(frozen=True)
class ScientificStopRule:
    max_finalists: int = 8
    min_marginal_information_per_cost_ppm: int = 50_000
    low_yield_patience: int = 3
    coverage_target_ppm: int = 900_000
    schema: str = "leanmill.scientific_stop_rule.v1"

    def __post_init__(self) -> None:
        if self.max_finalists < 1 or self.low_yield_patience < 1:
            raise ValueError("scientific stopping counts must be positive")
        for value in (
            self.min_marginal_information_per_cost_ppm,
            self.coverage_target_ppm,
        ):
            if not 0 <= value <= 1_000_000:
                raise ValueError("scientific stopping ratios must be parts per million")

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "max_finalists": self.max_finalists,
            "min_marginal_information_per_cost_ppm": self.min_marginal_information_per_cost_ppm,
            "low_yield_patience": self.low_yield_patience,
            "coverage_target_ppm": self.coverage_target_ppm,
        }

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "ScientificStopRule":
        return cls(
            max_finalists=int(value.get("max_finalists", 8)),
            min_marginal_information_per_cost_ppm=int(
                value.get("min_marginal_information_per_cost_ppm", 50_000)
            ),
            low_yield_patience=int(value.get("low_yield_patience", 3)),
            coverage_target_ppm=int(value.get("coverage_target_ppm", 900_000)),
            schema=str(value.get("schema", "leanmill.scientific_stop_rule.v1")),
        )


@dataclass(frozen=True)
class ExplorationBudget:
    preset: str
    wall_clock_s: int
    hard_caps: Mapping[str, int]
    phase_caps: Mapping[str, Mapping[str, int]]
    stop_rule: ScientificStopRule = field(default_factory=ScientificStopRule)
    allocation_policy: str = "roll_forward_protected_future"
    schema: str = BUDGET_SCHEMA
    _frozen_digest: str = field(default="", repr=False, compare=False)
    _omitted_resources: tuple[str, ...] = field(default=(), repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.schema != BUDGET_SCHEMA or self.wall_clock_s < 1:
            raise ValueError("invalid exploration budget schema or wall-clock cap")
        if self.allocation_policy not in {
            "global_cap",
            "strict_phase_caps",
            "roll_forward_protected_future",
        }:
            raise ValueError("invalid exploration budget allocation policy")
        if set(self.hard_caps) != RESOURCE_KINDS:
            raise ValueError("exploration budget must cap every resource kind")
        if set(self.phase_caps) != set(PHASES):
            raise ValueError("exploration budget must define every phase")
        for key, value in self.hard_caps.items():
            if type(value) is not int or value < 0:
                raise ValueError(f"invalid hard cap for {key}")
        phase_sums = {key: 0 for key in RESOURCE_KINDS}
        for phase, caps in self.phase_caps.items():
            if set(caps) != RESOURCE_KINDS:
                raise ValueError(f"phase {phase} must cap every resource kind")
            for key, value in caps.items():
                if type(value) is not int or value < 0:
                    raise ValueError(f"invalid {phase} cap for {key}")
                phase_sums[key] += value
        for key, total in phase_sums.items():
            if total > self.hard_caps[key]:
                raise ValueError(f"phase allocations exceed hard cap for {key}")

    @property
    def digest(self) -> str:
        return self._frozen_digest or (
            "budget:" + content_hash(self.to_json(include_digest=False))
        )

    def to_json(self, *, include_digest: bool = True) -> dict[str, Any]:
        omitted = set(self._omitted_resources)
        core = {
            "schema": self.schema,
            "preset": self.preset,
            "wall_clock_s": self.wall_clock_s,
            "hard_caps": {
                key: int(self.hard_caps[key])
                for key in sorted(RESOURCE_KINDS)
                if key not in omitted
            },
            "phase_caps": {
                phase: {
                    key: int(self.phase_caps[phase][key])
                    for key in sorted(RESOURCE_KINDS)
                    if key not in omitted
                }
                for phase in PHASES
            },
            "stop_rule": self.stop_rule.to_json(),
            "allocation_policy": self.allocation_policy,
        }
        return {**core, "budget_digest": self.digest} if include_digest else core

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "ExplorationBudget":
        raw_hard_caps = {
            str(key): int(item) for key, item in dict(value["hard_caps"]).items()
        }
        unknown = set(raw_hard_caps) - RESOURCE_KINDS
        if unknown:
            raise ValueError(f"exploration budget has unknown resources: {sorted(unknown)}")
        omitted = tuple(sorted(RESOURCE_KINDS - set(raw_hard_caps)))
        if set(omitted) - _LEGACY_OPTIONAL_RESOURCES:
            raise ValueError(
                f"exploration budget is missing resources: {sorted(set(omitted) - _LEGACY_OPTIONAL_RESOURCES)}"
            )
        hard_caps = {key: int(raw_hard_caps.get(key, 0)) for key in RESOURCE_KINDS}
        raw_phase_caps = {
            str(phase): {str(key): int(item) for key, item in dict(caps).items()}
            for phase, caps in dict(value["phase_caps"]).items()
        }
        if set(raw_phase_caps) != set(PHASES):
            raise ValueError("exploration budget must define every phase")
        for phase, caps in raw_phase_caps.items():
            phase_unknown = set(caps) - RESOURCE_KINDS
            phase_missing = (RESOURCE_KINDS - set(caps)) - _LEGACY_OPTIONAL_RESOURCES
            if phase_unknown or phase_missing:
                raise ValueError(
                    f"phase {phase} has invalid resources: "
                    f"unknown={sorted(phase_unknown)} missing={sorted(phase_missing)}"
                )
        phase_caps = {
            phase: {
                key: int(raw_phase_caps.get(phase, {}).get(key, 0))
                for key in RESOURCE_KINDS
            }
            for phase in PHASES
        }
        budget = cls(
            preset=str(value.get("preset") or "custom"),
            wall_clock_s=int(value["wall_clock_s"]),
            hard_caps=hard_caps,
            phase_caps=phase_caps,
            stop_rule=ScientificStopRule.from_json(dict(value.get("stop_rule") or {})),
            allocation_policy=str(
                value.get("allocation_policy") or "strict_phase_caps"
            ),
            schema=str(value.get("schema", BUDGET_SCHEMA)),
            _omitted_resources=omitted,
        )
        supplied = value.get("budget_digest")
        if supplied is None:
            return budget
        supplied = str(supplied)
        if supplied != budget.digest:
            raw_core = {
                key: value[key]
                for key in (
                    "schema",
                    "preset",
                    "wall_clock_s",
                    "hard_caps",
                    "phase_caps",
                    "stop_rule",
                    "allocation_policy",
                )
                if key in value
            }
            if supplied != "budget:" + content_hash(raw_core):
                raise ValueError("exploration budget digest mismatch")
        return cls(
            preset=budget.preset,
            wall_clock_s=budget.wall_clock_s,
            hard_caps=budget.hard_caps,
            phase_caps=budget.phase_caps,
            stop_rule=budget.stop_rule,
            allocation_policy=budget.allocation_policy,
            schema=budget.schema,
            _frozen_digest=supplied,
            _omitted_resources=omitted,
        )


@dataclass(frozen=True)
class BudgetPreferenceCompilation:
    source_mode: str
    source_text: str
    recognized_preferences: tuple[Mapping[str, Any], ...]
    delegated_stop_instruction: str
    budget_digest: str
    schema: str = "leanmill.budget_preference_compilation.v1"

    def to_json(self) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "source_mode": self.source_mode,
            "source_text": self.source_text,
            "recognized_preferences": [dict(row) for row in self.recognized_preferences],
            "delegated_stop_instruction": self.delegated_stop_instruction,
            "budget_digest": self.budget_digest,
        }
        return {**core, "receipt_sha256": content_hash(core)}


def budget_preset(name: str) -> ExplorationBudget:
    resolved = frontier_budget_preset_for_profile(str(name))
    try:
        wall_clock_s, hard_caps = _PRESET_CAPS[resolved]
    except KeyError as exc:
        raise ValueError(f"unknown exploration budget preset: {name!r}") from exc
    return ExplorationBudget(
        preset=resolved,
        wall_clock_s=wall_clock_s,
        hard_caps=hard_caps,
        phase_caps=_default_phase_caps(hard_caps),
    )


_DURATION = re.compile(r"^(?P<value>[0-9]+(?:\.[0-9]+)?)(?P<unit>ms|s|m|h)$")
def _duration_millis(value: str) -> int:
    match = _DURATION.fullmatch(value.strip().lower())
    if not match:
        raise ValueError(f"invalid duration: {value!r}")
    number = Decimal(match.group("value"))
    multiplier = {"ms": 1, "s": 1_000, "m": 60_000, "h": 3_600_000}[match.group("unit")]
    return int(number * multiplier)


def parse_exploration_budget(value: str | Mapping[str, Any] | ExplorationBudget | None) -> ExplorationBudget:
    """Parse a named profile or a typed/YAML budget mapping."""
    if isinstance(value, ExplorationBudget):
        return value
    if isinstance(value, Mapping):
        if "budget" in value:
            return budget_from_user_mapping(value)[0]
        if value.get("schema") == BUDGET_SCHEMA or "hard_caps" in value:
            return ExplorationBudget.from_json(value)
        if set(value) <= {"preset", "profile"}:
            return budget_preset(str(value.get("preset") or value.get("profile") or "standard"))
        raise ValueError("budget overrides must use the campaign YAML schema")
    text = str(value or "standard").strip().lower()
    if text not in _PRESET_CAPS and text not in {"default", "smoke", "hard"}:
        raise ValueError("budget strings must be named profiles; use YAML for overrides")
    return budget_preset(text)


def _human_duration(seconds: int) -> str:
    if seconds % 3_600 == 0:
        return f"{seconds // 3_600}h"
    if seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"


def budget_to_user_mapping(
    budget: ExplorationBudget,
    *,
    delegated_stop_instruction: str = "",
) -> dict[str, Any]:
    caps = budget.hard_caps
    return {
        "schema": USER_BUDGET_SCHEMA,
        "preset": budget.preset.split("+", 1)[0],
        "budget": {
            "wall_clock": _human_duration(budget.wall_clock_s),
            "provider_calls": caps["provider_calls"],
            "agent_turns": caps["agent_turns"],
            "input_tokens": caps["input_tokens"],
            "output_tokens": caps["output_tokens"],
            "metered_api_usd": str(Decimal(caps["metered_usd_micros"]) / 1_000_000),
            "workbench_actions": caps["workbench_actions"],
            "adapter_forge_attempts": caps["adapter_forge_attempts"],
            "context": {
                "models": caps["context_models"],
                "truth_cells": caps["truth_cells"],
            },
            "boundary": {
                "queries": caps["boundary_queries"],
                "smt_calls": caps["smt_calls"],
                "smt_time": f'{caps["smt_millis"]}ms',
                "formal_peer_attempts": caps["formal_peer_attempts"],
                "formal_peer_time": f'{caps["formal_peer_millis"]}ms',
                "lean_attempts": caps["lean_attempts"],
                "lean_time": f'{caps["lean_millis"]}ms',
            },
        },
        "stop": {
            "max_finalists": budget.stop_rule.max_finalists,
            "low_yield_patience": budget.stop_rule.low_yield_patience,
            "min_marginal_information_per_cost": str(
                Decimal(budget.stop_rule.min_marginal_information_per_cost_ppm) / 1_000_000
            ),
            "coverage_target": str(Decimal(budget.stop_rule.coverage_target_ppm) / 1_000_000),
            "when": delegated_stop_instruction or None,
        },
        "allocation_policy": budget.allocation_policy,
        "model_transport": "subscription_agent_runtime",
    }


def render_budget_yaml(
    budget: ExplorationBudget,
    *,
    delegated_stop_instruction: str = "",
) -> str:
    return yaml.safe_dump(
        budget_to_user_mapping(
            budget,
            delegated_stop_instruction=delegated_stop_instruction,
        ),
        sort_keys=False,
        default_flow_style=False,
    )


def budget_from_user_mapping(
    value: Mapping[str, Any],
) -> tuple[ExplorationBudget, str]:
    if value.get("schema") not in {None, USER_BUDGET_SCHEMA}:
        raise ValueError("unsupported user exploration-budget schema")
    preset = str(value.get("preset") or "standard")
    base = budget_preset(preset)
    allocation_policy = str(
        value.get("allocation_policy") or "roll_forward_protected_future"
    )
    supplied_budget = value.get("budget")
    budget_row = {} if supplied_budget is None else supplied_budget
    stop_row = value.get("stop") or {}
    if not isinstance(budget_row, Mapping) or not isinstance(stop_row, Mapping):
        raise ValueError("campaign budget and stop overrides must be mappings")
    hard_caps = dict(base.hard_caps)
    wall = budget_row.get("wall_clock", _human_duration(base.wall_clock_s))
    wall_clock_s = max(1, _duration_millis(str(wall)) // 1_000)
    direct = {
        "provider_calls": "provider_calls",
        "agent_turns": "agent_turns",
        "input_tokens": "input_tokens",
        "output_tokens": "output_tokens",
        "workbench_actions": "workbench_actions",
        "adapter_forge_attempts": "adapter_forge_attempts",
    }
    for yaml_key, resource in direct.items():
        if yaml_key in budget_row:
            hard_caps[resource] = int(budget_row[yaml_key])
    if "metered_api_usd" in budget_row:
        hard_caps["metered_usd_micros"] = int(
            Decimal(str(budget_row["metered_api_usd"])) * 1_000_000
        )
    context = budget_row.get("context") or {}
    boundary = budget_row.get("boundary") or {}
    if not isinstance(context, Mapping) or not isinstance(boundary, Mapping):
        raise ValueError("budget context and boundary entries must be mappings")
    for yaml_key, resource in (("models", "context_models"), ("truth_cells", "truth_cells")):
        if yaml_key in context:
            hard_caps[resource] = int(context[yaml_key])
    for yaml_key, resource in (
        ("queries", "boundary_queries"),
        ("smt_calls", "smt_calls"),
        ("formal_peer_attempts", "formal_peer_attempts"),
        ("lean_attempts", "lean_attempts"),
    ):
        if yaml_key in boundary:
            hard_caps[resource] = int(boundary[yaml_key])
    for yaml_key, resource in (
        ("smt_time", "smt_millis"),
        ("formal_peer_time", "formal_peer_millis"),
        ("lean_time", "lean_millis"),
    ):
        if yaml_key in boundary:
            hard_caps[resource] = _duration_millis(str(boundary[yaml_key]))
    if any(item < 0 for item in hard_caps.values()):
        raise ValueError("user budget YAML cannot contain negative caps")
    stop = ScientificStopRule(
        max_finalists=int(stop_row.get("max_finalists", base.stop_rule.max_finalists)),
        low_yield_patience=int(stop_row.get("low_yield_patience", base.stop_rule.low_yield_patience)),
        min_marginal_information_per_cost_ppm=int(
            Decimal(str(stop_row.get("min_marginal_information_per_cost", "0.05"))) * 1_000_000
        ),
        coverage_target_ppm=int(
            Decimal(str(stop_row.get("coverage_target", "0.9"))) * 1_000_000
        ),
    )
    budget = ExplorationBudget(
        preset=f"{base.preset}+yaml",
        wall_clock_s=wall_clock_s,
        hard_caps=hard_caps,
        phase_caps=_default_phase_caps(hard_caps),
        stop_rule=stop,
        allocation_policy=allocation_policy,
    )
    return budget, str(stop_row.get("when") or "").strip()


def load_budget_yaml(text: str) -> tuple[ExplorationBudget, str]:
    parsed = yaml.safe_load(str(text))
    if not isinstance(parsed, Mapping):
        raise ValueError("exploration budget YAML must contain one mapping")
    return budget_from_user_mapping(parsed)


def compile_budget_preference(
    value: str | Mapping[str, Any] | ExplorationBudget | None,
    *,
    direction_text: str = "",
    compiler_fn: Callable[[str], Mapping[str, Any] | str] | None = None,
) -> tuple[ExplorationBudget, BudgetPreferenceCompilation]:
    """Validate campaign YAML or ask the injected campaign compiler to produce it."""
    if isinstance(value, ExplorationBudget):
        budget = value
        return budget, BudgetPreferenceCompilation(
            source_mode="typed",
            source_text="",
            recognized_preferences=({"kind": "typed_budget", "value": budget.digest},),
            delegated_stop_instruction="",
            budget_digest=budget.digest,
        )
    if isinstance(value, Mapping):
        preference = value.get("preference") or value.get("budget_preference")
        if isinstance(preference, str):
            return compile_budget_preference(
                preference,
                direction_text=direction_text,
                compiler_fn=compiler_fn,
            )
        if "budget" in value:
            budget, delegated = budget_from_user_mapping(value)
        else:
            budget, delegated = parse_exploration_budget(value), ""
        return budget, BudgetPreferenceCompilation(
            source_mode="campaign_yaml" if "budget" in value else "typed",
            source_text=json.dumps(dict(value), sort_keys=True),
            recognized_preferences=({"kind": "campaign_budget", "value": budget.digest},),
            delegated_stop_instruction=delegated,
            budget_digest=budget.digest,
        )

    explicit_source = str(value or "").strip()
    source = explicit_source or (str(direction_text or "").strip() if compiler_fn is not None else "")
    if not source:
        budget = budget_preset("standard")
        return budget, BudgetPreferenceCompilation(
            source_mode="default_profile",
            source_text="",
            recognized_preferences=({"kind": "profile", "value": "standard"},),
            delegated_stop_instruction="",
            budget_digest=budget.digest,
        )
    lowered = source.lower()
    if lowered in _PRESET_CAPS or lowered in {"default", "smoke", "hard"}:
        budget = parse_exploration_budget(source)
        return budget, BudgetPreferenceCompilation(
            source_mode="preset",
            source_text=source,
            recognized_preferences=({"kind": "profile", "value": budget.preset},),
            delegated_stop_instruction="",
            budget_digest=budget.digest,
        )
    try:
        parsed_yaml = yaml.safe_load(source)
    except yaml.YAMLError:
        parsed_yaml = None
    if isinstance(parsed_yaml, Mapping) and "budget" in parsed_yaml:
        budget, delegated = budget_from_user_mapping(parsed_yaml)
        source_mode = "campaign_yaml"
    else:
        if compiler_fn is None:
            raise ValueError(
                "natural-language campaign budgets require an injected budget compiler"
            )
        compiled = compiler_fn(source)
        if isinstance(compiled, str):
            budget, delegated = load_budget_yaml(compiled)
        elif isinstance(compiled, Mapping):
            budget, delegated = budget_from_user_mapping(compiled)
        else:
            raise ValueError("budget compiler returned neither YAML nor a mapping")
        source_mode = "compiled_campaign_yaml"
    return budget, BudgetPreferenceCompilation(
        source_mode=source_mode,
        source_text=source,
        recognized_preferences=({"kind": "campaign_budget", "value": budget.digest},),
        delegated_stop_instruction=delegated,
        budget_digest=budget.digest,
    )


class BudgetExceeded(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class BudgetReservation:
    reservation_id: str
    action_id: str
    phase: str
    resources: Mapping[str, int]


@dataclass(frozen=True)
class BudgetStopReceipt:
    reason: str
    budget_digest: str
    elapsed_ms: int
    usage: Mapping[str, int]
    phase_usage: Mapping[str, Mapping[str, int]]
    outstanding_reservations: tuple[Mapping[str, Any], ...]
    attempt_id: str
    context_hash: str = ""
    last_information_observation: Mapping[str, Any] | None = None
    schema: str = STOP_RECEIPT_SCHEMA

    def to_json(self) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "reason": self.reason,
            "budget_digest": self.budget_digest,
            "elapsed_ms": self.elapsed_ms,
            "usage": dict(self.usage),
            "phase_usage": {key: dict(value) for key, value in self.phase_usage.items()},
            "outstanding_reservations": [dict(row) for row in self.outstanding_reservations],
            "attempt_id": self.attempt_id,
            "context_hash": self.context_hash,
            "last_information_observation": (
                dict(self.last_information_observation)
                if self.last_information_observation is not None else None
            ),
        }
        return {**core, "receipt_sha256": content_hash(core)}


class ExplorationBudgetLedger:
    """Append-only reservation ledger. The host is the only writer."""

    def __init__(
        self,
        path: str | Path,
        budget: ExplorationBudget,
        *,
        attempt_id: str,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        self.path = Path(path)
        self.budget = budget
        self.attempt_id = str(attempt_id)
        self._clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        rows = self._rows()
        if rows:
            started = rows[0]
            if started.get("event_type") != "budget_started" or started.get("budget_digest") != budget.digest:
                raise ValueError("budget ledger does not match the supplied budget")
            if started.get("attempt_id") != self.attempt_id:
                raise ValueError("budget ledger attempt mismatch")
            self.started_at_ms = int(started["at_ms"])
        else:
            self.started_at_ms = self._clock_ms()
            self._append(
                "budget_started",
                budget_digest=budget.digest,
                budget=budget.to_json(),
                attempt_id=self.attempt_id,
            )

    def _rows(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(errors="ignore").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
        return rows

    def _append(self, event_type: str, **payload: Any) -> dict[str, Any]:
        core = {
            "schema": BUDGET_EVENT_SCHEMA,
            "event_type": event_type,
            "at_ms": self._clock_ms(),
            **payload,
        }
        row = {**core, "event_sha256": content_hash(core)}
        if not append_jsonl_locked(self.path, row, ensure_ascii=True):
            if not self.path.is_file():
                raise OSError("budget ledger append failed")
        return row

    @staticmethod
    def _validated_resources(resources: Mapping[str, int]) -> dict[str, int]:
        values = {str(key): int(value) for key, value in resources.items() if int(value) != 0}
        if set(values) - RESOURCE_KINDS or any(value < 0 for value in values.values()):
            raise ValueError("invalid budget reservation resources")
        return values

    def elapsed_ms(self) -> int:
        for row in reversed(self._rows()):
            event_type = row.get("event_type")
            if event_type == "wall_clock_frozen":
                return max(0, int(row["elapsed_ms"]))
            if event_type == "wall_clock_resumed":
                return max(
                    0,
                    int(row["elapsed_before_resume_ms"])
                    + self._clock_ms()
                    - int(row["at_ms"]),
                )
        return max(0, self._clock_ms() - self.started_at_ms)

    def wall_clock_cap_s(self) -> int:
        """Return the campaign cap including explicit, receipted extensions."""

        extension_s = sum(
            int(row.get("extra_s", 0))
            for row in self._rows()
            if row.get("event_type") == "wall_clock_extended"
        )
        return self.budget.wall_clock_s + extension_s

    def resource_cap(self, resource: str) -> int:
        if resource not in RESOURCE_KINDS:
            raise ValueError(f"unknown exploration resource: {resource}")
        extra = sum(
            int(dict(row.get("resources") or {}).get(resource, 0))
            for row in self._rows()
            if row.get("event_type") == "resources_extended"
        )
        return int(self.budget.hard_caps[resource]) + extra

    def phase_cap(self, phase: str, resource: str) -> int:
        if phase not in PHASES or resource not in RESOURCE_KINDS:
            raise ValueError("unknown exploration phase or resource")
        extra = sum(
            int(dict(row.get("resources") or {}).get(resource, 0))
            for row in self._rows()
            if row.get("event_type") == "resources_extended"
            and row.get("phase") == phase
        )
        return int(self.budget.phase_caps[phase][resource]) + extra

    def extend_resources(
        self,
        *,
        phase: str,
        resources: Mapping[str, int],
        authority_ref: str,
        reason: str,
    ) -> dict[str, int]:
        values = self._validated_resources(resources)
        if phase not in PHASES or not values:
            raise ValueError("resource extension requires a phase and resources")
        if not str(authority_ref).strip() or not str(reason).strip():
            raise ValueError("resource extension requires authority and reason")
        self._append(
            "resources_extended",
            budget_digest=self.budget.digest,
            attempt_id=self.attempt_id,
            phase=phase,
            resources=values,
            authority_ref=str(authority_ref),
            reason=str(reason),
        )
        return {key: self.resource_cap(key) for key in values}

    def extend_wall_clock(
        self, *, extra_s: int, authority_ref: str, reason: str
    ) -> int:
        """Extend only the wall-clock cap; all resource caps stay frozen."""

        if type(extra_s) is not int or extra_s < 1:
            raise ValueError("wall-clock extension must be a positive integer")
        if not str(authority_ref).strip():
            raise ValueError("wall-clock extension requires an authority reference")
        if not str(reason).strip():
            raise ValueError("wall-clock extension requires a reason")
        self._append(
            "wall_clock_extended",
            budget_digest=self.budget.digest,
            attempt_id=self.attempt_id,
            extra_s=extra_s,
            authority_ref=str(authority_ref),
            reason=str(reason),
            cap_s=self.wall_clock_cap_s() + extra_s,
        )
        return self.wall_clock_cap_s()

    def freeze_wall_clock(self, *, reason: str) -> int:
        """Stop charging wall time while an attempt has no owned runner."""

        rows = self._rows()
        if rows and rows[-1].get("event_type") == "wall_clock_frozen":
            return int(rows[-1]["elapsed_ms"])
        elapsed = self.elapsed_ms()
        self._append(
            "wall_clock_frozen",
            budget_digest=self.budget.digest,
            attempt_id=self.attempt_id,
            elapsed_ms=elapsed,
            reason=str(reason),
        )
        return elapsed

    def recover_interrupted_wall_clock(self) -> int:
        """Freeze an interrupted active interval at its last durable event."""

        rows = self._rows()
        wall_event = next(
            (
                row
                for row in reversed(rows)
                if row.get("event_type")
                in {"wall_clock_frozen", "wall_clock_resumed"}
            ),
            None,
        )
        if wall_event is not None and wall_event["event_type"] == "wall_clock_frozen":
            return int(wall_event["elapsed_ms"])
        last_at_ms = int(rows[-1]["at_ms"]) if rows else self.started_at_ms
        elapsed = (
            int(wall_event["elapsed_before_resume_ms"])
            + max(0, last_at_ms - int(wall_event["at_ms"]))
            if wall_event is not None
            else max(0, last_at_ms - self.started_at_ms)
        )
        self._append(
            "wall_clock_frozen",
            budget_digest=self.budget.digest,
            attempt_id=self.attempt_id,
            elapsed_ms=elapsed,
            reason="interrupted_runner_recovery",
        )
        return elapsed

    def recover_interrupted_reservations(self) -> int:
        """Conservatively charge reservations orphaned by a prior runner."""

        outstanding = tuple(self.state()["reservations"].values())
        for row in outstanding:
            self._append(
                "reservation_committed",
                budget_digest=self.budget.digest,
                attempt_id=self.attempt_id,
                reservation_id=str(row["reservation_id"]),
                actual_resources=dict(row.get("resources") or {}),
                recovery_reason="interrupted_runner_conservative_charge",
            )
        return len(outstanding)

    def resume_wall_clock(self) -> int:
        """Resume charging from the last frozen active-runtime total."""

        rows = self._rows()
        if rows and rows[-1].get("event_type") == "wall_clock_resumed":
            return self.elapsed_ms()
        elapsed = self.elapsed_ms()
        self._append(
            "wall_clock_resumed",
            budget_digest=self.budget.digest,
            attempt_id=self.attempt_id,
            elapsed_before_resume_ms=elapsed,
        )
        return elapsed

    def state(self) -> dict[str, Any]:
        usage = {key: 0 for key in RESOURCE_KINDS}
        phase_usage = {phase: {key: 0 for key in RESOURCE_KINDS} for phase in PHASES}
        reservations: dict[str, dict[str, Any]] = {}
        information: list[dict[str, Any]] = []
        user_stop = False
        for row in self._rows():
            event_type = row.get("event_type")
            if event_type == "resources_reserved":
                reservations[str(row["reservation_id"])] = row
            elif event_type in {"reservation_committed", "reservation_released"}:
                reservation = reservations.pop(str(row["reservation_id"]), None)
                if event_type == "reservation_committed" and reservation is not None:
                    phase = str(reservation["phase"])
                    for key, value in dict(row.get("actual_resources") or {}).items():
                        usage[str(key)] += int(value)
                        phase_usage[phase][str(key)] += int(value)
            elif event_type == "information_observed":
                information.append(row)
            elif event_type in {"user_stop_requested", "operator_stop_requested"}:
                user_stop = True
        return {
            "usage": usage,
            "phase_usage": phase_usage,
            "reservations": reservations,
            "information": information,
            "user_stop": user_stop,
            "operator_stop": user_stop,
            "wall_clock_cap_s": self.wall_clock_cap_s(),
        }

    def _admission_failure(self, phase: str, resources: Mapping[str, int]) -> str | None:
        if phase not in PHASES:
            raise ValueError(f"unknown exploration phase: {phase!r}")
        if self.elapsed_ms() >= self.wall_clock_cap_s() * 1_000:
            return "hard_cap_reached:wall_clock_s"
        state = self.state()
        if state["user_stop"]:
            return "user_stop"
        reserved_total = {key: 0 for key in RESOURCE_KINDS}
        phase_index = PHASES.index(phase)
        active_phases = PHASES[: phase_index + 1]
        reserved_phase = {key: 0 for key in RESOURCE_KINDS}
        reserved_active = {key: 0 for key in RESOURCE_KINDS}
        for row in state["reservations"].values():
            for key, value in dict(row["resources"]).items():
                reserved_total[str(key)] += int(value)
                if row["phase"] == phase:
                    reserved_phase[str(key)] += int(value)
                if row["phase"] in active_phases:
                    reserved_active[str(key)] += int(value)
        for key, value in resources.items():
            if state["usage"][key] + reserved_total[key] + value > self.resource_cap(key):
                return f"blocked_before_action:{key}"
            if self.budget.allocation_policy == "global_cap":
                continue
            if self.budget.allocation_policy == "strict_phase_caps":
                if (
                    state["phase_usage"][phase][key] + reserved_phase[key] + value
                    > self.phase_cap(phase, key)
                ):
                    return f"blocked_before_action:{phase}:{key}"
                continue
            cumulative_cap = sum(
                self.phase_cap(item, key) for item in active_phases
            )
            # AdapterForge is the only consumer of the expansion agent slice.
            # When the frozen campaign disables forge attempts, that slice is
            # unreachable and may roll into earlier exploration without
            # weakening the still-reachable boundary or interpretation caps.
            if (
                phase_index < PHASES.index("expansion")
                and key in _EXPANSION_AGENT_RESOURCES
                and self.budget.hard_caps["adapter_forge_attempts"] == 0
            ):
                cumulative_cap += self.budget.phase_caps["expansion"][key]
                if key in _BOUNDARY_CALL_RESOURCES:
                    boundary_cap = self.budget.phase_caps["boundary"][key]
                    protected_boundary = min(
                        boundary_cap,
                        self.budget.hard_caps["lean_attempts"],
                    )
                    cumulative_cap += boundary_cap - protected_boundary
            cumulative_usage = sum(
                state["phase_usage"][item][key] for item in active_phases
            )
            if (
                cumulative_usage + reserved_active[key] + value
                > cumulative_cap
            ):
                return f"blocked_before_action:{phase}:{key}"
        return None

    def remaining_capacity(self, phase: str, resource: str) -> int:
        """Return exact immediately admissible units without reserving them."""

        if resource not in RESOURCE_KINDS:
            raise ValueError(f"unknown budget resource: {resource!r}")
        state = self.state()
        reserved = sum(
            int(dict(row.get("resources") or {}).get(resource, 0))
            for row in state["reservations"].values()
        )
        high = max(
            0,
            self.resource_cap(resource)
            - state["usage"][resource]
            - reserved,
        )
        low = 0
        while low < high:
            middle = (low + high + 1) // 2
            if self._admission_failure(phase, {resource: middle}) is None:
                low = middle
            else:
                high = middle - 1
        return low

    def reserve(self, action_id: str, phase: str, resources: Mapping[str, int]) -> BudgetReservation:
        requested = self._validated_resources(resources)
        failure = self._admission_failure(phase, requested)
        if failure is not None:
            raise BudgetExceeded(failure)
        reservation = BudgetReservation(
            reservation_id="reservation:" + uuid.uuid4().hex,
            action_id=str(action_id),
            phase=phase,
            resources=requested,
        )
        self._append(
            "resources_reserved",
            budget_digest=self.budget.digest,
            attempt_id=self.attempt_id,
            reservation_id=reservation.reservation_id,
            action_id=reservation.action_id,
            phase=reservation.phase,
            resources=dict(reservation.resources),
        )
        return reservation

    def commit(self, reservation: BudgetReservation, actual_resources: Mapping[str, int] | None = None) -> None:
        actual = self._validated_resources(actual_resources or reservation.resources)
        for key, value in actual.items():
            if value > int(reservation.resources.get(key, 0)):
                raise ValueError(f"actual {key} exceeds its host reservation")
        self._append(
            "reservation_committed",
            budget_digest=self.budget.digest,
            attempt_id=self.attempt_id,
            reservation_id=reservation.reservation_id,
            actual_resources=actual,
        )

    def release(self, reservation: BudgetReservation, *, reason: str) -> None:
        self._append(
            "reservation_released",
            budget_digest=self.budget.digest,
            attempt_id=self.attempt_id,
            reservation_id=reservation.reservation_id,
            reason=str(reason),
        )

    def observe_information(
        self,
        *,
        action_id: str,
        marginal_information_per_cost_ppm: int,
        coverage_ppm: int,
        evidence_refs: Sequence[str] = (),
        loop_control_action: str = "",
    ) -> None:
        if not 0 <= marginal_information_per_cost_ppm <= 1_000_000:
            raise ValueError("marginal information ratio must be parts per million")
        if not 0 <= coverage_ppm <= 1_000_000:
            raise ValueError("coverage ratio must be parts per million")
        self._append(
            "information_observed",
            budget_digest=self.budget.digest,
            attempt_id=self.attempt_id,
            action_id=str(action_id),
            marginal_information_per_cost_ppm=int(marginal_information_per_cost_ppm),
            coverage_ppm=int(coverage_ppm),
            evidence_refs=[str(row) for row in evidence_refs],
            loop_control_action=str(loop_control_action),
        )

    def request_user_stop(self, *, authority_ref: str) -> None:
        self._append(
            "user_stop_requested",
            budget_digest=self.budget.digest,
            attempt_id=self.attempt_id,
            authority_ref=str(authority_ref),
        )

    def request_operator_stop(self, *, authority_ref: str) -> None:
        """Compatibility alias for pre-unification callers."""
        self.request_user_stop(authority_ref=authority_ref)

    def soft_stop_reason(
        self,
        *,
        information_start_index: int = 0,
        allow_coverage_target: bool = True,
    ) -> str | None:
        """Evaluate scientific stopping over one loop's information window.

        Hard ceilings and user stop remain campaign-wide. Nested independent
        search lanes may start a fresh soft-stop window without receiving a new
        resource ledger or evading any shared cap.
        """

        if information_start_index < 0:
            raise ValueError("information start index must be nonnegative")
        state = self.state()
        if state["user_stop"]:
            return "user_stop"
        if self.elapsed_ms() >= self.wall_clock_cap_s() * 1_000:
            return "hard_cap_reached:wall_clock_s"
        information = state["information"][information_start_index:]
        if (
            allow_coverage_target
            and information
            and int(information[-1]["coverage_ppm"])
            >= self.budget.stop_rule.coverage_target_ppm
        ):
            return "target_reached"
        control_rows = [
            row for row in information if str(row.get("loop_control_action") or "")
        ]
        if control_rows:
            if control_rows[-1]["loop_control_action"] in {
                "PIVOT_REQUIRED", "UNDERIDENTIFIED"
            }:
                return "marginal_yield_below_threshold"
        else:
            threshold = self.budget.stop_rule.min_marginal_information_per_cost_ppm
            patience = self.budget.stop_rule.low_yield_patience
            tail = information[-patience:]
            if len(tail) == patience and all(
                int(row["marginal_information_per_cost_ppm"]) < threshold for row in tail
            ):
                return "marginal_yield_below_threshold"
        return None

    def stop_receipt(self, reason: str, *, context_hash: str = "") -> BudgetStopReceipt:
        state = self.state()
        outstanding = tuple(
            {
                "reservation_id": row["reservation_id"],
                "action_id": row["action_id"],
                "phase": row["phase"],
                "resources": dict(row["resources"]),
            }
            for row in state["reservations"].values()
        )
        last = state["information"][-1] if state["information"] else None
        receipt = BudgetStopReceipt(
            reason=str(reason),
            budget_digest=self.budget.digest,
            elapsed_ms=self.elapsed_ms(),
            usage=state["usage"],
            phase_usage=state["phase_usage"],
            outstanding_reservations=outstanding,
            attempt_id=self.attempt_id,
            context_hash=str(context_hash),
            last_information_observation=last,
        )
        self._append(
            "budget_stopped",
            budget_digest=self.budget.digest,
            attempt_id=self.attempt_id,
            receipt=receipt.to_json(),
        )
        return receipt


__all__ = [
    "BUDGET_SCHEMA", "PHASES", "RESOURCE_KINDS", "BudgetExceeded",
    "BudgetPreferenceCompilation", "BudgetReservation", "BudgetStopReceipt", "ExplorationBudget",
    "ExplorationBudgetLedger", "ScientificStopRule", "budget_preset",
    "budget_from_user_mapping", "budget_to_user_mapping", "compile_budget_preference",
    "load_budget_yaml", "parse_exploration_budget", "render_budget_yaml",
]
