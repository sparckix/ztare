#!/usr/bin/env python3
"""Run one formal Lean target through the governed LeanMill solver."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_LEAN_ROOT = REPO_ROOT / "ztare_proofs"


def _ratify_carried_theorem(*args, **kwargs):
    """Enter the bounded carried-artifact lifecycle without loading search."""

    from ztare.leanmill.carried_theorem_ratification import (
        ratify_carried_theorem,
    )

    return ratify_carried_theorem(*args, **kwargs)


def _solve_adhoc_governed(*args, **kwargs):
    """Load the proof-search lifecycle only for a proof-producing request."""

    from ztare.leanmill.solver.solver_core import solve_adhoc_governed

    return solve_adhoc_governed(*args, **kwargs)


def _typed_ratification_open_failure(
    source_text: str,
    target: str,
    source_file: str,
    error: ValueError,
) -> dict:
    """Classify a carried declaration that cannot enter the theorem contract.

    ``--ratify-existing-target`` is proposition-level: it opens one theorem or
    lemma and requires the source-aware ``C -> not C`` matched control. A
    proof-bearing ``def`` is a construction artifact, so sending it through
    that contract would manufacture an inapplicable negative control. Return
    a typed boundary result for navigation instead of raising a CLI traceback.
    """
    from ztare.leanmill.lean_source import decl_blocks, decl_kind

    selector = (target or "").strip()
    selector_without_root = (
        selector[len("_root_."):] if selector.startswith("_root_.") else selector
    )
    basename = selector_without_root.rsplit(".", 1)[-1]
    matches = []
    for name, block in decl_blocks(source_text or ""):
        if name and name in {selector_without_root, basename}:
            matches.append({"written_name": name, "kind": decl_kind(block) or "unknown"})

    construction_kinds = {"def", "abbrev", "structure", "inductive", "class", "opaque"}
    unique = matches[0] if len(matches) == 1 else None
    is_construction = bool(unique and unique["kind"] in construction_kinds)
    boundary = {
        "target_name": selector,
        "outcome": (
            "unsupported_artifact_kind" if is_construction
            else "invalid_ratification_target"
        ),
        "artifact_class": "construction_artifact" if is_construction else "unknown",
        "declaration_kind": unique["kind"] if unique else None,
        "provider": None,
        "providers_tried": [],
        "compile_ok": None,
        "reason": (
            "construction artifacts require a typed construction-artifact ratification contract; "
            "the theorem conclusion-perturbation contract was not applied"
            if is_construction else str(error)
        ),
        "required_next_capability": (
            "construction_artifact_ratification" if is_construction
            else "target_identity_repair"
        ),
    }
    return {
        "schema": "leanmill.ratification_boundary.v1",
        "target": selector,
        "source_file": source_file,
        "ratification_only": True,
        "attempted": 0,
        "eligible": 0,
        "closure_candidates": 0,
        "closure_certificate": None,
        "closure_lean": None,
        "derivation_fallback_permitted": False,
        "theorem_contract": "source_aware_conclusion_perturbation",
        "theorem_contract_applied": False,
        "outcome": boundary["outcome"],
        "results": [boundary],
        "declaration_matches": matches,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ztare leanmill solve-adhoc",
        description="Run a single Lean declaration through LeanMill's governed proof path."
    )
    parser.add_argument("--target", required=True, help="Lean declaration name to prove.")
    parser.add_argument("--source-file", required=True, help="Lean file containing the target.")
    parser.add_argument("--goal", default="", help="Optional goal text shown to the solver.")
    parser.add_argument("--provider", default=None, help="Optional solver provider override.")
    parser.add_argument("--timeout", type=int, default=500, help="Attempt timeout in seconds.")
    parser.add_argument("--mode", choices=["cascade", "dag_search"], default="dag_search")
    parser.add_argument("--substrate", default=None, help="Optional Lake project directory.")
    parser.add_argument("--notes", default=None, help="Optional notes file to guide decomposition.")
    parser.add_argument(
        "--ratify-existing-target",
        action="store_true",
        help=(
            "Extract the target's existing proof and send it directly through "
            "governance with derivation fallback disabled."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print JSON. Accepted for symmetry; output is JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    notes = Path(args.notes).read_text(encoding="utf-8") if args.notes else None
    substrate = Path(args.substrate) if args.substrate else None
    preverified_proof = None
    if args.ratify_existing_target:
        from ztare.leanmill.lean_source import open_decl_for_ratification

        try:
            source_text, preverified_proof = open_decl_for_ratification(
                source_text, args.target
            )
        except ValueError as error:
            result = _typed_ratification_open_failure(
                source_text, args.target, args.source_file, error
            )
            print(json.dumps(result, indent=2, sort_keys=True, default=str))
            return 0
    if preverified_proof is not None:
        if args.provider is not None:
            raise ValueError(
                "ratify-existing-target forbids provider overrides"
            )
        result = _ratify_carried_theorem(
            args.target,
            source_text,
            preverified_proof,
            args.goal,
            lean_root=substrate or DEFAULT_LEAN_ROOT,
            timeout_s=args.timeout,
            provider_label="existing_artifact",
        )
    else:
        result = _solve_adhoc_governed(
            args.target,
            source_text,
            args.goal,
            provider=args.provider,
            timeout_s=args.timeout,
            mode=args.mode,
            substrate=substrate,
            notes=notes,
        )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
