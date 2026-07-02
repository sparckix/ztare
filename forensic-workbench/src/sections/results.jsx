import React from "react";
import { displayMessage, displayText, Block, Tag } from "../design-system.js";

const h = React.createElement;

// Honest tones: ≥85% is strong; 60–85% is "likely, verify"; below is shaky. 78% holding still means a
// ~1-in-5 chance it fails, so it reads amber, not green.
function probTone(p) { return p >= 0.85 ? "ok" : p >= 0.6 ? "warn" : "danger"; }

// The kernel's probability DAG (probability_dag) as a Confidence readout: the outcome probability,
// then each sub-claim with a probability bar + the signal that would move it. The lowest is the weakest
// link — where one counterexample would do the most damage. This is the loop's own forecast, surfaced.
function ConfidenceBlock(dag) {
  const outcome = dag && dag.outcome;
  const nodes = Array.isArray(dag && dag.nodes) ? dag.nodes.filter((n) => n && typeof n.probability === "number") : [];
  if (!outcome || typeof outcome.probability !== "number") return null;
  const pct = Math.round(outcome.probability * 100);
  const weakest = nodes.length ? nodes.reduce((a, b) => (b.probability < a.probability ? b : a)) : null;
  return h(Block, { title: "How confident is the loop?",
    lead: "The loop's probability the thesis holds, decomposed into the sub-claims it rests on — the lowest is the weakest link." },
    h("div", { className: "conf-outcome" },
      h("div", { className: `conf-big tone-${probTone(outcome.probability)}` },
        h("span", { className: "conf-big-num" }, `${pct}%`),
        h("span", { className: "conf-big-cap" }, "likely to hold")),
      h("p", { className: "conf-outcome-label" }, displayMessage(outcome.label || "the thesis holds"))),
    nodes.length
      ? h("ul", { className: "conf-nodes" },
          nodes.map((n, i) => {
            const np = Math.round(n.probability * 100);
            const isWeak = weakest && n.id === weakest.id;
            return h("li", { key: n.id || i, className: "conf-node" },
              h("div", { className: "conf-node-head" },
                h("span", { className: "conf-node-pct" }, `${np}%`),
                h("span", { className: "conf-node-label" }, displayMessage(n.label || `claim ${i + 1}`)),
                isWeak ? h(Tag, { tone: "danger" }, "weakest link") : null),
              h("div", { className: "conf-bar" }, h("div", { className: `conf-bar-fill tone-${probTone(n.probability)}`, style: { width: `${Math.max(3, np)}%` } })),
              n.watch_signal ? h("p", { className: "conf-node-signal" }, h(Tag, { tone: "neutral" }, "watch"), h("span", null, displayMessage(n.watch_signal))) : null);
          }))
      : null);
}

function scoreModeLabel(mode) {
  const m = String(mode || "").toLowerCase();
  if (m === "raw_llm_score" || m.includes("raw")) return "raw model score";
  if (m.includes("rubric") || m.includes("regime")) return "scored against the rubric";
  return mode ? displayMessage(mode) : "";
}
function scorePhrase(score) {
  if (score === null || score === undefined) return "";
  if (score >= 80) return "Held up well";
  if (score >= 60) return "Mostly held up";
  if (score >= 40) return "Shaky";
  return "Didn't hold up";
}
function scoreBand(score) {
  if (score === null || score === undefined) return "mid";
  return score >= 80 ? "high" : score >= 60 ? "mid" : "low";
}


// A finding card: eyebrow + body. tone tints it (warn = the weakest point). `id` lets the metric strip
// jump to it.
function Card({ label, tone, children, className, id }) {
  return h("section", { id, className: `finding-card ${tone || ""} ${className || ""}` },
    label ? h("span", { className: "finding-card-label" }, label) : null,
    children);
}

// Smooth-scroll the metric strip to the section it counts.
function jumpTo(id) {
  if (typeof document === "undefined") return;
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}
function bulletList(items) {
  return h("ul", { className: "finding-bullets" },
    items.map((it, i) => h("li", { key: i }, displayMessage(it))));
}

// The thesis evolving across iterations — a sparkline of the run's scores (0–100).
function Sparkline({ series, band }) {
  if (!Array.isArray(series) || series.length < 2) return null;
  const w = 132, hgt = 40, pad = 4;
  const min = Math.min(...series), max = Math.max(...series);
  const span = max - min || 1;
  const pts = series.map((s, i) => {
    const x = pad + (i / (series.length - 1)) * (w - 2 * pad);
    const y = hgt - pad - ((s - min) / span) * (hgt - 2 * pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const last = pts[pts.length - 1].split(",");
  return h("svg", { className: `findings-spark band-${band}`, width: w, height: hgt, viewBox: `0 0 ${w} ${hgt}`, "aria-hidden": "true" },
    h("polyline", { points: pts.join(" "), fill: "none", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }),
    h("circle", { cx: last[0], cy: last[1], r: 3 }));
}

// "What the run found" — the run's epistemic payload as a findings report (Hex/Linear-grounded):
// a result hero, the weakest point highlighted, then findings as cards with real hierarchy.
export function RunFindings({ view, onOpenDetail }) {
  const v = view || {};
  if (!v.hasRun) {
    return h("section", { className: "findings", "aria-label": "What the run found" },
      h("div", { className: "findings-blank" },
        h("p", null, "No run yet. Pressure-test the thesis and this shows where it held up, where it's weakest, and what the evaluator argued."),
        h("button", { type: "button", className: "chip primary", onClick: () => onOpenDetail && onOpenDetail("run", "Start run") }, "Pressure-test the thesis →")));
  }
  const trust = v.trust || {};
  const dag = v.dag || {};
  const logic = v.logicGaps || [];
  const friction = v.frictionPoints || [];
  const band = scoreBand(v.score);

  return h(
    "section",
    { className: "findings", "aria-label": "What the run found" },

    // Result hero (Mercury big-number + Hex chart): the champion score, how the thesis evolved
    // (sparkline over the run's iterations), and how it was scored.
    h("div", { className: `findings-hero band-${band}` },
      h("div", { className: "findings-hero-score" },
        h("span", { className: "findings-hero-num" }, String(v.score)),
        h("span", { className: "findings-hero-out" }, "/100")),
      h("div", { className: "findings-hero-copy" },
        h("strong", null, scorePhrase(v.score)),
        h("span", null,
          trust.mode ? scoreModeLabel(trust.mode) : "scored",
          dag.outcome && typeof dag.outcome.probability === "number"
            ? ` · likely outcome ${Math.round(dag.outcome.probability * 100)}%` : "")),
      v.series && v.series.length > 1
        ? h("div", { className: "findings-hero-evolve" },
            h(Sparkline, { series: v.series, band }),
            h("span", null,
              v.firstScore !== null && v.firstScore !== v.score ? `sharpened ${v.firstScore} → ${v.score} ` : "",
              `over ${v.iterationCount} iteration${v.iterationCount === 1 ? "" : "s"}`,
              v.runCount > 1 ? ` · ${v.runCount} runs` : ""))
        : null,
      // The score is rubric-relative — say so when the rubric moved, so a drop isn't misread.
      v.rubricChanged
        ? h("p", { className: "findings-hero-rubric" }, "Scored against a tougher rubric than your saved best — a lower number here is a higher bar, not a weaker thesis.")
        : null),

    // At-a-glance metric strip (stripe/monarch "today metric blocks") — the counts that live only as prose
    // headers below, pulled up as scannable, band-coloured stats.
    (() => {
      const nodes = Array.isArray(dag.nodes) ? dag.nodes.filter((n) => n && typeof n.probability === "number") : [];
      const weakest = nodes.length ? Math.round(Math.min(...nodes.map((n) => n.probability)) * 100) : null;
      const blocks = [
        weakest !== null ? { label: "Weakest link", value: `${weakest}%`, tone: weakest < 60 ? "danger" : weakest < 85 ? "warn" : "ok", anchor: "find-confidence" } : null,
        nodes.length ? { label: "Sub-claims", value: String(nodes.length), anchor: "find-confidence" } : null,
        { label: "Logic gaps", value: String(logic.length), tone: logic.length ? "warn" : "ok", anchor: logic.length ? "find-logic" : null },
        { label: "Evaluator friction", value: String(friction.length), tone: friction.length ? "warn" : "", anchor: friction.length ? "find-friction" : null },
      ].filter(Boolean);
      return blocks.length
        ? h("div", { className: "findings-metrics" },
            blocks.map((b, i) => {
              const cls = `findings-metric ${b.tone ? "tone-" + b.tone : ""} ${b.anchor ? "linked" : ""}`;
              const label = h("span", { className: "findings-metric-label" }, b.label);
              const value = h("span", { className: "findings-metric-value" }, b.value);
              return b.anchor
                ? h("button", { type: "button", className: cls, key: i, title: "Jump to this section", onClick: () => jumpTo(b.anchor) }, label, value)
                : h("div", { className: cls, key: i }, label, value);
            }))
        : null;
    })(),

    // The single most important finding, highlighted.
    v.weakestPoint
      ? h(Card, { label: "⚠ Weakest point", tone: "warn", className: "finding-weakest" },
          h("p", null, displayMessage(v.weakestPoint)))
      : null,

    // The loop's probabilistic forecast — confidence the thesis holds, by sub-claim. Anchored so the
    // "Weakest link" / "Sub-claims" metrics jump here.
    (() => { const cb = ConfidenceBlock(dag); return cb ? h("div", { id: "find-confidence" }, cb) : null; })(),

    // Logic gaps + friction side by side (Hex two-up).
    (logic.length || friction.length)
      ? h("div", { className: "findings-grid" },
          logic.length ? h(Card, { id: "find-logic", label: `Logic gaps · ${logic.length}` }, bulletList(logic)) : null,
          friction.length ? h(Card, { id: "find-friction", label: `Friction with the evaluator · ${friction.length}` }, bulletList(friction)) : null)
      : null,

    v.debateSummary
      ? h(Card, { label: "What the evaluator and the thesis argued" },
          h("p", { className: "finding-prose" }, displayMessage(v.debateSummary)))
      : null,

    trust.alignmentText
      ? h(Card, { label: "Evaluator's read on alignment", className: "finding-trust" },
          trust.alignmentRead ? h("span", { className: "finding-pill" }, trust.alignmentRead) : null,
          h("p", null, displayMessage(trust.alignmentText)),
          h("small", null, "The evaluator's own assessment — not a computed measure of gaming."))
      : null,

    // The score is capped by MISSING EVIDENCE, not a weak thesis — a different next action.
    v.evidenceCeiling
      ? h(Card, { label: "The score is capped by missing evidence", tone: "warn" },
          h("p", null, "The thesis isn't being marked down for being wrong — the run ran out of evidence to test it further. Add or fetch the missing evidence and run again."))
      : null,

    // Is the score trustworthy? — why it capped (gaming / a too-narrow gate) + what the checks missed.
    v.metaAudit
      ? h(Card, { label: "Is the score trustworthy?", tone: "warn", className: "finding-meta" },
          v.metaAudit.cap_pattern ? h("p", null, displayMessage(v.metaAudit.cap_pattern)) : null,
          v.metaAudit.narrow_gate ? h("p", { className: "finding-meta-note" }, "A narrow check did most of the scoring: ", displayMessage(v.metaAudit.narrow_gate), ".") : null,
          (v.metaAudit.gates_missed && v.metaAudit.gates_missed.length)
            ? h(React.Fragment, null,
                h("span", { className: "finding-card-sublabel" }, "Checks that fired but didn't catch it"),
                bulletList(v.metaAudit.gates_missed))
            : null,
          h("small", null, "A cross-family model audited this run for gaming — not the same model that scored it."))
      : null,

    // Structural integrity — deterministic (no-LLM) checks on whether it's a real law or a curve-fit.
    v.coherence
      ? h("section", { className: "finding-card finding-coherence" },
          h("span", { className: "finding-card-label" }, "Structural integrity"),
          h("ul", { className: "finding-coherence-list" },
            v.coherence.checks.map((c, i) =>
              h("li", { key: i, className: `finding-coherence-row ${c.pass ? "ok" : "warn"}` },
                h("span", { className: "finding-coherence-mark" }, c.pass ? "✓" : "—"),
                h("span", null, displayText(c.label))))),
          h("small", null, "Code-computed checks (no model judgement): does it explain more than it costs, hold at the extremes, use the same rule across cases."))
      : null,

    // Why it concluded what it did — the reasoning steps the evaluator weighed, most-likely first.
    // A ranked list (full text, no clipping), not a cramped node-graph. Leads with the conclusion.
    dag.outcome
      ? h("section", { className: "finding-card finding-reason" },
          h("span", { className: "finding-card-label" }, "Why it concluded this"),
          h("p", { className: "finding-reason-outcome" },
            displayMessage(dag.outcome.label || "Most likely conclusion"),
            typeof dag.outcome.probability === "number"
              ? h("span", { className: "finding-reason-pct" }, `${Math.round(dag.outcome.probability * 100)}% likely`) : null),
          Array.isArray(dag.nodes) && dag.nodes.length
            ? h("ul", { className: "finding-reason-list" },
                dag.nodes
                  .slice()
                  .sort((a, b) => (Number(b.probability) || 0) - (Number(a.probability) || 0))
                  .map((n, i) => {
                    const p = typeof n.probability === "number" ? n.probability : null;
                    return h("li", { key: i, className: "finding-reason-step" },
                      h("p", null, displayMessage(n.label || "")),
                      p !== null
                        ? h("div", { className: "finding-reason-meter" },
                            h("span", { className: "finding-reason-bar", style: { width: `${Math.round(p * 100)}%` } }),
                            h("em", null, `${Math.round(p * 100)}%`))
                        : null);
                  }))
            : null)
      : null,

    // Did the answer drift off the mandate? (charter drift — plain line, links to Charter.)
    v.charterDrift
      ? h(Card, { label: "Drifted from your charter", tone: "warn", className: "finding-drift" },
          h("p", null, displayMessage(v.charterDrift.gap || "The thesis optimized a narrow proxy instead of the charter's intent.")),
          v.charterDrift.added_criterion
            ? h("small", null, "The run added a check for it: ", displayMessage(v.charterDrift.added_criterion))
            : null,
          onOpenDetail ? h("button", { type: "button", className: "chip ghost", onClick: () => onOpenDetail("overview", "Charter") }, "Open the charter →") : null)
      : null,

    // What would prove this wrong — lead each with the plain worry; tuck the technical experiment.
    v.inverter
      ? h("section", { className: "finding-card finding-falsify" },
          h("span", { className: "finding-card-label" }, "What would prove this wrong"),
          h("p", { className: "finding-falsify-intro" },
            "Concrete ways someone could try to break the thesis.",
            typeof v.inverter.survival_confidence === "number"
              ? h("span", null, ` The adversary puts its odds of surviving them at `, h("strong", null, `${Math.round(v.inverter.survival_confidence * 100)}%`), `.`)
              : null),
          h("ul", { className: "finding-falsify-list" },
            v.inverter.tests.slice(0, 5).map((t, i) => {
              // Lead with the first sentence (the headline worry); the rest is the elaboration — so it
              // reads as a titled card, not a bold wall of text.
              const doubt = displayMessage(t.doubt || t.test || "A way it could be wrong");
              const m = doubt.match(/^(.*?[.!?])\s+([\s\S]+)$/);
              const lead = m ? m[1] : doubt;
              const body = m ? m[2] : "";
              const hasTest = t.test || (Array.isArray(t.steps) && t.steps.length) || t.passes_if;
              return h("li", { key: i, className: "ff-card" },
                h("div", { className: "ff-card-head" },
                  h("span", { className: "ff-num" }, `R${i + 1}`),
                  h("strong", { className: "ff-lead" }, lead)),
                body ? h("p", { className: "ff-body" }, body) : null,
                t.fails_if
                  ? h("p", { className: "ff-row kill" }, h("span", { className: "ff-tag kill" }, "Killed if"), displayMessage(t.fails_if))
                  : null,
                hasTest
                  ? h("details", { className: "ff-test" },
                      h("summary", null, h("span", { className: "ff-tag test" }, "The test"), "how someone would check it"),
                      t.test ? h("p", { className: "ff-test-body" }, displayMessage(t.test)) : null,
                      Array.isArray(t.steps) && t.steps.length
                        ? h("ol", { className: "ff-steps" }, t.steps.map((s, j) => h("li", { key: j }, displayMessage(s))))
                        : null,
                      t.passes_if
                        ? h("p", { className: "ff-row pass" }, h("span", { className: "ff-tag pass" }, "Holds if"), displayMessage(t.passes_if))
                        : null)
                  : null);
            })))
      : null
  );
}
