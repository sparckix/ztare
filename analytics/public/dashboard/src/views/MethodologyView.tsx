// Publish-safety (dashboard_publish_safety_spec_2026_05_17 M1): the
// contextualized-rater primer is the private human-curated memory index and
// MUST NOT be inlined into the public bundle. The methodology is described
// publicly without dumping the private anchor.

import bundle from "../data/dashboard_bundle.json";
import type { TasteData } from "../lib/types";

// Numbers in the prose below are derived from the same build-time bundle
// every other view consumes (see lib/data.ts), never hardcoded — so the
// copy can't drift from the live readings. We describe the taste curve by
// its observed start, end, peak, and week count rather than asserting a
// monotone trend the data may not support.
function tasteShape() {
  const taste = (bundle as { datasets?: { taste?: TasteData | null } })
    ?.datasets?.taste;
  const stats = taste?.weekly_stats;
  if (!stats) return null;
  const weeks = Object.keys(stats).sort();
  if (weeks.length === 0) return null;
  const means = weeks.map((w) => stats[w].mean_score);
  const first = means[0];
  const last = means[means.length - 1];
  const peak = Math.max(...means);
  const trough = Math.min(...means);
  return { nWeeks: weeks.length, first, last, peak, trough };
}

const fmt = (x: number) => x.toFixed(1);

export function MethodologyView() {
  const t = tasteShape();
  return (
    <>
      <div className="methodology">
        <h3>What this dashboard measures</h3>
        <p>
          One question: <strong>is the research apparatus getting better at
          its own job over time, and can we show it without grading
          ourselves?</strong> The frontier framing (Anthropic, 2026) is that
          execution is becoming cheap and the binding constraint shifts to{" "}
          <em>judgment</em> — choosing which problems matter, which results to
          trust, and when an approach is a dead end. This dashboard tracks
          whether that judgment layer is compounding, measured{" "}
          <strong>model-agnostically</strong>: the work is done by whatever
          agent (Claude, Codex, or a human reviewer), and the gain lives in the
          apparatus, not inside any one model.
        </p>

        <h3>The two realized-gain readings (the honest ones)</h3>
        <ol>
          <li>
            <strong>Insight-quality trajectory.</strong> A contextualized
            rater scores a blinded weekly sample of artifacts 0–5 for how
            much genuine insight each carries.{" "}
            {t ? (
              <>
                Over the observed {t.nWeeks}-week window the weekly mean has
                moved between {fmt(t.trough)} and {fmt(t.peak)} — opening near{" "}
                {fmt(t.first)} and most recently {fmt(t.last)}. The week-to-week
                swing is wide, so we report the level and its spread; the short
                window does not support a directional trend claim.
              </>
            ) : (
              <>The weekly mean is read off the live taste pipeline.</>
            )}{" "}
            We track this as the insight signal, not a count of activity.
          </li>
          <li>
            <strong>Realized primitive gain.</strong> Of the apparatus's
            registered primitives, the fraction that{" "}
            <em>became depended-on downstream</em> — scored from exogenous
            evidence (an independent catch-ledger reference, or measured
            downstream use), not from narration. This is the realized-gain
            denominator the candidate list lacks.
          </li>
        </ol>
        <p>
          The "recursive-gain candidates" tab is the <em>forward</em> half — a
          ranked list of moves that <em>could</em> compound. It is a
          recommender, not evidence; a candidate only counts as realized when
          an independent ledger shows it was acted on. Read the two together:
          candidates ahead, realized measure behind.
        </p>

        <h3>How the trajectory panels are computed</h3>
        <p>
          Four independent, deterministic pipelines, each writing a JSON that
          this page imports at build time (only the taste rater is LLM-based):
        </p>
        <ol>
          <li>
            <strong>Volume.</strong> Walks the apparatus, bins artifacts per
            week by authored date, separating agent-work from iter-loop work
            (most authored work is agent-work outside the loop — the
            agent-agnostic substrate).
          </li>
          <li>
            <strong>Inflection.</strong> A robust (MAD-based) change-point
            detector per curve; a week counts as a real inflection only when
            several independent curves step at once.
          </li>
          <li>
            <strong>Reference graph.</strong> Extracts citations (GP-ids +
            file references) into a directed graph, then per week reports how
            much new work builds on earlier work — the structural compounding
            signal.
          </li>
          <li>
            <strong>Taste.</strong> A stratified weekly sample, blinded by
            week, rated against a fixed primer so the 0–5 scale is calibrated.
            Ratings are cached by content hash, so re-runs only re-rate what
            changed.
          </li>
        </ol>

        <h3>Honest limitations (read these before trusting any number)</h3>
        <p>
          Every metric here except the externally-checked slice is{" "}
          <strong>self-produced</strong> — a page that grades the apparatus
          that built it is itself a place bias can hide, so treat each number
          as an internal signal, not a benchmark. The contextualized rater is
          anchored on a primer, so changing the primer changes the
          distribution. The week count is short for inferential change-point
          claims. And the readings can go stale: if the trajectory's last week
          is old, the pipeline simply has not been re-run — the dashboard flags
          that rather than pretending the line ended.
        </p>
      </div>

      <div className="panel">
        <h3>Why "agent-agnostic recursive gain"</h3>
        <p style={{ fontSize: 13, color: "#666", margin: 0 }}>
          Improvement does not require an in-loop evaluation or a particular
          model. Any agent's work that reaches the apparatus's data ecosystem
          is harvested by the mining layer and fed back into apparatus state.
          The model is a frozen, swappable component; the judgment
          discipline — anti-laundering governance ("which results to trust"),
          calibration ("when an approach is a dead end"), and this mining
          layer — persists across model swaps and is what compounds.
        </p>
      </div>
    </>
  );
}
