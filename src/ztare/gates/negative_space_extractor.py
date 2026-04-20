"""Negative-space extractor (GP-061.B — inverted/void detector).

Sibling of `structural_constraint_extractor` (positive invariant path) and
`trajectory_thrash_detector` (trajectory axis). Reads the generalized AST
feature matrix across all failed families and surfaces (func, arg_pos, op)
slots that are present in the *candidate universe* but absent from every
observed family — i.e. mathematical moves the mutator has *never* tried.

Emits into the same `derived_constraints.json` delivery channel under
`producer=negative_space_extractor`. No veto, no retry, no live wiring
until the cold-retroactive gate passes on two closed sandboxes.

Design notes
------------
- Universe is derived mechanically from the observed corpus: for every
  (fname, arg_pos) pair seen in any family, all operator-type slots in
  `_GENERALIZED_OPS` + {Call} + the `leaf` tag constitute the candidate
  universe. A void is a slot in the universe that no family filled.
- Voids are only actionable when the universe is dense enough to make
  absence informative — we require at least `MIN_FAMILIES_FOR_VOID` failed
  families and at least `MIN_FILLED_SLOTS_PER_KEY` filled slots at a given
  (fname, arg_pos) key before emitting voids at that key. This is the
  guard against the "features no one has tried because they're gibberish"
  failure mode.
- The detector emits at most one constraint per run, containing all
  surfaced voids. Overfit-guard: the voids list is read by the Taxonomic
  LLM (or deterministic fallback below) which must decide whether the
  void is *actionable* or *coincidental*. This is a deliberate second
  filter after the mechanical void computation.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.ztare.gates.structural_constraint_extractor import (
    _GENERALIZED_OPS,
    _normalize_family_label,
    _parse_to_ast,
    extract_generalized_feature_matrix,
)


MIN_FAMILIES_FOR_VOID = 3
MIN_FILLED_SLOTS_PER_KEY = 2
RESIDUAL_THRESHOLD_DEFAULT = 0.15


@dataclass
class NegativeSpaceDiagnostic:
    fired: bool
    family_count: int
    universe_size: int
    present_feature_count: int
    void_features: list[str] = field(default_factory=list)
    void_keys_by_function: dict[str, list[str]] = field(default_factory=dict)
    sample_family_labels: list[str] = field(default_factory=list)


def _candidate_universe(feature_bags: list[set[str]]) -> set[str]:
    """Enumerate the (fname, arg_pos) × op_type candidate slots observed.

    Universe construction rule: for every (fname, arg_pos) pair observed
    in at least one family, emit the cartesian product of that key with
    the full operator catalog plus the `leaf` tag and the `Call` tag. This
    makes absence meaningful — every slot in the universe is one the
    mutator *could* have tried inside an argument the mutator *did*
    actually use.
    """
    keys: set[tuple[str, int]] = set()
    for bag in feature_bags:
        for feat in bag:
            if not feat.startswith("fn:"):
                continue
            # shape: fn:{fname}|arg{i}|<rest>
            try:
                fn_part, arg_part, _rest = feat.split("|", 2)
                fname = fn_part[len("fn:") :]
                arg_idx = int(arg_part[len("arg") :])
            except (ValueError, IndexError):
                continue
            keys.add((fname, arg_idx))

    universe: set[str] = set()
    op_catalog = list(_GENERALIZED_OPS.keys()) + ["Call"]
    for fname, arg_idx in keys:
        for op in op_catalog:
            universe.add(f"fn:{fname}|arg{arg_idx}|has_op:{op}")
        # Note: `leaf` is intentionally excluded from the candidate universe.
        # Any nontrivial mutator will put *some* operator in the argument, so
        # `leaf` would be a trivially-void slot on basically every corpus and
        # would clutter the voids list without adding signal. The feature is
        # still emitted by extract_generalized_feature_matrix for downstream
        # introspection, just not enumerated as a candidate here.
    return universe


def _group_by_key(features: set[str]) -> dict[tuple[str, int], set[str]]:
    out: dict[tuple[str, int], set[str]] = {}
    for feat in features:
        if not feat.startswith("fn:"):
            continue
        try:
            fn_part, arg_part, rest = feat.split("|", 2)
            fname = fn_part[len("fn:") :]
            arg_idx = int(arg_part[len("arg") :])
        except (ValueError, IndexError):
            continue
        out.setdefault((fname, arg_idx), set()).add(rest)
    return out


def detect_negative_space(
    *,
    families: list[dict[str, Any]],
    residual_threshold: float = RESIDUAL_THRESHOLD_DEFAULT,
) -> NegativeSpaceDiagnostic:
    _FAILED_CLASSIFICATIONS = {"structural_misfit", "parametric_noise"}
    failed = [
        f
        for f in families
        if f.get("latest_diagnostic_classification") in _FAILED_CLASSIFICATIONS
        and float(f.get("latest_visible_max_abs_residual", 0.0))
        >= residual_threshold
    ]

    if len(failed) < MIN_FAMILIES_FOR_VOID:
        return NegativeSpaceDiagnostic(
            fired=False,
            family_count=len(failed),
            universe_size=0,
            present_feature_count=0,
        )

    feature_bags: list[set[str]] = []
    sample_labels: list[str] = []
    for family in failed:
        label = family.get("family_label", "")
        tree = _parse_to_ast(label)
        if tree is None:
            continue
        bag = extract_generalized_feature_matrix(tree)
        if bag:
            feature_bags.append(bag)
            if len(sample_labels) < 5:
                sample_labels.append(label)

    if len(feature_bags) < MIN_FAMILIES_FOR_VOID:
        return NegativeSpaceDiagnostic(
            fired=False,
            family_count=len(feature_bags),
            universe_size=0,
            present_feature_count=0,
        )

    universe = _candidate_universe(feature_bags)
    present: set[str] = set().union(*feature_bags)
    # Limit to op/leaf slots only — depth features are informative for
    # reporting but aren't part of the void-slot universe.
    present_slot_features = {
        f for f in present if "|has_op:" in f or f.endswith("|leaf")
    }

    voids = universe - present_slot_features

    # Density guard: only report voids at keys where at least
    # MIN_FILLED_SLOTS_PER_KEY distinct slots are filled across the corpus.
    # If a key has only one filled slot, absence of other slots is not
    # informative — the mutator just hasn't varied at that key yet.
    present_by_key = _group_by_key(present_slot_features)
    dense_keys = {
        key
        for key, rests in present_by_key.items()
        if sum(1 for r in rests if r.startswith("has_op:") or r == "leaf")
        >= MIN_FILLED_SLOTS_PER_KEY
    }

    def _void_key(feat: str) -> tuple[str, int] | None:
        try:
            fn_part, arg_part, _ = feat.split("|", 2)
            return (fn_part[len("fn:") :], int(arg_part[len("arg") :]))
        except (ValueError, IndexError):
            return None

    dense_voids = sorted(
        v for v in voids if (_void_key(v) or ("", -1)) in dense_keys
    )

    voids_by_fn: dict[str, list[str]] = {}
    for v in dense_voids:
        key = _void_key(v)
        if key is None:
            continue
        fname, arg_idx = key
        voids_by_fn.setdefault(fname, []).append(f"arg{arg_idx}|{v.split('|', 2)[2]}")

    fired = len(dense_voids) > 0

    return NegativeSpaceDiagnostic(
        fired=fired,
        family_count=len(feature_bags),
        universe_size=len(universe),
        present_feature_count=len(present_slot_features),
        void_features=dense_voids,
        void_keys_by_function=voids_by_fn,
        sample_family_labels=sample_labels,
    )


def build_negative_space_proposal(
    diagnostic: NegativeSpaceDiagnostic,
    *,
    project: str,
) -> dict[str, str] | None:
    if not diagnostic.fired or not diagnostic.void_features:
        return None
    void_lines = []
    for fname, voids in sorted(diagnostic.void_keys_by_function.items()):
        for v in sorted(voids):
            void_lines.append(f"  - {fname}({v})")
    voids_block = "\n".join(void_lines)
    constraint = (
        f"Across {diagnostic.family_count} failed families the mutator has "
        f"never exercised the following structural slots (operator types at "
        f"function-argument positions that every candidate left empty):\n"
        f"{voids_block}\n"
        f"Any valid next candidate MUST fill at least one of these voids "
        f"unless it can articulate why the slot is grammatically or "
        f"physically inadmissible."
    )
    rationale = (
        f"Negative-space scan: universe={diagnostic.universe_size} slot "
        f"features derived from observed (function, arg_pos) keys; "
        f"{diagnostic.present_feature_count} present across corpus; "
        f"{len(diagnostic.void_features)} dense voids surfaced (keys with "
        f">= {MIN_FILLED_SLOTS_PER_KEY} filled slots). No family-level "
        f"hand-picking of features; all slots emitted mechanically by "
        f"`extract_generalized_feature_matrix`."
    )
    return {
        "constraint": constraint,
        "applies_to": f"mutator search-space coverage over {project}",
        "failure_family": "negative_space_blind_spot",
        "severity": "degrading",
        "producer": "negative_space_extractor",
        "rationale": rationale,
        "non_applicability_condition": (
            "Only non-applicable when a void slot is ruled out by the "
            "declared grammar spec or by a physical-admissibility "
            "constraint already recorded in project_charter.md."
        ),
    }


def run_negative_space_extractor(
    *,
    project_dir: Path,
    residual_threshold: float = RESIDUAL_THRESHOLD_DEFAULT,
) -> tuple[NegativeSpaceDiagnostic, dict[str, str] | None]:
    structural_path = project_dir / "workspace" / "structural_memory.json"
    if not structural_path.exists():
        return (
            NegativeSpaceDiagnostic(
                fired=False,
                family_count=0,
                universe_size=0,
                present_feature_count=0,
            ),
            None,
        )
    try:
        payload = json.loads(structural_path.read_text())
    except (json.JSONDecodeError, OSError):
        return (
            NegativeSpaceDiagnostic(
                fired=False,
                family_count=0,
                universe_size=0,
                present_feature_count=0,
            ),
            None,
        )
    families = [f for f in payload.get("families", []) if isinstance(f, dict)]
    diagnostic = detect_negative_space(
        families=families, residual_threshold=residual_threshold
    )
    proposal = build_negative_space_proposal(diagnostic, project=project_dir.name)
    return diagnostic, proposal


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="GP-061.B negative-space / void extractor (dry-run CLI)."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--projects-root", default="projects")
    parser.add_argument(
        "--residual-threshold", type=float, default=RESIDUAL_THRESHOLD_DEFAULT
    )
    args = parser.parse_args()

    project_dir = Path(args.projects_root) / args.project
    if not project_dir.exists():
        print(f"[neg-space] project_dir not found: {project_dir}")
        return 1

    diagnostic, proposal = run_negative_space_extractor(
        project_dir=project_dir,
        residual_threshold=args.residual_threshold,
    )

    print("[neg-space] --- diagnostic ---")
    print(f"  fired: {diagnostic.fired}")
    print(f"  family_count: {diagnostic.family_count}")
    print(f"  universe_size: {diagnostic.universe_size}")
    print(f"  present_feature_count: {diagnostic.present_feature_count}")
    print(f"  void_feature_count: {len(diagnostic.void_features)}")
    print("  void features by function:")
    for fname in sorted(diagnostic.void_keys_by_function):
        print(f"    {fname}:")
        for v in sorted(diagnostic.void_keys_by_function[fname]):
            print(f"      - {v}")
    print()
    if diagnostic.sample_family_labels:
        print("  sample failed family labels:")
        for lbl in diagnostic.sample_family_labels:
            print(f"    - {lbl}")
    print()
    if proposal is None:
        print("[neg-space] no proposal emitted.")
        return 0
    print("[neg-space] --- proposal ---")
    print(json.dumps(proposal, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
