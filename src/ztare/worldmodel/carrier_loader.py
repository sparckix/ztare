"""Single lowering door for executable transition carriers.

Candidate source, an already-executed namespace, batch evaluation, live
planning, and project gate harnesses must resolve the same carrier identity.
Keeping the lowering order here prevents a PATCH_BASE, catalog spec, callable,
or program AST from changing meaning at a producer/consumer seam.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from ztare.common.patch_base_identity import patch_base_fields_from_namespace
from ztare.common.worldmodel_carrier_purity import (
    project_dynamics_assumption,
    validate_worldmodel_carrier_source,
)


CarrierKind = Literal[
    "patch_base",
    "world_model_spec",
    "program_ast",
    "python_callable",
    "extensions_src",
]

CURRENT_CARRIER_EVIDENCE_SCHEMA = "ztare-current-carrier-evidence-identity-v1"


class CarrierEvidenceIdentityError(ValueError):
    """A receipt cannot be joined to the active carrier/evidence population."""


@dataclass(frozen=True)
class CurrentCarrierEvidenceIdentity:
    """Content identity shared by control-bearing carrier observations.

    ``carrier_ref`` is only a locator for the bytes occupying the current role;
    equality is the pair of full digests. ``adapter_identity`` is deliberately
    opaque so non-grid substrates can add their own lifecycle coordinate
    without this kernel interpreting it.
    """

    carrier_ref: str
    carrier_sha256: str
    evidence_epoch_sha256: str
    carrier_role: str
    adapter_identity: Any = None
    schema: str = CURRENT_CARRIER_EVIDENCE_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        row = {
            "schema": self.schema,
            "carrier_ref": self.carrier_ref,
            "carrier_sha256": self.carrier_sha256,
            "evidence_epoch_sha256": self.evidence_epoch_sha256,
            "carrier_role": self.carrier_role,
        }
        if self.adapter_identity is not None:
            row["adapter_identity"] = self.adapter_identity
        return row


def _full_sha256(value: object) -> str:
    digest = str(value or "").strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise CarrierEvidenceIdentityError("identity requires a full 64-hex sha256")
    return digest


def _project_relative_carrier(project: Path, ref: str | Path) -> tuple[Path, str]:
    raw = Path(ref)
    if raw.is_absolute() or ".." in raw.parts:
        raise CarrierEvidenceIdentityError(
            "current carrier locator must be project-relative"
        )
    path = (project / raw).resolve()
    if project != path and project not in path.parents:
        raise CarrierEvidenceIdentityError("current carrier locator escapes project")
    if not path.is_file():
        raise CarrierEvidenceIdentityError(f"current carrier not found: {raw}")
    return path, str(path.relative_to(project))


def resolve_current_carrier_evidence_identity(
    project_dir: str | Path,
    *,
    carrier_ref: str | Path | None = None,
    adapter_identity: Any = None,
) -> CurrentCarrierEvidenceIdentity:
    """Resolve the carrier bytes and evidence snapshot active *now*.

    Worldmodel projects use their canonical ``test_model.py`` carrier. An
    adapter may instead pass an opaque project-relative carrier locator and
    lifecycle token. If no canonical carrier exists, the epoch-current repair
    frontier is the compatibility source; its immutable artifact is already
    digest-checked by :mod:`patch_base_identity`.
    """

    project = Path(project_dir).resolve()
    selected = Path(carrier_ref) if carrier_ref is not None else Path("test_model.py")
    if carrier_ref is not None or (project / selected).is_file():
        path, normalized_ref = _project_relative_carrier(project, selected)
        carrier_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        carrier_role = "adapter_selected" if carrier_ref is not None else "canonical"
        from ztare.common.observation_chart import capture_project_evidence_epoch

        evidence_sha256 = capture_project_evidence_epoch(project).epoch_sha256
    else:
        from ztare.common.patch_base_identity import load_current_repair_frontier

        frontier = load_current_repair_frontier(project)
        path = Path(frontier["path"]).resolve()
        normalized_ref = str(path.relative_to(project))
        carrier_sha256 = _full_sha256(frontier["sha256"])
        evidence_sha256 = _full_sha256(frontier["evidence_epoch_sha256"])
        carrier_role = str(frontier["role"])
    return CurrentCarrierEvidenceIdentity(
        carrier_ref=normalized_ref,
        carrier_sha256=_full_sha256(carrier_sha256),
        evidence_epoch_sha256=_full_sha256(evidence_sha256),
        carrier_role=carrier_role,
        adapter_identity=adapter_identity,
    )


def require_current_carrier_evidence_binding(
    receipt: Mapping[str, Any],
    current: CurrentCarrierEvidenceIdentity,
) -> dict[str, Any]:
    """Return a normalized binding or reject a historical/unbound receipt.

    The nested schema is preferred. Existing typed ledgers may expose the same
    two coordinates at top level; those remain admissible only when both are
    full digests. Source paths and SHA prefixes never participate in equality.
    """

    nested = receipt.get("carrier_evidence_identity")
    binding = nested if isinstance(nested, Mapping) else receipt
    carrier_sha = (
        binding.get("carrier_sha256")
        or binding.get("carrier_sha")
        or binding.get("sha")
    )
    evidence_epoch = binding.get("evidence_epoch_sha256")
    if evidence_epoch is None and isinstance(binding.get("evidence_epoch"), Mapping):
        evidence_epoch = binding["evidence_epoch"].get("epoch_sha256")
    declared_carrier = _full_sha256(carrier_sha)
    declared_epoch = _full_sha256(evidence_epoch)
    if declared_carrier != current.carrier_sha256:
        raise CarrierEvidenceIdentityError(
            "receipt carrier does not match the current carrier bytes"
        )
    if declared_epoch != current.evidence_epoch_sha256:
        raise CarrierEvidenceIdentityError(
            "receipt evidence epoch is historical"
        )
    if current.adapter_identity is not None:
        if binding.get("adapter_identity") != current.adapter_identity:
            raise CarrierEvidenceIdentityError(
                "receipt adapter identity does not match the current adapter epoch"
            )
    return current.to_dict()


def carrier_kind(namespace: Mapping[str, Any]) -> CarrierKind:
    """Return the lowering branch selected by :func:`lower_carrier_namespace`."""

    if patch_base_fields_from_namespace(dict(namespace)) is not None:
        return "patch_base"
    if namespace.get("EXTENSIONS_SRC"):
        return "extensions_src"
    if namespace.get("WORLD_MODEL_SPEC") is not None:
        return "world_model_spec"
    if namespace.get("PROGRAM") is not None:
        return "program_ast"
    return "python_callable"


def _compile_carried_extensions(namespace: Mapping[str, Any]) -> dict[str, Any]:
    sources = namespace.get("EXTENSIONS_SRC") or {}
    if not sources:
        return {}
    from ztare.worldmodel.grammar_extension import compile_extension

    compiled: dict[str, Any] = {}
    for name, code in list(sources.items())[:6]:
        if not str(name).replace("_", "").isalnum():
            continue
        function, _error = compile_extension(str(code))
        if function is not None:
            compiled[str(name)] = function
    return compiled


def _to_program(node: Any) -> Any:
    if isinstance(node, list):
        return tuple(_to_program(item) for item in node)
    return node


def _program_extension_names(node: Any) -> set[str]:
    if not isinstance(node, tuple):
        return set()
    names = {str(node[1])} if len(node) > 1 and node[0] == "ext" else set()
    for child in node[1:]:
        names.update(_program_extension_names(child))
    return names


def _call_program(program: Any, state: Any, action: int, time_value: int) -> Any:
    if callable(program):
        return program(state, action, time_value)
    from ztare.worldmodel.grid_dsl import evaluate

    return evaluate(program, state, action, time_value)


def _attach_projection(
    program: Any,
    namespace: Mapping[str, Any],
    *,
    project_dir: Path,
) -> Any:
    try:
        from ztare.worldmodel.compiled_fiber_planning import (
            attach_compiled_projection,
        )

        return attach_compiled_projection(
            program,
            namespace,
            project_dir=project_dir,
        )
    except Exception:  # noqa: BLE001 - planning metadata has no gate authority
        if namespace.get("PATCH_DELTA_SPEC") is not None or callable(
            namespace.get("PATCH_DELTA")
        ):
            setattr(program, "_ztare_factored_projection", None)
        return program


def lower_carrier_namespace(
    namespace: Mapping[str, Any],
    *,
    project_dir: str | Path,
    attach_projection: bool = True,
    allow_patch_base: bool = True,
) -> Any:
    """Lower one executed candidate namespace through the canonical order."""

    mutable_namespace = dict(namespace)
    carried_extensions = _compile_carried_extensions(mutable_namespace)
    project = Path(project_dir).resolve()

    from ztare.worldmodel.patch_base_carrier import compose_patch_base_carrier

    patch_fields = patch_base_fields_from_namespace(mutable_namespace)
    if patch_fields is not None and not allow_patch_base:
        raise ValueError("PATCH_BASE carrier is disabled for this consumer")
    program = compose_patch_base_carrier(
        mutable_namespace,
        project_dir=project,
        load_program_from_namespace=lambda child: lower_carrier_namespace(
            child,
            project_dir=project,
            attach_projection=attach_projection,
            allow_patch_base=allow_patch_base,
        ),
        call_program=_call_program,
    )

    if program is None:
        spec = mutable_namespace.get("WORLD_MODEL_SPEC")
        if spec is not None:
            from ztare.worldmodel.spec_catalog import lower_spec

            program, error = lower_spec(spec)
            if program is None:
                raise ValueError(f"WORLD_MODEL_SPEC failed to lower: {error}")
        else:
            for alias in ("step", "f", "model", "I_model"):
                function = mutable_namespace.get(alias)
                if callable(function):
                    program = function
                    break
            if program is None and mutable_namespace.get("PROGRAM") is not None:
                program = _to_program(mutable_namespace["PROGRAM"])

    if program is None:
        raise AttributeError("candidate exposes no supported transition carrier")
    if mutable_namespace.get("EXTENSIONS_SRC") and not isinstance(program, tuple):
        raise ValueError("EXTENSIONS_SRC requires a PROGRAM AST carrier")
    if isinstance(program, tuple):
        extension_names = _program_extension_names(program)
        if extension_names:
            if mutable_namespace.get("EXTENSIONS_SRC"):
                registry = carried_extensions
            else:
                from ztare.worldmodel.grid_dsl import EXTENSIONS

                registry = {
                    name: EXTENSIONS[name]
                    for name in extension_names
                    if name in EXTENSIONS
                }
            from ztare.worldmodel.grid_dsl import bind_extensions

            program = bind_extensions(program, registry)
    if attach_projection:
        program = _attach_projection(
            program,
            mutable_namespace,
            project_dir=project,
        )
    return program


def load_carrier_from_source(
    source: str,
    source_path: str | Path,
    project_dir: str | Path,
    *,
    attach_projection: bool = True,
    dynamics_assumption: str | None = None,
) -> Any:
    """Validate, execute, and lower source under one project identity."""

    project = Path(project_dir).resolve()
    validate_worldmodel_carrier_source(
        source,
        dynamics_assumption=(
            dynamics_assumption
            if dynamics_assumption is not None
            else project_dynamics_assumption(project)
        ),
    )
    namespace: dict[str, Any] = {"__name__": "candidate"}
    exec(compile(source, str(source_path), "exec"), namespace)  # noqa: S102
    return lower_carrier_namespace(
        namespace,
        project_dir=project,
        attach_projection=attach_projection,
    )


def load_carrier_path(
    source_path: str | Path,
    *,
    project_dir: str | Path,
    attach_projection: bool = True,
    dynamics_assumption: str | None = None,
) -> tuple[Any, CarrierKind, str]:
    """Load a source path and return program, branch identity, and source SHA."""

    path = Path(source_path)
    source = path.read_text(encoding="utf-8")
    project = Path(project_dir).resolve()
    validate_worldmodel_carrier_source(
        source,
        dynamics_assumption=(
            dynamics_assumption
            if dynamics_assumption is not None
            else project_dynamics_assumption(project)
        ),
    )
    namespace: dict[str, Any] = {"__name__": "candidate"}
    exec(compile(source, str(path), "exec"), namespace)  # noqa: S102
    return (
        lower_carrier_namespace(
            namespace,
            project_dir=project,
            attach_projection=attach_projection,
        ),
        carrier_kind(namespace),
        hashlib.sha256(source.encode("utf-8")).hexdigest(),
    )


__all__ = [
    "CURRENT_CARRIER_EVIDENCE_SCHEMA",
    "CarrierKind",
    "CarrierEvidenceIdentityError",
    "CurrentCarrierEvidenceIdentity",
    "carrier_kind",
    "load_carrier_from_source",
    "load_carrier_path",
    "lower_carrier_namespace",
    "require_current_carrier_evidence_binding",
    "resolve_current_carrier_evidence_identity",
]
