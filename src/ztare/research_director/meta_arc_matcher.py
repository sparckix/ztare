"""GP-215 matcher — the NASA-LLIS-bottleneck artifact.

Given a substrate's current stall description (free-form text), rank the
catalogue of meta-move clusters by which one would resolve the stall.

Inputs (read at runtime, not bundled):
  analytics/public/queries/gp215/gp215_cycles_filled.json        — NS cycles, base
  analytics/public/queries/gp215/gp215_cluster6_subdivision.json — NS sub-clusters
  analytics/public/queries/gp215/gp215_results.json              — NS singleton clusters
  analytics/public/queries/gp215/gp215_cycles_aqual.json         — AQUAL cycles
  analytics/public/queries/gp215/gp215_cycles_neural.json        — neural cycles

Output (per stall query):
  - top-K ranked meta-moves with cosine score, source substrate, source cycle
  - adversary move (per panel-clause-F monoculture guard): the highest-ranked
    move from a different cluster than the top match, surfaced as a forced
    contrast option

CLI:
  python -m ztare.research_director.meta_arc_matcher \\
      --stall "free-form stall description" \\
      [--substrate ns|aqual|neural|all] \\
      [--top-k 5]

Library:
  from ztare.research_director.meta_arc_matcher import match_stall, load_catalog
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
QUERY_ROOTS = [
    REPO_ROOT / "analytics" / "queries",
    REPO_ROOT / "analytics" / "public" / "queries" / "gp215",
    REPO_ROOT / "analytics" / "public" / "queries",
]

DEFAULT_INBOX = REPO_ROOT / "ztare_workspace" / "inbox" / "meta_arc_recommendations"


def _query_path(name: str) -> Path:
    for root in QUERY_ROOTS:
        path = root / name
        if path.exists():
            return path
    roots = ", ".join(str(root) for root in QUERY_ROOTS)
    raise FileNotFoundError(f"{name} not found under any query root: {roots}")


def _read_query_json(name: str) -> Any:
    return json.loads(_query_path(name).read_text())


@dataclass
class MetaMove:
    move_id: str            # human-readable id
    move_name: str          # short label
    signature: str          # one-sentence structural description
    source_substrate: str   # ns | aqual | neural
    source_cycle: str       # phase or iteration range
    representative_text: str  # text used for embedding
    object_created: str     # the kind of artifact this move produces
    cluster_id: str | None  # optional cluster label for grouping


def _cycle_text_ns(c: dict) -> str:
    pod = c.get("proof_object_delta", {}) or {}
    return (
        f"resolution: {c.get('resolution_move','')} "
        f"object_before: {pod.get('before','')} "
        f"object_after: {pod.get('after','')} "
        f"delta_type: {pod.get('delta_type','')} "
        f"survived: {c.get('what_survived','')} "
        f"opened: {c.get('what_opened','')}"
    )


def _cycle_text_iter(c: dict) -> str:
    pod = c.get("proof_object_delta", {}) or {}
    return (
        f"resolution: {c.get('resolution_move','')} "
        f"object_before: {pod.get('before','')} "
        f"object_after: {pod.get('after','')} "
        f"delta_type: {pod.get('delta_type','')} "
        f"opened: {c.get('what_opened','')} "
        f"final_weakest: {c.get('final_weakest','')[:300]}"
    )


def load_catalog(substrate: str = "all") -> list[MetaMove]:
    """Load the full catalog from disk. Returns a list of MetaMove records,
    one per cycle. Sub-cluster info is attached when present."""
    moves: list[MetaMove] = []

    # NS — base cycles
    if substrate in ("ns", "all"):
        ns_cycles = _read_query_json("gp215_cycles_filled.json")
        ns_subs = _read_query_json("gp215_cluster6_subdivision.json")
        # Build cycle_id → sub_cluster lookup
        cycle_to_sub = {}
        for sub in ns_subs.get("sub_clusters", []):
            for ph in sub.get("members", []):
                cycle_to_sub[ph] = sub
        for c in ns_cycles:
            if "fill_error" in c:
                continue
            phase_label = f"{c['start_phase']}→{c['end_phase']}"
            sub = cycle_to_sub.get(phase_label)
            if sub:
                cluster_id = sub["sub_id"]
                cluster_name = sub["sub_move_name"]
                signature = sub.get("signature", "")
                object_created = sub.get("object_created", "")
            else:
                cluster_id = c.get("structural_move_class", "ns_singleton")
                cluster_name = c.get("structural_move_class", "ns_singleton")
                signature = c.get("resolution_move", "")
                pod = c.get("proof_object_delta", {}) or {}
                object_created = pod.get("after", "")
            moves.append(MetaMove(
                move_id=f"ns:{phase_label}",
                move_name=cluster_name,
                signature=signature[:250],
                source_substrate="ns",
                source_cycle=phase_label,
                representative_text=_cycle_text_ns(c),
                object_created=object_created[:200],
                cluster_id=cluster_id,
            ))

    # AQUAL
    if substrate in ("aqual", "all"):
        aqual_cycles = _read_query_json("gp215_cycles_aqual.json")
        for c in aqual_cycles:
            if "fill_error" in c:
                continue
            it_label = f"iter{c['start_iteration']}→{c['end_iteration']}"
            pod = c.get("proof_object_delta", {}) or {}
            moves.append(MetaMove(
                move_id=f"aqual:{it_label}",
                move_name=c.get("structural_move_class", "?"),
                signature=c.get("resolution_move", "")[:250],
                source_substrate="aqual",
                source_cycle=it_label,
                representative_text=_cycle_text_iter(c),
                object_created=pod.get("after", "")[:200],
                cluster_id=c.get("structural_move_class"),
            ))

    # Neural
    if substrate in ("neural", "all"):
        neural_cycles = _read_query_json("gp215_cycles_neural.json")
        for c in neural_cycles:
            if "fill_error" in c:
                continue
            it_label = f"iter{c['start_iteration']}→{c['end_iteration']}"
            pod = c.get("proof_object_delta", {}) or {}
            moves.append(MetaMove(
                move_id=f"neural:{it_label}",
                move_name=c.get("structural_move_class", "?"),
                signature=c.get("resolution_move", "")[:250],
                source_substrate="neural",
                source_cycle=it_label,
                representative_text=_cycle_text_iter(c),
                object_created=pod.get("after", "")[:200],
                cluster_id=c.get("structural_move_class"),
            ))

    return moves


def _embed(text: str, api_key: str) -> list[float]:
    # Migrated to the canonical embedding engine (ztare.common.embeddings) — the
    # ONE place Gemini embeddings are created/queried. The embedding space is
    # preserved EXACTLY: model gemini-embedding-001, task_type RETRIEVAL_DOCUMENT
    # (both the stall AND every move are embedded as documents here, NOT
    # asymmetric query/document — keep it symmetric so cosine stays comparable),
    # and the model's native dimensionality (3072) since the legacy
    # genai.embed_content call passed no output_dimensionality. No atlas/cache is
    # persisted by this matcher (stall + moves are embedded fresh each call and
    # compared only against each other), so there is no stored vector to break.
    # Error contract unchanged: this never returned None — callers only reach
    # _embed when api_key is truthy, and any failure propagates (rule 3: a
    # raising contract stays raising). make_client raises SystemExit on a missing
    # key, but api_key is non-empty by construction at every call site.
    from ztare.common.embeddings import embed_batch, make_client
    return embed_batch(
        make_client(api_key),
        [text],
        model="gemini-embedding-001",
        dimensions=3072,
        task_type="RETRIEVAL_DOCUMENT",
    )[0]


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na * nb > 0 else 0.0


def _token_counts(text: str) -> dict[str, int]:
    import re
    stop = {
        "the", "and", "or", "to", "of", "a", "in", "for", "with", "by",
        "is", "it", "this", "that", "from", "as", "on", "be", "not",
    }
    counts: dict[str, int] = {}
    for tok in re.findall(r"[a-zA-Z0-9_]{3,}", text.lower()):
        if tok in stop:
            continue
        counts[tok] = counts.get(tok, 0) + 1
    return counts


def _lexical_cos(a: str, b: str) -> float:
    ca = _token_counts(a)
    cb = _token_counts(b)
    if not ca or not cb:
        return 0.0
    common = set(ca) & set(cb)
    dot = sum(ca[t] * cb[t] for t in common)
    na = math.sqrt(sum(v * v for v in ca.values()))
    nb = math.sqrt(sum(v * v for v in cb.values()))
    return dot / (na * nb) if na * nb > 0 else 0.0


def match_stall(
    stall: str,
    moves: list[MetaMove] | None = None,
    *,
    substrate: str = "all",
    top_k: int = 5,
    api_key: str | None = None,
    force_offline: bool = False,
    apply_idf: bool = True,
    saturation_modal_threshold: float = 0.60,
    saturation_lift_threshold: float = 0.05,
) -> dict[str, Any]:
    """Match a stall description against the catalog with G1–G5 panel-review
    contract clauses applied:

      G2 — saturation gate: if modal cluster covers ≥ saturation_modal_threshold
           of the catalog AND top1_cosine - mean(top10_in_modal_cluster) <
           saturation_lift_threshold, return `recommendation_null` with reason
           "saturation". No fake top-1.
      G3 — IDF correction: down-weight match by log(N / cluster_size) so the
           modal cluster doesn't always win on raw cosine.
      G4 — real adversary contract: adversary must have different
           source_substrate AND different delta_type from top match.
    """
    from collections import Counter

    api_key = None if force_offline else (
        api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    )

    if moves is None:
        moves = load_catalog(substrate)

    if api_key:
        # Embed stall + every move
        scoring_mode = "embedding"
        stall_emb = _embed(stall, api_key)
        move_embs: list[list[float]] = []
        for m in moves:
            move_embs.append(_embed(m.representative_text, api_key))
            time.sleep(0.04)
        raw_scored = [(m, _cos(stall_emb, e)) for m, e in zip(moves, move_embs)]
    else:
        scoring_mode = "offline_lexical"
        raw_scored = [(m, _lexical_cos(stall, m.representative_text)) for m in moves]

    # G3 — IDF correction. Each cluster_id's effective weight is 1/log_factor.
    cluster_counts = Counter(m.cluster_id for m in moves)
    N = len(moves)
    def idf_weight(cluster_id: str | None) -> float:
        c = cluster_counts.get(cluster_id, 1)
        return math.log(max(N / c, 1.0)) if c > 0 else 1.0

    if apply_idf:
        scored = [(m, raw_cos, raw_cos * (1.0 + idf_weight(m.cluster_id) / 4.0)) for m, raw_cos in raw_scored]
    else:
        scored = [(m, raw_cos, raw_cos) for m, raw_cos in raw_scored]
    # Sort by IDF-adjusted score
    scored.sort(key=lambda x: -x[2])

    ranked = scored[:top_k]

    # G2 — saturation gate
    saturation_flag = False
    saturation_reason = None
    modal_cluster = cluster_counts.most_common(1)[0] if cluster_counts else (None, 0)
    modal_cluster_id, modal_count = modal_cluster
    modal_share = modal_count / N if N > 0 else 0
    top1_cos = raw_scored[0][1] if raw_scored else 0.0  # raw cos for the IDF-top match
    # Compute mean cosine within modal cluster for the top-K range
    modal_in_top10 = [c for m, c, _ in scored[:10] if m.cluster_id == modal_cluster_id]
    modal_mean_cos = sum(modal_in_top10) / len(modal_in_top10) if modal_in_top10 else 0.0
    # Re-pull top1 raw cos under IDF ranking
    if scored:
        top1_idf_match = scored[0][0]
        top1_idf_cos = scored[0][1]
    else:
        top1_idf_match = None
        top1_idf_cos = 0.0
    lift = top1_idf_cos - modal_mean_cos
    if (
        modal_share >= saturation_modal_threshold
        and lift < saturation_lift_threshold
    ):
        saturation_flag = True
        saturation_reason = (
            f"modal cluster '{modal_cluster_id}' covers {modal_share:.0%} of "
            f"catalog; top1_idf_cos {top1_idf_cos:.3f} − modal_mean_in_top10 "
            f"{modal_mean_cos:.3f} = {lift:.3f} < {saturation_lift_threshold} "
            "lift threshold. Catalog cannot generate above modal baseline for "
            "this stall; emitting recommendation_null per G2."
        )

    # G4 — real adversary contract: different source_substrate AND delta_type
    if not ranked:
        adversary = None
    else:
        top_match = ranked[0][0]
        # Read delta_type from the underlying cycle data via object_created mapping;
        # but we don't have delta_type on MetaMove. Approximate via source_substrate
        # diff + cluster_id diff (the strongest available signal).
        adversary = None
        for m, raw_cos, _idf_score in scored:
            if m.cluster_id != top_match.cluster_id and m.source_substrate != top_match.source_substrate:
                adversary = (m, raw_cos)
                break
        if adversary is None:
            adversary_reason = (
                "No structurally-distinct adversary available: every alternate "
                "cluster in the catalog shares either source_substrate or cluster_id "
                "with the top match. Catalog too narrow for clause-F monoculture guard."
            )
        else:
            adversary_reason = None

    # Generate a recommendation_id and record to the ledger
    import uuid
    rec_id = f"matcher-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"
    try:
        from ztare.research_director.meta_arc_acceptance import (
            LedgerEntry,
            append_ledger,
        )
        top1 = scored[0] if scored else None
        adv_id = (adversary[0].move_id if adversary is not None else None)
        ledger_entry = LedgerEntry(
            recommendation_id=rec_id,
            timestamp_iso=datetime.now(timezone.utc).isoformat(),
            stall_text=stall[:1000],
            catalog_version=f"{len(moves)}-cycle:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            top1_move_id=top1[0].move_id if top1 else "",
            top1_cluster_id=str(top1[0].cluster_id) if top1 else "",
            top1_source_substrate=top1[0].source_substrate if top1 else "",
            top1_cosine_raw=round(top1[1], 3) if top1 else 0.0,
            adversary_move_id=adv_id,
            saturation_flag=saturation_flag,
            modal_share=round(modal_share, 3),
        )
        append_ledger(ledger_entry)
    except Exception as exc:
        print(f"[ledger] append failed (non-fatal): {exc}")

    return {
        "recommendation_id": rec_id,
        "stall": stall,
        "n_catalog": len(moves),
        "scoring_mode": scoring_mode,
        "saturation_flag": saturation_flag,
        "saturation_reason": saturation_reason,
        "modal_cluster": modal_cluster_id,
        "modal_share": round(modal_share, 3),
        "lift": round(lift, 3),
        "ranked": [
            {
                "rank": i + 1,
                "move_id": m.move_id,
                "move_name": m.move_name,
                "signature": m.signature,
                "source_substrate": m.source_substrate,
                "source_cycle": m.source_cycle,
                "object_created": m.object_created,
                "cluster_id": m.cluster_id,
                "cosine_raw": round(raw_cos, 3),       # G1: kept in JSON, NOT in markdown
                "cosine_idf_adjusted": round(idf_score, 3),
            }
            for i, (m, raw_cos, idf_score) in enumerate(ranked)
        ],
        "adversary_move": (
            {
                "move_id": adversary[0].move_id,
                "move_name": adversary[0].move_name,
                "signature": adversary[0].signature,
                "source_substrate": adversary[0].source_substrate,
                "source_cycle": adversary[0].source_cycle,
                "object_created": adversary[0].object_created,
                "cluster_id": adversary[0].cluster_id,
                "cosine_raw": round(adversary[1], 3),
                "purpose": "G4 adversary: structurally-distinct alternative — different source_substrate AND different cluster from top match. Panel clause F monoculture guard.",
            }
            if adversary is not None
            else {"reason": adversary_reason}
        ),
        "theory_building_op_advisory": _annotate_theory_building_op(scored[:3] if scored else []),
    }


def _annotate_theory_building_op(top_scored: list) -> dict[str, Any]:
    """GP-216 advisory annotation: name the most-likely theory-building op the
    top match instantiates. ADVISORY ONLY — does not gate, does not bind, does
    not modify the recommendation. Per panel discipline, vocabulary v3 is
    DESCRIPTIVE not GENERATIVE; surface as a label for operator awareness only.

    Heuristic: from Pass 8 mining, ZTARE cycles cluster predominantly on tb_06
    (formalize tacit pattern → 4/40 cycles), tb_04 (constraint narrowing → 2/40),
    tb_NEW_POLYA (strategic specialization → 1/40). Map by keyword presence in
    the move's representative_text. Conservative: return "no_clear_label" if
    no keyword fires.
    """
    if not top_scored:
        return {"label": "no_clear_label", "reason": "empty top match"}
    top_move = top_scored[0][0]
    text = (top_move.representative_text or "").lower()
    label = "no_clear_label"
    reason = ""
    # Heuristic patterns derived from Pass 8 cycles that were tagged
    if any(k in text for k in ["lean obligation", "lean theorem", "gate", "predicate", "named", "typed"]):
        label = "tb_06"
        reason = "move installs/names a typed Lean predicate or gate (tacit-pattern formalization)"
    elif any(k in text for k in ["four-charge", "constraint", "must satisfy", "simultaneously", "all of"]):
        label = "tb_04"
        reason = "move accumulates a constraint stack that progressively narrows admissible solutions"
    elif any(k in text for k in ["special case", "killing-mode", "semistable", "barrier", "branch"]):
        label = "tb_NEW_POLYA"
        reason = "move solves a load-bearing special case selected to break a structural barrier"
    return {
        "label": label,
        "reason": reason,
        "vocabulary_ref": "src/ztare/research_director/theory_building_ops.py — VOCABULARY_V3",
        "advisory_only": True,
        "note": "GP-216 vocabulary v3 is descriptive, not generative; ~58% held-out coverage; this label is operator-awareness, not a directive",
    }


def render_markdown(result: dict[str, Any]) -> str:
    """G1 — operator-facing markdown uses ordinal rank only, no cosine.

    Also surfaces the scope-limit disclosure and current lift score per
    GP-215 acceptance-discipline (see meta_arc_acceptance.py)."""
    lines: list[str] = []
    rec_id = result.get("recommendation_id", "(unrecorded)")
    lines.append(f"# Meta-arc matcher recommendation\n")
    lines.append(f"_Recommendation id: `{rec_id}` — record action with `python -m ztare.research_director.meta_arc_acceptance record --recommendation-id {rec_id} --action accepted|rejected|modified|ignored`._\n")
    lines.append(f"**Stall:** {result['stall']}\n")
    lines.append(f"_Catalog: {result['n_catalog']} moves across NS / AQUAL / Neural. Scoring mode: `{result.get('scoring_mode', 'unknown')}`. Modal cluster `{result.get('modal_cluster','?')}` covers {int(result.get('modal_share',0)*100)}% of catalog._\n")

    # G2 — saturation gate: when fired, refuse to recommend
    if result.get("saturation_flag"):
        lines.append("## ⚠ Recommendation withheld — catalog saturated for this stall\n")
        lines.append(result.get("saturation_reason", ""))
        lines.append("")
        lines.append("**This is not a failure. It is the matcher's correct refusal to fake authority.** The closed-arc catalog says the move-class your stall most resembles is the dominant move-class — i.e., the work the substrate has already done many times. The next valuable move is structurally rare in the catalog and therefore cannot be retrieved by similarity matching.\n")
        lines.append("**What to do:** look at the structurally-rare cluster members below as a SEED for a new direction (not as a recommendation). If your stall describes a current obligation that has already been named in Lean, the residual is the PDE estimate / falsifier / partition that fills the obligation — a move with no in-distribution exemplar in the catalog.\n")
        lines.append("## Structurally-rare cluster seeds (for inspiration only)\n")
        # Show only matches NOT in the modal cluster
        modal_id = result.get("modal_cluster")
        rare = [r for r in result["ranked"] if r.get("cluster_id") != modal_id]
        if rare:
            lines.append("| Rank | Source | Move | Object created |")
            lines.append("|---:|---|---|---|")
            for r in rare[:5]:
                lines.append(f"| top-{r['rank']} | `{r['source_substrate']}/{r['source_cycle']}` | **{r['move_name']}** | {r['object_created'][:80]} |")
        else:
            lines.append("_No non-modal-cluster matches in top-K. Catalog is too narrow to surface alternatives._")
        lines.append("")
    else:
        lines.append("## Top matches (ordinal rank; cosine omitted per panel clause G1)\n")
        lines.append("| Rank | Source | Move | Object created |")
        lines.append("|---:|---|---|---|")
        for r in result["ranked"]:
            obj = r["object_created"][:80]
            lines.append(f"| top-{r['rank']} | `{r['source_substrate']}/{r['source_cycle']}` | **{r['move_name']}** | {obj} |")
        lines.append("")

    # G4 — adversary
    adv = result.get("adversary_move") or {}
    if "move_id" in adv:
        lines.append("## Adversary move (panel clause G4 — different source_substrate AND cluster)\n")
        lines.append(f"_Forced contrast option. The matcher's top recommendation rotates within whatever cluster dominates the catalog; this entry comes from a structurally-distinct corner._\n")
        lines.append(f"- **{adv['move_name']}** (`{adv['source_substrate']}/{adv['source_cycle']}`)")
        lines.append(f"  - Object: {adv['object_created']}")
        lines.append(f"  - Signature: {adv['signature']}")
    else:
        lines.append("## ⚠ No structurally-distinct adversary available\n")
        lines.append(adv.get("reason", "Catalog too narrow for clause-G4 monoculture guard."))
    lines.append("")

    lines.append("---")
    lines.append("")

    # Lift score + scope-limit (GP-215 acceptance discipline)
    try:
        from ztare.research_director.meta_arc_acceptance import (
            compute_lift_score,
            current_scope_limit,
        )
        score = compute_lift_score()
        lines.append("## Calibration: how confident should you be in this recommendation?\n")
        if score.get("n_actioned", 0) == 0:
            lines.append(f"_{score.get('notes','')}_\n")
        else:
            mb = score.get("modal_baseline_estimate")
            mb_str = f"{mb:.0%}" if mb is not None else "n/a"
            lift = score.get("lift_estimate")
            lift_str = f"{lift:+.0%}" if lift is not None else "n/a"
            lines.append(
                f"- Operator accept rate so far: **{score['matcher_top1_accept_rate']:.0%}** "
                f"(n={score['n_actioned']} actioned of {score['n_entries']} issued)"
            )
            lines.append(f"- Modal-baseline estimate: **{mb_str}**")
            lines.append(f"- **Lift over modal:** {lift_str}")
            lines.append(f"- Saturation refusals (matcher correctly stayed silent): {score.get('n_saturation_correctly_refused', 0)}")
            lines.append("")
            lines.append(f"_{score.get('notes','')}_\n")
        lines.append(current_scope_limit())
    except Exception as exc:
        lines.append(f"_(scope-limit module unavailable: {exc})_")
    lines.append("")
    lines.append("\n_Generated by `ztare.research_director.meta_arc_matcher`. Advisory-only: this recommendation annotates BRIDGE-1 rationale; the substrate's `predicted_class` (operator-supplied) wins for routing._")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ztare.research_director.meta_arc_matcher")
    p.add_argument("--stall", required=True, help="Free-form stall description")
    p.add_argument("--substrate", default="all", choices=["ns", "aqual", "neural", "all"])
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--out", type=Path, default=DEFAULT_INBOX)
    p.add_argument("--print-only", action="store_true")
    p.add_argument("--offline", action="store_true",
                   help="force local lexical scoring even when an embedding API key is present")
    args = p.parse_args(argv)

    moves = load_catalog(args.substrate)
    result = match_stall(
        args.stall, moves=moves, top_k=args.top_k, force_offline=args.offline)
    md = render_markdown(result)

    if args.print_only:
        print(md)
        return 0

    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    args.out.mkdir(parents=True, exist_ok=True)
    out_path = args.out / f"{ts}_match.md"
    out_path.write_text(md)
    json_path = args.out / f"{ts}_match.json"
    json_path.write_text(json.dumps(result, indent=2))
    print(f"wrote {out_path}")
    print(f"wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
