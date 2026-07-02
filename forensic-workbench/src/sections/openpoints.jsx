import React from "react";
import { displayMessage, Block, Tag } from "../design-system.js";

const h = React.createElement;
const { useState } = React;

// "Ask anything" — the WOW forecast affordance: type ANY question about the project, get a calibrated
// probability + tail-risk at a click (priced by the sealed forecast pool). Questions naturally live in
// Open points, so this is where ad-hoc ones belong. Advisory — framed as "ask the loop", not truth.
function AskForecast({ onForecast, forecast }) {
  const [q, setQ] = useState("");
  const fc = forecast || {};
  const r = fc.result || {};
  const ask = () => { const t = q.trim(); if (t && onForecast) onForecast(t); };
  return h(Block, { title: "Ask the loop", lead: "Have a question about this project? Get an on-demand probability — priced with tail-risk by the forecast pool. Advisory, not a verdict." },
    h("div", { className: "ask-row" },
      h("input", { className: "ask-input", type: "text", value: q, placeholder: "Will the lease-conflict mechanism reproduce in production?",
        onChange: (e) => setQ(e.target.value), onKeyDown: (e) => { if (e.key === "Enter") ask(); } }),
      h("button", { type: "button", className: "chip primary", disabled: !q.trim() || fc.running, onClick: ask }, fc.running ? "Forecasting…" : "Forecast →")),
    fc.running
      ? h("p", { className: "ask-note" }, "The model is estimating the probability, then the pool prices it — this takes a moment.")
      : typeof r.p_success === "number"
        ? h("div", { className: "ask-result" },
            h("div", { className: "ask-result-head" },
              h("span", { className: `ask-result-pct tone-${r.p_success >= 0.85 ? "ok" : r.p_success >= 0.6 ? "warn" : "danger"}` }, `${Math.round(r.p_success * 100)}%`),
              h("span", { className: "ask-result-q" }, displayMessage(fc.question || ""))),
            r.rationale ? h("p", { className: "ask-result-why" }, displayMessage(r.rationale)) : null,
            h("p", { className: "ask-result-meta" }, h(Tag, null, "tail-risk"),
              h("span", null, `insure ${Math.round((r.tail_insurance_premium || 0) * 100)}% · downside ${Math.round((r.tail_loss_magnitude || 0) * 100)}%`)))
        : fc.error ? h("p", { className: "ask-note attention" }, fc.error) : null);
}

// Open points — what the loop itself flagged as unresolved. Composed entirely from the design-system
// kit (Block / Tag) so it breathes and matches every other section. Pure view.
export function OpenPoints({ view, onOpenDetail, onAddEvidence, onForecast, forecast }) {
  const v = view || {};
  const questions = Array.isArray(v.openQuestions) ? v.openQuestions : [];
  const discriminators = Array.isArray(v.discriminators) ? v.discriminators : [];
  const redTeam = Array.isArray(v.redTeam) ? v.redTeam : [];
  const logicGaps = Array.isArray(v.logicGaps) ? v.logicGaps : [];
  const askBlock = onForecast ? h(AskForecast, { onForecast, forecast }) : null;

  if (!questions.length && !discriminators.length && !redTeam.length && !logicGaps.length) {
    return h("section", { className: "openpoints", "aria-label": "Open points" },
      askBlock,
      h("p", { className: "openpoints-empty" },
        v.hasRun
          ? "No open questions flagged in the latest run — the argument has no identified gaps right now."
          : "Pressure-test the thesis and the loop will surface what's still unresolved and what would settle it."),
      h("button", { type: "button", className: "chip primary", onClick: () => onOpenDetail && onOpenDetail("run", "Start run") },
        "Pressure-test the thesis →"));
  }

  return h(
    "section",
    { className: "openpoints", "aria-label": "Open points" },

    askBlock,

    // The run's own red-team — the sharpest open points.
    redTeam.length
      ? h(Block, { title: "Ways it could be wrong", lead: "The run's own attempts to break the thesis." },
          h("ul", { className: "op-list" },
            redTeam.map((t, i) =>
              h("li", { key: i, className: "op-redteam-item" },
                h("p", { className: "op-redteam-doubt" }, displayMessage(t.doubt)),
                t.steps.length
                  ? h("details", { className: "op-redteam-how" },
                      h("summary", null, h(Tag, { tone: "accent" }, "How to check"), "the test"),
                      h("ol", { className: "op-steps" }, t.steps.map((s, si) => h("li", { key: si }, displayMessage(s)))))
                  : null))))
      : null,

    questions.length
      ? h(Block, { title: "Open questions", lead: `${questions.length} the loop flagged as unresolved.` },
          // Grouped by status with a count per bucket (the Linear pattern) so "what's blocked vs open" is
          // glanceable, instead of a flat numbered list.
          ...[["Blocked", "warn", questions.filter((q) => q.blocking)],
              ["Open", "neutral", questions.filter((q) => !q.blocking)]]
            .filter(([, , items]) => items.length)
            .map(([label, tone, items]) =>
              h("div", { className: "op-group", key: label },
                h("div", { className: "op-group-head" },
                  h("span", { className: "eyebrow" }, label),
                  h(Tag, { tone }, String(items.length))),
                h("ul", { className: "op-list" },
                  items.map((q, i) =>
                    h("li", { key: i, className: "op-question" },
                      h("div", { className: "op-q-body" },
                        h("p", { className: "op-q-text" }, displayMessage(q.question)),
                        q.why ? h("p", { className: "op-q-meta" }, h(Tag, null, "Why it matters"), h("span", null, displayMessage(q.why))) : null,
                        q.blocking ? h("p", { className: "op-q-meta" }, h(Tag, { tone: "warn" }, "Blocked by"), h("span", null, displayMessage(q.blocking))) : null)))))))
      : null,

    logicGaps.length
      ? h(Block, { title: "Gaps in the reasoning", lead: "What the argument hasn't ruled out yet." },
          h("ul", { className: "op-list op-logicgaps" },
            logicGaps.map((g, i) => h("li", { key: i }, displayMessage(g)))))
      : null,

    discriminators.length
      ? h(Block, { title: "What would settle it", lead: "The cheapest test to separate the rival explanations." },
          h("ul", { className: "op-list" },
            discriminators.map((d, i) =>
              h("li", { key: i, className: "op-discriminator" },
                h("p", null, displayMessage(d.test)),
                h("div", { className: "op-flags" },
                  d.auto_testable ? h(Tag, { tone: "ok" }, "auto-testable") : h(Tag, null, "needs manual test"),
                  d.can_support_promotion ? h(Tag, { tone: "accent" }, "could promote the thesis") : null)))))
      : null,

    questions.length || discriminators.length
      ? h("div", { className: "op-footer" },
          h("span", null, "These close as the thesis is pressure-tested with the evidence above."),
          h("button", { type: "button", className: "chip", onClick: () => (onAddEvidence || onOpenDetail) && (onAddEvidence || (() => onOpenDetail("sources", "Add file")))() }, "Add evidence"),
          h("button", { type: "button", className: "chip", onClick: () => onOpenDetail && onOpenDetail("run", "Start run") }, "Run again"))
      : null
  );
}
