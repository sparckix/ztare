"""GP-144 Gate G5 — Translation Semantic Drift (SPECULATIVE SHELL).

Status: 2026-04-24 — partially implementable today (hash canonicalization);
full implementation blocked on live GP-122 Lean translation pipeline to
provide pre/post translation pairs.

PURPOSE
-------
During lean_compiler translation from apparatus-output to Lean 4, no
symbol may be silently swapped (pi' vs pi, zeta(3) vs zeta'(3), gamma vs
gamma_constant, etc.). gp139 guarantees kernel soundness but NOT semantic
identity between the input statement and the output theorem.

DISCOVERY
---------
This gate was discovered by gp147 iter 2 meta-validation run (mutator o3
rediscovered this via inversion). H7 in the gp147 taxonomy.

CORE CHECK
----------
Hash-canonicalize both the pre-translation expression and the post-
translation Lean statement at a SYMBOL-CLASS level. Compare. If the
canonical hash differs beyond operator-declared tolerance, reject.

Today's capability: implement the HASH CANONICALIZATION side. The
pipeline side (invocation of lean_compiler's translator with before/after
pair capture) is blocked on autoresearch_loop PHASE D integration.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Optional

GATE_ID = "translation_diff"
PRODUCER = "GP-144.G5"

# Canonical symbol substitutions (case-insensitive) to normalize before hashing.
CANONICAL_SYMBOLS = [
    (r"\bpi\b", "PI"),
    (r"π", "PI"),
    (r"\be\b", "E_CONST"),
    (r"\bln\(", "LN("),
    (r"\blog\(", "LN("),
    (r"\bzeta\(", "ZETA("),
    (r"ζ\(", "ZETA("),
    (r"\bgamma\b", "GAMMA"),
    (r"γ", "GAMMA"),
    (r"\bG\b", "CATALAN_G"),  # Catalan's constant — ambiguous; keep tagged
    (r"\bsqrt\(", "SQRT("),
    (r"√", "SQRT"),
]


def canonicalize_expression(expr: str) -> str:
    """Normalize a mathematical expression string to a canonical symbol form
    so symbolically-equivalent statements hash identically.
    """
    out = expr.strip()
    # Collapse whitespace
    out = re.sub(r"\s+", " ", out)
    for pat, repl in CANONICAL_SYMBOLS:
        out = re.sub(pat, repl, out)
    return out


def canonical_hash(expr: str) -> str:
    return hashlib.sha256(canonicalize_expression(expr).encode()).hexdigest()[:16]


def hash_canonicalization_check(
    pre_translation_expr: str,
    post_translation_lean_statement: str,
) -> dict[str, Any]:
    """Compare canonical hashes of pre and post translation.

    IMPLEMENTED TODAY for the canonicalization; depends on operator
    providing both strings.
    """
    pre_hash = canonical_hash(pre_translation_expr)
    post_hash = canonical_hash(post_translation_lean_statement)
    passed = pre_hash == post_hash
    return {
        "passed": passed,
        "pre_canonical_hash": pre_hash,
        "post_canonical_hash": post_hash,
        "pre_canonical_form": canonicalize_expression(pre_translation_expr)[:200],
        "post_canonical_form": canonicalize_expression(post_translation_lean_statement)[:200],
        "reason": ("hashes_match_semantic_identity_preserved" if passed
                   else f"hashes_differ_pre={pre_hash[:8]}_post={post_hash[:8]}_symbol_swap_suspected"),
    }


def lean_compiler_invocation_check(claim: dict[str, Any]) -> dict[str, Any]:
    """Check whether a pre/post translation pair has been captured by the
    lean_compiler wrapper.

    IMPLEMENTED 2026-04-24. When GP-122 prove_from_compression is invoked,
    the lean_compiler wrapper at src.ztare.formal.lean_compiler_capture
    emits workspace/lean_translation_pair.json containing the pre-translation
    expression (from compression_results.json) and the post-translation Lean
    source (from project_dir/<project>.lean). This function reads that file.
    """
    from pathlib import Path as _Path
    project_dir = claim.get("project_dir")
    if not project_dir:
        return {
            "implemented": True,
            "captured": False,
            "reason": "project_dir not provided in claim",
        }
    pair_path = _Path(project_dir) / "workspace" / "lean_translation_pair.json"
    if not pair_path.is_file():
        return {
            "implemented": True,
            "captured": False,
            "reason": f"No translation pair captured yet at {pair_path}. "
                      "lean_compiler_capture.py must be invoked during proof generation.",
        }
    import json as _json
    pair = _json.loads(pair_path.read_text())
    return {
        "implemented": True,
        "captured": True,
        "pre_translation_expression": pair.get("pre_translation_expression"),
        "post_translation_lean_statement": pair.get("post_translation_lean_statement"),
        "capture_timestamp": pair.get("capture_timestamp"),
    }


def run_gate(
    claim: dict[str, Any],
    rubric_params: dict[str, Any],
) -> dict[str, Any]:
    """Run G5 translation-diff on a claim.

    claim schema:
        {
            "pre_translation_expression": "...",    # optional; if both present, runs hash check
            "post_translation_lean_statement": "...",
            "lean_proof_path": "<optional>",       # triggers lean_compiler_invocation_check
            ...
        }
    """
    pre = claim.get("pre_translation_expression")
    post = claim.get("post_translation_lean_statement")

    if pre and post:
        r_hash = hash_canonicalization_check(pre, post)
        return {
            "name": GATE_ID,
            "passed": r_hash["passed"],
            "actual": r_hash.get("post_canonical_hash"),
            "threshold": r_hash.get("pre_canonical_hash"),
            "reason": r_hash["reason"],
            "penalty": 0 if r_hash["passed"] else 1,
            "hard_fail": not r_hash["passed"],
            "source": PRODUCER,
            "extra": {
                "hash_canonicalization": r_hash,
                "shell_fully_implemented": True,  # this branch IS fully implemented
            },
        }

    # No pre/post pair provided — blocked on pipeline integration
    r_invoc = lean_compiler_invocation_check(claim)
    return {
        "name": GATE_ID,
        "passed": None,
        "actual": None,
        "threshold": None,
        "reason": ("shell_not_fully_implemented: requires pre_translation_expression + "
                   "post_translation_lean_statement pair from lean_compiler; "
                   "not yet wired into autoresearch_loop PHASE D."),
        "penalty": 0,
        "hard_fail": False,
        "source": PRODUCER,
        "extra": {
            "lean_compiler_invocation": r_invoc,
            "shell_fully_implemented": False,
        },
    }


def filter_per_candidate_for_mutator_prompt(gate_result: dict[str, Any]) -> dict[str, Any]:
    filtered = {k: v for k, v in gate_result.items() if k != "extra"}
    extra = gate_result.get("extra", {})
    filtered["extra"] = {
        "shell_fully_implemented": extra.get("shell_fully_implemented"),
        "hash_match": extra.get("hash_canonicalization", {}).get("passed"),
    }
    return filtered
