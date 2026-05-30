import { useEffect, useState } from "react";
import { loadDashboardData, type DashboardData } from "./lib/data";
import { P0View } from "./views/P0View";
import { BifurcationView } from "./views/BifurcationView";
import { TrajectoryView } from "./views/TrajectoryView";
import { ReferenceGraphView } from "./views/ReferenceGraphView";
import { MethodologyView } from "./views/MethodologyView";
import { ConsequentialArtifactsView } from "./views/ConsequentialArtifactsView";
import { RecursiveGainView } from "./views/RecursiveGainView";

type Tab =
  | "p0" | "bifurcation" | "trajectory" | "weeks"
  | "recursive_gain" | "graph" | "methodology";

const TABS: Array<[Tab, string]> = [
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
    return (t && TABS.some(([id]) => id === t)) ? (t as Tab) : "p0";
  } catch { return "p0" as Tab; }
})();

export function App() {
  const [tab, setTab] = useState<Tab>(_qpTab);
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData().then(setData).catch((e) => setError(String(e)));
  }, []);

  if (error) {
    return <div className="app-shell"><div className="error">Failed to load data: {error}</div></div>;
  }
  if (!data) {
    return <div className="app-shell"><div className="loading">Loading instruments…</div></div>;
  }

  const asOf = data.bifurcation?.as_of_today?.date;

  return (
    <div className="app-shell">
      <div className="app-header">
        <h1>
          ZTARE
          <span className="sub">Reflexive Research Instrument</span>
        </h1>
        <div className="app-meta">
          {asOf ? <>As of <b>{asOf}</b></> : "—"}<br />
          {data.trajectoryCurves
            ? `mine ${new Date(data.trajectoryCurves.audit_timestamp_utc).toLocaleDateString()}`
            : ""}
        </div>
      </div>

      <div className="caveat">
        <strong>Instrument, not verdict.</strong> Volume panels are activity,
        not insight; the honest insight signal is the contextualized taste
        curve — and the apparatus has demoted its own measurement here before.
      </div>

      <div className="tabs">
        {TABS.map(([id, label]) => (
          <button key={id}
            className={`tab ${tab === id ? "active" : ""}`}
            onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {tab === "p0" && <P0View data={data} />}
      {tab === "bifurcation" && <BifurcationView data={data} />}
      {tab === "trajectory" && <TrajectoryView data={data} />}
      {tab === "weeks" && <ConsequentialArtifactsView data={data} />}
      {tab === "recursive_gain" && <RecursiveGainView data={data} />}
      {tab === "graph" && <ReferenceGraphView data={data} />}
      {tab === "methodology" && <MethodologyView />}

      <div className="foot">
        ZTARE · zero-trust adversarial reasoning · the discipline that keeps
        an agent honest under recursion
      </div>
    </div>
  );
}
