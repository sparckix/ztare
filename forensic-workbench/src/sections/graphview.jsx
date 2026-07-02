import React from "react";
import ReactFlow, { Background, Controls, Handle, Position, MarkerType } from "reactflow";
import "reactflow/dist/style.css";
import { displayMessage, displayText } from "../design-system.js";

const h = React.createElement;
const { useState, useMemo, useRef, useEffect } = React;

// Lenses — different PROJECTIONS over the one research-landscape graph (the n-dimensional basin). Each
// is the set of node types it keeps; the thesis is always the anchor.
const LENSES = [
  { key: "all", label: "Whole landscape", types: null },
  { key: "reasoning", label: "Reasoning", types: ["thesis", "claim"] },
  { key: "evidence", label: "Evidence", types: ["thesis", "evidence", "candidate"] },
  { key: "fronts", label: "Open fronts", types: ["thesis", "tension", "gap", "branch", "candidate"] },
  { key: "break", label: "What could break it", types: ["thesis", "falsifier", "rejected", "tension"] },
  { key: "constraints", label: "Constraints", types: ["thesis", "constraint"] },
];

// type → visual tone + the small kind label under each node. Falsifiers get their OWN danger tone (red) —
// they're what could break the thesis, distinct from soft tensions/gaps (warn/orange).
const TYPE_TONE = {
  thesis: "thesis", evidence: "ok", constraint: "ok",
  tension: "warn", gap: "warn", falsifier: "danger",
  claim: "neutral", candidate: "neutral", branch: "neutral", rejected: "neutral",
};
const TYPE_KIND = {
  thesis: "thesis", claim: "sub-claim", candidate: "to test", evidence: "evidence",
  tension: "tension", gap: "open gap", constraint: "constraint", branch: "branch", falsifier: "falsifier", rejected: "ruled out",
};

// The typed relations ARE the argument structure — colour each edge by what it does, so the graph
// reads as reasoning, not a grey hairball. Plain verbs for the detail panel (no kernel SHOUTING_CASE).
const REL_STYLE = {
  SUPPORTS: { color: "#2f9e44", verb: "supports", weight: 1.4 },
  DERIVES: { color: "#2f9e44", verb: "derives from", weight: 1.2 },
  TESTS: { color: "#4263eb", verb: "tests", weight: 1.2 },
  CONSTRAINS: { color: "#7048e8", verb: "constrains", weight: 1.2 },
  CHALLENGES: { color: "#e8590c", verb: "challenges", weight: 1.6 },
  FALSIFIES: { color: "#e03131", verb: "could falsify", weight: 1.8 },
};
function relStyle(rel) { return REL_STYLE[rel] || { color: "#c4cad8", verb: String(rel || "links").toLowerCase(), weight: 1.2 }; }

function toneFor(n) {
  if (n.type === "claim" && typeof n.weight === "number") return n.weight >= 0.66 ? "ok" : n.weight >= 0.4 ? "neutral" : "warn";
  return TYPE_TONE[n.type] || "neutral";
}
function subFor(n) {
  const kind = TYPE_KIND[n.type] || n.type || "";
  if (typeof n.weight === "number") return `${kind} · ${Math.round(n.weight * 100)}%`;
  if (n.status) return `${kind} · ${displayText(n.status)}`;
  return kind;
}

// Layered "elevation" layout (Sugiyama longest-path layer assignment) — the topographic shape, not a
// hairball. x = the longest chain of from→to edges ending at a node, so support flows LEFT→RIGHT and the
// thesis (everything points at it) lands in the rightmost column — the summit. Adversarial nodes point AT
// their target, so a falsifier sits one column left of what it attacks and its edge reads cleanly rightward.
// Bounded to `nodes.length` passes (Bellman-Ford shape) so a circular-reasoning cycle can't loop forever.
const COL_W = 340, ROW_H = 128;
function layeredLayout(nodes, edges) {
  const ids = new Set(nodes.map((n) => n.id));
  const es = edges.filter((e) => ids.has(e.from) && ids.has(e.to));
  const depth = {};
  nodes.forEach((n) => { depth[n.id] = 0; });
  for (let k = 0; k < nodes.length; k++) {
    let changed = false;
    for (const e of es) {
      if (depth[e.from] + 1 > depth[e.to]) { depth[e.to] = depth[e.from] + 1; changed = true; }
    }
    if (!changed) break;
  }
  const byDepth = {};
  nodes.forEach((n) => { (byDepth[depth[n.id]] = byDepth[depth[n.id]] || []).push(n); });
  const pos = {};
  Object.keys(byDepth).map(Number).sort((a, b) => a - b).forEach((d) => {
    const col = byDepth[d].slice().sort((a, b) =>
      String(a.type).localeCompare(String(b.type)) || String(a.id).localeCompare(String(b.id)));
    const n = col.length;
    col.forEach((node, i) => { pos[node.id] = { x: d * COL_W, y: (i - (n - 1) / 2) * ROW_H }; });
  });
  return pos;
}

function MapNode({ data }) {
  const cls = `gv-node tone-${data.tone} ${data.big ? "gv-node-big" : ""} ${data.faded ? "gv-node-faded" : ""} ${data.dim ? "gv-node-dim" : ""} ${data.selected ? "selected" : ""}`;
  return h("div", { className: cls },
    h(Handle, { type: "target", position: Position.Left, isConnectable: false }),
    h("span", { className: "gv-node-label" }, displayText(data.label)),
    data.sub ? h("span", { className: "gv-node-sub" }, data.sub) : null,
    h(Handle, { type: "source", position: Position.Right, isConnectable: false }));
}
const NODE_TYPES = { map: MapNode };

// Natural-language → predicate facet. So the ONE search box also answers questions ("what could falsify
// the thesis" → the FALSIFIES facet + the thesis as the keyword anchor) — no second "ask" input, no model.
// Mirrors the CLI grammar in ztare.reports.research_graph_query at the altitude the facet UI needs.
const MQ_REL_PHRASES = [
  ["FALSIFIES", ["falsif", "disprove", "refute", "overturn", "sink", "break the"]],
  ["RULED_OUT", ["ruled out", "rejected", "set aside", "dismissed", "alternativ"]],
  ["CONTRADICTS", ["contradic", "conflict", "inconsist"]],
  ["CHALLENGES", ["challeng", "tension", "undercut", "threaten", "weaken", "cut against", "argue against"]],
  ["SUPPORTS", ["support", "backs", "backed by", "evidence for", "holds up", "in favou", "in favor", "props up"]],
  ["DERIVES", ["rest on", "rests on", "depend", "rely", "relies", "build on", "built on", "derive", "follow from", "hinge"]],
  ["TESTS", ["would test", "discriminat", "would settle", "distinguish", "probe", "decide between"]],
  ["CONSTRAINS", ["constrain", "limit", "bound", "restrict", "govern"]],
];
const MQ_STOP = new Set(["what", "which", "would", "could", "does", "the", "this", "that", "thesis", "claim",
  "claims", "about", "and", "for", "with", "are", "our", "have", "how", "why", "you", "its", "it", "is",
  "a", "an", "on", "of", "to", "me", "show", "list", "all"]);

// Interpret a typed query. If it reads as a relation-question present in THIS graph, return the predicate to
// facet on + the residual anchor words as a keyword; otherwise it's a plain keyword search.
function interpretMapQuestion(text, presentPreds) {
  const t = String(text || "").toLowerCase();
  let predicate = null;
  for (const [rel, kws] of MQ_REL_PHRASES) {
    if (presentPreds.includes(rel) && kws.some((k) => t.includes(k))) { predicate = rel; break; }
  }
  if (!predicate) return { predicate: null, keyword: text };
  const relWords = new Set(MQ_REL_PHRASES.flatMap(([, kws]) => kws).flatMap((k) => k.split(" ")));
  const anchor = t.replace(/[^a-z0-9 ]+/g, " ").split(/\s+/)
    .filter((w) => w.length > 2 && !MQ_STOP.has(w) && !relWords.has(w) && ![...relWords].some((rw) => rw.length > 3 && w.startsWith(rw)))
    .join(" ");
  return { predicate, keyword: anchor };
}

// GraphView — the traversable research-landscape graph with selectable lenses (projections). Click a
// node to interrogate it; switch the lens to project along a dimension. Fed by the typed projection.
export function GraphView({ nodes, edges, truncated, focusId, onFocusHandled }) {
  const [selected, setSelected] = useState(null);
  const [hovered, setHovered] = useState(null);
  const [lens, setLens] = useState("all");
  const rfRef = useRef(null);
  const [query, setQuery] = useState("");          // keyword facet (node-label substring)
  const [preds, setPreds] = useState([]);          // predicate facets (relations to keep; empty = all)
  const [showTriples, setShowTriples] = useState(false);
  const allNodes = Array.isArray(nodes) ? nodes : [];
  const allEdges = Array.isArray(edges) ? edges : [];
  const labelById = useMemo(() => {
    const m = {}; allNodes.forEach((n) => { m[n.id] = n.label || n.id; }); return m;
  }, [allNodes]);
  // Every predicate present in the graph — the facet vocabulary (no LLM: a controlled query, formally a
  // faceted SPARQL fragment over the subject—predicate—object triples).
  const allPreds = useMemo(() => {
    const seen = []; const set = new Set();
    allEdges.forEach((e) => { const r = e.relation || "LINKS"; if (!set.has(r)) { set.add(r); seen.push(r); } });
    return seen;
  }, [allEdges]);

  // Faceted query: lens (node-type facet) → predicate facet → keyword facet. Each narrows the triples.
  const { vNodes, vEdges } = useMemo(() => {
    const def = LENSES.find((l) => l.key === lens) || LENSES[0];
    const keep = def.types ? new Set(def.types) : null;
    let ns = allNodes.filter((n) => !keep || keep.has(n.type) || n.type === "thesis");
    let ids = new Set(ns.map((n) => n.id));
    const predSet = preds.length ? new Set(preds) : null;
    let es = allEdges.filter((e) => ids.has(e.from) && ids.has(e.to) && (!predSet || predSet.has(e.relation || "LINKS")));
    // Predicate facet active → keep only nodes that participate in a kept edge (+ the thesis anchor).
    if (predSet) {
      const live = new Set(["thesis"]); es.forEach((e) => { live.add(e.from); live.add(e.to); });
      ns = ns.filter((n) => live.has(n.id) || n.type === "thesis"); ids = new Set(ns.map((n) => n.id));
      es = es.filter((e) => ids.has(e.from) && ids.has(e.to));
    }
    // Keyword facet → the matching nodes + their 1-hop neighbours (so you can trace from a hit).
    const q = query.trim().toLowerCase();
    if (q) {
      const hit = new Set(ns.filter((n) => String(n.label || n.id).toLowerCase().includes(q)).map((n) => n.id));
      const near = new Set(hit);
      es.forEach((e) => { if (hit.has(e.from)) near.add(e.to); if (hit.has(e.to)) near.add(e.from); });
      ns = ns.filter((n) => near.has(n.id)); ids = new Set(ns.map((n) => n.id));
      es = es.filter((e) => ids.has(e.from) && ids.has(e.to));
    }
    return { vNodes: ns, vEdges: es };
  }, [allNodes, allEdges, lens, preds, query]);

  // Click-to-focus from the Structural reads: select the node and pan the canvas to it. If it's hidden by
  // the current lens, drop back to "Whole landscape" first (next render brings it into view, effect re-runs).
  useEffect(() => {
    if (!focusId || !rfRef.current) return;
    if (!vNodes.some((n) => n.id === focusId)) { setLens("all"); return; }
    const p = layeredLayout(vNodes, vEdges)[focusId];
    setSelected(focusId);
    if (p) rfRef.current.setCenter(p.x + 105, p.y, { zoom: 1.05, duration: 500 });
    if (onFocusHandled) onFocusHandled();
  }, [focusId, vNodes]);

  // Focus+context: hovering a node lights up its 1-hop neighbourhood and dims everything else, so a dense
  // map stays traceable. Pure view state; null = nothing hovered (full opacity).
  const neighbors = useMemo(() => {
    if (!hovered) return null;
    const s = new Set([hovered]);
    vEdges.forEach((e) => { if (e.from === hovered) s.add(e.to); if (e.to === hovered) s.add(e.from); });
    return s;
  }, [hovered, vEdges]);

  const rfNodes = useMemo(() => {
    const pos = layeredLayout(vNodes, vEdges);
    return vNodes.map((n) => ({
      id: n.id, type: "map", position: pos[n.id] || { x: 0, y: 0 },
      data: {
        label: n.label || n.id, sub: subFor(n), tone: toneFor(n), selected: selected === n.id,
        big: n.type === "thesis",                                    // the summit
        faded: typeof n.weight === "number" && n.weight < 0.4,       // low-confidence claims recede (lowland)
        dim: neighbors ? !neighbors.has(n.id) : false,               // hover focus+context
      },
    }));
  }, [vNodes, vEdges, selected, neighbors]);

  // Edges coloured by relation (the argument structure), with an arrowhead for direction. Adversarial
  // relations (challenges / falsifies) sit on top, slightly heavier — they're what could break it. On hover,
  // edges touching the hovered node stay lit; the rest recede.
  const rfEdges = useMemo(() => vEdges.map((e, i) => {
    const rs = relStyle(e.relation);
    const adversarial = e.relation === "FALSIFIES" || e.relation === "CHALLENGES";
    const touches = hovered ? (e.from === hovered || e.to === hovered) : true;
    const opacity = hovered ? (touches ? 0.95 : 0.1) : 0.7;
    return {
      id: `e${i}`, source: e.from, target: e.to, zIndex: touches && hovered ? 3 : adversarial ? 2 : 1,
      style: { stroke: rs.color, strokeWidth: rs.weight, opacity },
      markerEnd: { type: MarkerType.ArrowClosed, color: rs.color, width: 14, height: 14 },
    };
  }), [vEdges, hovered]);
  // Which relations are present in this lens — drives the legend.
  const legend = useMemo(() => {
    const seen = []; const set = new Set();
    vEdges.forEach((e) => { const r = e.relation || "links"; if (!set.has(r)) { set.add(r); seen.push(r); } });
    return seen;
  }, [vEdges]);

  if (!allNodes.length) return null;
  const sel = selected ? allNodes.find((n) => n.id === selected) : null;
  const selDetail = sel ? String(sel.detail || sel.label || "").split("\n").map((s) => s.trim()).filter(Boolean) : [];
  // The selected node's role in the argument — its typed relations, in plain language.
  const selRels = sel ? allEdges.flatMap((e) => {
    if (e.from === sel.id) return [{ verb: relStyle(e.relation).verb, color: relStyle(e.relation).color, other: labelById[e.to] || e.to, dir: "out" }];
    if (e.to === sel.id) return [{ verb: relStyle(e.relation).verb, color: relStyle(e.relation).color, other: labelById[e.from] || e.from, dir: "in" }];
    return [];
  }) : [];
  const hiddenCount = truncated && typeof truncated === "object"
    ? Object.values(truncated).reduce((a, b) => a + (Number(b) || 0), 0) : 0;

  const togglePred = (r) => setPreds((cur) => cur.includes(r) ? cur.filter((x) => x !== r) : [...cur, r]);
  // The visible triples — subject —predicate→ object — the RDF reading of the current faceted query.
  const triples = vEdges.map((e) => ({ s: labelById[e.from] || e.from, p: relStyle(e.relation).verb, o: labelById[e.to] || e.to, color: relStyle(e.relation).color }));

  return h("div", { className: "gv" },
    // Lens selector — project the landscape along a dimension (node-type facet).
    h("div", { className: "gv-lenses" },
      LENSES.map((l) => h("button", {
        key: l.key, type: "button", className: `gv-lens ${lens === l.key ? "active" : ""}`,
        onClick: () => { setLens(l.key); setSelected(null); },
      }, l.label))),

    // Faceted query — no LLM: search node labels + filter by predicate (subject—predicate—object).
    h("div", { className: "gv-query" },
      h("input", {
        type: "search", className: "gv-search", value: query,
        placeholder: "Search or ask — e.g. what could falsify the thesis",
        title: "Type a term to filter, or ask a question (“what supports this”, “what rests on S002”) and press Enter",
        onChange: (e) => { setQuery(e.target.value); setSelected(null); },
        onKeyDown: (e) => {
          if (e.key !== "Enter") return;
          const parsed = interpretMapQuestion(query, allPreds);
          if (parsed.predicate) { setPreds([parsed.predicate]); setQuery(parsed.keyword); setSelected(null); }
        },
      }),
      h("div", { className: "gv-preds" },
        allPreds.map((r) => h("button", {
          key: r, type: "button",
          className: `gv-pred ${preds.includes(r) ? "active" : ""}`,
          style: preds.includes(r) ? { borderColor: relStyle(r).color, color: relStyle(r).color } : null,
          title: `Show only “${relStyle(r).verb}” relations`,
          onClick: () => { togglePred(r); setSelected(null); },
        }, relStyle(r).verb))),
      h("button", {
        type: "button", className: `gv-triples-toggle ${showTriples ? "active" : ""}`,
        onClick: () => setShowTriples((v) => !v),
      }, showTriples ? "Hide statements" : `Read as statements (${triples.length})`)),

    // Relation legend — what the edge colours mean (only the ones present in this query).
    legend.length
      ? h("div", { className: "gv-legend" },
          legend.map((r) => h("span", { key: r, className: "gv-legend-item" },
            h("span", { className: "gv-legend-swatch", style: { background: relStyle(r).color } }),
            relStyle(r).verb)))
      : null,

    // Triples readout — the graph as subject—predicate→object statements (the structured query result).
    showTriples
      ? h("div", { className: "gv-triple-list" },
          triples.length
            ? triples.map((t, i) => h("p", { key: i, className: "gv-triple" },
                h("span", { className: "gv-triple-s" }, displayText(t.s)),
                h("span", { className: "gv-triple-p", style: { color: t.color } }, t.p),
                h("span", { className: "gv-triple-o" }, displayText(t.o))))
            : h("p", { className: "gv-detail-empty" }, "No statements match this query."))
      : null,

    h("div", { className: "gv-canvas" },
      h(ReactFlow, {
        nodes: rfNodes, edges: rfEdges, nodeTypes: NODE_TYPES,
        onInit: (inst) => { rfRef.current = inst; },
        onNodeClick: (_e, n) => setSelected((cur) => (cur === n.id ? null : n.id)),
        onNodeMouseEnter: (_e, n) => setHovered(n.id),
        onNodeMouseLeave: () => setHovered(null),
        onPaneClick: () => setSelected(null),
        fitView: true, fitViewOptions: { padding: 0.16 }, proOptions: { hideAttribution: true },
        nodesDraggable: true, nodesConnectable: false, elementsSelectable: true, minZoom: 0.3, maxZoom: 1.8,
      },
        h(Background, { gap: 22, color: "#eef0f6" }),
        h(Controls, { showInteractive: false })),
      hiddenCount
        ? h("p", { className: "gv-truncated" }, `+${hiddenCount} more node${hiddenCount === 1 ? "" : "s"} not shown (the densest evidence and constraints are summarised to keep the map readable)`)
        : null),

    sel
      ? h("div", { className: "gv-detail" },
          h("span", { className: "eyebrow" }, `${TYPE_KIND[sel.type] || sel.type} · ${displayText(sel.label)}`),
          selDetail.length
            ? h("ul", null, selDetail.map((d, i) => h("li", { key: i }, displayMessage(d))))
            : h("p", { className: "gv-detail-empty" }, "Nothing more recorded for this node."),
          // The node's role in the argument — its typed relations to other nodes.
          selRels.length
            ? h("div", { className: "gv-detail-rels" },
                selRels.slice(0, 8).map((r, i) =>
                  h("span", { key: i, className: "gv-rel" },
                    h("span", { className: "gv-rel-verb", style: { color: r.color } }, r.dir === "out" ? r.verb : `${r.verb} (from)`),
                    " ", displayText(r.other))))
            : null)
      : h("p", { className: "gv-hint" }, "Click a node to see its role and what it connects to. Switch the lens to project the landscape along a dimension. Drag to rearrange, scroll to zoom."));
}
