import type {
  TrajectoryCurves, InflectionData, TasteData, ReferenceGraph,
  ConsequentialArtifactsByWeek, RecursiveGainCandidates, Bifurcation,
  GraphSowhat, P0Metrics, P0MetricsHistory,
} from "./types";

// Single bundle import → Vite inlines the entire dashboard payload at
// build time. The single-file dist/index.html therefore needs no
// server, no fetch, no CORS — it works on file:// directly.
//
// The bundle is produced by
// scripts/public/mining/build_dashboard_bundle.py, which folds the nine
// per-dataset query JSONs into one file with the same keys this module
// exposes. Earlier versions of this file imported nine JSONs directly;
// each import path was a drift surface (see
// docs/concepts/reflexive_mining_methodology.md §4 G1–G4). One bundle
// collapses that surface to one.
//
// To refresh data: re-run mining → run scripts/refresh-data.sh →
// npm run build. The refresh script regenerates the bundle and copies
// it to src/data/ (for the bundler) and public/data/ (kept as a
// fallback that does work in dev-server mode).

import bundle from "../data/dashboard_bundle.json";

interface DashboardBundle {
  schema_version: number;
  bundle_generated_utc: string;
  sources: Record<string, string>;
  statuses: Record<string, string>;
  datasets: {
    trajectoryCurves: TrajectoryCurves | null;
    inflections: InflectionData | null;
    taste: TasteData | null;
    referenceGraph: ReferenceGraph | null;
    consequentialArtifacts: ConsequentialArtifactsByWeek | null;
    recursiveGainCandidates: RecursiveGainCandidates | null;
    bifurcation: Bifurcation | null;
    graphSowhat: GraphSowhat | null;
    p0Metrics: P0Metrics | null;
    p0MetricsHistory: P0MetricsHistory | null;
  };
}

export interface DashboardData {
  trajectoryCurves: TrajectoryCurves | null;
  inflections: InflectionData | null;
  taste: TasteData | null;
  referenceGraph: ReferenceGraph | null;
  consequentialArtifacts: ConsequentialArtifactsByWeek | null;
  recursiveGainCandidates: RecursiveGainCandidates | null;
  bifurcation: Bifurcation | null;
  graphSowhat: GraphSowhat | null;
  p0Metrics: P0Metrics | null;
  p0MetricsHistory: P0MetricsHistory | null;
}

export async function loadDashboardData(): Promise<DashboardData> {
  const b = bundle as unknown as DashboardBundle;
  return { ...b.datasets };
}
