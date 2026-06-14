import { jsxs as _jsxs, jsx as _jsx, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { loadDashboardData } from "./lib/data";
import { P0View } from "./views/P0View";
import { BifurcationView } from "./views/BifurcationView";
import { TrajectoryView } from "./views/TrajectoryView";
import { ReferenceGraphView } from "./views/ReferenceGraphView";
import { MethodologyView } from "./views/MethodologyView";
import { ConsequentialArtifactsView } from "./views/ConsequentialArtifactsView";
import { RecursiveGainView } from "./views/RecursiveGainView";
const TABS = [
    ["p0", "P0 Metrics"],
    ["bifurcation", "In-Loop · Out-of-Loop"],
    ["trajectory", "Trajectory"],
    ["weeks", "Week Digests"],
    ["recursive_gain", "Recursive Gain"],
    ["graph", "Reference Graph"],
    ["methodology", "Methodology"],
];
const _qpTab = (() => {
    try {
        const t = new URLSearchParams(window.location.search).get("tab");
        return (t && TABS.some(([id]) => id === t)) ? t : "p0";
    }
    catch {
        return "p0";
    }
})();
export function App() {
    const [tab, setTab] = useState(_qpTab);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    useEffect(() => {
        loadDashboardData().then(setData).catch((e) => setError(String(e)));
    }, []);
    if (error) {
        return _jsx("div", { className: "app-shell", children: _jsxs("div", { className: "error", children: ["Failed to load data: ", error] }) });
    }
    if (!data) {
        return _jsx("div", { className: "app-shell", children: _jsx("div", { className: "loading", children: "Loading instruments\u2026" }) });
    }
    const asOf = data.bifurcation?.as_of_today?.date;
    return (_jsxs("div", { className: "app-shell", children: [_jsxs("div", { className: "app-header", children: [_jsxs("h1", { children: ["ZTARE", _jsx("span", { className: "sub", children: "Reflexive Research Instrument" })] }), _jsxs("div", { className: "app-side", children: [_jsx("div", { className: "app-links", children: _jsx("a", { href: "./ns-atlas/", children: "NS Atlas" }) }), _jsxs("div", { className: "app-meta", children: [asOf ? _jsxs(_Fragment, { children: ["As of ", _jsx("b", { children: asOf })] }) : "—", _jsx("br", {}), data.trajectoryCurves
                                        ? `mine ${new Date(data.trajectoryCurves.audit_timestamp_utc).toLocaleDateString()}`
                                        : ""] })] })] }), _jsxs("div", { className: "caveat", children: [_jsx("strong", { children: "Read as an instrument." }), " Counts show activity. The stronger signals are external calibration, cross-family disagreement, downstream dependence, and the contextualized taste curve."] }), _jsx("div", { className: "tabs", children: TABS.map(([id, label]) => (_jsx("button", { className: `tab ${tab === id ? "active" : ""}`, onClick: () => setTab(id), children: label }, id))) }), tab === "p0" && _jsx(P0View, { data: data }), tab === "bifurcation" && _jsx(BifurcationView, { data: data }), tab === "trajectory" && _jsx(TrajectoryView, { data: data }), tab === "weeks" && _jsx(ConsequentialArtifactsView, { data: data }), tab === "recursive_gain" && _jsx(RecursiveGainView, { data: data }), tab === "graph" && _jsx(ReferenceGraphView, { data: data }), tab === "methodology" && _jsx(MethodologyView, {}), _jsx("div", { className: "foot", children: "ZTARE \u00B7 zero-trust adversarial reasoning \u00B7 the discipline that keeps an agent honest under recursion" })] }));
}
