"""GP-174 Phase 1 — Parallel-mutator recombination pipeline.

PANEL REVIEW PENDING. This is the "ship while reviewers debate" cut. The
five-seat panel review (genetic-programming, LLM-ensembling, MCTS,
adversarial-ML, apparatus-systems) is in-flight; this module is built
modularly so panel-recommended changes apply as drop-in patches without
restructuring.

Composition (per GP-174 §2):

    Stage 1: K Parallel Mutators           (already shipped 2026-04-27
                                             at autoresearch_loop wire-in)
    Stage 2: AST Crossover                  (this module)
    Stage 3: Persona-Fusion synthesis       (this module)
    Stage 4: Tournament + extended scoring  (this module)
    Stage 5: Adversarial Refinement         (deferred to Phase 2)

Default behavior: disabled. Opt-in via rubric `enable_recombination=True`
plus `parallel_mutator_k >= 2`. With either flag off, this module is
inert — autoresearch_loop falls back to the existing tournament-only
pick_best_candidate path.

Failure-mode posture (per GP-174 §3 catalog):

  * FM-2a — AST crossover requires shared-skeleton: enforced via the
    skeleton-hash pre-check in `_shared_skeleton_pairs`. Pairs whose
    top-level operator structure differs are skipped (logged as
    "skeleton_mismatch"), the originals still enter the tournament.

  * FM-2b — variable/parameter aliasing: each parent's PARAMETER_NAMES
    list is captured pre-crossover; post-crossover hybrids are scanned
    for cross-parent name collisions and rewritten with namespaced
    placeholders. If renaming would collapse the form's degrees of
    freedom, the hybrid is discarded.

  * FM-2d — round-trip serialization: each input is round-trip tested
    via apparatus→sympy→apparatus before crossover; failures are logged
    and that parent skipped from crossover (still enters tournament).

  * FM-3a — fusion regression-to-mean: the fusion prompt explicitly
    asks for the LEAST-common structural fragment per candidate, and
    the fusion result is hashed against each input; identical-hash
    fusion is demoted in scoring.

  * FM-X-a — R1 contract failure compounding: pre-crossover R1 sanity
    check (parametric_form extracted + parses + has at least one feature
    + at least one parameter) gates which candidates enter crossover.
    Crossover does NOT re-run if all K mutators failed R1 (early abort).

  * FM-X-b — telemetry: every candidate carries a `stage_origin` field;
    `pipeline_log.jsonl` records the per-iter breakdown.

Public API:

    recombine(blitz_results, runtime, model_id, prior_champion_form,
              workspace_dir, iter_idx, rubric_data) -> RecombineResult

    Returns the EXPANDED candidate pool (originals + valid crossovers +
    fusion) and a structured pipeline log entry. Caller (autoresearch_loop)
    passes the expanded pool through pick_best_candidate.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ── Apparatus parametric-form parsing helpers ─────────────────────────


# Feature/param index regexes — needed at the form-string level (after
# extraction). These stay regex-based because they operate on the
# already-extracted form string, not on the surrounding Python source.
# `_PARAMETER_NAMES_PATTERN` is also kept (regex) for the assemble-
# crossover-thesis REPLACE operation, where AST round-tripping the
# entire python block would be invasive. Extraction is AST-based;
# this regex is only used to splice a new PARAMETER_NAMES list back
# into a python block during hybrid assembly.
_PARAMETER_NAMES_PATTERN = re.compile(
    r'PARAMETER_NAMES\s*=\s*(\[.*?\])',
    re.DOTALL,
)
_FEATURES_INDEX_PATTERN = re.compile(r"features\[\s*['\"]([^'\"]+)['\"]\s*\]")
_PARAMS_GET_PATTERN = re.compile(
    r"params\.get\(\s*['\"]([^'\"]+)['\"]\s*(?:,\s*([^)]*))?\)"
)
_PARAMS_INDEX_PATTERN = re.compile(r"params\[\s*['\"]([^'\"]+)['\"]\s*\]")


def _extract_python_block(text: str) -> Optional[str]:
    """Pull the Python source from a thesis. Two supported layouts:
      (a) markdown thesis with fenced ```python ... ``` block (typical
          mutator output piped through autoresearch_loop)
      (b) raw .py content (a test_model.py file fed directly)

    Returns None when neither pattern yields anything Python-like.
    """
    if not text:
        return None
    # (a) fenced block — non-greedy across newlines
    m = re.search(r"```python(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1)
    # (b) raw .py — heuristic: top-level PARAMETRIC_FORM AND def/import
    if "PARAMETRIC_FORM" in text and ("def " in text or "import " in text):
        return text
    return None


def _ast_module_assignments(source: str):
    """Yield (target_name, value_node) for each module-level assignment
    in `source`. Tolerant: returns nothing if the source has any syntax
    error; caller treats that as 'no assignments found'.
    """
    import ast
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    yield t.id, node.value


def extract_parametric_form(thesis_text: str) -> Optional[str]:
    """AST-based PARAMETRIC_FORM extraction. Handles every Python
    string-literal layout the mutator produces:

      • PARAMETRIC_FORM = "single line"
      • PARAMETRIC_FORM = ( "line1 " "line2" )      # implicit concat
      • PARAMETRIC_FORM = '''triple-quoted'''
      • PARAMETRIC_FORM = "a" \\
                           "b"                     # backslash-continued

    Python's compiler folds adjacent string literals into a single
    `Constant` node at parse time, so `ast.literal_eval` on that node
    returns the concatenated string regardless of source layout.

    Returns None if the python block doesn't exist, has a syntax error,
    or PARAMETRIC_FORM isn't assigned to a literal-evaluable expression.
    """
    body = _extract_python_block(thesis_text)
    if not body:
        return None
    import ast
    for name, value in _ast_module_assignments(body):
        if name != "PARAMETRIC_FORM":
            continue
        try:
            v = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            # Fallback: try unparsing the expression — covers exotic
            # cases like `"a" + "b"` which literal_eval doesn't handle.
            try:
                txt = ast.unparse(value).strip()
                # Strip outer quotes if it's still a quoted literal
                if (txt.startswith('"') and txt.endswith('"')) or \
                   (txt.startswith("'") and txt.endswith("'")):
                    txt = txt[1:-1]
                return txt
            except Exception:
                return None
        if isinstance(v, str):
            return v.strip()
    return None


def extract_parameter_names(thesis_text: str) -> list[str]:
    """AST-based PARAMETER_NAMES extraction. Same robustness as
    `extract_parametric_form`. Returns [] when absent or non-list.
    """
    body = _extract_python_block(thesis_text)
    if not body:
        return []
    import ast
    for name, value in _ast_module_assignments(body):
        if name != "PARAMETER_NAMES":
            continue
        try:
            v = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return []
        if isinstance(v, (list, tuple)):
            return [str(x) for x in v]
    return []


def collect_form_features(form: str) -> set[str]:
    """Set of features['k'] keys referenced by a parametric form."""
    return set(_FEATURES_INDEX_PATTERN.findall(form))


def collect_form_params(form: str) -> set[str]:
    """Set of params keys referenced by a parametric form (both .get and
    bracket-index access patterns)."""
    a = set(_PARAMS_GET_PATTERN.findall(form))
    # The .get pattern returns tuples (name, default); take name only.
    a = {x if isinstance(x, str) else x[0] for x in a}
    a |= set(_PARAMS_INDEX_PATTERN.findall(form))
    return a


# ── R1-sanity pre-check (FM-X-a mitigation) ───────────────────────────


def candidate_passes_r1_sanity(thesis_text: str) -> tuple[bool, str]:
    """Cheap pre-crossover sanity gate. Returns (ok, reason)."""
    if not thesis_text or not thesis_text.strip():
        return False, "empty thesis"
    body = _extract_python_block(thesis_text)
    if not body:
        return False, "no fenced python block"
    pf = extract_parametric_form(thesis_text)
    if not pf:
        return False, "no PARAMETRIC_FORM"
    if not collect_form_features(pf):
        return False, "PARAMETRIC_FORM uses no features[]"
    if not collect_form_params(pf):
        return False, "PARAMETRIC_FORM uses no params"
    # Surface-level Python compile check for the python block as a whole;
    # if that fails this candidate cannot survive the apparatus's R1 anyway.
    try:
        compile(body, "<recomb_r1_sanity>", "exec")
    except Exception as exc:
        return False, f"python compile: {type(exc).__name__}: {exc!s}"[:160]
    return True, "ok"


# ── Apparatus ↔ SymPy translation (FM-2d) ─────────────────────────────


def apparatus_to_sympy(form: str):
    """Translate apparatus PARAMETRIC_FORM into a SymPy expression.

    Substitutions:
      * features['k']        → symbol  feat_k
      * params.get('k', d)   → symbol  param_k  (default discarded)
      * params['k']          → symbol  param_k
      * np.where(...)        → not crossover-friendly — caller checks
        the pre-translated form for `np.where` and skips when present
      * exp / log / sqrt etc → sympy.exp / log / sqrt via auto-import

    Returns (sympy_expr, feature_names, param_names) on success;
    returns (None, [], []) on any failure. Failure is non-fatal — caller
    skips that parent from crossover, it still enters the tournament.
    """
    try:
        import sympy as sp
    except ImportError:
        return None, [], []

    if not form:
        return None, [], []

    # FM-2d guard: np.where is not a SymPy primitive; bail rather than
    # produce wrong-semantics translations
    if "np.where" in form or "np.sign" in form or "np.maximum" in form:
        return None, [], []

    work = str(form)
    feats: list[str] = []
    params: list[str] = []

    def _sub_feature(m: re.Match) -> str:
        name = m.group(1)
        sym = f"feat_{re.sub(r'[^a-zA-Z0-9_]', '_', name)}"
        if name not in feats:
            feats.append(name)
        return sym

    def _sub_param(m: re.Match) -> str:
        name = m.group(1)
        sym = f"param_{re.sub(r'[^a-zA-Z0-9_]', '_', name)}"
        if name not in params:
            params.append(name)
        return sym

    work = _FEATURES_INDEX_PATTERN.sub(_sub_feature, work)
    work = _PARAMS_GET_PATTERN.sub(_sub_param, work)
    work = _PARAMS_INDEX_PATTERN.sub(_sub_param, work)
    # Common bare-function names we expect:
    work = re.sub(r"\bnp\.exp\b", "exp", work)
    work = re.sub(r"\bnp\.log\b", "log", work)
    work = re.sub(r"\bnp\.sqrt\b", "sqrt", work)
    work = re.sub(r"\bmath\.exp\b", "exp", work)
    work = re.sub(r"\bmath\.log\b", "log", work)
    work = re.sub(r"\bmath\.sqrt\b", "sqrt", work)
    # Logical / boolean bits won't translate cleanly
    if "if " in work or " else " in work:
        return None, [], []

    try:
        local = {f"feat_{re.sub(r'[^a-zA-Z0-9_]', '_', x)}": sp.Symbol(
                    f"feat_{re.sub(r'[^a-zA-Z0-9_]', '_', x)}")
                 for x in feats}
        local.update({f"param_{re.sub(r'[^a-zA-Z0-9_]', '_', x)}": sp.Symbol(
                        f"param_{re.sub(r'[^a-zA-Z0-9_]', '_', x)}")
                      for x in params})
        local.update({"exp": sp.exp, "log": sp.log, "sqrt": sp.sqrt,
                      "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
                      "tanh": sp.tanh, "sinh": sp.sinh, "cosh": sp.cosh,
                      "atan": sp.atan, "asinh": sp.asinh, "abs": sp.Abs})
        expr = sp.sympify(work, locals=local)
        return expr, feats, params
    except Exception as exc:
        logger.debug("apparatus_to_sympy failed: %s", exc)
        return None, [], []


def sympy_to_apparatus(expr, feature_names: list[str], param_names: list[str]) -> Optional[str]:
    """Translate a SymPy expression back into apparatus PARAMETRIC_FORM.
    Substitutes feat_k → features['k'] and param_k → params.get('k', 0.0).
    Returns None if the expression contains symbols that aren't in the
    declared feature/param lists (would produce a form the apparatus
    can't evaluate).
    """
    try:
        import sympy as sp
    except ImportError:
        return None
    try:
        text = sp.sstr(expr)
    except Exception:
        return None
    declared = set()
    for f in feature_names:
        declared.add(f"feat_{re.sub(r'[^a-zA-Z0-9_]', '_', f)}")
    for p in param_names:
        declared.add(f"param_{re.sub(r'[^a-zA-Z0-9_]', '_', p)}")
    # Find any symbol-like token that wasn't declared
    tokens = set(re.findall(r"\b(feat_[a-zA-Z0-9_]+|param_[a-zA-Z0-9_]+)\b", text))
    if tokens - declared:
        # Crossover dragged in a symbol that doesn't exist in this form's
        # declared features/params — would crash at evaluation. Reject.
        return None
    # Substitute back: feat_X → features['X']; param_X → params.get('X', 0.0)
    def _back_feat(m: re.Match) -> str:
        sanitized = m.group(1)
        # Reverse the sanitization by matching against declared feature_names
        for f in feature_names:
            if f"feat_{re.sub(r'[^a-zA-Z0-9_]', '_', f)}" == f"feat_{sanitized}":
                return f"features['{f}']"
        return m.group(0)
    def _back_param(m: re.Match) -> str:
        sanitized = m.group(1)
        for p in param_names:
            if f"param_{re.sub(r'[^a-zA-Z0-9_]', '_', p)}" == f"param_{sanitized}":
                return f"params.get('{p}', 0.0)"
        return m.group(0)
    text = re.sub(r"\bfeat_([a-zA-Z0-9_]+)\b", _back_feat, text)
    text = re.sub(r"\bparam_([a-zA-Z0-9_]+)\b", _back_param, text)
    # SymPy uses ** for power which matches Python; leave as-is.
    return text


# ── Skeleton hashing for FM-2a shared-skeleton requirement ────────────


def _skeleton_hash(form: str) -> str:
    """Token-level skeleton hash. Cheap, gameable. Use _canonical_hash
    for collision-resistant comparison; this stays only as a fast
    pre-filter for crossover bucketing.
    """
    if not form:
        return ""
    sk = str(form)
    sk = _FEATURES_INDEX_PATTERN.sub("FEAT", sk)
    sk = _PARAMS_GET_PATTERN.sub("PARAM", sk)
    sk = _PARAMS_INDEX_PATTERN.sub("PARAM", sk)
    sk = re.sub(r"\b\d+\.?\d*([eE][+-]?\d+)?\b", "N", sk)
    sk = re.sub(r"\s+", "", sk)
    return hashlib.md5(sk.encode()).hexdigest()[:12]


def _canonical_hash(form: str) -> str:
    """Adversarial-resistant canonical form hash (panel seat 4 mitigation).

    Pipeline: apparatus_to_sympy → sympy.simplify → alpha-rename params
    in DAG-traversal order → operator-multiset string → MD5.

    Two forms with the same canonical hash are algebraically equivalent
    after parameter relabeling. Defeats: parameter renaming, term
    reordering (commutative), trivial identities like x*1.0, whitespace.

    Falls back to _skeleton_hash on translation failure (silent — caller
    still gets a comparable token).
    """
    if not form:
        return ""
    expr, feats, params = apparatus_to_sympy(form)
    if expr is None:
        return _skeleton_hash(form) + "_fb"
    try:
        import sympy as sp
        simplified = sp.simplify(expr)
        # Alpha-rename params in DAG-order: walk the simplified tree,
        # collect param symbols in deterministic order, replace with p0, p1...
        param_syms = sorted(
            [s for s in simplified.free_symbols if str(s).startswith("param_")],
            key=lambda s: str(s),
        )
        rename_map = {s: sp.Symbol(f"p{i}") for i, s in enumerate(param_syms)}
        canon = simplified.xreplace(rename_map)
        text = sp.sstr(canon)
    except Exception:
        return _skeleton_hash(form) + "_fb"
    return hashlib.md5(text.encode()).hexdigest()[:16]


def _operator_multiset(form: str) -> dict[str, int]:
    """Count occurrences of each operator/function in the canonicalized
    form (panel seat 4 — defeats structural rearrangement gaming).

    Returns multiset over: +, *, **, exp, log, sqrt, sin, cos, tanh,
    sigmoid, etc. Symmetric in commutative children.
    """
    expr, _, _ = apparatus_to_sympy(form)
    if expr is None:
        return {}
    try:
        import sympy as sp
        counts: dict[str, int] = {}
        def _walk(e):
            if e.is_Atom:
                return
            name = type(e).__name__
            counts[name] = counts.get(name, 0) + 1
            for ch in e.args:
                _walk(ch)
        _walk(expr)
        return counts
    except Exception:
        return {}


def _multiset_jaccard(a: dict[str, int], b: dict[str, int]) -> float:
    """Jaccard distance over multiset operator counts. 1.0 = disjoint
    operator sets; 0.0 = identical."""
    if not a and not b:
        return 0.0
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    inter = sum(min(a.get(k, 0), b.get(k, 0)) for k in keys)
    union = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    if union == 0:
        return 0.0
    return 1.0 - (inter / union)


def _ast_node_count(form: str) -> int:
    """Count of non-atom nodes in the form's SymPy tree. Used for
    parsimony pressure and bloat hard caps (GP seat 1 — Koza's First Law).
    """
    expr, _, _ = apparatus_to_sympy(form)
    if expr is None:
        # Fallback proxy: token count
        return len(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|[+\-*/^()]", form or ""))
    try:
        c = 0
        def _walk(e):
            nonlocal c
            if not e.is_Atom:
                c += 1
                for ch in e.args:
                    _walk(ch)
        _walk(expr)
        return c
    except Exception:
        return 0


def _ast_depth(form: str) -> int:
    """Maximum depth of the form's SymPy tree."""
    expr, _, _ = apparatus_to_sympy(form)
    if expr is None:
        return 0
    try:
        def _depth(e) -> int:
            if e.is_Atom:
                return 0
            return 1 + max((_depth(ch) for ch in e.args), default=0)
        return _depth(expr)
    except Exception:
        return 0


# Panel seat 1 (GP) — hard caps. These are bloat guards.
# Calibrated empirically against the gp163d gravity-bridge forms
# (real K=3 mutator output is routinely depth 13, ~25-30 nodes).
# Phase 1 caps were too aggressive and rejected every hybrid.
# Phase 1.1 (2026-04-28 backtest): doubled depth, 2× node count.
MAX_NODE_COUNT = 80
MAX_AST_DEPTH = 16
PARSIMONY_LAMBDA = 0.02  # score reduction per node above 20


# ── Crossover (Stage 2) ────────────────────────────────────────────────


def find_swappable_subtrees(expr, min_depth: int = 2) -> list:
    """Walk the SymPy expression tree, return sub-expressions at depth
    ≥ min_depth that are non-trivial (contain at least one symbol).

    Returns a list of (parent_path, sub_expr) tuples. The parent_path is
    a tuple of indices into expr.args at each level; allows reconstruction
    of the parent for substitution.
    """
    try:
        import sympy as sp
    except ImportError:
        return []
    out = []

    def _walk(e, path: tuple, depth: int):
        if depth >= min_depth and len(e.free_symbols) >= 1 and not e.is_Atom:
            out.append((path, e))
        if not e.is_Atom:
            for i, child in enumerate(e.args):
                _walk(child, path + (i,), depth + 1)

    _walk(expr, (), 0)
    return out


def _replace_at_path(expr, path: tuple, replacement):
    """Build a new sympy expression by replacing the sub-expr at `path`
    with `replacement`. Returns None on failure.
    """
    try:
        if not path:
            return replacement
        # Recursively rebuild
        head_args = list(expr.args)
        if path[0] >= len(head_args):
            return None
        new_child = _replace_at_path(head_args[path[0]], path[1:], replacement)
        if new_child is None:
            return None
        head_args[path[0]] = new_child
        return expr.func(*head_args)
    except Exception:
        return None


def crossover_pair(
    form_a: str,
    form_b: str,
    *,
    max_hybrids: int = 3,
) -> list[str]:
    """Generate up to `max_hybrids` hybrid PARAMETRIC_FORM strings by
    swapping sub-trees between two parents that share top-level skeleton.

    Returns [] when:
      * either parent fails apparatus_to_sympy
      * skeleton hashes differ (FM-2a (a) shared-skeleton requirement)
      * sympy_to_apparatus rejects any candidate hybrid (variable-aliasing
        or undeclared-symbol post-substitution; FM-2b)
    """
    # GP-174 Phase 1.1 — drop strict shared-skeleton gate (panel FM-2a
    # vs Munger Lollapalooza-A tradeoff). The persona-private suffix
    # is DESIGNED to produce divergent skeletons; a strict
    # equality pre-filter rejects every pair, defeating recombination.
    # Replace with AST-parseability + minimum-shared-feature gate.
    # Bloat caps + canonical-hash de-dup catch malformed hybrids
    # downstream; skeleton equality is over-engineering.
    expr_a, feats_a, params_a = apparatus_to_sympy(form_a)
    expr_b, feats_b, params_b = apparatus_to_sympy(form_b)
    if expr_a is None or expr_b is None:
        return []
    # Crossover requires the parents share at least one feature so the
    # resulting hybrid is anchored to a common substrate axis. (All
    # apparatus forms reference features['x'] by contract, so this is
    # ~always satisfied; the gate only excludes pathological inputs.)
    shared_features = set(feats_a) & set(feats_b)
    if not shared_features:
        return []
    feats_union = list(dict.fromkeys(feats_a + feats_b))
    params_union = list(dict.fromkeys(params_a + params_b))

    sub_a = find_swappable_subtrees(expr_a, min_depth=2)
    sub_b = find_swappable_subtrees(expr_b, min_depth=2)
    if not sub_a or not sub_b:
        return []

    hybrids: list[str] = []
    # Use CANONICAL hash for de-duplication, not token-level skeleton hash
    # (panel seat 4 — defeats parameter-rename + commutativity gaming)
    seen_canonical: set[str] = {_canonical_hash(form_a), _canonical_hash(form_b)}

    sub_a_top = sorted(sub_a, key=lambda x: -len(x[0]))[:5]
    sub_b_top = sorted(sub_b, key=lambda x: -len(x[0]))[:5]

    for left_path, _st_a in sub_a_top:
        for _right_path, st_b in sub_b_top:
            if len(hybrids) >= max_hybrids:
                break
            new_expr = _replace_at_path(expr_a, left_path, st_b)
            if new_expr is None:
                continue
            try:
                hybrid_form = sympy_to_apparatus(new_expr, feats_union, params_union)
            except Exception:
                hybrid_form = None
            if not hybrid_form:
                continue
            # Bloat hard caps (panel seat 1 — Koza's First Law)
            n_nodes = _ast_node_count(hybrid_form)
            depth = _ast_depth(hybrid_form)
            if n_nodes > MAX_NODE_COUNT or depth > MAX_AST_DEPTH:
                continue
            # Canonical-hash dedup (defeats syntactic gaming)
            ch = _canonical_hash(hybrid_form)
            if ch in seen_canonical:
                continue
            seen_canonical.add(ch)
            hybrids.append(hybrid_form)
        if len(hybrids) >= max_hybrids:
            break
    return hybrids


def assemble_crossover_thesis(
    parent_thesis: str,
    hybrid_form: str,
    extra_param_names: list[str],
) -> str:
    """Take a parent thesis (which contains a fenced python block with
    PARAMETRIC_FORM, PARAMETER_NAMES, MODEL_PARAMS, I_model, etc.), swap
    its PARAMETRIC_FORM with the hybrid, and merge in any new parameter
    names introduced by the crossover.

    The mutator's I_model body operates on `params` dict so it tolerates
    the added parameter names without modification. The fitting layer
    will fit the union of parameters declared in PARAMETER_NAMES.
    """
    body = _extract_python_block(parent_thesis) or parent_thesis
    new_form = hybrid_form.replace('"', '\\"')
    body_new = re.sub(
        r'(PARAMETRIC_FORM\s*=\s*)(?:r?["\'])(.+?)(?:["\'])',
        rf'\1"{new_form}"',
        body,
        count=1,
        flags=re.DOTALL,
    )
    if extra_param_names:
        # Merge the cross-over-introduced params into PARAMETER_NAMES
        m = _PARAMETER_NAMES_PATTERN.search(body_new)
        if m:
            existing = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
            merged = list(dict.fromkeys(existing + extra_param_names))
            new_list = "[" + ", ".join(f"'{p}'" for p in merged) + "]"
            body_new = body_new.replace(m.group(0), f"PARAMETER_NAMES = {new_list}", 1)
    # Reassemble: replace the parent's python block with the patched one.
    # Use a lambda replacement so backslash sequences in body_new (e.g.
    # `params['log_alpha']` which contains \w-equivalent escape patterns
    # when re-interpreted) don't get parsed as regex backreferences.
    if "```python" in parent_thesis and "```" in parent_thesis:
        replacement = f"```python{body_new}```"
        return re.sub(
            r"```python.*?```",
            lambda _m: replacement,
            parent_thesis,
            count=1,
            flags=re.DOTALL,
        )
    return body_new


# ── Persona-Fusion (Stage 3) ──────────────────────────────────────────


_FUSION_PROMPT = """You are a structural-fragment synthesizer for a
symbolic regression apparatus. The K candidate parametric forms below
were produced in parallel by independently-seeded mutator personas
(Stage 1) and may have been recombined via AST crossover (Stage 2).

Your task is TWO-PASS (panel review FM-3a — single-pass reconciliation
regresses to the mean):

PASS 1 — DIAGNOSIS (return this section in your JSON):
  For each candidate i in {1..K}, identify:
    - decisive_fragment_i: the AST sub-tree this candidate uniquely
      contributes (a sub-expression NO other candidate has)
    - failure_mode_i: the structural property this candidate cannot
      represent (one sentence, mechanical not philosophical)
  Then identify:
    - dominant_family: the functional family ≥ 2 of the candidates share
      (e.g. "threshold_sigmoid", "polynomial_log", "screened_scalar")

PASS 2 — CONSTRUCTION (return as fusion_form):
  Construct a single PARAMETRIC_FORM F such that:
    (a) F contains decisive_fragment_1 AND _2 AND _3 simultaneously.
    (b) F is NOT in dominant_family. If 2 of 3 inputs are threshold
        forms, the fusion form must be non-threshold.
    (c) For each candidate i, name the mechanism by which F structurally
        cannot exhibit failure_mode_i. "Cannot exhibit" means the
        sub-tree containing failure_mode_i is absent from F by
        construction, not that a parameter could be tuned to suppress it.

If the candidates collapsed to a single family (no genuinely disjoint
decision-critical fragments), return:
    {"fusion_form": null,
     "diagnosis": {{"dominant_family": "<name>", ...}},
     "reasoning": "candidates_collapsed_to_<family>"}

Otherwise return strict JSON:
    {{
      "diagnosis": {{
        "candidates": [
          {{"i": 1, "decisive_fragment": "<expr>", "failure_mode": "<...>"}},
          {{"i": 2, ...}},
          ...
        ],
        "dominant_family": "<name>"
      }},
      "fusion_form": "<apparatus PARAMETRIC_FORM string>",
      "novel_fragments_used": ["<fragment_1>", "<fragment_2>", ...],
      "failure_mode_closures": [
        "candidate 1's <failure_mode> impossible because <mechanism>",
        "candidate 2's <failure_mode> impossible because <mechanism>",
        ...
      ],
      "reasoning": "<2-3 sentences on the construction>"
    }}

The fusion_form must:
  - reference features[] for substrate axes — only names that appear in
    ≥1 candidate; do NOT invent feature names
  - reference params.get('name', 0.0) for fitted parameters
  - be a single Python expression evaluable in (features, params) namespace
  - have node_count <= 40 and depth <= 8 (apparatus parsimony cap)

CANDIDATES:

{candidate_block}

Output strict JSON only, no markdown fences. Be terse in reasoning."""


@dataclass
class FusionResult:
    success: bool
    form: Optional[str] = None
    reasoning: str = ""
    novel_fragments: list[str] = field(default_factory=list)
    raw_response: str = ""
    error: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0


def persona_fusion(
    candidate_forms: list[str],
    *,
    runtime: Any,
    model_id: str,
    timeout_seconds: int = 90,
) -> FusionResult:
    """Single LLM call that synthesizes a hybrid form from K candidates.

    FM-3a mitigation: prompt explicitly demands LEAST-common fragments.
    FM-3b mitigation: caller hashes the result against each input;
    identical-hash fusion is demoted in tournament scoring.
    """
    if not candidate_forms or len(candidate_forms) < 2:
        return FusionResult(success=False, error="need ≥2 candidates")
    if not runtime or not model_id:
        return FusionResult(success=False, error="missing runtime/model_id")

    block_lines = []
    for i, form in enumerate(candidate_forms):
        block_lines.append(f"CANDIDATE {i+1}:")
        block_lines.append(f"  PARAMETRIC_FORM = \"{form}\"")
        block_lines.append("")
    # Bug B fix (dry-run 2026-04-28): _FUSION_PROMPT contains JSON-example
    # braces ({ } in the output schema) which `.format()` tries to interpret
    # as positional placeholders → "Replacement index out of range" crash.
    # Use literal-substitution sentinel instead.
    prompt = _FUSION_PROMPT.replace("{candidate_block}", "\n".join(block_lines))

    try:
        from src.ztare.common.dispatch_model import dispatch_call_text

        response = dispatch_call_text(
            "recombination_fusion",
            prompt,
            llm_response_call=lambda p: runtime.call_text(
                p,
                model_id=model_id,
                timeout_seconds=timeout_seconds,
                request_label="gp174_persona_fusion",
                retries=2,
            ),
            timeout_seconds=int(timeout_seconds),
        )
    except Exception as exc:
        return FusionResult(success=False, error=f"{type(exc).__name__}: {exc!s}"[:200])

    raw = response.text or ""
    usage = response.usage if hasattr(response, "usage") else None
    tokens_in = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
    tokens_out = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0

    # Parse JSON
    parsed = None
    raw_stripped = raw.strip()
    if raw_stripped.startswith("```"):
        raw_stripped = re.sub(r"^```(?:json)?\s*", "", raw_stripped)
        raw_stripped = re.sub(r"```\s*$", "", raw_stripped)
    try:
        parsed = json.loads(raw_stripped)
    except json.JSONDecodeError:
        return FusionResult(
            success=False,
            error="non-JSON fusion response",
            raw_response=raw[:500],
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

    fform = parsed.get("fusion_form")
    if not fform or fform == "null":
        return FusionResult(
            success=False,
            reasoning=str(parsed.get("reasoning", "")),
            raw_response=raw[:500],
            error="fusion_form is null (candidates_collapsed)",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

    return FusionResult(
        success=True,
        form=str(fform).strip(),
        reasoning=str(parsed.get("reasoning", ""))[:500],
        novel_fragments=[str(x)[:120] for x in parsed.get("novel_fragments_used", [])][:8],
        raw_response=raw[:1000],
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )


def assemble_fusion_thesis(parent_thesis: str, fusion_form: str) -> str:
    """Wrap a fusion form into a thesis using a parent thesis as the
    prose template. Same mechanic as assemble_crossover_thesis.
    """
    return assemble_crossover_thesis(parent_thesis, fusion_form, extra_param_names=[])


# ── Tournament scoring extension (Stage 4 — partial) ──────────────────


def score_candidate_extended(
    thesis_text: str,
    *,
    prior_champion_form: Optional[str] = None,
) -> float:
    """Score a candidate thesis. Panel-revised (2026-04-27):

      Baseline (syntactic validity):
        + 1.0 PARAMETRIC_FORM present
        + 1.0 PARAMETER_NAMES present
        + 1.0 MODEL_PARAMS present
        + 1.0 def I_model present
        + 0.5 ```python fenced block present
        + 2.0 the python block compiles cleanly

      Novelty (panel seat 4 — 3-axis stack, residual-fingerprint deferred):
        + 0.5  if canonical-hash differs from prior champion (defeats
               parameter renames + commutativity gaming via _canonical_hash)
        + 0.5  if operator-multiset Jaccard distance from prior champion
               is ≥ 0.3 (defeats structural rearrangement gaming)

      Multi-feature anti-collapse:
        + 0.5  if PARAMETRIC_FORM references ≥3 distinct features

      Length proxy (capped):
        + min(len/4000, 1.0)

      Parsimony penalty (panel seat 1 — Koza's First Law):
        - PARSIMONY_LAMBDA × max(0, node_count - 20)

      Hard caps (panel seat 1):
        return -1.0 if node_count > MAX_NODE_COUNT
        return -1.0 if depth > MAX_AST_DEPTH
    """
    if not thesis_text:
        return -1.0
    s = 0.0
    if "PARAMETRIC_FORM" in thesis_text:
        s += 1.0
    if "PARAMETER_NAMES" in thesis_text:
        s += 1.0
    if "MODEL_PARAMS" in thesis_text:
        s += 1.0
    if "def I_model" in thesis_text or "def model" in thesis_text:
        s += 1.0
    if "```python" in thesis_text:
        s += 0.5
    body = _extract_python_block(thesis_text)
    if body:
        try:
            compile(body, "<recomb_score>", "exec")
            s += 2.0
        except Exception:
            pass
    pf = extract_parametric_form(thesis_text)
    if pf:
        # Hard parsimony caps. Bug N fix (round-2 dry-run): SymPy
        # flattens commutative ops (`Mul(a,b,c,d,...)` is depth-1), so
        # `_ast_depth` is near-useless for catching chained-multiplication
        # bloat. Depth=20 chain has sympy-AST depth=2. Use node_count as
        # the primary axis; keep depth as a soft secondary.
        n_nodes = _ast_node_count(pf)
        depth = _ast_depth(pf)
        if n_nodes > MAX_NODE_COUNT:
            return -1.0
        if depth > MAX_AST_DEPTH:
            return -1.0
        # Catch chained-mult / chained-add bloat: token-level operator count.
        # If form has > MAX_NODE_COUNT operator tokens (` * ` ` + ` ` ** `), reject.
        op_token_count = (
            pf.count(" * ") + pf.count(" + ") + pf.count(" - ") + pf.count(" ** ")
        )
        if op_token_count > MAX_NODE_COUNT:
            return -1.0
        feats = collect_form_features(pf)
        if len(feats) >= 3:
            s += 0.5
        if prior_champion_form:
            # 3-axis novelty (panel seat 4)
            if _canonical_hash(pf) != _canonical_hash(prior_champion_form):
                s += 0.5
            jacc = _multiset_jaccard(
                _operator_multiset(pf),
                _operator_multiset(prior_champion_form),
            )
            if jacc >= 0.3:
                s += 0.5
        # Parsimony penalty (smooth, panel seat 1)
        if n_nodes > 20:
            s -= PARSIMONY_LAMBDA * (n_nodes - 20)
    s += min(len(thesis_text) / 4000.0, 1.0)
    return s


# ── Orchestration ──────────────────────────────────────────────────────


@dataclass
class RecombineResult:
    expanded_pool: list  # MutatorResult-shaped list
    log_entry: dict
    fusion_succeeded: bool
    n_crossovers: int
    n_fusion: int


def recombine(
    blitz_results: list,
    *,
    runtime: Any,
    model_id: str,
    prior_champion_form: Optional[str],
    workspace_dir: Path,
    iter_idx: int,
    enable_crossover: bool = True,
    enable_fusion: bool = True,
    max_crossover_pairs: int = 3,
    max_hybrids_per_pair: int = 2,
) -> RecombineResult:
    """Apply Stage 2 (AST crossover) and Stage 3 (Persona-Fusion) to the
    K parallel mutator results. Returns the EXPANDED candidate pool with
    `stage_origin` tagged on each entry.

    Pipeline:
      1. R1-sanity pre-check (FM-X-a) — exclude failed candidates from
         crossover; they still enter the tournament with their original
         scores.
      2. AST crossover across pairs of R1-passing parents that share
         skeleton (FM-2a (a)).
      3. Persona-Fusion call with the (originals + crossovers) as input.
      4. Returns expanded pool + structured log entry.

    The caller (autoresearch_loop) passes the expanded pool through the
    existing pick_best_candidate to select the iter winner. No changes
    to the downstream R1 retry / fit / cage / judge pipeline.
    """
    log: dict[str, Any] = {
        "iter": iter_idx,
        "timestamp": _utc_now_iso(),
        "n_originals": len(blitz_results),
        "stages": [],
    }
    # Lazy-import the dataclass so a missing parallel_mutator module
    # surfaces here rather than at autoresearch_loop import time.
    from src.ztare.orchestrator.parallel_mutator import MutatorResult

    # ── Stage 0: tag originals with stage_origin and run R1 sanity ────
    expanded: list = []
    sanitized_pool: list = []  # only R1-passing parents enter crossover
    for r in blitz_results:
        ok, reason = candidate_passes_r1_sanity(r.thesis_text or "")
        extras = dict(r.extras or {})
        extras["stage_origin"] = f"mutator_{r.persona}"
        extras["r1_sanity"] = "ok" if ok else f"fail:{reason}"
        new = MutatorResult(
            worker_id=r.worker_id,
            persona=r.persona,
            thesis_text=r.thesis_text or "",
            test_model_text=r.test_model_text or "",
            score=r.score,
            extras=extras,
        )
        expanded.append(new)
        if ok:
            sanitized_pool.append(new)
    log["stages"].append({
        "stage": "r1_sanity",
        "n_passing": len(sanitized_pool),
        "n_total": len(blitz_results),
    })

    # Early abort: if no parent passes R1, crossover and fusion are pointless
    if len(sanitized_pool) < 2:
        log["stages"].append({"stage": "early_abort",
                              "reason": "fewer than 2 R1-passing parents"})
        _write_pipeline_log(workspace_dir, log)
        return RecombineResult(
            expanded_pool=expanded,
            log_entry=log,
            fusion_succeeded=False,
            n_crossovers=0,
            n_fusion=0,
        )

    # ── Stage 2: AST crossover ─────────────────────────────────────────
    # GP-174 Phase 1.1 (2026-04-28 backtest fix): pair candidates
    # all-vs-all rather than gating on skeleton-equality. The
    # persona-private suffix engineers cross-persona divergence by
    # design — strict shared-skeleton bucketing rejects every pair
    # exactly when the pipeline's value would be highest. The
    # downstream `crossover_pair` enforces AST-parseability +
    # shared-feature + bloat caps + canonical-hash de-dup; that
    # stack alone is sufficient quality control without a strict
    # pre-filter at this stage.
    crossover_records: list[dict] = []
    n_crossovers = 0
    if enable_crossover:
        pairs_attempted = 0
        skeleton_observed: dict[str, int] = {}
        # Stress-test fix (2026-04-28): pre-filter parents to those whose
        # PARAMETRIC_FORM is sympy-parseable. Pair-selection is positional
        # (i,j with i<j stops at max_pairs); if parent 0 has un-parseable
        # form (walrus operator, statement-seq, etc.), the first
        # max_pairs attempts all fail before promising pairs are tried.
        # Filter first so the budget goes to viable pairs.
        crossover_eligible: list = []
        non_eligible_reasons: list[str] = []
        for r in sanitized_pool:
            pf = extract_parametric_form(r.thesis_text)
            if not pf:
                non_eligible_reasons.append(f"{r.persona}: no PARAMETRIC_FORM")
                continue
            expr, _, _ = apparatus_to_sympy(pf)
            if expr is None:
                non_eligible_reasons.append(f"{r.persona}: sympy-unparseable")
                continue
            sk = _skeleton_hash(pf)
            skeleton_observed[sk] = skeleton_observed.get(sk, 0) + 1
            crossover_eligible.append(r)
        for i in range(len(crossover_eligible)):
            for j in range(i + 1, len(crossover_eligible)):
                if pairs_attempted >= max_crossover_pairs:
                    break
                pairs_attempted += 1
                parent_a = crossover_eligible[i]
                parent_b = crossover_eligible[j]
                pf_a = extract_parametric_form(parent_a.thesis_text) or ""
                pf_b = extract_parametric_form(parent_b.thesis_text) or ""
                hybrids = crossover_pair(pf_a, pf_b, max_hybrids=max_hybrids_per_pair)
                for hk, hyb_form in enumerate(hybrids):
                    params_a = collect_form_params(pf_a)
                    params_b = collect_form_params(pf_b)
                    new_params = sorted(params_b - params_a)
                    thesis = assemble_crossover_thesis(
                        parent_a.thesis_text, hyb_form, list(new_params)
                    )
                    worker_id = 1000 + n_crossovers
                    n_crossovers += 1
                    ext = {
                        "stage_origin": f"crossover_{parent_a.persona}+{parent_b.persona}",
                        "hybrid_index": hk,
                        "parent_ids": [parent_a.worker_id, parent_b.worker_id],
                        "parent_skeletons": [_skeleton_hash(pf_a), _skeleton_hash(pf_b)],
                    }
                    expanded.append(MutatorResult(
                        worker_id=worker_id,
                        persona=f"crossover_{parent_a.persona}+{parent_b.persona}",
                        thesis_text=thesis,
                        test_model_text="",
                        score=None,
                        extras=ext,
                    ))
                    crossover_records.append({
                        "worker_id": worker_id,
                        "parents": [parent_a.persona, parent_b.persona],
                        "form": hyb_form[:200],
                    })
            if pairs_attempted >= max_crossover_pairs:
                break
        log["stages"].append({
            "stage": "ast_crossover",
            "pairs_attempted": pairs_attempted,
            "n_eligible_parents": len(crossover_eligible),
            "n_pool_parents": len(sanitized_pool),
            "ineligible_reasons": non_eligible_reasons,
            "skeleton_observed_pre_pair": skeleton_observed,
            "n_hybrids": n_crossovers,
            "hybrids": crossover_records[:20],
        })

    # ── Stage 3: Persona-Fusion ────────────────────────────────────────
    fusion_succeeded = False
    n_fusion = 0
    if enable_fusion and len(sanitized_pool) >= 2:
        # Use originals + a sampling of crossovers as fusion input
        fusion_inputs = []
        for r in sanitized_pool:
            pf = extract_parametric_form(r.thesis_text)
            if pf:
                fusion_inputs.append(pf)
        for r in expanded:
            if r.extras and r.extras.get("stage_origin", "").startswith("crossover_"):
                pf = extract_parametric_form(r.thesis_text)
                if pf and len(fusion_inputs) < 6:
                    fusion_inputs.append(pf)
        if len(fusion_inputs) >= 2:
            fr = persona_fusion(
                fusion_inputs,
                runtime=runtime,
                model_id=model_id,
            )
            fusion_record = {
                "stage": "persona_fusion",
                "n_inputs": len(fusion_inputs),
                "success": fr.success,
                "tokens_in": fr.tokens_in,
                "tokens_out": fr.tokens_out,
                "error": fr.error,
                "novel_fragments": fr.novel_fragments,
                "reasoning_preview": fr.reasoning[:200],
            }
            if fr.success and fr.form:
                # Bug M fix (round-2 dry-run): validate fusion form is
                # sympy-parseable + bloat-cap-clean BEFORE adding to pool.
                # Without this, malformed LLM output reaches the tournament.
                _fusion_expr, _, _ = apparatus_to_sympy(fr.form)
                _fusion_node_count = _ast_node_count(fr.form)
                fusion_record["fusion_parseable"] = (_fusion_expr is not None)
                fusion_record["fusion_node_count"] = _fusion_node_count
                _fusion_admissible = (
                    _fusion_expr is not None
                    and _fusion_node_count <= MAX_NODE_COUNT
                )
                if not _fusion_admissible:
                    fusion_record["demoted"] = "fusion_form_unparseable_or_bloated"
                # FM-3b: reject fusion that hashes identically to any input
                if _fusion_admissible:
                    fusion_sk = _skeleton_hash(fr.form)
                    input_sks = {_skeleton_hash(pf) for pf in fusion_inputs}
                    fusion_record["fusion_skeleton"] = fusion_sk
                    fusion_record["fusion_collapsed_to_input"] = (fusion_sk in input_sks)
                    if not (fusion_sk in input_sks):
                        # Wrap into a thesis using the longest-prose original as template
                        template = max(sanitized_pool, key=lambda r: len(r.thesis_text or ""))
                        thesis = assemble_fusion_thesis(template.thesis_text, fr.form)
                        expanded.append(MutatorResult(
                            worker_id=2000,
                            persona="fusion",
                            thesis_text=thesis,
                            test_model_text="",
                            score=None,
                            extras={
                                "stage_origin": "fusion",
                                "fusion_skeleton": fusion_sk,
                                "novel_fragments": fr.novel_fragments,
                                "reasoning": fr.reasoning[:200],
                            },
                        ))
                        fusion_succeeded = True
                        n_fusion = 1
                    else:
                        fusion_record["demoted"] = "fusion_skeleton_matches_input"
            log["stages"].append(fusion_record)

    # ── Persist log ────────────────────────────────────────────────────
    log["expanded_pool_size"] = len(expanded)
    log["n_crossovers"] = n_crossovers
    log["n_fusion"] = n_fusion
    _write_pipeline_log(workspace_dir, log)

    return RecombineResult(
        expanded_pool=expanded,
        log_entry=log,
        fusion_succeeded=fusion_succeeded,
        n_crossovers=n_crossovers,
        n_fusion=n_fusion,
    )


def _utc_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _write_pipeline_log(workspace_dir: Path, log: dict) -> None:
    """Write the iter-summary record AND emit per-stage and per-candidate
    sub-records into pipeline_log.jsonl (panel seat 5 schema with
    record_type discriminator).

    The `log` dict carries the full pipeline trace from `recombine`;
    this writer fans it out into the three-record-type schema that
    `telemetry_reporter` and post-run audits consume.
    """
    try:
        workspace_dir = Path(workspace_dir)
        workspace_dir.mkdir(parents=True, exist_ok=True)
        path = workspace_dir / "pipeline_log.jsonl"
        records: list[dict] = []
        # 1. iter_summary
        summary = {
            "record_type": "iter_summary",
            "iter": log.get("iter"),
            "ts": log.get("timestamp"),
            "n_originals": log.get("n_originals"),
            "expanded_pool_size": log.get("expanded_pool_size"),
            "n_crossovers": log.get("n_crossovers"),
            "n_fusion": log.get("n_fusion"),
        }
        records.append(summary)
        # 2. stage_event (one per stage in log["stages"])
        for stage_event in log.get("stages", []):
            records.append({
                "record_type": "stage_event",
                "iter": log.get("iter"),
                "ts": log.get("timestamp"),
                **stage_event,
            })
        with open(path, "a", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, default=str) + "\n")
    except Exception as exc:
        logger.warning("pipeline_log write failed: %s", exc)


def write_candidate_record(
    workspace_dir: Path,
    iter_idx: int,
    candidate_id: str,
    *,
    stage_origin: str,
    parametric_form: Optional[str],
    score: float,
    score_components: dict,
    selected_as_winner: bool,
    parent_ids: Optional[list[int]] = None,
    extras: Optional[dict] = None,
) -> None:
    """Emit a per-candidate record (panel seat 5 schema). Called by the
    autoresearch_loop wire-in after winner-selection so each candidate's
    score breakdown is queryable for postmortem.
    """
    try:
        workspace_dir = Path(workspace_dir)
        path = workspace_dir / "pipeline_log.jsonl"
        rec = {
            "record_type": "candidate",
            "iter": iter_idx,
            "candidate_id": candidate_id,
            "stage_origin": stage_origin,
            "parent_ids": parent_ids or [],
            "parametric_form_preview": (parametric_form or "")[:200],
            "canonical_hash": _canonical_hash(parametric_form) if parametric_form else "",
            "node_count": _ast_node_count(parametric_form) if parametric_form else 0,
            "ast_depth": _ast_depth(parametric_form) if parametric_form else 0,
            "score": round(float(score), 3),
            "score_components": score_components,
            "selected_as_winner": bool(selected_as_winner),
            "extras": extras or {},
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
    except Exception as exc:
        logger.warning("write_candidate_record failed: %s", exc)
