"""Export a ZTARE project's verified research graph as an Obsidian vault — a linked knowledge base a
researcher writes their article FROM, with the weak spots and open questions already marked.

Why this maps cleanly: the research graph is ALREADY a typed node/edge structure, so it lands in Obsidian's
model with almost no impedance — each claim/evidence/tension/falsifier becomes a note, each typed relation a
`[[wikilink]]` (so Obsidian's own graph view mirrors the argument), the thesis is the index MOC, and a Verdict
note carries the trust read + what would change your mind. NOT a source-discovery tool (that's Elicit/NotebookLM);
this is the rigor layer's output, exported for writing.

Reuses the same read-only projection the workbench Map uses (`research_graph.build_research_graph` +
`graph_algorithms.analyze`) plus the eval's weakest_point/gaps — no new kernel computation. CLI-master:
`ztare autoresearch export-obsidian --project <slug> [--out <vault_dir>]`.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from ztare.common import graph_algorithms
from ztare.reports.research_graph import build_research_graph

# Human verbs for the typed relations (match the workbench Map's reading).
_VERB = {
    "SUPPORTS": "supports", "DERIVES": "derives", "TESTS": "tests", "CONSTRAINS": "constrains",
    "CHALLENGES": "challenges", "FALSIFIES": "could falsify",
}
_SUPPORT = graph_algorithms.SUPPORT_RELATIONS
_ATTACK = graph_algorithms.ATTACK_RELATIONS
# type → Obsidian tag + an emoji marker so the vault reads at a glance.
_TAG = {
    "thesis": "thesis", "claim": "claim", "candidate": "to-test", "evidence": "evidence",
    "tension": "tension", "gap": "open-gap", "constraint": "constraint", "branch": "branch",
    "falsifier": "falsifier", "rejected": "ruled-out",
}


def _slug(text: str, fallback: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|#\[\]^]", "", str(text or "")).strip()
    text = re.sub(r"\s+", " ", text)
    return (text[:70].strip() or fallback)


def _note_names(nodes: list[dict[str, Any]]) -> dict[str, str]:
    """id → unique note filename (no extension). Human-readable (label-based) so wikilinks read well."""
    names: dict[str, str] = {}
    used: set[str] = set()
    for n in nodes:
        base = _slug(n.get("label"), n.get("id", "node"))
        name, i = base, 2
        while name.lower() in used:
            name = f"{base} ({i})"
            i += 1
        used.add(name.lower())
        names[n["id"]] = name
    return names


def _yaml_list(items: list[str]) -> str:
    return "[" + ", ".join(json.dumps(x) for x in items) + "]"


def _node_note(node: dict[str, Any], edges: list[dict], by_id: dict[str, dict],
               names: dict[str, str], insight_tags: list[str]) -> str:
    nid = node["id"]
    ntype = node.get("type", "node")
    fm = [
        "---",
        f"type: {ntype}",
        f"tags: {_yaml_list(['ztare/' + _TAG.get(ntype, ntype)] + insight_tags)}",
    ]
    if isinstance(node.get("weight"), (int, float)):
        fm.append(f"confidence: {round(float(node['weight']) * 100)}")
    if node.get("status"):
        fm.append(f"status: {json.dumps(str(node['status']))}")
    fm.append(f"aliases: {_yaml_list([str(node.get('label') or nid)])}")
    fm.append("---")

    body = ["", f"# {node.get('label') or nid}", ""]
    if isinstance(node.get("weight"), (int, float)):
        body.append(f"> [!info] Confidence: {round(float(node['weight']) * 100)}%")
        body.append("")
    detail = str(node.get("detail") or "").strip()
    label = str(node.get("label") or "").strip()
    if detail.startswith(label):                     # detail often repeats the label as its first line
        detail = detail[len(label):].strip()
    if detail:
        body += [detail, ""]

    def links(pairs: list[tuple[str, str]]) -> list[str]:
        return [f"- [[{names[o]}]] — {_VERB.get(rel, rel.lower())}" for o, rel in pairs if o in names]

    supported_by = [(e["from"], e["relation"]) for e in edges if e.get("to") == nid and e.get("relation") in _SUPPORT and e.get("from") in by_id]
    challenged_by = [(e["from"], e["relation"]) for e in edges if e.get("to") == nid and e.get("relation") in _ATTACK and e.get("from") in by_id]
    supports = [(e["to"], e["relation"]) for e in edges if e.get("from") == nid and e.get("relation") in _SUPPORT and e.get("to") in by_id]
    challenges = [(e["to"], e["relation"]) for e in edges if e.get("from") == nid and e.get("relation") in _ATTACK and e.get("to") in by_id]

    if supported_by:
        body += ["## Supported by", *links(supported_by), ""]
    if challenged_by:
        body += ["## Challenged by — what could break it", *links(challenged_by), ""]
    if supports:
        body += ["## Supports", *links(supports), ""]
    if challenges:
        body += ["## Challenges", *links(challenges), ""]
    return "\n".join(fm + body).rstrip() + "\n"


def _index_note(project: str, thesis: dict | None, nodes: list[dict], names: dict[str, str],
                insights: dict, eval_data: dict) -> str:
    def link(nid: str) -> str:
        return f"[[{names[nid]}]]" if nid in names else ""

    fm = ["---", "type: research-map", f"tags: {_yaml_list(['ztare/thesis', 'MOC'])}",
          f"project: {json.dumps(project)}", "---", ""]
    title = thesis.get("label") if thesis else project
    out = fm + [f"# {title}", ""]

    # Verdict callout — structural confidence (DF-QuAD, not the gameable judge score) + the weak spot.
    strength = insights.get("argument_strength")
    verdict = ["> [!abstract] Verdict"]
    if isinstance(strength, (int, float)):
        verdict.append(f"> **Structural confidence:** {round(strength * 100)}% (after every support and attack nets out — bipolar argumentation, not the raw judge score).")
    wl = insights.get("weakest_link")
    if wl:
        verdict.append(f"> **Weakest link:** {link(wl.get('id'))} at {round((wl.get('probability') or 0) * 100)}% — settle this first.")
    lp = insights.get("linchpin")
    if lp:
        verdict.append(f"> **The most rests on:** {link(lp.get('id'))}.")
    cl = insights.get("critical_link")
    if cl:
        verdict.append(f"> **Single point of failure:** the link {link(cl.get('from'))} → {link(cl.get('to'))} — cut it and {cl.get('disconnects')} nodes lose support.")
    out += verdict + [""]

    # What would change your mind — the honest core for a writer.
    falsifiers = [n for n in nodes if n.get("type") == "falsifier"]
    tensions = [n for n in nodes if n.get("type") == "tension"]
    wp = str(eval_data.get("weakest_point") or "").strip()
    if falsifiers or tensions or wp:
        out += ["## What would change my mind", "> [!question] Address these before you rely on the thesis", ""]
        if wp:
            out.append(f"- **Weakest point (judge):** {wp}")
        out += [f"- {link(n['id'])}" for n in falsifiers + tensions if n["id"] in names]
        out.append("")

    def section(title: str, kinds: tuple[str, ...]) -> None:
        rows = [n for n in nodes if n.get("type") in kinds and n["id"] in names]
        if not rows:
            return
        out.append(f"## {title}")
        for n in rows:
            conf = f" — {round(float(n['weight']) * 100)}%" if isinstance(n.get("weight"), (int, float)) else ""
            out.append(f"- {link(n['id'])}{conf}")
        out.append("")

    section("Claims", ("claim", "candidate"))
    section("Evidence", ("evidence",))
    section("Constraints", ("constraint",))

    unsup = insights.get("unsupported") or []
    if unsup:
        out += ["## Assertions with no evidence yet",
                *[f"- {link(u.get('id'))}" for u in unsup if u.get("id") in names], ""]
    out += ["---", "*Exported from ZTARE — a stress-tested argument, not a finished article. Open in Obsidian's graph view to walk the structure.*", ""]
    return "\n".join(out)


def build_obsidian_vault(project: str, repo_root: Path, out_dir: Path) -> dict[str, Any]:
    carrier = build_research_graph(project, repo_root)
    nodes = [n for n in carrier.get("nodes", []) if isinstance(n, dict) and n.get("id")]
    edges = carrier.get("edges", [])
    by_id = {n["id"]: n for n in nodes}
    insights = graph_algorithms.analyze(carrier)
    eval_path = repo_root / "projects" / project / "latest_eval_results.json"
    try:
        eval_data = json.loads(eval_path.read_text()) if eval_path.exists() else {}
    except Exception:
        eval_data = {}
    thesis = next((n for n in nodes if n.get("type") == "thesis"), None) or (nodes[0] if nodes else None)

    names = _note_names(nodes)
    # nodes flagged by an insight get a tag so Obsidian search/filter can find "weak links", "linchpins", etc.
    flagged: dict[str, list[str]] = {}
    for key, tag in (("linchpin", "ztare/linchpin"), ("weakest_link", "ztare/weak-link"), ("most_contested", "ztare/contested")):
        ref = insights.get(key)
        if isinstance(ref, dict) and ref.get("id"):
            flagged.setdefault(ref["id"], []).append(tag)

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    index_name = f"{_slug(project, 'research-map')} — Research map"
    (out_dir / f"{index_name}.md").write_text(_index_note(project, thesis, nodes, names, insights, eval_data), encoding="utf-8")
    written.append(index_name + ".md")
    for n in nodes:
        (out_dir / f"{names[n['id']]}.md").write_text(
            _node_note(n, edges, by_id, names, flagged.get(n["id"], [])), encoding="utf-8")
        written.append(names[n["id"]] + ".md")

    return {
        "ok": True, "schema": "ztare-obsidian-export-v1", "project": project,
        "out_dir": str(out_dir), "index": index_name + ".md",
        "note_count": len(written), "node_count": len(nodes), "edge_count": len(edges),
    }


def _selfcheck() -> None:
    import tempfile
    carrier = {
        "graph_kind": "source_claim_graph",
        "nodes": [
            {"id": "thesis", "type": "thesis", "label": "T holds", "weight": 0.7},
            {"id": "c1", "type": "claim", "label": "Claim one", "weight": 0.4, "detail": "Claim one\nmore detail"},
            {"id": "e1", "type": "evidence", "label": "Source / A: 1"},   # illegal filename chars
            {"id": "f1", "type": "falsifier", "label": "Could break it"},
        ],
        "edges": [
            {"from": "e1", "to": "c1", "relation": "SUPPORTS"},
            {"from": "c1", "to": "thesis", "relation": "DERIVES"},
            {"from": "f1", "to": "thesis", "relation": "FALSIFIES"},
        ],
    }
    names = _note_names(carrier["nodes"])
    assert len(set(names.values())) == 4, names                       # unique note names
    assert "/" not in names["e1"] and ":" not in names["e1"], names["e1"]  # filename-safe
    by_id = {n["id"]: n for n in carrier["nodes"]}
    note = _node_note(by_id["c1"], carrier["edges"], by_id, names, ["ztare/weak-link"])
    assert "type: claim" in note and "confidence: 40" in note, note
    assert "## Supported by" in note and "## Supports" in note, note   # incoming evidence + outgoing derive
    assert note.count("Claim one") == 2, "H1 + alias, detail's duplicate label line stripped"  # not 3
    idx = _index_note("p", by_id["thesis"], carrier["nodes"], names, graph_algorithms.analyze(carrier), {"weakest_point": "wp"})
    assert "What would change my mind" in idx and names["f1"] in idx, idx
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / f"{names['c1']}.md").write_text(note)              # note filenames are writable as-is
    print("export_obsidian selfcheck: OK")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ztare autoresearch export-obsidian")
    parser.add_argument("--project", required=True, help="Project slug.")
    parser.add_argument("--out", default="", help="Target vault directory (default: projects/<slug>/exports/obsidian).")
    parser.add_argument("--json", action="store_true", help="Emit JSON manifest.")
    args = parser.parse_args(argv)
    root = _repo_root()
    out_dir = Path(args.out).expanduser() if args.out else (root / "projects" / args.project / "exports" / "obsidian")
    manifest = build_obsidian_vault(args.project, root, out_dir)
    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(f"Exported {manifest['note_count']} notes for '{args.project}' → {manifest['out_dir']}\n"
              f"Open the vault in Obsidian and start from: {manifest['index']}")
    return 0


if __name__ == "__main__":
    import sys as _sys
    if "--selfcheck" in _sys.argv:
        _selfcheck()
    else:
        raise SystemExit(main())
