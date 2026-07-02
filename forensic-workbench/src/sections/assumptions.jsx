import React from "react";
import { displayMessage, Block, Tag } from "../design-system.js";

const h = React.createElement;

// Assumptions — the constraint ledger. The home the Thesis rail's "View the ledger →" links to.
// Provisional constraints are what the program is working under; they become confirmed once they
// survive a threshold number of runs. Pure view: everything via `view`.
export function Assumptions({ view, onOpenDetail }) {
  const v = view || {};
  const axioms = Array.isArray(v.verifiedAxioms) ? v.verifiedAxioms : [];
  const provisional = Array.isArray(v.provisional) ? v.provisional : [];
  const confirmed = Array.isArray(v.confirmed) ? v.confirmed : [];
  const proposed = Array.isArray(v.proposedThisRun) ? v.proposedThisRun : [];
  const retired = Array.isArray(v.retiredAxioms) ? v.retiredAxioms : [];

  if (!provisional.length && !confirmed.length && !axioms.length) {
    return h(
      "section",
      { className: "ledger", "aria-label": "Assumptions" },
      h("p", { className: "ledger-empty" },
        v.hasRun
          ? "No constraints learned yet. The loop derives constraints as it pressure-tests the thesis."
          : "No constraints yet — pressure-test the thesis and the loop will derive the rules it commits to."),
      h("button", { type: "button", className: "ledger-cta", onClick: () => onOpenDetail && onOpenDetail("run", "Start run") },
        "Pressure-test the thesis →")
    );
  }

  const group = (title, note, rows) =>
    rows.length
      ? h(
          Block,
          { title: `${title} (${rows.length})`, lead: note },
          h("ul", { className: "ledger-list" },
            rows.map((row, i) =>
              h("li", { key: i, className: "ledger-row" },
                h("span", { className: "ledger-row-text" }, displayMessage(row.constraint || row)),
                row.status && row.status !== "provisional" && row.status !== "confirmed"
                  ? h(Tag, null, displayMessage(row.status)) : null)))
        )
      : null;

  const thresholdNote = v.threshold
    ? `confirmed after surviving ${v.threshold} run${v.threshold === 1 ? "" : "s"}`
    : "not yet confirmed";

  return h(
    "section",
    { className: "ledger", "aria-label": "Assumptions" },
    h("p", { className: "ledger-intro" },
      "What this thesis is committed to. Verified axioms are the foundation the loop treats as ",
      "established; derived constraints are rules it has learned — provisional until they survive ",
      "repeated pressure-testing."),
    group("Verified axioms", "the foundation — treated as established", axioms),
    group("Provisional constraints", thresholdNote, provisional),
    group("Confirmed constraints", "held across runs", confirmed),
    group("Retired", "assumptions the loop gave up — no longer relied on", retired),
    proposed.length
      ? h(
          "details",
          { className: "ledger-proposed" },
          h("summary", null, `Proposed in the latest run (${proposed.length})`),
          h("ul", { className: "ledger-list" },
            proposed.map((row, i) => h("li", { key: i, className: "ledger-row" },
              h("span", { className: "ledger-row-text" }, displayMessage(row.constraint || row)))))
        )
      : null
  );
}
