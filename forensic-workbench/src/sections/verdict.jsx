import React from "react";
import { displayMessage, Block, Tag } from "../design-system.js";
import { compiledDecisionState, DecisionPanel } from "./decisionpanel.jsx";
import { DeliverablesPanel } from "./deliverablespanel.jsx";

const h = React.createElement;

// Verdict — "can I rely on this, and exactly where is it thin?" The judgment + the WHY come from the
// CLI's claim-support reliability (one source of truth, shared with Thesis); the per-claim list shows
// the claims to verify with their sources. Then the deliverable. Pure view — simple, no Frankenstein.
//
// PRD §4.2a folds two governed-decision surfaces in here as blocks (never as sidebar items): DecisionPanel
// (the graded "how firmly" strength read — lane-labelled "From the governed map:" since it's a DIFFERENT
// engine from the crisp reliability verdict above and never overrides it) and DeliverablesPanel (merged into
// the existing "The deliverable" block — report / claim card / templated deliverables, one list).
export function Verdict({ view, onOpenReport, onMakeCard, onPreview, onOpenDetail, onForecast, onExportObsidian, obsidianExport, onFalsify, falsify, project, liveMode, decision, scenario, onDecisionRefresh, onCheckDraft }) {
  const v = view || {};
  const tone = v.tone || "almost";
  const obs = obsidianExport || {};
  const obsDone = obs.result && obs.result.ok ? obs.result : null;
  const fx = falsify || {};
  const fxRes = (fx.result && fx.result.ok) ? fx.result : null;
  const fxTests = fxRes && Array.isArray(fxRes.tests) ? fxRes.tests : [];
  const toVerify = Array.isArray(v.toVerify) ? v.toVerify : [];
  const shown = toVerify.length;
  const more = Math.max(0, (v.attentionTotal || 0) - shown);
  const compiled = compiledDecisionState(decision);
  const compiledTone = compiled && ({ SUPPORTED: "rely", BLOCKED: "almost", REFUTED: "no" }[compiled.status]);
  const heroTone = compiledTone || tone;
  const heroPhrase = (compiled && compiled.headline) || v.phrase || "Compiling the decision";
  const heroReason = (compiled && compiled.reason) || v.why;

  return h(
    "section",
    { className: "verdict", "aria-label": "Verdict" },

    // Hero — the reliability verdict + the real backing mix (the affordance, not "Report readiness is current").
    h("div", { className: `verdict-hero tone-${heroTone}` },
      h("span", { className: "verdict-dot" }),
      h("div", { className: "verdict-hero-copy" },
        h("div", { className: "verdict-hero-line" },
          h("strong", null, heroPhrase)),
        heroReason ? h("span", null, displayMessage(heroReason)) : null),
      // Run observations never compete with the compiled decision posture.
      typeof v.confidence === "number"
        ? h("div", { className: "verdict-run-signal",
            title: "Model-authored probability from the latest run; it has no demonstrated calibration." },
            h("span", { className: "verdict-run-signal-label" }, "Run observation"),
            h("strong", null, `${Math.round(v.confidence * 100)}%`),
            h("span", null, "uncalibrated model estimate"))
        : null),

    // The graded "how firmly" read — a different, lane-labelled engine from the crisp verdict above (PRD §4.2a).
    project ? h(DecisionPanel, { key: "decision", project, liveMode, decision, onRefresh: onDecisionRefresh,
      onOpenEvidence: () => onOpenDetail && onOpenDetail("sources", "Prepare files") }) : null,

    // How could this break? — the adversarial inverter, pointed at your thesis. It loads the probability DAG
    // and targets the weakest node itself, then proposes the concrete tests that would refute it. The honest
    // completion of the verdict: not just "how confident", but "what would change my mind" — before a paid run.
    onFalsify
      ? h(Block, { title: "How could this break?", className: "verdict-falsify",
          lead: "Point the adversarial inverter at your thesis — it finds the weakest link and proposes the concrete tests that would refute it. One model call, no full run." },
          h("button", {
            type: "button", className: `chip primary ${fx.running ? "is-busy" : ""}`, disabled: fx.running,
            title: "Runs the inverter against your thesis — it targets the weakest node and returns falsification tests",
            onClick: () => onFalsify(),
          }, fx.running ? "Inverting…" : fxRes ? "Check again" : "See how it could break →"),
          fx.error ? h("p", { className: "verdict-falsify-error" }, displayMessage(fx.error)) : null,
          fxTests.length
            ? h("ul", { className: "verdict-falsify-tests" },
                fxTests.slice(0, 4).map((t, i) =>
                  h("li", { key: i, className: "verdict-falsify-test" },
                    h("p", { className: "verdict-falsify-what" }, displayMessage(t.popper_test || t.munger_inversion || "(test)")),
                    t.fail_criterion ? h("p", { className: "verdict-falsify-fail" }, "Fails if — ", displayMessage(t.fail_criterion)) : null)))
            : (fxRes ? h("p", { className: "verdict-falsify-empty" }, "The inverter didn't surface a concrete test this time — try again.") : null))
      : null,

    // Where to verify — the claims that aren't directly sourced, each with its plain status + sources.
    shown
      ? h(Block, { title: "Where to verify", lead: "Claims that aren't directly sourced — check each before you rely on it." },
          h("ul", { className: "verdict-claims" },
            toVerify.slice(0, 12).map((c, i) =>
              h("li", { key: i, className: "verdict-claim" },
                h("div", { className: "verdict-claim-head" },
                  h("span", { className: "verdict-claim-text" }, displayMessage(c.claim)),
                  // The whole list IS "not directly sourced" (see the Block lead), so the identical
                  // "synthesized" tag on every row is noise — flag only the exceptions (unsupported).
                  c.statusTone === "no" ? h(Tag, { tone: "danger" }, c.statusLabel) : null),
                c.sources.length
                  ? h("div", { className: "verdict-claim-sources" },
                      c.sources.map((s, si) =>
                        h("button", {
                          key: si, type: "button", className: "verdict-source",
                          onClick: () => onPreview && onPreview({ type: "file", value: s.path }),
                        }, s.name)))
                  : null))),
          more ? h("p", { className: "verdict-more" }, `+ ${more} more claim${more === 1 ? "" : "s"} to verify`) : null)
      : h(Block, { title: "Where to verify" },
          h("p", { className: "verdict-muted" },
            tone === "rely" ? "Nothing to verify — every claim is directly sourced." : "No per-claim breakdown available yet — run a backing check.")),

    // Handoff is a distinct job from judging. The report is primary; cards, audit, and export are supporting tools.
    h(Block, { title: "Handoff" },
      h("div", { className: "verdict-deliverable-home" },
        h("div", { className: "verdict-deliverable-primary" },
          h("div", null,
            h("span", { className: "eyebrow" }, "Current decision"),
            h("strong", null, "Decision report"),
            h("p", null, "The full checked account of the decision, its evidence, and what could change it.")),
          h("button", {
            type: "button", className: "chip primary",
            onClick: () => (v.reportFile && onPreview) ? onPreview({ type: "file", value: v.reportFile }) : (onOpenReport && onOpenReport())
          }, "Open decision report")),
        h("div", { className: "verdict-deliverable-tools", "aria-label": "Supporting handoff tools" },
          h("button", {
            type: "button", className: "text-link",
            onClick: () => (v.cardFile && onPreview) ? onPreview({ type: "file", value: v.cardFile }) : (onMakeCard && onMakeCard())
          }, "Open claim card"),
          onMakeCard
            ? h("button", { type: "button", className: "text-link", onClick: () => onMakeCard() }, "Refresh claim card")
            : null,
          v.contractFile && onPreview
            ? h("button", { type: "button", className: "text-link", title: "The record of how each claim was checked against its sources",
                onClick: () => onPreview({ type: "file", value: v.contractFile }) }, "Review source checks")
            : null,
          onExportObsidian
            ? h("button", { type: "button", className: "text-link", disabled: obs.running,
                title: "Export the verified graph as a linked Obsidian vault you write from",
                onClick: () => onExportObsidian() }, obs.running ? "Exporting…" : "Export to Obsidian")
            : null)),
      obsDone
        ? h("p", { className: "verdict-export-done" },
            `Exported ${obsDone.note_count} linked notes to `, h("code", null, obsDone.out_dir), ".")
        : (obs.error ? h("p", { className: "verdict-muted" }, displayMessage(obs.error)) : null),
      project ? h(DeliverablesPanel, { key: "deliverables", project, liveMode, scenario, onPreview,
        onManageDocuments: () => onOpenDetail && onOpenDetail("projects", "Plugins"), onCheckDraft }) : null),

    // On-demand forecasting has ONE home — Open points' "Ask the loop" (Priority 1: this used to duplicate
    // that exact box here as "Fresh forecast"; now it just points there instead of stacking a second one).
    onForecast && v.question && onOpenDetail
      ? h("p", { className: "verdict-muted" }, "Want an on-demand probability for a specific question? Ask the loop on the ",
          h("button", { type: "button", className: "text-link", onClick: () => onOpenDetail("review", "Things to review") }, "Open points"),
          " screen.")
      : null
  );
}
