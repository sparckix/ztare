import type { DashboardData } from "../lib/data";
import { SoWhat } from "./SoWhat";

function SplitBar({
  label, loop, agent, unit,
}: { label: string; loop: number; agent: number; unit: string }) {
  const total = Math.max(1, loop + agent);
  const lp = (loop / total) * 100;
  const ap = (agent / total) * 100;
  return (
    <div className="split-row">
      <div className="lbl">
        <span>{label}</span>
        <span><b>{loop.toLocaleString()}</b> in-loop · <b>{agent.toLocaleString()}</b> out-of-loop {unit}</span>
      </div>
      <div className="split">
        <div className="seg loop" style={{ flexBasis: `${lp}%` }}>
          {lp > 8 ? `${lp.toFixed(lp < 10 ? 1 : 0)}%` : ""}
        </div>
        <div className="seg agent" style={{ flexBasis: `${ap}%` }}>
          {`${ap.toFixed(0)}%`}
        </div>
      </div>
    </div>
  );
}

export function BifurcationView({ data }: { data: DashboardData }) {
  const b = data.bifurcation;
  if (!b || !b.bifurcation) {
    return <div className="panel"><h3>In-Loop vs Out-of-Loop</h3>
      <div className="legend">bifurcation_report.json not yet wired — run the reflexive orchestrator.</div></div>;
  }
  const cum = b.bifurcation;
  const today = b.as_of_today;
  const sharePct = Math.round(cum.agent_work_share * 100);
  const todayShare = today
    ? Math.round((today.modified_last_7d.agent_work /
        Math.max(1, today.modified_last_7d.all)) * 100)
    : sharePct;

  const trees = Object.entries(b.by_tree || {})
    .map(([tree, n]) => ({ tree, n }))
    .sort((a, z) => z.n - a.n);
  const maxN = Math.max(1, ...trees.map((t) => t.n));

  return (
    <div>
      <div className="panel">
        <div className="bif-hero">
          <div className="eyebrow">The architecture bifurcated</div>
          <div className="headline">
            <em>{todayShare}%</em> of this week's authored work
            happens <em>outside</em> the loop
          </div>
          <div className="sub">
            ZTARE's evolutionary iter-loop is now a minority substrate.
            The live work is agent dispatch + governance + mining —
            measured by the apparatus, on itself.
          </div>
        </div>

        <SoWhat data={data} k="bifurcation" />

        <SplitBar
          label="Cumulative — all authored artifacts"
          loop={cum.iter_loop_artifacts}
          agent={cum.agent_work_artifacts}
          unit="artifacts"
        />
        {today && (
          <SplitBar
            label={`As of today (${today.date}) — trailing 7 days`}
            loop={today.modified_last_7d.iter_loop}
            agent={today.modified_last_7d.agent_work}
            unit="artifacts"
          />
        )}

        <div className="stat-grid">
          <div className="stat">
            <div className="v">{b.indexed.toLocaleString()}</div>
            <div className="k">Authored artifacts indexed</div>
          </div>
          <div className="stat">
            <div className="v agent">{sharePct}%</div>
            <div className="k">Out-of-loop (cumulative)</div>
          </div>
          <div className="stat">
            <div className="v agent">{todayShare}%</div>
            <div className="k">Out-of-loop (this week)</div>
          </div>
        </div>
        <div className="legend">
          Generated/vendored excluded ({b.excluded_generated_vendored.toLocaleString()}).
          In-loop = the ZTARE iteration work files themselves (the iter**
          artifacts: debate_log_iter_*, iteration_telemetry,
          current_iteration, iter_*). Out-of-loop = everything else,
          including the rest of <code>projects/</code>. The invariant is the
          iter** files, not which directory they sit in. {today?.note}
        </div>
      </div>

      <div className="panel">
        <h3>Where the authored work lives</h3>
        <div className="legend">
          Authored artifacts by tree. ztare_proofs &amp; analytics dominate
          (NS/Clay formalization + governance). Loop status is a
          cross-cutting file pattern, not a tree — see the split above.
        </div>
        <div className="treebars">
          {trees.map((t) => {
            const pct = (t.n / maxN) * 100;
            return (
              <div className="treebar" key={t.tree}>
                <div className="tb-name">{t.tree}</div>
                <div className="tb-track">
                  <div className="tb-fill"
                    style={{
                      width: `${Math.max(pct, 1.5)}%`,
                      background: "linear-gradient(90deg,#e8a33d,#c8862c)",
                    }} />
                </div>
                <div className="tb-val">{t.n.toLocaleString()}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
