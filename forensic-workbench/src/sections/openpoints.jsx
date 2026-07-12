import React from "react";
import { displayMessage, Block, Tag } from "../design-system.js";
import { WagerPanel } from "./wagerpanel.jsx";
import { ChallengeQueueBlock } from "./decisionpanel.jsx";

const h = React.createElement;
const { useState } = React;

function compactCritique(value, limit = 220) {
  const text = displayMessage(value).trim();
  if (text.length <= limit) return { lead: text, full: "" };
  const window = text.slice(0, limit + 1);
  const sentenceEnds = [...window.matchAll(/[.!?](?=\s|$)/g)];
  const sentenceCut = sentenceEnds.filter((match) => match.index >= 80).at(-1);
  const wordCut = window.lastIndexOf(" ");
  const cut = sentenceCut ? sentenceCut.index + 1 : Math.max(80, wordCut);
  return { lead: `${text.slice(0, cut).trim()}…`, full: text };
}

// "Ask anything" — the WOW forecast affordance: type ANY question about the project, get a calibrated
// probability + tail-risk at a click (priced by the sealed forecast pool). Questions naturally live in
// Open points, so this is where ad-hoc ones belong. Advisory — framed as "ask the loop", not truth.
function AskForecast({ id, onForecast, forecast }) {
  const [q, setQ] = useState("");
  const fc = forecast || {};
  const r = fc.result || {};
  const ask = () => { const t = q.trim(); if (t && onForecast) onForecast(t); };
  return h(Block, { id, title: "Ask the loop", lead: "Have a question about this project? Get an on-demand probability — priced with tail-risk by the forecast pool. Advisory, not a verdict." },
    h("div", { className: "ask-row" },
      h("input", { className: "ask-input", type: "text", value: q, placeholder: "What would most change this thesis?",
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

// Open points is the one place to decide what to resolve next. The unified agenda already incorporates
// loop-proposed discriminators, declared tests, and untested assumptions through a single admission gate;
// rendering the raw discriminator queue beside it would make the operator choose between two worklists.
// The challenge queue explains what is holding the current decision back, while the agenda owns the next test.
export function OpenPoints({
  view, onOpenDetail, onAddEvidence, onForecast, forecast,
  project, liveMode, wagers, onWagersRefresh, onExpire, agenda, onAgendaRefresh,
  decision, onDecisionRefresh, onOpenModal, projectChecks, onReviewCheck,
  onPrefillWager, onNewWager, onExecuteWager,
}) {
  const v = view || {};
  const questions = Array.isArray(v.openQuestions) ? v.openQuestions : [];
  const discriminators = Array.isArray(v.discriminators) ? v.discriminators : [];
  const redTeam = Array.isArray(v.redTeam) ? v.redTeam : [];
  const logicGaps = Array.isArray(v.logicGaps) ? v.logicGaps : [];
  const checks = Array.isArray(projectChecks) ? projectChecks : [];
  if (v.loading) {
    return h("section", { className: "openpoints", "aria-label": "Open points", "aria-busy": "true" },
      h("div", { className: "section-loading" },
        h("span", { className: "runconsole-spinner", "aria-hidden": "true" }),
        h("span", null, "Loading open points…")));
  }
  const askBlock = onForecast ? h(AskForecast, { id: "op-ask", onForecast, forecast }) : null;
  const decisionTestsBlock = project
    ? h("div", { className: "openpoints-governed", id: "op-decision-tests", key: "decision-tests" },
        h(ChallengeQueueBlock, { project, liveMode, decision, onRefresh: onDecisionRefresh }),
        h(WagerPanel, { project, liveMode, agenda, onAgendaRefresh, onOpenModal, wagers, onWagersRefresh, onExpire,
          onPrefill: onPrefillWager, onNew: onNewWager, onExecute: onExecuteWager }))
    : null;
  const checksBlock = checks.length
    ? h(Block, { id: "op-checks", title: "Project checks", lead: `${checks.length} check${checks.length === 1 ? "" : "s"} still need a disposition.` },
        h("ul", { className: "op-check-list" },
          checks.map((check) =>
            h("li", { key: check.id, className: "op-check-row" },
              h("div", { className: "op-check-copy" },
                h("strong", null, displayMessage(check.label)),
                check.detail ? h("p", null, displayMessage(check.detail)) : null),
              h("button", { type: "button", className: "chip", onClick: () => onReviewCheck && onReviewCheck(check.id) }, "Review check")))))
    : null;

  if (!questions.length && !discriminators.length && !redTeam.length && !logicGaps.length && !checks.length) {
    return h("section", { className: "openpoints", "aria-label": "Open points" },
      askBlock,
      h("p", { className: "openpoints-empty" },
        v.hasRun
          ? "No open questions flagged in the latest run — the argument has no identified gaps right now."
          : "Pressure-test the thesis and the loop will surface what's still unresolved and what would settle it."),
      h("button", { type: "button", className: "chip primary", onClick: () => onOpenDetail && onOpenDetail("run", "Start run") },
        "Pressure-test the thesis →"),
      decisionTestsBlock);
  }

  // Each stacked Block gets a stable id (passed straight into Block, not a wrapper div — a wrapper would
  // make every block its own parent's `:first-child` and silently drop every hairline) so the "On this
  // page" rail (L1 rail primitive) can jump to it. Only the ones actually present show up in the rail.
  const redteamSection = redTeam.length
    ? h(Block, { id: "op-redteam", title: "Ways it could be wrong", lead: "The run's own attempts to break the thesis." },
        h("ul", { className: "op-list" },
          redTeam.map((t, i) => {
            const critique = compactCritique(t.doubt);
            return h("li", { key: i, className: "op-redteam-item" },
              h("p", { className: "op-redteam-doubt" }, critique.lead),
              critique.full
                ? h("details", { className: "op-redteam-full" },
                    h("summary", null, "Full critique"),
                    h("p", null, critique.full))
                : null,
              t.steps.length
                ? h("details", { className: "op-redteam-how" },
                    h("summary", null, h(Tag, { tone: "accent" }, "How to check"), "the test"),
                    h("ol", { className: "op-steps" }, t.steps.map((s, si) => h("li", { key: si }, displayMessage(s)))))
                : null);
          })))
    : null;

  const questionsSection = questions.length
    ? h(Block, { id: "op-questions", title: "Open questions", lead: `${questions.length} the loop flagged as unresolved.` },
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
    : null;

  const logicSection = logicGaps.length
    ? h(Block, { id: "op-logicgaps", title: "Gaps in the reasoning", lead: "What the argument hasn't ruled out yet." },
        h("ul", { className: "op-list op-logicgaps" },
          logicGaps.map((g, i) => h("li", { key: i }, displayMessage(g)))))
    : null;

  // With an active project the unified decision-test agenda above owns these suggestions. The fallback keeps
  // a detached/static render useful for an older or read-only project view that has no decision state.
  const discSection = !project && discriminators.length
    ? h(Block, { id: "op-discriminators", title: "What would settle it", lead: "The cheapest test to separate the rival explanations." },
        h("ul", { className: "op-list" },
          discriminators.map((d, i) =>
            h("li", { key: i, className: "op-discriminator" },
              h("p", null, displayMessage(d.test)),
              h("div", { className: "op-flags" },
                d.auto_testable ? h(Tag, { tone: "ok" }, "auto-testable") : h(Tag, null, "needs manual test"),
                d.can_support_promotion ? h(Tag, { tone: "accent" }, "could promote the thesis") : null)))))
    : null;

  const footerSection = questions.length || discriminators.length
    ? h("div", { key: "footer", className: "op-footer" },
        h("span", null, "These close as the thesis is pressure-tested with the evidence above."),
        h("button", { type: "button", className: "chip", onClick: () => (onAddEvidence || onOpenDetail) && (onAddEvidence || (() => onOpenDetail("sources", "Add file")))() }, "Add evidence"),
        // A link to Pressure-test, not a second "run" — the ONE real run lives there (Priority 6).
        h("button", { type: "button", className: "chip ghost", onClick: () => onOpenDetail && onOpenDetail("run", "Start run") }, "Pressure-test again →"))
    : null;

  const anchors = [
    askBlock && { id: "op-ask", label: "Ask the loop" },
    checksBlock && { id: "op-checks", label: "Project checks" },
    redteamSection && { id: "op-redteam", label: "Ways it could be wrong" },
    questionsSection && { id: "op-questions", label: "Open questions" },
    logicSection && { id: "op-logicgaps", label: "Gaps in the reasoning" },
    discSection && { id: "op-discriminators", label: "What would settle it" },
    decisionTestsBlock && { id: "op-decision-tests", label: "Decision tests" },
  ].filter(Boolean);

  return h(
    "section",
    { className: "openpoints", "aria-label": "Open points" },
    h("div", { className: "openpoints-body" },
      h("div", { className: "openpoints-main" },
        askBlock, checksBlock, redteamSection, questionsSection, logicSection, discSection, footerSection, decisionTestsBlock),
      anchors.length > 1
        ? h("nav", { className: "openpoints-rail", "aria-label": "On this page" },
            h("span", { className: "eyebrow" }, "On this page"),
            anchors.map((a) => h("a", { key: a.id, href: `#${a.id}` }, a.label)))
        : null)
  );
}
