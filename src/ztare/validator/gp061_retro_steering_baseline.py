"""
GP-061 negative-space extractor — tier-2 retrospective baseline (A-arm only).

Reads the ACTUAL structural_memory.json for sandbox_07 and sandbox_08,
which stores canonical `N(...)` labels (matches what the detector expects).

At each iteration k where the detector can fire (>=3 qualifying families),
it computes:
  - the void set at (fn, arg_pos) keys
  - the chance rate (per-key voids / per-key universe)
  - the next new family to enter the corpus (first_seen_iteration > k)
  - whether that new family's feature bag fills any void at the detected key

Reports observed hit rate vs chance rate across all firing iterations.
This is the A arm — mutator runs with no negative-space injection — which
is factually true for sandbox_07/08 since the extractor did not exist when
they ran. The B arm (live run with injection) is deferred.

Constraints respected:
  - Only `structural_misfit` families enter (matches R4 protocol)
  - Only families with latest_visible_max_abs_residual >= 0.15
  - Dedup by fingerprint, not string
  - Density guard (MIN_FILLED_SLOTS_PER_KEY) applied per detector
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

from src.ztare.gates.negative_space_extractor import (
    detect_negative_space,
    extract_generalized_feature_matrix,
    _parse_to_ast,
    _normalize_family_label,
    _GENERALIZED_OPS,
    MIN_FAMILIES_FOR_VOID,
    MIN_FILLED_SLOTS_PER_KEY,
    RESIDUAL_THRESHOLD_DEFAULT,
)


def load_families(project: str) -> list[dict]:
    repo_root = Path(__file__).resolve().parents[3]
    path = repo_root / "projects" / project / "workspace" / "structural_memory.json"
    d = json.loads(path.read_text())
    fams = d.get("families", []) if isinstance(d, dict) else d
    if isinstance(fams, dict):
        fams = list(fams.values())
    return fams


def qualifies(fam: dict) -> bool:
    if fam.get("latest_diagnostic_classification") != "structural_misfit":
        return False
    r = fam.get("latest_visible_max_abs_residual")
    if r is None or r < RESIDUAL_THRESHOLD_DEFAULT:
        return False
    return True


def feature_bag(family_label: str) -> set[str]:
    normalized = _normalize_family_label(family_label)
    tree = _parse_to_ast(normalized)
    if tree is None:
        return set()
    return extract_generalized_feature_matrix(tree)


def run_detector_on(families: list[dict]):
    # Use detect_negative_space directly; it applies MIN_FAMILIES_FOR_VOID
    # and MIN_FILLED_SLOTS_PER_KEY internally.
    return detect_negative_space(
        families=families, residual_threshold=RESIDUAL_THRESHOLD_DEFAULT
    )


def per_key_universe_and_voids(diag, corpus: list[dict]) -> dict[str, dict]:
    """Build per-key voids (from diag) + filled (by unioning corpus bags)."""
    out = defaultdict(lambda: {"voids": set(), "filled": set()})
    for f in diag.void_features:
        parts = f.split("|")
        if len(parts) < 3:
            continue
        key = parts[0] + "|" + parts[1]
        op = parts[2]
        out[key]["voids"].add(op)
    # Compute filled slots per key by unioning feature bags of the corpus.
    for fam in corpus:
        bag = feature_bag(fam.get("family_label", ""))
        for feat in bag:
            parts = feat.split("|")
            if len(parts) < 3:
                continue
            key = parts[0] + "|" + parts[1]
            op = parts[2]
            if key in out:
                out[key]["filled"].add(op)
    return out


def summarize_project(project: str) -> None:
    print(f"\n====== {project} ======")
    all_fams = load_families(project)
    qfams = [f for f in all_fams if qualifies(f)]
    qfams.sort(key=lambda f: (f.get("first_seen_iteration") or 0))
    print(
        f"total families={len(all_fams)} | qualifying (structural_misfit & residual>={RESIDUAL_THRESHOLD_DEFAULT})={len(qfams)}"
    )
    if not qfams:
        return

    # Walk by iteration index. For each iteration k that introduces >=1 new
    # qualifying family, compute detector state using families with
    # first_seen_iteration <= k, then measure whether the NEXT newly-introduced
    # family's bag fills a void in the current void set.
    intro_iters = sorted({f.get("first_seen_iteration") or 0 for f in qfams})

    observed_hits = 0
    chance_sum = 0.0
    observed_steps = 0

    for idx, k in enumerate(intro_iters[:-1]):
        corpus = [f for f in qfams if (f.get("first_seen_iteration") or 0) <= k]
        if len(corpus) < MIN_FAMILIES_FOR_VOID:
            print(
                f"  iter<= {k:2d}: corpus={len(corpus)} — below MIN_FAMILIES_FOR_VOID, skip"
            )
            continue
        diag = run_detector_on(corpus)
        if not diag.fired:
            print(f"  iter<= {k:2d}: corpus={len(corpus)} fired=False")
            continue

        key_info = per_key_universe_and_voids(diag, corpus)

        # Next iteration that introduces a new family
        next_k = intro_iters[idx + 1]
        new_families = [
            f for f in qfams if (f.get("first_seen_iteration") or 0) == next_k
        ]
        if not new_families:
            continue

        # For each new family, compute its feature bag and check per-key fills.
        for nf in new_families:
            bag = feature_bag(nf.get("family_label", ""))
            # For each key in the detector's dense-key set, compute chance rate
            # and whether the new family's bag fills a void slot at that key.
            per_step_chance = []
            per_step_hit = 0
            for key, info in key_info.items():
                universe_size = len(info["voids"]) + len(info["filled"])
                if universe_size == 0:
                    continue
                chance = len(info["voids"]) / universe_size
                per_step_chance.append(chance)
                # Does this new family touch the void set at this key?
                bag_at_key = {
                    b.split("|")[2]
                    for b in bag
                    if b.startswith(key + "|") and len(b.split("|")) >= 3
                }
                if bag_at_key & info["voids"]:
                    per_step_hit = 1
                    break
            if per_step_chance:
                avg_chance = sum(per_step_chance) / len(per_step_chance)
                observed_hits += per_step_hit
                chance_sum += avg_chance
                observed_steps += 1
                marker = "HIT" if per_step_hit else "miss"
                print(
                    f"  iter<= {k:2d} -> next iter {next_k:2d}: corpus={len(corpus)} "
                    f"keys={len(key_info)} avg_chance={avg_chance:.2f} {marker}"
                )
                print(f"       new family: {nf.get('family_label','')[:100]}")

    if observed_steps == 0:
        print("  NO steps where detector fired with a next-family to measure")
        return
    observed_rate = observed_hits / observed_steps
    chance_rate = chance_sum / observed_steps
    print(
        f"\n  SUMMARY: steps={observed_steps} "
        f"observed_fill_rate={observed_rate:.2f} "
        f"chance_fill_rate={chance_rate:.2f} "
        f"lift={observed_rate - chance_rate:+.2f}"
    )


if __name__ == "__main__":
    for p in ("gp023_planck_sandbox_07", "gp023_planck_sandbox_08"):
        summarize_project(p)
