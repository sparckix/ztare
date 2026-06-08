import { LineChart, Line, ResponsiveContainer, YAxis, Tooltip } from "recharts";
import type { DashboardData } from "../lib/data";
import type { P0Metric, P0MetricsHistory } from "../lib/types";

const GROUP_TITLE: Record<string, string> = {
  "3.1_exogenous": "Exogenous anchors — the only Goodhart-resistant metrics",
  "3.2_state": "State — where the work is",
  "3.3_insight": "Insight generation (self-measured)",
  "3.4_recursive": "Recursive improvement (self-measured)",
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

function fmt(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "object")
    return Object.entries(v as Record<string, unknown>)
      .map(([k, val]) => `${k}: ${typeof val === "object" ? JSON.stringify(val) : val}`)
      .join("  ·  ");
  return String(v);
}

function historyFor(history: P0MetricsHistory | null, m: P0Metric):
    { points: Array<{ x: string; y: number }>; sparkKey: string } {
  if (!history || history.length === 0) return { points: [], sparkKey: m.key };
  const tryKey = (k: string) => {
    const pts: Array<{ x: string; y: number }> = [];
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
      if (pts.length >= SPARK_MIN) return { points: pts, sparkKey: k };
    }
  }
  return { points: [], sparkKey: m.key };
}

function Sparkline({ points, sparkKey }:
    { points: Array<{ x: string; y: number }>; sparkKey: string }) {
  if (points.length < SPARK_MIN) return null;
  const ys = points.map((p) => p.y);
  const latest = ys[ys.length - 1];
  const first = ys[0];
  const delta = latest - first;
  const trend = delta > 0 ? "↑" : delta < 0 ? "↓" : "→";
  const subKey = sparkKey.includes(".") ? sparkKey.split(".").slice(1).join(".") : null;
  return (
    <div className="p0-spark" title={`${sparkKey}: ${points.length} cycles`}>
      <div className="p0-spark-chart">
        <ResponsiveContainer width={120} height={32}>
          <LineChart data={points} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
            <YAxis hide domain={["dataMin", "dataMax"]} />
            <Tooltip
              cursor={false}
              contentStyle={{ background: "#15171c", border: "1px solid #262a31",
                              fontSize: 11, padding: "4px 8px" }}
              labelFormatter={(v: unknown) =>
                typeof v === "string" ? v.slice(0, 10) : String(v ?? "")}
              formatter={(v: unknown) => [String(v), sparkKey]}
            />
            <Line type="monotone" dataKey="y" stroke="#e8a33d" strokeWidth={1.5}
                  dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="p0-spark-meta">
        <span className="p0-spark-trend">{trend}</span>
        <span className="p0-spark-n">{points.length} cycles{subKey ? ` · .${subKey}` : ""}</span>
      </div>
    </div>
  );
}

// Pull a single metric's value off the live p0Metrics list by key, so
// the glance cards below are derived from data — never re-hardcoded.
// Returns the metric's `value` (scalar / breakdown object / series), or
// null if the key is absent.
function metricValue(metrics: P0Metric[], key: string): unknown {
  return metrics.find((m) => m.key === key)?.value ?? null;
}

// Narrow a breakdown value to its numeric subfield, tolerating a missing
// metric or missing field (returns null so the caller can fall back to "—").
function subNum(v: unknown, field: string): number | null {
  if (v && typeof v === "object" && field in (v as Record<string, unknown>)) {
    const n = (v as Record<string, unknown>)[field];
    if (typeof n === "number" && Number.isFinite(n)) return n;
  }
  return null;
}

function numOrDash(n: number | null): string {
  return n === null ? "—" : String(n);
}

function MetricRow({ m, history }: { m: P0Metric; history: P0MetricsHistory | null }) {
  const tierClass = m.tier === "A" ? "tag-signal" : m.tier === "B" ? "tag-amber"
    : m.tier === "C" ? "tag-slate" : "tag-warn";
  const spark = historyFor(history, m);
  return (
    <div className={`p0-row p0-${m.status}`}>
      <div className="p0-head">
        <span className="p0-label">{m.label}</span>
        <span className="p0-badges">
          <span className={`tag ${tierClass}`}>tier {m.tier}</span>
          <span className="tag tag-slate">{m.lane}</span>
          {m.self_measured
            ? <span className="tag tag-warn">self-measured</span>
            : <span className="tag tag-signal">exogenous/consumed</span>}
          {m.status !== "ok" && <span className="tag tag-warn">{m.status}</span>}
        </span>
      </div>
      <div className="p0-value-row">
        <div className="p0-value">
          {m.status === "not_yet_computable"
            ? <em>not yet computable — null by design, not fabricated</em>
            : fmt(m.value)}
        </div>
        <Sparkline points={spark.points} sparkKey={spark.sparkKey} />
      </div>
      <div className="p0-caveat">{m.caveat}
        {m.owner && m.owner !== "p0_rollup" &&
          <span className="p0-owner"> · owner: {m.owner}</span>}
      </div>
    </div>
  );
}

export function P0View({ data }: { data: DashboardData }) {
  const p0 = data.p0Metrics;
  const history = data.p0MetricsHistory;
  const sw = data.graphSowhat?.panels?.p0;
  if (!p0 || !p0.metrics) {
    return <div className="panel"><h3>P0 Metrics</h3>
      <div className="legend">p0_metrics.json not wired — run the orchestrator (Phase 2c).</div></div>;
  }
  const order = p0.group_order || Object.keys(GROUP_TITLE);
  const byGroup = (g: string) => p0.metrics.filter((m) => m.group === g);

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
  const extPos = subNum(
    (ext as Record<string, unknown> | null)?.positive, "distinct_tags");
  const extNeg = subNum(
    (ext as Record<string, unknown> | null)?.negative, "distinct_tags");
  const brierSeries = metricValue(metrics, "brier_per_period");
  const brierRow = Array.isArray(brierSeries) ? brierSeries[brierSeries.length - 1] : null;
  const brier = subNum(brierRow, "brier");
  const brierBase = subNum(brierRow, "uniform_baseline");

  // Self-correction: who diagnosed the catches (apparatus vs operator).
  const diag = metricValue(metrics, "operator_vs_apparatus_diagnosis_ratio");
  const apparatus = subNum(diag, "apparatus");
  const operator = subNum(diag, "operator");

  // Insight density: latest contextualized-taste read + its weekly trend.
  const taste = metricValue(metrics, "contextualized_taste");
  const tasteLatest = subNum(taste, "latest");
  const tasteMax = subNum(taste, "max");
  const traj = metricValue(metrics, "recursive_gain_trajectory");
  const trajSeries = (traj as { series?: Array<{ week: string; mean: number }> } | null)?.series;
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
      sub: `${numOrDash(apparatus)} catches diagnosed by apparatus, ${numOrDash(operator)} by operator`,
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

  return (
    <div>
      {sw && (
        <div className="p0-verdict">
          <div className="p0-verdict-tag">So what — the honest verdict</div>
          <div className="p0-verdict-head">{sw.headline}</div>
          {sw.detail && <div className="p0-verdict-detail">{sw.detail}</div>}
        </div>
      )}

      <div className="p0-glance">
        {glance.map((g) => (
          <div className={`p0-gcard p0-g-${g.tone}`} key={g.k}>
            <div className="p0-gv">{g.v}</div>
            <div className="p0-gk">{g.k}</div>
            <div className="p0-gs">{g.sub}</div>
          </div>
        ))}
      </div>

      <div className="p0-pagecaveat">
        <strong>How to read this:</strong> {p0.page_caveat} Only the green
        "exogenous" panel resists this. Everything tagged
        <span className="tag tag-warn">self-measured</span> is the apparatus
        grading itself; everything tagged
        <span className="tag tag-signal">exogenous/consumed</span> has real
        independence. Tier A→C = how much to trust the number.
      </div>

      {order.map((g) => {
        const rows = byGroup(g);
        if (!rows.length) return null;
        const exo = g === "3.1_exogenous";
        return (
          <div className={`panel ${exo ? "p0-exo" : ""}`} key={g}>
            <h3>{GROUP_TITLE[g] || g}</h3>
            {rows.map((m) => <MetricRow key={m.key} m={m} history={history} />)}
          </div>
        );
      })}

      <div className="foot">
        GP-236 P0 rollup · deterministic, regenerated each cycle ·
        consumed rows owned by their producing track, never recomputed here
      </div>
    </div>
  );
}
