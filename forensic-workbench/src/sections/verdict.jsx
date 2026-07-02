import React from "react";
import { displayMessage, Block, Tag } from "../design-system.js";

const h = React.createElement;

// Verdict — "can I rely on this, and exactly where is it thin?" The judgment + the WHY come from the
// CLI's claim-support reliability (one source of truth, shared with Thesis); the per-claim list shows
// the claims to verify with their sources. Then the deliverable. Pure view — simple, no Frankenstein.
export function Verdict({ view, onOpenReport, onMakeCard, onPreview, onForecast, forecast, onExportObsidian, obsidianExport, onFalsify, falsify }) {
  const v = view || {};
  const tone = v.tone || "almost";
  const fc = forecast || {};
  const fcResult = fc.result || {};
  const obs = obsidianExport || {};
  const obsDone = obs.result && obs.result.ok ? obs.result : null;
  const fx = falsify || {};
  const fxRes = (fx.result && fx.result.ok) ? fx.result : null;
  const fxTests = fxRes && Array.isArray(fxRes.tests) ? fxRes.tests : [];
  const toVerify = Array.isArray(v.toVerify) ? v.toVerify : [];
  const shown = toVerify.length;
  const more = Math.max(0, (v.attentionTotal || 0) - shown);

  return h(
    "section",
    { className: "verdict", "aria-label": "Verdict" },

    // Hero — the reliability verdict + the real backing mix (the affordance, not "Report readiness is current").
    h("div", { className: `verdict-hero tone-${tone}` },
      h("span", { className: "verdict-dot" }),
      h("div", { className: "verdict-hero-copy" },
        h("div", { className: "verdict-hero-line" },
          h("strong", null, v.phrase || "Not checked yet")),
        v.why ? h("span", null, displayMessage(v.why)) : null),
      // The trust % answers the whole "can I rely on this?" — make it the biggest, band-coloured thing.
      typeof v.confidence === "number"
        ? h("div", { className: `verdict-conf-hero tone-${v.confidence >= 0.85 ? "ok" : v.confidence >= 0.6 ? "warn" : "danger"}`,
            title: "The loop's probability the thesis holds (probability_dag) — see the Confidence breakdown under Results." },
            h("span", { className: "verdict-conf-num" }, `${Math.round(v.confidence * 100)}%`),
            h("span", { className: "verdict-conf-cap" }, "likely to hold"))
        : null),

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
          }, fx.running ? "Inverting…" : fxRes ? "Run it again" : "See how it could break →"),
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

    // The deliverable — the actual rendered documents (opened in the file viewer).
    h(Block, { title: "The deliverable" },
      h("div", { className: "verdict-actions" },
        h("button", {
          type: "button", className: "chip primary",
          onClick: () => (v.reportFile && onPreview) ? onPreview({ type: "file", value: v.reportFile }) : (onOpenReport && onOpenReport())
        }, "View the full report"),
        h("button", {
          type: "button", className: "chip",
          onClick: () => (v.cardFile && onPreview) ? onPreview({ type: "file", value: v.cardFile }) : (onMakeCard && onMakeCard())
        }, "Open the claim card"),
        onMakeCard
          ? h("button", { type: "button", className: "chip ghost", onClick: () => onMakeCard() }, "Regenerate claim card")
          : null,
        v.contractFile && onPreview
          ? h("button", { type: "button", className: "chip ghost", title: "The record of how each claim was checked against its sources",
              onClick: () => onPreview({ type: "file", value: v.contractFile }) }, "See how claims were checked")
          : null,
        // Take the whole verified structure to a writing tool — one linked note per claim/evidence/falsifier,
        // weak spots already marked. The capstone: you've reached a verdict, now write the article from it.
        onExportObsidian
          ? h("button", { type: "button", className: "chip ghost", disabled: obs.running,
              title: "Export the verified graph as a linked Obsidian vault you write from",
              onClick: () => onExportObsidian() }, obs.running ? "Exporting…" : "Export to Obsidian →")
          : null),
      obsDone
        ? h("p", { className: "verdict-export-done" },
            `Exported ${obsDone.note_count} linked notes → `, h("code", null, obsDone.out_dir),
            " — open that folder as an Obsidian vault.")
        : (obs.error ? h("p", { className: "verdict-muted" }, displayMessage(obs.error)) : null)),

    // On-demand forecast (#78) — spin up a fresh probability for the thesis, priced via the sealed pool.
    onForecast && v.question
      ? h(Block, { title: "Fresh forecast", lead: "Ask the loop for an on-demand probability the thesis holds — priced with tail-risk via the forecast pool." },
          fc.running
            ? h("p", { className: "verdict-muted" }, "Forecasting… the model is estimating the probability, then the pool prices it (this takes a moment).")
            : typeof fcResult.p_success === "number"
              ? h("div", { className: "fc-result" },
                  h("div", { className: "fc-result-head" },
                    h("span", { className: `fc-result-pct tone-${fcResult.p_success >= 0.85 ? "ok" : fcResult.p_success >= 0.6 ? "warn" : "danger"}` }, `${Math.round(fcResult.p_success * 100)}%`),
                    h("span", { className: "fc-result-cap" }, "likely to hold")),
                  fcResult.rationale ? h("p", { className: "fc-result-why" }, displayMessage(fcResult.rationale)) : null,
                  h("p", { className: "fc-result-meta" },
                    h(Tag, null, "tail-risk"),
                    h("span", null, `insure ${Math.round((fcResult.tail_insurance_premium || 0) * 100)}% · downside ${Math.round((fcResult.tail_loss_magnitude || 0) * 100)}%`)),
                  h("button", { type: "button", className: "chip ghost", onClick: () => onForecast(v.question) }, "Forecast again"))
              : fc.error
                ? h("div", null, h("p", { className: "verdict-muted" }, fc.error),
                    h("button", { type: "button", className: "chip", onClick: () => onForecast(v.question) }, "Try again"))
                : h("button", { type: "button", className: "chip primary", onClick: () => onForecast(v.question) }, "Forecast this thesis →"))
      : null
  );
}
