"""GP-157 v5.0 Gap #5 — Phase 1/2 immutable handoff.

Per panel Failure Mode 3 (DAG Phase Contamination): if Phase 1
(Formulation/Fitting) and Phase 2 (Falsification) share mutable state,
the loop generates spurious score drops. The fix is a frozen handoff
object: Phase 1 returns `FrozenFittedModel`; Phase 2 gates accept it
as read-only. Any attempted mutation raises FrozenInstanceError.

This is a TYPE SAFETY guarantee, not a runtime gate. Phase 2 gates
that try to alter MODEL_PARAMS or rewrite I_model fail at construction
time, not silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class FrozenFittedModel:
    """Immutable Phase 1 → Phase 2 handoff.

    Phase 1 (FitInstrument router):
      - Selects adapter via `select_adapter(substrate, candidate)`.
      - Runs `engine.fit(declaration, evidence, **kwargs)`.
      - Wraps the result in `FrozenFittedModel.from_fit_success(...)`.

    Phase 2 (gate harness, holdout, asymptotic discipline, etc.):
      - Receive `FrozenFittedModel` as `Final[FrozenFittedModel]`.
      - Read `.I_model`, `.fitted_params`, `.expression_str`.
      - MUST NOT modify any field. Frozen dataclass enforces.

    Mutable nested mappings are wrapped in `MappingProxyType` so even
    runtime mutation attempts raise TypeError.
    """

    I_model: Callable[..., float]
    """The fitted, locked callable. Phase 2 calls this — never reconstructs."""

    fitted_params: Mapping[str, float]
    """Read-only view of MODEL_PARAMS post-fit. MappingProxyType wrapped."""

    expression_str: str = ""
    """Symbolic form e.g. 'a / (x + b)'. Free-form for diagnostics."""

    abi_name: str = ""
    """The SubstrateABI.name this model was built for (e.g. 'SCALAR_1D')."""

    convergence_classification: str = ""
    """e.g. 'converged' / 'partial' / 'failed'. Free-form."""

    extras: Mapping[str, Any] = field(default_factory=dict)
    """Frozen forward-compat slot. Wrap mutable contents in MappingProxyType."""

    @classmethod
    def from_components(
        cls,
        I_model: Callable[..., float],
        fitted_params: Mapping[str, float],
        *,
        expression_str: str = "",
        abi_name: str = "",
        convergence_classification: str = "",
        extras: Mapping[str, Any] | None = None,
    ) -> "FrozenFittedModel":
        """Construct with mappings wrapped read-only.

        Use this factory rather than the raw constructor so callers
        can pass plain dicts and get the immutable view automatically.
        """
        return cls(
            I_model=I_model,
            fitted_params=MappingProxyType(dict(fitted_params)),
            expression_str=expression_str,
            abi_name=abi_name,
            convergence_classification=convergence_classification,
            extras=MappingProxyType(dict(extras or {})),
        )
