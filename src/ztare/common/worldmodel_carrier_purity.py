from __future__ import annotations

import ast
import os


_TRANSITION_FUNCTION_NAMES = {"step", "PATCH_DELTA"}
_PREDICTOR_NAMES = {"step", "f", "model", "I_model"}
_PROGRAM_NAMES = {"PROGRAM", "WORLD_MODEL_SPEC"}
_PATCH_BASE_NAMES = {"PATCH_BASE", "PATCH_BASE_REF", "PATCH_BASE_PATH"}
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
    has_patch_base = bool(names & _PATCH_BASE_NAMES)
    if has_patch_delta or has_patch_base:
        if not has_patch_delta:
            raise ValueError(
                "Worldmodel carrier contract reject: PATCH_BASE requires callable PATCH_DELTA."
            )
        if not has_patch_base:
            raise ValueError(
                "Worldmodel carrier contract reject: PATCH_DELTA is a patch "
                "combiner, not a standalone transition law. Declare PATCH_BASE "
                "with a gate-supplied full sha256, or submit a direct step/PROGRAM/"
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
        "WORLD_MODEL_SPEC, or PATCH_BASE plus PATCH_DELTA."
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
    _validate_literal_world_model_spec(tree)


def _validate_literal_world_model_spec(tree: ast.AST) -> None:
    spec_node: ast.AST | None = None
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "WORLD_MODEL_SPEC" for t in node.targets):
                spec_node = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "WORLD_MODEL_SPEC":
                spec_node = node.value
    if spec_node is None:
        return
    try:
        spec = ast.literal_eval(spec_node)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(
            "Worldmodel carrier contract reject: WORLD_MODEL_SPEC must be a "
            "literal catalog spec. If submitting executable Python instead, "
            "omit WORLD_MODEL_SPEC and define step(grid, action, t), PROGRAM, "
            "or model aliases directly."
        ) from exc
    from ztare.worldmodel.spec_catalog import validate_spec

    err = validate_spec(spec)
    if err:
        raise ValueError(
            "Worldmodel carrier contract reject: WORLD_MODEL_SPEC failed "
            f"catalog validation: {err}. Submit a valid catalog spec with "
            "non-empty actions, or omit WORLD_MODEL_SPEC and define executable "
            "step(grid, action, t)."
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
