import React from "react";
import { displayText } from "../design-system.js";

const h = React.createElement;

function ageText(seconds) {
  const age = Number(seconds);
  if (!Number.isFinite(age) || age < 0) return "just now";
  if (age < 60) return `${Math.max(1, Math.round(age))}s ago`;
  const minutes = Math.floor(age / 60);
  return `${minutes}m ago`;
}

function runPhase(status) {
  if (status.jobStatus === "queued") return "Preparing the run and waiting for the first receipt";
  if (status.heartbeatStale) return "The current model call is taking longer than the last heartbeat";
  if (status.progressSource === "job" && !status.iteration) return "Starting the run — the first iteration has not landed yet";
  if (status.iteration) return `Evaluating iteration ${status.iteration}`;
  return "Starting the run";
}

// Run console — Pressure-test's primary control: set iterations and launch the autoresearch loop.
// again (the JTBD is "view the last run, then run it again for N more rounds"). Leads the screen.
// Shows live progress when a run is in flight. Pure view; main.js owns the launch + persistence.
export function RunConsole({ view, liveMode, running, previewing, message, scenarios, selectedScenario, onScenario, onIters, onLaunch, onResolve, onOpenSettings, onOpenScoring }) {
  const v = view || {};
  const status = v.status || {};
  const busy = running || previewing;

  // A run is in flight — show progress instead of the launch control.
  if (status.active) {
    const budget = Number(status.budget);
    const iteration = Number(status.iteration) || 0;
    const determinate = Number.isFinite(budget) && budget > 0 && iteration > 0;
    const percent = determinate ? Math.min(100, Math.round((iteration / budget) * 100)) : 0;
    const stateLabel = status.jobStatus === "queued" ? "Queued" : "Running";
    const details = [
      determinate ? `round ${iteration} of ${budget}` : iteration ? `round ${iteration}` : "first round pending",
      typeof status.score === "number" ? `best so far ${status.score}` : "",
      status.mutator ? `mutator ${displayText(status.mutator)}` : "",
      status.judge ? `judge ${displayText(status.judge)}` : "",
    ].filter(Boolean).join(" · ");
    return h("section", { className: "runconsole running", "aria-label": "Run in progress" },
      h("div", { className: "runconsole-progress-shell" },
        h("div", { className: "runconsole-progress-head" },
          h("div", { className: "runconsole-progress-title" },
            h("span", { className: "runconsole-spinner", "aria-hidden": "true" }),
            h("div", null,
              h("span", { className: "eyebrow" }, "Pressure-test"),
              h("strong", null, stateLabel),
              h("small", null, runPhase(status)))),
          h("span", { className: `ds-tag ${status.heartbeatStale ? "warn" : "accent"}` }, stateLabel)),
        h("div", { className: `runconsole-progress-track ${determinate ? "" : "is-indeterminate"}`, role: "progressbar", "aria-valuemin": 0, "aria-valuemax": determinate ? budget : undefined, "aria-valuenow": determinate ? iteration : undefined, "aria-label": determinate ? `${iteration} of ${budget} rounds` : "Run progress" },
          h("div", { className: "runconsole-progress-fill", style: { width: determinate ? `${percent}%` : "38%" } })),
        h("div", { className: "runconsole-progress-meta" },
          h("span", null, details),
          status.lastUpdateAgeSeconds !== null && status.lastUpdateAgeSeconds !== undefined
            ? h("span", null, `last receipt ${ageText(status.lastUpdateAgeSeconds)}`)
            : null),
        status.heartbeatStale
          ? h("p", { className: "runconsole-progress-note warn" }, "No new telemetry has arrived recently. The durable job is still live, so this may be a long model call rather than a failed run.")
          : h("p", { className: "runconsole-progress-note" }, "You can leave this page. The run and its receipts are saved to project history.")));
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
        // Scenario picker — a use-case bundle (rubric + run config) for this run; "Default" keeps the
        // project's own rubric. Only shown when scenarios are installed, so the plain path stays plain.
        (scenarios && scenarios.length)
          ? h("label", { className: "runconsole-scenario" },
              h("span", null, "Scenario"),
              h("select", {
                value: selectedScenario || "",
                disabled: !liveMode || busy,
                onChange: (e) => onScenario && onScenario(e.target.value),
              },
                h("option", { value: "" }, "Default"),
                (scenarios || []).map((s) => h("option",
                  { key: s.name, value: s.name, title: s.description || "" }, displayText(s.name)))))
          : null,
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
