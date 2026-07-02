import React from "react";
import { displayMessage, Block, Tag } from "../design-system.js";
import { GraphView } from "./graphview.jsx";

const h = React.createElement;

// Graph-algorithmic structural reads (kernel-computed, no LLM) — insight the eye can't get from a node
// cloud: what the most rests on, the weakest link, the most-attacked claim, assertions with no evidence.
function StructuralReads({ insights, onFocus }) {
  const ins = insights || {};
  const rows = [];
  // li props: click a read to select+pan to that node on the graph (when it maps to a single node).
  const mk = (key, id) => id && onFocus
    ? { key, className: "rmap-read rmap-read-clickable", role: "button", tabIndex: 0,
        onClick: () => onFocus(id), title: "Show on the map" }
    : { key, className: "rmap-read" };
  if (ins.linchpin) rows.push(h("li", mk("lb", ins.linchpin.id),
    h("div", null, h(Tag, { tone: "accent" }, "linchpin"), h("span", { className: "rmap-read-label" }, displayMessage(ins.linchpin.label))),
    h("p", { className: "rmap-read-why" }, `Supports ${ins.linchpin.supports} other nodes — the most rests on this one.`)));
  if (ins.weakest_link) rows.push(h("li", mk("wl", ins.weakest_link.id),
    h("div", null, h(Tag, { tone: "danger" }, "weakest link"), h("span", { className: "rmap-read-label" }, displayMessage(ins.weakest_link.label))),
    h("p", { className: "rmap-read-why" }, `The lowest-probability claim in the spine (${Math.round((ins.weakest_link.probability || 0) * 100)}%) — settle this first.`)));
  if (ins.most_contested) rows.push(h("li", mk("mc", ins.most_contested.id),
    h("div", null, h(Tag, { tone: "warn" }, "most contested"), h("span", { className: "rmap-read-label" }, displayMessage(ins.most_contested.label))),
    h("p", { className: "rmap-read-why" }, `${ins.most_contested.challenges} challenges/falsifiers aim at it.`)));
  if (Array.isArray(ins.unsupported) && ins.unsupported.length) rows.push(h("li", mk("un", ins.unsupported[0].id),
    h("div", null, h(Tag, null, "no evidence"), h("span", { className: "rmap-read-label" }, `${ins.unsupported.length} assertion${ins.unsupported.length === 1 ? "" : "s"} with no source`)),
    h("p", { className: "rmap-read-why" }, ins.unsupported.map((u) => displayMessage(u.label)).join(" · "))));
  if (Array.isArray(ins.circular) && ins.circular.length) rows.push(h("li", mk("ci", ins.circular[0].id),
    h("div", null, h(Tag, { tone: "danger" }, "circular"), h("span", { className: "rmap-read-label" }, "Circular reasoning")),
    h("p", { className: "rmap-read-why" }, ins.circular.map((c) => displayMessage(c.label)).join(" → "))));
  if (ins.essential && ins.essential.length) rows.push(h("li", mk("es", ins.essential[0].id),
    h("div", null, h(Tag, { tone: "accent" }, "essential"), h("span", { className: "rmap-read-label" }, ins.essential.map((e) => displayMessage(e.label)).join(" · "))),
    h("p", { className: "rmap-read-why" }, "Every support-path to the thesis runs through this — a structural single point of failure (dominator).")));
  if (typeof ins.argument_strength === "number") rows.push(h("li", mk("as", "thesis"),
    h("div", null, h(Tag, { tone: ins.argument_strength >= 0.6 ? "ok" : "warn" }, "argument strength"),
      h("span", { className: "rmap-read-label" }, `${Math.round(ins.argument_strength * 100)}% after the debate nets out`)),
    h("p", { className: "rmap-read-why" }, "The thesis's strength once every support and attack propagates (bipolar argumentation / DF-QuAD) — not its bare probability.")));
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
  return h(Block, { title: "Structural reads", lead: "What the graph's shape says — computed, not eyeballed." },
    h("ul", { className: "rmap-reads" }, rows));
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
export function ResearchMap({ view, onOpenDetail, onIsomorphism, isomorphism }) {
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
    // Insights FIRST — the kernel-computed structural reads are the actionable layer (what to settle next,
    // what carries the most, what has no evidence). The graph below is for exploring; this is for deciding.
    h(StructuralReads, { insights: v.graphInsights, onFocus: setFocusId }),

    // The traversable graph — the run's reasoning DAG (sub-claims → the conclusion), reused from the
    // eval report. Click a node to see how likely it is and what would settle it; drag/zoom to explore.
    Array.isArray(v.graphNodes) && v.graphNodes.length
      ? h("div", { className: "rmap-graph-block" },
          h("div", { className: "rmap-group-head" },
            h("span", { className: "eyebrow" }, "The shape of the argument"),
            h("span", { className: "rmap-group-hint" }, "evidence on the left builds up to the thesis on the right; edges coloured by what they do — click a read above to jump to it, or a node to trace it")),
          h(GraphView, {
            nodes: v.graphNodes, edges: v.graphEdges, truncated: v.graphTruncated,
            focusId, onFocusHandled: () => setFocusId(null),
          }))
      : null,

    // "What is this like?" — the cross-field analogy (advisory). Map is its home (the trio: eigenquestion
    // in Thesis, isomorphism here, forecast in the Ask box).
    h(WhatIsThisLike, { onIsomorphism, isomorphism }),

    // Only the contested frontier in full text — "left to test" lives in Open points, support in Verdict
    // (no duplication); the graph already shows them as nodes.
    h(Group, { label: "Open tensions", hint: "unresolved — where the argument could still turn", items: v.tensions, tone: "warn" }));
}
