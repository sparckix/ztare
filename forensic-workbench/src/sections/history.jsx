import React from "react";
import { displayMessage, displayText, StatusLine } from "../design-system.js";

const h = React.createElement;

// Compact run trajectory sparkline — how the evaluator score moved across recent scored
// passes (decision.result.trajectory from /api/scenario-strength, plumbed in by main.js). Renders
// nothing when there's no usable series (needs 2+ scored iterations); the timeline is unaffected.
function trajectorySparkline(trajectory) {
  const iterations = (trajectory && Array.isArray(trajectory.iterations)) ? trajectory.iterations : [];
  const scored = iterations.filter((it) => it && typeof it.score === "number" && !Number.isNaN(it.score));
  if (scored.length < 2) return null;

  const scores = scored.map((it) => it.score);
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const span = max - min || 1;
  const w = 130, hgt = 30, pad = 4;
  const stepX = (w - pad * 2) / (scores.length - 1);
  const points = scores.map((s, i) => ({
    x: pad + i * stepX,
    y: pad + (1 - (s - min) / span) * (hgt - pad * 2),
  }));

  const first = scores[0];
  const last = scores[scores.length - 1];
  const delta = trajectory.score_delta;
  const label = `run score: ${first} → ${last}`
    + (typeof delta === "number" ? ` (Δ ${delta >= 0 ? "+" : ""}${delta})` : "");

  const sd = Array.isArray(trajectory.strength_delta) ? trajectory.strength_delta : null;
  const sdMoved = sd && sd.some((d) => Number(d) !== 0);

  return h("div", { className: "history-trajectory" },
    h("svg", { width: w, height: hgt, viewBox: `0 0 ${w} ${hgt}` },
      h("polyline", {
        points: points.map((p) => `${p.x},${p.y}`).join(" "),
        fill: "none", stroke: "var(--muted)", strokeWidth: 1.5,
        strokeLinecap: "round", strokeLinejoin: "round",
      }),
      points.map((p, i) => h("circle", { key: i, cx: p.x, cy: p.y, r: 2, fill: "var(--muted)" }))),
    h("p", null, label),
    sdMoved
      ? h("p", { className: "history-strength-delta" },
          `strength moved since last snapshot: Δ [${sd.map((d) => `${Number(d) >= 0 ? "+" : ""}${d}`).join(", ")}]`)
      : null);
}

const DECISION_TONE = { SUPPORTED: "ok", BLOCKED: "warn", REFUTED: "danger" };
const DECISION_WORD = { SUPPORTED: "Ready to rely on", BLOCKED: "Not ready to rely on", REFUTED: "Does not hold" };

function DecisionChange({ trajectory }) {
  const series = (trajectory && Array.isArray(trajectory.strength_series)) ? trajectory.strength_series : [];
  const snapshots = series.filter((row) => row && row.decision && row.decision.fingerprint);
  if (snapshots.length < 2) return null;
  const previous = snapshots[snapshots.length - 2];
  const current = snapshots[snapshots.length - 1];
  const before = previous.decision;
  const after = current.decision;
  const statusChanged = before.status !== after.status;
  const beforeTest = (before.next_test && before.next_test.text) || "No next test recorded";
  const afterTest = (after.next_test && after.next_test.text) || "No next test recorded";
  const beforeHinge = (before.hinge && before.hinge.text) || "No hinge recorded";
  const afterHinge = (after.hinge && after.hinge.text) || "No hinge recorded";
  const testChanged = beforeTest !== afterTest;
  const hingeChanged = beforeHinge !== afterHinge;
  const beforeGraph = previous.graph || {};
  const afterGraph = current.graph || {};
  const graphChanged = Boolean(beforeGraph.hash && afterGraph.hash && beforeGraph.hash !== afterGraph.hash);
  const graphSummary = graphChanged
    ? `${beforeGraph.nodes || 0} → ${afterGraph.nodes || 0} claims and evidence · ${beforeGraph.edges || 0} → ${afterGraph.edges || 0} relationships`
    : "";
  const changeHeadline = statusChanged
    ? "The decision posture changed"
    : graphChanged
      ? "The research map changed; the posture held"
      : "The posture held; its path changed";
  return h("section", { className: "history-decision-change", "aria-label": "Latest decision change" },
    h("div", { className: "history-decision-change-head" },
      h("div", null,
        h("span", { className: "eyebrow" }, "Latest decision change"),
        h("strong", null, changeHeadline)),
      h("div", { className: "history-decision-status" },
        h(StatusLine, { tone: DECISION_TONE[before.status] || "neutral" }, DECISION_WORD[before.status] || displayText(before.status)),
        h("span", { "aria-hidden": "true" }, "→"),
        h(StatusLine, { tone: DECISION_TONE[after.status] || "neutral" }, DECISION_WORD[after.status] || displayText(after.status)))),
    after.reason ? h("p", { className: "history-decision-reason" }, displayMessage(after.reason)) : null,
    h("dl", { className: "history-decision-facts" },
      hingeChanged ? h("div", null, h("dt", null, "Hinge"), h("dd", null, displayMessage(afterHinge))) : null,
      testChanged ? h("div", null, h("dt", null, "Next test"), h("dd", null, displayMessage(afterTest))) : null,
      graphChanged ? h("div", null, h("dt", null, "Research map"), h("dd", null, graphSummary)) : null,
      h("div", null, h("dt", null, "Recorded"), h("dd", null, displayText(current.timestamp || "now")))));
}

// History — a reverse-chronological ACTIVITY TIMELINE (Linear/Vercel/GitHub feed): day groups, a
// vertical spine with a type-coloured dot per event, human verbs + relative time, no raw paths.
// Repetitive same-kind events within a day collapse to one node ("· 12 times") but stay expandable.
// Pure view; main.js owns the data (buildHistoryView). See PRD §7.8.
export function History({ view, liveMode, onPreview, trajectory, jobs = [] }) {
  const v = view || {};
  const days = Array.isArray(v.days) ? v.days : [];
  const spark = trajectorySparkline(trajectory);
  const jobRows = (Array.isArray(jobs) ? jobs : []).slice(0, 5);

  if (!days.length) {
    return h("section", { className: "history", "aria-label": "History" },
      h(DecisionChange, { trajectory }),
      spark,
      jobRows.length ? h(JobHistory, { jobs: jobRows }) : null,
      h("p", { className: "history-empty" }, liveMode
        ? "Nothing saved yet — your decisions, evidence changes, runs, and checks will show up here as a timeline."
        : "Saved history is available when the workbench server is running."));
  }

  const openBtn = (item, label) =>
    item && item.openValue
      ? h("button", {
          type: "button", className: "history-open", disabled: !liveMode,
          onClick: () => onPreview && onPreview({ type: item.openType || "receipt", value: item.openValue }),
        }, label || (item.openType === "file" ? "Open file" : "Open"))
      : null;

  // One expanded entry on the spine (used when a node is expanded to its individual events).
  const subEntry = (it, i) =>
    h("li", { key: i, className: "history-sub" },
      h("span", { className: "history-sub-when" }, it.when),
      it.detail ? h("span", { className: "history-sub-detail" }, displayText(it.detail)) : null,
      openBtn(it));

  const node = (n, i) => {
    const meta = n.count > 1 ? `${n.count} times · latest ${n.latestWhen}` : n.latestWhen;
    const single = n.items[0];
    // A node with one item + a distinct detail reads as a single rich event.
    const headline = (n.count === 1 && single.detail) ? single.detail : displayText(n.verb);
    const rich = n.count === 1;
    return h("li", { key: i, className: `history-node tone-${n.tone}` },
      h("span", { className: "history-dot" }),
      h("div", { className: "history-node-body" },
        h("div", { className: "history-node-head" },
          h("strong", null, displayText(headline)),
          rich && single.detail ? h("span", { className: "history-node-verb" }, displayText(n.verb)) : null,
          h("small", null, meta),
          rich ? openBtn(single) : null),
        // The weakness this run exposed — the substance of the research log, not a scoreboard.
        rich && single.weakSpot
          ? h("p", { className: "history-weakspot" },
              h("span", { className: "history-weakspot-label" }, "Weak spot it exposed: "),
              displayText(single.weakSpot))
          : null,
        // Trust + ops chips (cross-checked / self-judged · updated rubric · cost · gates).
        rich && Array.isArray(single.meta) && single.meta.length
          ? h("div", { className: "history-chips" }, single.meta.map((m, mi) => h("span", { key: mi, className: "history-chip" }, m)))
          : null,
        // Multi-event nodes expand to the individual entries (decluttered, not hidden).
        n.count > 1
          ? h("details", { className: "history-expand" },
              h("summary", null, `show ${n.count} entries`),
              h("ul", { className: "history-subs" }, n.items.map(subEntry)))
          : null));
  };

  // Things that happened but didn't change the standing (probes, routine saves) — quiet footnotes.
  const footnotes = Array.isArray(v.footnotes) ? v.footnotes.filter(Boolean) : [];

  // Advisory "worth another pass?" verdict — is the program still compressing (tightening its explanation)
  // or into diminishing returns? Leads the log because it's the decision the reader faces. The ⓘ carries the
  // full method as a tooltip; this is NOT the judge score (which this tool treats as gameable).
  const cp = v.compression;
  const verdict = cp
    ? h("div", { className: `history-verdict tone-${cp.tone}` },
        h("div", { className: "history-verdict-head" },
          h("span", { className: "history-verdict-eyebrow" }, "Worth another pass?"),
          cp.how_computed
            ? h("span", { className: "history-verdict-info", tabIndex: 0, role: "note",
                title: cp.how_computed, "aria-label": cp.how_computed }, "ⓘ")
            : null),
        h("strong", { className: "history-verdict-headline" }, displayText(cp.headline)),
        cp.detail ? h("p", { className: "history-verdict-detail" }, displayText(cp.detail)) : null)
    : null;

  return h("section", { className: "history", "aria-label": "History" },
    verdict,
    v.summary ? h("p", { className: "history-summary" }, v.summary) : null,
    h(DecisionChange, { trajectory }),
    spark,
    jobRows.length ? h(JobHistory, { jobs: jobRows }) : null,
    days.map((day, di) =>
      h("div", { className: "history-day", key: di },
        h("div", { className: "history-day-label" }, displayText(day.label)),
        h("ul", { className: "history-spine" }, day.nodes.map(node)))),
    footnotes.length
      ? h("div", { className: "history-footnote" }, footnotes.map((f, fi) => h("p", { key: fi }, `+ ${f}`)))
      : null);
}

function JobHistory({ jobs }) {
  return h("section", { className: "history-jobs", "aria-label": "Background work" },
    h("div", { className: "history-jobs-head" },
      h("span", { className: "eyebrow" }, "Background work"),
      h("span", { className: "muted" }, "Persisted run receipts")),
    h("ul", null, jobs.map((job) => h("li", { key: job.id },
      h("strong", null, displayText(job.label || job.kind || "Project run")),
      h("span", { className: `history-job-status is-${displayText(job.status || "unknown")}` }, displayText(job.status || "unknown")),
      job.finished_at ? h("small", null, "finished") : h("small", null, "still open")))));
}
