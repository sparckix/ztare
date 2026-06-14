import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { LineChart, Line, ResponsiveContainer, YAxis, Tooltip } from "recharts";
const GROUP_TITLE = {
    "3.1_exogenous": "External checks",
    "3.2_state": "System state",
    "3.3_insight": "Research quality signals",
    "3.4_recursive": "Self-correction and compounding",
};
const GROUP_DETAIL = {
    "3.1_exogenous": "Signals with some independence from the apparatus: forecast calibration, human catch attribution, and cross-family disagreement.",
    "3.2_state": "Inventory and activity measures. Useful for context, weak as evidence of quality.",
    "3.3_insight": "Quality-oriented signals. These are stricter than volume counts, but several still depend on in-system ratings.",
    "3.4_recursive": "Whether the system catches faults, reuses primitives, avoids regressions, and turns proposed improvements into acted-on changes.",
};
// Sparkline minimum sample count. Below this we hide the sparkline:
// two points are a line, not a trend; three are a shape.
const SPARK_MIN = 3;
// Headline subfields the python history extractor pulls out of
// breakdown values. Mirror these so the React sparkline can find them.
const SPARK_SUBFIELDS = [
    "latest", "rate", "mean_score", "mean", "share",
    "operator_share", "ratio_count",
];
function fmt(v) {
    if (v === null || v === undefined)
        return "—";
    if (typeof v === "object")
        return Object.entries(v)
            .map(([k, val]) => `${publicText(k)}: ${typeof val === "object" ? publicText(JSON.stringify(val)) : publicText(String(val))}`)
            .join("  ·  ");
    return publicText(String(v));
}
function historyFor(history, m) {
    if (!history || history.length === 0)
        return { points: [], sparkKey: m.key };
    const tryKey = (k) => {
        const pts = [];
        for (const row of history) {
            const v = row.values?.[k];
            if (typeof v === "number" && Number.isFinite(v)) {
                pts.push({ x: row.generated_utc, y: v });
            }
        }
        return pts;
    };
    // Scalars: direct match by key.
    if (m.value_kind === "scalar" || m.value_kind === undefined) {
        return { points: tryKey(m.key), sparkKey: m.key };
    }
    // Breakdowns: try headline subfields in priority order.
    if (m.value_kind === "breakdown") {
        for (const sub of SPARK_SUBFIELDS) {
            const k = `${m.key}.${sub}`;
            const pts = tryKey(k);
            if (pts.length >= SPARK_MIN)
                return { points: pts, sparkKey: k };
        }
    }
    return { points: [], sparkKey: m.key };
}
function Sparkline({ points, sparkKey }) {
    if (points.length < SPARK_MIN)
        return null;
    const ys = points.map((p) => p.y);
    const latest = ys[ys.length - 1];
    const first = ys[0];
    const delta = latest - first;
    const trend = delta > 0 ? "↑" : delta < 0 ? "↓" : "→";
    const subKey = sparkKey.includes(".") ? sparkKey.split(".").slice(1).join(".") : null;
    return (_jsxs("div", { className: "p0-spark", title: `${sparkKey}: ${points.length} cycles`, children: [_jsx("div", { className: "p0-spark-chart", children: _jsx(ResponsiveContainer, { width: 120, height: 32, children: _jsxs(LineChart, { data: points, margin: { top: 4, right: 4, bottom: 4, left: 4 }, children: [_jsx(YAxis, { hide: true, domain: ["dataMin", "dataMax"] }), _jsx(Tooltip, { cursor: false, contentStyle: { background: "#15171c", border: "1px solid #262a31",
                                    fontSize: 11, padding: "4px 8px" }, labelFormatter: (v) => typeof v === "string" ? v.slice(0, 10) : String(v ?? ""), formatter: (v) => [String(v), sparkKey] }), _jsx(Line, { type: "monotone", dataKey: "y", stroke: "#e8a33d", strokeWidth: 1.5, dot: false, isAnimationActive: false })] }) }) }), _jsxs("div", { className: "p0-spark-meta", children: [_jsx("span", { className: "p0-spark-trend", children: trend }), _jsxs("span", { className: "p0-spark-n", children: [points.length, " cycles", subKey ? ` · .${subKey}` : ""] })] })] }));
}
// Pull a single metric's value off the live p0Metrics list by key, so
// the glance cards below are derived from data — never re-hardcoded.
// Returns the metric's `value` (scalar / breakdown object / series), or
// null if the key is absent.
function metricValue(metrics, key) {
    return metrics.find((m) => m.key === key)?.value ?? null;
}
// Narrow a breakdown value to its numeric subfield, tolerating a missing
// metric or missing field (returns null so the caller can fall back to "—").
function subNum(v, field) {
    if (v && typeof v === "object" && field in v) {
        const n = v[field];
        if (typeof n === "number" && Number.isFinite(n))
            return n;
    }
    return null;
}
function numOrDash(n) {
    return n === null ? "—" : String(n);
}
function publicText(s) {
    return s
        .replace(/\bOperator-vs-apparatus\b/g, "Human-vs-apparatus")
        .replace(/\boperator-vs-apparatus\b/g, "human-vs-apparatus")
        .replace(/\boperator-caught\b/g, "human-caught")
        .replace(/\boperator-curated\b/g, "human-curated")
        .replace(/\boperator working\b/g, "human working")
        .replace(/\boperator load\b/g, "human review load")
        .replace(/\boperator\b/g, "human")
        .replace(/\bOperator\b/g, "Human");
}
function MetricRow({ m, history }) {
    const tierClass = m.tier === "A" ? "tag-signal" : m.tier === "B" ? "tag-amber"
        : m.tier === "C" ? "tag-slate" : "tag-warn";
    const spark = historyFor(history, m);
    const label = publicText(m.label);
    const caveat = publicText(m.caveat || "");
    return (_jsxs("div", { className: `p0-row p0-${m.status}`, children: [_jsxs("div", { className: "p0-head", children: [_jsx("span", { className: "p0-label", children: label }), _jsxs("span", { className: "p0-badges", children: [_jsxs("span", { className: `tag ${tierClass}`, children: ["tier ", m.tier] }), _jsx("span", { className: "tag tag-slate", children: m.lane }), m.self_measured
                                ? _jsx("span", { className: "tag tag-warn", children: "self-measured" })
                                : _jsx("span", { className: "tag tag-signal", children: "external/consumed" }), m.status !== "ok" && _jsx("span", { className: "tag tag-warn", children: m.status })] })] }), _jsxs("div", { className: "p0-value-row", children: [_jsx("div", { className: "p0-value", children: m.status === "not_yet_computable"
                            ? _jsx("em", { children: "not yet computable \u2014 null by design, not fabricated" })
                            : fmt(m.value) }), _jsx(Sparkline, { points: spark.points, sparkKey: spark.sparkKey })] }), _jsxs("div", { className: "p0-caveat", children: [caveat, m.owner && m.owner !== "p0_rollup" &&
                        _jsxs("span", { className: "p0-owner", children: [" \u00B7 owner: ", m.owner] })] })] }));
}
export function P0View({ data }) {
    const p0 = data.p0Metrics;
    const history = data.p0MetricsHistory;
    const sw = data.graphSowhat?.panels?.p0;
    if (!p0 || !p0.metrics) {
        return _jsxs("div", { className: "panel", children: [_jsx("h3", { children: "P0 Metrics" }), _jsx("div", { className: "legend", children: "p0_metrics.json not wired \u2014 run the orchestrator (Phase 2c)." })] });
    }
    const order = p0.group_order || Object.keys(GROUP_TITLE);
    const byGroup = (g) => p0.metrics.filter((m) => m.group === g);
    // 5-second at-a-glance — derived live from p0Metrics, never hardcoded.
    // Each card reads the same numbers the panels below show, so the glance
    // can't drift from the rollup.
    const metrics = p0.metrics;
    // Out-of-loop: live 7-day share is the headline; cumulative is context.
    const ool = metricValue(metrics, "out_of_loop_share");
    const oolLive = subNum(ool, "live_7d_pct");
    const oolCum = subNum(ool, "cumulative_pct");
    // Calibration: distinct positive/negative externality tags + latest Brier.
    const ext = metricValue(metrics, "forecast_externalities");
    const extPos = subNum(ext?.positive, "distinct_tags");
    const extNeg = subNum(ext?.negative, "distinct_tags");
    const brierSeries = metricValue(metrics, "brier_per_period");
    const brierRow = Array.isArray(brierSeries) ? brierSeries[brierSeries.length - 1] : null;
    const brier = subNum(brierRow, "brier");
    const brierBase = subNum(brierRow, "uniform_baseline");
    // Self-correction: who diagnosed the catches (apparatus vs human reviewer).
    const diag = metricValue(metrics, "operator_vs_apparatus_diagnosis_ratio");
    const apparatus = subNum(diag, "apparatus");
    const human = subNum(diag, "operator");
    // Insight density: latest contextualized-taste read + its weekly trend.
    const taste = metricValue(metrics, "contextualized_taste");
    const tasteLatest = subNum(taste, "latest");
    const tasteMax = subNum(taste, "max");
    const traj = metricValue(metrics, "recursive_gain_trajectory");
    const trajSeries = traj?.series;
    const lastWeek = Array.isArray(trajSeries) && trajSeries.length
        ? trajSeries[trajSeries.length - 1] : null;
    // Science frontier: state-only, honestly stuck (no progress score).
    const frontier = metricValue(metrics, "scientific_frontier_state");
    const frontierKnown = frontier !== null;
    const glance = [
        {
            k: "Out-of-loop (live)",
            v: oolLive !== null ? `${oolLive}%` : "—",
            sub: oolCum !== null
                ? `7-day agent work · cumulative ~${oolCum}%`
                : "7-day agent work, not the loop",
            tone: "neutral",
        },
        {
            k: "Calibration",
            v: "net-positive",
            sub: `externalities ${numOrDash(extPos)}:${numOrDash(extNeg)}`
                + (brier !== null
                    ? ` · Brier ${brier}${brierBase !== null ? ` < ${brierBase}` : ""}`
                    : ""),
            tone: "good",
        },
        {
            k: "Self-correction",
            v: "apparatus-carried",
            sub: `${numOrDash(apparatus)} catches diagnosed by apparatus, ${numOrDash(human)} by human review`,
            tone: "good",
        },
        {
            k: "Insight density",
            v: "plateaued",
            sub: (tasteLatest !== null
                ? `latest ~${tasteLatest}${tasteMax !== null ? ` (peak ${tasteMax})` : ""}`
                : "plateau")
                + (lastWeek
                    ? ` · week ${lastWeek.week} dipped to ${lastWeek.mean}`
                    : ""),
            tone: "flat",
        },
        {
            k: "Science frontier",
            v: "stuck",
            sub: frontierKnown
                ? "NS/gravity/neural — state only, no breakthrough"
                : "frontier state not wired this cycle",
            tone: "flat",
        },
    ];
    return (_jsxs("div", { children: [sw && (_jsxs("div", { className: "p0-verdict", children: [_jsx("div", { className: "p0-verdict-tag", children: "So what \u2014 the honest verdict" }), _jsx("div", { className: "p0-verdict-head", children: sw.headline }), sw.detail && _jsx("div", { className: "p0-verdict-detail", children: sw.detail })] })), _jsx("div", { className: "p0-glance", children: glance.map((g) => (_jsxs("div", { className: `p0-gcard p0-g-${g.tone}`, children: [_jsx("div", { className: "p0-gv", children: g.v }), _jsx("div", { className: "p0-gk", children: g.k }), _jsx("div", { className: "p0-gs", children: g.sub })] }, g.k))) }), _jsxs("div", { className: "p0-pagecaveat", children: [_jsx("strong", { children: "Trust the external checks first." }), " ", p0.page_caveat, "Metrics tagged", _jsx("span", { className: "tag tag-warn", children: "self-measured" }), " are the apparatus grading itself. Metrics tagged", _jsx("span", { className: "tag tag-signal", children: "external/consumed" }), " have a stronger independence story. Tier A-C is the trust grade, not an achievement score."] }), order.map((g) => {
                const rows = byGroup(g);
                if (!rows.length)
                    return null;
                const exo = g === "3.1_exogenous";
                return (_jsxs("div", { className: `panel ${exo ? "p0-exo" : ""}`, children: [_jsx("h3", { children: GROUP_TITLE[g] || g }), GROUP_DETAIL[g] && _jsx("div", { className: "panel-intro", children: GROUP_DETAIL[g] }), rows.map((m) => _jsx(MetricRow, { m: m, history: history }, m.key))] }, g));
            }), _jsx("div", { className: "foot", children: "GP-236 P0 rollup \u00B7 deterministic, regenerated each cycle \u00B7 consumed rows owned by their producing track, never recomputed here" })] }));
}
