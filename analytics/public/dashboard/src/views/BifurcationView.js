import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { SoWhat } from "./SoWhat";
function SplitBar({ label, loop, agent, unit, }) {
    const total = Math.max(1, loop + agent);
    const lp = (loop / total) * 100;
    const ap = (agent / total) * 100;
    return (_jsxs("div", { className: "split-row", children: [_jsxs("div", { className: "lbl", children: [_jsx("span", { children: label }), _jsxs("span", { children: [_jsx("b", { children: loop.toLocaleString() }), " in-loop \u00B7 ", _jsx("b", { children: agent.toLocaleString() }), " out-of-loop ", unit] })] }), _jsxs("div", { className: "split", children: [_jsx("div", { className: "seg loop", style: { flexBasis: `${lp}%` }, children: lp > 8 ? `${lp.toFixed(lp < 10 ? 1 : 0)}%` : "" }), _jsx("div", { className: "seg agent", style: { flexBasis: `${ap}%` }, children: `${ap.toFixed(0)}%` })] })] }));
}
export function BifurcationView({ data }) {
    const b = data.bifurcation;
    if (!b || !b.bifurcation) {
        return _jsxs("div", { className: "panel", children: [_jsx("h3", { children: "In-Loop vs Out-of-Loop" }), _jsx("div", { className: "legend", children: "bifurcation_report.json not yet wired \u2014 run the reflexive orchestrator." })] });
    }
    const cum = b.bifurcation;
    const today = b.as_of_today;
    const sharePct = Math.round(cum.agent_work_share * 100);
    const todayShare = today
        ? Math.round((today.modified_last_7d.agent_work /
            Math.max(1, today.modified_last_7d.all)) * 100)
        : sharePct;
    const trees = Object.entries(b.by_tree || {})
        .map(([tree, n]) => ({ tree, n }))
        .sort((a, z) => z.n - a.n);
    const maxN = Math.max(1, ...trees.map((t) => t.n));
    return (_jsxs("div", { children: [_jsxs("div", { className: "panel", children: [_jsxs("div", { className: "bif-hero", children: [_jsx("div", { className: "eyebrow", children: "The architecture bifurcated" }), _jsxs("div", { className: "headline", children: [_jsxs("em", { children: [todayShare, "%"] }), " of this week's authored work happens ", _jsx("em", { children: "outside" }), " the loop"] }), _jsx("div", { className: "sub", children: "ZTARE's evolutionary iter-loop is now a minority substrate. The live work is agent dispatch + governance + mining \u2014 measured by the apparatus, on itself." })] }), _jsx(SoWhat, { data: data, k: "bifurcation" }), _jsx(SplitBar, { label: "Cumulative \u2014 all authored artifacts", loop: cum.iter_loop_artifacts, agent: cum.agent_work_artifacts, unit: "artifacts" }), today && (_jsx(SplitBar, { label: `As of today (${today.date}) — trailing 7 days`, loop: today.modified_last_7d.iter_loop, agent: today.modified_last_7d.agent_work, unit: "artifacts" })), _jsxs("div", { className: "stat-grid", children: [_jsxs("div", { className: "stat", children: [_jsx("div", { className: "v", children: b.indexed.toLocaleString() }), _jsx("div", { className: "k", children: "Authored artifacts indexed" })] }), _jsxs("div", { className: "stat", children: [_jsxs("div", { className: "v agent", children: [sharePct, "%"] }), _jsx("div", { className: "k", children: "Out-of-loop (cumulative)" })] }), _jsxs("div", { className: "stat", children: [_jsxs("div", { className: "v agent", children: [todayShare, "%"] }), _jsx("div", { className: "k", children: "Out-of-loop (this week)" })] })] }), _jsxs("div", { className: "legend", children: ["Generated/vendored excluded (", b.excluded_generated_vendored.toLocaleString(), "). In-loop = the ZTARE iteration work files themselves (the iter** artifacts: debate_log_iter_*, iteration_telemetry, current_iteration, iter_*). Out-of-loop = everything else, including the rest of ", _jsx("code", { children: "projects/" }), ". The invariant is the iter** files, not which directory they sit in. ", today?.note] })] }), _jsxs("div", { className: "panel", children: [_jsx("h3", { children: "Where the authored work lives" }), _jsx("div", { className: "legend", children: "Authored artifacts by tree. ztare_proofs & analytics dominate (NS/Clay formalization + governance). Loop status is a cross-cutting file pattern, not a tree \u2014 see the split above." }), _jsx("div", { className: "treebars", children: trees.map((t) => {
                            const pct = (t.n / maxN) * 100;
                            return (_jsxs("div", { className: "treebar", children: [_jsx("div", { className: "tb-name", children: t.tree }), _jsx("div", { className: "tb-track", children: _jsx("div", { className: "tb-fill", style: {
                                                width: `${Math.max(pct, 1.5)}%`,
                                                background: "linear-gradient(90deg,#e8a33d,#c8862c)",
                                            } }) }), _jsx("div", { className: "tb-val", children: t.n.toLocaleString() })] }, t.tree));
                        }) })] })] }));
}
