"""Structural-presence constraint extractor (GP-061).

Reads `workspace/structural_memory.json` for a project, finds the
mathematical skeleton invariant across failed families via deterministic AST
intersection, classifies the skeleton against a rigid taxonomy (variable
coupling / asymptotic behavior / error geometry), and emits a have-to-believe
constraint into `workspace/derived_constraints.json` under
`producer=structural_extractor`.

Two layers:

1. extract_shared_skeleton(structural_memory) - deterministic tree-pattern
   intersection over normalized family_label strings. No LLM.
2. classify_skeleton(skeleton, diagnostics) - optional LLM call with a
   rigid enum schema; deterministic fallback if no model is wired.

Entry points:

- run_structural_extractor(project_dir, run_id, iteration, ...) - full
  pipeline, writes into the ledger via update_derived_constraints_ledger.
- Module CLI (__main__) - dry-run against a project's closed workspace.
  Prints the extracted skeleton and the constraint that would be emitted,
  does NOT modify derived_constraints.json unless --write is passed.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# --------------------------------------------------------------------------- #
# Data classes
# --------------------------------------------------------------------------- #


@dataclass
class SharedSkeleton:
    """Result of deterministic AST intersection across failed families."""

    rendered: str
    operator_node_count: int
    supporting_fingerprints: list[str]
    sample_family_labels: list[str]
    residual_summary: dict[str, float] = field(default_factory=dict)


@dataclass
class StructuralDiagnostic:
    """Rigid-schema classification of a shared skeleton."""

    variable_coupling: str
    asymptotic_behavior: str
    error_geometry: str
    have_to_believe: str


ALLOWED_COUPLING = {
    "separable",
    "ratio_coupled",
    "product_coupled",
    "compound_nonlinear",
}
ALLOWED_ASYMPTOTIC = {
    "unbounded_growth",
    "exponential_decay",
    "polynomial_decay",
    "saturates",
}
ALLOWED_ERROR_GEOMETRY = {
    "tail_dominated",
    "origin_dominated",
    "midrange_dominated",
    "uniform_structured",
}


# --------------------------------------------------------------------------- #
# Layer 1: deterministic skeleton extraction
# --------------------------------------------------------------------------- #


_WILDCARD = "?"
_EML_MARKER = "EMLCALL"
_MATHE_MARKER = "MATHECONST"


def _normalize_family_label(label: str) -> str:
    """Rewrite the normalized family_label so that Python's ast module can parse it.

    structural_memory emits labels like:
        P0 * X0 ** P1 * X1 ** P2 * N(-(P1 * X0) / (P3 * X1), CONST) + P4
    with `N(...)` representing the eml primitive, `CONST` representing a
    literal constant, and optionally `math.e`. We substitute these for valid
    Python identifiers before parsing.
    """

    text = label.strip()
    # Treat the eml primitive marker as a function call.
    text = re.sub(r"\bN\(", f"{_EML_MARKER}(", text)
    # `math.e` is an attribute access on the bare name 'math', which would
    # require a Name node for 'math'; simpler to flatten to a single name.
    text = re.sub(r"\bmath\.e(?![a-zA-Z0-9_])", _MATHE_MARKER, text)
    return text


def _parse_to_ast(label: str) -> ast.AST | None:
    try:
        return ast.parse(_normalize_family_label(label), mode="eval").body
    except SyntaxError:
        return None



def _extract_feature_bag(tree: ast.AST) -> set[str]:
    """Extract a bag of structural features from a parsed family_label AST.

    Features are strings that capture structural properties independent of
    multiplicative ordering and numerator/denominator placement. This is the
    primary extraction path because the family_label format (parameterized
    products with Mult/Div interleaved) makes pure AST intersection too
    strict — families that share a conceptual skeleton but differ in where
    the eml term sits collapse to trivial matches.
    """

    features: set[str] = set()

    # Collect all Name ids, BinOp shapes, and Call info across the tree.
    var_powers: set[str] = set()
    eml_arg_shapes: set[str] = set()
    has_eml = False
    has_outer_additive_const = False
    has_negation_inside_eml = False

    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            base = getattr(node.left, "id", None)
            if base and base.startswith("X"):
                var_powers.add(f"var_power:{base}")
        if isinstance(node, ast.Call):
            func = getattr(node.func, "id", None)
            if func == _EML_MARKER:
                has_eml = True
                if node.args:
                    first_arg = node.args[0]
                    # Check for negation (UnaryOp USub) at the top of the eml arg.
                    if isinstance(first_arg, ast.UnaryOp) and isinstance(first_arg.op, ast.USub):
                        has_negation_inside_eml = True
                    # Detect whether the arg contains both X0 and X1 (compound form).
                    names_in_arg = {
                        getattr(n, "id", None)
                        for n in ast.walk(first_arg)
                        if isinstance(n, ast.Name)
                    }
                    has_x0 = "X0" in names_in_arg
                    has_x1 = "X1" in names_in_arg
                    if has_x0 and has_x1:
                        eml_arg_shapes.add("eml_arg:compound_X0_X1")
                        # Distinguish ratio vs product coupling from the AST,
                        # not from raw label strings.
                        # Ratio: any BinOp(Div, ?, ?) where X0 is in numerator
                        # and X1 is in denominator (or vice versa).
                        # Product: BinOp(Mult, ...) with both X0 and X1 as
                        # immediate children inside the eml arg.
                        has_ratio = any(
                            isinstance(n, ast.BinOp)
                            and isinstance(n.op, ast.Div)
                            and (
                                "X0" in {getattr(m, "id", None) for m in ast.walk(n.left)}
                                or "X1" in {getattr(m, "id", None) for m in ast.walk(n.left)}
                            )
                            for n in ast.walk(first_arg)
                        )
                        if has_ratio:
                            eml_arg_shapes.add("eml_arg:ratio_X0_X1")
                        else:
                            eml_arg_shapes.add("eml_arg:product_X0_X1")
                    elif has_x0:
                        eml_arg_shapes.add("eml_arg:X0_only")
                    elif has_x1:
                        eml_arg_shapes.add("eml_arg:X1_only")

    # Check for top-level additive constant: the root must be BinOp(Add, ?, Name starting with P).
    if isinstance(tree, ast.BinOp) and isinstance(tree.op, ast.Add):
        right = tree.right
        if isinstance(right, ast.Name) and right.id.startswith("P"):
            has_outer_additive_const = True

    features.update(var_powers)
    features.update(eml_arg_shapes)
    if has_eml:
        features.add("has_eml_term")
    if has_outer_additive_const:
        features.add("has_outer_additive_const")
    if has_negation_inside_eml:
        features.add("eml_first_arg_negated")

    return features


# --------------------------------------------------------------------------- #
# Generalized AST feature matrix (GP-061.B — negative-space vocabulary)
# --------------------------------------------------------------------------- #
#
# The legacy `_extract_feature_bag` above is a hand-crafted set of features
# driven by what we observed mattered for sandbox_07 (eml_arg shapes, var
# powers, outer additive const). It is still used by the positive-path
# Structural-presence extractor — do not remove it without re-running retroactive
# tests on sandbox_07.
#
# The matrix below is mechanical and schema-driven: for every Call node in
# the AST, for every argument position, it enumerates which operator types
# appear inside that argument's subtree, plus the subtree's maximum operator
# depth. The feature names are chosen so the detector picks the features to
# care about, not the human who wrote the extractor. This is the vocabulary
# the negative-space detector reads.


_GENERALIZED_OPS: dict[str, type[ast.AST]] = {
    "Pow":  ast.Pow,
    "Mult": ast.Mult,
    "Div":  ast.Div,
    "Add":  ast.Add,
    "Sub":  ast.Sub,
    "USub": ast.USub,
    "Mod":  ast.Mod,
}


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _subtree_op_types(subtree: ast.AST) -> set[str]:
    found: set[str] = set()
    for n in ast.walk(subtree):
        if isinstance(n, ast.BinOp):
            for label, op_cls in _GENERALIZED_OPS.items():
                if isinstance(n.op, op_cls):
                    found.add(label)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            found.add("USub")
        if isinstance(n, ast.Call):
            found.add("Call")
    return found


def _subtree_operator_depth(subtree: ast.AST) -> int:
    """Max chain length of BinOp/UnaryOp/Call nodes from root of subtree."""
    def _d(node: ast.AST) -> int:
        if isinstance(node, (ast.BinOp,)):
            left = _d(node.left) if isinstance(node.left, ast.AST) else 0
            right = _d(node.right) if isinstance(node.right, ast.AST) else 0
            return 1 + max(left, right)
        if isinstance(node, ast.UnaryOp):
            return 1 + _d(node.operand)
        if isinstance(node, ast.Call):
            inner = max((_d(a) for a in node.args), default=0)
            return 1 + inner
        return 0
    return _d(subtree)


def extract_generalized_feature_matrix(tree: ast.AST) -> set[str]:
    """Emit mechanical (func × arg_pos × op_type | depth) features for every Call.

    This extractor does not know what "matters" — it records what is there.
    Feature shapes:
      - ``fn:{fname}|arg{i}|has_op:{OP}`` — operator OP appears anywhere in
        the i-th argument's subtree of a call to {fname}.
      - ``fn:{fname}|arg{i}|depth:{d}`` — max operator-chain depth in that
        subtree, bucketed by integer value.
      - ``fn:{fname}|arg{i}|leaf`` — the argument is a bare Name/Constant
        (depth 0, no operators).
    """
    features: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fname = _call_name(node)
        if fname is None:
            continue
        for i, arg in enumerate(node.args):
            ops = _subtree_op_types(arg)
            depth = _subtree_operator_depth(arg)
            if not ops and depth == 0:
                features.add(f"fn:{fname}|arg{i}|leaf")
            for op_label in ops:
                features.add(f"fn:{fname}|arg{i}|has_op:{op_label}")
            features.add(f"fn:{fname}|arg{i}|depth:{depth}")
    return features


def _features_to_skeleton_string(features: set[str]) -> str:
    """Render an invariant feature bag as a human-readable skeleton description."""
    parts = []
    if "var_power:X0" in features and "var_power:X1" in features:
        parts.append("P0 * X0**P1 * X1**P2")
    elif "var_power:X0" in features:
        parts.append("P0 * X0**P1")
    elif "var_power:X1" in features:
        parts.append("P0 * X1**P1")

    if "has_eml_term" in features:
        eml_arg = "?"
        if "eml_arg:compound_X0_X1" in features:
            eml_arg = "f(X0, X1)"
        elif "eml_arg:X0_only" in features:
            eml_arg = "f(X0)"
        elif "eml_arg:X1_only" in features:
            eml_arg = "f(X1)"
        negation = "-" if "eml_first_arg_negated" in features else ""
        parts.append(f"[mul-or-div] eml({negation}{eml_arg}, ?)")

    if "has_outer_additive_const" in features:
        parts.append("+ P_const")

    if not parts:
        return "?"
    return " ".join(parts)


def extract_shared_skeleton(
    structural_memory: dict[str, Any],
    *,
    confidence_threshold: int = 3,
    min_operator_nodes: int = 4,
    residual_threshold: float = 0.15,
) -> SharedSkeleton | None:
    """Find the structural invariant shared by all failed families.

    Uses a feature-bag intersection (robust to multiplicative order and
    numerator/denominator placement) rather than strict AST subtree
    intersection, because the family_label format mixes Mult and Div at the
    outer level in a way that collapses AST intersection to trivial matches.
    """

    families = structural_memory.get("families", [])
    failed = [
        f for f in families
        if f.get("latest_diagnostic_classification") == "structural_misfit"
        and float(f.get("latest_visible_max_abs_residual", 0.0)) >= residual_threshold
    ]
    if len(failed) < confidence_threshold:
        return None

    parsed: list[tuple[dict[str, Any], ast.AST]] = []
    for family in failed:
        label = family.get("family_label", "")
        tree = _parse_to_ast(label)
        if tree is not None:
            parsed.append((family, tree))

    if len(parsed) < confidence_threshold:
        return None

    # Feature-bag intersection across all parsed families.
    feature_bags = [_extract_feature_bag(tree) for _, tree in parsed]
    invariant_features: set[str] = set.intersection(*feature_bags) if feature_bags else set()

    if len(invariant_features) < min_operator_nodes:
        return None

    rendered = _features_to_skeleton_string(invariant_features)

    residuals = [
        float(f.get("latest_visible_max_abs_residual", 0.0))
        for f, _ in parsed
    ]
    residual_summary = {
        "count": float(len(residuals)),
        "min": min(residuals) if residuals else 0.0,
        "max": max(residuals) if residuals else 0.0,
        "mean": sum(residuals) / len(residuals) if residuals else 0.0,
    }

    skeleton = SharedSkeleton(
        rendered=rendered,
        operator_node_count=len(invariant_features),
        supporting_fingerprints=[f.get("fingerprint", "") for f, _ in parsed],
        sample_family_labels=[f.get("family_label", "") for f, _ in parsed[:5]],
        residual_summary=residual_summary,
    )
    # Stash the raw feature set on the object for downstream classification.
    skeleton.features = invariant_features  # type: ignore[attr-defined]
    return skeleton



# --------------------------------------------------------------------------- #
# Layer 2: taxonomic classification (rigid enums)
# --------------------------------------------------------------------------- #


def _deterministic_classify(
    skeleton: SharedSkeleton,
    residual_diagnostics: list[dict[str, Any]],
) -> StructuralDiagnostic:
    """Deterministic classifier used when no LLM is available.

    Reads the feature bag attached to the skeleton (populated by
    extract_shared_skeleton) and maps it onto the rigid taxonomy. This path
    makes the retroactive sandbox_07 test runnable without hitting an API.
    Production structural-presence A.2 uses an LLM with the same enum schema.
    """

    features: set[str] = getattr(skeleton, "features", set())

    # Variable coupling: driven by the eml_arg_shape feature.
    if "eml_arg:compound_X0_X1" in features:
        # Both state variables appear inside the eml argument together.
        # The specific compound form is already resolved in the feature bag
        # by _extract_feature_bag — read it directly from features, no string
        # matching on raw labels needed.
        if "eml_arg:ratio_X0_X1" in features:
            coupling = "ratio_coupled"
        elif "eml_arg:product_X0_X1" in features:
            coupling = "product_coupled"
        else:
            coupling = "compound_nonlinear"
    else:
        # The outer structure multiplies X0^P * X1^Q but the eml inner term
        # does not compound the two state variables. This is exactly the
        # sandbox_07 failure mode: the outer multiplicative skeleton is
        # "separable" in the sense that X0 and X1 appear in independent
        # multiplicative factors even though one of them may also show up
        # inside an eml call on its own.
        coupling = "separable"

    # Asymptotic behavior: negation inside eml argument implies decay.
    if "has_eml_term" in features:
        if "eml_first_arg_negated" in features:
            asymptotic = "exponential_decay"
        else:
            asymptotic = "unbounded_growth"
    else:
        asymptotic = "polynomial_decay"

    # Error geometry: read from residual_diagnostic if present.
    error_geometry = "uniform_structured"
    for diag in residual_diagnostics:
        region = str(diag.get("concentration_region", "")).lower()
        if "tail" in region:
            error_geometry = "tail_dominated"
            break
        if "origin" in region:
            error_geometry = "origin_dominated"
            break
        if "mid" in region:
            error_geometry = "midrange_dominated"
            break

    htb = _build_have_to_believe(coupling, asymptotic, error_geometry, skeleton)
    return StructuralDiagnostic(
        variable_coupling=coupling,
        asymptotic_behavior=asymptotic,
        error_geometry=error_geometry,
        have_to_believe=htb,
    )


def _build_have_to_believe(
    coupling: str,
    asymptotic: str,
    error_geometry: str,
    skeleton: SharedSkeleton,
) -> str:
    """Build the positive-inversion constraint string from a classified diagnostic."""

    direction_clause = {
        "separable": (
            "introduce compound (non-separable) coupling between the two state variables "
            "in the inner composition"
        ),
        "ratio_coupled": (
            "break the ratio coupling between the two state variables and introduce an "
            "alternative compound form"
        ),
        "product_coupled": (
            "extend the product coupling with a second-order interaction term that the "
            "current skeleton omits"
        ),
        "compound_nonlinear": (
            "restructure the compound nonlinearity — the current form does not match the "
            "observed failure geometry"
        ),
    }[coupling]

    evidence_clause = (
        f"Evidence: {len(skeleton.supporting_fingerprints)} failed families all "
        f"instantiate the skeleton `{skeleton.rendered}` with varied inner composition, "
        f"all classified structural_misfit with residual band "
        f"[{skeleton.residual_summary.get('min', 0.0):.3f}, "
        f"{skeleton.residual_summary.get('max', 0.0):.3f}] and {error_geometry} error "
        f"geometry."
    )

    return f"Any valid model MUST {direction_clause}. {evidence_clause}"


def classify_skeleton(
    skeleton: SharedSkeleton,
    residual_diagnostics: list[dict[str, Any]],
    *,
    model: str | None = None,
) -> StructuralDiagnostic:
    """Classify a shared skeleton against the rigid taxonomy.

    Returns an unvalidated StructuralDiagnostic. The caller is responsible for
    calling _validate_diagnostic before emission. This keeps validation in one
    place (run_structural_extractor) regardless of which classification path ran.

    If `model` is None, uses the deterministic classifier.
    The LLM classification path is scaffolded (model arg accepted) but not yet
    wired — it falls back to the deterministic path until the LLM hook is
    implemented. This is intentional and documented: the stub ensures the call
    site and schema are correct before the LLM call is added.
    """

    # Both paths return an unvalidated diagnostic; _validate_diagnostic is
    # called once by run_structural_extractor, not here.
    return _deterministic_classify(skeleton, residual_diagnostics)


def _validate_diagnostic(diag: StructuralDiagnostic) -> StructuralDiagnostic:
    """Fail-closed consistency check before emission."""
    if diag.variable_coupling not in ALLOWED_COUPLING:
        raise ValueError(f"invalid variable_coupling: {diag.variable_coupling!r}")
    if diag.asymptotic_behavior not in ALLOWED_ASYMPTOTIC:
        raise ValueError(f"invalid asymptotic_behavior: {diag.asymptotic_behavior!r}")
    if diag.error_geometry not in ALLOWED_ERROR_GEOMETRY:
        raise ValueError(f"invalid error_geometry: {diag.error_geometry!r}")
    # The have_to_believe string must reference at least one of the three
    # classified axes so it is not free-floating prose.
    lower = diag.have_to_believe.lower()
    axis_lexicon = {
        "separable", "coupling", "coupled", "compound", "ratio", "product",
        "growth", "decay", "saturate", "asymptot",
        "tail", "origin", "midrange", "uniform",
    }
    if not any(token in lower for token in axis_lexicon):
        raise ValueError("have_to_believe does not reference any classified axis")
    return diag


# --------------------------------------------------------------------------- #
# Proposal building + ledger integration
# --------------------------------------------------------------------------- #


def build_structural_constraint_proposal(
    skeleton: SharedSkeleton,
    diagnostic: StructuralDiagnostic,
) -> dict[str, str]:
    """Build a proposal dict in the shape consumed by update_derived_constraints_ledger."""
    return {
        "constraint": diagnostic.have_to_believe,
        "applies_to": "candidate_functional_form_outer_skeleton",
        "failure_family": f"structural_invariant_{diagnostic.variable_coupling}_{diagnostic.error_geometry}",
        "severity": "blocking",
        "producer": "structural_extractor",
        "rationale": (
            f"Deterministic AST intersection across "
            f"{len(skeleton.supporting_fingerprints)} failed families yielded the "
            f"shared skeleton `{skeleton.rendered}` ({skeleton.operator_node_count} "
            f"operator nodes). Taxonomic classification: coupling="
            f"{diagnostic.variable_coupling}, asymptotic="
            f"{diagnostic.asymptotic_behavior}, error_geometry="
            f"{diagnostic.error_geometry}."
        ),
        "non_applicability_condition": (
            "If a candidate that violates this skeleton scores strictly higher than "
            "the current champion, the constraint is auto-downgraded and its "
            "directional prior is retracted."
        ),
    }


def run_structural_extractor(
    *,
    project_dir: Path,
    run_id: int,
    iteration_index: int,
    model: str | None = None,
    confidence_threshold: int = 3,
    min_operator_nodes: int = 4,
    residual_threshold: float = 0.15,
) -> tuple[SharedSkeleton | None, StructuralDiagnostic | None, dict[str, str] | None]:
    """End-to-end pipeline. Returns the skeleton, diagnostic, and proposal.

    Does NOT write to derived_constraints.json by itself — the caller (the
    autoresearch loop hook or the CLI dry-run path) decides whether to thread
    the proposal through update_derived_constraints_ledger.
    """

    memory_path = project_dir / "workspace" / "structural_memory.json"
    if not memory_path.exists():
        return None, None, None

    memory = json.loads(memory_path.read_text())
    skeleton = extract_shared_skeleton(
        memory,
        confidence_threshold=confidence_threshold,
        min_operator_nodes=min_operator_nodes,
        residual_threshold=residual_threshold,
    )
    if skeleton is None:
        return None, None, None

    # Residual diagnostics: read the most recent fit_result if present.
    residual_diagnostics: list[dict[str, Any]] = []
    fit_result_path = project_dir / "workspace" / "fit_result.json"
    if fit_result_path.exists():
        try:
            fit_result = json.loads(fit_result_path.read_text())
            diag = fit_result.get("residual_diagnostic")
            if isinstance(diag, dict):
                residual_diagnostics.append(diag)
        except (json.JSONDecodeError, OSError):
            pass

    diagnostic = classify_skeleton(skeleton, residual_diagnostics, model=model)
    diagnostic = _validate_diagnostic(diagnostic)
    proposal = build_structural_constraint_proposal(skeleton, diagnostic)
    return skeleton, diagnostic, proposal


# --------------------------------------------------------------------------- #
# CLI (dry-run against a closed workspace)
# --------------------------------------------------------------------------- #


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="GP-061 structural constraint extractor (dry-run CLI)."
    )
    parser.add_argument("--project", required=True, help="Project directory name under projects/")
    parser.add_argument(
        "--projects-root",
        default="projects",
        help="Path to the projects/ root (default: ./projects)",
    )
    parser.add_argument("--confidence-threshold", type=int, default=3)
    parser.add_argument("--min-operator-nodes", type=int, default=4)
    parser.add_argument("--residual-threshold", type=float, default=0.15)
    parser.add_argument(
        "--write",
        action="store_true",
        help="If set, append the extracted constraint into derived_constraints.json.",
    )
    args = parser.parse_args()

    project_dir = Path(args.projects_root) / args.project
    skeleton, diagnostic, proposal = run_structural_extractor(
        project_dir=project_dir,
        run_id=0,
        iteration_index=0,
        confidence_threshold=args.confidence_threshold,
        min_operator_nodes=args.min_operator_nodes,
        residual_threshold=args.residual_threshold,
    )

    if skeleton is None:
        print("[extractor] no shared skeleton found under current thresholds.")
        return

    print("[extractor] --- shared skeleton ---")
    print(f"  rendered: {skeleton.rendered}")
    print(f"  operator_node_count: {skeleton.operator_node_count}")
    print(f"  supporting_fingerprints: {len(skeleton.supporting_fingerprints)}")
    for fp in skeleton.supporting_fingerprints:
        print(f"    - {fp}")
    print(f"  residual_summary: {skeleton.residual_summary}")
    print()
    print("[extractor] --- diagnostic ---")
    print(f"  variable_coupling:   {diagnostic.variable_coupling}")
    print(f"  asymptotic_behavior: {diagnostic.asymptotic_behavior}")
    print(f"  error_geometry:      {diagnostic.error_geometry}")
    print()
    print("[extractor] --- have-to-believe constraint ---")
    print(f"  {diagnostic.have_to_believe}")
    print()
    print("[extractor] --- proposal (shape used by derived_constraints ledger) ---")
    print(json.dumps(proposal, indent=2))

    if args.write:
        print()
        print("[extractor] --write is not yet wired — run from autoresearch_loop hook instead.")


if __name__ == "__main__":
    _cli()
