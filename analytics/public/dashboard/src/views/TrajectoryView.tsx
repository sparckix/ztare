import { useEffect, useRef } from "react";
import type { DashboardData } from "../lib/data";
import { SoWhat } from "./SoWhat";

export function TrajectoryView({ data }: { data: DashboardData }) {
  const sophRef = useRef<HTMLDivElement>(null);
  const insightRef = useRef<HTMLDivElement>(null);
  const tasteRef = useRef<HTMLDivElement>(null);
  const compRef = useRef<HTMLDivElement>(null);
  const confRef = useRef<HTMLDivElement>(null);

  const Plotly = window.Plotly;
  const { trajectoryCurves, inflections, taste, referenceGraph } = data;

  // Everything the prose asserts about the taste curve is derived from the
  // live `data` prop here, never hardcoded — so the legend/expander text
  // can't drift out of sync with the chart above it.
  const tasteWeeksSorted = Object.keys(taste?.weekly_stats || {}).sort();
  const tasteNWeeks = tasteWeeksSorted.length;
  const tastePeak = tasteWeeksSorted.reduce<{ week: string; mean: number } | null>(
    (best, w) => {
      const m = taste!.weekly_stats[w].mean_score;
      return best && best.mean >= m ? best : { week: w, mean: m };
    },
    null,
  );
  const tasteFirst = tasteNWeeks ? taste!.weekly_stats[tasteWeeksSorted[0]] : null;
  const tasteLast = tasteNWeeks
    ? taste!.weekly_stats[tasteWeeksSorted[tasteNWeeks - 1]]
    : null;
  const tasteAvgN = tasteNWeeks
    ? Math.round(
        tasteWeeksSorted.reduce((s, w) => s + taste!.weekly_stats[w].n_rated, 0) /
          tasteNWeeks,
      )
    : 0;

  // Same for the compounding ratio: compute the actual peak week/value from
  // the reference graph rather than asserting a stale number in prose.
  const compWeeksSorted = Object.keys(referenceGraph?.weekly_stats || {}).sort();
  const compPeak = compWeeksSorted.reduce<{ week: string; ratio: number } | null>(
    (best, w) => {
      const s = referenceGraph!.weekly_stats[w] as { n_nodes?: number; n_outbound_to_earlier_weeks?: number };
      const ratio = s.n_nodes && s.n_nodes > 0 ? (s.n_outbound_to_earlier_weeks || 0) / s.n_nodes : 0;
      return best && best.ratio >= ratio ? best : { week: w, ratio };
    },
    null,
  );

  useEffect(() => {
    if (!Plotly || !trajectoryCurves) return;
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
    const asOf = (data as any)?.bifurcation?.as_of_today?.date as string | undefined;
    const tickText = (arr: string[]) =>
      arr.map((w, i) =>
        asOf && i === arr.length - 1 && asOf > w ? `${asOf} ·now` : w);
    const baseLayout = (title: string, xs: string[] = weeks) => ({
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

    const seriesFromObj = (obj: Record<string, number> | undefined) =>
      weeks.map((w) => (obj && obj[w] !== undefined ? obj[w] : null));

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
    return <div className="error">Trajectory curves not available — run mine_trajectory_curves.py first</div>;
  }

  return (
    <>
      <div className="methodology">
        <h3>How to read this dashboard</h3>
        <p>
          Five panels measuring apparatus trajectory along independent axes.
          Vertical orange bands mark <strong>auto-detected real inflections</strong>
          (a week where ≥3 of the metrics show a step-change simultaneously).
          Vertical dashed grey lines are <strong>external events</strong>
          (paper deadlines, GPU runs, model upgrades — confound markers).
        </p>
        <p>
          <strong>What's measured:</strong>
        </p>
        <ul>
          <li><strong>Sophistication</strong> — apparatus capability and autonomy. Pure deterministic counts, file mtime / parsed iter timestamps. <em>Cumulative capability only ever rises; read the slope, not the level.</em></li>
          <li><strong>Insight (volume)</strong> — count of insight-bearing artifacts created. Counts only; doesn't measure quality.</li>
          <li><strong>Insight (taste)</strong> — quality of artifacts. <em>Cold sub-agent rates each artifact 0-5 with a context primer</em> (see panel 3 expander).</li>
          <li><strong>Compounding</strong> — cross-artifact citation graph. Distinguishes "lots of new work" from "new work building on old work."</li>
          <li><strong>Confounds</strong> — general activity volume + external events. Sham-arm — if the apparatus story is real, sophistication and taste curves should diverge from these.</li>
        </ul>
      </div>

      <div className="panel">
        <h3>1. Sophistication — capability growth</h3>
        <SoWhat data={data} k="sophistication" />
        <div ref={sophRef} />
        <div className="legend">Soph-A is cumulative apparatus generators. Soph-D is autonomous cage actions per week (parsed iter timestamps).</div>
        <details className="info">
          <summary>How this is calculated</summary>
          <p><strong>Soph-A (capability count, cumulative):</strong> walks <code>src/ztare/{'{gates,orchestrator,fit,...}'}</code>, all <code>org/{'{mandates,key_results,signals,...}'}</code> dirs, the research-area seam dirs, and <code>scripts/public/mining/</code>. Each <code>.md</code> / <code>.py</code> / <code>.yaml</code> file gets attributed to the week of its earliest known timestamp (frontmatter <code>opened</code>/<code>discovered</code> date if present, else stat birthtime, else mtime). Cumulative count = total apparatus generators that EXIST as of week N.</p>
          <p><strong>Soph-D (autonomous actions per week):</strong> reads <code>projects/*/workspace/cage_engagement.jsonl</code>. Each line has its own <code>utc</code> timestamp; events are bucketed by their actual emission week, not by file mtime. The value is the sum of <code>engaged_count</code> across all events that week — the count of cage-gate engagements the apparatus performed autonomously.</p>
        </details>
      </div>

      <div className="panel">
        <h3>2. Insight — volume (count and content)</h3>
        <SoWhat data={data} k="insight_volume" />
        <div ref={insightRef} />
        <div className="legend">F-row creates/closures from EXPERIMENT_TRACK_RECORD; project artifacts from projects/*/workspace/*; verified axioms from per-project ledgers. (Paper line-count deliberately excluded — a gameable, self-defeating proxy.)</div>
        <details className="info">
          <summary>How this is calculated</summary>
          <ul>
            <li><strong>Insight-A (F-row creates):</strong> count of <code>| E-{'{ID}'} |</code> lines added to <code>research_areas/EXPERIMENT_TRACK_RECORD.md</code> per week, dated by the date column in the row.</li>
            <li><strong>Insight-B (F-row closures):</strong> subset of A where the row's prose matches <code>verified|theorem proven|machine-check|falsified.*finding|counterexample.*found</code>.</li>
            <li><em>Insight-C (paper line-count) was removed — line count is a gameable, self-defeating proxy (more lines ≠ more value).</em></li>
            <li><strong>Insight-D (project workspace artifacts):</strong> count of <code>.md</code>/<code>.json</code>/<code>.jsonl</code>/<code>.py</code>/<code>.yaml</code> files in <code>projects/*/workspace/</code> + project root. Captures NS phase work, gravity proofs, consciousness theory, etc. — the bulk of substantive research output.</li>
            <li><strong>Insight-E (verified axioms):</strong> count of non-sentinel axioms in <code>projects/*/verified_axioms.json</code> (excludes "no inherited truth" sentinel entries), attributed by file mtime.</li>
          </ul>
          <p>All metrics are pure counts — <em>volume only, not quality</em>. Quality lives in panel 3.</p>
        </details>
      </div>

      <div className="panel">
        <h3>3. Insight — taste (contextualized rater 0-5)</h3>
        <SoWhat data={data} k="taste" />
        <div ref={tasteRef} />
        <div className="legend">N≈{tasteAvgN}/week stratified across 11 kinds, {tasteNWeeks} weeks total. Rater anchored on top-cited seams + memory entries. The un-anchored cold rater gave no 5s and over-rated mechanism-looking content; the anchored rater is stricter.</div>
        <details className="info">
          <summary>How taste is calculated (read this if it's the first time)</summary>
          <p><strong>The pipeline:</strong></p>
          <ol>
            <li><code>scripts/public/mining/sample_artifacts_for_taste.py</code> walks 11 artifact kinds (F-rows, seams, paper sections, project evaluations, verified axioms, project workspace markdown, raw evidence inputs, evidence files, project charters, concept docs, memory entries, top-level reasoning) across the corpus.</li>
            <li>Stratified sampling: ~25 per week, balanced across kinds, capped at 3 per project so NS doesn't dominate. Random shuffle so the rater can't infer week from order.</li>
            <li><code>scripts/public/mining/build_context_primer.py</code> compiles a primer of (a) top-15 most-cited seams in the reference graph, (b) the operator-curated memory entries, (c) anti-pattern catalog headers, (d) DECISION_LOG headers.</li>
            <li>A <strong>cold sub-agent</strong> (no context contamination from this codebase) reads the primer FIRST, then rates each sample 0-5: <strong>0</strong> = boilerplate, <strong>1</strong> = trivially observable, <strong>2</strong> = useful but expected, <strong>3</strong> = sharp framing, <strong>4</strong> = high-reuse / mechanism-revealing, <strong>5</strong> = paradigm-shifting (would force rewriting one of the most-cited seams in the primer).</li>
            <li><code>scripts/public/mining/aggregate_taste.py</code> bins ratings by the sample's week (revealed only at aggregation time) and computes mean / max / count of ≥4 / count of ≥5 per week.</li>
          </ol>
          <p><strong>Why the primer matters:</strong> the cold rater without the primer gave <em>zero 5s</em> and over-rated mechanism-looking content at 4. With the primer (so it knows which seams are central in THIS codebase), the rater is stricter overall.{tastePeak && tasteFirst && tasteLast && (
            <> Across the {tasteNWeeks} rated weeks, the weekly mean peaks at <strong>{tastePeak.mean.toFixed(2)}</strong> in the week of <strong>{tastePeak.week}</strong> (first week {tasteFirst.mean_score.toFixed(2)}, latest week {tasteLast.mean_score.toFixed(2)}). With N≈{tasteAvgN}/week the per-week numbers are noisy — read the shape across weeks, not any single point.</>
          )}</p>
          <p><strong>Cost discipline:</strong> ratings persist in <code>analytics/public/queries/taste/taste_ledger.json</code> keyed by content SHA. A re-run only rates artifacts whose content changed. Bumping <code>CODE_VERSION</code> or <code>--require-primer-match</code> invalidates stale entries.</p>
          <p><strong>Caveat:</strong> N≈{tasteAvgN}/week with ±1 rater spread means individual week comparisons are noisy. The trajectory across the {tasteNWeeks} rated weeks is the signal, not any single week.</p>
        </details>
      </div>

      <div className="panel">
        <h3>4. Compounding — cross-artifact reference graph</h3>
        <SoWhat data={data} k="compounding" />
        <div ref={compRef} />
        <div className="legend"><strong>Inbound from later weeks:</strong> how much this week's work is cited by later work (became depended-on downstream). <strong>Outbound to earlier weeks:</strong> how much this week's work pulls from prior context (compounding). A rising compounding ratio means newer artifacts cite more accumulated history per artifact.</div>
        <details className="info">
          <summary>How this is calculated</summary>
          <p><code>scripts/public/mining/mine_reference_graph.py</code> walks every apparatus markdown file (capped at 2000 nodes for performance) and extracts citations using two patterns:</p>
          <ul>
            <li><strong>GP-N references:</strong> <code>GP-148</code>, <code>gp226</code>, etc. → resolved to the matching seam file.</li>
            <li><strong>File-path references:</strong> <code>src/ztare/...</code>, <code>projects/.../phase5fa.md</code>, <code>papers/paper4/draft.md</code> → resolved by suffix match against the node table.</li>
          </ul>
          <p>Builds a directed graph: edge from citer → citee. Then per-week:</p>
          <ul>
            <li><strong>Inbound from later weeks</strong> — sum of edges where this week's nodes are cited by future-week nodes. <em>Became depended-on downstream:</em> high inbound = work that future research builds on.</li>
            <li><strong>Outbound to earlier weeks</strong> — sum of edges where this week's nodes cite earlier-week nodes. <em>Compounding:</em> high outbound = current work is pulling on accumulated history.</li>
            <li><strong>Compounding ratio</strong> = outbound_to_earlier / nodes-this-week. Normalizes for week-volume; a high ratio means individual artifacts are pulling more historical context than usual.</li>
          </ul>
          {compPeak && (
            <p>The compounding ratio peaks at <strong>{compPeak.ratio.toFixed(2)}</strong> in the week of <strong>{compPeak.week}</strong> — a dimension that raw volume and per-artifact taste don't capture. Recompute it each refresh; it moves with the corpus.</p>
          )}
        </details>
      </div>

      <div className="panel">
        <h3>5. Confounds — general activity & external events</h3>
        <div ref={confRef} />
        <div className="legend">If the apparatus story is real, sophistication and taste curves should diverge from confound curves. If they track together, the apparent acceleration is general activity volume.</div>
        <details className="info">
          <summary>How this is calculated</summary>
          <ul>
            <li><strong>Confound-A (code activity):</strong> count of <code>.py</code>/<code>.md</code>/<code>.yaml</code> files in <code>src/</code> + <code>scripts/</code> with mtime in the week. Captures "amount of typing/editing happening" regardless of whether it's apparatus-relevant.</li>
            <li><strong>Confound-B (total artifact creation):</strong> count of <em>all</em> apparatus-shaped files created repo-wide per week. The broadest possible activity-volume signal.</li>
            <li><strong>Confound-C (external events):</strong> manually curated in <code>org/runtime/external_events.yaml</code>. Paper deadlines, model upgrades, GPU runs, conferences — anything not apparatus-driven that might create activity.</li>
          </ul>
          <p>If sophistication / insight / compounding curves rise together with confounds, the apparent acceleration is mostly "operator working more hours that week." If they diverge — sophistication up, confounds flat — the apparatus signal is something other than raw typing volume.</p>
        </details>
      </div>

      <div className="panel">
        <h3>Auto-detected real inflections (≥3 metrics step-change)</h3>
        {(() => {
          const real = (inflections?.ranked_inflections || []).filter((r) => r.verdict === "real_inflection");
          if (real.length === 0) return <p><em>none</em></p>;
          return (
            <table>
              <thead><tr><th>Week</th><th>Score</th><th>Metrics</th><th>External events</th></tr></thead>
              <tbody>
                {real.map((r) => (
                  <tr key={r.week}>
                    <td>{r.week}</td>
                    <td>{r.convergence_score}</td>
                    <td>{r.metrics.map((m) => m.replace(/_/g, " ")).join(", ")}</td>
                    <td>{(r.coincident_external_events || []).map((e) => e.label).join("; ") || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          );
        })()}
      </div>
    </>
  );
}
