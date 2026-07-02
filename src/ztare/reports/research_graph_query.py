"""No-LLM natural-language query over the source-claim graph (the SPO triples from research_graph.py).

Answers questions a researcher actually asks of the map — "what could falsify the thesis", "what supports
S002", "what rests on the claim about pricing", "what are the open tensions" — by mapping the question's
keywords to the graph's relation vocabulary + an anchor node, then traversing edges. Fully deterministic,
zero model cost. CLI is master; the workbench Ask box just renders the answer.

Graph shape (from research_graph.build_research_graph):
  nodes: [{id, type, label, detail, status, weight}]  types: thesis|claim|evidence|candidate|tension|gap|
                                                              constraint|branch|falsifier|rejected
  edges: [{from, to, relation}]  relations: SUPPORTS|DERIVES|CHALLENGES|CONTRADICTS|CONSTRAINS|TESTS|
                                            FALSIFIES|RULED_OUT
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

# Question keyword → graph relation(s). Ordered so the most specific intent wins (falsify before the
# broader "challenge/weaken"). A question may map to several relations (they're OR-ed in the traversal).
_RELATION_KEYWORDS: list[tuple[str, list[str]]] = [
    ("FALSIFIES", ["falsif", "disprove", "refute", "would kill", "break the thesis", "sink", "overturn"]),
    ("RULED_OUT", ["ruled out", "rejected", "set aside", "dismissed", "considered and", "alternativ"]),
    ("CONTRADICTS", ["contradic", "conflict", "inconsisten"]),
    ("CHALLENGES", ["challeng", "tension", "undercut", "threaten", "weaken", "push back", "cut against", "argue against"]),
    ("SUPPORTS", ["support", "backs ", "back it", "backed by", "evidence for", "holds up", "in favou", "in favor", "props up", "vouch"]),
    ("DERIVES", ["rest on", "rests on", "depend", "rely", "relies", "build on", "built on", "derive", "follow from", "hinge", "lean on"]),
    ("TESTS", ["test", "discriminat", "would settle", "distinguish", "probe", "check whether", "decide between", "pin down"]),
    ("CONSTRAINS", ["constrain", "limit", "bound ", "bounds", "restrict", "governs", "rule out the"]),
]

# node-type → keywords, for "what are the X" style questions carrying no relation/anchor.
_TYPE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("falsifier", ["falsifier", "falsification test"]),
    ("evidence", ["evidence", "sources", "the facts", "data"]),
    ("candidate", ["candidate", "claims to test", "untested claim"]),
    ("tension", ["tension", "contradiction", "conflict"]),
    ("gap", ["gap", "unknown", "void", "missing", "blind spot"]),
    ("constraint", ["constraint", "the rules", "boundaries", "established rule"]),
    ("branch", ["branch", "discriminator", "next test", "what to test"]),
    ("rejected", ["rejected", "ruled out", "alternative", "non-claim", "non claim"]),
    ("claim", ["sub-claim", "sub claim", "the claims", "reasoning spine"]),
]

_STOP = {"what", "which", "would", "could", "does", "the", "this", "that", "thesis", "claim", "about",
         "and", "for", "with", "from", "into", "over", "most", "are", "our", "have", "how", "why"}


def _norm(text: Any) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", str(text or "").lower()).strip()


def _node_view(nodes: dict[str, dict], node_id: str, relation: str = "") -> dict[str, Any]:
    n = nodes.get(node_id, {})
    return {
        "id": node_id,
        "type": n.get("type"),
        "label": n.get("label"),
        "detail": n.get("detail"),
        "status": n.get("status"),
        "relation": relation,
    }


def query_graph(carrier: dict[str, Any], question: str) -> dict[str, Any]:
    """Interpret `question` against the graph and return the matching nodes with how they were reached.

    Resolution order: (1) relation keywords → relations; (2) an anchor node (explicit id token, else a
    label overlap, else the thesis); (3) a bare node-type intent ("what are the falsifiers"). Traversal
    returns edges of the chosen relation(s) incident to the anchor; with no relation, the anchor's whole
    neighbourhood; with a type intent and no anchor, all nodes of that type."""
    nodes = {str(n.get("id")): n for n in (carrier.get("nodes") or []) if isinstance(n, dict) and n.get("id")}
    edges = [e for e in (carrier.get("edges") or []) if isinstance(e, dict)]
    q = _norm(question)

    relations = [rel for rel, kws in _RELATION_KEYWORDS if any(k in q for k in kws)]

    # Anchor: an explicit id token (S002, a claim id), else best label overlap, else the thesis.
    anchor_id: str | None = None
    token_match = re.search(r"\b([a-z]?\d{2,}[a-z0-9]*)\b", q)
    if token_match:
        token = token_match.group(1)
        for nid, n in nodes.items():
            if token in _norm(nid) or token in _norm(n.get("label")):
                anchor_id = nid
                break
    if anchor_id is None:
        qwords = {w for w in q.split() if len(w) > 3 and w not in _STOP}
        best_id, best_score = None, 0
        for nid, n in nodes.items():
            if n.get("type") == "thesis":
                continue
            overlap = len(qwords & set(_norm(n.get("label")).split()))
            if overlap > best_score:
                best_id, best_score = nid, overlap
        if best_score >= 2:  # require a genuine overlap before anchoring on a specific node
            anchor_id = best_id
    if anchor_id is None:
        anchor_id = "thesis" if "thesis" in nodes else (next(iter(nodes)) if nodes else None)

    type_intent = next((t for t, kws in _TYPE_KEYWORDS if any(k in q for k in kws)), None)

    results: list[dict[str, Any]] = []
    interpreted = ""

    if relations and anchor_id:
        seen: set[str] = set()
        for e in edges:
            if e.get("relation") not in relations:
                continue
            if e.get("to") == anchor_id and str(e.get("from")) in nodes and e["from"] not in seen:
                seen.add(e["from"])
                results.append(_node_view(nodes, e["from"], e["relation"]))
            elif e.get("from") == anchor_id and str(e.get("to")) in nodes and e["to"] not in seen:
                seen.add(e["to"])
                results.append(_node_view(nodes, e["to"], e["relation"]))
        interpreted = f"{'/'.join(relations)} → {nodes.get(anchor_id, {}).get('label', anchor_id)}"
    elif type_intent:
        for nid, n in nodes.items():
            if n.get("type") == type_intent:
                results.append(_node_view(nodes, nid))
        interpreted = f"all “{type_intent}” nodes"
    elif anchor_id:
        seen = set()
        for e in edges:
            if e.get("to") == anchor_id and str(e.get("from")) in nodes and e["from"] not in seen:
                seen.add(e["from"])
                results.append(_node_view(nodes, e["from"], e.get("relation", "")))
            elif e.get("from") == anchor_id and str(e.get("to")) in nodes and e["to"] not in seen:
                seen.add(e["to"])
                results.append(_node_view(nodes, e["to"], e.get("relation", "")))
        interpreted = f"everything connected to “{nodes.get(anchor_id, {}).get('label', anchor_id)}”"

    return {
        "ok": True,
        "question": question,
        "interpreted_as": interpreted,
        "anchor": anchor_id,
        "relations": relations,
        "type_intent": type_intent,
        "results": results,
        "result_count": len(results),
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ztare research map-query",
                                     description="No-LLM natural-language query over the project's research map.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--q", "--question", dest="question", required=True, help="Plain-English question about the map.")
    parser.add_argument("--repo", type=Path, default=None)
    parser.add_argument("--json", action="store_true", help="Emit the answer as JSON (for the workbench).")
    args = parser.parse_args(argv)
    from ztare.reports.research_graph import build_research_graph
    carrier = build_research_graph(args.project, args.repo or _repo_root())
    answer = query_graph(carrier, args.question)
    if args.json:
        print(json.dumps(answer))
        return 0
    print(f"Q: {answer['question']}")
    print(f"Read as: {answer['interpreted_as'] or '(no anchor found)'}")
    if not answer["results"]:
        print("No matching nodes.")
        return 0
    for r in answer["results"]:
        rel = f"[{r['relation']}] " if r.get("relation") else ""
        print(f"  {rel}{r.get('label')}  ({r.get('type')})")
    return 0


def _selfcheck() -> None:
    carrier = {
        "nodes": [
            {"id": "thesis", "type": "thesis", "label": "Rates cut in 2026"},
            {"id": "claim:s002", "type": "claim", "label": "Inflation falls below 3%"},
            {"id": "falsifier:1", "type": "falsifier", "label": "CPI reaccelerates two quarters running"},
            {"id": "src:1", "type": "evidence", "label": "FOMC minutes"},
            {"id": "tension:1", "type": "tension", "label": "Labor market still tight"},
        ],
        "edges": [
            {"from": "claim:s002", "to": "thesis", "relation": "DERIVES"},
            {"from": "falsifier:1", "to": "thesis", "relation": "FALSIFIES"},
            {"from": "src:1", "to": "thesis", "relation": "SUPPORTS"},
            {"from": "tension:1", "to": "thesis", "relation": "CHALLENGES"},
        ],
    }
    a = query_graph(carrier, "what could falsify the thesis?")
    assert a["relations"] == ["FALSIFIES"] and a["anchor"] == "thesis", a
    assert [r["label"] for r in a["results"]] == ["CPI reaccelerates two quarters running"], a
    b = query_graph(carrier, "what supports the thesis?")
    assert [r["label"] for r in b["results"]] == ["FOMC minutes"], b
    c = query_graph(carrier, "what rests on s002?")  # anchor by id token, DERIVES direction
    assert c["anchor"] == "claim:s002", c
    d = query_graph(carrier, "what are the open tensions?")
    assert [r["label"] for r in d["results"]] == ["Labor market still tight"], d
    print("research_graph_query selfcheck: OK")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--selfcheck":
        _selfcheck()
    else:
        raise SystemExit(main())
