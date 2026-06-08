import { useState } from "react";
import type { DashboardData } from "../lib/data";

export function ConsequentialArtifactsView({ data }: { data: DashboardData }) {
  const { consequentialArtifacts: ca } = data;
  const weeks = ca ? Object.keys(ca.weeks).sort() : [];
  const [selectedWeek, setSelectedWeek] = useState<string>(
    weeks[weeks.length - 1] || ""
  );

  if (!ca || weeks.length === 0) {
    return <div className="error">No consequential-artifacts data — run build_consequential_artifacts.py first</div>;
  }

  const wk = ca.weeks[selectedWeek];

  return (
    <>
      <div className="methodology">
        <h3>What actually happened each week</h3>
        <p>
          Per-week digest of artifacts the rater scored ≥{ca.score_floor} (mechanism-revealing
          or sharper) plus the most-cited nodes (heavily-cited infrastructure). This is what's
          driving each week's metrics in the Trajectory tab — pick a week, see the artifacts
          that produced its insight density.
        </p>
        <p>
          <strong>Source:</strong> joins <code>_taste_metadata.json</code> (sample/week mapping)
          + <code>taste_ledger.json</code> (scores) + <code>reference_graph.json</code> (in-degrees).
          Re-run with <code>python scripts/public/mining/build_consequential_artifacts.py</code>.
        </p>
      </div>

      <div className="controls">
        <label>Week: </label>
        {weeks.map((w) => (
          <button
            key={w}
            className={`tab ${w === selectedWeek ? "active" : ""}`}
            onClick={() => setSelectedWeek(w)}
            style={{ padding: "6px 12px", fontSize: 13 }}
          >
            {w} ({ca.weeks[w].n_rated_above_floor})
          </button>
        ))}
      </div>

      {wk && (
        <>
          <div className="panel">
            <h3>{selectedWeek} — at a glance</h3>
            <div style={{ display: "flex", gap: 24, fontSize: 13, color: "#444", marginBottom: 12 }}>
              <div><strong>{wk.n_rated_above_floor}</strong> artifacts rated ≥{ca.score_floor}</div>
              <div><strong>{wk.n_cited_above_floor}</strong> artifacts cited ≥3 times</div>
            </div>

            {Object.keys(wk.rated_by_kind).length > 0 && (
              <>
                <div style={{ fontSize: 12, color: "#666", marginBottom: 6 }}>By kind:</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                  {Object.entries(wk.rated_by_kind)
                    .sort((a, b) => b[1] - a[1])
                    .map(([k, n]) => (
                      <span
                        key={k}
                        style={{
                          fontSize: 12,
                          background: "#f0f4f8",
                          padding: "3px 8px",
                          borderRadius: 4,
                          border: "1px solid #d8e1ee",
                        }}
                      >
                        <strong>{k}</strong>: {n}
                      </span>
                    ))}
                </div>
              </>
            )}
          </div>

          {wk.top_rated.length > 0 && (
            <div className="panel">
              <h3>Top-rated artifacts (mechanism-revealing or better)</h3>
              <table>
                <thead>
                  <tr>
                    <th style={{ width: 50 }}>Score</th>
                    <th style={{ width: 130 }}>Kind</th>
                    <th>Path</th>
                    <th>Why it scored</th>
                  </tr>
                </thead>
                <tbody>
                  {wk.top_rated.map((r) => (
                    <tr key={r.sample_id}>
                      <td style={{ fontWeight: 600, color: r.score >= 4 ? "#1f77b4" : "#444" }}>
                        {r.score}
                      </td>
                      <td><code>{r.kind}</code></td>
                      <td><code style={{ fontSize: 11 }}>{r.path}</code></td>
                      <td style={{ fontSize: 12, color: "#444" }}>{r.rationale}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {wk.top_cited.length > 0 && (
            <div className="panel">
              <h3>Most-cited artifacts (heavily-cited infrastructure created this week)</h3>
              <table>
                <thead>
                  <tr>
                    <th style={{ width: 80 }}>In-degree</th>
                    <th style={{ width: 130 }}>Kind</th>
                    <th>Path</th>
                  </tr>
                </thead>
                <tbody>
                  {wk.top_cited.map((c, i) => (
                    <tr key={`${c.path}-${i}`}>
                      <td style={{ fontWeight: 600 }}>{c.in_degree}</td>
                      <td><code>{c.kind}</code></td>
                      <td><code style={{ fontSize: 11 }}>{c.path}</code></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {wk.narrative_seeds.length > 0 && (
            <div className="panel">
              <h3>What the rater said about the top 3</h3>
              <ul style={{ fontSize: 13, color: "#333", lineHeight: 1.5 }}>
                {wk.narrative_seeds.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </>
  );
}
