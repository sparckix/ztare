#!/usr/bin/env python3
"""Structural-analogy miner — pair one-shots with analogous loops.

Closes the reflexive-mining blind spot identified 2026-05-06 PM:
today's miners can ask "is X engaging / load-bearing / dead /
covered" but cannot ask "this one-shot generation step looks like
that loop — should it become recursive?"

Consumes the process catalog produced by ``mine_process_loops.py``
and pairs each one-shot/recursion-candidate with its closest
structural analogue from the loops list. Pairing uses three
signals:

  1. **Path-class kinship** — shared parent directory bucket
     (org/charters/ ~ org/mandates/, scripts/public/mining/ ~ scripts/public/)
  2. **Lexical overlap** — Jaccard over filename tokens + seam_ids
  3. **Seed-declared input/output class match** when both are in
     the seed catalog

Output: ``analytics/public/queries/process/structural_analogies.{json,md}`` with
pairs ranked by combined similarity score and a rationale string
the operator can use to decide "is this one-shot actually a
recursion candidate?"

Pure CPU. No LLM. Reads only `process_catalog.json` + the seed YAML.

Usage:
    python scripts/public/mining/mine_process_loops.py     # produces input
    python scripts/public/mining/mine_structural_analogies.py
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml  # type: ignore[import-untyped]

REPO = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO / "analytics" / "public" / "queries" / "process" / "process_catalog.json"
SEED_PATH = REPO / "org" / "runtime" / "process_catalog_seed.yaml"
OUT_JSON = REPO / "analytics" / "public" / "queries" / "process" / "structural_analogies.json"
OUT_MD = REPO / "analytics" / "public" / "queries" / "process" / "structural_analogies.md"


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]+")


def _tokens(s: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(s) if len(t) > 2}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


# Path-class buckets — artifacts in the same bucket share a structural
# role. Hand-tuned, kept short. Add buckets as new artifact families
# emerge.
_PATH_BUCKETS = {
    "charters": ["org/charters", "charter"],
    "mandates": ["org/mandates", "mandate"],
    "rubrics": ["rubric", "scaffold_rubric"],
    "key_results": ["org/key_results", "kr_"],
    "objectives": ["org/objectives"],
    "signals": ["org/signals"],
    "seams": ["research_areas/private/seams"],
    "evidence": ["evidence"],
    "miners": ["scripts/public/mining"],
    "audits": ["scripts/public/", "audit_"],
    "gates": ["src/ztare/gates"],
    "orchestrator": ["src/ztare/orchestrator"],
    "queries": ["analytics/public/queries"],
}


def _path_bucket(path: str) -> Optional[str]:
    plow = path.lower()
    for bucket, fragments in _PATH_BUCKETS.items():
        if any(f in plow for f in fragments):
            return bucket
    return None


def _path_class_kinship(p1: str, p2: str) -> float:
    """1.0 if same bucket, 0.5 if both are in org/ or both in scripts/public/, 0.0 else."""
    b1 = _path_bucket(p1)
    b2 = _path_bucket(p2)
    if b1 and b2 and b1 == b2:
        return 1.0
    same_org = p1.startswith("org/") and p2.startswith("org/")
    same_scripts = p1.startswith("scripts/public/") and p2.startswith("scripts/public/")
    same_seams = p1.startswith("research_areas/private/seams") and p2.startswith(
        "research_areas/private/seams"
    )
    if same_org or same_scripts or same_seams:
        return 0.5
    return 0.0


def _load_seed_by_pointer() -> dict[str, dict]:
    """Map code_pointer → seed entry (full)."""
    if not SEED_PATH.exists():
        return {}
    try:
        data = yaml.safe_load(SEED_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    out: dict[str, dict] = {}
    for entry in (data or {}).get("processes", []) or []:
        for ptr in entry.get("code_pointers") or []:
            if isinstance(ptr, str) and ptr.strip() and not ptr.startswith("(TODO"):
                out[ptr.strip()] = entry
    return out


def _consumes_overlap(seed_a: Optional[dict], seed_b: Optional[dict]) -> float:
    """Jaccard on the consumes/produces sets of two seed entries."""
    if not seed_a or not seed_b:
        return 0.0
    a_in = set(seed_a.get("consumes") or [])
    b_in = set(seed_b.get("consumes") or [])
    a_out = set(seed_a.get("produces") or [])
    b_out = set(seed_b.get("produces") or [])
    return 0.5 * _jaccard(a_in, b_in) + 0.5 * _jaccard(a_out, b_out)


def _score_pair(
    one_shot: dict,
    loop: dict,
    seed_lookup: dict[str, dict],
) -> tuple[float, list[str]]:
    """Return (combined_score, rationale_lines)."""
    rationale: list[str] = []
    p_kin = _path_class_kinship(one_shot["path"], loop["path"])
    if p_kin > 0:
        rationale.append(f"path-class kinship = {p_kin}")

    one_tokens = _tokens(one_shot["path"]) | _tokens(
        one_shot.get("frontmatter_seam_id", "") or ""
    )
    loop_tokens = _tokens(loop["path"]) | _tokens(
        loop.get("frontmatter_seam_id", "") or ""
    )
    lex = _jaccard(one_tokens, loop_tokens)
    if lex > 0:
        rationale.append(f"lexical-token Jaccard = {lex:.2f}")

    seed_a = seed_lookup.get(one_shot["path"])
    seed_b = seed_lookup.get(loop["path"])
    seed_score = _consumes_overlap(seed_a, seed_b)
    if seed_score > 0:
        rationale.append(f"seed consumes/produces overlap = {seed_score:.2f}")

    # Combined score — weighted sum, capped at 1.0
    combined = min(1.0, 0.4 * p_kin + 0.3 * lex + 0.3 * seed_score)
    return round(combined, 3), rationale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    ap.add_argument("--top-k-per-one-shot", type=int, default=3)
    ap.add_argument("--score-floor", type=float, default=0.10,
                    help="Drop pairs below this combined score")
    args = ap.parse_args()

    print("=== structural-analogy miner ===")
    if not args.catalog.exists():
        print(f"  ERROR: missing {args.catalog}; run mine_process_loops.py first")
        return 2

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    one_shots_and_candidates = (
        catalog.get("recursion_candidates") or []
    )
    loops = catalog.get("loops") or []
    print(f"  recursion-candidate one-shots: {len(one_shots_and_candidates)}")
    print(f"  detected loops: {len(loops)}")

    seed_lookup = _load_seed_by_pointer()
    print(f"  seed entries (for consumes/produces overlap): {len(seed_lookup)}")

    pairs: list[dict] = []
    for one in one_shots_and_candidates:
        scored = []
        for loop in loops:
            score, rationale = _score_pair(one, loop, seed_lookup)
            if score < args.score_floor:
                continue
            scored.append({
                "one_shot": one["path"],
                "one_shot_kind": one["inferred_kind"],
                "analogous_loop": loop["path"],
                "loop_confidence": loop.get("confidence", 0.0),
                "score": score,
                "rationale": rationale,
            })
        scored.sort(key=lambda p: -p["score"])
        for p in scored[: args.top_k_per_one_shot]:
            pairs.append(p)
    pairs.sort(key=lambda p: -p["score"])

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_pairs": len(pairs),
        "n_distinct_one_shots": len({p["one_shot"] for p in pairs}),
        "score_floor": args.score_floor,
        "top_k_per_one_shot": args.top_k_per_one_shot,
        "pairs": pairs,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {args.out_json}")

    md = ["# Structural-Analogy Pairing — Recursion Candidates\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(
        f"_Pairs:_ {len(pairs)}  "
        f"_Distinct one-shots:_ {payload['n_distinct_one_shots']}  "
        f"_Score floor:_ {args.score_floor}\n"
    )
    md.append(
        "Each row: a one-shot artifact paired with its closest existing "
        "loop / periodic process by the structural-analogy heuristic. "
        "**A high score does NOT prove the one-shot should be a loop**; "
        "it surfaces a candidate for operator inspection. The point is "
        "to make the question askable, not to auto-propose recursion.\n"
    )

    md.append("## Top recursion candidates\n")
    md.append(
        "| Score | One-shot | Closest loop | Rationale |\n"
        "|---:|---|---|---|"
    )
    for p in pairs[:30]:
        rationale = "; ".join(p["rationale"])[:120]
        md.append(
            f"| {p['score']} | `{p['one_shot']}` | "
            f"`{p['analogous_loop']}` | {rationale} |"
        )
    md.append("")

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    print(f"  emitted {len(pairs)} pairs (one-shot ↔ loop)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
