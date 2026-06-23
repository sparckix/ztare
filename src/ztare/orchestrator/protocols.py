"""GP-157 v5.0 Layer 1 — runtime-checkable PEP 544 Protocols.

Per panel synthesis: the apparatus types its own consumption
of the mutator's test_model.py via Protocols, NOT the other way. Mutator
emits free Python; apparatus calls `adapt(module, spec)` once at the
boundary, raises `ContractError` on mismatch, returns a typed callable
for downstream use. One adapter, one Protocol, one error class.

Pairs with `contract_table.py` (the ABI registry) and
`render_evidence_template.py` (evidence.txt §D rendering).
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Mapping, Optional, Protocol, runtime_checkable

from ztare.orchestrator.contract_table import ContractSpec, SubstrateABI


# ── Protocols ─────────────────────────────────────────────────────────────


@runtime_checkable
class ScalarModel(Protocol):
    """Contract C: `I_model(d, params=None) -> float`."""

    def __call__(
        self,
        d: float,
        params: Optional[Mapping[str, float]] = None,
    ) -> float: ...


@runtime_checkable
class FeatureModel(Protocol):
    """Contract B: `I_model(features) -> float`."""

    def __call__(self, features: Mapping[str, Any]) -> float: ...


# ── Errors ────────────────────────────────────────────────────────────────


class ContractError(Exception):
    """Raised when a mutator submission violates the active ContractSpec.

    Attributes:
      code         — short canonical code (one of CONTRACT_ERROR_CODES).
      spec         — the ContractSpec that was being enforced.
      observed     — what was observed (e.g. inspect.Signature or repr).
      remediation  — short string instructing the mutator how to comply.

    Caller decides whether to translate to an R1 strike (free retry) or
    a hard fail. The error class itself is uniform.
    """

    def __init__(
        self,
        code: str,
        spec: ContractSpec,
        *,
        observed: Any = None,
        remediation: str = "",
    ) -> None:
        self.code = code
        self.spec = spec
        self.observed = observed
        self.remediation = remediation
        msg = (
            f"ContractError[{code}] for ABI={spec.abi.name}: "
            f"observed={observed!r}; remediation={remediation!r}"
        )
        super().__init__(msg)


CONTRACT_ERROR_CODES: frozenset[str] = frozenset({
    "MISSING_IMODEL",
    "WRONG_SIGNATURE",
    "MISSING_MODULE_GLOBAL",
    "FORBIDDEN_MODULE_PATTERN",
    "MISSING_FILESYSTEM_CAP",
    "RUNTIME_NAN_RETURN",
    "RUNTIME_RAISES",
    "RUNTIME_IMPORT_FAILURE",
})


# ── Adapter ───────────────────────────────────────────────────────────────


def _signature_matches(observed: inspect.Signature, abi: SubstrateABI) -> bool:
    """Lightweight signature-shape check.

    Strict isinstance against Protocol requires runtime_checkable + a real
    callable; we want to validate BEFORE running. Heuristic match by
    parameter name + count is sufficient for the gp159-class divergence
    detection (`features` vs `d` swap).
    """
    params = list(observed.parameters.values())
    # Drop *args/**kwargs/keyword-only sentinels
    real_params = [p for p in params if p.kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.POSITIONAL_ONLY,
    )]
    if not real_params:
        return False
    first_name = real_params[0].name.strip().lower()

    if abi == SubstrateABI.SCALAR_1D:
        # First arg should be `d` or `x` (scalar). Reject `features`.
        return first_name in {"d", "x"} and first_name != "features"
    if abi == SubstrateABI.FEATURE_DICT:
        # First arg should be `features` (dict). Reject scalars.
        return first_name in {"features", "row", "feature_dict"}
    # Discriminator / Lean ABIs do not have an I_model contract
    return True


def adapt(module: Any, spec: ContractSpec) -> Callable[..., float]:
    """Validate a freshly-imported test_model module against `spec`.

    Returns the typed `I_model` callable on success. Raises ContractError
    with one canonical code on any boundary violation. Caller is the
    apparatus (autoresearch_loop / gate_harness); the mutator never sees
    this function — it sees the rendered evidence template + Protocol-
    derived hint.

    Validation order:
      1. Required module globals present (MODEL_PARAMS, VISIBLE_SET, ...).
      2. Forbidden module patterns absent (handled by AST-level check
         elsewhere; this function checks the imported module's namespace).
      3. I_model exists and is callable.
      4. I_model signature matches spec.

    Runtime-result checks (NaN return, raises) live in
    `contract_adherence.runtime_check_imodel` — adapt() does NOT call
    I_model; it only validates the boundary.
    """
    # 1. Required globals
    for name in spec.required_module_globals:
        if not hasattr(module, name):
            raise ContractError(
                "MISSING_MODULE_GLOBAL",
                spec,
                observed=f"module missing `{name}`",
                remediation=(
                    f"Add `{name}` at module scope in test_model.py. "
                    f"Required by ABI {spec.abi.name}."
                ),
            )

    # 3. I_model callable (skip ABIs that don't require it)
    if "I_model" in spec.required_module_globals:
        I_model = getattr(module, "I_model", None)
        if I_model is None or not callable(I_model):
            raise ContractError(
                "MISSING_IMODEL",
                spec,
                observed=f"I_model={I_model!r}",
                remediation=(
                    f"test_model.py must define a callable I_model with signature "
                    f"`{spec.signature_str}`."
                ),
            )

        # 4. Signature shape
        try:
            observed_sig = inspect.signature(I_model)
        except (ValueError, TypeError) as exc:
            raise ContractError(
                "WRONG_SIGNATURE",
                spec,
                observed=str(exc),
                remediation=f"I_model must have signature `{spec.signature_str}`.",
            )
        if not _signature_matches(observed_sig, spec.abi):
            raise ContractError(
                "WRONG_SIGNATURE",
                spec,
                observed=str(observed_sig),
                remediation=(
                    f"I_model signature observed={observed_sig}; "
                    f"expected `{spec.signature_str}`. Common mistake: "
                    f"emitting Contract-{('B' if spec.abi == SubstrateABI.SCALAR_1D else 'C')} "
                    f"shape when ABI is {spec.abi.name}."
                ),
            )
        return I_model  # type: ignore[return-value]

    # ABIs without I_model contract (DISCRIMINATOR, LEAN_PROOF) return a
    # no-op sentinel so callers can downcast uniformly.
    def _no_imodel(*_args: Any, **_kwargs: Any) -> float:
        raise ContractError(
            "MISSING_IMODEL",
            spec,
            observed="ABI has no I_model contract",
            remediation=f"ABI {spec.abi.name} does not use I_model.",
        )
    return _no_imodel
