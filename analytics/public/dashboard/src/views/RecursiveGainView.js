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
    if (!rg) {
        return _jsx("div", { className: "error", children: "No recursive-gain candidates \u2014 run mine_recursive_gain_candidates.py first" });
    }
    const mechanisms = Array.from(new Set(rg.candidates.map((c) => c.mechanism))).sort();
    const sources = Array.from(new Set(rg.candidates.map((c) => c.source))).sort();
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "methodology", children: [_jsx("h3", { children: "Recursive-gain candidates \u2014 what to ship next" }), _jsx("p", { children: "Aggregates 5 mining surfaces (cross-audit, structural-analogy, closure-pattern, reference-graph, process-catalog) into a single ranked list of recursive-gain bets. Each row is a concrete move the operator could ship to compound apparatus capability." }), _jsxs("ul", { children: [_jsxs("li", { children: [_jsx("strong", { children: "Mechanism" }), " \u2014 kind of recursive gain (retire-decorative-primitive, wire-one-shot-as-loop, promote-to-cage-gate, run-new-ZTARE-substrate, revive-stalled-loop, self-skeptic-substrate)"] }), _jsxs("li", { children: [_jsx("strong", { children: "Cost" }), " \u2014 operator effort estimate (trivial / day / week / month)"] }), _jsxs("li", { children: [_jsx("strong", { children: "Confidence" }), " \u2014 signal strength from the source miner"] }), _jsxs("li", { children: [_jsx("strong", { children: "Source" }), " \u2014 which mining surface produced it"] })] }), _jsxs("p", { children: [_jsx("strong", { children: "Re-run:" }), " ", _jsx("code", { children: "python scripts/mining/mine_recursive_gain_candidates.py" }), " after any of the upstream miners refresh."] })] }), _jsxs("div", { className: "panel", children: [_jsx("h3", { children: "By the numbers" }), _jsxs("div", { style: { display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }, children: [_jsxs("div", { style: { fontSize: 13 }, children: [_jsx("strong", { children: rg.n_candidates }), " total candidates"] }), Object.entries(rg.by_source).map(([k, v]) => (_jsxs("span", { className: "chip", children: [_jsx("code", { children: k }), ": ", v] }, k)))] })] }), _jsxs("div", { className: "controls", children: [_jsxs("label", { children: ["Confidence:", _jsxs("select", { value: confidenceFilter, onChange: (e) => setConfidenceFilter(e.target.value), children: [_jsx("option", { value: "", children: "all" }), _jsx("option", { value: "high", children: "high" }), _jsx("option", { value: "medium", children: "medium" }), _jsx("option", { value: "low", children: "low" })] })] }), _jsxs("label", { children: ["Mechanism:", _jsxs("select", { value: mechanismFilter, onChange: (e) => setMechanismFilter(e.target.value), children: [_jsx("option", { value: "", children: "all" }), mechanisms.map((m) => _jsx("option", { value: m, children: m }, m))] })] }), _jsxs("label", { children: ["Source:", _jsxs("select", { value: sourceFilter, onChange: (e) => setSourceFilter(e.target.value), children: [_jsx("option", { value: "", children: "all" }), sources.map((s) => _jsx("option", { value: s, children: s }, s))] })] }), _jsxs("span", { style: { marginLeft: 12, fontSize: 12, color: "var(--text-faint)" }, children: [filtered.length, " of ", rg.n_candidates, " shown"] })] }), _jsxs("div", { className: "panel", children: [_jsx("h3", { children: "Ranked candidates (high-confidence + low-cost first)" }), _jsxs("table", { children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { style: { width: 90 }, children: "Confidence" }), _jsx("th", { style: { width: 70 }, children: "Cost" }), _jsx("th", { style: { width: 220 }, children: "Mechanism" }), _jsx("th", { children: "Entity" }), _jsx("th", { children: "Why this is a recursive-gain bet" })] }) }), _jsx("tbody", { children: filtered.map((c, i) => (_jsxs("tr", { children: [_jsx("td", { children: _jsx("span", { className: CONFIDENCE_TAG[c.confidence] || "tag tag-slate", children: c.confidence }) }), _jsx("td", { children: _jsx("span", { className: COST_TAG[c.cost] || "tag tag-slate", children: c.cost }) }), _jsx("td", { children: _jsx("code", { style: { fontSize: 11 }, children: c.mechanism }) }), _jsx("td", { children: _jsx("code", { style: { fontSize: 11 }, children: c.entity }) }), _jsx("td", { style: { fontSize: 12, color: "var(--text-dim)", lineHeight: 1.45 }, children: c.rationale })] }, `${c.source}-${c.entity}-${i}`))) })] })] }), _jsxs("div", { className: "caveat", children: [_jsx("strong", { children: "The strange-loop bet:" }), " watch for the ", _jsx("code", { children: "strange_loop_ZTARE_substrate" }), " ", "mechanism in the table above. That's the meta-recursive proposal \u2014 a new ZTARE substrate that ingests evidence from outside-of-ZTARE work (Research Director output on NS, gravity, etc.) as input. Closes the recursive-gain loop that ZTARE-on-ZTARE used to provide before most R&D moved outside the ZTARE evaluation surface. See GP-134 for the seam writeup."] })] }));
}
