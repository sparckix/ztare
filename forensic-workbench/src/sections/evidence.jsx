import React from "react";
import { displayMessage, Block, Tag } from "../design-system.js";

const h = React.createElement;

const TYPE_LABEL = {
  source_evidence: "evidence",
  seed_hypothesis: "hypothesis",
  research_question: "question",
  collection_todo: "to collect",
  untyped: "untyped",
};
function typeLabel(t) { return TYPE_LABEL[t] || (t ? String(t).replace(/_/g, " ") : "untyped"); }
function sizeLabel(chars) {
  const n = Number(chars || 0);
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k chars` : `${n} chars`;
}
function baseName(path) { return String(path || "").split("/").pop() || path; }

function Meter({ value, total }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return h("div", { className: "meter", role: "img", "aria-label": `${value} of ${total}` },
    h("div", { className: "meter-fill", style: { width: `${pct}%` } }));
}

// Evidence — "what backs my thesis, where is it thin, add more." Grounded in how the loop actually
// works: raw files in raw/ are the INPUT; compiling turns them into the typed, provenance-tracked,
// replayable evidence the loop reads (evidence.txt + compiled_evidence_packet.json). So this is a
// pipeline (add → compile → inspect), not two equal paths. Pure view; everything via `view`.
export function Evidence({ view, onPreview, onCompile, onAddFile, onAddCitedSource, onOpenGaps, onFetchGap, fetchRunning }) {
  const v = view || {};
  const backing = v.backing || {};
  const compile = v.compile || {};
  const groups = v.fileGroups || [];
  const health = v.sourceHealth || {};
  const gaps = v.gaps || {};
  const gapItems = Array.isArray(gaps.items) ? gaps.items : [];

  return h(
    "section",
    { className: "evidence", "aria-label": "Evidence" },

    // 1. Two properties, never one misleading "backed" count: source mapping says a file is traceable;
    // admitted decision support says the claim-to-source inference has passed the governed gate.
    h("div", { className: "evidence-standing", "aria-label": "Evidence standing" },
      h("section", null,
        h("span", { className: "eyebrow" }, "Source coverage"),
        backing.total
          ? h(React.Fragment, null,
              h("div", { className: "evidence-standing-value" },
                h("strong", null, `${backing.strong} / ${backing.total}`),
                h("span", null, "mapped to a project source")),
              h(Meter, { value: backing.strong, total: backing.total }),
              h("p", null, backing.thin
                ? `${backing.thin} extracted claim${backing.thin === 1 ? " has" : "s have"} no source mapping yet.`
                : "Every extracted claim has a source reference. This does not verify the inference."))
          : h("p", null, "Compile evidence to measure source coverage.")),
      h("section", { className: backing.decisionTotal && backing.decisionAdmitted < backing.decisionTotal ? "needs-verification" : "" },
        h("span", { className: "eyebrow" }, "Decision support"),
        backing.decisionTotal
          ? h(React.Fragment, null,
              h("div", { className: "evidence-standing-value" },
                h("strong", null, `${backing.decisionAdmitted} / ${backing.decisionTotal}`),
                h("span", null, "claims with admitted support")),
              h(Meter, { value: backing.decisionAdmitted, total: backing.decisionTotal }),
              h("p", null, backing.decisionAdmitted === backing.decisionTotal
                ? "Every governed decision claim has a checked support path."
                : "Highlight source text and verify which claim it can support."),
              backing.decisionAdmitted < backing.decisionTotal && onAddCitedSource
                ? h("button", { type: "button", className: "text-link", onClick: () => onAddCitedSource() }, "Verify claim support →")
                : null)
          : h("p", null, "Run or build the governed map to measure decision support."))),

    // 2. Compile pipeline — the central concept, explained.
    h(Block, { className: `evidence-compile ${compile.fresh ? "fresh" : "stale"}`, title: "Compiled evidence",
      actions: h("span", { className: `evidence-compile-state ${compile.fresh ? "fresh" : "stale"}` },
        compile.fresh ? "up to date" : "needs compiling") },
      h("p", { className: "evidence-compile-note" },
        "Your files in ", h("code", null, v.rawDir || "raw/"), " are the input. ",
        "Compiling turns them into the typed, provenance-tracked evidence the loop actually reads",
        compile.fresh ? " — and it's current." : ". The loop won't see your latest files until you compile."),
      compile.reason
        ? h("p", { className: "evidence-health warn" }, displayMessage(compile.reason))
        : null,
      // Source health — a changed-on-disk source means the loop is scoring an old version of it.
      health.stale
        ? h("p", { className: "evidence-health warn" },
            `${health.stale} file${health.stale === 1 ? " has" : "s have"} changed since you last compiled — the loop is still scoring the old version. Re-compile to use your latest files.`)
        : health.total
          ? h("p", { className: "evidence-health ok" }, `All ${health.total} sources match the compiled evidence.`)
          : null,
      h("div", { className: "evidence-compile-actions" },
        h("button", { type: "button", className: `chip primary ${compile.running ? "is-busy" : ""}`, disabled: !onCompile || compile.running, onClick: () => onCompile && onCompile() },
          compile.running ? "Compiling…" : (compile.fresh ? "Re-compile" : "Compile evidence")),
        v.compiledFile
          ? h("button", { type: "button", className: "chip", onClick: () => onPreview && onPreview({ type: "file", value: v.compiledFile }) },
              "Inspect compiled evidence")
          : null)),

    // 3. Your files — grouped by type, each with size + provenance, click to read.
    h(Block, { className: "evidence-files", title: "Your files",
      actions: h("span", { className: "evidence-files-count" },
        v.fileState === "loading"
          ? "loading"
          : v.fileState === "error"
            ? "unavailable"
            : `${v.fileCount || 0} file${v.fileCount === 1 ? "" : "s"}`,
        v.fileState === "ready" && v.untypedCount ? ` · ${v.untypedCount} untyped` : "",
        v.fileState === "ready" && v.invalidCount ? ` · ${v.invalidCount} with an invalid type` : "") },
      groups.length
        ? groups.map((g) =>
            h("div", { className: "evidence-file-group", key: g.type },
              h("h4", null, `${typeLabel(g.type)} (${g.files.length})`),
              h("ul", { className: "evidence-file-list" },
                g.files.map((f, i) =>
                  h("li", { key: i, className: `evidence-file-row ${f.invalid ? "invalid" : ""}` },
                    h("button", { type: "button", className: "evidence-file-name",
                      onClick: () => onPreview && onPreview({ type: "file", value: f.path }) }, baseName(f.path)),
                    h("span", { className: "evidence-file-meta" },
                      sizeLabel(f.chars),
                      f.provenance ? h("span", { className: "evidence-file-prov", title: `sha256 ${f.provenance}` }, ` · ${f.provenance.slice(0, 7)}`) : null,
                      f.stale ? h("span", { className: "evidence-file-warn" }, " · changed since compiled") : null,
                      f.invalid ? h("span", { className: "evidence-file-warn" }, " · invalid type") : null))))))
        : h("p", { className: "evidence-muted" },
            v.fileState === "loading"
              ? "Loading project files…"
              : v.fileState === "error"
                ? displayMessage(v.fileMessage || "Project files could not be loaded.")
                : "No files yet. Add what backs your thesis.")),

    // 4. Evidence work. Files join the project; a verified passage can carry a specific claim.
    h("div", { className: "evidence-add" },
      h("button", { type: "button", className: "chip primary", disabled: !onAddFile, onClick: () => onAddFile && onAddFile() }, "Add a file"),
      onAddCitedSource
        ? h("button", { type: "button", className: "chip", onClick: () => onAddCitedSource() }, "Verify claim support")
        : null,
      h("span", { className: "evidence-muted" }, "Add files to the project, then compile them. To make the decision rely on a source, highlight the exact passage and verify the claim it supports.")),

    // Missing evidence — what the run couldn't find. The kernel marks which gaps can be FETCHED from the
    // web; for those, one click runs the evidence agent (search → source → compile into typed evidence).
    gapItems.length
      ? h(Block, { className: "evidence-gaps", title: "Missing evidence",
          actions: h("span", { className: "evidence-gaps-sub" },
            gaps.fetchable
              ? `${gaps.fetchable} of ${gapItems.length} can be fetched from the web`
              : `${gapItems.length} gap${gapItems.length === 1 ? "" : "s"} the run flagged`) },
          h("ul", { className: "evidence-gap-list" },
            gapItems.map((g, i) =>
              h("li", { key: i, className: "evidence-gap" },
                h("div", { className: "evidence-gap-body" },
                  h("span", { className: `evidence-gap-sev sev-${g.severity}` }, g.severity),
                  h("p", { className: "evidence-gap-what" }, displayMessage(g.what))),
                g.online
                  ? h("button", {
                      type: "button", className: `chip primary evidence-gap-fetch ${fetchRunning ? "is-busy" : ""}`,
                      disabled: !onFetchGap || fetchRunning,
                      title: g.query ? `Searches the web (${g.query.slice(0, 80)}…), then compiles what it finds into typed evidence` : "Search the web for sources to close this gap",
                      onClick: () => onFetchGap && onFetchGap(g.target),
                    }, fetchRunning ? "Fetching…" : "Fetch online →")
                  : h("span", { className: "evidence-gap-local" }, "needs a local check")))))
      : (v.gapCount && gaps.ceiling
          ? h("p", { className: "evidence-gaps-ceiling" },
              `${v.gapCount} evidence gap${v.gapCount === 1 ? "" : "s"} — but the score is capped by what can be sourced at all, not by a missing file. More evidence won't lift it; the limit is the boundary of the available data.`)
          : null)
  );
}
