"""Static, reviewable adapter registry for frontier theory campaigns."""
from __future__ import annotations

import importlib
from typing import Any, Mapping

from ztare.leanmill.theory_ir import content_hash

from ztare.common.task_discharge import (
    TaskDischargeContract,
    TaskDischargeReceipt,
    adjudicate_task_discharge,
)

_ADAPTERS = {
    "binary_linear_code.v1": "ztare.leanmill.adapters.binary_linear_code",
    "rational_polynomial_map.v1": (
        "ztare.leanmill.adapters.rational_polynomial_map"
    ),
    "generic_fol_finite.v1": "ztare.leanmill.adapters.generic_fol_finite",
    "magma_equational.v1": "ztare.leanmill.adapters.magma_equational",
    "finite_deterministic_protocol.v1": "ztare.leanmill.adapters.finite_protocol",
    "generic_finite_evidence.v1": "ztare.leanmill.adapters.generic_finite_evidence",
}


def registered_theory_adapter_ids() -> tuple[str, ...]:
    return tuple(sorted(_ADAPTERS))


def resolve_theory_adapter_module(adapter_id: str) -> Any:
    try:
        module_name = _ADAPTERS[str(adapter_id)]
    except KeyError as exc:
        raise ValueError(f"unregistered theory adapter: {adapter_id!r}") from exc
    return importlib.import_module(module_name)


def materialize_theory_adapter_capability(
    adapter_id: str,
    capability: str,
    **kwargs: Any,
) -> Any:
    """Invoke one reviewed adapter property without turning it into adapter identity."""

    module = resolve_theory_adapter_module(adapter_id)
    capabilities = getattr(module, "CAPABILITIES", None)
    factory = capabilities.get(str(capability)) if isinstance(capabilities, Mapping) else None
    if not callable(factory):
        raise ValueError(
            f"adapter {adapter_id!r} lacks capability {str(capability)!r}"
        )
    return factory(**kwargs)


def theory_adapter_capabilities(adapter_id: str) -> tuple[str, ...]:
    module = resolve_theory_adapter_module(adapter_id)
    capabilities = getattr(module, "CAPABILITIES", None)
    if capabilities is None:
        return ()
    if not isinstance(capabilities, Mapping) or any(
        not isinstance(key, str) or not callable(value)
        for key, value in capabilities.items()
    ):
        raise ValueError(f"adapter {adapter_id!r} has an invalid capability registry")
    return tuple(sorted(capabilities))


def theory_adapter_capability_contract(
    adapter_id: str, capability_id: str
) -> dict[str, Any]:
    """Return immutable role/contract metadata for one executable capability."""

    module = resolve_theory_adapter_module(adapter_id)
    metadata = getattr(module, "CAPABILITY_CONTRACTS", None)
    raw = metadata.get(str(capability_id)) if isinstance(metadata, Mapping) else None
    if not isinstance(raw, Mapping) or set(raw) != {
        "role", "contract", "contract_sha256",
    }:
        raise ValueError(
            f"adapter {adapter_id!r} capability {capability_id!r} lacks "
            "reviewed role metadata"
        )
    role = str(raw.get("role") or "")
    contract = raw.get("contract")
    if (
        not role
        or not isinstance(contract, Mapping)
        or not contract
        or raw.get("contract_sha256") != content_hash(contract)
    ):
        raise ValueError(
            f"adapter {adapter_id!r} capability {capability_id!r} has "
            "invalid role metadata"
        )
    return {
        "role": role,
        "contract": dict(contract),
        "contract_sha256": str(raw["contract_sha256"]),
    }


def theory_task_capability_catalog(
    adapter_id: str,
    *,
    adapter_config: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return reviewed task IDs leaves may name without guessing vocabulary."""

    module = resolve_theory_adapter_module(adapter_id)
    config = dict(adapter_config or {})
    factory = getattr(module, "theory_task_capabilities", None)
    rows = (
        factory(adapter_config=config)
        if callable(factory)
        else getattr(module, "THEORY_TASK_CAPABILITIES", ())
    )
    if not isinstance(rows, (list, tuple)):
        raise ValueError(f"adapter {adapter_id!r} has an invalid task capability catalog")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    required = {"capability_id", "purpose", "use_when"}
    for raw in rows:
        if not isinstance(raw, Mapping) or frozenset(raw) not in {
            frozenset(required),
            frozenset(required | {"interface"}),
        }:
            raise ValueError(
                f"adapter {adapter_id!r} has a malformed task capability row"
            )
        row = {key: str(raw[key]).strip() for key in sorted(required)}
        capability_id = row["capability_id"]
        if not all(row.values()) or capability_id in seen:
            raise ValueError(
                f"adapter {adapter_id!r} has a duplicate or empty task capability"
            )
        if "interface" in raw:
            from ztare.leanmill.witness_construction_boundary import (
                GOVERNED_WITNESS_CONSTRUCTION_CAPABILITY,
                validate_witness_construction_interface,
            )

            if capability_id != GOVERNED_WITNESS_CONSTRUCTION_CAPABILITY:
                raise ValueError(
                    f"adapter {adapter_id!r} attached a construction interface "
                    "to another task capability"
                )
            row["interface"] = validate_witness_construction_interface(
                raw["interface"]
            )
            if callable(factory):
                from ztare.leanmill.theory_ir import content_hash

                if row["interface"]["target_config_sha256"] != content_hash(
                    config
                ):
                    raise ValueError(
                        f"adapter {adapter_id!r} construction interface crossed "
                        "its frozen adapter configuration"
                    )
        seen.add(capability_id)
        normalized.append(row)
    return tuple(sorted(normalized, key=lambda row: row["capability_id"]))


class _RegisteredTheoryTaskAdjudicator:
    """Present one reviewed module capability through the common adapter door."""

    def __init__(self, adapter_id: str, kwargs: Mapping[str, Any]) -> None:
        self.adapter_id = str(adapter_id)
        self.kwargs = dict(kwargs)

    def adjudicate_task_discharge(
        self, contract: TaskDischargeContract
    ) -> TaskDischargeReceipt | Mapping[str, Any]:
        if "task_discharge_adjudicator" not in theory_adapter_capabilities(
            self.adapter_id
        ):
            reason = "adapter_capability_unavailable"
        else:
            try:
                return materialize_theory_adapter_capability(
                    self.adapter_id,
                    "task_discharge_adjudicator",
                    contract=contract,
                    **self.kwargs,
                )
            except KeyError:
                reason = "adjudicator_unavailable"
        return TaskDischargeReceipt(
            contract_sha256=contract.sha256,
            adjudicator_id=contract.adjudicator_id,
            status="unavailable",
            authority="leanmill.theory_adapter_registry",
            observed={"reason": reason, "adapter_id": self.adapter_id},
        )


def adjudicate_theory_adapter_task(
    adapter_id: str,
    contract: TaskDischargeContract,
    **kwargs: Any,
) -> TaskDischargeReceipt:
    """Resolve a registered theory adjudicator and verify its receipt identity."""

    return adjudicate_task_discharge(
        _RegisteredTheoryTaskAdjudicator(adapter_id, kwargs),
        contract,
    )


def load_model_universe(value: Mapping[str, Any]) -> Any:
    adapter_id = str(value.get("adapter_id") or "")
    module = resolve_theory_adapter_module(adapter_id)
    loader = getattr(module, "load_model_universe", None)
    if not callable(loader):
        raise ValueError(f"adapter {adapter_id!r} cannot load a model universe snapshot")
    return loader(value)


def preflight_theory_adapter(
    adapter_id: str,
    signature: Any,
    *,
    adapter_config: Mapping[str, Any],
    formula_grammar: Mapping[str, Any],
    strata: tuple[Mapping[str, Any], ...],
) -> dict[str, Any]:
    module = resolve_theory_adapter_module(adapter_id)
    preflight = getattr(module, "preflight_blueprint", None)
    if not callable(preflight):
        raise ValueError(f"adapter {adapter_id!r} has no frontier-blueprint preflight")
    result = preflight(
        signature,
        adapter_config=adapter_config,
        formula_grammar=formula_grammar,
        strata=strata,
    )
    if not isinstance(result, dict) or result.get("complete_census_available") is not True:
        raise ValueError("adapter preflight did not establish executable complete semantics")
    return result


__all__ = [
    "adjudicate_theory_adapter_task", "load_model_universe",
    "registered_theory_adapter_ids",
    "materialize_theory_adapter_capability", "preflight_theory_adapter",
    "resolve_theory_adapter_module", "theory_adapter_capabilities",
    "theory_adapter_capability_contract",
    "theory_task_capability_catalog",
]
