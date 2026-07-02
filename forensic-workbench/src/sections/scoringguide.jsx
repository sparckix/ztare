import React from "react";
import { displayMessage, displayText, Block } from "../design-system.js";

const h = React.createElement;

// Pre-run rubric review — the six questions that decide whether the SCORING INSTRUMENT itself can be
// trusted, in plain language. The kernel returns the raw check_name; this is the human label.
const RUBRIC_CHECK_LABELS = {
  gaming_surface_coverage: "Covers how the thesis could be gamed",
  evidence_anchor_requirement: "Forces claims to be anchored in evidence",
  score_ceiling_reachability_without_evidence: "A high score is unreachable without evidence",
  criterion_independence: "Scoring criteria don't double-count",
  persona_blind_spot_coverage: "The adversarial grader covers the blind spots",
  charter_spirit_coverage: "The rubric tests the charter's intent",
};

// Render the rubric-review result as a calm "rubric health" card — pass/fail per check with the issue +
// proposed fix, scenario validity, and a note that any patch is advisory (commit stays CLI). Tasteful,
// reuses the same status-dot vocabulary as the rest of the workbench.
function renderRubricReview(state) {
  if (!state) return null;
  if (state.running) {
    return h("div", { className: "rubric-review is-running" },
      h("span", { className: "rubric-review-spinner", "aria-hidden": "true" }),
      h("span", null, "Checking whether this rubric can be gamed…"));
  }
  if (state.error) {
    return h("div", { className: "rubric-review is-error" }, "Rubric review failed: ", String(state.error));
  }
  const r = (state.result && state.result.review) || {};
  const checks = Array.isArray(r.checks) ? r.checks : [];
  if (!checks.length) return null;
  const passed = checks.filter((c) => c.status === "pass").length;
  const scenario = r.scenario_validity || {};
  const scenarioBad = scenario.status && scenario.status !== "pass";
  const clean = passed === checks.length && !scenarioBad;
  return h("div", { className: "rubric-review" },
    h("div", { className: "rubric-review-head" },
      h("strong", null, "Rubric health"),
      h("span", { className: `rubric-review-score ${clean ? "ok" : "warn"}` },
        `${passed}/${checks.length} checks pass${scenarioBad ? " · scenario stale" : ""}`)),
    r.overall_summary ? h("p", { className: "rubric-review-summary" }, displayMessage(r.overall_summary)) : null,
    h("ul", { className: "rubric-review-checks" },
      checks.map((c, i) =>
        h("li", { key: i, className: `rubric-review-check ${c.status}` },
          h("div", { className: "rubric-review-check-head" },
            h("span", { className: `rubric-review-dot ${c.status}`, "aria-hidden": "true" }),
            h("span", null, RUBRIC_CHECK_LABELS[c.check_name] || displayText(c.check_name))),
          c.status !== "pass" && c.issue ? h("p", { className: "rubric-review-issue" }, displayMessage(c.issue)) : null,
          c.status !== "pass" && c.proposed_fix ? h("p", { className: "rubric-review-fix" }, "Fix — ", displayMessage(c.proposed_fix)) : null))),
    scenarioBad
      ? h("p", { className: "rubric-review-scenario" }, "Scenario validity: ",
          displayMessage(scenario.issue || "the charter's scenario may no longer be live"),
          scenario.suggested_revision ? " — " + displayMessage(scenario.suggested_revision) : "")
      : null,
    (state.result && state.result.patch_path)
      ? h("p", { className: "rubric-review-patch" }, "A candidate patch was written for your review — apply it via the CLI. The workbench never edits your rubric for you.")
      : null);
}

// Scoring guide — how the thesis is scored, made human (was raw JSON). Reads the rubric spec:
// weighted dimensions + mode + gate toggles (each with a reason) + the evaluator persona. Pure view.
export function ScoringGuide({ view, onEditRaw, onPropose, proposing, onToggleGate, saving, onReviewRubric, rubricReview }) {
  const v = view || {};
  const dims = Array.isArray(v.dimensions) ? v.dimensions : [];
  const gates = Array.isArray(v.gates) ? v.gates : [];
  const committee = Array.isArray(v.committee) ? v.committee : [];

  if (!v.exists) {
    return h("section", { className: "rubric", "aria-label": "Scoring guide" },
      h("p", { className: "rubric-empty" },
        onEditRaw
          ? "No scoring guide yet — write the weighted dimensions your thesis should be judged on."
          : "No scoring guide yet for this thesis."),
      onEditRaw ? h("button", { type: "button", className: "chip primary", onClick: () => onEditRaw() }, "Write the scoring guide") : null);
  }

  const wTotal = dims.reduce((s, d) => s + (Number(d.weight) || 0), 0);

  return h(
    "section",
    { className: "rubric", "aria-label": "Scoring guide" },

    h("div", { className: "rubric-head" },
      v.mode ? h("span", { className: "rubric-mode-badge" }, `${displayText(v.mode)} mode`) : null,
      h("span", { className: "rubric-mode-reason" }, displayMessage(v.modeGloss || v.modeReason || ""))),

    // Scoring dimensions — the core "how it's graded", with weight bars.
    dims.length
      ? h(Block, { title: "How it's scored",
          actions: h("span", { className: `rubric-weight-total ${wTotal === 100 ? "ok" : "warn"}` }, `weights total ${wTotal}${wTotal === 100 ? "" : " — should be 100"}`) },
          h("ul", { className: "rubric-dims" },
            dims.map((d, i) =>
              h("li", { key: i, className: "rubric-dim" },
                h("div", { className: "rubric-dim-head" },
                  h("strong", null, displayText(d.name || `Dimension ${i + 1}`)),
                  h("span", { className: "rubric-dim-weight" }, `${d.weight || 0}%`)),
                h("div", { className: "rubric-dim-bar" }, h("div", { className: "rubric-dim-fill", style: { width: `${Math.min(100, Number(d.weight) || 0)}%` } })),
                d.description ? h("p", null, displayMessage(d.description)) : null))))
      : null,

    // Gates & checks — the on/off rules. Each says what it does (the spec) and why it's set this
    // way here, and flips in place (no JSON editing) when live.
    gates.length
      ? h(Block, { title: "Gates & checks",
          actions: onToggleGate ? h("span", { className: "rubric-committee-note" }, "click a switch to turn a check on or off") : null },
          h("ul", { className: "rubric-gates" },
            gates.map((g, i) =>
              h("li", { key: i, className: "rubric-gate" },
                onToggleGate
                  ? h("button", {
                      type: "button", className: `rubric-gate-switch ${g.on ? "on" : "off"}`,
                      disabled: saving, "aria-pressed": g.on, title: g.on ? "Turn this check off" : "Turn this check on",
                      onClick: () => onToggleGate(g.key, !g.value)
                    }, h("span", { className: "rubric-gate-knob" }))
                  : h("span", { className: `rubric-gate-state ${g.on ? "on" : "off"}` }, g.on ? "on" : "off"),
                h("div", { className: "rubric-gate-copy" },
                  h("strong", null, displayText(g.label)),
                  g.gloss ? h("p", null, displayMessage(g.gloss)) : null,
                  g.reason ? h("small", null, "For this thesis: ", displayMessage(g.reason)) : null)))))
      : null,

    // The adversarial panel — generated from THIS thesis when committee judging is on
    // (generate_committee.py). Who actually attacks the claim, and where each one aims.
    committee.length
      ? h(Block, { title: "Who attacks this thesis",
          actions: h("span", { className: "rubric-committee-note" }, `${committee.length}-panel committee, written for your thesis`) },
          h("ul", { className: "rubric-committee" },
            committee.map((m, i) =>
              h("li", { key: i, className: "rubric-committee-member" },
                h("strong", null, displayText(m.role || `Attacker ${i + 1}`)),
                m.focus_area ? h("span", { className: "rubric-committee-focus" }, displayMessage(m.focus_area)) : null,
                m.persona ? h("details", null, h("summary", null, "How they attack"), h("p", null, displayMessage(m.persona))) : null))))
      : null,

    v.persona
      ? h("details", { className: "rubric-persona" },
          h("summary", null, "The evaluator's persona"),
          h("p", null, displayMessage(v.persona)))
      : null,

    h("div", { className: "rubric-actions" },
      onReviewRubric
        ? h("button", {
            type: "button",
            className: `chip primary ${rubricReview && rubricReview.running ? "is-busy" : ""}`,
            disabled: !!(rubricReview && rubricReview.running),
            title: "Asks a model whether this rubric can be gamed — before you pay for a run",
            onClick: () => onReviewRubric(),
          }, rubricReview && rubricReview.running ? "Reviewing…" : "Review this rubric →")
        : null,
      onPropose ? h("button", { type: "button", className: "chip", disabled: proposing, onClick: () => onPropose() },
        proposing ? "Drafting…" : "Re-propose from thesis") : null,
      onEditRaw ? h("button", { type: "button", className: "chip ghost", onClick: () => onEditRaw() }, "Edit the raw guide") : null),

    renderRubricReview(rubricReview)
  );
}
