"""Governed artifacts — adapters into a GovernedState (research-map carrier, a run's persisted record) + the
interim governed serialization. See `artifacts.py` for the module-level docstring."""
from __future__ import annotations

from ztare.scenarios.governed_types import GovernedEdge, GovernedElement, GovernedState
from ztare.scenarios.verdict import Verdict

_NODE_NOTE_MARKERS = ("What would settle it:", "Kills it if:", "What would change our mind:")


def _clean_node_text(text: str) -> str:
    """A research-map node's `detail` often bundles the CLAIM with a trailing watch/falsification note
    ("Completion lift ≥1pp\\nWhat would settle it: …"). The governed ELEMENT is the claim (it must be verbatim-
    matchable + read cleanly in a deliverable), and the run already emits separate falsifier nodes — so split
    off a trailing note. Only strips a note that STARTS PAST the beginning (a node that IS a falsifier keeps its
    text)."""
    for marker in _NODE_NOTE_MARKERS:
        i = text.find(marker)
        if i > 0:
            return text[:i].strip()
    return text.strip()


def governed_state_from_carrier(carrier: dict) -> GovernedState:
    """Adapt a research-map carrier (`ztare-research-graph-v1`: nodes {id,type,label,detail,weight}, edges
    {from,to,relation}) into a GovernedState. The research map IS the governed argument graph — this is the ONE
    bridge between them, not a second representation. Node text = detail (fuller) else label, with a trailing
    watch-note split off (`_clean_node_text`) so a bare claim is clean + verbatim-matchable; relation = edge kind."""
    elements: "list[GovernedElement]" = []
    for node in carrier.get("nodes", []) or []:
        text = _clean_node_text(str(node.get("detail") or node.get("label") or "").strip())
        if text:
            kind = str(node.get("type") or "claim")
            source_key = (str(node.get("source_sha256") or node.get("content_sha256") or node.get("source_id") or "")
                          if kind == "evidence" else "")
            elements.append(GovernedElement(id=str(node.get("id")), kind=kind, text=text, source_key=source_key))
    edges: "list[GovernedEdge]" = []
    for edge in carrier.get("edges", []) or []:
        src, rel = str(edge.get("from")), str(edge.get("relation") or "")
        # A warrant is EARNED by a check, never INFERRED from the source node's type. Source authenticity (a
        # hash-bound quote proves what a source SAYS) is a different property from inference validity (that the
        # quote SUPPORTS this claim), and the old rule conflated them: it stamped W2 (cited) on any support edge
        # out of an evidence node, so a pile of generic facts read as cited support for the thesis (ai_capex:
        # 0.973 cited while every causal subclaim was unsupported — a laundering vector, human-caught 2026-07-10).
        # So EVERY proposed edge begins UNCHECKED (W3). W2/W1/W0 are minted only when a path that actually did the
        # check stamps the edge's `warrant` (a promoted citation carries a claim target + excerpt + source receipt
        # + admission; gp-ansatz recomputes; LeanMill certifies) — never the generic carrier.
        declared_w = str(edge.get("warrant") or "").strip()
        warrant = declared_w if declared_w in ("W0", "W1", "W2", "W3") else "W3"
        edges.append(GovernedEdge(src=src, kind=rel, dst=str(edge.get("to")), warrant=warrant))
    return GovernedState(elements, edges)


def argument_overlay(carrier: dict) -> dict:
    """The argument-kernel VIEW of a research-map carrier, for the workbench Map: the grounded verdict + humane
    reason, which nodes the decision TURNS ON (minimal cores), the load-bearing hinge, and each node's grounded
    lifecycle (BACKED / CONTRADICTED / UNTESTED). The research map already IS the argument graph
    (`governed_state_from_carrier` — one source of truth); this reads the kernel's analysis of it so the graph
    the user already looks at renders the DECISION, not just the topology. Best-effort: `{}` on any failure. No LLM."""
    from collections import Counter

    try:
        from ztare.scenarios.argument_kernel import argument_analysis
        g = governed_state_from_carrier(carrier)
        if not g.elements:
            return {}
        analysis = argument_analysis(g)
        cores = [list(core) for core in (analysis.get("minimal_cores") or [])]
        core_members = {item for core in cores for item in core}
        hinge = str(analysis.get("hinge") or "")
        node_states = analysis.get("node_states") or {}
        per_node_strength = (analysis.get("strength") or {}).get("per_node") or {}
        nodes = {el.id: {"grounded": node_states.get(el.id, "UNTESTED"),
                         "in_core": el.id in core_members, "hinge": el.id == hinge,
                         **({"profile": per_node_strength[el.id]} if el.id in per_node_strength else {})}
                 for el in g.elements}
        overlay = {"verdict": analysis["verdict"], "structural_verdict": analysis["verdict"],
                   "reason": analysis["reason"], "warrant_ceiling": analysis["warrant_ceiling"],
                   "coverage": analysis.get("coverage", 0.0),
                   "cores": cores, "hinge": hinge, "nodes": nodes}
        # Node-level provenance honesty (Fable — the moat's soft spot): how much of the graph's own wording is
        # LLM-authored (unchecked at the node level) vs traces to a real source. Surfaced so a reader knows the
        # determinism starts AFTER an LLM-shaped carrier.
        provs = [str(n.get("provenance") or "llm") for n in (carrier.get("nodes") or [])]
        if provs:
            counts = dict(Counter(provs))
            overlay["node_provenance"] = {"llm": counts.get("llm", 0), "sourced": counts.get("sourced", 0),
                                          "total": len(provs), "counts": counts}
        strength = analysis.get("strength") or {}
        overlay["strength_status"] = strength.get("status")
        overlay["thesis_profile"] = strength.get("profile")
        return overlay
    except Exception:  # noqa: BLE001 — the overlay is additive; a bad map must never blank the graph
        return {}


def governed_state_from_research_map(project: str, repo_root) -> GovernedState:
    """The RICH governed state: the workbench research map itself (`build_research_graph` over the run's kernel
    files — probability_dag, evidence packet, constraints, discriminators, falsifiers). ONE source of truth for
    the map, the argument, and the deliverables. Empty state on any read failure (best-effort, never crashes)."""
    try:
        from pathlib import Path as _Path

        from ztare.reports.research_graph import build_research_graph
        carrier = build_research_graph(project, _Path(repo_root))
        state = governed_state_from_carrier(carrier) if carrier.get("ok") else GovernedState()
        return _merge_governed_overlay(project, repo_root, state)
    except Exception:  # noqa: BLE001 — a missing/unbuildable map yields an empty governed state, never a crash
        return GovernedState()


def governed_overlay_path(project: str, repo_root):
    from pathlib import Path
    return Path(repo_root) / "projects" / project / "workspace" / "governed_overlay.json"


def _merge_governed_overlay(project: str, repo_root, state: GovernedState) -> GovernedState:
    """Merge the project's GOVERNED OVERLAY (elements/edges written back by an executed wager outcome or a
    warrant promotion) onto the derived research map — so a RESOLVED experiment becomes part of the governed
    state and `recompile`/strength pick it up. Additive + dedup'd; a missing/bad overlay leaves the map as-is."""
    import json

    p = governed_overlay_path(project, repo_root)
    if not p.is_file():
        return state
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return state
    ids = {e.id for e in state.elements}
    elements = list(state.elements)
    for e in data.get("elements", []) or []:
        eid = str(e.get("id") or "")
        if eid and eid not in ids:
            source_key = str(e.get("source_sha256") or e.get("content_sha256") or e.get("source_id") or "")
            elements.append(GovernedElement(eid, str(e.get("kind") or "claim"), str(e.get("text") or ""), source_key))
            ids.add(eid)
    have = {(x.src, x.kind, x.dst) for x in state.edges}
    edges = list(state.edges)
    for e in data.get("edges", []) or []:
        key = (str(e.get("src")), str(e.get("kind") or ""), str(e.get("dst")))
        if key[0] and key[2] and key not in have:
            edges.append(GovernedEdge(key[0], key[1], key[2], str(e.get("warrant") or "W3")))
            have.add(key)
    return GovernedState(elements, edges)


def append_governed_overlay(project: str, repo_root, elements: "list[dict]", edges: "list[dict]") -> None:
    """Append governed elements/edges to the project overlay — the write-back door an executed wager outcome (or
    a warrant promotion) uses to make a resolved experiment part of the map."""
    import json

    p = governed_overlay_path(project, repo_root)
    data = {"elements": [], "edges": []}
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {"elements": [], "edges": []}
    # Idempotent by governed identity. A user can submit the same citation twice; duplicate edges must not make
    # it look like independent corroboration. If the same edge is re-admitted more strongly, keep the stronger
    # deterministic warrant.
    rank = {"W3": 0, "W2": 1, "W1": 2, "W0": 3}
    by_id = {str(e.get("id")): e for e in (data.get("elements") or []) if isinstance(e, dict) and e.get("id")}
    for element in elements:
        if isinstance(element, dict) and element.get("id"):
            by_id[str(element["id"])] = element
    by_edge = {(str(e.get("src")), str(e.get("kind")), str(e.get("dst"))): e
               for e in (data.get("edges") or []) if isinstance(e, dict)}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        key = (str(edge.get("src")), str(edge.get("kind")), str(edge.get("dst")))
        current = by_edge.get(key)
        if current is None or rank.get(str(edge.get("warrant") or "W3"), 0) >= rank.get(str(current.get("warrant") or "W3"), 0):
            by_edge[key] = edge
    data["elements"] = list(by_id.values())
    data["edges"] = list(by_edge.values())
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


RECHECK_ID_PREFIX = "ev.recheck."  # the recheck driver OWNS overlay entries under this evidence-id prefix


def set_recheck_overlay_entries(project: str, repo_root, elements: "list[dict]", edges: "list[dict]") -> None:
    """Reconcile the RECHECK-owned slice of the project overlay (elements/edges whose id/src starts with
    `RECHECK_ID_PREFIX`): drop all prior recheck-owned entries and write exactly the given ones. Unlike
    `append_governed_overlay` (add-only, for a resolved wager), the recheck driver must be able to DEMOTE — a
    warrant it no longer re-earns must DISAPPEAR — so it owns its slice and rewrites it idempotently, leaving
    every non-recheck entry (wager outcomes, etc.) untouched."""
    import json

    p = governed_overlay_path(project, repo_root)
    data = {"elements": [], "edges": []}
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {"elements": [], "edges": []}
    kept_els = [e for e in (data.get("elements") or []) if not str(e.get("id", "")).startswith(RECHECK_ID_PREFIX)]
    kept_edges = [e for e in (data.get("edges") or []) if not str(e.get("src", "")).startswith(RECHECK_ID_PREFIX)]
    data["elements"] = kept_els + list(elements)
    data["edges"] = kept_edges + list(edges)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def governed_state_from_run(*, claim: str = "", evidence: str = "",
                            findings: "list[str] | None" = None,
                            falsifiers: "list[str] | None" = None) -> GovernedState:
    """Build the governed final state from a run's persisted governed record. `claim` is the HARDENED claim
    (the final working thesis — NOT the pre-test charter claim). Empty pieces are simply absent (a thinner but
    still fully-governed state — better a thin governed artifact than a rich ungoverned one)."""
    elements: "list[GovernedElement]" = []
    if claim.strip():
        elements.append(GovernedElement("claim.hardened", "claim", claim.strip()))
    if evidence.strip():
        elements.append(GovernedElement("evidence.bound", "evidence", evidence.strip()))
    for i, finding in enumerate(findings or []):
        if str(finding).strip():
            elements.append(GovernedElement(f"finding.{i}", "finding", str(finding).strip()))
    for i, falsifier in enumerate(falsifiers or []):
        if str(falsifier).strip():
            elements.append(GovernedElement(f"falsifier.{i}", "falsifier", str(falsifier).strip()))
    return GovernedState(elements)


def serialize_governed(governed: GovernedState, *, verdict: "Verdict | None" = None) -> dict:
    """The interim GOVERNED artifact (Fable's option B — emitted as a free serialization, NOT the trust
    boundary). Everything here traces to the governed graph; a downstream AI polish is the USER's UNGOVERNED
    step and must be re-checked with `reingest_gate` before it ships wearing the stamp."""
    payload = {
        "schema": "ztare-governed-artifact-v1",
        "elements": [{"id": e.id, "kind": e.kind, "text": e.text,
                      **({"source_key": e.source_key} if e.source_key else {})} for e in governed.elements],
        "edges": [{"src": e.src, "kind": e.kind, "dst": e.dst, "warrant": getattr(e, "warrant", "W3")}
                  for e in governed.edges],
        "downstream_polish": "UNGOVERNED — re-check any AI-polished prose with reingest_gate() before shipping.",
    }
    if verdict is not None:
        payload["verdict"] = {"status": verdict.status, "reason": verdict.reason,
                              "citations": verdict.citations, "load_bearing": verdict.load_bearing,
                              "load_bearing_ties": verdict.load_bearing_ties, "coverage": verdict.coverage}
    # The principled ATMS/ABA analysis (grounded verdict + minimal cores + dominators + warrant ceiling + test
    # agenda) — the AUTHORITATIVE hinge analysis (minimal cores subsume the old single-toggle `decision_hinges`,
    # which has been removed: cores catch jointly-pivotal sets it could not see). Presentation is the renderer's job.
    try:
        from ztare.scenarios.argument_kernel import argument_analysis
        payload["argument"] = argument_analysis(governed)
    except Exception:  # noqa: BLE001 — the argument analysis is additive; never break serialization
        pass
    return payload


def governed_state_from_serialized(payload: dict) -> GovernedState:
    """Rebuild a GovernedState from a `serialize_governed` payload (the inverse) — so a DECISION BASELINE can be
    stored and recompiled against later (the stale-decision diff). Preserves warrant classes on edges."""
    elements = [GovernedElement(id=str(e.get("id")), kind=str(e.get("kind") or "claim"),
                                text=str(e.get("text") or ""), source_key=str(e.get("source_key") or ""))
                for e in (payload.get("elements") or []) if e.get("id")]
    edges = [GovernedEdge(src=str(e.get("src")), kind=str(e.get("kind") or ""), dst=str(e.get("dst")),
                          warrant=str(e.get("warrant") or "W3"))
             for e in (payload.get("edges") or [])]
    return GovernedState(elements, edges)


def _selftest() -> int:
    # evidence-rooted thesis → SUPPORTED, both nodes BACKED
    c1 = {"ok": True,
          "nodes": [{"id": "e1", "type": "evidence", "detail": "measured X"},
                    {"id": "t1", "type": "thesis", "detail": "thesis T"}],
          "edges": [{"from": "e1", "to": "t1", "relation": "SUPPORTS"}]}
    ov = argument_overlay(c1)
    # the HUMAN verdict is the graded status (a clean-supported thesis still reads CONTESTED — nothing is ever
    # settled); the crisp grounded verdict is kept internal as `structural_verdict` (pick-once, Fable).
    assert ov["verdict"] == "CONTESTED", ov.get("verdict")
    assert ov["structural_verdict"] == "SUPPORTED", ov.get("structural_verdict")
    assert ov["nodes"]["t1"]["grounded"] == "BACKED" and ov["nodes"]["e1"]["grounded"] == "BACKED"
    # no evidence → graded UNSUPPORTED (crisp BLOCKED), humane reason; the thesis reads UNTESTED
    c2 = {"ok": True, "nodes": [{"id": "t1", "type": "thesis", "detail": "thesis T"}], "edges": []}
    ov2 = argument_overlay(c2)
    assert ov2["verdict"] == "UNSUPPORTED" and "No evidence is bound" in ov2["reason"], ov2
    assert ov2["structural_verdict"] == "BLOCKED", ov2.get("structural_verdict")
    assert ov2["nodes"]["t1"]["grounded"] == "UNTESTED"
    # empty / unbuildable carrier → {} (never crashes, never blanks the graph)
    assert argument_overlay({"ok": True, "nodes": [], "edges": []}) == {}
    assert argument_overlay({}) == {}
    print("ADAPTERS OVERLAY SELFTEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
