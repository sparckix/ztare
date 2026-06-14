import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState, useMemo } from "react";
const CONFIDENCE_ORDER = { high: 0, medium: 1, low: 2 };
const COST_ORDER = { trivial: 0, day: 1, week: 2, month: 3 };
const CONFIDENCE_TAG = {
    high: "tag tag-signal",
    medium: "tag tag-amber",
    low: "tag tag-slate",
};
const COST_TAG = {
    trivial: "tag tag-signal",
    day: "tag tag-amber",
    week: "tag tag-amber",
    month: "tag tag-warn",
};
const MECHANISM_COPY = {
    retire_or_widen_can_handle: {
        title: "Retire or broaden narrow rules",
        detail: "A rule is present but its eligibility predicate appears too narrow. Either delete it if it adds little, or widen the predicate and test that it engages beyond one substrate.",
    },
    wire_one_shot_as_loop: {
        title: "Turn one-off checks into recurring loops",
        detail: "A useful check exists as a manual or one-time artifact. The candidate is to make it part of the recurring apparatus so the same failure cannot reappear quietly.",
    },
    strange_loop_ZTARE_substrate: {
        title: "Measure external research as a substrate",
        detail: "Bring evidence from outside the ZTARE self-evaluation surface back into the apparatus, so external research output can be scored and acted on.",
    },
};
function mechanismTitle(mechanism) {
    return MECHANISM_COPY[mechanism]?.title || mechanism.replace(/_/g, " ");
}
function mechanismDetail(mechanism) {
    return MECHANISM_COPY[mechanism]?.detail || "Candidate family from the upstream miner. Inspect the raw rows before acting.";
}
function compactList(xs, max = 10) {
    const visible = xs.slice(0, max);
    const suffix = xs.length > max ? ` +${xs.length - max} more` : "";
    return visible.join(", ") + suffix;
}
export function RecursiveGainView({ data }) {
    const { recursiveGainCandidates: rg } = data;
    const [confidenceFilter, setConfidenceFilter] = useState("");
    const [mechanismFilter, setMechanismFilter] = useState("");
    const [sourceFilter, setSourceFilter] = useState("");
    const filtered = useMemo(() => {
        if (!rg)
            return [];
        return rg.candidates.filter((c) => {
            if (confidenceFilter && c.confidence !== confidenceFilter)
                return false;
            if (mechanismFilter && c.mechanism !== mechanismFilter)
                return false;
            if (sourceFilter && c.source !== sourceFilter)
                return false;
            return true;
        });
    }, [rg, confidenceFilter, mechanismFilter, sourceFilter]);
    const groups = useMemo(() => {
        const byKey = new Map();
        for (const c of filtered) {
            const key = `${c.mechanism}::${c.source}::${c.confidence}::${c.cost}`;
            const g = byKey.get(key) || {
                key,
                mechanism: c.mechanism,
                source: c.source,
                confidence: c.confidence,
                cost: c.cost,
                count: 0,
                entities: [],
                rows: [],
            };
            g.count += 1;
            if (c.entity && !g.entities.includes(c.entity))
                g.entities.push(c.entity);
            g.rows.push(c);
            byKey.set(key, g);
        }
        return Array.from(byKey.values()).sort((a, b) => (CONFIDENCE_ORDER[a.confidence] ?? 9) - (CONFIDENCE_ORDER[b.confidence] ?? 9)
            || (COST_ORDER[a.cost] ?? 9) - (COST_ORDER[b.cost] ?? 9)
            || b.count - a.count
            || a.mechanism.localeCompare(b.mechanism));
    }, [filtered]);
    if (!rg) {
        return _jsx("div", { className: "error", children: "No recursive-gain candidates \u2014 run mine_recursive_gain_candidates.py first" });
    }
    const mechanisms = Array.from(new Set(rg.candidates.map((c) => c.mechanism))).sort();
    const sources = Array.from(new Set(rg.candidates.map((c) => c.source))).sort();
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "methodology", children: [_jsx("h3", { children: "Recursive-gain backlog" }), _jsx("p", { children: "These are proposed apparatus improvements mined from cross-audit, structural analogy, closure patterns, reference graphs, and process catalogs. They are grouped by action family so repeated rule-level warnings do not dominate the page. A candidate only becomes evidence of gain after an independent ledger shows it was acted on." }), _jsxs("ul", { children: [_jsxs("li", { children: [_jsx("strong", { children: "Action family" }), " \u2014 the recurring improvement pattern."] }), _jsxs("li", { children: [_jsx("strong", { children: "Cost" }), " \u2014 implementation effort estimate (trivial / day / week / month)"] }), _jsxs("li", { children: [_jsx("strong", { children: "Confidence" }), " \u2014 signal strength from the source miner"] }), _jsxs("li", { children: [_jsx("strong", { children: "Source" }), " \u2014 the mining surface that produced the candidate"] })] }), _jsxs("p", { style: { fontSize: 13, color: "#666" }, children: [_jsx("strong", { children: "Honest caveat:" }), " these candidates are only as fresh as their upstream scorecards, and follow-through is measured ", _jsx("em", { children: "exogenously" }), " (a candidate's GP-id appearing in the catch ledger). A high dead-letter rate means the mining is surfacing moves nobody ships \u2014 a signal to read, not to hide. Re-run", " ", _jsx("code", { children: "python scripts/public/mining/mine_recursive_gain_candidates.py" }), " after the upstream miners refresh."] })] }), _jsxs("div", { className: "panel", children: [_jsx("h3", { children: "By the numbers" }), _jsxs("div", { style: { display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }, children: [_jsxs("div", { style: { fontSize: 13 }, children: [_jsx("strong", { children: rg.n_candidates }), " total candidates"] }), Object.entries(rg.by_source).map(([k, v]) => (_jsxs("span", { className: "chip", children: [_jsx("code", { children: k }), ": ", v] }, k)))] })] }), _jsxs("div", { className: "controls", children: [_jsxs("label", { children: ["Confidence:", _jsxs("select", { value: confidenceFilter, onChange: (e) => setConfidenceFilter(e.target.value), children: [_jsx("option", { value: "", children: "all" }), _jsx("option", { value: "high", children: "high" }), _jsx("option", { value: "medium", children: "medium" }), _jsx("option", { value: "low", children: "low" })] })] }), _jsxs("label", { children: ["Mechanism:", _jsxs("select", { value: mechanismFilter, onChange: (e) => setMechanismFilter(e.target.value), children: [_jsx("option", { value: "", children: "all" }), mechanisms.map((m) => _jsx("option", { value: m, children: m }, m))] })] }), _jsxs("label", { children: ["Source:", _jsxs("select", { value: sourceFilter, onChange: (e) => setSourceFilter(e.target.value), children: [_jsx("option", { value: "", children: "all" }), sources.map((s) => _jsx("option", { value: s, children: s }, s))] })] }), _jsxs("span", { style: { marginLeft: 12, fontSize: 12, color: "var(--text-faint)" }, children: [filtered.length, " of ", rg.n_candidates, " shown"] })] }), _jsxs("div", { className: "panel", children: [_jsx("h3", { children: "Grouped actions" }), _jsx("div", { className: "gain-group-list", children: groups.map((g) => (_jsxs("div", { className: "gain-group", children: [_jsxs("div", { className: "gain-group-head", children: [_jsxs("div", { children: [_jsx("div", { className: "gain-group-title", children: mechanismTitle(g.mechanism) }), _jsxs("div", { className: "gain-group-sub", children: [g.count, " row", g.count === 1 ? "" : "s", " from ", _jsx("code", { children: g.source })] })] }), _jsxs("div", { className: "gain-group-tags", children: [_jsx("span", { className: CONFIDENCE_TAG[g.confidence] || "tag tag-slate", children: g.confidence }), _jsx("span", { className: COST_TAG[g.cost] || "tag tag-slate", children: g.cost })] })] }), _jsx("p", { children: mechanismDetail(g.mechanism) }), _jsxs("div", { className: "gain-entities", children: [_jsx("span", { children: "Rows:" }), " ", _jsx("code", { children: compactList(g.entities) })] })] }, g.key))) })] }), _jsxs("details", { className: "details-panel gain-raw", children: [_jsx("summary", { children: "Raw candidate rows" }), _jsxs("table", { children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { style: { width: 90 }, children: "Confidence" }), _jsx("th", { style: { width: 70 }, children: "Cost" }), _jsx("th", { style: { width: 220 }, children: "Mechanism" }), _jsx("th", { children: "Entity" }), _jsx("th", { children: "Why this is a recursive-gain bet" })] }) }), _jsx("tbody", { children: filtered.map((c, i) => (_jsxs("tr", { children: [_jsx("td", { children: _jsx("span", { className: CONFIDENCE_TAG[c.confidence] || "tag tag-slate", children: c.confidence }) }), _jsx("td", { children: _jsx("span", { className: COST_TAG[c.cost] || "tag tag-slate", children: c.cost }) }), _jsx("td", { children: _jsx("code", { style: { fontSize: 11 }, children: c.mechanism }) }), _jsx("td", { children: _jsx("code", { style: { fontSize: 11 }, children: c.entity }) }), _jsx("td", { style: { fontSize: 12, color: "var(--text-dim)", lineHeight: 1.45 }, children: c.rationale })] }, `${c.source}-${c.entity}-${i}`))) })] })] }), _jsxs("div", { className: "caveat", children: [_jsx("strong", { children: "Current read:" }), " the repeated R10/R11-style warnings are one family: rules that exist but may engage too narrowly. Treat them as a pruning or broadening backlog, not as eight separate conceptual findings."] })] }));
}
