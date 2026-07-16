import React from "react";
import { displayMessage, Block, Tag } from "../design-system.js";
import { GraphView } from "./graphview.jsx";

const h = React.createElement;

// Decision standing + next pass from core `decision_state` (via scenario strength) — not a second verdict.
// Terrain vocabulary is presentation only over existing carriers (insights + decision_state); no new kernel type.
const STANDING_TONE = { SUPPORTED: "ok", BLOCKED: "warn", REFUTED: "danger" };

function StructuralReads({ insights, onFocus, decisionState }) {
  const ins = insights || {};
  const ds = decisionState || {};
  const rows = [];
  // li props: click a read to select+pan to that node on the graph (when it maps to a single node).
  const mk = (key, id) => id && onFocus
    ? { key, "data-read-key": key, className: "rmap-read rmap-read-clickable", role: "button", tabIndex: 0,
        onClick: () => onFocus(id),
        onKeyDown: (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onFocus(id);
          }
        },
        title: "Show on the map" }
    : { key, "data-read-key": key, className: "rmap-read" };
  // Standing + next pass lead: operator question "where am I / what do I do next?"
  if (ds.status) {
    rows.push(h("li", mk("st", (ds.hinge && ds.hinge.id) || "thesis"),
      h("div", null,
        h(Tag, { tone: STANDING_TONE[ds.status] || "neutral" }, "standing"),
        h("span", { className: "rmap-read-label" }, displayMessage(ds.headline || ds.status))),
      h("p", { className: "rmap-read-why" },
        displayMessage(ds.reason || "Based on evidence that has been checked and admitted — not a model score."))));
  }
  if (ds.next_test && (ds.next_test.id || ds.next_test.text)) {
    rows.push(h("li", mk("np", ds.next_test.id),
      h("div", null,
        h(Tag, { tone: "accent" }, "next pass"),
        h("span", { className: "rmap-read-label" }, displayMessage(ds.next_test.text || ds.next_test.id))),
      h("p", { className: "rmap-read-why" },
        ds.next_test.flips_alone
          ? "Settling this alone can flip the verdict — the highest-leverage open test."
          : `The best next test for changing the current decision${ds.next_test.in_cores ? ` · it reaches ${ds.next_test.in_cores} smallest unresolved ${ds.next_test.in_cores === 1 ? "dependency" : "dependencies"}` : ""}.`)));
  }
  // Elevation = structural necessity (dominators / essential).
  if (ins.essential && ins.essential.length) rows.push(h("li", mk("es", ins.essential[0].id),
    h("div", null, h(Tag, { tone: "accent" }, "ridge"), h("span", { className: "rmap-read-label" }, ins.essential.map((e) => displayMessage(e.label)).join(" · "))),
    h("p", { className: "rmap-read-why", title: "Graph-theory term: a dominator node" }, "Every support-path to the thesis runs through this — structural elevation, not a score.")));
  if (ins.linchpin) rows.push(h("li", mk("lb", ins.linchpin.id),
    h("div", null, h(Tag, { tone: "accent" }, "linchpin"), h("span", { className: "rmap-read-label" }, displayMessage(ins.linchpin.label))),
    h("p", { className: "rmap-read-why" }, `Supports ${ins.linchpin.supports} other nodes — the most rests on this one.`)));
  if (ins.weakest_link) rows.push(h("li", mk("wl", ins.weakest_link.id),
    h("div", null, h(Tag, { tone: "danger" }, "weakest link"), h("span", { className: "rmap-read-label" }, displayMessage(ins.weakest_link.label))),
    h("p", { className: "rmap-read-why" }, `The lowest-probability claim in the spine (${Math.round((ins.weakest_link.probability || 0) * 100)}%) — settle this first.`)));
  if (ins.most_contested) rows.push(h("li", mk("mc", ins.most_contested.id),
    h("div", null, h(Tag, { tone: "warn" }, "valley"), h("span", { className: "rmap-read-label" }, displayMessage(ins.most_contested.label))),
    h("p", { className: "rmap-read-why" }, `${ins.most_contested.challenges} challenges/falsifiers aim at it — contested low ground.`)));
  if (Array.isArray(ins.unsupported) && ins.unsupported.length) rows.push(h("li", mk("un", ins.unsupported[0].id),
    h("div", null, h(Tag, null, "no evidence"), h("span", { className: "rmap-read-label" }, `${ins.unsupported.length} assertion${ins.unsupported.length === 1 ? "" : "s"} with no source`)),
    h("p", { className: "rmap-read-why" }, ins.unsupported.map((u) => displayMessage(u.label)).join(" · "))));
  if (Array.isArray(ins.circular) && ins.circular.length) rows.push(h("li", mk("ci", ins.circular[0].id),
    h("div", null, h(Tag, { tone: "danger" }, "circular"), h("span", { className: "rmap-read-label" }, "Circular reasoning")),
    h("p", { className: "rmap-read-why" }, ins.circular.map((c) => displayMessage(c.label)).join(" → "))));
  if (typeof ins.argument_strength === "number") rows.push(h("li", mk("as", "thesis"),
    h("div", null, h(Tag, { tone: ins.argument_strength >= 0.6 ? "ok" : "warn" }, "argument strength"),
      h("span", { className: "rmap-read-label" }, `${Math.round(ins.argument_strength * 100)}% after the debate nets out`)),
    h("p", { className: "rmap-read-why", title: "Computed via bipolar argumentation / DF-QuAD" }, "The thesis's strength once every support and attack propagates — not its bare probability.")));
  if (ins.debate_shift) rows.push(h("li", mk("ds", ins.debate_shift.id),
    h("div", null, h(Tag, { tone: ins.debate_shift.direction === "weakened" ? "danger" : "ok" }, ins.debate_shift.direction),
      h("span", { className: "rmap-read-label" }, displayMessage(ins.debate_shift.label))),
    h("p", { className: "rmap-read-why" }, `The debate ${ins.debate_shift.direction} this by ${Math.abs(Math.round((ins.debate_shift.delta || 0) * 100))} points vs. its bare probability.`)));
  // The single support link the whole argument hangs on — cut it and N nodes lose their path to the thesis.
  if (ins.critical_link) rows.push(h("li", mk("cl", ins.critical_link.from),
    h("div", null, h(Tag, { tone: "danger" }, "single link"),
      h("span", { className: "rmap-read-label" }, `${displayMessage(ins.critical_link.from_label)} → ${displayMessage(ins.critical_link.to_label)}`)),
    h("p", { className: "rmap-read-why" }, `If this one link fails, ${ins.critical_link.disconnects} node${ins.critical_link.disconnects === 1 ? "" : "s"} lose their support-path to the thesis — the highest-leverage thing to pressure-test or defend.`)));
  // Illusory redundancy (Jaccard over evidence sets) — two "independent" legs that actually share a base.
  if (Array.isArray(ins.correlated_support) && ins.correlated_support.length) {
    const c = ins.correlated_support[0];
    rows.push(h("li", mk("cs", c.a),
      h("div", null, h(Tag, { tone: "warn" }, "two legs, one base"),
        h("span", { className: "rmap-read-label" }, `${displayMessage(c.a_label)} + ${displayMessage(c.b_label)}`)),
      h("p", { className: "rmap-read-why" }, `These look like independent support but share ${c.shared} of their sources (${Math.round((c.jaccard || 0) * 100)}% overlap) — one retracted source knocks out both. Find a genuinely independent line.`)));
  }
  // Controversy — how balanced support-mass vs attack-mass is at the thesis (a coin-flip vs one-sided).
  if (ins.polarization && ins.polarization.leaning === "contested") rows.push(h("li", mk("pol", "thesis"),
    h("div", null, h(Tag, { tone: "warn" }, "contested"),
      h("span", { className: "rmap-read-label" }, `Support and attack are near-balanced (${Math.round((ins.polarization.score || 0) * 100)}%)`)),
    h("p", { className: "rmap-read-why" }, "The thesis is close to a coin-flip once support and attack mass net out — a genuine open question, not settled either way. Break the tie before you rely on it.")));
  // Independent lines of argument (fronts) — the thesis rests on separate threads that each stand alone.
  if (Array.isArray(ins.fronts) && ins.fronts.length >= 2) rows.push(h("li", mk("fr", ins.fronts[0].nodes && ins.fronts[0].nodes[0] && ins.fronts[0].nodes[0].id),
    h("div", null, h(Tag, { tone: "accent" }, `${ins.fronts.length} lines of argument`),
      h("span", { className: "rmap-read-label" }, "The thesis stands on separate threads")),
    h("p", { className: "rmap-read-why" }, `Peel away the shared spine and the support splits into ${ins.fronts.length} independent lines (${ins.fronts.map((f) => `${f.size} claims`).join(", ")}) — redundancy is real here, no single failure sinks all of it.`)));
  // A claim falsified and left unanswered (grounded/Dung, sharpened to decisive falsifiers only).
  if (Array.isArray(ins.defeated) && ins.defeated.length) rows.push(h("li", mk("df", ins.defeated[0].id),
    h("div", null, h(Tag, { tone: "danger" }, "falsified"),
      h("span", { className: "rmap-read-label" }, ins.defeated.map((d) => displayMessage(d.label)).join(" · "))),
    h("p", { className: "rmap-read-why" }, "A falsifier landed on this and nothing rebuts it — under the strict reading it doesn't stand. Answer the falsifier or drop the claim.")));
  if (!rows.length) return null;
  // A terrain read is a compass, not a dump of every graph calculation. Keep the standing, the next test,
  // and the most consequential structural condition in view; the rest remains one disclosure away.
  const primaryOrder = ["st", "np", "df", "ci", "cl", "wl", "mc", "un", "cs", "pol", "es", "lb", "fr", "as", "ds"];
  const byKey = new Map(rows.map((row) => [row && row.props && row.props["data-read-key"], row]));
  const primary = primaryOrder.map((key) => byKey.get(key)).filter(Boolean).slice(0, 3);
  const primarySet = new Set(primary.map((row) => row.props["data-read-key"]));
  const secondary = rows.filter((row) => !primarySet.has(row && row.props && row.props["data-read-key"]));
  return h(Block, { title: "Decision terrain", lead: "Where the decision stands, what would move it, and the shape most worth inspecting." },
    h("ul", { className: "rmap-reads" }, primary),
    secondary.length
      ? h("details", { className: "rmap-reads-more" },
          h("summary", null, `${secondary.length} more structural read${secondary.length === 1 ? "" : "s"}`),
          h("ul", { className: "rmap-reads" }, secondary))
      : null);
}

// Isomorphism (advisory) — "what is this like, and what does that predict?" Asks the loop to deanchor
// from the project's own field and name an established result elsewhere with the same structure, plus a
// sharp prediction whose failure would refute the transport. A candidate to forecast and test, never a
// result — so the copy says "ask the loop," and the prediction is framed as the next thing to settle.
function WhatIsThisLike({ onIsomorphism, isomorphism }) {
  if (!onIsomorphism) return null;
  const st = isomorphism || {};
  const rx = (st.result && st.result.ok) ? st.result : null;
  const body = rx
    ? [
        // The analogy, led big — the delightful payload ("oh, it's like X in another field").
        h("div", { key: "head", className: "rmap-iso-head" },
          h(Tag, { tone: "accent" }, "it's like"),
          h("span", { className: "rmap-iso-theorem" }, displayMessage(rx.source_theorem)),
          h("span", { className: "rmap-iso-field" }, "in " + displayMessage(rx.source_field))),
        // How that maps onto THIS problem — the substantive, specific part.
        h("div", { key: "map", className: "rmap-iso-mapblock" },
          h("span", { className: "eyebrow" }, "how it maps to your problem"),
          h("p", { className: "rmap-iso-map" }, displayMessage(rx.transported_structure))),
        // The action — composes into the forecast feature (the trio working together), and stays honest:
        // the loop surfaced the analogy; you derive the sharp consequence and forecast it.
        h("div", { key: "move", className: "rmap-iso-predict" },
          h("span", { className: "eyebrow" }, "your move — predict, then falsify"),
          h("p", null, "Derive the one sharp consequence this analogy forces at your seam, then forecast it in ",
            h("strong", null, "Ask the loop"), ". If it fails, the analogy doesn't transport — and you've learned where your problem is genuinely different.")),
        Array.isArray(rx.alternatives) && rx.alternatives.length
          ? h("div", { key: "alts", className: "rmap-iso-alts" },
              h("span", { className: "rmap-iso-alts-label" }, "other fields it rhymes with: "),
              rx.alternatives.map((a, i) => h(Tag, { key: i }, displayMessage(a.theorem || a.field))))
          : null,
      ]
    : [h("p", { key: "lead", className: "rmap-iso-lead" },
        "Stuck on this claim? Ask the loop what established result in another field has the same underlying structure. It deliberately looks away from your own discipline — that's where the non-obvious analogies live — and hands back something you can forecast and test. Advisory, never a verdict.")];
  return h(Block, { title: "What is this like?", className: "rmap-iso" },
    body,
    st.error ? h("p", { className: "rmap-iso-error" }, displayMessage(st.error)) : null,
    h("button", { type: "button", className: rx ? "thesis-more-link" : "chip", disabled: st.running,
      onClick: () => onIsomorphism() },
      st.running ? "Searching other fields…" : rx ? "Find another analogy →" : "Find an analogy →"));
}

function MapTime({ project, liveMode, freshness, onSnapshot, onCompare }) {
  const f = freshness || {};
  const result = f.result || {};
  const compare = result && result.ok && Object.prototype.hasOwnProperty.call(result, "decision_stale") ? result : null;
  const [reference, setReference] = React.useState({ loading: true, exists: false });
  React.useEffect(() => {
    if (!project || !liveMode) {
      setReference({ loading: false, exists: false });
      return undefined;
    }
    let cancelled = false;
    setReference({ loading: true, exists: false });
    fetch(`/api/scenario-baseline-status?project=${encodeURIComponent(project)}`, { headers: { Accept: "application/json" } })
      .then((response) => response.json())
      .then((payload) => { if (!cancelled) setReference({ loading: false, ...payload }); })
      .catch(() => { if (!cancelled) setReference({ loading: false, exists: false }); });
    return () => { cancelled = true; };
  }, [project, liveMode]);
  if (!project || !liveMode) return null;
  const saveReference = async () => {
    const saved = await Promise.resolve(onSnapshot && onSnapshot());
    if (saved && saved.ok) setReference((previous) => ({ ...previous, loading: false, exists: true, verdict: saved.verdict || "" }));
  };
  const hasReference = Boolean(reference.exists || result.snapshotted);
  const graphDelta = (compare && compare.graph_delta) || {};
  const deltaGroups = compare ? [
    { key: "added", label: "Added claims", kind: "node", tone: "ok", rows: graphDelta.nodes_added || [] },
    { key: "removed", label: "Removed claims", kind: "node", tone: "danger", rows: graphDelta.nodes_removed || [] },
    { key: "changed", label: "Reworded claims", kind: "change", tone: "accent", rows: graphDelta.nodes_changed || [] },
    { key: "links-added", label: "New connections", kind: "edge", tone: "ok", rows: graphDelta.edges_added || [] },
    { key: "links-removed", label: "Removed connections", kind: "edge", tone: "danger", rows: graphDelta.edges_removed || [] },
  ].filter((group) => group.rows.length) : [];
  const renderDelta = (group, row, index) => {
    if (group.kind === "change") {
      return h("li", { key: row.id || index, className: "rmap-delta-change" },
        h("div", null, h(Tag, { tone: "neutral" }, "before"), h("span", null, displayMessage(row.before))),
        h("div", null, h(Tag, { tone: "accent" }, "now"), h("span", null, displayMessage(row.after))));
    }
    if (group.kind === "edge") {
      return h("li", { key: `${row.from}:${row.relation}:${row.to}:${index}`, className: "rmap-delta-edge" },
        h("span", null, displayMessage(row.from_text)),
        h(Tag, { tone: group.tone }, displayText(row.relation)),
        h("span", null, displayMessage(row.to_text)),
        row.warrant ? h("small", null, `warrant ${displayText(row.warrant)}`) : null);
    }
    return h("li", { key: row.id || index, className: "rmap-delta-node" },
      row.kind ? h(Tag, { tone: group.tone }, displayText(row.kind)) : null,
      h("span", null, displayMessage(row.text)));
  };
  const deltaCount = Object.values(graphDelta.counts || {}).reduce((total, count) => total + Number(count || 0), 0);
  return h("section", { className: "rmap-time", "aria-label": "Map time" },
    h("div", { className: "rmap-time-head" },
      h("div", null,
        h("span", { className: "eyebrow" }, "Decision change"),
        h("strong", null, "Save a reference, then check what changed")),
      h("div", { className: "rmap-time-actions" },
        h("button", { type: "button", className: hasReference ? "chip ghost" : "chip primary", disabled: f.running || reference.loading,
          onClick: saveReference }, f.running ? "Saving…" : hasReference ? "Replace reference" : "Save current reference"),
        hasReference ? h("button", { type: "button", className: "chip", disabled: f.running, onClick: onCompare }, "Check for changes") : null)),
    h("p", { className: "rmap-time-copy" }, hasReference
      ? "A saved decision reference is available. Check the current map against it after evidence or assumptions change."
      : "Save today's decision state first. Later, this will show exactly which claims and next tests changed."),
    f.running ? h("p", { className: "muted" }, "Checking the current decision…") : null,
    f.error ? h("p", { className: "rmap-iso-error" }, displayMessage(f.error)) : null,
    f.result && f.result.snapshotted
      ? h("p", { className: "muted" }, "Reference saved. Check for changes after the next admitted update.")
      : null,
    compare
      ? h("div", { className: `rmap-time-result ${compare.decision_stale ? "is-stale" : "is-held"}` },
          h("strong", null, compare.decision_stale ? "The standing changed" : "The standing held"),
          h("span", null, `${displayMessage(compare.was)} → ${displayMessage(compare.now)}`),
          compare.flipped && compare.flipped.length
            ? h("span", null, `${compare.flipped.length} claim${compare.flipped.length === 1 ? "" : "s"} flipped`)
            : h("span", null, "No claims flipped"),
          compare.to_test && compare.to_test.length
            ? h("p", null, h("b", null, "Next to test: "), displayMessage(compare.to_test[0].text || compare.to_test[0].assumption))
            : null,
          deltaGroups.length
            ? h("details", { className: "rmap-time-diff", open: Boolean(compare.decision_stale) },
                h("summary", null, h("span", null, "Argument changes"), h("strong", null, `${deltaCount} change${deltaCount === 1 ? "" : "s"}`)),
                h("div", { className: "rmap-time-diff-groups" },
                  deltaGroups.map((group) => h("section", { key: group.key },
                    h("span", { className: "eyebrow" }, `${group.label} · ${group.rows.length}`),
                    h("ul", null, group.rows.slice(0, 6).map((row, index) => renderDelta(group, row, index))))))
              )
            : null)
      : null);
}

// One group of the program's live structure — a labelled list of points (tensions / to-test / support).
function Group({ label, hint, items, tone }) {
  if (!items || !items.length) return null;
  return h("section", { className: `rmap-group ${tone || ""}` },
    h("div", { className: "rmap-group-head" },
      h("span", { className: "eyebrow" }, label),
      hint ? h("span", { className: "rmap-group-hint" }, hint) : null),
    h("ul", { className: "rmap-points" },
      items.slice(0, 8).map((it, i) => h("li", { key: i }, displayMessage(it)))));
}

// Research map — the program's live structure: what's contested, what's left to test, what holds it up.
// The kernel's generic scaffold graph (Orientation/Synthesis/Handoffs) is dropped as noise; this shows
// the three things a researcher actually steers by. Pure view.
export function ResearchMap({
  view, onOpenDetail, onIsomorphism, isomorphism,
  project, liveMode, decision, onDecisionRefresh, agenda, onAgendaRefresh, wagers, onWagersRefresh, onGraphRefresh,
  onPrefillDecisionTest, onExecuteDecisionTest,
  freshness, onSnapshotBaseline, onRecompile,
}) {
  const v = view || {};
  // A read clicked in Structural reads focuses that node on the graph below (select + pan). One-shot: the
  // graph clears it via onFocusHandled so the same read can be clicked again.
  const [focusId, setFocusId] = React.useState(null);

  if (!v.hasContent) {
    return h("section", { className: "rmap", "aria-label": "Research map" },
      h("p", { className: "rmap-empty" },
        "Your program hasn't branched yet. As you run the loop, the open tensions, the branches left to test, and the strongest support show up here — the structure of the argument, not just the claim."),
      // "What is this like?" needs only a claim, not a branched graph — so it's available from the start.
      h(WhatIsThisLike, { onIsomorphism, isomorphism }));
  }

  return h("section", { className: "rmap", "aria-label": "Research map" },
    // The GRAPH FIRST — the map is what the operator opened this screen to see; the stack of structural-read
    // text used to push it below the fold (operator: "a lot of wall of text before getting to the map"). The
    // computed reads move directly BELOW it — one glance away, not a wall in front.
    Array.isArray(v.graphNodes) && v.graphNodes.length
      ? h("div", { className: "rmap-graph-block" },
          h("div", { className: "rmap-group-head" },
            h("span", { className: "eyebrow" }, "The shape of the argument")),
          h(GraphView, {
            nodes: v.graphNodes, edges: v.graphEdges, truncated: v.graphTruncated, argument: v.graphArgument,
            focusId, onFocusHandled: () => setFocusId(null),
            project, liveMode, decision, onDecisionRefresh, agenda, onAgendaRefresh, wagers, onWagersRefresh,
            onRefresh: onGraphRefresh, onOpenDetail, onPrefillDecisionTest, onExecuteDecisionTest,
          }))
      : null,

    // Core carriers only: research-graph insights + decision_state (from scenario strength). No plugin nouns.
    h(StructuralReads, {
      insights: v.graphInsights,
      onFocus: setFocusId,
      decisionState: (decision && decision.result && decision.result.decision_state) || null,
    }),

    h(MapTime, { project, liveMode, freshness, onSnapshot: onSnapshotBaseline, onCompare: onRecompile }),

    // "What is this like?" — the cross-field analogy (advisory). Map is its home (the trio: eigenquestion
    // in Thesis, isomorphism here, forecast in the Ask box).
    h(WhatIsThisLike, { onIsomorphism, isomorphism }),

    // Only the contested frontier in full text — "left to test" lives in Open points, support in Verdict
    // (no duplication); the graph already shows them as nodes.
    h(Group, { label: "Open tensions", hint: "unresolved — where the argument could still turn", items: v.tensions, tone: "warn" }));
}
