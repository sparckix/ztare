import { useState, useMemo } from "react";
import type { DashboardData } from "../lib/data";

const CONFIDENCE_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };
const COST_ORDER: Record<string, number> = { trivial: 0, day: 1, week: 2, month: 3 };

const CONFIDENCE_TAG: Record<string, string> = {
  high: "tag tag-signal",
  medium: "tag tag-amber",
  low: "tag tag-slate",
};
const COST_TAG: Record<string, string> = {
  trivial: "tag tag-signal",
  day: "tag tag-amber",
  week: "tag tag-amber",
  month: "tag tag-warn",
};

export function RecursiveGainView({ data }: { data: DashboardData }) {
  const { recursiveGainCandidates: rg } = data;
  const [confidenceFilter, setConfidenceFilter] = useState<string>("");
  const [mechanismFilter, setMechanismFilter] = useState<string>("");
  const [sourceFilter, setSourceFilter] = useState<string>("");

  const filtered = useMemo(() => {
    if (!rg) return [];
    return rg.candidates.filter((c) => {
      if (confidenceFilter && c.confidence !== confidenceFilter) return false;
      if (mechanismFilter && c.mechanism !== mechanismFilter) return false;
      if (sourceFilter && c.source !== sourceFilter) return false;
      return true;
    });
  }, [rg, confidenceFilter, mechanismFilter, sourceFilter]);

  if (!rg) {
    return <div className="error">No recursive-gain candidates — run mine_recursive_gain_candidates.py first</div>;
  }

  const mechanisms = Array.from(new Set(rg.candidates.map((c) => c.mechanism))).sort();
  const sources = Array.from(new Set(rg.candidates.map((c) => c.source))).sort();

  return (
    <>
      <div className="methodology">
        <h3>Recursive-gain candidates — the forward half</h3>
        <p>
          This is the <strong>forward recommender</strong>: a ranked list of moves that{" "}
          <em>could</em> compound apparatus capability, aggregated from five mining surfaces
          (cross-audit, structural-analogy, closure-pattern, reference-graph, process-catalog).
          It is a list of bets, <strong>not evidence of gain</strong>. A candidate counts as
          realized only when an independent ledger shows it was acted on — see the{" "}
          <strong>realized-gain</strong> readings on the P0 tab (insight-quality trajectory +
          the fraction of registered primitives that became depended-on downstream). Read them
          together: candidates ahead, realized measure behind.
        </p>
        <ul>
          <li><strong>Mechanism</strong> — kind of gain (retire-decorative, wire-one-shot-as-loop, promote-to-gate, new-substrate, revive-stalled-loop)</li>
          <li><strong>Cost</strong> — operator effort estimate (trivial / day / week / month)</li>
          <li><strong>Confidence</strong> — signal strength from the source miner</li>
          <li><strong>Source</strong> — which mining surface produced it</li>
        </ul>
        <p style={{ fontSize: 13, color: "#666" }}>
          <strong>Honest caveat:</strong> these candidates are only as fresh as their upstream
          scorecards, and follow-through is measured <em>exogenously</em> (a candidate's GP-id
          appearing in the catch ledger). A high dead-letter rate means the mining is surfacing
          moves nobody ships — a signal to read, not to hide. Re-run{" "}
          <code>python scripts/public/mining/mine_recursive_gain_candidates.py</code> after the
          upstream miners refresh.
        </p>
      </div>

      <div className="panel">
        <h3>By the numbers</h3>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ fontSize: 13 }}><strong>{rg.n_candidates}</strong> total candidates</div>
          {Object.entries(rg.by_source).map(([k, v]) => (
            <span key={k} className="chip"><code>{k}</code>: {v}</span>
          ))}
        </div>
      </div>

      <div className="controls">
        <label>Confidence:
          <select value={confidenceFilter} onChange={(e) => setConfidenceFilter(e.target.value)}>
            <option value="">all</option>
            <option value="high">high</option>
            <option value="medium">medium</option>
            <option value="low">low</option>
          </select>
        </label>
        <label>Mechanism:
          <select value={mechanismFilter} onChange={(e) => setMechanismFilter(e.target.value)}>
            <option value="">all</option>
            {mechanisms.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </label>
        <label>Source:
          <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
            <option value="">all</option>
            {sources.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <span style={{ marginLeft: 12, fontSize: 12, color: "var(--text-faint)" }}>
          {filtered.length} of {rg.n_candidates} shown
        </span>
      </div>

      <div className="panel">
        <h3>Ranked candidates (high-confidence + low-cost first)</h3>
        <table>
          <thead>
            <tr>
              <th style={{ width: 90 }}>Confidence</th>
              <th style={{ width: 70 }}>Cost</th>
              <th style={{ width: 220 }}>Mechanism</th>
              <th>Entity</th>
              <th>Why this is a recursive-gain bet</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((c, i) => (
              <tr key={`${c.source}-${c.entity}-${i}`}>
                <td>
                  <span className={CONFIDENCE_TAG[c.confidence] || "tag tag-slate"}>
                    {c.confidence}</span>
                </td>
                <td>
                  <span className={COST_TAG[c.cost] || "tag tag-slate"}>
                    {c.cost}</span>
                </td>
                <td><code style={{ fontSize: 11 }}>{c.mechanism}</code></td>
                <td><code style={{ fontSize: 11 }}>{c.entity}</code></td>
                <td style={{ fontSize: 12, color: "var(--text-dim)", lineHeight: 1.45 }}>{c.rationale}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="caveat">
        <strong>The strange-loop bet:</strong> watch for the <code>strange_loop_ZTARE_substrate</code>{" "}
        mechanism in the table above. That's the meta-recursive proposal — a new ZTARE substrate
        that ingests evidence from outside-of-ZTARE work (Research Director output on NS, gravity,
        etc.) as input. Closes the recursive-gain loop that ZTARE-on-ZTARE used to provide before
        most R&D moved outside the ZTARE evaluation surface. See GP-134 for the seam writeup.
      </div>
    </>
  );
}
