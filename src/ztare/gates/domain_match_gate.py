"""GP-144 Gate G6 — Hidden Domain-Restriction Injection (SPECULATIVE SHELL).

Status: 2026-04-24 — partially implementable (hypothesis enumeration on a
provided Lean file); blocked on lean_compiler integration for automatic
pre/post hypothesis diff.

PURPOSE
-------
Translator must not silently add side-conditions (e.g., "x != 0", "assume
convergent", "over a separable space") that make the theorem true but
NARROWER than the intended claim.

DISCOVERY
---------
gp147 iter 2 meta-validation, H8.

CORE CHECK
----------
Pre-register the domain scope (quantifiers / universe constraints) in the
pre-translation artifact. After translation, enumerate all `⊢`-free
hypotheses introduced. Reject if any NEW hypothesis is present that was
not in the pre-registered scope.

Today's capability: implement the HYPOTHESIS ENUMERATION side. The
pipeline side (captured pre-translation scope) is blocked.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

GATE_ID = "domain_match"
PRODUCER = "GP-144.G6"

# Regex for a Lean 4 hypothesis — captures lines of form "h_name : Type"
# or "(hname : Type)" or implicit "{hname : Type}".
LEAN_HYPOTHESIS_PATTERN = re.compile(
    r"(?:\(|\{|^)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([^\)\{\},\n]+)"
)


def enumerate_lean_hypotheses(lean_source: str) -> list[dict[str, str]]:
    """Parse a Lean source string and return the list of hypotheses
    declared in theorem signatures. Best-effort regex; misses elaborated
    / macro-expanded hypotheses.
    """
    hypotheses = []
    # Find each `theorem` / `lemma` / `example` block and parse its signature
    for m in re.finditer(r"(?:theorem|lemma|example)\s+(\w+)?\s*([^\:]+):([^:=]+)(?::=|\bby\b)",
                         lean_source, re.DOTALL):
        sig_binders = m.group(2)
        for hm in LEAN_HYPOTHESIS_PATTERN.finditer(sig_binders):
            name = hm.group(1).strip()
            typ = hm.group(2).strip()
            if name and typ and name not in ("True", "False", "Type", "Prop"):
                hypotheses.append({"name": name, "type": typ})
    return hypotheses


def domain_match_check(
    pre_registered_scope: list[dict[str, str]],
    post_translation_lean_source: str,
) -> dict[str, Any]:
    """Check that the post-translation Lean source introduces no NEW
    hypothesis beyond the pre-registered scope.

    IMPLEMENTED TODAY for the enumeration + diff; depends on operator
    supplying the pre_registered_scope list.
    """
    observed = enumerate_lean_hypotheses(post_translation_lean_source)
    pre_names = {h["name"] for h in pre_registered_scope}
    new_hyps = [h for h in observed if h["name"] not in pre_names]
    passed = len(new_hyps) == 0
    return {
        "passed": passed,
        "observed_hypotheses": observed,
        "pre_registered_hypotheses": pre_registered_scope,
        "new_hypotheses_injected": new_hyps,
        "reason": ("no_new_hypotheses_injected" if passed
                   else f"{len(new_hyps)}_new_hypotheses_injected: "
                        f"{[h['name'] for h in new_hyps]}"),
    }


def pipeline_integration_check(claim: dict[str, Any]) -> dict[str, Any]:
    """Placeholder for automatic pre/post capture from lean_compiler."""
    return {
        "implemented": False,
        "blocked_on": "autoresearch_loop + lean_compiler pre-translation scope capture",
        "reason": ("lean_compiler currently produces Lean source without emitting a "
                   "pre-translation domain-scope artifact for comparison. Would "
                   "require GP-122 extension to log the intended scope before translating."),
    }


def run_gate(
    claim: dict[str, Any],
    rubric_params: dict[str, Any],
) -> dict[str, Any]:
    """Run G6 domain-match on a claim.

    claim schema:
        {
            "pre_registered_scope": [{"name": "x", "type": "Real"}, ...],
            "post_translation_lean_source": "theorem foo (x : Real) ...",  # OR
            "lean_proof_path": "<path>"                                    # loads file
        }
    """
    pre_scope = claim.get("pre_registered_scope")
    post_source = claim.get("post_translation_lean_source")
    if post_source is None:
        lean_path = claim.get("lean_proof_path")
        if lean_path and Path(lean_path).is_file():
            post_source = Path(lean_path).read_text(encoding="utf-8", errors="ignore")

    if pre_scope is not None and post_source:
        r = domain_match_check(pre_scope, post_source)
        return {
            "name": GATE_ID,
            "passed": r["passed"],
            "actual": len(r["new_hypotheses_injected"]),
            "threshold": 0,
            "reason": r["reason"],
            "penalty": 0 if r["passed"] else 1,
            "hard_fail": not r["passed"],
            "source": PRODUCER,
            "extra": {
                "domain_match": r,
                "shell_fully_implemented": True,  # this branch IS fully implemented
            },
        }

    # Missing inputs — blocked
    r_pipeline = pipeline_integration_check(claim)
    return {
        "name": GATE_ID,
        "passed": None,
        "actual": None,
        "threshold": None,
        "reason": ("shell_not_fully_implemented: requires pre_registered_scope + "
                   "post_translation_lean_source (or lean_proof_path); "
                   "automatic capture blocked on lean_compiler integration."),
        "penalty": 0,
        "hard_fail": False,
        "source": PRODUCER,
        "extra": {
            "pipeline_integration": r_pipeline,
            "shell_fully_implemented": False,
        },
    }


def filter_per_candidate_for_mutator_prompt(gate_result: dict[str, Any]) -> dict[str, Any]:
    filtered = {k: v for k, v in gate_result.items() if k != "extra"}
    extra = gate_result.get("extra", {})
    filtered["extra"] = {
        "shell_fully_implemented": extra.get("shell_fully_implemented"),
        "no_new_hypotheses_injected": extra.get("domain_match", {}).get("passed"),
    }
    return filtered
