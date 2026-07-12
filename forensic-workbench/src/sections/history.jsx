import React from "react";
import { displayText } from "../design-system.js";

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
