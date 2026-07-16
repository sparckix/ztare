import React from "react";
import ReactFlow, { Background, Controls, Handle, Position, MarkerType } from "reactflow";
import "reactflow/dist/style.css";
import { Maximize2, Minimize2, RefreshCw, Search, X } from "lucide-react";
import { displayMessage, displayText, Block, Tag, FactRow, EmptyState, StatusLine } from "../design-system.js";
import { governedMapReady, meaningfulRests } from "./decisionpanel.jsx";
import { decisionTestContext } from "./wagerpanel.jsx";
import { interpretMapQuestion, layeredLayout, looksLikeMapQuestion } from "./researchgraphmodel.js";

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
  REPORTS: { color: "var(--gv-grey)", verb: "reports", weight: 1.0 },
  SUPPORTS: { color: "var(--ready)", verb: "supports", weight: 1.4 },
  DERIVES: { color: "var(--ready)", verb: "derives from", weight: 1.2 },
  TESTS: { color: "var(--accent)", verb: "tests", weight: 1.2 },
  CONSTRAINS: { color: "var(--gv-purple)", verb: "constrains", weight: 1.2 },
  CHALLENGES: { color: "var(--attention)", verb: "challenges", weight: 1.6 },
  FALSIFIES: { color: "var(--danger)", verb: "could falsify", weight: 1.8 },
};
function relStyle(rel) { return REL_STYLE[rel] || { color: "var(--gv-edge-default)", verb: String(rel || "links").toLowerCase(), weight: 1.2 }; }

// Argument-kernel verdict overlay. The compiled crisp status leads; older graded values stay readable for
// payload compatibility without becoming a second decision.
const ARGUMENT_STYLE = {
  CONTESTED: { color: "var(--gv-amber)", bg: "rgba(146,64,14,0.07)" },
  REFUTED: { color: "var(--danger)", bg: "rgba(224,49,49,0.07)" },
  UNSUPPORTED: { color: "var(--gv-grey)", bg: "rgba(134,142,150,0.09)" },
  NONCONVERGENT: { color: "var(--gv-grey)", bg: "rgba(134,142,150,0.09)" },
  SUPPORTED: { color: "var(--ready)", bg: "rgba(47,158,68,0.07)" },
  BLOCKED: { color: "var(--attention)", bg: "rgba(198,93,9,0.07)" },
};
const ARGUMENT_WORD = {
  CONTESTED: "Contested", REFUTED: "Refuted", UNSUPPORTED: "Unsupported", NONCONVERGENT: "Unresolved",
  SUPPORTED: "Supported", BLOCKED: "Blocked",
};

// Backing glyph — a node's `profile` is the backing strength at each tier, hardest to flimsiest
// (proven, reproducible, cited, unchecked). Drawn bottom-to-top, darkest-at-bottom, so a "castle of citations"
// ([0,0,0.97,0.97]) reads instantly as hollow bedrock/rock with solid soil/snow on top — no hard footing
// underneath. Fill opacity ∝ strength; a 0 band is empty (outline only), a ~1 band reads solid. Absent/short
// profile → null (older payloads render with no glyph at all).
const STRATA_COLORS = ["var(--gv-strata-0)", "var(--gv-strata-1)", "var(--gv-strata-2)", "var(--gv-strata-3)"]; // proven (bedrock) .. unchecked (snow), dark → pale
const STRATA_LABELS = ["proven", "reproducible", "cited", "unchecked"];
const TRUST_VIEWS = [
  { key: "cited", label: "Cited", waterline: 2, lens: "all", title: "Show the whole landscape backed by cited or stronger support" },
  { key: "skeptic", label: "Skeptic", waterline: 2, lens: "break", title: "Inspect falsifiers, tensions, and rejected paths at cited or stronger support" },
  { key: "recompute", label: "Reproducible", waterline: 1, lens: "all", title: "Keep only re-executable or proven support" },
  { key: "proven", label: "Proven only", waterline: 0, lens: "all", title: "Keep only kernel-certified support" },
];
const STRATA_W = 10, STRATA_H = 28, STRATA_ROW_H = STRATA_H / 4;
function strataGlyph(profile) {
  if (!Array.isArray(profile) || profile.length < 4) return null;
  const bands = [0, 1, 2, 3].map((i) => {
    const v = Number(profile[i]);
    return Number.isFinite(v) ? Math.max(0, Math.min(1, v)) : 0;
  });
  return h("svg", {
    width: STRATA_W, height: STRATA_H, viewBox: `0 0 ${STRATA_W} ${STRATA_H}`,
    style: { flex: "none" }, title: "backing, bottom→top: proven · reproducible · cited · unchecked",
  }, bands.map((v, i) => h("rect", {
    key: i, x: 0, y: STRATA_H - (i + 1) * STRATA_ROW_H, width: STRATA_W, height: STRATA_ROW_H,
    fill: STRATA_COLORS[i], fillOpacity: v, stroke: "rgba(31,34,51,0.2)", strokeWidth: 0.5,
  })));
}

// Waterline scrub — the selected stratum (0=kernel..3=proposed) drives node opacity: profile[stratum] near
// zero sinks a node toward transparent, a kernel-hard node stays a solid "island". Stratum 3 (proposed) is
// the default "trust everything" position and is defined as a no-op, so today's rendering is unchanged
// until the user actually raises the waterline. Undefined-safe: no profile → always full opacity.
function waterlineOpacityFor(stratum, profile) {
  if (stratum === 3 || !Array.isArray(profile)) return 1;
  const v = Number(profile[stratum]);
  return Number.isFinite(v) ? 0.08 + 0.92 * Math.max(0, Math.min(1, v)) : 1;
}

const WARRANT_RANK = { W3: 0, W2: 1, W1: 2, W0: 3 };
function edgeClearsWaterline(stratum, edge) {
  return (WARRANT_RANK[edge.warrant || "W3"] || 0) >= (3 - stratum);
}

// Node glass box — "why should I trust this, and what would change it?" Backing tier is the strongest
// tier the strata profile actually clears (proven > reproducible > cited), falling back to "unchecked".
// Same profile the glyph already draws — this just names it in words for the FactRow.
const TIER_TONE = ["ok", "ok", "neutral", "warn"]; // proven, reproducible, cited, unchecked
function backingTier(profile) {
  if (!Array.isArray(profile) || !profile.length) return null;
  for (let i = 0; i < 3; i++) if (Number(profile[i]) >= 0.5) return i;
  return 3;
}

// A sourced node's citation comes only from a REPORTS provenance edge. A provenance edge must never be
// treated as support merely because its origin is a source node.
// A node whose own id IS a source (id starts with "src:") is its own citation.
function sourceNodeFor(node, allNodes, allEdges) {
  if (!node) return null;
  if (String(node.id).startsWith("src:")) return node;
  const inbound = allEdges.filter((e) => e.to === node.id && e.relation === "REPORTS");
  for (const e of inbound) {
    const from = allNodes.find((n) => n.id === e.from);
    if (from && String(from.id).startsWith("src:")) return from;
  }
  return null;
}

// "What it rests on" — the thesis-level Shapley contributors from `GET /api/scenario-strength`. The kernel
// computes this ONLY for the thesis as a whole (no per-claim/per-node breakdown exists yet) — so a claim or
// evidence node gets an honest note instead of a fabricated number.
function RestsOnBlock({ sel, decisionResult, labelById }) {
  if (sel.type !== "thesis") {
    return h(Block, { title: "What it rests on" },
      h(EmptyState, { text: "Contribution ranking is computed for the thesis as a whole, not per node yet — select the thesis to see it." }));
  }
  // Not ready → hide rather than show a dead "bind evidence" promise (Priority 2). The Verdict screen
  // already carries the one honest "not connected yet" line for this project; this block just disappears.
  if (!governedMapReady(decisionResult)) return null;
  const rests = meaningfulRests(decisionResult);
  if (!rests.length) return null;
  const textOf = (decisionResult && decisionResult.text_of) || {};
  const positiveTotal = rests.reduce((sum, pair) => sum + Math.max(0, Number(pair && pair[1]) || 0), 0);
  return h(Block, { title: "Evidence carrying the decision", lead: "The sources whose removal would most change the current backing." },
    h("ul", { className: "decision-restson" },
      rests.slice(0, 5).map((pair, i) => {
        const sid = (pair && pair[0]) != null ? pair[0] : "";
        const c = Number(pair && pair[1]) || 0;
        const share = c > 0 && positiveTotal > 0 ? Math.round((c / positiveTotal) * 100) : 0;
        return h("li", { key: sid || i },
          h("div", { className: "decision-contributor-head" },
            h("span", null, displayText(textOf[sid] || labelById[sid] || sid)
              .replace(/\s*\(source evidence\)\s*$/i, "").replace(/\s+/g, " ").trim()),
            h("strong", { className: c < 0 ? "is-negative" : "" }, c < 0 ? "weakens" : `${share}%`)),
          c > 0 ? h("div", { className: "meter", "aria-hidden": "true" },
            h("div", { className: "meter-fill accent", style: { width: `${share}%` } })) : null);
      })));
}

// "What would flip it" — the minimal core(s) this node sits in (`argument.cores`, kernel-computed) + the
// cheapest open test that targets it (`GET /api/scenario-next-agenda`, matched by `claim_ref`). Both read
// straight off the payload, never derived or guessed.
function WhatWouldFlipBlock({ sel, argument, agendaRows, labelById }) {
  const cores = (argument && Array.isArray(argument.cores)) ? argument.cores : [];
  const myCores = cores.filter((core) => Array.isArray(core) && core.includes(sel.id));
  const isHinge = Boolean(argument && argument.hinge === sel.id);
  const agendaRow = (agendaRows || []).find((r) => r && r.claim_ref === sel.id);
  if (!myCores.length && !isHinge && !agendaRow) {
    return h(Block, { title: "What would flip it" },
      h(EmptyState, { text: "No minimal core or open test is recorded against this node yet." }));
  }
  return h(Block, { title: "What would flip it" },
    isHinge
      ? h("p", { className: "gv-flip-note" }, h(Tag, { tone: "accent" }, "decision hinge"), " — settling this alone could flip the verdict.")
      : null,
    myCores.slice(0, 3).map((core, i) => h("p", { key: i, className: "gv-flip-note" },
      "Sits in a minimal core with ",
      core.filter((id) => id !== sel.id).map((id) => displayText(labelById[id] || id)).join(", ") || "no other open node",
      ".")),
    agendaRow
      ? h("p", {
          className: "gv-flip-note",
          title: `Expected information gain if this test runs: ${(Number(agendaRow.bits) || 0).toFixed(2)} bits (Shannon information)`,
        },
          h("strong", null, "Cheapest test: "), displayText(agendaRow.test),
          ` — ranked #${agendaRow.rank || "—"} for settling this`,
          agendaRow.cost != null ? ` · cost ${agendaRow.cost}` : " · cost not declared",
          agendaRow.flips_crisp ? " (could flip the verdict)" : "")
      : null);
}

// The glass box itself — backing tier + provenance (always, once the argument kernel has run) plus the two
// sub-blocks above. Absent `argument` (no governed map yet, or an older payload) → render nothing extra, so
// the plain detail panel below is today's unchanged behaviour.
function TrustBox({ sel, argument, decisionResult, agendaRows, allNodes, allEdges, labelById }) {
  if (!argument) return null;
  const tier = backingTier(sel.profile);
  const src = sel.provenance === "sourced" ? sourceNodeFor(sel, allNodes, allEdges) : null;
  return h(Block, { title: "Why trust this", lead: "Computed from the recorded evidence and relations, not a model judgment." },
    h(FactRow, { label: "Backing" },
      tier == null
        ? h(StatusLine, { tone: "neutral" }, "not graded")
        : h(StatusLine, { tone: TIER_TONE[tier] }, displayText(STRATA_LABELS[tier]))),
    h(FactRow, { label: "Provenance" },
      sel.provenance === "sourced"
        ? (src && src.id !== sel.id ? `Sourced — ${displayText(src.label || src.id)}` : "Sourced — traces to an original file")
        : sel.provenance === "llm" ? "AI-drafted — wording not independently checked" : "Not recorded"),
    h(RestsOnBlock, { sel, decisionResult, labelById }),
    h(WhatWouldFlipBlock, { sel, argument, agendaRows, labelById }));
}

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

// One re-fit config shared by every re-fit trigger below (init, projection change, container resize) —
// reactflow v11's `fitView:true` only fires once, on init, so lens/facet/search re-projecting the graph or
// the canvas resizing (sidebar collapse, window resize) left the view stale until now.
const FIT = { padding: 0.15, maxZoom: 1.1, duration: 300 };

// Decision overlay, inline-only (no CSS file touched): hinge/in_core draw one ring colour at two
// intensities (hinge = the single decision-critical node, strongest; in_core = lighter, "turns on this too").
// Chained with the selected ring (box-shadow supports multiple layers) so clicking a hinge node doesn't
// lose either. untested/contradicted only touch border-style / one edge, so they never fight the
// existing tone border-colour. All undefined on older payloads → no style object → pure fallback.
function overlayStyle(data) {
  const ring = data.hinge ? "0 0 0 3px rgba(66,99,235,0.55)" : data.inCore ? "0 0 0 2px rgba(66,99,235,0.28)" : null;
  const style = {};
  if (ring) style.boxShadow = data.selected ? `${ring}, 0 0 0 2px var(--accent)` : ring;
  if (data.untested) style.borderStyle = "dashed";                          // not yet grounded — neutral, not an error
  if (data.contradicted) { style.borderLeftWidth = "3px"; style.borderLeftColor = "var(--danger)"; }
  return Object.keys(style).length ? style : undefined;
}

function MapNode({ data }) {
  const cls = `gv-node tone-${data.tone} ${data.big ? "gv-node-big" : ""} ${data.faded ? "gv-node-faded" : ""} ${data.dim ? "gv-node-dim" : ""} ${data.selected ? "selected" : ""} ${data.flip ? "gv-node-flip" : ""}`;
  const style = overlayStyle(data) || {};
  if (typeof data.waterlineOpacity === "number" && data.waterlineOpacity < 1) style.opacity = data.waterlineOpacity;
  const glyph = strataGlyph(data.profile);
  return h("div", { className: cls, style: Object.keys(style).length ? style : undefined },
    h(Handle, { type: "target", position: Position.Left, isConnectable: false }),
    glyph
      ? h("div", { key: "gv-row", style: { display: "flex", alignItems: "flex-start", gap: "6px" } },
          h("div", { key: "gv-txt", style: { display: "flex", flexDirection: "column", gap: "3px", minWidth: 0 } },
            h("span", { className: "gv-node-label" }, displayText(data.label)),
            data.sub ? h("span", { className: "gv-node-sub" }, data.sub) : null),
          glyph)
      : [
          h("span", { key: "gv-label", className: "gv-node-label" }, displayText(data.label)),
          data.sub ? h("span", { key: "gv-sub", className: "gv-node-sub" }, data.sub) : null,
        ],
    h(Handle, { type: "source", position: Position.Right, isConnectable: false }));
}
const NODE_TYPES = { map: MapNode };

// GraphView — the traversable research-landscape graph with selectable lenses (projections). Click a
// node to interrogate it; switch the lens to project along a dimension. Fed by the typed projection.
export function GraphView({
  nodes, edges, truncated, argument, focusId, onFocusHandled,
  project, liveMode, decision, onDecisionRefresh, agenda, onAgendaRefresh, wagers, onWagersRefresh,
  onRefresh, onOpenDetail,
  onPrefillDecisionTest, onExecuteDecisionTest,
}) {
  const [selected, setSelected] = useState(null);
  const [hovered, setHovered] = useState(null);
  const [lens, setLens] = useState("all");
  const rfRef = useRef(null);
  const canvasRef = useRef(null);
  const [queryInput, setQueryInput] = useState("");
  const [keywordQuery, setKeywordQuery] = useState("");
  const [queryAnswer, setQueryAnswer] = useState(null);
  const [queryResultIds, setQueryResultIds] = useState(null);
  const [queryRunning, setQueryRunning] = useState(false);
  const [preds, setPreds] = useState([]);          // predicate facets (relations to keep; empty = all)
  const [showTriples, setShowTriples] = useState(false);
  const [waterline, setWaterline] = useState(2);   // cited support is the useful default; unchecked remains reachable via the scrubber
  const [refreshing, setRefreshing] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const allNodes = Array.isArray(nodes) ? nodes : [];
  const allEdges = Array.isArray(edges) ? edges : [];
  const labelById = useMemo(() => {
    const m = {}; allNodes.forEach((n) => { m[n.id] = n.label || n.id; }); return m;
  }, [allNodes]);
  // The glass-box data the node detail panel needs (Shapley contributors + the ranked test agenda) —
  // fetched once per project, same lazy-load convention as the Decision panel / Open points.
  const canRun = liveMode && !!project;
  useEffect(() => { if (canRun && !decision && onDecisionRefresh) onDecisionRefresh(); }, [project, liveMode]); // eslint-disable-line
  useEffect(() => { if (canRun && !agenda && onAgendaRefresh) onAgendaRefresh(); }, [project, liveMode]); // eslint-disable-line
  useEffect(() => { if (canRun && !wagers && onWagersRefresh) onWagersRefresh(); }, [project, liveMode]); // eslint-disable-line
  const decisionResult = (decision && decision.result) || null;
  const agendaRows = (agenda && agenda.result && agenda.result.agenda) || [];
  const doRefresh = () => {
    if (!onRefresh || refreshing) return;
    setRefreshing(true);
    Promise.resolve(onRefresh()).finally(() => setRefreshing(false));
  };

  // Recompile animation — one restrained flash when a node's backing tier (or the thesis's verdict) moves,
  // so the user SEES the decision shift instead of just re-reading numbers. Value-keyed (not reference-keyed)
  // so it never fires on an unrelated re-render — only when the actual tier/verdict content changes. This
  // doubles as the "prev vs next compare" the map itself owns (no upstream refresh signal to piggyback on).
  const prevGradeRef = useRef(null);
  const flipTimer = useRef(null);
  const [justChanged, setJustChanged] = useState(() => new Set());
  useEffect(() => {
    const tiers = {};
    allNodes.forEach((n) => { tiers[n.id] = backingTier(n.profile); });
    const verdict = argument && argument.verdict;
    const prev = prevGradeRef.current;
    if (prev) {
      const changed = new Set();
      Object.keys(tiers).forEach((id) => { if (id in prev.tiers && prev.tiers[id] !== tiers[id]) changed.add(id); });
      if ("verdict" in prev && prev.verdict !== verdict) {
        const thesisNode = allNodes.find((n) => n.type === "thesis");
        if (thesisNode) changed.add(thesisNode.id);
      }
      if (changed.size) {
        setJustChanged(changed);
        // Force the highlighted paint to land on screen (rAF), then drop the class next frame — the base
        // `.gv-node` transition takes it from there and eases the highlight back OUT over ~400ms.
        if (flipTimer.current) cancelAnimationFrame(flipTimer.current);
        flipTimer.current = requestAnimationFrame(() => {
          flipTimer.current = requestAnimationFrame(() => setJustChanged(new Set()));
        });
      }
    }
    prevGradeRef.current = { tiers, verdict };
  }, [nodes, argument]);
  useEffect(() => () => { if (flipTimer.current) cancelAnimationFrame(flipTimer.current); }, []);
  // Every predicate present in the graph — the facet vocabulary (no LLM: a controlled query, formally a
  // faceted SPARQL fragment over the subject—predicate—object triples).
  const allPreds = useMemo(() => {
    const seen = []; const set = new Set();
    allEdges.forEach((e) => { const r = e.relation || "LINKS"; if (!set.has(r)) { set.add(r); seen.push(r); } });
    return seen;
  }, [allEdges]);

  const clearQuery = () => {
    setQueryInput("");
    setKeywordQuery("");
    setQueryAnswer(null);
    setQueryResultIds(null);
    setPreds([]);
    setSelected(null);
  };

  const onQueryInputChange = (value) => {
    if (queryAnswer) setPreds([]);
    setQueryInput(value);
    setQueryAnswer(null);
    setQueryResultIds(null);
    setKeywordQuery(looksLikeMapQuestion(value) ? "" : value);
    setSelected(null);
  };

  const runMapQuery = async () => {
    const question = queryInput.trim();
    if (!question || queryRunning) return;
    const parsed = interpretMapQuestion(question, allPreds);
    setLens("all");
    setSelected(null);
    setKeywordQuery(parsed.predicate ? parsed.keyword : (looksLikeMapQuestion(question) ? "" : question));
    if (parsed.predicate) setPreds([parsed.predicate]);
    if (!canRun) return;

    setQueryRunning(true);
    try {
      const response = await fetch(`/api/scenario-map-query?project=${encodeURIComponent(project)}&q=${encodeURIComponent(question)}`,
        { headers: { Accept: "application/json" } });
      const answer = await response.json();
      setQueryAnswer(answer);
      if (answer && answer.ok !== false) {
        const relations = Array.isArray(answer.relations) ? answer.relations : [];
        const resultIds = (answer.results || []).map((row) => row && row.id).filter(Boolean);
        if (relations.length) setPreds(relations);
        setKeywordQuery("");
        if (relations.length && answer.anchor) resultIds.push(answer.anchor);
        setQueryResultIds(resultIds.length ? [...new Set(resultIds)] : null);
      }
    } catch (error) {
      setQueryAnswer({ ok: false, error: String(error) });
    } finally {
      setQueryRunning(false);
    }
  };

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
    const q = keywordQuery.trim().toLowerCase();
    if (q) {
      const hit = new Set(ns.filter((n) => String(n.label || n.id).toLowerCase().includes(q)).map((n) => n.id));
      const near = new Set(hit);
      es.forEach((e) => { if (hit.has(e.from)) near.add(e.to); if (hit.has(e.to)) near.add(e.from); });
      ns = ns.filter((n) => near.has(n.id)); ids = new Set(ns.map((n) => n.id));
      es = es.filter((e) => ids.has(e.from) && ids.has(e.to));
    }
    // A natural-language answer is a graph projection, not a detached list: retain the answer, its anchor,
    // and only the typed links among those nodes.
    if (Array.isArray(queryResultIds)) {
      const resultSet = new Set(queryResultIds);
      ns = ns.filter((n) => resultSet.has(n.id));
      ids = new Set(ns.map((n) => n.id));
      es = es.filter((e) => ids.has(e.from) && ids.has(e.to));
    }
    return { vNodes: ns, vEdges: es };
  }, [allNodes, allEdges, lens, preds, keywordQuery, queryResultIds]);

  const layout = useMemo(() => layeredLayout(vNodes, vEdges), [vNodes, vEdges]);

  // Re-fit whenever the PROJECTION changes (lens/predicate-facet/search narrow or widen the graph) —
  // `fitView:true` below only runs once, at init, so without this a facet change left the view zoomed/panned
  // for the OLD node set. Value-keyed on vNodes.length (not the array reference) so it only fires when the
  // visible set actually changes size, not on every unrelated re-render.
  useEffect(() => {
    const raf = requestAnimationFrame(() => rfRef.current && rfRef.current.fitView(FIT));
    return () => cancelAnimationFrame(raf);
  }, [lens, preds, keywordQuery, queryResultIds, vNodes.length]);

  // Re-fit on container resize (sidebar collapse, window resize, panel toggle) — reactflow has no built-in
  // resize handling; the canvas silently stayed at its old fit otherwise.
  useEffect(() => {
    const el = canvasRef.current;
    if (!el || typeof ResizeObserver === "undefined") return undefined;
    const ro = new ResizeObserver(() => rfRef.current && rfRef.current.fitView(FIT));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!fullscreen) return undefined;
    document.body.classList.add("map-fullscreen");
    const close = (event) => { if (event.key === "Escape") setFullscreen(false); };
    window.addEventListener("keydown", close);
    return () => {
      document.body.classList.remove("map-fullscreen");
      window.removeEventListener("keydown", close);
    };
  }, [fullscreen]);

  // Click-to-focus from the Structural reads: select the node and pan the canvas to it. If it's hidden by
  // the current lens, drop back to "Whole landscape" first (next render brings it into view, effect re-runs).
  useEffect(() => {
    if (!focusId || !rfRef.current) return;
    if (!vNodes.some((n) => n.id === focusId)) {
      setLens("all");
      setPreds([]);
      setKeywordQuery("");
      setQueryInput("");
      setQueryAnswer(null);
      setQueryResultIds(null);
      return;
    }
    const p = layout[focusId];
    setSelected(focusId);
    if (p) rfRef.current.setCenter(p.x + 105, p.y, { zoom: 1.05, duration: 500 });
    if (onFocusHandled) onFocusHandled();
  }, [focusId, vNodes, layout]);

  // Focus+context: hovering a node lights up its 1-hop neighbourhood and dims everything else, so a dense
  // map stays traceable. Pure view state; null = nothing hovered (full opacity).
  const neighbors = useMemo(() => {
    if (!hovered) return null;
    const s = new Set([hovered]);
    vEdges.forEach((e) => { if (e.from === hovered) s.add(e.to); if (e.to === hovered) s.add(e.from); });
    return s;
  }, [hovered, vEdges]);

  const rfNodes = useMemo(() => {
    // Decision overlay per node — hinge/in_core/grounded are undefined on older payloads (no argument
    // kernel run yet), so this degrades to no suffix + no ring, i.e. today's plain rendering.
    return vNodes.map((n) => {
      const suffix = n.hinge ? " · decision hinge" : n.in_core ? " · turns on this" : "";
      return {
        id: n.id, type: "map", position: layout[n.id] || { x: 0, y: 0 },
        data: {
          label: n.label || n.id, sub: subFor(n) + suffix, tone: toneFor(n), selected: selected === n.id,
          big: n.type === "thesis",                                    // the summit
          faded: typeof n.weight === "number" && n.weight < 0.4,       // low-confidence claims recede (lowland)
          dim: neighbors ? !neighbors.has(n.id) : false,               // hover focus+context
          hinge: n.hinge === true, inCore: n.in_core === true,
          untested: n.grounded === "UNTESTED", contradicted: n.grounded === "CONTRADICTED",
          profile: n.profile, waterlineOpacity: waterlineOpacityFor(waterline, n.profile),
          flip: justChanged.has(n.id),                                  // recompile animation, one-shot
        },
      };
    });
  }, [vNodes, selected, neighbors, waterline, justChanged, layout]);

  // Edges coloured by relation (the argument structure), with an arrowhead for direction. Adversarial
  // relations (challenges / falsifies) sit on top, slightly heavier — they're what could break it. On hover,
  // edges touching the hovered node stay lit; the rest recede.
  const rfEdges = useMemo(() => vEdges.map((e, i) => {
    const rs = relStyle(e.relation);
    const adversarial = e.relation === "FALSIFIES" || e.relation === "CHALLENGES";
    const touches = hovered ? (e.from === hovered || e.to === hovered) : true;
    const admitted = edgeClearsWaterline(waterline, e);
    const opacity = admitted ? (hovered ? (touches ? 0.95 : 0.1) : 0.7) : 0.055;
    return {
      id: `e:${e.from}:${e.relation || "LINKS"}:${e.to}:${i}`, source: e.from, target: e.to,
      zIndex: touches && hovered ? 3 : adversarial ? 2 : 1,
      style: {
        stroke: rs.color, strokeWidth: rs.weight, opacity,
        strokeDasharray: e.relation === "REPORTS" ? "3 5" : admitted ? undefined : "2 5",
      },
      markerEnd: { type: MarkerType.ArrowClosed, color: rs.color, width: 14, height: 14 },
    };
  }), [vEdges, hovered, waterline]);
  // Which relations are present in this lens — drives the legend.
  const legend = useMemo(() => {
    const seen = []; const set = new Set();
    vEdges.forEach((e) => { const r = e.relation || "links"; if (!set.has(r)) { set.add(r); seen.push(r); } });
    return seen;
  }, [vEdges]);
  // Any node in this view carries a strata profile → show the glyph legend + the waterline slider is meaningful.
  const hasStrata = useMemo(() => vNodes.some((n) => Array.isArray(n.profile)), [vNodes]);
  const waterlineStats = useMemo(() => ({
    nodes: vNodes.filter((n) => waterlineOpacityFor(waterline, n.profile) > 0.1).length,
    edges: vEdges.filter((e) => edgeClearsWaterline(waterline, e)).length,
  }), [vNodes, vEdges, waterline]);

  if (!allNodes.length) return null;
  const sel = selected ? allNodes.find((n) => n.id === selected) : null;
  const selectedTest = decisionTestContext(agenda, wagers, sel && sel.id);
  const selectedAgenda = selectedTest.row;
  const selectedWager = selectedTest.wager;
  const selectedAction = sel
    ? selectedAgenda
      ? selectedTest.mode === "record"
        ? { label: "Record outcome", run: () => onExecuteDecisionTest && onExecuteDecisionTest(selectedWager) }
        : selectedTest.mode === "define"
          ? { label: "Define this test", run: () => onPrefillDecisionTest && onPrefillDecisionTest(selectedAgenda) }
          : { label: "Review this test", destination: ["review", "Things to review"] }
      : ["gap", "tension", "falsifier", "branch", "candidate"].includes(sel.type)
        ? { label: "Open related questions", destination: ["review", "Things to review"] }
        : sel.type === "evidence" || String(sel.id || "").startsWith("src:")
          ? { label: "Inspect project evidence", destination: ["sources", "Prepare files"] }
          : { label: "Open the checked verdict", destination: ["save", "Report readiness"] }
    : null;
  const selDetail = sel ? String(sel.detail || sel.label || "").split("\n").map((s) => s.trim()).filter(Boolean) : [];
  // The selected node's role in the argument — its typed relations, in plain language.
  const selRels = sel ? allEdges.flatMap((e) => {
    if (e.from === sel.id) return [{ verb: relStyle(e.relation).verb, color: relStyle(e.relation).color, other: labelById[e.to] || e.to, dir: "out" }];
    if (e.to === sel.id) return [{ verb: relStyle(e.relation).verb, color: relStyle(e.relation).color, other: labelById[e.from] || e.from, dir: "in" }];
    return [];
  }) : [];
  const hiddenCount = truncated && typeof truncated === "object"
    ? Object.values(truncated).reduce((a, b) => a + (Number(b) || 0), 0) : 0;

  const togglePred = (r) => {
    setQueryAnswer(null);
    setQueryResultIds(null);
    setPreds((cur) => cur.includes(r) ? cur.filter((x) => x !== r) : [...cur, r]);
  };
  const applyTrustView = (view) => {
    setWaterline(view.waterline);
    setLens(view.lens);
    setPreds([]);
    setSelected(null);
    setQueryAnswer(null);
    setQueryResultIds(null);
  };
  const focusQueryResult = (id) => {
    const point = layout[id];
    setSelected(id);
    if (point && rfRef.current) rfRef.current.setCenter(point.x + 105, point.y, { zoom: 1.05, duration: 400 });
  };
  // The visible triples — subject —predicate→ object — the RDF reading of the current faceted query.
  const triples = vEdges.map((e) => ({ s: labelById[e.from] || e.from, p: relStyle(e.relation).verb, o: labelById[e.to] || e.to, color: relStyle(e.relation).color }));

  const argStyle = argument && argument.verdict ? (ARGUMENT_STYLE[argument.verdict] || ARGUMENT_STYLE.BLOCKED) : null;
  let queryAnswerView = null;
  if (queryAnswer) {
    let content;
    if (queryAnswer.ok === false) {
      content = h("p", null, displayMessage(queryAnswer.error || "The map could not interpret that question."));
    } else {
      const resultRows = (queryAnswer.results || []).map((result) => h("li", { key: result.id },
        h("button", { type: "button", onClick: () => focusQueryResult(result.id) },
          result.relation ? h(Tag, null, relStyle(result.relation).verb) : null,
          h("span", null, displayText(result.label || result.id)))));
      content = h(React.Fragment, null,
        h("p", { className: "gv-query-interpretation" },
          queryAnswer.interpreted_as ? `Read as ${queryAnswer.interpreted_as}` : "No anchor was found in that question."),
        resultRows.length
          ? h("ul", { className: "gv-query-results" }, resultRows)
          : h("p", { className: "gv-query-empty" }, "No matching nodes."));
    }
    queryAnswerView = h("div", {
      className: `gv-query-answer ${queryAnswer.ok === false ? "is-error" : ""}`,
      "aria-live": "polite",
    }, content);
  }

  return h("div", { className: "gv" },
    // Decision banner (optional overlay) — the argument kernel's grounded read of THIS map: supported /
    // blocked / refuted, plus its humane one-line reason. Informational only, not a control.
    argStyle
      ? h("div", {
          className: "gv-verdict",
          style: {
            display: "flex", flexWrap: "wrap", alignItems: "baseline", gap: "0 8px",
            padding: "7px 12px", marginBottom: "8px", borderRadius: "8px", fontSize: "12.5px",
            background: argStyle.bg, borderLeft: `3px solid ${argStyle.color}`,
          },
        },
          h("strong", { style: { color: argStyle.color } }, ARGUMENT_WORD[argument.verdict] || displayText(argument.verdict)),
          argument.reason ? h("span", { style: { color: "var(--muted)" } }, `— ${displayMessage(argument.reason)}`) : null)
      : null,

    // Lens selector — project the landscape along a dimension (node-type facet).
    h("div", { className: "gv-lenses" },
      LENSES.map((l) => h("button", {
        key: l.key, type: "button", className: `gv-lens ${lens === l.key ? "active" : ""}`,
        onClick: () => { setLens(l.key); setSelected(null); },
      }, l.label)),
      // Re-pull the governed map — the node whose backing tier or the thesis's verdict moved gets the
      // one-shot flash (see `justChanged` above) so a recompile is something you SEE, not just re-read.
      onRefresh
        ? h("button", {
            type: "button", className: `chip gv-refresh ${refreshing ? "is-busy" : ""}`,
            style: { marginLeft: "auto" }, disabled: !canRun || refreshing, onClick: doRefresh,
            title: "Re-check the governed map for a moved verdict or backing tier",
          }, h(RefreshCw, { size: 14, "aria-hidden": true }), refreshing ? "Refreshing…" : "Refresh")
        : null),

    // Waterline scrub (optional — only meaningful when nodes carry a strata profile): raise the trust floor
    // from "proposed" toward "kernel" and every node's opacity follows its strength at that tier, so
    // quote-castles visibly sink while kernel-hard nodes stay solid islands. Purely a view, no server call.
    hasStrata
      ? h("div", { className: "gv-trust-stack" },
          h("div", { className: "gv-trust-views", role: "group", "aria-label": "Trust views" },
            TRUST_VIEWS.map((view) => h("button", {
              key: view.key, type: "button",
              className: `gv-trust-view ${waterline === view.waterline && lens === view.lens ? "active" : ""}`,
              title: view.title, onClick: () => applyTrustView(view),
            }, view.label))),
          h("div", { className: "gv-waterline" },
          h("label", { htmlFor: "gv-waterline-range" }, "Trust floor"),
          h("input", {
            id: "gv-waterline-range", type: "range", min: 0, max: 3, step: 1,
            value: 3 - waterline,
            "aria-valuetext": STRATA_LABELS[waterline],
            title: `Fade nodes and links weaker than the "${STRATA_LABELS[waterline]}" tier`,
            onChange: (e) => setWaterline(3 - Number(e.target.value)),
            style: { width: "120px", verticalAlign: "middle" },
          }),
          h("strong", { className: "gv-waterline-tier" }, STRATA_LABELS[waterline]),
          h("span", { className: "gv-waterline-count" },
            `${waterlineStats.nodes}/${vNodes.length} nodes · ${waterlineStats.edges}/${vEdges.length} links remain`)))
      : null,

    // One query surface: simple terms filter immediately; questions are deterministically interpreted by the
    // CLI-master query engine and projected back onto the same graph.
    h("form", { className: "gv-query", onSubmit: (event) => { event.preventDefault(); runMapQuery(); } },
      h("div", { className: "gv-search-shell" },
        h(Search, { size: 16, "aria-hidden": true }),
        h("input", {
          type: "search", className: "gv-search", value: queryInput,
          placeholder: "Search, or ask what supports, threatens, or reports a claim",
          "aria-label": "Search or ask the research map",
          onChange: (event) => onQueryInputChange(event.target.value),
        }),
        queryInput
          ? h("button", { type: "button", className: "gv-query-clear", onClick: clearQuery,
              title: "Clear map query", "aria-label": "Clear map query" },
              h(X, { size: 15, "aria-hidden": true }))
          : null),
      h("button", { type: "submit", className: `chip gv-query-submit ${queryRunning ? "is-busy" : ""}`,
        disabled: !queryInput.trim() || queryRunning }, queryRunning ? "Reading…" : "Ask"),
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

    queryAnswerView,

    // Relation legend — what the edge colours mean (only the ones present in this query).
    legend.length
      ? h("div", { className: "gv-legend" },
          legend.map((r) => h("span", { key: r, className: "gv-legend-item" },
            h("span", { className: "gv-legend-swatch", style: { background: relStyle(r).color } }),
            r === "REPORTS" ? "reports (provenance)" : relStyle(r).verb)))
      : null,

    // Node-level provenance is a state read, not a tutorial paragraph.
    argument && argument.node_provenance && argument.node_provenance.llm > 0
      ? h("div", { className: "gv-provenance", title: "AI-drafted wording is unchecked until it traces to a source." },
          h("span", null, `${argument.node_provenance.llm} AI-drafted`),
          h("span", null, `${argument.node_provenance.sourced} sourced`))
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

    h("div", { className: `gv-canvas ${fullscreen ? "is-fullscreen" : ""}`, ref: canvasRef },
      h("button", {
        type: "button", className: "gv-fullscreen", onClick: () => setFullscreen((value) => !value),
        title: fullscreen ? "Exit full screen" : "View map full screen",
        "aria-label": fullscreen ? "Exit full screen" : "View map full screen",
      }, fullscreen
        ? h(Minimize2, { size: 16, "aria-hidden": true })
        : h(Maximize2, { size: 16, "aria-hidden": true })),
      h(ReactFlow, {
        nodes: rfNodes, edges: rfEdges, nodeTypes: NODE_TYPES,
        onInit: (inst) => { rfRef.current = inst; },
        onNodeClick: (_e, n) => {
          setSelected((cur) => (cur === n.id ? null : n.id));
          const rf = rfRef.current;
          if (rf && n.position) rf.setCenter(n.position.x + 105, n.position.y, { zoom: Math.max(rf.getZoom(), 0.9), duration: 300 });
        },
        onNodeMouseEnter: (_e, n) => setHovered(n.id),
        onNodeMouseLeave: () => setHovered(null),
        onPaneClick: () => setSelected(null),
        fitView: true, fitViewOptions: { padding: 0.16, maxZoom: 1.1 }, proOptions: { hideAttribution: true },
        nodesDraggable: true, nodesConnectable: false, elementsSelectable: true, minZoom: 0.3, maxZoom: 1.8,
      },
        h(Background, { gap: 22, color: "var(--gv-canvas-dot)" }),
        h(Controls, { showInteractive: false })),
      hiddenCount
        ? h("p", { className: "gv-truncated" }, `+${hiddenCount} more node${hiddenCount === 1 ? "" : "s"} not shown (the densest evidence and constraints are summarised to keep the map readable)`)
        : null,
      // The node detail is a FLOATING panel over the canvas (top-right, fixed width, scrolls) — not a
      // full-width block below it (operator: "when u click it expands so badly"). The map stays visible.
      sel
        ? h("div", { className: "gv-detail" },
            h("button", { type: "button", className: "gv-detail-close", title: "Close node details",
                "aria-label": "Close node details", onClick: () => setSelected(null) },
                h(X, { size: 16, "aria-hidden": true })),
            h("span", { className: "eyebrow" }, `${TYPE_KIND[sel.type] || sel.type} · ${displayText(sel.label)}`),
            selDetail.length
              ? h("ul", null, selDetail.map((d, i) => h("li", { key: i }, displayMessage(d))))
              : h("p", { className: "gv-detail-empty" }, "Nothing more recorded for this node."),
            // The glass box — why trust this node, and what would change it. Null on an older payload.
            h(TrustBox, { sel, argument, decisionResult, agendaRows, allNodes, allEdges, labelById }),
            // The node's role in the argument — its typed relations (an incoming edge reads "← verb").
            selRels.length
              ? h("div", { className: "gv-detail-rels" },
                  selRels.slice(0, 8).map((r, i) =>
                    h("span", { key: i, className: "gv-rel" },
                      h("span", { className: "gv-rel-verb", style: { color: r.color } }, r.dir === "out" ? r.verb : `← ${r.verb}`),
                      " ", displayText(r.other))))
              : null,
            selectedAction && (selectedAction.run || onOpenDetail)
              ? h("div", { className: "gv-detail-actions" },
                  h("button", { type: "button", className: "chip primary",
                    onClick: () => selectedAction.run
                      ? selectedAction.run()
                      : onOpenDetail(selectedAction.destination[0], selectedAction.destination[1]) },
                    selectedAction.label))
              : null)
        : null));
}
