import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useRef } from "react";
import { SoWhat } from "./SoWhat";
export function TrajectoryView({ data }) {
    const sophRef = useRef(null);
    const insightRef = useRef(null);
    const tasteRef = useRef(null);
    const compRef = useRef(null);
    const confRef = useRef(null);
    const Plotly = window.Plotly;
    const { trajectoryCurves, inflections, taste, referenceGraph } = data;
    // Everything the prose asserts about the taste curve is derived from the
    // live `data` prop here, never hardcoded — so the legend/expander text
    // can't drift out of sync with the chart above it.
    const tasteWeeksSorted = Object.keys(taste?.weekly_stats || {}).sort();
    const tasteNWeeks = tasteWeeksSorted.length;
    const tastePeak = tasteWeeksSorted.reduce((best, w) => {
        const m = taste.weekly_stats[w].mean_score;
        return best && best.mean >= m ? best : { week: w, mean: m };
    }, null);
    const tasteFirst = tasteNWeeks ? taste.weekly_stats[tasteWeeksSorted[0]] : null;
    const tasteLast = tasteNWeeks
        ? taste.weekly_stats[tasteWeeksSorted[tasteNWeeks - 1]]
        : null;
    const tasteAvgN = tasteNWeeks
        ? Math.round(tasteWeeksSorted.reduce((s, w) => s + taste.weekly_stats[w].n_rated, 0) /
            tasteNWeeks)
        : 0;
    // Same for the compounding ratio: compute the actual peak week/value from
    // the reference graph rather than asserting a stale number in prose.
    const compWeeksSorted = Object.keys(referenceGraph?.weekly_stats || {}).sort();
    const compPeak = compWeeksSorted.reduce((best, w) => {
        const s = referenceGraph.weekly_stats[w];
        const ratio = s.n_nodes && s.n_nodes > 0 ? (s.n_outbound_to_earlier_weeks || 0) / s.n_nodes : 0;
        return best && best.ratio >= ratio ? best : { week: w, ratio };
    }, null);
    useEffect(() => {
        if (!Plotly || !trajectoryCurves)
            return;
        const weeks = trajectoryCurves.weeks || [];
        const c = trajectoryCurves.curves || {};
        const events = trajectoryCurves.external_events || [];
        const eventShapes = events.map((e) => ({
            type: "line",
            x0: e.date, x1: e.date, xref: "x",
            y0: 0, y1: 1, yref: "paper",
            line: { color: "rgba(120,120,120,0.4)", width: 1, dash: "dash" },
        }));
        const realInflections = (inflections?.ranked_inflections || [])
            .filter((r) => r.verdict === "real_inflection");
        const inflectionShapes = realInflections.map((r) => ({
            type: "rect",
            x0: r.week, x1: r.week, xref: "x",
            y0: 0, y1: 1, yref: "paper",
            line: { color: "rgba(255,165,0,0.85)", width: 3 },
            fillcolor: "rgba(255,200,100,0.15)",
        }));
        // The current (incomplete) week buckets under its Monday; it actually
        // contains work through today, so relabel the trailing tick with the
        // as-of-today date (operator: "i still see 11 not 16").
        const asOf = data?.bifurcation?.as_of_today?.date;
        const tickText = (arr) => arr.map((w, i) => asOf && i === arr.length - 1 && asOf > w ? `${asOf} ·now` : w);
        const baseLayout = (title, xs = weeks) => ({
            title: { text: title, font: { size: 13, color: "#e9e5dc",
                    family: "Fraunces, Georgia, serif" } },
            height: 330,
            margin: { l: 58, r: 48, t: 42, b: 64 },
            hovermode: "x unified",
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { color: "#9aa0a8", family: "IBM Plex Mono, monospace", size: 11 },
            colorway: ["#e8a33d", "#4ec9a5", "#5b6b7a", "#d9683f", "#c8862c"],
            legend: { bgcolor: "rgba(0,0,0,0)", orientation: "h", y: -0.26,
                font: { color: "#9aa0a8", size: 10 } },
            shapes: [...eventShapes, ...inflectionShapes],
            xaxis: {
                type: "category", categoryorder: "array", categoryarray: xs,
                tickvals: xs, ticktext: tickText(xs),
                gridcolor: "#1d2026", linecolor: "#262a31", zerolinecolor: "#262a31",
                tickfont: { color: "#9aa0a8", size: 10 },
            },
            yaxis: { gridcolor: "#1d2026", zerolinecolor: "#262a31" },
        });
        const seriesFromObj = (obj) => weeks.map((w) => (obj && obj[w] !== undefined ? obj[w] : null));
        // Panel 1: Sophistication
        if (sophRef.current) {
            Plotly.newPlot(sophRef.current, [
                { x: weeks, y: seriesFromObj(c.sophistication_a_capability_count_cumulative),
                    type: "scatter", mode: "lines+markers", name: "Soph-A: cumulative capability",
                    line: { color: "#1f77b4", width: 3 } },
                { x: weeks, y: seriesFromObj(c.sophistication_d_autonomous_actions_per_week),
                    type: "bar", name: "Soph-D: autonomous actions/wk", yaxis: "y2",
                    marker: { color: "#ff7f0e", opacity: 0.6 } },
            ], {
                ...baseLayout("Sophistication — capability + autonomy"),
                yaxis: { title: "capability (cumulative)" },
                yaxis2: { title: "actions / wk", overlaying: "y", side: "right" },
            }, { responsive: true });
        }
        // Panel 2: Insight volume
        if (insightRef.current) {
            Plotly.newPlot(insightRef.current, [
                { x: weeks, y: seriesFromObj(c.insight_a_f_row_creates_per_week), type: "scatter", mode: "lines+markers", name: "F-row creates" },
                { x: weeks, y: seriesFromObj(c.insight_b_f_row_closures_per_week), type: "scatter", mode: "lines+markers", name: "F-row closures" },
                { x: weeks, y: seriesFromObj(c.insight_d_project_workspace_artifacts_per_week), type: "scatter", mode: "lines+markers", name: "Project artifacts", yaxis: "y2" },
                { x: weeks, y: seriesFromObj(c.insight_e_verified_axioms_added_per_week), type: "scatter", mode: "lines+markers", name: "Verified axioms" },
            ], {
                ...baseLayout("Insight volume across multiple sources"),
                yaxis: { title: "count" },
                yaxis2: { title: "larger-scale", overlaying: "y", side: "right" },
            }, { responsive: true });
        }
        // Panel 3: Taste (contextualized)
        if (tasteRef.current && taste) {
            const tasteWeeks = Object.keys(taste.weekly_stats || {}).sort();
            const tasteMean = tasteWeeks.map((w) => taste.weekly_stats[w].mean_score);
            const tasteMax = tasteWeeks.map((w) => taste.weekly_stats[w].max_score);
            const tasteHQ = tasteWeeks.map((w) => taste.weekly_stats[w].n_high_quality_ge4);
            Plotly.newPlot(tasteRef.current, [
                { x: tasteWeeks, y: tasteMean, type: "scatter", mode: "lines+markers", name: "Mean score (0-5)",
                    line: { color: "#e8a33d", width: 3 }, marker: { size: 7 } },
                { x: tasteWeeks, y: tasteMax, type: "scatter", mode: "lines+markers", name: "Max score",
                    line: { color: "#5b6b7a", dash: "dot" } },
                { x: tasteWeeks, y: tasteHQ, type: "bar", name: "High-quality count (≥4)", yaxis: "y2",
                    marker: { color: "#4ec9a5", opacity: 0.45 } },
            ], {
                ...baseLayout("Taste — contextualized rater", tasteWeeks),
                yaxis: { title: "score", range: [0, 5], gridcolor: "#1d2026", zerolinecolor: "#262a31" },
                yaxis2: { title: "≥4 count", overlaying: "y", side: "right", gridcolor: "transparent" },
            }, { responsive: true });
        }
        // Panel 4: Compounding
        if (compRef.current && referenceGraph) {
            const ws = referenceGraph.weekly_stats || {};
            const cw = Object.keys(ws).sort();
            const inLater = cw.map((w) => ws[w].n_inbound_from_later_weeks || 0);
            const outEarlier = cw.map((w) => ws[w].n_outbound_to_earlier_weeks || 0);
            const nodes = cw.map((w) => ws[w].n_nodes || 0);
            const ratio = cw.map((w, i) => (nodes[i] > 0 ? outEarlier[i] / nodes[i] : 0));
            Plotly.newPlot(compRef.current, [
                { x: cw, y: inLater, type: "bar", name: "Inbound from later (high-reuse)", marker: { color: "#5b6b7a", opacity: 0.75 } },
                { x: cw, y: outEarlier, type: "bar", name: "Outbound to earlier (compounding)", marker: { color: "#e8a33d", opacity: 0.8 } },
                { x: cw, y: ratio, type: "scatter", mode: "lines+markers", name: "Compounding ratio (out/nodes)", yaxis: "y2",
                    line: { color: "#4ec9a5", width: 3 }, marker: { size: 7 } },
            ], {
                ...baseLayout("Compounding — cross-artifact reference graph", cw),
                yaxis: { title: "edge count", gridcolor: "#1d2026", zerolinecolor: "#262a31" },
                yaxis2: { title: "ratio", overlaying: "y", side: "right", gridcolor: "transparent" },
                barmode: "group",
            }, { responsive: true });
        }
        // Panel 5: Confounds
        if (confRef.current) {
            Plotly.newPlot(confRef.current, [
                { x: weeks, y: seriesFromObj(c.confound_a_code_activity_density), type: "scatter", mode: "lines+markers", name: "Conf-A: code activity", line: { color: "#aaa" } },
                { x: weeks, y: seriesFromObj(c.confound_b_total_artifact_creation_per_week), type: "scatter", mode: "lines+markers", name: "Conf-B: total creates", line: { color: "#bbb" } },
            ], {
                ...baseLayout("Confounds — general activity"),
                yaxis: { title: "count" },
            }, { responsive: true });
        }
    }, [trajectoryCurves, inflections, taste, referenceGraph, Plotly]);
    if (!trajectoryCurves) {
        return _jsx("div", { className: "error", children: "Trajectory curves not available \u2014 run mine_trajectory_curves.py first" });
    }
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "methodology", children: [_jsx("h3", { children: "How to read this dashboard" }), _jsxs("p", { children: ["Five panels measuring apparatus trajectory along independent axes. Vertical orange bands mark ", _jsx("strong", { children: "auto-detected real inflections" }), "(a week where \u22653 of the metrics show a step-change simultaneously). Vertical dashed grey lines are ", _jsx("strong", { children: "external events" }), "(paper deadlines, GPU runs, model upgrades \u2014 confound markers)."] }), _jsx("p", { children: _jsx("strong", { children: "What's measured:" }) }), _jsxs("ul", { children: [_jsxs("li", { children: [_jsx("strong", { children: "Sophistication" }), " \u2014 apparatus capability and autonomy. Pure deterministic counts, file mtime / parsed iter timestamps. ", _jsx("em", { children: "Cumulative capability only ever rises; read the slope, not the level." })] }), _jsxs("li", { children: [_jsx("strong", { children: "Insight (volume)" }), " \u2014 count of insight-bearing artifacts created. Counts only; doesn't measure quality."] }), _jsxs("li", { children: [_jsx("strong", { children: "Insight (taste)" }), " \u2014 quality of artifacts. ", _jsx("em", { children: "Cold sub-agent rates each artifact 0-5 with a context primer" }), " (see panel 3 expander)."] }), _jsxs("li", { children: [_jsx("strong", { children: "Compounding" }), " \u2014 cross-artifact citation graph. Distinguishes \"lots of new work\" from \"new work building on old work.\""] }), _jsxs("li", { children: [_jsx("strong", { children: "Confounds" }), " \u2014 general activity volume + external events. Sham-arm \u2014 if the apparatus story is real, sophistication and taste curves should diverge from these."] })] })] }), _jsxs("div", { className: "panel", children: [_jsx("h3", { children: "1. Sophistication \u2014 capability growth" }), _jsx(SoWhat, { data: data, k: "sophistication" }), _jsx("div", { ref: sophRef }), _jsx("div", { className: "legend", children: "Soph-A is cumulative apparatus generators. Soph-D is autonomous cage actions per week (parsed iter timestamps)." }), _jsxs("details", { className: "info", children: [_jsx("summary", { children: "How this is calculated" }), _jsxs("p", { children: [_jsx("strong", { children: "Soph-A (capability count, cumulative):" }), " walks ", _jsxs("code", { children: ["src/ztare/", '{gates,orchestrator,fit,...}'] }), ", all ", _jsxs("code", { children: ["org/", '{mandates,key_results,signals,...}'] }), " dirs, the research-area seam dirs, and ", _jsx("code", { children: "scripts/public/mining/" }), ". Each ", _jsx("code", { children: ".md" }), " / ", _jsx("code", { children: ".py" }), " / ", _jsx("code", { children: ".yaml" }), " file gets attributed to the week of its earliest known timestamp (frontmatter ", _jsx("code", { children: "opened" }), "/", _jsx("code", { children: "discovered" }), " date if present, else stat birthtime, else mtime). Cumulative count = total apparatus generators that EXIST as of week N."] }), _jsxs("p", { children: [_jsx("strong", { children: "Soph-D (autonomous actions per week):" }), " reads ", _jsx("code", { children: "projects/*/workspace/cage_engagement.jsonl" }), ". Each line has its own ", _jsx("code", { children: "utc" }), " timestamp; events are bucketed by their actual emission week, not by file mtime. The value is the sum of ", _jsx("code", { children: "engaged_count" }), " across all events that week \u2014 the count of cage-gate engagements the apparatus performed autonomously."] })] })] }), _jsxs("div", { className: "panel", children: [_jsx("h3", { children: "2. Insight \u2014 volume (count and content)" }), _jsx(SoWhat, { data: data, k: "insight_volume" }), _jsx("div", { ref: insightRef }), _jsx("div", { className: "legend", children: "F-row creates/closures from EXPERIMENT_TRACK_RECORD; project artifacts from projects/*/workspace/*; verified axioms from per-project ledgers. (Paper line-count deliberately excluded \u2014 a gameable, self-defeating proxy.)" }), _jsxs("details", { className: "info", children: [_jsx("summary", { children: "How this is calculated" }), _jsxs("ul", { children: [_jsxs("li", { children: [_jsx("strong", { children: "Insight-A (F-row creates):" }), " count of ", _jsxs("code", { children: ["| E-", '{ID}', " |"] }), " lines added to ", _jsx("code", { children: "research_areas/EXPERIMENT_TRACK_RECORD.md" }), " per week, dated by the date column in the row."] }), _jsxs("li", { children: [_jsx("strong", { children: "Insight-B (F-row closures):" }), " subset of A where the row's prose matches ", _jsx("code", { children: "verified|theorem proven|machine-check|falsified.*finding|counterexample.*found" }), "."] }), _jsx("li", { children: _jsx("em", { children: "Insight-C (paper line-count) was removed \u2014 line count is a gameable, self-defeating proxy (more lines \u2260 more value)." }) }), _jsxs("li", { children: [_jsx("strong", { children: "Insight-D (project workspace artifacts):" }), " count of ", _jsx("code", { children: ".md" }), "/", _jsx("code", { children: ".json" }), "/", _jsx("code", { children: ".jsonl" }), "/", _jsx("code", { children: ".py" }), "/", _jsx("code", { children: ".yaml" }), " files in ", _jsx("code", { children: "projects/*/workspace/" }), " + project root. Captures NS phase work, gravity proofs, consciousness theory, etc. \u2014 the bulk of substantive research output."] }), _jsxs("li", { children: [_jsx("strong", { children: "Insight-E (verified axioms):" }), " count of non-sentinel axioms in ", _jsx("code", { children: "projects/*/verified_axioms.json" }), " (excludes \"no inherited truth\" sentinel entries), attributed by file mtime."] })] }), _jsxs("p", { children: ["All metrics are pure counts \u2014 ", _jsx("em", { children: "volume only, not quality" }), ". Quality lives in panel 3."] })] })] }), _jsxs("div", { className: "panel", children: [_jsx("h3", { children: "3. Insight \u2014 taste (contextualized rater 0-5)" }), _jsx(SoWhat, { data: data, k: "taste" }), _jsx("div", { ref: tasteRef }), _jsxs("div", { className: "legend", children: ["N\u2248", tasteAvgN, "/week stratified across 11 kinds, ", tasteNWeeks, " weeks total. Rater anchored on top-cited seams + memory entries. The un-anchored cold rater gave no 5s and over-rated mechanism-looking content; the anchored rater is stricter."] }), _jsxs("details", { className: "info", children: [_jsx("summary", { children: "How taste is calculated (read this if it's the first time)" }), _jsx("p", { children: _jsx("strong", { children: "The pipeline:" }) }), _jsxs("ol", { children: [_jsxs("li", { children: [_jsx("code", { children: "scripts/public/mining/sample_artifacts_for_taste.py" }), " walks 11 artifact kinds (F-rows, seams, paper sections, project evaluations, verified axioms, project workspace markdown, raw evidence inputs, evidence files, project charters, concept docs, memory entries, top-level reasoning) across the corpus."] }), _jsx("li", { children: "Stratified sampling: ~25 per week, balanced across kinds, capped at 3 per project so NS doesn't dominate. Random shuffle so the rater can't infer week from order." }), _jsxs("li", { children: [_jsx("code", { children: "scripts/public/mining/build_context_primer.py" }), " compiles a primer of (a) top-15 most-cited seams in the reference graph, (b) human-curated memory entries, (c) anti-pattern catalog headers, (d) DECISION_LOG headers."] }), _jsxs("li", { children: ["A ", _jsx("strong", { children: "cold sub-agent" }), " (no context contamination from this codebase) reads the primer FIRST, then rates each sample 0-5: ", _jsx("strong", { children: "0" }), " = boilerplate, ", _jsx("strong", { children: "1" }), " = trivially observable, ", _jsx("strong", { children: "2" }), " = useful but expected, ", _jsx("strong", { children: "3" }), " = sharp framing, ", _jsx("strong", { children: "4" }), " = high-reuse / mechanism-revealing, ", _jsx("strong", { children: "5" }), " = paradigm-shifting (would force rewriting one of the most-cited seams in the primer)."] }), _jsxs("li", { children: [_jsx("code", { children: "scripts/public/mining/aggregate_taste.py" }), " bins ratings by the sample's week (revealed only at aggregation time) and computes mean / max / count of \u22654 / count of \u22655 per week."] })] }), _jsxs("p", { children: [_jsx("strong", { children: "Why the primer matters:" }), " the cold rater without the primer gave ", _jsx("em", { children: "zero 5s" }), " and over-rated mechanism-looking content at 4. With the primer (so it knows which seams are central in THIS codebase), the rater is stricter overall.", tastePeak && tasteFirst && tasteLast && (_jsxs(_Fragment, { children: [" Across the ", tasteNWeeks, " rated weeks, the weekly mean peaks at ", _jsx("strong", { children: tastePeak.mean.toFixed(2) }), " in the week of ", _jsx("strong", { children: tastePeak.week }), " (first week ", tasteFirst.mean_score.toFixed(2), ", latest week ", tasteLast.mean_score.toFixed(2), "). With N\u2248", tasteAvgN, "/week the per-week numbers are noisy \u2014 read the shape across weeks, not any single point."] }))] }), _jsxs("p", { children: [_jsx("strong", { children: "Cost discipline:" }), " ratings persist in ", _jsx("code", { children: "analytics/public/queries/taste/taste_ledger.json" }), " keyed by content SHA. A re-run only rates artifacts whose content changed. Bumping ", _jsx("code", { children: "CODE_VERSION" }), " or ", _jsx("code", { children: "--require-primer-match" }), " invalidates stale entries."] }), _jsxs("p", { children: [_jsx("strong", { children: "Caveat:" }), " N\u2248", tasteAvgN, "/week with \u00B11 rater spread means individual week comparisons are noisy. The trajectory across the ", tasteNWeeks, " rated weeks is the signal, not any single week."] })] })] }), _jsxs("div", { className: "panel", children: [_jsx("h3", { children: "4. Compounding \u2014 cross-artifact reference graph" }), _jsx(SoWhat, { data: data, k: "compounding" }), _jsx("div", { ref: compRef }), _jsxs("div", { className: "legend", children: [_jsx("strong", { children: "Inbound from later weeks:" }), " how much this week's work is cited by later work (became depended-on downstream). ", _jsx("strong", { children: "Outbound to earlier weeks:" }), " how much this week's work pulls from prior context (compounding). A rising compounding ratio means newer artifacts cite more accumulated history per artifact."] }), _jsxs("details", { className: "info", children: [_jsx("summary", { children: "How this is calculated" }), _jsxs("p", { children: [_jsx("code", { children: "scripts/public/mining/mine_reference_graph.py" }), " walks every apparatus markdown file (capped at 2000 nodes for performance) and extracts citations using two patterns:"] }), _jsxs("ul", { children: [_jsxs("li", { children: [_jsx("strong", { children: "GP-N references:" }), " ", _jsx("code", { children: "GP-148" }), ", ", _jsx("code", { children: "gp226" }), ", etc. \u2192 resolved to the matching seam file."] }), _jsxs("li", { children: [_jsx("strong", { children: "File-path references:" }), " ", _jsx("code", { children: "src/ztare/..." }), ", ", _jsx("code", { children: "projects/.../phase5fa.md" }), ", ", _jsx("code", { children: "papers/paper4/draft.md" }), " \u2192 resolved by suffix match against the node table."] })] }), _jsx("p", { children: "Builds a directed graph: edge from citer \u2192 citee. Then per-week:" }), _jsxs("ul", { children: [_jsxs("li", { children: [_jsx("strong", { children: "Inbound from later weeks" }), " \u2014 sum of edges where this week's nodes are cited by future-week nodes. ", _jsx("em", { children: "Became depended-on downstream:" }), " high inbound = work that future research builds on."] }), _jsxs("li", { children: [_jsx("strong", { children: "Outbound to earlier weeks" }), " \u2014 sum of edges where this week's nodes cite earlier-week nodes. ", _jsx("em", { children: "Compounding:" }), " high outbound = current work is pulling on accumulated history."] }), _jsxs("li", { children: [_jsx("strong", { children: "Compounding ratio" }), " = outbound_to_earlier / nodes-this-week. Normalizes for week-volume; a high ratio means individual artifacts are pulling more historical context than usual."] })] }), compPeak && (_jsxs("p", { children: ["The compounding ratio peaks at ", _jsx("strong", { children: compPeak.ratio.toFixed(2) }), " in the week of ", _jsx("strong", { children: compPeak.week }), " \u2014 a dimension that raw volume and per-artifact taste don't capture. Recompute it each refresh; it moves with the corpus."] }))] })] }), _jsxs("div", { className: "panel", children: [_jsx("h3", { children: "5. Confounds \u2014 general activity & external events" }), _jsx("div", { ref: confRef }), _jsx("div", { className: "legend", children: "If the apparatus story is real, sophistication and taste curves should diverge from confound curves. If they track together, the apparent acceleration is general activity volume." }), _jsxs("details", { className: "info", children: [_jsx("summary", { children: "How this is calculated" }), _jsxs("ul", { children: [_jsxs("li", { children: [_jsx("strong", { children: "Confound-A (code activity):" }), " count of ", _jsx("code", { children: ".py" }), "/", _jsx("code", { children: ".md" }), "/", _jsx("code", { children: ".yaml" }), " files in ", _jsx("code", { children: "src/" }), " + ", _jsx("code", { children: "scripts/" }), " with mtime in the week. Captures \"amount of typing/editing happening\" regardless of whether it's apparatus-relevant."] }), _jsxs("li", { children: [_jsx("strong", { children: "Confound-B (total artifact creation):" }), " count of ", _jsx("em", { children: "all" }), " apparatus-shaped files created repo-wide per week. The broadest possible activity-volume signal."] }), _jsxs("li", { children: [_jsx("strong", { children: "Confound-C (external events):" }), " manually curated in ", _jsx("code", { children: "org/runtime/external_events.yaml" }), ". Paper deadlines, model upgrades, GPU runs, conferences \u2014 anything not apparatus-driven that might create activity."] })] }), _jsx("p", { children: "If sophistication / insight / compounding curves rise together with confounds, the apparent acceleration is mostly \"more human work that week.\" If they diverge \u2014 sophistication up, confounds flat \u2014 the apparatus signal is something other than raw typing volume." })] })] }), _jsxs("div", { className: "panel", children: [_jsx("h3", { children: "Auto-detected real inflections (\u22653 metrics step-change)" }), (() => {
                        const real = (inflections?.ranked_inflections || []).filter((r) => r.verdict === "real_inflection");
                        if (real.length === 0)
                            return _jsx("p", { children: _jsx("em", { children: "none" }) });
                        return (_jsxs("table", { children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "Week" }), _jsx("th", { children: "Score" }), _jsx("th", { children: "Metrics" }), _jsx("th", { children: "External events" })] }) }), _jsx("tbody", { children: real.map((r) => (_jsxs("tr", { children: [_jsx("td", { children: r.week }), _jsx("td", { children: r.convergence_score }), _jsx("td", { children: r.metrics.map((m) => m.replace(/_/g, " ")).join(", ") }), _jsx("td", { children: (r.coincident_external_events || []).map((e) => e.label).join("; ") || "—" })] }, r.week))) })] }));
                    })()] })] }));
}
