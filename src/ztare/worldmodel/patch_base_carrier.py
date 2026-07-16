from __future__ import annotations

import ast
import hashlib
import inspect
from pathlib import Path
import pprint
from typing import Any, Callable

from ztare.common.patch_base_identity import (
    patch_base_fields_from_namespace,
    patch_base_fields_from_source,
    resolve_patch_base_ref,
    verify_patch_base_digest,
)
from ztare.common.worldmodel_carrier_purity import (
    carrier_contract_error,
    project_dynamics_assumption,
)


ProgramLoader = Callable[[dict[str, Any]], Any]


def materialize_immutable_patch_base(
    project_dir: str | Path,
    source: str,
    *,
    prefix: str = "frontier",
) -> tuple[str, str]:
    """Persist candidate bytes once under their content identity.

    Promotion, repair preflight, and deterministic compilation all need the
    same immutable composition edge.  Keeping that edge behind one door avoids
    reconstructing a mutable ``test_model.py`` through prose or an older base.
    """

    if not isinstance(source, str) or not source.strip():
        raise ValueError("immutable patch base requires non-empty candidate source")
    safe_prefix = "".join(
        ch for ch in str(prefix or "frontier") if ch.isalnum() or ch in {"_", "-"}
    )
    if not safe_prefix:
        raise ValueError("immutable patch base prefix has no safe characters")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    relative = f"workspace/submissions/{safe_prefix}_{digest[:16]}.py"
    path = Path(project_dir) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("content-addressed patch-base path collision")
    else:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(source, encoding="utf-8")
        temporary.replace(path)
    return relative, digest


def _literal_assignment(source: str, name: str) -> Any | None:
    tree = ast.parse(source)
    for node in tree.body:
        value = None
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                value = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                value = node.value
        if value is not None:
            try:
                return ast.literal_eval(value)
            except (TypeError, ValueError, SyntaxError):
                return None
    return None


def compact_literal_patch_prefix(
    candidate_path: str | Path,
    *,
    project_dir: str | Path,
    max_depth: int = 64,
) -> str | None:
    """Collapse consecutive literal patch specs into one equivalent delta.

    Each patch spec sees the same source state and the consequence produced by
    the preceding layer.  The generated delta preserves that order by invoking
    the existing catalog lowerer once per spec; it does not merge rule lists or
    let rule identifiers leak across layer boundaries.  Python patch layers
    terminate the compactable prefix and remain untouched.
    """

    project = Path(project_dir).resolve()
    candidate = Path(candidate_path)
    if not candidate.is_absolute():
        candidate = project / candidate
    candidate = candidate.resolve()
    chain = (
        candidate,
        *resolved_patch_base_paths(
            candidate,
            project_dir=project,
            max_depth=max_depth,
        ),
    )
    specs: list[dict[str, Any]] = []
    source_refs: list[str] = []
    base_path: Path | None = None
    for path in chain:
        source = path.read_text(encoding="utf-8")
        spec = _literal_assignment(source, "PATCH_DELTA_SPEC")
        if not isinstance(spec, dict):
            base_path = path
            break
        specs.append(spec)
        source_refs.append(str(path.relative_to(project)))
    if len(specs) < 2 or base_path is None:
        return None

    time_dependent = any(
        any(
            "when_t_mod" in rule
            or "when_phase" in rule
            or "rate" in rule
            for rules in (
                list(spec.get("actions", {}).values()),
                [spec.get("always", [])],
            )
            for group in rules
            for rule in (group or [])
            if isinstance(rule, dict)
        )
        for spec in specs
    )
    lawful_time = project_dynamics_assumption(project) == "lawful_time"
    if time_dependent and not lawful_time:
        return None

    base_ref = str(base_path.relative_to(project))
    base_sha = hashlib.sha256(base_path.read_bytes()).hexdigest()
    ordered_specs = list(reversed(specs))
    signature = (
        "def PATCH_DELTA(base_next, state, action, t):\n"
        if lawful_time
        else "def PATCH_DELTA(base_next, state, action):\n"
    )
    time_argument = "t" if lawful_time else "0"
    return (
        "# CompactedPatchSources: "
        + ",".join(source_refs)
        + "\nPATCH_BASE = "
        + pprint.pformat(
            {"source_ref": base_ref, "sha256": base_sha},
            sort_dicts=True,
            width=100,
        )
        + "\n\n_PATCH_DELTA_SPECS = "
        + pprint.pformat(ordered_specs, sort_dicts=True, width=100)
        + "\n\nfrom ztare.worldmodel.spec_catalog import lower_patch_delta_spec as _lower_patch\n"
        + "_PATCH_DELTAS = []\n"
        + "for _spec in _PATCH_DELTA_SPECS:\n"
        + "    _delta, _error = _lower_patch(_spec)\n"
        + "    if _delta is None:\n"
        + "        raise ValueError(f'compacted patch spec failed to lower: {_error}')\n"
        + "    _PATCH_DELTAS.append(_delta)\n"
        + "_PATCH_DELTAS = tuple(_PATCH_DELTAS)\n\n"
        + signature
        + "    current = base_next\n"
        + "    for delta in _PATCH_DELTAS:\n"
        + f"        current = delta(current, state, action, {time_argument})\n"
        + "        if current is None:\n"
        + "            return None\n"
        + "    return current\n"
    )
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
            from ztare.common.interface_inconsistency import (
                write_interface_inconsistency_receipt,
            )

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


def _validate_patch_base_contract(path: Path, project_dir: Path) -> None:
    source = path.read_text(encoding="utf-8", errors="ignore")
    err = carrier_contract_error(
        source,
        dynamics_assumption=project_dynamics_assumption(project_dir),
    )
    if err:
        raise ValueError(
            "PATCH_BASE source_ref violates the current worldmodel carrier "
            f"contract: {err}"
        )


def _resolved_patch_base_paths(
    fields: tuple[str, object],
    *,
    project_dir: Path,
    max_depth: int,
    seen: set[Path] | None = None,
    allow_legacy_prefix: bool = False,
) -> tuple[Path, ...]:
    """Resolve the immutable source closure behind one PATCH_BASE edge."""

    if max_depth < 1:
        raise ValueError("PATCH_BASE depth exceeds configured max_depth.")
    ref, expected_sha = fields
    base_path = resolve_patch_base_ref(project_dir, ref)
    _checked_hash_matches(
        project_dir,
        ref,
        base_path,
        expected_sha,
        allow_legacy_prefix=allow_legacy_prefix,
    )
    _validate_patch_base_contract(base_path, project_dir)
    visited = set(seen or set())
    if base_path in visited:
        raise ValueError("PATCH_BASE chain contains a cycle.")
    visited.add(base_path)
    source = base_path.read_text(encoding="utf-8")
    nested = patch_base_fields_from_source(source)
    if nested is None:
        return (base_path,)
    return (
        base_path,
        *_resolved_patch_base_paths(
            nested,
            project_dir=project_dir,
            max_depth=max_depth - 1,
            seen=visited,
            allow_legacy_prefix=True,
        ),
    )


def resolved_patch_base_paths(
    candidate_path: str | Path,
    *,
    project_dir: str | Path,
    max_depth: int = 16,
) -> tuple[Path, ...]:
    """Return validated PATCH_BASE ancestors, nearest edge first.

    This is the shared identity-preserving chain resolver.  Consumers that
    inspect provenance, score composed complexity, or evaluate layer effects
    must traverse the same content-addressed edges as the execution gate.
    """

    project = Path(project_dir).resolve()
    candidate = Path(candidate_path)
    if not candidate.is_absolute():
        candidate = project / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(project)
    except ValueError as exc:
        raise ValueError("candidate_path escapes project_dir") from exc
    source = candidate.read_text(encoding="utf-8")
    fields = patch_base_fields_from_source(source)
    if fields is None:
        return ()
    return _resolved_patch_base_paths(
        fields,
        project_dir=project,
        max_depth=max_depth,
    )


def composed_carrier_description_length(
    candidate_path: str | Path,
    *,
    project_dir: str | Path,
    max_depth: int = 16,
) -> int:
    """Description length of candidate bytes plus their PATCH_BASE closure.

    A content-addressed base reference is a composition edge, not permission to
    erase the referenced program from model complexity.  The unit measure is
    shared MDL vocabulary; this function owns which composed sources count.
    """

    from ztare.fit.mdl import description_units

    source = Path(candidate_path).read_text(encoding="utf-8")
    fields = patch_base_fields_from_source(source)
    closure_paths = () if fields is None else _resolved_patch_base_paths(
        fields,
        project_dir=Path(project_dir),
        max_depth=max_depth,
    )
    return description_units(
        source,
        *(path.read_text(encoding="utf-8") for path in closure_paths),
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
    project = Path(project_dir)
    return len(_resolved_patch_base_paths(
        fields,
        project_dir=project,
        max_depth=max_depth,
        seen=_seen,
        allow_legacy_prefix=_allow_legacy_prefix,
    ))


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
    ``PATCH_DELTA(base_next, state, action)`` function or a literal
    ``PATCH_DELTA_SPEC``. The gate loads the base under its own authority and
    still scores the composed carrier through normal replay/rollout. Older
    four-argument deltas remain ABI-compatible, but the fourth argument is
    adapter trace metadata and is guarded by ``worldmodel_carrier_purity``.
    """

    fields = patch_base_fields_from_namespace(namespace)
    if fields is None:
        return None
    delta = namespace.get("PATCH_DELTA")
    delta_spec = namespace.get("PATCH_DELTA_SPEC")
    if callable(delta) and delta_spec is not None:
        raise ValueError(
            "PATCH_BASE carrier must choose PATCH_DELTA or PATCH_DELTA_SPEC, not both."
        )
    if not callable(delta):
        if delta_spec is None:
            raise ValueError(
                "PATCH_BASE carrier requires PATCH_DELTA or PATCH_DELTA_SPEC."
            )
        from ztare.worldmodel.spec_catalog import lower_patch_delta_spec

        delta, error = lower_patch_delta_spec(delta_spec)
        if delta is None:
            raise ValueError(f"PATCH_DELTA_SPEC failed to lower: {error}")
    project = Path(project_dir)
    ref, expected_sha = fields
    base_path = resolve_patch_base_ref(project, ref)
    _checked_hash_matches(project, ref, base_path, expected_sha)
    _validate_patch_base_contract(base_path, project)

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
    # A PATCH_BASE edge composes transition programs; it must not erase a
    # consumer projection carried by the base program.  The projection remains
    # a proposal for the composed carrier rather than an unchecked theorem:
    # ``search_factored`` tests its commuting/forward-simulation obligation at
    # every merge and returns ``projection_noncommuting`` on a counterexample.
    # This keeps the interface available without granting the delta authority
    # to certify its own quotient.
    inherited_projection = getattr(
        base_program, "_ztare_factored_projection", None
    )
    if inherited_projection is not None:
        setattr(
            _composed,
            "_ztare_factored_projection",
            inherited_projection,
        )
        setattr(
            _composed,
            "_ztare_factored_projection_transport",
            {
                "kind": "patch_base_interface_transport",
                "source_ref": ref,
                "source_sha256": expected_sha,
                "compatibility_guard": "search_factored_noncommutation",
            },
        )
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
