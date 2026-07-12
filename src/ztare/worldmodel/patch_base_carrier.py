from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, Callable

from ztare.common.patch_base_identity import (
    patch_base_fields_from_namespace,
    resolve_patch_base_ref,
    verify_patch_base_digest,
)
from ztare.common.worldmodel_carrier_purity import carrier_contract_error
from ztare.common.interface_inconsistency import write_interface_inconsistency_receipt


ProgramLoader = Callable[[dict[str, Any]], Any]
ProgramCaller = Callable[[Any, Any, int, int], Any]


def _checked_hash_matches(
    project_dir: Path,
    ref: str,
    path: Path,
    expected: object,
    *,
    allow_legacy_prefix: bool = False,
) -> None:
    try:
        verify_patch_base_digest(path, expected, allow_legacy_prefix=allow_legacy_prefix)
    except ValueError as exc:
        try:
            write_interface_inconsistency_receipt(
                project_dir=project_dir,
                kind="patch_base_identity_mismatch",
                invariant="artifact identity is kernel-supplied and full-digest bound",
                producer_surface="candidate PATCH_BASE declaration",
                consumer_surface="patch_base_carrier gate",
                expected="full 64-hex sha256 matching workspace/submissions artifact bytes",
                observed=f"{ref}: {expected!r}",
                evidence_refs=[ref],
                repair_status="blocked_by_gate",
                severity="error",
                metadata={"error": str(exc)},
            )
        except Exception:
            pass
        raise


def _validate_patch_base_contract(path: Path) -> None:
    source = path.read_text(encoding="utf-8", errors="ignore")
    err = carrier_contract_error(source)
    if err:
        raise ValueError(
            "PATCH_BASE source_ref violates the current worldmodel carrier "
            f"contract: {err}"
        )


def patch_base_chain_depth(
    namespace: dict[str, Any],
    *,
    project_dir: str | Path,
    max_depth: int = 16,
    _seen: set[Path] | None = None,
    _allow_legacy_prefix: bool = False,
) -> int:
    """Return the declared PATCH_BASE composition depth for a candidate.

    Depth is a cost/provenance property of a composed carrier, not an adoption
    verdict. Callers use it to bound evaluation work while preserving the
    possibility of lawful base+delta steering.
    """

    fields = patch_base_fields_from_namespace(namespace)
    if fields is None:
        return 0
    if max_depth < 1:
        raise ValueError("PATCH_BASE depth exceeds configured max_depth.")
    project = Path(project_dir)
    ref, expected_sha = fields
    base_path = resolve_patch_base_ref(project, ref)
    _checked_hash_matches(
        project,
        ref,
        base_path,
        expected_sha,
        allow_legacy_prefix=_allow_legacy_prefix,
    )
    _validate_patch_base_contract(base_path)
    seen = set(_seen or set())
    if base_path in seen:
        raise ValueError("PATCH_BASE chain contains a cycle.")
    seen.add(base_path)
    base_namespace: dict[str, Any] = {"__name__": "patch_base_depth_probe"}
    exec(compile(base_path.read_text(encoding="utf-8"), str(base_path), "exec"), base_namespace)
    return 1 + patch_base_chain_depth(
        base_namespace,
        project_dir=project,
        max_depth=max_depth - 1,
        _seen=seen,
        _allow_legacy_prefix=True,
    )


def compose_patch_base_carrier(
    namespace: dict[str, Any],
    *,
    project_dir: str | Path,
    load_program_from_namespace: ProgramLoader,
    call_program: ProgramCaller,
) -> Callable[[Any, int, int], Any] | None:
    """Return a gate-owned base+delta carrier when a candidate declares one.

    Candidate code may not import prior submissions by path. This helper gives
    deterministic harnesses a sealed alternative: the candidate names a
    project-local prior artifact by content hash and provides a pure
    ``PATCH_DELTA(base_next, state, action)`` function. The gate loads the base
    under its own authority and still scores the composed carrier through normal
    replay/rollout. Older four-argument deltas remain ABI-compatible, but the
    fourth argument is adapter trace metadata and is guarded by
    ``worldmodel_carrier_purity``.
    """

    fields = patch_base_fields_from_namespace(namespace)
    if fields is None:
        return None
    delta = namespace.get("PATCH_DELTA")
    if not callable(delta):
        raise ValueError("PATCH_BASE carrier requires callable PATCH_DELTA.")
    project = Path(project_dir)
    ref, expected_sha = fields
    base_path = resolve_patch_base_ref(project, ref)
    _checked_hash_matches(project, ref, base_path, expected_sha)
    _validate_patch_base_contract(base_path)

    base_namespace: dict[str, Any] = {"__name__": "patch_base_candidate"}
    exec(compile(base_path.read_text(encoding="utf-8"), str(base_path), "exec"), base_namespace)
    _normalize_legacy_base_namespace(project, base_namespace)
    base_program = load_program_from_namespace(base_namespace)
    delta_arity = _patch_delta_arity(delta)

    def _composed(state: Any, action: int, t: int) -> Any:
        base_next = call_program(base_program, state, action, t)
        if delta_arity == 3:
            return delta(base_next, state, action)
        return delta(base_next, state, action, t)

    _composed.__name__ = "patch_base_composed_step"
    return _composed


def _normalize_legacy_base_namespace(project: Path, namespace: dict[str, Any]) -> None:
    fields = patch_base_fields_from_namespace(namespace)
    if fields is None:
        return
    ref, expected_sha = fields
    path = resolve_patch_base_ref(project, ref)
    digest = verify_patch_base_digest(path, expected_sha, allow_legacy_prefix=True)
    spec = namespace.get("PATCH_BASE")
    if isinstance(spec, dict):
        spec["sha256"] = digest
        spec.pop("sha256_prefix", None)
        spec.pop("sha", None)
        spec.pop("source_sha", None)
        return
    if namespace.get("PATCH_BASE_REF") or namespace.get("PATCH_BASE_PATH"):
        namespace["PATCH_BASE_SHA256"] = digest
        namespace.pop("PATCH_BASE_SHA256_PREFIX", None)
        namespace.pop("PATCH_BASE_SHA", None)


def _patch_delta_arity(delta: Callable[..., Any]) -> int:
    try:
        sig = inspect.signature(delta)
    except (TypeError, ValueError):
        return 4
    params = list(sig.parameters.values())
    if any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params):
        return 4
    positional = [
        p for p in params
        if p.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    ]
    if len(positional) == 3:
        return 3
    if len(positional) == 4:
        return 4
    raise ValueError(
        "PATCH_DELTA must accept either "
        "(base_next, state, action) or (base_next, state, action, t)."
    )
