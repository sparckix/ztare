import { useEffect, useRef, useState } from "react";
import type { DashboardData } from "../lib/data";
import type { GraphNode } from "../lib/types";

const KIND_COLORS: Record<string, string> = {
  seam_reflexive: "#9467bd",
  seam_engine: "#1f77b4",
  seam_apparatus: "#17becf",
  seam_other: "#aec7e8",
  evidence: "#ff7f0e",
  philosophy: "#bcbd22",
  paper: "#d62728",
  project: "#2ca02c",
  doc: "#8c564b",
  org: "#e377c2",
  script: "#7f7f7f",
  src: "#666",
  spec: "#fdae61",
  analytics: "#a6cee3",
  other: "#cccccc",
};

export function ReferenceGraphView({ data }: { data: DashboardData }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<any>(null);
  const [minInDeg, setMinInDeg] = useState(2);
  const [kindFilter, setKindFilter] = useState("");
  const [minWeek, setMinWeek] = useState("");
  const [showEdges, setShowEdges] = useState(true);
  const [selected, setSelected] = useState<GraphNode | null>(null);

  const { referenceGraph } = data;

  const allNodes = referenceGraph?.nodes || [];
  const allEdges = referenceGraph?.edges || [];

  const kinds = Array.from(new Set(allNodes.map((n) => n.kind))).sort();

  useEffect(() => {
    if (!referenceGraph || !containerRef.current || !window.vis) return;

    const visible = allNodes.filter((n) => {
      if ((n.in_degree || 0) < minInDeg) return false;
      if (kindFilter && n.kind !== kindFilter) return false;
      if (minWeek && n.week < minWeek) return false;
      return true;
    });
    const visibleSet = new Set(visible.map((n) => n.id));

    // Sqrt-scaled node size so heavy hubs (GP-023 at 460 cites,
    // GP-163d at 391, etc.) are visibly distinct from medium hubs
    // and small nodes. Linear scaling would make small nodes
    // invisible; raw in_degree caps at the same upper bound.
    // sqrt(in_degree+1) gives ~21× ratio between top hub and floor.
    const maxInDeg = Math.max(...visible.map((n) => n.in_degree || 0), 1);
    const sqrtMax = Math.sqrt(maxInDeg + 1);
    const visNodes = visible.map((n) => {
      const inDeg = n.in_degree || 0;
      const sqrtVal = Math.sqrt(inDeg + 1);
      // Show label when node is in the top 30% by in-degree
      // (proportional to sqrtMax).  Other nodes get hover-only label.
      const isHub = sqrtVal >= sqrtMax * 0.45;
      return {
        id: n.id,
        label: isHub ? n.id.split("/").slice(-2).join("/").replace(/\.md$/, "") : "",
        title: `${n.id}\nkind: ${n.kind}\nweek: ${n.week}\nin: ${inDeg}, out: ${n.out_degree || 0}`,
        color: KIND_COLORS[n.kind] || "#ccc",
        value: sqrtVal,
        font: { size: isHub ? 13 : 9, color: "#cfd4da",
                strokeWidth: 3, strokeColor: "#0b0c0e" },
      };
    });
    const visEdges = showEdges
      ? allEdges
          .filter((e) => visibleSet.has(e.from) && visibleSet.has(e.to))
          .map((e) => ({
            from: e.from,
            to: e.to,
            arrows: "to",
            color: { color: "rgba(120,120,120,0.3)" },
            width: Math.min(4, e.weight),
          }))
      : [];

    if (networkRef.current) networkRef.current.destroy();
    networkRef.current = new window.vis.Network(
      containerRef.current,
      { nodes: new window.vis.DataSet(visNodes), edges: new window.vis.DataSet(visEdges) },
      {
        nodes: { shape: "dot", scaling: { min: 4, max: 90, label: { enabled: true, min: 9, max: 18 } } },
        edges: { smooth: { type: "continuous" } },
        physics: {
          stabilization: { iterations: 200 },
          solver: "forceAtlas2Based",
          forceAtlas2Based: { gravitationalConstant: -50, springLength: 100, springConstant: 0.08 },
        },
        interaction: { hover: true, tooltipDelay: 200 },
      }
    );
    networkRef.current.on("click", (params: any) => {
      if (params.nodes.length === 0) {
        setSelected(null);
        return;
      }
      const nid = params.nodes[0];
      const n = allNodes.find((x) => x.id === nid);
      setSelected(n || null);
    });
  }, [referenceGraph, minInDeg, kindFilter, minWeek, showEdges, allNodes, allEdges]);

  if (!referenceGraph) {
    return <div className="error">Reference graph not available — run mine_reference_graph.py first</div>;
  }

  const cites = selected ? allEdges.filter((e) => e.from === selected.id).map((e) => e.to) : [];
  const citers = selected ? allEdges.filter((e) => e.to === selected.id).map((e) => e.from) : [];

  return (
    <>
      <div className="methodology">
        <h3>Reference Graph — what you're looking at</h3>
        <p>
          A directed citation graph of the apparatus. Each node is a markdown
          artifact (seam, paper, project workspace doc, evidence file).
          Each edge points from a citer to what it cites.
        </p>
        <p>
          <strong>How edges are extracted:</strong> regex over markdown text matches{" "}
          <code>GP-NNN</code> identifiers (resolved to the seam file with that GP number)
          and file-path references (e.g. <code>src/ztare/gates/cage.py</code>,{" "}
          <code>docs/concepts/architecture.md</code>).
          Edges are deduplicated and weighted by reference count.
        </p>
        <p>
          <strong>Node size = in-degree</strong> (how many other artifacts cite it).
          Big nodes = heavily-cited infrastructure. Try filtering{" "}
          <code>kind = seam_engine</code> with{" "}
          <code>min in-degree = 5</code> to see the apparatus's structural backbone.
          Click any node to see its citers and what it cites.
        </p>
        <p>
          <strong>Why this exists:</strong> per-artifact taste rating treats each file
          as an island. The graph measures cross-artifact compounding — does
          newer work build on older work? That's the recursive-self-improvement
          signature you can't see from per-artifact metrics alone. Aggregate
          stats live in panel 4 of the Trajectory tab.
        </p>
      </div>

      <div className="controls">
        <span style={{ fontSize: 13, color: "#666" }}>
          {referenceGraph.n_nodes.toLocaleString()} nodes / {referenceGraph.n_edges.toLocaleString()} edges
        </span>
        <label>Min in-degree: <input type="number" min="0" value={minInDeg} onChange={(e) => setMinInDeg(parseInt(e.target.value) || 0)} style={{ width: 60 }} /></label>
        <label>Kind:
          <select value={kindFilter} onChange={(e) => setKindFilter(e.target.value)}>
            <option value="">all</option>
            {kinds.map((k) => <option key={k} value={k}>{k}</option>)}
          </select>
        </label>
        <label>Week ≥: <input type="text" value={minWeek} onChange={(e) => setMinWeek(e.target.value)} placeholder="2026-04-01" style={{ width: 110 }} /></label>
        <label><input type="checkbox" checked={showEdges} onChange={(e) => setShowEdges(e.target.checked)} /> show edges</label>
      </div>

      <div className="legend-strip">
        {kinds.map((k) => (
          <span key={k} className="legend-item">
            <span className="legend-swatch" style={{ background: KIND_COLORS[k] || "#ccc" }} />
            {k}
          </span>
        ))}
      </div>

      <div id="network-canvas" ref={containerRef} />

      <div className="details-panel">
        {selected ? (
          <>
            <h3 style={{ margin: "0 0 6px 0", fontSize: 14 }}><code>{selected.id}</code></h3>
            <div>kind: <strong>{selected.kind}</strong> · week: <strong>{selected.week}</strong> · in: <strong>{selected.in_degree || 0}</strong> · out: <strong>{selected.out_degree || 0}</strong></div>
            <div style={{ display: "flex", gap: 24, marginTop: 8 }}>
              <div style={{ flex: 1 }}>
                <strong>Cited by ({citers.length}):</strong>
                <ul>{citers.slice(0, 15).map((c) => <li key={c}><code>{c}</code></li>)}</ul>
              </div>
              <div style={{ flex: 1 }}>
                <strong>Cites ({cites.length}):</strong>
                <ul>{cites.slice(0, 15).map((c) => <li key={c}><code>{c}</code></li>)}</ul>
              </div>
            </div>
          </>
        ) : (
          <em>Click a node to see its citers / cited.</em>
        )}
      </div>
    </>
  );
}
