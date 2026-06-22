"""Semantic MOVE ATLAS — the ONE agent-facing move menu, semantically RANKED for the current goal.

Embeds the unified `move_corpus` (tools + structural + technique + math-research moves) via the SHARED
`common.embeddings` builder and, at solve time, retrieves the most goal-relevant moves so the agent sees the
right moves FIRST. The atlas DRIVES the move ORDERING — it is not advisory decoration (operator 2026-06-20:
"shouldn't be advisory only if it's more powerful"). The Goldilocks split: move ORDERING is upstream agency,
so the better signal (semantic recall) owns it; the governed scheduler still applies the hard gates (backend
liveness / cost / calibration floor) and the KERNEL ratifies every closure — soundness never moves. A move
surfaced wrongly just gets tried first and fails honestly through the same gates.

Degrades to the static `move_cards` tool block when the embedder is down / the atlas is unbuilt — so there is
no regression and never a second surface to forget. A/B baseline arm: `ZTARE_LEANMILL_MOVE_ATLAS=0` (static
fixed order). Build the atlas once (content-hash cached): `python -m ztare.leanmill.solver.move_atlas --build`.
Consumed by BOTH the solver leaf (`agentic_leaf._leaf_prompt`) and the planner (`isomorphism_decompose`).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
ATLAS_PATH = _REPO / "analytics" / "public" / "index" / "leanmill_move_atlas.json"
MANIFEST_PATH = _REPO / "analytics" / "public" / "index" / "leanmill_move_atlas.manifest.json"
_PROV_LOG = _REPO / "analytics" / "public" / "queries" / "move_atlas_provenance.jsonl"

_KIND_LABEL = {"tool": "TOOL", "structural": "MOVE", "technique": "TECHNIQUE", "research_op": "RESEARCH-MOVE"}
_STATIC_ORDER = {"tool": 0, "structural": 1, "technique": 2, "research_op": 3}


def is_enabled() -> bool:
    """Default-ON (the semantic ordering is the stronger signal; sound — it only re-orders an advisory menu).
    `ZTARE_LEANMILL_MOVE_ATLAS=0` reverts to the static fixed order (the A/B baseline arm)."""
    return os.environ.get("ZTARE_LEANMILL_MOVE_ATLAS", "1") != "0"


def _atlas_nonempty() -> bool:
    try:
        return ATLAS_PATH.exists() and ATLAS_PATH.stat().st_size > 2
    except Exception:  # noqa: BLE001
        return False


def build(*, rebuild: bool = False, model: "str | None" = None) -> dict:
    """Build/refresh the atlas from the unified corpus (CLI `--build`). Content-hash cached by
    `common.embeddings.build_atlas`, so re-running only embeds new/changed moves."""
    from ztare.common import embeddings as _emb
    from ztare.leanmill.solver.move_corpus import atlas_entries
    kw: dict = {"rebuild": rebuild}
    if model:
        kw["model"] = model
    return _emb.build_atlas(atlas_entries(), ATLAS_PATH, MANIFEST_PATH, **kw)


_RANK_CACHE: dict = {}   # per-process memo: the ranking is deterministic per (goal, k, kinds) and the atlas is
#                          static within a run, so a goal re-attacked across rounds/leaf+planner embeds ONCE
#                          (the embedding API call is the hot cost on a multi-hundred-node P1 run).


import re as _re   # channel-2 structural triggers: symbolic matches on the goal's logical FORM
#
# DUAL-CHANNEL (HYBRID) MOVE RECALL. Channel 1 = dense embedding (goal-text ↔ card-text cosine, `rank()` above).
# Channel 2 = structural triggers: deterministic symbolic matches on the goal's LOGICAL FORM, fused with the
# dense ranking. The motivation is the classic IR vocabulary-mismatch / lexical-gap failure: a formal Lean goal
# (`∃ x : <built type>, …`, a self-reference impossibility) shares almost no surface tokens with a strategy
# card's English prose, so a SHAPE-keyed move is effectively unretrievable by cosine alone (2026-06-21 RCA — the
# witness move never surfaced for abstract ∃ goals; the consciousness Čech target gapped on exactly this). The
# standard cure is hybrid dense+sparse/structural retrieval; here the structural channel GUARANTEES a shape-keyed
# move reaches the menu. Adding a strategy move keyed on goal-shape = ONE `(matcher, move_id)` line below — no
# per-move plumbing. A/B-gated (`ZTARE_LEANMILL_STRUCT_TRIGGER=0`, back-compat `ZTARE_LEANMILL_WITNESS_TRIGGER`)
# so the closure LIFT is measurable against the research's prior null on the *text* channel (this is the untested
# *structural* channel; `move_engagement.jsonl` accrues the verdict). Agency-preserving (Goldilocks): a trigger
# ADDS a menu option (injected just after the top dense hit), never forces a move — the agent still chooses.


def _shape_abstract_existence(goal_text: "str | None") -> bool:
    """Trigger → `instances_first` (reduce-to-minimal-witness). Fires on an ABSTRACT EXISTENCE/IFF over an
    arbitrary/constructed carrier (`∃` or `↔` with a `Type*`/`Sort` carrier) — where 'exhibit the smallest
    concrete witness' is the move. Conservative: the abstractness marker is REQUIRED, so it does NOT fire on a
    concrete numeric `∃ n : ℕ, …`."""
    g = goal_text or ""
    if not g.strip() or (("∃" not in g) and ("↔" not in g)):
        return False
    return bool(_re.search(r"Type\s*\*|Type\s+[uvw]\b|\bSort\b", g))


def _shape_self_reference(goal_text: "str | None") -> bool:
    """Trigger → `op_spec_02` (Internalization / Self-Reference / Diagonal — the Gödel-Lawvere-Cantor move; the
    R2 / general-criterion tier: necessity of self-opacity). Fires on a LIMITATIVE / impossibility claim about a
    system encoding or applying ITSELF: a negated surjection/injection of a self-map into its own power/function
    space (`¬ Surjective (… : α → (α → …))`, `α → Set α`), a negated faithful self-encoding
    (`¬ ∃ … (encode|faithful|represent)`), or explicit diagonal/fixed-point vocabulary. Conservative: outside the
    explicit-vocabulary case it REQUIRES an impossibility marker, so it does not fire on ordinary surjectivity."""
    g = goal_text or ""
    if not g.strip():
        return False
    if _re.search(r"\b(Cantor|[Dd]iagonal|fixedPoint|fixed_point|Lawvere|G[öo]del|Tarski|halting|incomplete\w*)\b", g):
        return True
    neg = ("¬" in g) or ("Not " in g) or ("→ False" in g) or ("≠" in g)
    if not neg:
        return False
    selfmap = bool(_re.search(r"(\w+)\s*→\s*\(\s*\1\s*→|(\w+)\s*→\s*Set\s+\2\b|→\s*\(\s*\w+\s*→\s*(Prop|Bool)\s*\)", g))
    if ("Surjective" in g or "Injective" in g) and (selfmap or "Set " in g):
        return True
    return bool(_re.search(r"(encode|encoding|faithful|represent\w*|self[-_ ]?model|self[-_ ]?refer)", g, _re.I))


# CHANNEL-2 registry — (goal-shape matcher, move_id to GUARANTEE-surface). Extend = append one line.
_STRUCTURAL_TRIGGERS = [
    (_shape_abstract_existence, "instances_first"),   # abstract ∃/iff over a built carrier → reduce to witness
    (_shape_self_reference,     "op_spec_02"),         # self-encoding impossibility / fixed-point → diagonal move
]
_witness_goal_shape = _shape_abstract_existence        # back-compat alias (earlier callers / tests)


def _move_meta(move_id: str) -> "dict | None":
    """Surfaced-meta for ANY move, built from the ONE corpus (never re-authored here)."""
    try:
        from ztare.leanmill.solver.move_corpus import build_corpus
        for e in build_corpus():
            if e.move_id == move_id:
                return {"score": None, "id": e.move_id, "name": e.name, "kind": e.kind,
                        "when": e.when, "avoid": e.avoid, "cli": e.cli, "source": e.source}
    except Exception:  # noqa: BLE001
        pass
    return None


def _struct_trigger_enabled() -> bool:
    return os.environ.get("ZTARE_LEANMILL_STRUCT_TRIGGER",
                          os.environ.get("ZTARE_LEANMILL_WITNESS_TRIGGER", "1")) != "0"


def _fuse_structural_triggers(metas: list, source: str, goal_text: "str | None", k: int,
                              kinds: "set | None") -> "tuple[list, str]":
    """Hybrid fusion: for EACH structural trigger whose goal-shape matcher fires, guarantee its move is on the
    menu (injected just after the top dense hit, deduped, trimmed to k) — respecting the caller's `kinds` filter
    via each move's real kind. A/B-gated; agency-preserving (adds options, never forces)."""
    if not _struct_trigger_enabled():
        return metas, source
    fired: list = []
    for matcher, mid in _STRUCTURAL_TRIGGERS:
        try:
            if not matcher(goal_text):
                continue
        except Exception:  # noqa: BLE001
            continue
        if any(m.get("id") == mid for m in metas) or any(m.get("id") == mid for m in fired):
            continue
        meta = _move_meta(mid)
        if meta is None or (kinds is not None and meta.get("kind") not in kinds):
            continue
        fired.append(meta)
    if not fired:
        return metas, source
    fused, seen = [], set()
    for m in (metas[:1] + fired + metas[1:]):
        mid = m.get("id")
        if mid in seen:
            continue
        seen.add(mid)
        fused.append(m)
    return fused[:k], (source + "+struct_trigger")


_fuse_witness_trigger = _fuse_structural_triggers   # back-compat alias (rank() + earlier callers)


def rank(goal_text: str, k: int = 12, kinds: "set | None" = None) -> "tuple[list, str]":
    """(ordered move metas, source). source ∈ {"atlas","static"}. ATLAS path queries the embedded corpus for
    goal relevance (DRIVES the order); cached per process. STATIC path returns the corpus in a fixed kind order
    (tool → structural → technique → research_op) when the flag is off / atlas unbuilt / embedder down —
    graceful, no crash. `kinds` (e.g. {"technique","research_op","structural"}) restricts to a subset (the
    planner wants the research moves, not the exogenous tool CLIs)."""
    ck = ((goal_text or "")[:512], k, tuple(sorted(kinds)) if kinds else None, is_enabled())
    hit = _RANK_CACHE.get(ck)
    if hit is not None:
        return hit
    out = None
    if is_enabled() and (goal_text or "").strip() and _atlas_nonempty():
        try:
            from ztare.common.embeddings import query_atlas
            # over-fetch when filtering so the top-k AFTER the kind filter is still full
            hits = query_atlas(ATLAS_PATH, goal_text, k=(k * 3 if kinds else k))
            if kinds:
                hits = [h for h in hits if h.get("kind") in kinds]
            if hits:
                out = (hits[:k], "atlas")
        except Exception:  # noqa: BLE001 — embedder down / no key / quota ⇒ fall through to static (NOT cached: a transient embedder outage shouldn't pin us to static for the whole run)
            out = None
    if out is None:
        from ztare.leanmill.solver.move_corpus import build_corpus
        items = [e for e in build_corpus() if (kinds is None or e.kind in kinds)]
        items = sorted(items, key=lambda e: _STATIC_ORDER.get(e.kind, 9))
        metas = [{"score": None, "id": e.move_id, "name": e.name, "kind": e.kind, "when": e.when,
                  "avoid": e.avoid, "cli": e.cli, "source": e.source} for e in items[:k]]
        return _fuse_witness_trigger(metas, "static", goal_text, k, kinds)   # NOT cached — retry atlas next time
    out = _fuse_witness_trigger(out[0], out[1], goal_text, k, kinds)   # channel-2 hybrid fusion (post-dense)
    if len(_RANK_CACHE) > 1024:   # soft bound (distinct goals ≈ node count; clear rather than grow unbounded)
        _RANK_CACHE.clear()
    _RANK_CACHE[ck] = out
    return out


_ENG_LOG = _REPO / "analytics" / "public" / "queries" / "move_engagement.jsonl"


def engaged_rank(goal_text: str, move_id: str, k: int = 12, kinds: "set | None" = None) -> dict:
    """Given a goal and a move the agent ENGAGED, return its position in the SURFACED ranking the agent saw
    (1-based `rank`, `score`, `surfaced`=was it in the top-k menu, `source`). Reuses the cached `rank()` (same
    k the leaf used ⇒ cache hit, ~free). This is the JOIN that gap #1 was missing: surfaced (provenance) ×
    engaged (here) ⇒ 'the agent used a move the atlas ranked #k'."""
    try:
        metas, source = rank(goal_text or "", k=k, kinds=kinds)
        for i, m in enumerate(metas):
            if move_id in (m.get("id"), m.get("name")):
                return {"rank": i + 1, "score": m.get("score"), "surfaced": True, "source": source}
        return {"rank": None, "score": None, "surfaced": False, "source": source}
    except Exception:  # noqa: BLE001
        return {"rank": None, "score": None, "surfaced": False, "source": "error"}


def log_engagement(goal_text: "str | None", engaged: str, *, outcome: str = "", via: str = "governed_move",
                   k: int = 12, kinds: "set | None" = None) -> None:
    """Append a JOINED engagement row {goal, engaged move, its atlas rank/score, surfaced?, outcome, via} to
    `move_engagement.jsonl`. `via`: governed_move (the DAG move runner) / tool (an exogenous tool call) /
    declared (the agent self-reported a technique). Best-effort telemetry — never raises, never gates."""
    try:
        er = engaged_rank(goal_text or "", engaged, k=k, kinds=kinds)
        row = {"goal": (goal_text or "")[:160], "engaged": engaged, "via": via, "outcome": outcome,
               "atlas_rank": er["rank"], "atlas_score": er["score"], "surfaced": er["surfaced"],
               "source": er["source"]}
        _ENG_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _ENG_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass


def _log_provenance(goal_text: "str | None", metas: list, source: str) -> None:
    """Best-effort advisory telemetry: which moves were surfaced for a goal + their scores + the source
    (atlas vs static) — feeds the A/B 'does atlas-ordering lift closure?' measurement. Never breaks the solve."""
    try:
        _PROV_LOG.parent.mkdir(parents=True, exist_ok=True)
        row = {"goal": (goal_text or "")[:160], "source": source,
               "ranked": [{"id": m.get("id"), "kind": m.get("kind"), "score": m.get("score")} for m in metas]}
        with _PROV_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass


def render_for_goal(goal_text: "str | None" = None, k: int = 12, db_path=None,
                    kinds: "set | None" = None, with_preamble: bool = True, header: "str | None" = None) -> str:
    """The agent-facing move menu, goal-RANKED. Reuses the shared `move_cards` preamble + per-move calibration
    receipts + dead-backend liveness filter (a tool whose backend is down is dropped). `kinds` restricts to a
    subset; `with_preamble=False` + `header` is the lighter PLANNER form (no tool-autonomy preamble — the
    planner has its own framing). Empty when the master tool flag is off (parity with `render_tool_block`)."""
    if os.environ.get("ZTARE_LEANMILL_AGENT_TOOLS", "1") == "0":   # same master gate as the static tool block
        return ""
    metas, source = rank(goal_text or "", k=k, kinds=kinds)
    from ztare.leanmill.solver import move_cards as _mc
    tele = _mc._telemetry(db_path)
    live = []
    for m in metas:
        if m.get("kind") == "tool":
            try:
                if not _mc._tool_backend_live(m.get("name", "")):
                    continue   # don't advertise a dead tool backend (operator foot-gun)
            except Exception:  # noqa: BLE001
                pass
        live.append(m)
    _log_provenance(goal_text, live, source)
    lines = _mc.menu_preamble_lines() if with_preamble else ([header] if header else [])
    if source == "atlas":
        lines.append("(Ranked for your specific goal by semantic recall — most relevant first. Pick what fits; "
                     "the kernel verifies every closure regardless of order.)")
    for m in live:
        label = _KIND_LABEL.get(m.get("kind"), "MOVE")
        name = m.get("name", "?")
        # The cached atlas stores the PORTABLE cli (machine-independent artifact); re-absolutize it here so the
        # agent (cwd = the lake project) can actually run it. Idempotent on the static-path's already-abs cli.
        cli = _mc.absolutize_cli(m.get("cli") or "")
        head = f"\n• {label} `{name}`" + (f" — run: {cli}" if cli else "")
        lines.append(head)
        if m.get("when"):
            lines.append(f"   WHEN: {m['when']}")
        if m.get("avoid"):
            lines.append(f"   NOT: {m['avoid']}")
        ev = _mc._evidence_for(m.get("id"), tele)
        if ev and not ev.startswith("new tool"):   # suppress the generic 'no receipts yet' filler (noise on techniques/research moves)
            lines.append(f"   track record: {ev}")
    # RECEIPT-A-PRIORI (gap #2, NS-RD `pattern_action_contract` lineage: "checked class + receipt beat
    # free-form synthesis", H32–H42). A TECHNIQUE/RESEARCH-MOVE has no exogenous tool-check (sos/nlsat/… do),
    # so the receipt IS the agent stating the move's PRECONDITION for THIS goal BEFORE building — the a-priori
    # check that it matched the right move (and the "plan-before-work helps the agent think" lever). The kernel
    # still verifies the proof; this only sharpens + audits the move choice. Default-on; =0 reverts (A/B).
    if (any(m.get("kind") in ("technique", "research_op", "structural") for m in live)
            and os.environ.get("ZTARE_LEANMILL_MOVE_RECEIPTS", "1") != "0"):
        lines.append(
            "\nRECEIPT (state BEFORE you build on a TECHNIQUE / RESEARCH-MOVE / structural MOVE above): on its own "
            "line write `RECEIPT: <move name> — <the concrete structural feature of THIS goal that licenses it>` "
            "(instantiate the move's precondition for your goal: e.g. for `finite Hankel rank ⇒ rational`, exhibit "
            "the finite-rank Hankel/recurrence; for `obstruction-descent`, name the obstruction class + why the "
            "boundedness hypothesis forces it to vanish). Stating the precondition first is the a-priori check "
            "that you picked the RIGHT move — if you can't name a concrete precondition, the move does NOT fit, "
            "pick another. The kernel still verifies the proof regardless.")
    lines.append("")
    return "\n".join(lines)


def render_research_moves_for_goal(goal_text: "str | None" = None, k: int = 8, db_path=None) -> str:
    """The PLANNER form — the goal-ranked RESEARCH moves (structural + transportable technique + math
    research-op), WITHOUT the exogenous-tool CLIs (those are for the executing leaf). The 'lever deeper' the
    planner reasons with: the named mathematician moves + transport attacks, surfaced from the SAME corpus the
    leaf sees, ranked for this goal. Domain-general content ⇒ respects the deanchor no-leak rule (same as the
    pre-existing transportable-technique prior). '' when the master flag is off."""
    return render_for_goal(goal_text, k=k, db_path=db_path,
                           kinds={"structural", "technique", "research_op"}, with_preamble=False,
                           header="RESEARCH MOVES you can build the plan around (named mathematician moves + "
                                  "transport attacks; the kernel audits whatever DAG you produce):")


def _selftest() -> int:
    fails = []
    os.environ["ZTARE_LEANMILL_AGENT_TOOLS"] = "1"
    # STATIC path (no atlas built in CI / embedder not probed): rank must degrade, never crash
    metas, source = rank("theorem t (f : RatFunc K) : simpleResidueCoeff c = 0 := by sorry", k=12)
    if source != "static":
        # atlas may exist locally; both are acceptable, but it must be one of the two
        if source != "atlas":
            fails.append(f"unexpected source {source!r}")
    if not metas:
        fails.append("rank returned no moves")
    kinds = {m.get("kind") for m in metas}
    if "tool" not in kinds:
        fails.append(f"no tool move surfaced in top-k: {kinds}")
    blk = render_for_goal("theorem t : 1 + 1 = 2 := by sorry", k=12)
    for tok in ("AUTONOMOUS", "WHEN:"):
        if tok not in blk:
            fails.append(f"render missing {tok!r}")
    # A/B baseline: flag off ⇒ static order regardless of any atlas
    os.environ["ZTARE_LEANMILL_MOVE_ATLAS"] = "0"
    _, src0 = rank("anything", k=5)
    if src0 != "static":
        fails.append("flag=0 must force the static order (A/B baseline)")
    os.environ.pop("ZTARE_LEANMILL_MOVE_ATLAS", None)
    # master tool flag off ⇒ empty (parity with render_tool_block)
    os.environ["ZTARE_LEANMILL_AGENT_TOOLS"] = "0"
    if render_for_goal("x") != "":
        fails.append("AGENT_TOOLS=0 must render empty")
    os.environ.pop("ZTARE_LEANMILL_AGENT_TOOLS", None)
    # BEHAVIORAL (beyond-unit): the ranking must DISCRIMINATE by goal. Gated on the atlas being LIVE so the
    # suite stays hermetic — when the embedder is down / atlas unbuilt this SKIPS (per the sledgehammer-live
    # lesson: a default-on capability gating on a live service must not make a hermetic test pass/fail by box).
    _RANK_CACHE.clear()
    pell, src_p = rank("theorem pell : exists x y : Nat, x*x - 61*y*y = 1 := by sorry", k=8)
    if src_p == "atlas":
        behavioral = 0
        names_p = [m["name"] for m in pell]
        if "witness" not in names_p[:3]:
            fails.append(f"BEHAVIORAL: Pell existential should rank `witness` top-3, got {names_p[:3]}")
        poly, _ = rank("theorem nn (x : Real) : 0 <= x^4 - 2*x^2 + 1 := by sorry", k=8)
        names_q = [m["name"] for m in poly]
        if "sos" not in names_q[:3]:
            fails.append(f"BEHAVIORAL: poly-nonneg should rank `sos` top-3, got {names_q[:3]}")
        behavioral = "ran"
    else:
        behavioral = "SKIPPED (atlas not live — hermetic)"
    # ENGAGEMENT JOIN (gap #1): engaged_rank finds a surfaced move's position in the menu the agent saw.
    er = engaged_rank("theorem t : exists x y : Nat, x*x - 61*y*y = 1 := by sorry", "witness_transport", k=12)
    for key in ("rank", "score", "surfaced", "source"):
        if key not in er:
            fails.append(f"engaged_rank missing key {key}")
    if er.get("source") == "atlas" and not er.get("surfaced"):
        fails.append(f"engaged_rank: witness_transport should be surfaced for a Pell goal, got {er}")
    en = engaged_rank("theorem t : True := by sorry", "definitely_not_a_move_xyz", k=12)
    if en.get("surfaced") is not False:
        fails.append("engaged_rank: a non-move must report surfaced=False")
    print(f"move_atlas self-test {'PASS' if not fails else 'FAIL ' + str(fails)} "
          f"(source={source}, {len(metas)} ranked, kinds={sorted(kinds)}; behavioral={behavioral})")
    return 1 if fails else 0


def _main(argv) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="LeanMill semantic move atlas")
    ap.add_argument("--build", action="store_true", help="build/refresh the atlas from move_corpus")
    ap.add_argument("--rebuild", action="store_true", help="force re-embed every move (ignore cache)")
    ap.add_argument("--query", type=str, default="", help="rank the corpus for a goal and print the top-k")
    ap.add_argument("--k", type=int, default=12)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.build or a.rebuild:
        at = build(rebuild=a.rebuild)
        print(f"[move_atlas] built {ATLAS_PATH} — {at.get('size')} moves, model={at.get('model')}")
        return 0
    if a.query:
        metas, source = rank(a.query, k=a.k)
        print(f"[move_atlas] source={source}")
        for m in metas:
            print(f"  {m.get('score')}  {m.get('kind'):11s} {m.get('name')}")
        return 0
    return _selftest()


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
