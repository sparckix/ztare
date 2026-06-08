import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
const KIND_COLORS = {
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
export function ReferenceGraphView({ data }) {
    const containerRef = useRef(null);
    const networkRef = useRef(null);
    const [minInDeg, setMinInDeg] = useState(2);
    const [kindFilter, setKindFilter] = useState("");
    const [minWeek, setMinWeek] = useState("");
    const [showEdges, setShowEdges] = useState(true);
    const [selected, setSelected] = useState(null);
    const { referenceGraph } = data;
    const allNodes = referenceGraph?.nodes || [];
    const allEdges = referenceGraph?.edges || [];
    const kinds = Array.from(new Set(allNodes.map((n) => n.kind))).sort();
    useEffect(() => {
        if (!referenceGraph || !containerRef.current || !window.vis)
            return;
        const visible = allNodes.filter((n) => {
            if ((n.in_degree || 0) < minInDeg)
                return false;
            if (kindFilter && n.kind !== kindFilter)
                return false;
            if (minWeek && n.week < minWeek)
                return false;
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
        if (networkRef.current)
            networkRef.current.destroy();
        networkRef.current = new window.vis.Network(containerRef.current, { nodes: new window.vis.DataSet(visNodes), edges: new window.vis.DataSet(visEdges) }, {
            nodes: { shape: "dot", scaling: { min: 4, max: 90, label: { enabled: true, min: 9, max: 18 } } },
            edges: { smooth: { type: "continuous" } },
            physics: {
                stabilization: { iterations: 200 },
                solver: "forceAtlas2Based",
                forceAtlas2Based: { gravitationalConstant: -50, springLength: 100, springConstant: 0.08 },
            },
            interaction: { hover: true, tooltipDelay: 200 },
        });
        networkRef.current.on("click", (params) => {
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
        return _jsx("div", { className: "error", children: "Reference graph not available \u2014 run mine_reference_graph.py first" });
    }
    const cites = selected ? allEdges.filter((e) => e.from === selected.id).map((e) => e.to) : [];
    const citers = selected ? allEdges.filter((e) => e.to === selected.id).map((e) => e.from) : [];
    // Cross-week edges where a later artifact references an earlier one —
    // i.e. newer work building on older work. Derived from weekly_stats so
    // the caption number stays in sync with the data instead of drifting.
    const weeklyStats = referenceGraph.weekly_stats || {};
    const compoundingEdges = Object.values(weeklyStats).reduce((sum, w) => sum + (w.n_outbound_to_earlier_weeks || 0), 0);
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "methodology", children: [_jsx("h3", { children: "Reference Graph \u2014 what you're looking at" }), _jsx("p", { children: "A directed citation graph of the apparatus. Each node is a markdown artifact (seam, paper, project workspace doc, evidence file). Each edge points from a citer to what it cites." }), _jsxs("p", { children: [_jsx("strong", { children: "How edges are extracted:" }), " regex over markdown text matches", " ", _jsx("code", { children: "GP-NNN" }), " identifiers (resolved to the seam file with that GP number) and file-path references (e.g. ", _jsx("code", { children: "src/ztare/gates/cage.py" }), ",", " ", _jsx("code", { children: "docs/concepts/architecture.md" }), "). Edges are deduplicated and weighted by reference count."] }), _jsxs("p", { children: [_jsx("strong", { children: "Node size = in-degree" }), " (how many other artifacts cite it). Big nodes = heavily-cited infrastructure. Try filtering", " ", _jsx("code", { children: "kind = seam_engine" }), " with", " ", _jsx("code", { children: "min in-degree = 5" }), " to see the apparatus's structural backbone. Click any node to see its citers and what it cites."] }), _jsxs("p", { children: [_jsx("strong", { children: "Why this exists:" }), " per-artifact taste rating treats each file as an island. The graph instead asks whether newer work becomes depended-on downstream \u2014 something per-artifact metrics can't show. Here ", compoundingEdges.toLocaleString(), " cross-week reference", compoundingEdges === 1 ? "" : "s", " ", "point from a later artifact back to an earlier one; that count is a rough proxy for build-on-prior-work, not a claim about why. Aggregate stats live in panel 4 of the Trajectory tab."] })] }), _jsxs("div", { className: "controls", children: [_jsxs("span", { style: { fontSize: 13, color: "#666" }, children: [referenceGraph.n_nodes.toLocaleString(), " nodes / ", referenceGraph.n_edges.toLocaleString(), " edges"] }), _jsxs("label", { children: ["Min in-degree: ", _jsx("input", { type: "number", min: "0", value: minInDeg, onChange: (e) => setMinInDeg(parseInt(e.target.value) || 0), style: { width: 60 } })] }), _jsxs("label", { children: ["Kind:", _jsxs("select", { value: kindFilter, onChange: (e) => setKindFilter(e.target.value), children: [_jsx("option", { value: "", children: "all" }), kinds.map((k) => _jsx("option", { value: k, children: k }, k))] })] }), _jsxs("label", { children: ["Week \u2265: ", _jsx("input", { type: "text", value: minWeek, onChange: (e) => setMinWeek(e.target.value), placeholder: "2026-04-01", style: { width: 110 } })] }), _jsxs("label", { children: [_jsx("input", { type: "checkbox", checked: showEdges, onChange: (e) => setShowEdges(e.target.checked) }), " show edges"] })] }), _jsx("div", { className: "legend-strip", children: kinds.map((k) => (_jsxs("span", { className: "legend-item", children: [_jsx("span", { className: "legend-swatch", style: { background: KIND_COLORS[k] || "#ccc" } }), k] }, k))) }), _jsx("div", { id: "network-canvas", ref: containerRef }), _jsx("div", { className: "details-panel", children: selected ? (_jsxs(_Fragment, { children: [_jsx("h3", { style: { margin: "0 0 6px 0", fontSize: 14 }, children: _jsx("code", { children: selected.id }) }), _jsxs("div", { children: ["kind: ", _jsx("strong", { children: selected.kind }), " \u00B7 week: ", _jsx("strong", { children: selected.week }), " \u00B7 in: ", _jsx("strong", { children: selected.in_degree || 0 }), " \u00B7 out: ", _jsx("strong", { children: selected.out_degree || 0 })] }), _jsxs("div", { style: { display: "flex", gap: 24, marginTop: 8 }, children: [_jsxs("div", { style: { flex: 1 }, children: [_jsxs("strong", { children: ["Cited by (", citers.length, "):"] }), _jsx("ul", { children: citers.slice(0, 15).map((c) => _jsx("li", { children: _jsx("code", { children: c }) }, c)) })] }), _jsxs("div", { style: { flex: 1 }, children: [_jsxs("strong", { children: ["Cites (", cites.length, "):"] }), _jsx("ul", { children: cites.slice(0, 15).map((c) => _jsx("li", { children: _jsx("code", { children: c }) }, c)) })] })] })] })) : (_jsx("em", { children: "Click a node to see its citers / cited." })) })] }));
}
