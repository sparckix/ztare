import { useState, useMemo } from "react";
import type { DashboardData } from "../lib/data";
import type { RecursiveGainCandidates } from "../lib/types";

type Candidate = RecursiveGainCandidates["candidates"][number];

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

const MECHANISM_COPY: Record<string, { title: string; detail: string }> = {
  retire_or_widen_can_handle: {
    title: "Retire or broaden narrow rules",
    detail: "A rule is present but its eligibility predicate appears too narrow. Either delete it if it adds little, or widen the predicate and test that it engages beyond one substrate.",
  },
  wire_one_shot_as_loop: {
    title: "Turn one-off checks into recurring loops",
    detail: "A useful check exists as a manual or one-time artifact. The candidate is to make it part of the recurring apparatus so the same failure cannot reappear quietly.",
  },
  strange_loop_ZTARE_substrate: {
    title: "Measure external research as a substrate",
    detail: "Bring evidence from outside the ZTARE self-evaluation surface back into the apparatus, so external research output can be scored and acted on.",
  },
};

function mechanismTitle(mechanism: string): string {
  return MECHANISM_COPY[mechanism]?.title || mechanism.replace(/_/g, " ");
}

function mechanismDetail(mechanism: string): string {
  return MECHANISM_COPY[mechanism]?.detail || "Candidate family from the upstream miner. Inspect the raw rows before acting.";
}

function compactList(xs: string[], max = 10): string {
  const visible = xs.slice(0, max);
  const suffix = xs.length > max ? ` +${xs.length - max} more` : "";
  return visible.join(", ") + suffix;
}

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

  const groups = useMemo(() => {
    const byKey = new Map<string, {
      key: string;
      mechanism: string;
      source: string;
      confidence: string;
      cost: string;
      count: number;
      entities: string[];
      rows: Candidate[];
    }>();
    for (const c of filtered) {
      const key = `${c.mechanism}::${c.source}::${c.confidence}::${c.cost}`;
      const g = byKey.get(key) || {
        key,
        mechanism: c.mechanism,
        source: c.source,
        confidence: c.confidence,
        cost: c.cost,
        count: 0,
        entities: [],
        rows: [],
      };
      g.count += 1;
      if (c.entity && !g.entities.includes(c.entity)) g.entities.push(c.entity);
      g.rows.push(c);
      byKey.set(key, g);
    }
    return Array.from(byKey.values()).sort((a, b) =>
      (CONFIDENCE_ORDER[a.confidence] ?? 9) - (CONFIDENCE_ORDER[b.confidence] ?? 9)
      || (COST_ORDER[a.cost] ?? 9) - (COST_ORDER[b.cost] ?? 9)
      || b.count - a.count
      || a.mechanism.localeCompare(b.mechanism));
  }, [filtered]);

  if (!rg) {
    return <div className="error">No recursive-gain candidates — run mine_recursive_gain_candidates.py first</div>;
  }

  const mechanisms = Array.from(new Set(rg.candidates.map((c) => c.mechanism))).sort();
  const sources = Array.from(new Set(rg.candidates.map((c) => c.source))).sort();

  return (
    <>
      <div className="methodology">
        <h3>Recursive-gain backlog</h3>
        <p>
          These are proposed apparatus improvements mined from cross-audit, structural analogy,
          closure patterns, reference graphs, and process catalogs. They are grouped by action
          family so repeated rule-level warnings do not dominate the page. A candidate only
          becomes evidence of gain after an independent ledger shows it was acted on.
        </p>
        <ul>
          <li><strong>Action family</strong> — the recurring improvement pattern.</li>
          <li><strong>Cost</strong> — implementation effort estimate (trivial / day / week / month)</li>
          <li><strong>Confidence</strong> — signal strength from the source miner</li>
          <li><strong>Source</strong> — the mining surface that produced the candidate</li>
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
        <h3>Grouped actions</h3>
        <div className="gain-group-list">
          {groups.map((g) => (
            <div className="gain-group" key={g.key}>
              <div className="gain-group-head">
                <div>
                  <div className="gain-group-title">{mechanismTitle(g.mechanism)}</div>
                  <div className="gain-group-sub">
                    {g.count} row{g.count === 1 ? "" : "s"} from <code>{g.source}</code>
                  </div>
                </div>
                <div className="gain-group-tags">
                  <span className={CONFIDENCE_TAG[g.confidence] || "tag tag-slate"}>
                    {g.confidence}</span>
                  <span className={COST_TAG[g.cost] || "tag tag-slate"}>
                    {g.cost}</span>
                </div>
              </div>
              <p>{mechanismDetail(g.mechanism)}</p>
              <div className="gain-entities">
                <span>Rows:</span> <code>{compactList(g.entities)}</code>
              </div>
            </div>
          ))}
        </div>
      </div>

      <details className="details-panel gain-raw">
        <summary>Raw candidate rows</summary>
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
      </details>

      <div className="caveat">
        <strong>Current read:</strong> the repeated R10/R11-style warnings are one family:
        rules that exist but may engage too narrowly. Treat them as a pruning or broadening
        backlog, not as eight separate conceptual findings.
      </div>
    </>
  );
}
