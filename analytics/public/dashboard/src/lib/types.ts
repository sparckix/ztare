// Shared types for the dashboard data files. Loaded from
// public/data/ via fetch() at runtime; refresh-data.sh copies the
// latest analytics/queries/*.json there.

export interface TrajectoryCurves {
  audit_timestamp_utc: string;
  n_weeks: number;
  weeks: string[];
  curves: Record<string, Record<string, number>>;
  external_events: Array<{ date: string; kind: string; label: string }>;
}

export interface InflectionData {
  ranked_inflections: Array<{
    week: string;
    convergence_score: number;
    metrics: string[];
    verdict: string;
    coincident_external_events?: Array<{ date: string; kind: string; label: string }>;
  }>;
}

export interface TasteData {
  audit_timestamp_utc: string;
  n_samples_with_ratings: number;
  weekly_stats: Record<string, {
    n_rated: number;
    mean_score: number;
    max_score: number;
    n_high_quality_ge4: number;
    n_paradigm_shift_ge5: number;
  }>;
}

export interface GraphNode {
  id: string;
  kind: string;
  week: string;
  size_bytes?: number;
  in_degree?: number;
  out_degree?: number;
}

export interface GraphEdge {
  from: string;
  to: string;
  weight: number;
  kinds: string[];
}

export interface ReferenceGraph {
  audit_timestamp_utc: string;
  n_nodes: number;
  n_edges: number;
  weekly_stats: Record<string, {
    n_nodes: number;
    total_in_degree: number;
    total_out_degree: number;
    n_inbound_from_later_weeks: number;
    n_outbound_to_earlier_weeks: number;
  }>;
  nodes: GraphNode[];
  edges: GraphEdge[];
  top_cited_nodes: GraphNode[];
}

export interface ConsequentialArtifactsByWeek {
  audit_timestamp_utc: string;
  score_floor: number;
  weeks: Record<string, {
    week: string;
    n_rated_above_floor: number;
    n_cited_above_floor: number;
    top_rated: Array<{
      sample_id: string;
      kind: string;
      path: string;
      score: number;
      rationale: string;
      content_sha: string;
    }>;
    top_cited: Array<{
      path: string;
      kind: string;
      in_degree: number;
      out_degree: number;
      week: string;
    }>;
    rated_by_kind: Record<string, number>;
    narrative_seeds: string[];
  }>;
}

export interface RecursiveGainCandidates {
  audit_timestamp_utc: string;
  n_candidates: number;
  by_source: Record<string, number>;
  by_mechanism: Record<string, number>;
  candidates: Array<{
    source: string;
    entity: string;
    kind: string;
    mechanism: string;
    cost: string;
    confidence: string;
    rationale: string;
    details: string;
  }>;
}

export interface Bifurcation {
  generated_utc: string;
  scanned: number;
  excluded_generated_vendored: number;
  indexed: number;
  by_tree: Record<string, number>;
  bifurcation: {
    iter_loop_artifacts: number;
    agent_work_artifacts: number;
    agent_work_share: number;
  };
  as_of_today: {
    date: string;
    modified_today: { all: number; iter_loop: number; agent_work: number };
    modified_last_7d: { all: number; iter_loop: number; agent_work: number };
    note: string;
  };
}

export interface GraphSowhat {
  authored_utc?: string;
  note?: string;
  panels: Record<string, { headline: string; detail?: string; trend?: string }>;
}

export interface P0Metric {
  group: string; key: string; label: string;
  value: unknown; unit: string; lane: string; tier: string;
  source: string; caveat: string;
  self_measured: boolean; status: string; owner: string;
  // value_kind: scalar | breakdown | series | null — tells the renderer
  // how to display value (typography, key:value grid, period rows,
  // not-yet-computable marker).
  value_kind?: "scalar" | "breakdown" | "series" | "null";
}
export interface P0Metrics {
  generated_utc?: string;
  spec?: string;
  page_caveat: string;
  group_order: string[];
  status_counts?: Record<string, number>;
  metrics: P0Metric[];
}

// Append-only history snapshots: one row per build_p0_metrics.py run.
// ``values`` is a flat dict of sparkable numeric headlines (scalars +
// extracted headline subfields from breakdowns, e.g.
// "contextualized_taste.latest"). The dashboard renders a sparkline
// next to any metric whose key has ≥3 history points.
export interface P0MetricsHistoryRow {
  generated_utc: string;
  values: Record<string, number>;
}
export type P0MetricsHistory = P0MetricsHistoryRow[];

declare global {
  interface Window {
    Plotly: any;
    vis: any;
  }
}
