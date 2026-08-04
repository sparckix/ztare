from __future__ import annotations

import ast
import hashlib
import inspect
import json
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


def rewrite_patch_base_source(
    source: str,
    *,
    source_ref: str,
    source_sha256: str,
) -> str:
    """Rebind one top-level PATCH_BASE edge while preserving delta bytes."""

    tree = ast.parse(source)
    target_node: ast.Assign | ast.AnnAssign | None = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "PATCH_BASE"
            for target in node.targets
        ):
            target_node = node
            break
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "PATCH_BASE"
        ):
            target_node = node
            break
    if target_node is None or target_node.col_offset != 0:
        raise ValueError("rebase requires one top-level PATCH_BASE assignment")
    lines = source.splitlines(keepends=True)
    start = sum(len(line) for line in lines[: target_node.lineno - 1])
    end = sum(len(line) for line in lines[: target_node.end_lineno - 1]) + int(
        target_node.end_col_offset
    )
    replacement = "PATCH_BASE = " + pprint.pformat(
        {"source_ref": str(source_ref), "sha256": str(source_sha256)},
        sort_dicts=True,
        width=100,
    )
    return source[:start] + replacement + source[end:]


def carrier_provenance_from_source(source: str) -> dict[str, Any]:
    """Read the typed operation provenance carried by a composed candidate.

    Literal metadata is the current contract.  The three historical comment
    headers remain a bounded compatibility reader for already materialized
    candidates; new producers emit both until those artifacts age out.
    """

    payload = _literal_assignment(source, "CARRIER_PROVENANCE")
    if isinstance(payload, dict):
        refs = payload.get("receipt_refs")
        if isinstance(refs, (list, tuple)):
            return {
                "task_id": str(payload.get("task_id") or ""),
                "operation_identity_sha256": str(
                    payload.get("operation_identity_sha256") or ""
                ),
                "receipt_refs": [str(ref) for ref in refs if str(ref).strip()],
            }
    legacy: dict[str, str] = {}
    for line in source.splitlines()[:12]:
        if not line.startswith("# ") or ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        legacy[key.strip()] = value.strip()
    return {
        "task_id": legacy.get("TaskIdentity", ""),
        "operation_identity_sha256": legacy.get("OperationIdentity", ""),
        "receipt_refs": [
            ref.strip()
            for ref in legacy.get("ReceiptRefs", "").split(",")
            if ref.strip()
        ],
    }


def _compacted_source_refs(source: str) -> tuple[str, ...]:
    for line in source.splitlines()[:8]:
        if line.startswith("# CompactedPatchSources: "):
            return tuple(
                ref.strip()
                for ref in line.split(":", 1)[1].split(",")
                if ref.strip()
            )
    return ()


def literal_patch_prefix_layers(
    candidate_path: str | Path,
    *,
    project_dir: str | Path,
    max_depth: int = 64,
) -> tuple[Path, tuple[dict[str, Any], ...]]:
    """Return the root carrier and execution-ordered literal patch layers."""

    project = Path(project_dir).resolve()
    candidate = Path(candidate_path)
    if not candidate.is_absolute():
        candidate = project / candidate
    candidate = candidate.resolve()
    chain = (
        candidate,
        *resolved_patch_base_paths(candidate, project_dir=project, max_depth=max_depth),
    )
    top_down: list[dict[str, Any]] = []
    base_path: Path | None = None

    def source_layer(path: Path, spec: dict[str, Any]) -> dict[str, Any]:
        source = path.read_text(encoding="utf-8")
        return {
            "spec": spec,
            "provenance": carrier_provenance_from_source(source),
            "source_ref": str(path.relative_to(project)),
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        }

    for path in chain:
        source = path.read_text(encoding="utf-8")
        spec = _literal_assignment(source, "PATCH_DELTA_SPEC")
        if isinstance(spec, dict):
            top_down.append(source_layer(path, spec))
            continue
        typed_layers = _literal_assignment(source, "_PATCH_LAYERS")
        if isinstance(typed_layers, (list, tuple)) and all(
            isinstance(layer, dict) and isinstance(layer.get("spec"), dict)
            for layer in typed_layers
        ):
            top_down.extend(reversed([dict(layer) for layer in typed_layers]))
            continue
        compacted_specs = _literal_assignment(source, "_PATCH_DELTA_SPECS")
        if isinstance(compacted_specs, (list, tuple)) and all(
            isinstance(item, dict) for item in compacted_specs
        ):
            refs = tuple(reversed(_compacted_source_refs(source)))
            recovered: list[dict[str, Any]] = []
            for index, item in enumerate(compacted_specs):
                ref = refs[index] if index < len(refs) else ""
                source_path = (project / ref).resolve() if ref else path
                if project != source_path and project not in source_path.parents:
                    source_path = path
                if not source_path.is_file():
                    source_path = path
                recovered.append(source_layer(source_path, dict(item)))
            top_down.extend(reversed(recovered))
            continue
        base_path = path
        break
    if base_path is None:
        raise ValueError("literal patch prefix has no root carrier")
    return base_path, tuple(reversed(top_down))


def render_literal_patch_layers(
    *,
    base_path: str | Path,
    layers: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    project_dir: str | Path,
) -> str:
    """Render one provenance-preserving literal patch composition."""

    project = Path(project_dir).resolve()
    base = Path(base_path).resolve()
    normalized = [dict(layer) for layer in layers]
    if not normalized or not all(
        isinstance(layer.get("spec"), dict) for layer in normalized
    ):
        raise ValueError("compacted carrier requires typed literal layers")
    base_ref = str(base.relative_to(project))
    base_sha = hashlib.sha256(base.read_bytes()).hexdigest()
    lawful_time = project_dynamics_assumption(project) == "lawful_time"
    signature = (
        "def PATCH_DELTA(base_next, state, action, t):\n"
        if lawful_time
        else "def PATCH_DELTA(base_next, state, action):\n"
    )
    time_argument = "t" if lawful_time else "0"
    return (
        "# CompactedPatchSources: "
        + ",".join(str(layer.get("source_ref") or "") for layer in reversed(normalized))
        + "\nPATCH_BASE = "
        + pprint.pformat(
            {"source_ref": base_ref, "sha256": base_sha},
            sort_dicts=True,
            width=100,
        )
        + "\n\n_PATCH_LAYERS = "
        + pprint.pformat(normalized, sort_dicts=True, width=100)
        + "\n_PATCH_DELTA_SPECS = [layer['spec'] for layer in _PATCH_LAYERS]"
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


def carrier_execution_sha256_from_source(source: str) -> str:
    """Identify executable literal IR while preserving source provenance.

    Receipt refs and task ids explain where a carrier came from; they do not
    change a literal carrier's transition function.  Quotient only the loader
    branches whose executable inputs are statically available.  Free-form
    Python remains byte-identified.
    """
    payload: dict[str, Any] | None = None
    patch_base = patch_base_fields_from_source(source)
    patch_spec = _literal_assignment(source, "PATCH_DELTA_SPEC")
    compacted_specs = _literal_assignment(source, "_PATCH_DELTA_SPECS")
    typed_layers = _literal_assignment(source, "_PATCH_LAYERS")
    if isinstance(typed_layers, (list, tuple)) and all(
        isinstance(layer, dict) and isinstance(layer.get("spec"), dict)
        for layer in typed_layers
    ):
        compacted_specs = [layer["spec"] for layer in typed_layers]
    if patch_base is not None and isinstance(patch_spec, dict):
        _base_ref, base_sha = patch_base
        if len(str(base_sha)) == 64:
            payload = {
                "kind": "patch_base_literal_v1",
                "base_sha256": str(base_sha),
                "delta_spec": patch_spec,
            }
    elif patch_base is not None and isinstance(compacted_specs, (list, tuple)):
        _base_ref, base_sha = patch_base
        if len(str(base_sha)) == 64 and all(
            isinstance(spec, dict) for spec in compacted_specs
        ):
            payload = {
                "kind": "patch_base_literal_sequence_v1",
                "base_sha256": str(base_sha),
                "delta_specs": list(compacted_specs),
            }
    else:
        world_spec = _literal_assignment(source, "WORLD_MODEL_SPEC")
        if isinstance(world_spec, dict):
            payload = {"kind": "world_model_spec_v1", "spec": world_spec}
        else:
            program = _literal_assignment(source, "PROGRAM")
            if program is not None:
                payload = {"kind": "program_ast_v1", "program": program}
    if payload is None:
        return hashlib.sha256(source.encode("utf-8")).hexdigest()
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


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
    base_path, layers = literal_patch_prefix_layers(
        candidate_path,
        project_dir=project,
        max_depth=max_depth,
    )
    if len(layers) < 2:
        return None
    specs = [layer["spec"] for layer in layers]

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
    if time_dependent and project_dynamics_assumption(project) != "lawful_time":
        return None
    return render_literal_patch_layers(
        base_path=base_path,
        layers=layers,
        project_dir=project,
    )


def composed_literal_operator_spec(
    candidate_path: str | Path,
    *,
    project_dir: str | Path,
    max_depth: int = 64,
) -> dict[str, Any] | None:
    """Expose the literal operation algebra carried by a composed program.

    Execution, goal abduction, and active discrimination must consume the same
    operator chain.  This reader follows the validated PATCH_BASE identity
    edges and concatenates literal specs in execution order.  Free-form layers
    remain executable but contribute no invented operator metadata.
    """

    project = Path(project_dir).resolve()
    candidate = Path(candidate_path)
    if not candidate.is_absolute():
        candidate = project / candidate
    candidate = candidate.resolve()
    chain = tuple(reversed(resolved_patch_base_paths(
        candidate,
        project_dir=project,
        max_depth=max_depth,
    ))) + (candidate,)
    specs: list[dict[str, Any]] = []
    for path in chain:
        source = path.read_text(encoding="utf-8")
        typed_layers = _literal_assignment(source, "_PATCH_LAYERS")
        if isinstance(typed_layers, (list, tuple)):
            specs.extend(
                layer["spec"]
                for layer in typed_layers
                if isinstance(layer, dict) and isinstance(layer.get("spec"), dict)
            )
            continue
        compacted = _literal_assignment(source, "_PATCH_DELTA_SPECS")
        if isinstance(compacted, (list, tuple)):
            specs.extend(spec for spec in compacted if isinstance(spec, dict))
            continue
        patch_spec = _literal_assignment(source, "PATCH_DELTA_SPEC")
        if isinstance(patch_spec, dict):
            specs.append(patch_spec)
            continue
        world_spec = _literal_assignment(source, "WORLD_MODEL_SPEC")
        if isinstance(world_spec, dict):
            specs.append(world_spec)
    if not specs:
        return None
    actions: dict[str, list[Any]] = {}
    always: list[Any] = []
    for spec in specs:
        for action, rules in (spec.get("actions") or {}).items():
            actions.setdefault(str(action), []).extend(list(rules or []))
        always.extend(list(spec.get("always") or []))
    return {"actions": actions, "always": always}
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
        if base_next is None:
            # PATCH_BASE composition is a partial morphism.  An annihilated or
            # undefined base image cannot be lowered through a grid delta.
            return None
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
