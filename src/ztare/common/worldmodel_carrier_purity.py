from __future__ import annotations

import ast
import json
import os
from pathlib import Path


_TRANSITION_FUNCTION_NAMES = {"step", "PATCH_DELTA"}
_PREDICTOR_NAMES = {"step", "f", "model", "I_model"}
_PROGRAM_NAMES = {"PROGRAM", "WORLD_MODEL_SPEC"}
_PATCH_BASE_NAMES = {"PATCH_BASE", "PATCH_BASE_REF", "PATCH_BASE_PATH"}
_PATCH_DELTA_SPEC_NAME = "PATCH_DELTA_SPEC"
_MUTATING_METHODS = {
    "append",
    "clear",
    "extend",
    "insert",
    "pop",
    "popitem",
    "remove",
    "reverse",
    "setdefault",
    "sort",
    "update",
}


def validate_worldmodel_transition_purity(tree: ast.AST) -> None:
    """Reject replay-order memory in executable worldmodel carriers."""
    module_names: set[str] = set()
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                module_names |= _assigned_names(target)
        elif isinstance(node, ast.AnnAssign):
            module_names |= _assigned_names(node.target)

    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if fn.name not in _TRANSITION_FUNCTION_NAMES:
            continue
        for node in ast.walk(fn):
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                raise ValueError(
                    "Worldmodel carrier contract reject: transition functions "
                    "must be pure over their inputs; `global`/`nonlocal` replay "
                    "state is not allowed."
                )
            targets: list[ast.AST] = []
            if isinstance(node, ast.Assign):
                targets.extend(node.targets)
            elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                targets.append(node.target)
            for target in targets:
                root = _root_name(target)
                if root in module_names and not isinstance(target, ast.Name):
                    raise ValueError(
                        "Worldmodel carrier contract reject: transition functions "
                        f"must not mutate module-scope object {root!r}; keep "
                        "all transition state local to the call."
                    )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                root = _root_name(node.func.value)
                if root in module_names and node.func.attr in _MUTATING_METHODS:
                    raise ValueError(
                        "Worldmodel carrier contract reject: transition functions "
                        f"must not mutate module-scope object {root!r}; keep "
                        "all transition state local to the call."
                    )


def _resolve_dynamics_assumption(dynamics_assumption: str | None = None) -> str:
    """Return the effective dynamics assumption, with env > param > default precedence.

    "markovian"   — default; syntactic t-read ban enforced verbatim.
    "lawful_time" — t-reading permitted; anti-memorization discharged by gates.
    """
    # ponytail: env wins, absent env falls to param, absent both = markovian
    env = os.environ.get("ZTARE_DYNAMICS_ASSUMPTION")
    if env:
        return env
    if dynamics_assumption:
        return dynamics_assumption
    return "markovian"


def project_dynamics_assumption(project_dir: str | Path) -> str | None:
    """Resolve the transition contract declared for one project identity.

    Candidate-memory and prompt projections often run outside the main loop,
    so process-local environment state cannot be their authority.  The rubric
    adjacent to ``projects/<project_id>`` is the durable declaration.
    """
    project = Path(project_dir).resolve()
    rubric_candidates = [
        project / "rubric.json",
        project.parent.parent / "rubrics" / f"{project.name}.json",
    ]
    for rubric in rubric_candidates:
        try:
            payload = json.loads(rubric.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        value = str(payload.get("dynamics_assumption") or "").strip().lower()
        if value:
            return value
    return None


def validate_no_step_argument_reads(tree: ast.AST, dynamics_assumption: str | None = None) -> None:
    """Reject carriers that read the adapter replay index inside dynamics.

    Under "markovian" (default) the syntactic ban is enforced verbatim.
    Under "lawful_time" the ban is lifted; anti-memorization is discharged
    structurally by the held-out rollout and dominance gates.
    """
    assumption = _resolve_dynamics_assumption(dynamics_assumption)
    if assumption == "lawful_time":
        return  # ban discharged by held-out gates; no syntactic check
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if fn.name not in _TRANSITION_FUNCTION_NAMES:
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and node.id == "t" and isinstance(node.ctx, ast.Load):
                raise ValueError(
                    "Worldmodel temporal admissibility reject: transition "
                    "carriers must not read the adapter replay index. "
                    "The step argument is a trace coordinate for the adapter; "
                    "portable dynamics must use state/action evidence or a "
                    "state-encoded clock. "
                    "Substrates whose physics is lawfully time-dependent may "
                    "declare dynamics_assumption: lawful_time in the rubric; "
                    "anti-memorization is then enforced by the held-out gates."
                )


def validate_worldmodel_transition_contract(tree: ast.AST, dynamics_assumption: str | None = None) -> None:
    validate_worldmodel_transition_purity(tree)
    validate_no_step_argument_reads(tree, dynamics_assumption)
    validate_worldmodel_carrier_shape(tree)


def validate_worldmodel_carrier_shape(tree: ast.AST) -> None:
    """Reject source that is pure Python but not a lowerable world-model carrier."""

    names = _top_level_names(tree)
    has_patch_delta = "PATCH_DELTA" in names
    has_patch_delta_spec = _PATCH_DELTA_SPEC_NAME in names
    has_patch_base = bool(names & _PATCH_BASE_NAMES)
    if has_patch_delta or has_patch_delta_spec or has_patch_base:
        if has_patch_delta and has_patch_delta_spec:
            raise ValueError(
                "Worldmodel carrier contract reject: choose PATCH_DELTA or "
                "PATCH_DELTA_SPEC, not both."
            )
        if not (has_patch_delta or has_patch_delta_spec):
            raise ValueError(
                "Worldmodel carrier contract reject: PATCH_BASE requires "
                "PATCH_DELTA or PATCH_DELTA_SPEC."
            )
        if not has_patch_base:
            delta_name = "PATCH_DELTA" if has_patch_delta else "PATCH_DELTA_SPEC"
            raise ValueError(
                f"Worldmodel carrier contract reject: {delta_name} is a patch "
                "combiner, not a standalone transition law. Declare PATCH_BASE with a "
                "gate-supplied full sha256, or submit a direct step/PROGRAM/"
                "WORLD_MODEL_SPEC carrier."
            )
        return

    if names & _PROGRAM_NAMES:
        return
    if names & _PREDICTOR_NAMES:
        return
    raise ValueError(
        "Worldmodel carrier contract reject: source exposes no lowerable "
        "transition carrier. Define step/grid model aliases, PROGRAM, "
        "WORLD_MODEL_SPEC, or PATCH_BASE plus a typed patch delta."
    )


def carrier_purity_error(source: str) -> str | None:
    """Return the purity error for source, or None when no violation is parsed."""
    return carrier_contract_error(source)


def carrier_contract_error(source: str, dynamics_assumption: str | None = None) -> str | None:
    """Return the current carrier-contract error for source, if any."""
    if not isinstance(source, str) or not source.strip():
        return "Worldmodel carrier contract reject: source is empty."
    try:
        validate_worldmodel_carrier_source(source, dynamics_assumption=dynamics_assumption)
    except ValueError as exc:
        return str(exc)
    return None


def validate_worldmodel_carrier_source(source: str, *, dynamics_assumption: str | None = None) -> None:
    """Validate the source-level world-model carrier contract.

    This is the single compatibility door shared by leaf-local preflight,
    candidate memory, patch-base chain validation, and parent gate import.

    dynamics_assumption: "markovian" (default) enforces the syntactic t-read ban.
    "lawful_time" lifts the ban; anti-memorization is discharged by the held-out
    rollout and dominance gates. Env var ZTARE_DYNAMICS_ASSUMPTION overrides this.
    """

    if not isinstance(source, str) or not source.strip():
        raise ValueError("Worldmodel carrier contract reject: source is empty.")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(
            f"Worldmodel carrier contract reject: source is not valid Python: {exc.msg}."
        ) from exc
    validate_worldmodel_transition_contract(tree, dynamics_assumption)
    _validate_literal_catalog_specs(tree)


def _validate_literal_catalog_specs(tree: ast.AST) -> None:
    spec_nodes: dict[str, ast.AST] = {}
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id in {"WORLD_MODEL_SPEC", _PATCH_DELTA_SPEC_NAME}
                ):
                    spec_nodes[target.id] = node.value
        elif isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Name)
                and node.target.id in {"WORLD_MODEL_SPEC", _PATCH_DELTA_SPEC_NAME}
            ):
                spec_nodes[node.target.id] = node.value
    from ztare.worldmodel.spec_catalog import validate_patch_delta_spec, validate_spec

    for name, spec_node in spec_nodes.items():
        try:
            spec = ast.literal_eval(spec_node)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                f"Worldmodel carrier contract reject: {name} must be a literal "
                "catalog spec."
            ) from exc
        validator = validate_patch_delta_spec if name == _PATCH_DELTA_SPEC_NAME else validate_spec
        err = validator(spec)
        if err:
            role_hint = (
                "a dict-valued actions field and at least one catalog rule"
                if name == _PATCH_DELTA_SPEC_NAME
                else "non-empty actions"
            )
            raise ValueError(
                f"Worldmodel carrier contract reject: {name} failed catalog "
                f"validation: {err}. Submit a valid catalog spec with "
                f"{role_hint}."
            )


def _top_level_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                names |= _assigned_names(target)
        elif isinstance(node, ast.AnnAssign):
            names |= _assigned_names(node.target)
    return names


def _assigned_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        out: set[str] = set()
        for elt in target.elts:
            out |= _assigned_names(elt)
        return out
    return set()


def _root_name(node: ast.AST) -> str | None:
    current = node
    while isinstance(current, ast.Subscript):
        current = current.value
    if isinstance(current, ast.Attribute):
        return _root_name(current.value)
    if isinstance(current, ast.Name):
        return current.id
    return None
