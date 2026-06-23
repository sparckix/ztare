"""Trajectory-level thrash detector (GP-062).

Reads `workspace/latent_distance.jsonl` (semantic distance axis) and
`workspace/structural_memory.json` (structural feature axis), detects
iterations where the mutator rewrote the thesis completely at the semantic
surface while preserving the outer algebraic skeleton, and emits a
constraint into the GP-061 delivery channel (`derived_constraints.json`)
under `producer=trajectory_extractor`.

No veto, no retry, no mid-iteration interrupt. Same post-eval channel as
GP-061; second reader over a different signal axis.

Status (2026-04-14): implemented + retroactive-test path only. Intentionally
NOT wired into `autoresearch_loop._refresh_derived_constraints_from_eval`
until a second fit-primitive project closes and the feature-set choice is
validated cold. See GP-062 seam for rollout discipline.

Reuses the skeleton feature-bag extractor from
structural_constraint_extractor so the two detectors share a single notion of
"structural feature."
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ztare.gates.structural_constraint_extractor import (
    _extract_feature_bag,
    _normalize_family_label,
    _parse_to_ast,
)


SEMANTIC_THRESHOLD = 0.8
STRUCTURAL_EPSILON = 0.1
MIN_THRASH_COUNT = 2


SKELETON_FEATURE_PREFIXES = (
    "var_power:",
    "has_eml_term",
    "has_outer_additive_const",
    "eml_arg:",
    "eml_first_arg_negated",
)


def _is_skeleton_feature(feature: str) -> bool:
    return any(
        feature == prefix or feature.startswith(prefix)
        for prefix in SKELETON_FEATURE_PREFIXES
    )


@dataclass
class ThrashDiagnostic:
    fired: bool
    iterations_covered: list[int] = field(default_factory=list)
    semantic_means: list[float] = field(default_factory=list)
    structural_deltas: list[float] = field(default_factory=list)
    preserved_features: list[str] = field(default_factory=list)


def _load_latent_distance(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _load_families(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(payload, dict):
        return []
    families = payload.get("families", [])
    return [f for f in families if isinstance(f, dict)]


def _semantic_mean(row: dict[str, Any]) -> float | None:
    distances = row.get("distances") or {}
    if not isinstance(distances, dict):
        return None
    axes = [
        distances.get("jaccard_failure_families"),
        distances.get("jaccard_attack_surface"),
        distances.get("jaccard_named_primitives"),
        distances.get("thesis_text_distance"),
    ]
    vals = [v for v in axes if isinstance(v, (int, float))]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _skeleton_bag_for_iteration(
    families: list[dict[str, Any]],
    iteration: int,
) -> set[str]:
    bag: set[str] = set()
    for family in families:
        first = family.get("first_seen_iteration")
        if first != iteration:
            continue
        label = family.get("family_label", "")
        tree = _parse_to_ast(_normalize_family_label(label))
        if tree is None:
            continue
        feats = _extract_feature_bag(tree)
        bag.update(f for f in feats if _is_skeleton_feature(f))
    return bag


def _jaccard_distance(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return 1.0 - (len(a & b) / len(union))


def _carry_forward_bags(
    iterations: list[int],
    bag_by_iter: dict[int, set[str]],
) -> dict[int, set[str]]:
    """For iterations with empty skeleton bags (no family first-seen that iter),
    carry forward the most recent non-empty bag. Iterations frequently re-try
    members of earlier families without registering a new fingerprint.
    """
    filled: dict[int, set[str]] = {}
    last: set[str] = set()
    for i in iterations:
        cur = bag_by_iter.get(i, set())
        if cur:
            last = cur
        filled[i] = last
    return filled


def detect_trajectory_thrash(
    *,
    latent_rows: list[dict[str, Any]],
    families: list[dict[str, Any]],
) -> ThrashDiagnostic:
    iterations = sorted(
        {
            int(row["iteration_index"])
            for row in latent_rows
            if isinstance(row.get("iteration_index"), int)
        }
    )
    if len(iterations) < 2:
        return ThrashDiagnostic(fired=False)

    semantic_by_iter: dict[int, float] = {}
    for row in latent_rows:
        i = row.get("iteration_index")
        if not isinstance(i, int):
            continue
        sm = _semantic_mean(row)
        if sm is not None:
            semantic_by_iter[i] = sm

    raw_bags = {i: _skeleton_bag_for_iteration(families, i) for i in iterations}
    bag_by_iter = _carry_forward_bags(iterations, raw_bags)

    thrash_iters: list[int] = []
    semantic_means: list[float] = []
    structural_deltas: list[float] = []
    preserved_accumulator: set[str] | None = None

    prev_i: int | None = None
    for i in iterations:
        if prev_i is None:
            prev_i = i
            continue
        prev_bag = bag_by_iter.get(prev_i, set())
        cur_bag = bag_by_iter.get(i, set())
        sem = semantic_by_iter.get(i)
        prev_i = i

        if sem is None:
            continue
        if not prev_bag or not cur_bag:
            continue

        struct_delta = _jaccard_distance(prev_bag, cur_bag)
        if sem >= SEMANTIC_THRESHOLD and struct_delta <= STRUCTURAL_EPSILON:
            thrash_iters.append(i)
            semantic_means.append(sem)
            structural_deltas.append(struct_delta)
            preserved = prev_bag & cur_bag
            if preserved_accumulator is None:
                preserved_accumulator = set(preserved)
            else:
                preserved_accumulator &= preserved

    fired = len(thrash_iters) >= MIN_THRASH_COUNT
    preserved_features = sorted(preserved_accumulator) if preserved_accumulator else []

    return ThrashDiagnostic(
        fired=fired,
        iterations_covered=thrash_iters,
        semantic_means=semantic_means,
        structural_deltas=structural_deltas,
        preserved_features=preserved_features,
    )


def build_thrash_constraint_proposal(
    diagnostic: ThrashDiagnostic,
    *,
    project: str,
) -> dict[str, str] | None:
    if not diagnostic.fired or not diagnostic.preserved_features:
        return None
    n = len(diagnostic.iterations_covered)
    feat_list = ", ".join(diagnostic.preserved_features)
    rounded_sem = [round(x, 3) for x in diagnostic.semantic_means]
    rounded_delta = [round(x, 3) for x in diagnostic.structural_deltas]
    constraint = (
        f"Across the last {n} iterations the mutator rewrote failure_families, "
        f"attack_surface, named_primitives, and thesis text completely while "
        f"preserving the structural features: {feat_list}. Any valid next "
        f"candidate MUST remove or alter at least one of these features."
    )
    rationale = (
        f"semantic_mean={rounded_sem}, structural_delta={rounded_delta} "
        f"across iterations {diagnostic.iterations_covered}; thresholds "
        f"semantic>={SEMANTIC_THRESHOLD}, structural<={STRUCTURAL_EPSILON}."
    )
    return {
        "constraint": constraint,
        "applies_to": f"mutator trajectory over {project}",
        "failure_family": "trajectory_thrash",
        "severity": "degrading",
        "producer": "trajectory_extractor",
        "rationale": rationale,
        "non_applicability_condition": (
            "Only non-applicable when the thesis intentionally fixes the skeleton "
            "and varies only fit coefficients across iterations."
        ),
    }


def run_trajectory_thrash_detector(
    *,
    project_dir: Path,
) -> tuple[ThrashDiagnostic, dict[str, str] | None]:
    latent_path = project_dir / "workspace" / "latent_distance.jsonl"
    structural_path = project_dir / "workspace" / "structural_memory.json"

    latent_rows = _load_latent_distance(latent_path)
    families = _load_families(structural_path)

    diagnostic = detect_trajectory_thrash(
        latent_rows=latent_rows, families=families
    )
    proposal = build_thrash_constraint_proposal(diagnostic, project=project_dir.name)
    return diagnostic, proposal


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="GP-062 trajectory-thrash detector dry-run CLI."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--projects-root", default="projects")
    args = parser.parse_args()

    project_dir = Path(args.projects_root) / args.project
    if not project_dir.exists():
        print(f"[thrash] project_dir not found: {project_dir}")
        return 1

    diagnostic, proposal = run_trajectory_thrash_detector(project_dir=project_dir)

    print("[thrash] --- diagnostic ---")
    print(f"  fired: {diagnostic.fired}")
    print(f"  iterations_covered: {diagnostic.iterations_covered}")
    print(
        f"  semantic_means: {[round(x, 3) for x in diagnostic.semantic_means]}"
    )
    print(
        f"  structural_deltas: {[round(x, 3) for x in diagnostic.structural_deltas]}"
    )
    print(f"  preserved_features: {diagnostic.preserved_features}")
    print()
    if proposal is None:
        print("[thrash] no proposal emitted.")
        return 0
    print("[thrash] --- proposal ---")
    print(json.dumps(proposal, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
