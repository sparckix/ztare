import React from "react";
import { displayText } from "../design-system.js";

const h = React.createElement;

// Run console — Harden's primary control: set how many iterations and launch the autoresearch loop
// again (the JTBD is "view the last run, then run it again for N more rounds"). Leads the screen.
// Shows live progress when a run is in flight. Pure view; main.js owns the launch + persistence.
export function RunConsole({ view, liveMode, running, previewing, message, onIters, onLaunch, onResolve, onOpenSettings, onOpenScoring }) {
  const v = view || {};
  const status = v.status || {};
  const busy = running || previewing;

  // A run is in flight — show progress instead of the launch control.
  if (status.active) {
    return h("section", { className: "runconsole running", "aria-label": "Run in progress" },
      h("div", { className: "runconsole-progress" },
        h("span", { className: "runconsole-spinner", "aria-hidden": "true" }),
        h("div", null,
          h("strong", null, status.budget ? `Pressure-testing the thesis — round ${status.iteration} of ${status.budget}` : `Pressure-testing the thesis — round ${status.iteration || 1}`),
          h("small", null, [
            typeof status.score === "number" ? `best so far ${status.score}` : "",
            status.mutator ? `drafting with ${displayText(status.mutator)}` : "",
          ].filter(Boolean).join(" · ") || "running…"))));
  }

  return h("section", { className: "runconsole", "aria-label": "Run the loop" },
    h("div", { className: "runconsole-main" },
      h("div", { className: "runconsole-copy" },
        h("span", { className: "eyebrow" }, "Run the loop"),
        h("p", null, "Attack the thesis again across several rounds — each round drafts a sharper version and scores it."),
        // Will another run learn anything? (information-yield from the last run.)
        v.yieldGuidance
          ? h("p", { className: `runconsole-yield ${v.yieldGuidance.tone}` }, displayText(v.yieldGuidance.text))
          : null),
      h("div", { className: "runconsole-launch" },
        h("label", { className: "runconsole-iters" },
          h("span", null, "Rounds"),
          h("input", {
            type: "number", min: 1, max: 50, step: 1, value: v.iters,
            disabled: !liveMode || busy,
            onChange: (e) => onIters && onIters(e.target.value),
          })),
        // One button. It previews the cost first (free, no model calls) and opens the confirm dialog —
        // or, if something's missing, says so. No separate "readiness" step.
        h("button", {
          type: "button", className: `chip primary ${busy ? "is-busy" : ""}`,
          disabled: !liveMode || busy,
          title: "Shows the cost first, then asks before it spends anything",
          onClick: () => onLaunch && onLaunch(),
        }, busy ? (previewing ? "Checking the cost…" : "Running…") : `Run ${v.iters || ""} round${String(v.iters) === "1" ? "" : "s"} →`))),

    // Anything the preview reported (what's missing, or a queued note) — plain, only when present.
    // If it's a not-ready/blocking message, offer a path to resolve it (no dead end).
    message
      ? h("div", { className: "runconsole-note" },
          h("span", null, message),
          (/not ready|readiness|evidence gap|blocked|fetch or justify/i.test(message) && onResolve)
            ? h("button", { type: "button", className: "text-link", onClick: () => onResolve() }, "Fix what's blocking →")
            : null)
      : null,

    // How this run is configured — compact, with the two prep screens one click away.
    h("div", { className: "runconsole-modes" },
      (v.modes || []).map((m, i) => h("span", { key: i, className: "runconsole-mode" }, m)),
      onOpenSettings || onOpenScoring ? h("span", { className: "runconsole-mode-sep" }, "·") : null,
      onOpenSettings ? h("button", { type: "button", className: "text-link", onClick: () => onOpenSettings() }, "Run settings") : null,
      onOpenScoring ? h("button", { type: "button", className: "text-link", onClick: () => onOpenScoring() }, "Scoring guide") : null));
}
