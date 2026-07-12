import React from "react";
import { Teach, displayMessage, EmptyState } from "../design-system.js";
import { compiledDecisionState } from "./decisionpanel.jsx";

const h = React.createElement;
const CLAIM_CANVAS_LIMIT = 900;

function claimExcerpt(text) {
  const raw = String(text || "").trim();
  if (raw.length <= CLAIM_CANVAS_LIMIT) return { text: raw, truncated: false };
  const boundary = raw.lastIndexOf(" ", CLAIM_CANVAS_LIMIT);
  const end = boundary > CLAIM_CANVAS_LIMIT * 0.65 ? boundary : CLAIM_CANVAS_LIMIT;
  return { text: `${raw.slice(0, end).trimEnd()}…`, truncated: true };
}

// "What would change my mind" reads best scannable. The text is usually one sentence of the form
// "Reject or demote the claim if A, if B, if C" or a "; "-separated list. Split into a lead + one
// bullet per condition; fall back to prose when it isn't a list.
export function falsifierItems(text) {
  const raw = String(text || "").trim();
  if (!raw) return { lead: "", items: [] };
  if (/;\s/.test(raw)) return { lead: "", items: raw.split(/;\s+/).map((s) => s.trim()).filter(Boolean) };
  const byIf = raw.split(/,?\s+if\s+/i);
  if (byIf.length > 2) {
    return { lead: byIf[0].replace(/[:,]?\s*$/, ""), items: byIf.slice(1).map((c) => `If ${c}`.replace(/\.\s*$/, "")) };
  }
  return { lead: "", items: [raw] };
}

function Meter({ value, total }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return h("div", { className: "meter", role: "img", "aria-label": `${value} of ${total}` },
    h("div", { className: "meter-fill", style: { width: `${pct}%` } }));
}

// A rail SummaryCard: the IA unit — eyebrow + headline + one fact + a link to the artifact's home.
function SummaryCard({ label, headline, fact, child, linkText, onClick, tone }) {
  return h(
    "section",
    { className: `summary-card ${tone || ""}` },
    h("span", { className: "summary-card-label" }, label),
    headline ? h("strong", { className: "summary-card-headline" }, headline) : null,
    child || null,
    fact ? h("p", { className: "summary-card-fact" }, fact) : null,
    linkText ? h("button", { type: "button", className: "summary-card-link", onClick }, linkText) : null
  );
}

// The Thesis screen — the project landing. Score is the headline (how the thesis held up when
// attacked); verdict + backing are secondary. L1 doc + rail. Pure view: everything via `view`.
export function Thesis({ view, decision, onOpenDetail, onOpenModal, onPreview, onEigenquestion, eigenquestion }) {
  const v = view || {};
  const eq = eigenquestion || {};
  const eqText = (eq.result && eq.result.eigenquestion) || "";
  const go = (workspace, subsection) => onOpenDetail && onOpenDetail(workspace, subsection);
  // The ledger is reference you peek at, not a workflow stage — open it in the reusable modal.
  const peek = (workspace, subsection) => (onOpenModal || onOpenDetail) && (onOpenModal || onOpenDetail)(workspace, subsection);
  const ruledOut = v.ruledOut || null;
  const falsifier = falsifierItems(v.falsifierText);
  const backing = v.backing || {};
  const assumptions = v.assumptions || {};
  const verdict = v.verdict || {};
  const compiled = compiledDecisionState(decision);
  const hasRun = v.score !== null && v.score !== undefined;
  const hasClaim = Boolean(v.claim);
  const claimRead = claimExcerpt(v.claim);

  // Header answers the eigenquestion "can I rely on it" — so the VERDICT leads, not the score. The
  // score is rubric-relative (partial), shown only as a caveated chip in the substatus line.
  // Use the CLI-derived tone (rely=high/green, verify_inference=mid/amber, do_not_rely=low/red) — NOT
  // `warn`, which is true for everything but "rely" and wrongly reddened the usable "verify" tier.
  const verdictTone = (compiled && ({ SUPPORTED: "high", BLOCKED: "mid", REFUTED: "low" }[compiled.status]))
    || verdict.tone || "mid";
  const headline = (compiled && compiled.headline)
    || (hasRun ? (verdict.phrase || "Decision not compiled yet") : "Not yet pressure-tested");
  const decisionReason = (compiled && compiled.reason)
    || verdict.why || (hasRun ? "" : "pressure-test the thesis to assess it");
  const scoreChip = hasRun
    ? h("span", {
        className: `thesis-score-chip band-${v.scoreBand || "mid"}`,
        title: "The latest run's score (0–100), measured against the current rubric. It's a partial, rubric-relative signal — under autoevolve the rubric changes across runs, so don't read it as a verdict. See Pressure-test for the full trajectory.",
      }, `run score ${v.score}`)
    : null;
  const header = h(
    "div",
    { className: "thesis-head" },
    h(
      "div",
      { className: "thesis-status" },
      h("span", {
        className: hasRun ? `thesis-verdict tone-${verdictTone}` : "thesis-verdict is-empty",
        onClick: hasRun ? undefined : () => go("run", "Start run"),
        role: hasRun ? undefined : "button",
      },
        h("span", { className: "thesis-verdict-dot" }),
        headline),
      h(
        "span",
        { className: "thesis-substatus" },
        scoreChip,
        // The WHY behind the verdict — the real per-claim backing mix (directly sourced vs inference
        // vs unsupported), computed by the CLI. This is the affordance "Almost there" never gave.
        h("span", null, decisionReason)
      )
    ),
    h(
      "div",
      { className: "thesis-actions" },
      h("button", { type: "button", className: `chip ${hasClaim ? "primary" : ""}`.trim(), onClick: () => go("run", "Start run") }, "Pressure-test"),
      h("button", { type: "button", className: "chip", onClick: () => go("sources", "Add file") }, "Add evidence"),
      hasClaim
        ? h("button", { type: "button", className: "chip", onClick: () => peek("overview", "Annotate a doc") }, "Check a draft")
        : null
    )
  );

  const main = h(
    "div",
    { className: "thesis-main" },
    !hasClaim
      ? h(
          "div",
          { className: "thesis-empty" },
          h(EmptyState, {
            text: "No thesis is recorded for this project yet.",
            action: h("button", { type: "button", className: "chip primary", onClick: () => go("sources", "Project brief") }, "Define the thesis"),
          })
        )
      : null,
    v.claim
      ? h(React.Fragment, null,
          h("blockquote", { className: "thesis-claim" }, h(Teach, { text: displayMessage(claimRead.text) })),
          claimRead.truncated
            ? h("div", { className: "thesis-claim-expand" },
                h("span", null, "Showing the opening of a longer thesis."),
                v.claimFile && onPreview
                  ? h("button", { type: "button", className: "text-link", onClick: () => onPreview({ type: "file", value: v.claimFile }) }, "Open full thesis")
                  : h("button", { type: "button", className: "text-link", onClick: () => go("sources", "Project brief") }, "Open project brief"))
            : null)
      : h("p", { className: "thesis-claim is-empty" },
          "No thesis recorded yet. State what you're arguing in your project brief."),
    v.claimWarning ? h("p", { className: "thesis-warning" }, displayMessage(v.claimWarning)) : null,

    h(
      "section",
      { className: "thesis-block" },
      h("h3", null, "What would change my mind"),
      falsifier.items.length
        ? h("div", null,
            falsifier.lead ? h("p", { className: "thesis-falsifier-lead" }, displayMessage(falsifier.lead)) : null,
            h("ul", { className: "thesis-falsifiers" },
              falsifier.items.map((item, i) => h("li", { key: i }, displayMessage(item)))))
        : h("button", { type: "button", className: "thesis-empty-cta", onClick: () => go("sources", "Project brief") },
            "No change-test yet — name the evidence that would make you drop this thesis →")
    ),

    h(
      "section",
      { className: "thesis-block" },
      h("h3", null, "Where it's weakest"),
      v.weakestPoint
        ? h("div", null,
            h("p", { className: "thesis-weakest" }, displayMessage(v.weakestPoint)),
            v.weakSpotsMore
              ? h("button", { type: "button", className: "thesis-more-link", onClick: () => go("run", "Ready to run") },
                  `${v.weakSpotsMore} more weak spot${v.weakSpotsMore === 1 ? "" : "s"} from the latest run →`)
              : null)
        : h("button", { type: "button", className: "thesis-empty-cta", onClick: () => go("run", "Start run") },
            hasRun ? "No weak point recorded this run." : "Pressure-test the thesis to find its weakest point →")
    ),

    ruledOut && ruledOut.summary
      ? h("section", { className: "thesis-block thesis-ruledout" },
          h("h3", null, "Scope — what this isn't claiming"),
          h("p", null, displayMessage(ruledOut.summary)),
          ruledOut.file && onPreview
            ? h("button", { type: "button", className: "thesis-more-link",
                onClick: () => onPreview({ type: "file", value: ruledOut.file }) }, "See the scope limits →")
            : null,
          // Ruled-out RIVAL explanations (alternatives found weaker) are a different thing from scope;
          // they live in the research map as the "does not explain" nodes.
          h("button", { type: "button", className: "thesis-more-link",
            onClick: () => go("overview", "Research map") }, "See rival explanations ruled out, in the map →"))
      : null,

    // Eigenquestion (advisory) — the one question that most moves the thesis. Ask the loop to propose it.
    onEigenquestion
      ? h("section", { className: "thesis-block thesis-eigen" },
          h("h3", null, "The question that matters most"),
          eqText
            ? h("p", { className: "thesis-eigen-q" }, displayMessage(eqText))
            : h("p", { className: "thesis-falsifier-lead" },
                "Ask the loop to propose the single question that, answered, would most move your confidence in this thesis — advisory, for your review."),
          eq.error ? h("p", { className: "thesis-warning" }, displayMessage(eq.error)) : null,
          h("button", { type: "button", className: eqText ? "thesis-more-link" : "chip", disabled: eq.running, onClick: () => onEigenquestion() },
            eq.running ? "Thinking…" : eqText ? "Propose another →" : "Sharpen the question →"))
      : null
  );

  const rail = h(
    "aside",
    { className: "thesis-rail" },
    h(SummaryCard, {
      label: "Backing",
      // The backing ratio is the thesis's headline stat — a big, band-coloured number, not an 11px label.
      headline: backing.total
        ? h("span", { className: "summary-card-big" },
            h("span", { className: `summary-card-big-num tone-${backing.thin ? "warn" : "ok"}` }, `${backing.strong}/${backing.total}`),
            h("span", { className: "summary-card-big-cap" }, backing.thin ? "backed" : "strong"))
        : null,
      child: backing.total
        ? h("div", { className: "summary-card-meter" }, h(Meter, { value: backing.strong, total: backing.total }))
        : null,
      // The ceiling distinction is the cheapest-fix signal: capped by missing data ≠ a weak claim.
      fact: backing.ceilingCapped
        ? "The score is capped by missing evidence — add sources, the thesis itself isn't the problem."
        : backing.total
          ? (backing.thin ? `${backing.thin} need a stronger source` : "every point has a source")
          : displayMessage(backing.sourceDetail || "Evidence base not summarized yet."),
      linkText: "Open evidence →",
      onClick: () => go("sources", "Prepare files"),
      tone: (backing.thin || backing.ceilingCapped) ? "warn" : ""
    }),
    h(SummaryCard, {
      label: "Assumptions",
      headline: `${assumptions.confirmed || 0} confirmed · ${assumptions.provisional || 0} provisional`,
      fact: assumptions.learnedThisRun
        ? `+${assumptions.learnedThisRun} learned this run${assumptions.topConstraint ? ` · "${assumptions.topConstraint}"` : ""}`
        : (assumptions.topConstraint ? `"${assumptions.topConstraint}"` : "No constraints learned yet."),
      linkText: assumptions.provisional || assumptions.confirmed ? "View the ledger →" : null,
      onClick: () => peek("overview", "Assumptions")
    })
  );

  return h(
    "section",
    { className: "thesis", "aria-label": "Thesis" },
    header,
    h("div", { className: "thesis-body" }, main, rail)
  );
}
