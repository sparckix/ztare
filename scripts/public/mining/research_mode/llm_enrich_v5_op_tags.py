#!/usr/bin/env python3
"""LLM-enriched v5-op tagging on the verified-axioms corpus.

The keyword tagger in mine_closure_patterns.py catches ~4.2% of
2,595 axioms — too few for the closure-pattern miner's grammar-
evolution arm to be decision-critical. This script does a one-pass
LLM enrichment:

  1. Walk projects/*/verified_axioms.json (same loader as the miner)
  2. Batch axioms (default 10/batch) into a tagging prompt that lists
     the 15 v5 ops with one-line definitions
  3. LLM returns JSON {axiom_id: [op_ids]} per batch
  4. Cache + write ``analytics/public/queries/v5_op_tags_llm.json`` keyed
     by ``f"{project}::{axiom_idx_in_corpus}"``

Cost: ~2,500 axioms / 10 per batch = 250 calls. On gpt-4.1-mini
that's ~$0.25-$3 depending on token count. Use ``--limit N`` for
a pilot, ``--budget USD`` to cap.

Idempotent: re-running re-uses cached tags from the output file
(skips axioms with ≥1 tag already cached). Safe to interrupt + resume.

Output:
  ``analytics/public/queries/v5_op_tags_llm.json`` —
  ``{axiom_id: {axiom_text, project, substrate_class, ops, model_id, ts}}``

Usage:
    python scripts/public/mining/llm_enrich_v5_op_tags.py \\
        --batch-size 10 --limit 100 --model auto
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from src.ztare.common.llm_runtime import (  # noqa: E402
    LLMRuntime,
    pick_default_model_id_for_scripts,
)

# Reuse the miner's loader so we tag the SAME corpus the miner consumes
# — guarantees axiom_id keys line up if the miner is later updated to
# read this enrichment file.
sys.path.insert(0, str(REPO / "scripts" / "mining"))
from mine_closure_patterns import walk_verified_axioms  # noqa: E402


OUT_PATH = REPO / "analytics" / "public" / "queries" / "v5_op_tags_llm.json"


# 15 v5 ops with one-line definitions (mirror of V5_OP_PATTERNS in
# mine_closure_patterns.py; keep these synchronized when the
# vocabulary evolves).
V5_OPS = [
    ("core_01_reformulation",
     "Recast the problem in a different language / domain (translate, isomorph, change of basis)."),
    ("core_02_iterative_refinement",
     "Repeated polishing or sharpening of a candidate solution."),
    ("core_03_decomposition",
     "Split / partition / factorize the problem into sub-pieces."),
    ("core_04_local_to_global",
     "Glue local results / patches / sheaves to a global one."),
    ("core_05_canonical_invariance",
     "Use canonical form, gauge invariance, equivariance, or normalisation."),
    ("core_06_external_framework",
     "Import / borrow a framework from a different field."),
    ("core_07_generalization",
     "Lift / abstract to a broader case (family, parametrised version)."),
    ("broad_extremal_case",
     "Reason via worst-case / extremal / boundary instance."),
    ("broad_compression",
     "Reduce the problem to a simpler equivalent (collapse, equivalence)."),
    ("broad_inversion",
     "Use duality, contrapositive, adjoint, or inversion of the question."),
    ("broad_falsification",
     "Counterexample search / refutation / disproof."),
    ("subfield_pde_estimate_craft",
     "PDE-style estimates: Sobolev/Holder bounds, interpolation, integration."),
    ("subfield_proof_search_pivot",
     "Mid-search switch of tactic / approach / angle."),
    ("subfield_residual_chasing",
     "Asymptotic-tail / convergence-rate / residual-chasing technique."),
    ("subfield_basin_hopping",
     "Optimization-landscape escape (basin-hop, escape local min)."),
]
VALID_OP_IDS = {op_id for op_id, _ in V5_OPS}


PROMPT_HEADER = (
    "You are tagging axioms / verified mathematical statements with "
    "categories from a 15-op research-operations vocabulary. For each "
    "axiom in the batch, return the subset of v5 ops whose META-OPERATION "
    "is plausibly used in the proof-or-derivation of the axiom. Tag only "
    "ops that are clearly applicable; many axioms will have ZERO tags "
    "(empty list is fine).\n\n"
    "v5 op vocabulary (id — definition):\n"
)


def _make_prompt(batch: list[tuple[str, str]]) -> str:
    """Build the LLM prompt for one batch.

    ``batch`` is a list of (axiom_id, axiom_text) tuples.
    """
    lines = [PROMPT_HEADER]
    for op_id, defn in V5_OPS:
        lines.append(f"  - {op_id}: {defn}")
    lines.append("")
    lines.append(
        "Return a SINGLE JSON object mapping axiom_id (the EXACT key I give "
        "you) to a JSON array of v5 op_ids. Do not include explanations, "
        "do not invent op_ids not in the vocabulary, do not return prose. "
        "Empty array `[]` is a valid value if no op applies. Wrap your "
        "JSON in ```json ... ``` fences.\n"
    )
    lines.append("Axioms to tag:")
    for ax_id, ax_text in batch:
        # Truncate excessively long axioms to keep token cost bounded
        snippet = ax_text if len(ax_text) <= 600 else ax_text[:600] + "…"
        lines.append(f"\n## {ax_id}\n{snippet}")
    return "\n".join(lines)


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _parse_response(text: str, expected_ids: set[str]) -> dict[str, list[str]]:
    """Parse LLM JSON response. Returns {axiom_id: [op_ids]}.

    Best-effort: if JSON parse fails, returns empty dict (caller treats
    as "no tags for this batch" and moves on).
    """
    if not text:
        return {}
    m = _JSON_FENCE_RE.search(text)
    raw = m.group(1) if m else text.strip()
    # Strip leading/trailing fences if no match
    if raw.startswith("```"):
        raw = raw.strip("`")
    if raw.startswith("json"):
        raw = raw[4:]
    try:
        obj = json.loads(raw)
    except Exception:  # noqa: BLE001
        # Try to find the first {...} block
        m2 = re.search(r"\{[\s\S]*\}", raw)
        if not m2:
            return {}
        try:
            obj = json.loads(m2.group(0))
        except Exception:  # noqa: BLE001
            return {}
    if not isinstance(obj, dict):
        return {}
    out: dict[str, list[str]] = {}
    for k, v in obj.items():
        if k not in expected_ids:
            continue
        if not isinstance(v, list):
            continue
        ops = [op for op in v if isinstance(op, str) and op in VALID_OP_IDS]
        out[k] = ops
    return out


def _axiom_id(axiom: dict) -> str:
    """Stable per-axiom id: ``{project}::{sha8(axiom_text)}``.

    SHA prefix means re-runs and corpus permutations produce stable
    keys without depending on listing order.
    """
    sha = hashlib.sha1(axiom["axiom_text"].encode("utf-8")).hexdigest()[:8]
    return f"{axiom['project']}::{sha}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--limit", type=int, default=0,
                    help="Max axioms to tag this run; 0 = unlimited")
    ap.add_argument("--model", type=str, default=None,
                    help="Model id; default uses pick_default_model_id_for_scripts")
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--dry-run", action="store_true",
                    help="Build prompts but don't call LLM (for debugging)")
    ap.add_argument("--retag", action="store_true",
                    help="Ignore cache; re-tag every axiom")
    args = ap.parse_args()

    print("=== LLM v5-op enrichment ===")

    # ---- Load corpus ----
    corpus = walk_verified_axioms()
    print(f"  axioms in corpus: {len(corpus)}")

    # ---- Load cache ----
    cache: dict[str, dict] = {}
    if args.out.exists() and not args.retag:
        try:
            cache = json.loads(args.out.read_text(encoding="utf-8")) or {}
            if not isinstance(cache, dict):
                cache = {}
        except Exception:  # noqa: BLE001
            cache = {}
        print(f"  cache: {len(cache)} axioms already tagged")

    # ---- Filter to axioms not yet cached ----
    pending: list[tuple[str, dict]] = []
    for ax in corpus:
        ax_id = _axiom_id(ax)
        if ax_id in cache and cache[ax_id].get("ops") is not None:
            continue
        pending.append((ax_id, ax))
    print(f"  axioms pending: {len(pending)}")
    if args.limit and args.limit > 0:
        pending = pending[: args.limit]
        print(f"  limited to: {len(pending)} (per --limit)")

    if not pending:
        print("  nothing to do")
        return 0

    # ---- Pick model ----
    model_id = args.model or pick_default_model_id_for_scripts()
    if model_id is None:
        print("  ERROR: no LLM provider — set ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY")
        return 2
    print(f"  model: {model_id}")
    if args.dry_run:
        print("  dry-run mode: skipping LLM calls")

    runtime = LLMRuntime() if not args.dry_run else None

    # ---- Batch + tag ----
    n_calls = 0
    n_tagged = 0
    n_with_ops = 0
    started_at = time.time()
    total_batches = (len(pending) + args.batch_size - 1) // args.batch_size
    for bi in range(0, len(pending), args.batch_size):
        batch = pending[bi : bi + args.batch_size]
        batch_pairs = [(ax_id, ax["axiom_text"]) for ax_id, ax in batch]
        prompt = _make_prompt(batch_pairs)
        expected_ids = {ax_id for ax_id, _ in batch_pairs}

        batch_idx = bi // args.batch_size + 1
        if args.dry_run:
            tags = {ax_id: [] for ax_id, _ in batch_pairs}
            elapsed = ""
        else:
            try:
                resp = runtime.call_text(  # type: ignore[union-attr]
                    prompt,
                    model_id=model_id,
                    max_tokens=args.max_tokens,
                    request_label="v5_op_enrichment",
                )
                text = resp.text or ""
            except Exception as exc:  # noqa: BLE001
                print(f"  batch {batch_idx} failed: {type(exc).__name__}: {exc}")
                tags = {}
                text = ""
            else:
                tags = _parse_response(text, expected_ids)
            n_calls += 1
            elapsed = f" ({time.time() - started_at:.0f}s)"

        # Merge into cache
        for ax_id, ax in batch:
            ops = tags.get(ax_id, [])
            cache[ax_id] = {
                "ops": ops,
                "axiom_text": ax["axiom_text"][:500],  # truncate for storage
                "project": ax["project"],
                "substrate_class": ax["substrate_class"],
                "model_id": model_id,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            n_tagged += 1
            if ops:
                n_with_ops += 1

        # Persist after every batch — interrupt-safe
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(cache, indent=2))

        n_with_ops_in_batch = sum(1 for ax_id, _ in batch if cache[ax_id]["ops"])
        print(
            f"  batch {batch_idx}/{total_batches}: "
            f"{n_with_ops_in_batch}/{len(batch)} tagged with ≥1 op{elapsed}"
        )

    # ---- Summary ----
    coverage_with_ops = n_with_ops / max(1, n_tagged)
    print(f"\n  axioms processed: {n_tagged}")
    print(f"  axioms with ≥1 op: {n_with_ops} ({coverage_with_ops:.1%})")
    print(f"  LLM calls: {n_calls}")
    print(f"  output: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
