from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ztare.validator.fit_primitive import FitDeclaration, FitSuccess


STRUCTURAL_MEMORY_FILENAME = "structural_memory.json"


@dataclass(frozen=True)
class StructuralFamilySignature:
    fingerprint: str
    family_label: str


class _NormalizeFamilyAst(ast.NodeTransformer):
    def __init__(self, independent_vars: list[str], parameter_names: list[str]):
        self._var_map = {name: f"X{i}" for i, name in enumerate(independent_vars)}
        self._param_map = {name: f"P{i}" for i, name in enumerate(parameter_names)}

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id == "math":
            return ast.copy_location(ast.Name(id="math", ctx=node.ctx), node)
        if node.id in self._var_map:
            return ast.copy_location(ast.Name(id=self._var_map[node.id], ctx=node.ctx), node)
        if node.id in self._param_map:
            return ast.copy_location(ast.Name(id=self._param_map[node.id], ctx=node.ctx), node)
        return ast.copy_location(ast.Name(id="N", ctx=node.ctx), node)

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, (int, float)):
            return ast.copy_location(ast.Name(id="CONST", ctx=ast.Load()), node)
        return node


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_structural_family_signature(declaration: FitDeclaration) -> StructuralFamilySignature:
    """Create a stable, coarse structural-family signature from FIT_DECLARATION.

    This is intentionally weaker than a full symbolic classifier. Slice 1 only
    needs durable deduplication and a human-legible family label for prompt
    carry-forward across pivots.
    """

    tree = ast.parse(declaration.expression, mode="eval")
    normalized = _NormalizeFamilyAst(
        declaration.independent_vars,
        declaration.parameter_names,
    ).visit(tree)
    ast.fix_missing_locations(normalized)
    structural_dump = ast.dump(normalized, annotate_fields=False, include_attributes=False)
    fingerprint = "sfam:" + hashlib.sha256(structural_dump.encode("utf-8")).hexdigest()[:16]
    family_label = ast.unparse(normalized.body) if isinstance(normalized, ast.Expression) else structural_dump
    return StructuralFamilySignature(
        fingerprint=fingerprint,
        family_label=family_label,
    )


def _memory_path(workspace_dir: Path) -> Path:
    return workspace_dir / STRUCTURAL_MEMORY_FILENAME


def load_structural_memory(workspace_dir: Path) -> dict[str, Any]:
    path = _memory_path(workspace_dir)
    if not path.exists():
        return {
            "schema_version": 1,
            "updated_at_utc": "",
            "families": [],
            "most_recent_family_fingerprint": "",
            "most_recent_structural_escape_fingerprint": "",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "schema_version": 1,
            "updated_at_utc": "",
            "families": [],
            "most_recent_family_fingerprint": "",
            "most_recent_structural_escape_fingerprint": "",
        }
    if not isinstance(payload, dict):
        return {
            "schema_version": 1,
            "updated_at_utc": "",
            "families": [],
            "most_recent_family_fingerprint": "",
            "most_recent_structural_escape_fingerprint": "",
        }
    payload.setdefault("schema_version", 1)
    payload.setdefault("updated_at_utc", "")
    payload.setdefault("families", [])
    payload.setdefault("most_recent_family_fingerprint", "")
    payload.setdefault("most_recent_structural_escape_fingerprint", "")
    return payload


def update_structural_memory(
    *,
    workspace_dir: Path,
    declaration: FitDeclaration,
    fit_result: FitSuccess,
    iteration_index: int,
    diagnostic_classification: str = "",
) -> dict[str, Any]:
    """Persist coarse structural-family memory across iterations.

    The first slice is deliberately neutral: it records structurally distinct
    families and their visible residual outcomes. It does not declare a family
    "correct"; it preserves run state so later iterations do not unknowingly
    collapse back to iteration-1 behavior after a pivot.
    """

    memory = load_structural_memory(workspace_dir)
    signature = build_structural_family_signature(declaration)
    families = memory.get("families", [])
    if not isinstance(families, list):
        families = []

    existing: dict[str, Any] | None = None
    for item in families:
        if isinstance(item, dict) and item.get("fingerprint") == signature.fingerprint:
            existing = item
            break

    current_best = float(fit_result.max_abs_residual)
    if existing is None:
        existing = {
            "fingerprint": signature.fingerprint,
            "family_label": signature.family_label,
            "example_expression": declaration.expression,
            "independent_vars": list(declaration.independent_vars),
            "first_seen_iteration": iteration_index,
            "last_seen_iteration": iteration_index,
            "seen_count": 1,
            "best_visible_max_abs_residual": current_best,
            "latest_visible_max_abs_residual": current_best,
            "best_rmse": float(fit_result.rmse),
            "latest_diagnostic_classification": diagnostic_classification,
        }
        families.append(existing)
    else:
        existing["last_seen_iteration"] = iteration_index
        existing["seen_count"] = int(existing.get("seen_count", 0) or 0) + 1
        existing["latest_visible_max_abs_residual"] = current_best
        existing["latest_diagnostic_classification"] = diagnostic_classification
        if current_best < float(existing.get("best_visible_max_abs_residual", float("inf"))):
            existing["best_visible_max_abs_residual"] = current_best
            existing["best_rmse"] = float(fit_result.rmse)
            existing["example_expression"] = declaration.expression

    prior_family = str(memory.get("most_recent_family_fingerprint", "") or "")
    if prior_family and prior_family != signature.fingerprint:
        memory["most_recent_structural_escape_fingerprint"] = signature.fingerprint

    memory["families"] = families
    memory["most_recent_family_fingerprint"] = signature.fingerprint
    memory["updated_at_utc"] = _utc_now_iso()
    _memory_path(workspace_dir).write_text(json.dumps(memory, indent=2) + "\n", encoding="utf-8")
    return memory


def render_structural_memory_prompt_section(
    workspace_dir: Path,
    *,
    max_families: int = 4,
) -> str:
    """Render a read-only prompt block for structurally distinct prior families."""

    memory = load_structural_memory(workspace_dir)
    families = memory.get("families", [])
    if not isinstance(families, list) or len(families) < 2:
        return ""

    escape_fp = str(memory.get("most_recent_structural_escape_fingerprint", "") or "")
    family_by_fp = {
        item.get("fingerprint"): item
        for item in families
        if isinstance(item, dict) and item.get("fingerprint")
    }
    ordered: list[dict[str, Any]] = []
    has_escape = False
    if escape_fp and escape_fp in family_by_fp:
        ordered.append(family_by_fp.pop(escape_fp))
        has_escape = True
    ordered.extend(
        sorted(
            family_by_fp.values(),
            key=lambda item: (
                float(item.get("best_visible_max_abs_residual", float("inf"))),
                -int(item.get("last_seen_iteration", 0) or 0),
            ),
        )
    )

    lines = [
        "### GP-042 STRUCTURAL MEMORY (READ-ONLY)",
        "Distinct structural families already reached in this run. This memory survives pivot resets.",
        "Use it to avoid unintentional collapse back to a prior family. Leave a family only for an evidence-grounded reason.",
    ]
    if has_escape:
        lines.append("")
        lines.append("Most recent structural escape is listed first below.")
    lines.append("")
    lines.append("Known structural families:")
    for item in ordered[:max_families]:
        label = str(item.get("family_label", "") or "")
        example_expression = str(item.get("example_expression", "") or "")
        best_residual = item.get("best_visible_max_abs_residual")
        last_iter = item.get("last_seen_iteration")
        diagnostic = str(item.get("latest_diagnostic_classification", "") or "unknown")
        lines.append(
            f"- iter {last_iter}: {label}"
        )
        lines.append(f"  example_expression: {example_expression}")
        lines.append(f"  best_visible_max_abs_residual: {best_residual}")
        lines.append(f"  latest_diagnostic: {diagnostic}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GP-048 Math AST Analyzer
# ---------------------------------------------------------------------------
#
# Extends the existing _NormalizeFamilyAst with two capabilities the rest of
# the stack (preservation lane, retrospective analysis, debriefs) needs:
#
#   1. extract_primitives(tree) -> set[str]
#        Classify a normalized expression into a small structural vocabulary.
#        Vocabulary is intentionally domain-free: no physics names.
#
#   2. tree_edit_distance(tree_a, tree_b) -> int
#        Zhang-Shasha unit-cost tree edit distance over normalized trees.
#
# The normalizer is shared with build_structural_family_signature, which
# already parses, remaps variables/parameters to X_i / P_i, and collapses
# numeric literals to CONST. GP-048 reuses that canonical form.


PRIMITIVE_LABELS = frozenset({
    "power",
    "exp_pos",
    "exp_neg",
    "log",
    "trig",
    "rational_simple",
    "rational_with_additive_offset",
    "sigmoid",
    "polynomial",
    "additive_composition",
    "multiplicative_composition",
    "constant",
})


class ExpressionParseError(ValueError):
    """Raised when GP-048 cannot parse an expression string."""


def normalize_expression(
    expression: str,
    independent_vars: list[str],
    parameter_names: list[str],
) -> ast.AST:
    """Parse and normalize an expression string into a canonical AST.

    The returned tree has:
      - independent_vars remapped to X0, X1, ...
      - parameter_names remapped to P0, P1, ...
      - numeric literals collapsed to a sentinel Name("CONST")
      - unknown names collapsed to Name("N")

    This is the same normalization used for structural family fingerprinting.
    """

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ExpressionParseError(f"failed to parse expression: {exc}") from exc
    normalized = _NormalizeFamilyAst(independent_vars, parameter_names).visit(tree)
    ast.fix_missing_locations(normalized)
    return normalized


def _expr_body(tree: ast.AST) -> ast.AST:
    return tree.body if isinstance(tree, ast.Expression) else tree


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _is_const_name(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and node.id == "CONST"


def _arg_is_negated(node: ast.AST) -> bool:
    """Return True if the top of `node` is syntactically negated.

    Catches `-x`, `-(a*b)`, and the common pattern `(-k) * something` where a
    UnaryOp USub sits at the head of a multiplicative chain.
    """

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _arg_is_negated(node.left) or _arg_is_negated(node.right)
    return False


def _denominator_has_additive_offset(denom: ast.AST) -> bool:
    return isinstance(denom, ast.BinOp) and isinstance(denom.op, (ast.Add, ast.Sub))


def _has_sigmoid(node: ast.AST) -> bool:
    """Detect the 1/(1 + exp(...)) or CONST/(CONST + exp(...)) pattern."""

    for sub in ast.walk(node):
        if not (isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.Div)):
            continue
        denom = sub.right
        if not (isinstance(denom, ast.BinOp) and isinstance(denom.op, ast.Add)):
            continue
        for part in (denom.left, denom.right):
            if isinstance(part, ast.Call) and _call_name(part.func) == "exp":
                return True
    return False


class _PrimitiveExtractor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.primitives: set[str] = set()
        self._has_transcendental = False
        self._pow_const_exponent_seen = False

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, ast.Pow):
            self.primitives.add("power")
            if _is_const_name(node.right):
                self._pow_const_exponent_seen = True
        elif isinstance(node.op, ast.Div):
            if _denominator_has_additive_offset(node.right):
                self.primitives.add("rational_with_additive_offset")
            else:
                self.primitives.add("rational_simple")
        elif isinstance(node.op, (ast.Add, ast.Sub)):
            self.primitives.add("additive_composition")
        elif isinstance(node.op, ast.Mult):
            self.primitives.add("multiplicative_composition")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node.func)
        if name == "exp":
            self._has_transcendental = True
            if node.args and _arg_is_negated(node.args[0]):
                self.primitives.add("exp_neg")
            else:
                self.primitives.add("exp_pos")
        elif name == "log":
            self._has_transcendental = True
            self.primitives.add("log")
        elif name in {"sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh"}:
            self._has_transcendental = True
            self.primitives.add("trig")
        self.generic_visit(node)


def extract_primitives(tree: ast.AST) -> set[str]:
    """Classify a normalized expression tree into the GP-048 primitive vocabulary.

    The returned set is always a subset of PRIMITIVE_LABELS. No domain names
    (physics, queueing, biology) appear in this classification.
    """

    body = _expr_body(tree)
    extractor = _PrimitiveExtractor()
    extractor.visit(body)
    primitives = set(extractor.primitives)

    if _has_sigmoid(body):
        primitives.add("sigmoid")

    if extractor._pow_const_exponent_seen and not extractor._has_transcendental:
        primitives.add("polynomial")

    for sub in ast.walk(body):
        if _is_const_name(sub):
            primitives.add("constant")
            break

    return primitives


# --- Zhang-Shasha tree edit distance -----------------------------------------


def _node_label(node: ast.AST) -> str:
    """Label used for edit-cost comparison. Captures operator class for BinOp,
    identifier for Name/Attribute, type of Constant literal."""

    if isinstance(node, ast.BinOp):
        return f"BinOp:{type(node.op).__name__}"
    if isinstance(node, ast.UnaryOp):
        return f"UnaryOp:{type(node.op).__name__}"
    if isinstance(node, ast.BoolOp):
        return f"BoolOp:{type(node.op).__name__}"
    if isinstance(node, ast.Compare):
        ops = ",".join(type(op).__name__ for op in node.ops)
        return f"Compare:{ops}"
    if isinstance(node, ast.Name):
        return f"Name:{node.id}"
    if isinstance(node, ast.Attribute):
        return f"Attr:{node.attr}"
    if isinstance(node, ast.Call):
        return "Call"
    if isinstance(node, ast.Constant):
        return f"Const:{type(node.value).__name__}"
    return type(node).__name__


_SKIP_FIELDS = {"ctx", "op", "ops"}


def _ordered_children(node: ast.AST) -> list[ast.AST]:
    """Return semantic children of an AST node.

    Skips `ctx` (Load/Store markers), `op` (BinOp/UnaryOp operator — encoded
    in the node label), and `ops` (Compare operator list — also in the
    label). Also skips operator-type singletons (Add, Sub, ...).
    """

    children: list[ast.AST] = []
    for field, value in ast.iter_fields(node):
        if field in _SKIP_FIELDS:
            continue
        if isinstance(value, ast.AST):
            if isinstance(value, (ast.operator, ast.unaryop, ast.boolop, ast.cmpop, ast.expr_context)):
                continue
            children.append(value)
        elif isinstance(value, list):
            for item in value:
                if not isinstance(item, ast.AST):
                    continue
                if isinstance(item, (ast.operator, ast.unaryop, ast.boolop, ast.cmpop, ast.expr_context)):
                    continue
                children.append(item)
    return children


def _flatten_postorder(root: ast.AST) -> tuple[list[ast.AST], list[int]]:
    """Return (post-order list, leftmost-leaf descendant indices) for ZS DP."""

    post: list[ast.AST] = []
    leftmost: dict[int, int] = {}

    def _walk(node: ast.AST) -> int:
        children = _ordered_children(node)
        if not children:
            idx = len(post)
            post.append(node)
            leftmost[id(node)] = idx
            return idx
        first_lm = _walk(children[0])
        for child in children[1:]:
            _walk(child)
        idx = len(post)
        post.append(node)
        leftmost[id(node)] = first_lm
        return first_lm

    _walk(root)
    lld = [leftmost[id(n)] for n in post]
    return post, lld


def _keyroots(lld: list[int]) -> list[int]:
    seen: dict[int, int] = {}
    for i, l in enumerate(lld):
        seen[l] = i
    return sorted(seen.values())


def tree_edit_distance(tree_a: ast.AST, tree_b: ast.AST) -> int:
    """Zhang-Shasha tree edit distance with unit insert/delete/relabel costs.

    Operates on normalized AST bodies. The distance is the minimum number of
    single-node edits (insert/delete/relabel) that transforms one tree into the
    other.
    """

    a = _expr_body(tree_a)
    b = _expr_body(tree_b)
    post_a, lld_a = _flatten_postorder(a)
    post_b, lld_b = _flatten_postorder(b)
    labels_a = [_node_label(n) for n in post_a]
    labels_b = [_node_label(n) for n in post_b]
    n = len(post_a)
    m = len(post_b)
    if n == 0 and m == 0:
        return 0
    if n == 0:
        return m
    if m == 0:
        return n

    td = [[0] * m for _ in range(n)]
    kr_a = _keyroots(lld_a)
    kr_b = _keyroots(lld_b)

    for i in kr_a:
        for j in kr_b:
            li = lld_a[i]
            lj = lld_b[j]
            size_i = i - li + 2
            size_j = j - lj + 2
            fd = [[0] * size_j for _ in range(size_i)]
            for di in range(1, size_i):
                fd[di][0] = fd[di - 1][0] + 1
            for dj in range(1, size_j):
                fd[0][dj] = fd[0][dj - 1] + 1
            for di in range(1, size_i):
                for dj in range(1, size_j):
                    ai = li + di - 1
                    bj = lj + dj - 1
                    if lld_a[ai] == li and lld_b[bj] == lj:
                        cost = 0 if labels_a[ai] == labels_b[bj] else 1
                        fd[di][dj] = min(
                            fd[di - 1][dj] + 1,
                            fd[di][dj - 1] + 1,
                            fd[di - 1][dj - 1] + cost,
                        )
                        td[ai][bj] = fd[di][dj]
                    else:
                        pi = lld_a[ai] - li
                        pj = lld_b[bj] - lj
                        fd[di][dj] = min(
                            fd[di - 1][dj] + 1,
                            fd[di][dj - 1] + 1,
                            fd[pi][pj] + td[ai][bj],
                        )
    return td[n - 1][m - 1]
