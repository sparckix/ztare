import React from "react";
import { RotateCw } from "lucide-react";
import { displayText, Block, StatusLine, FactRow } from "../design-system.js";

const h = React.createElement;

// Decision — the "how firmly" block on Verdict (PRD §4.2a): a strength profile (which tiers of backing you
// actually have), what the call rests on, how many independent legs it stands on, any hard cruxes. Lane-labelled
// "From the governed map:" because the scenario kernel's graded strength and the spine's crisp reliability
// verdict are two DIFFERENT engines until the loop consumes the governed seams — this block never overrides the
// crisp verdict above it. Pure PM language: "proven / reproducible / cited / unchecked" IS the plain-language
// backing tiers (no engine jargon). The challenge queue moved to Open points (see ChallengeQueueBlock below) —
// it's a worklist, not part of the judgment.

export const STATUS_TONE = { CONTESTED: "warn", REFUTED: "danger", UNSUPPORTED: "neutral", NONCONVERGENT: "neutral" };
export const STATUS_WORD = {
  CONTESTED: "Contested — supported but with open challenges",
  REFUTED: "Refuted",
  UNSUPPORTED: "Unsupported — nothing backs this yet",
  NONCONVERGENT: "Unresolved — the argument loops",
};
const TIERS = ["proven", "reproducible", "cited", "unchecked"];
export const DECISION_TONE = { SUPPORTED: "ok", BLOCKED: "warn", REFUTED: "danger" };

export function compiledDecisionState(decision) {
  const result = decision && decision.result;
  return (result && result.decision_state) || null;
}

function profileIsBlank(profile) {
  return !(profile || []).some((v) => Number(v) > 0);
}

// ONE readiness signal for every governed-map block app-wide (Verdict/Open points/Map) — a real graded
// read exists once the strength profile has a non-zero tier, OR it rests on something, OR there's a
// challenge queue. Anything less is "nothing graded here yet", never a dead "bind evidence" CTA (there is
// no bind route) — see the callers for the honest not-ready line + which blocks hide entirely.
export function governedMapReady(result) {
  const strength = (result && result.strength) || {};
  const restsOn = meaningfulRests(result);
  const queue = (result && result.challenge_queue) || [];
  return !profileIsBlank(strength.profile) || restsOn.length > 0 || queue.length > 0;
}

export function meaningfulRests(result) {
  return ((result && result.rests_on) || []).filter((pair) =>
    Math.abs(Number(pair && pair[1]) || 0) >= 0.005);
}

export function governedMapHasMaterial(result) {
  const counts = ((result && result.decision_state) || {}).counts || {};
  const corroboration = (result && result.corroboration) || [];
  return Number(counts.evidence) > 0
    || Number(corroboration[3]) > 0
    || ((result && result.rests_on) || []).length > 0;
}

function ProfileBar({ profile }) {
  const p = profile || [];
  return h("div", { className: "decision-profile" },
    TIERS.map((label, i) => {
      const v = Math.max(0, Math.min(1, Number(p[i]) || 0));
      return h("div", { key: label, className: "decision-profile-row" },
        h("span", { className: "decision-profile-label" }, label),
        h("div", { className: "meter" }, h("div", { className: "meter-fill accent", style: { width: `${v * 100}%` } })),
        h("span", { className: "decision-profile-value" }, v.toFixed(2)));
    }));
}

// The shape IS the point — a headline like 0,0,0.97,0.97 ("a castle of citations") says more than the number.
function shapeCaption(profile) {
  const p = profile || [];
  const [proven, repro, cited] = [0, 1, 2].map((i) => Number(p[i]) || 0);
  if (profileIsBlank(p)) return "No admitted support reaches the thesis at any trust floor.";
  if (cited > 0 && proven === 0 && repro === 0) return "a castle of citations — plenty is cited, but nothing here is reproducible or proven.";
  if (proven > 0.5) return "solid footing — a good share of this is proven.";
  if (proven === 0 && repro === 0) return "entirely unchecked — no independent check behind it yet.";
  return "a mix of tiers — see which ones are thin before you lean on it.";
}

function RestsOn({ result }) {
  const rests = meaningfulRests(result);
  if (!rests.length) return null;
  const textOf = (result && result.text_of) || {};
  const visible = rests.slice(0, 4);
  const positiveTotal = rests.reduce((sum, pair) => sum + Math.max(0, Number(pair && pair[1]) || 0), 0);
  const contributorText = (id) => displayText(textOf[id] || id)
    .replace(/\s*\(source evidence\)\s*$/i, "").replace(/\s+/g, " ").trim();
  return h("section", { className: "decision-contributors", "aria-label": "Evidence carrying the decision" },
    h("h3", null, "Evidence carrying the decision"),
    h("ul", { className: "decision-restson" },
      visible.map((pair, i) => {
        const sid = (pair && pair[0]) != null ? pair[0] : "";
        const c = Number(pair && pair[1]) || 0;
        const share = c > 0 && positiveTotal > 0 ? Math.round((c / positiveTotal) * 100) : 0;
        return h("li", { key: sid || i },
          h("div", { className: "decision-contributor-head" },
            h("span", null, contributorText(sid)),
            h("strong", { className: c < 0 ? "is-negative" : "" }, c < 0 ? "weakens" : `${share}%`)),
          c > 0 ? h("div", { className: "meter", "aria-hidden": "true" },
            h("div", { className: "meter-fill accent", style: { width: `${share}%` } })) : null);
      })),
    rests.length > visible.length
      ? h("p", { className: "muted decision-contributor-more" }, `${rests.length - visible.length} more contributing source${rests.length - visible.length === 1 ? "" : "s"}`)
      : null);
}

function corroborationLine(corroboration) {
  const c = corroboration || [];
  const proven = Number(c[0]) || 0;
  const reproducible = Number(c[1]) || 0;
  const cited = Number(c[2]) || 0;
  const mapped = Number(c[3]) || 0;
  if (!cited) {
    return mapped
      ? `${mapped} source${mapped === 1 ? " is" : "s are"} mapped to this project, but none has a verified passage attached to this decision.`
      : "No source currently has a verified passage attached to this decision.";
  }
  const details = [];
  if (reproducible) details.push(`${reproducible} reproducible`);
  if (proven) details.push(`${proven} proven`);
  return `${cited} independent source${cited === 1 ? " meets" : "s meet"} the cited threshold${details.length ? `; ${details.join(", ")}` : ""}.`;
}

function EvidenceReadiness({ hasMaterial, corroboration, nextTest, onReviewEvidence }) {
  const nextText = nextTest && nextTest.text ? displayText(nextTest.text) : "Identify the claim that needs support, then review the available evidence.";
  return h("section", { className: `evidence-readiness ${hasMaterial ? "has-sources" : ""}`, "aria-label": "Evidence readiness" },
    h("div", { className: "evidence-readiness-summary" },
      h(StatusLine, { tone: "neutral" }, hasMaterial ? "Sources need verification" : "No source attached yet"),
      h("p", null, hasMaterial
        ? corroborationLine(corroboration)
        : "No project source is carrying this decision yet.")),
    h("div", { className: "evidence-readiness-next" },
      h("span", { className: "evidence-readiness-next-label" }, "Next to resolve"),
      h("p", null, nextText)),
    h("button", { type: "button", className: "chip primary", disabled: !onReviewEvidence,
      title: "Review the available sources and attach evidence to the claim that needs support",
      onClick: () => onReviewEvidence && onReviewEvidence() }, "Review evidence gap"));
}

function CruxBlock({ crux }) {
  if (!crux || !crux.length) return null;
  return h(Block, { title: "These two cannot both stand" },
    h("ul", { className: "decision-crux" },
      crux.map((c, i) => h("li", { key: i }, `${displayText(c.a_text || c.a)}  ⟂  ${displayText(c.b_text || c.b)}`))));
}

// Challenge queue — moved OUT of the Decision block per PRD §4.2a ("its challenge queue is a worklist, not a
// judgment"). Mounted on Open points instead, reusing the same `decision` read (no second fetch).
export function ChallengeQueueBlock({ project, liveMode, decision, onRefresh }) {
  const canRun = liveMode && !!project;
  React.useEffect(() => { if (canRun && !decision && onRefresh) onRefresh(); }, [project, liveMode]);  // eslint-disable-line
  const result = (decision && decision.result) || null;
  const rows = ((result && result.challenge_queue) || []).slice(0, 8);
  if (!rows.length) return null;
  const maxDrag = Math.max(0, ...rows.map((r) => Math.abs(Number(r.drag) || 0)));
  const hasMeaningfulDrag = maxDrag > 0.0005;
  return h(Block, { title: "What's holding the decision back",
    lead: hasMeaningfulDrag
      ? "Resolve these first: they would move the current decision the most."
      : "These are the unresolved checks in the current decision. None has a meaningful priority estimate yet." },
    h("ol", { className: "decision-challenge" },
      rows.map((r, i) => h("li", { key: r.id || i },
        h("span", { className: "decision-challenge-drag" }, hasMeaningfulDrag ? `Priority ${i + 1}` : "Unresolved"),
        hasMeaningfulDrag
          ? h("div", { className: "meter", "aria-label": `Relative effect of priority ${i + 1}` },
              h("div", { className: "meter-fill attention", style: { width: `${(Math.abs(Number(r.drag) || 0) / maxDrag) * 100}%` } }))
          : null,
        h("span", null, displayText(r.text))))));
}

const RECHECK_TONE = { earned: "ok", held: "ok", demoted: "warn", failed: "warn", expired: "neutral", missing_capability: "danger" };
const RECHECK_WORD = {
  earned: "re-earned", held: "still holds", demoted: "backing lost", failed: "check failed",
  expired: "expired (stale)", missing_capability: "check unavailable",
};
const TIER_WORD = { W0: "proven", W1: "reproducible", W2: "cited", W3: "unchecked" };
// The reliability prior (J5 "can I rely on this?"): the empirical hold-rate per backing tier, read from the
// recheck receipts (real re-executions). Silent when no re-checks exist; "not enough to calibrate (N=…)" below
// the threshold; a rate only once a tier has enough — never a fabricated %.
function calibrationLine(cal) {
  if (!cal || !cal.n_total) return null;
  const hit = Object.entries(cal.per_tier || {}).find(([, v]) => v && v.rate != null);
  if (hit) {
    const [tier, v] = hit;
    return h("p", { className: "decision-shape" },
      `Reliability: ${tier}-tier backing has held ${Math.round(v.rate * 100)}% of ${v.total} re-checks.`);
  }
  return h("p", { className: "decision-shape" },
    `Reliability: not enough re-checks to calibrate yet (N=${cal.n_total}).`);
}


// What the scenario did — the post-run attribution mirror of the pre-run authoring surface: which scenario/
// rubric actually drove the run, and how its score moved, read straight off existing run artifacts (never
// recomputed, never fabricated). A supporting card, not a hero. Self-contained: owns its own fetch
// (GET /api/scenario-attribution).
function scoreMoveRow(baseline, latest) {
  if (baseline == null && latest == null) return h(FactRow, { label: "Score" }, "not recorded for this run");
  if (baseline == null || latest == null) return h(FactRow, { label: "Score" }, `${baseline == null ? "—" : baseline} → ${latest == null ? "—" : latest}`);
  const delta = Number(latest) - Number(baseline);
  const cue = delta > 0 ? "rising" : delta < 0 ? "falling" : "flat";
  return h(FactRow, { label: "Score" }, `${baseline} → ${latest}  (${delta >= 0 ? "+" : ""}${delta}, ${cue})`);
}

function AttributionCard({ attribution }) {
  const a = attribution;
  if (!a || a.ok === false || !a.has_run) return null;
  const failedGates = (a.gates || []).filter((g) => g && g.outcome === "fail");
  const dims = a.dimensions_scored || [];
  return h(Block, { title: "What the scenario did" },
    h(FactRow, { label: "Scenario" }, displayText(a.scenario || "(not recorded)")),
    h(FactRow, { label: "Rubric" }, displayText(a.rubric || "(not recorded)")),
    scoreMoveRow(a.score_baseline, a.score_latest),
    h(FactRow, { label: "Verdict" }, displayText(a.verdict || "(not recorded)")),
    dims.length
      ? h(FactRow, { label: "Per-dimension" }, dims.map((d) => `${displayText(d.name)}: ${d.score}`).join(" · "))
      : h("p", { className: "muted" }, "Per-dimension scores are not persisted for this run."),
    failedGates.length
      ? h("p", { className: "decision-error" }, `Failed gates: ${failedGates.map((g) => displayText(g.name)).join(", ")}`)
      : null,
    (a.notes || []).length
      ? h("ul", { className: "muted" }, a.notes.map((n, i) => h("li", { key: i }, n)))
      : null);
}

function RecheckSection({ recheck }) {
  if (!recheck) return null;
  if (recheck.running) return h("p", { className: "muted" }, "Re-running the checks…");
  if (recheck.error) return h("p", { className: "decision-error" }, displayText(recheck.error));
  const receipts = (recheck.data && recheck.data.receipts) || [];
  if (!receipts.length) return h("p", { className: "muted" }, "Nothing behind this decision recomputes yet — its backing is cited, not reproducible.");
  return h(Block, { title: "Evidence recheck" },
    h("ul", { className: "decision-recheck" },
      receipts.map((r, i) => h("li", { key: (r.capability || "") + i },
        h(StatusLine, { tone: RECHECK_TONE[r.status] || "neutral" }, RECHECK_WORD[r.status] || r.status),
        (r.status === "earned" || r.status === "held") && TIER_WORD[r.warrant]
          ? h("span", { className: "muted" }, ` the ${TIER_WORD[r.warrant]} tier`) : null,
        r.detail || r.reason ? h("div", { className: "muted" }, displayText(r.detail || r.reason)) : null))));
}

export function DecisionPanel({ project, liveMode, decision, onRefresh, onOpenEvidence }) {
  const canRun = liveMode && !!project;
  const [recheck, setRecheck] = React.useState(null);
  const [attribution, setAttribution] = React.useState(null);

  React.useEffect(() => {
    if (!canRun) { setAttribution(null); return undefined; }
    let cancelled = false;
    fetch(`/api/scenario-attribution?project=${encodeURIComponent(project)}`, { headers: { Accept: "application/json" } })
      .then((res) => res.json())
      .then((json) => { if (!cancelled) setAttribution(json); })
      .catch((e) => { if (!cancelled) setAttribution({ ok: false, error: String(e) }); });
    return () => { cancelled = true; };
  }, [project, canRun]);

  const doRecheck = async () => {
    if (!canRun) return;
    setRecheck({ running: true });
    try {
      const res = await fetch("/api/scenario-recheck", { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project }) });
      setRecheck({ running: false, data: await res.json() });
      if (onRefresh) onRefresh();
    } catch (e) { setRecheck({ running: false, error: String(e) }); }
  };

  React.useEffect(() => { if (canRun && onRefresh) onRefresh(); }, [project, liveMode]);  // eslint-disable-line

  const result = (decision && decision.result) || null;
  const compiled = compiledDecisionState(decision);
  const strength = (result && result.strength) || {};
  const busy = decision && decision.running;
  const ready = Boolean(result && result.ok && governedMapReady(result));
  const hasMaterial = Boolean(result && result.ok && governedMapHasMaterial(result));
  const canRecheck = Boolean(
    Number((strength.profile || [])[1]) > 0
    || Number(((result && result.calibration) || {}).n_total) > 0
  );

  return h(Block, {
    title: ready ? "Evidence strength" : "Evidence readiness",
    className: "decision-block",
    lead: ready
      ? "How this decision holds up as evidence moves from unchecked to cited, reproducible, and proven."
      : hasMaterial
        ? "Source files are present, but this decision has no verified passage yet."
        : "Review the evidence workspace before relying on this decision.",
    actions: h("div", { className: "decision-actions" },
      h("button", { type: "button", className: "text-link",
        title: "Refresh this evidence read", disabled: !canRun || busy,
        onClick: () => onRefresh && onRefresh() }, "Refresh"),
      canRecheck ? h("button", { type: "button", className: `chip ${recheck && recheck.running ? "is-busy" : ""}`,
        disabled: !canRun || (recheck && recheck.running), onClick: doRecheck,
        title: "Re-run the checks behind this decision — watch the reproducible tier light up or go dark" },
        h(RotateCw, { size: 15, "aria-hidden": "true" }),
        recheck && recheck.running ? "Rechecking…" : "Re-run the checks") : null),
  },
    h(RecheckSection, { recheck }),
    !canRun ? h("p", { className: "muted" }, "Open a project first to read how its evidence supports the decision.") : null,
    decision && decision.error ? h("p", { className: "decision-error" }, displayText(decision.error)) : null,
    result && result.ok === false
      ? h("p", { className: "muted" }, displayText(result.error) || "Run this project first.")
      : null,

    (result && result.ok)
      ? (ready
          ? h(React.Fragment, null,
              h(StatusLine, { tone: STATUS_TONE[strength.status] || "neutral" }, STATUS_WORD[strength.status] || strength.status),
              h(ProfileBar, { profile: strength.profile }),
              h("p", { className: "decision-shape" }, shapeCaption(strength.profile)),
              compiled && compiled.next_test
                ? h(FactRow, {
                    label: compiled.next_test.flips_alone || Number(compiled.next_test.in_cores) > 0
                      ? "Next discriminating test"
                      : "Next test",
                  }, displayText(compiled.next_test.text))
                : null,
              calibrationLine(result.calibration),
              h(AttributionCard, { attribution }),
              h(RestsOn, { result }),
              h(FactRow, { label: "Independent backing" }, corroborationLine(result.corroboration)),
              h(CruxBlock, { crux: result.crux }),
              (result.trajectory_delta && result.trajectory_delta.length)
                ? h("p", { className: "muted" }, "Moved since last snapshot: Δ "
                    + result.trajectory_delta.map((d) => `${d >= 0 ? "+" : ""}${Number(d).toFixed(2)}`).join(" / "))
                : null)
          : h(EvidenceReadiness, {
              hasMaterial,
              corroboration: result.corroboration,
              nextTest: compiled && compiled.next_test,
              onReviewEvidence: () => onOpenEvidence && onOpenEvidence(),
            }))
      : null);
}

// Add evidence — the door that makes the graded lane real. Binds only if the excerpt appears verbatim
// (whitespace-normalized) in the pasted source; that verbatim gate is the whole feature (POST /api/
// scenario-bind, PRD "add a cited source to connect it"). A refusal here is the system doing its job,
// not an error — rendered calm, not red. Mounted only inside the modal shell (main.js "Add cited
// source" workspacePanels entry), same pattern as RegisterBetForm. Self-contained: owns its own fetch.
function bindResultView(result, targetLabel) {
  if (!result) return null;
  if (result.ok === false && result.refused) {
    return h("div", { className: "bind-evidence-gate" },
      h("strong", null, "That quote isn't in the source you pasted"),
      h("p", null, "Cite the exact words — a citation that's drifted from its source is refused, on purpose."));
  }
  if (result.ok === false) {
    return h("p", { className: "decision-error" }, displayText(result.error || "Could not add this evidence."));
  }
  const delta = result.decision_delta || {};
  const status = delta.status || { from: result.status_before, to: result.status_after,
    changed: result.status_before !== result.status_after };
  const trust = delta.trust_floor || {};
  const nextTest = delta.next_test || {};
  const moved = Boolean(delta.decision_changed);
  const bound = result.bound || {};
  const inferenceChecked = bound.inference_tier === "cited";
  return h("div", { className: "bind-evidence-ok" },
    h("p", { className: "register-bet-ok" }, inferenceChecked
      ? `The source contains this claim verbatim. Added as cited backing to ${displayText(targetLabel(bound.target))}.`
      : `The quote is authentic and now attached to ${displayText(targetLabel(bound.target))}.`),
    h("div", { className: "decision-delta", "aria-label": "Decision delta" },
      h("div", { className: "decision-delta-heading" },
        h("strong", null, status.changed ? "Decision changed" : "Decision held"),
        h("span", { className: "decision-delta-status" },
          h(StatusLine, { tone: STATUS_TONE[status.from] || "neutral" }, STATUS_WORD[status.from] || status.from),
          h("span", { "aria-hidden": "true" }, "→"),
          h(StatusLine, { tone: STATUS_TONE[status.to] || "neutral" }, STATUS_WORD[status.to] || status.to))),
      trust.changed
        ? h("p", null, `Trust floor: ${displayText(trust.from || "none")} → ${displayText(trust.to || "none")}`)
        : null,
      nextTest.changed
        ? h("div", { className: "decision-delta-tests" },
            nextTest.from && nextTest.from.text
              ? h("p", null, h("span", { className: "muted" }, "Previous next test: "), displayText(nextTest.from.text))
              : null,
            nextTest.to && nextTest.to.text
              ? h("p", null, h("span", { className: "muted" }, "Now test: "), displayText(nextTest.to.text))
              : null)
        : null),
    h("p", { className: "muted" }, inferenceChecked
      ? (moved ? "The cited tier strengthened." : "The citation is sound, but another unchecked link still caps the thesis.")
      : "Its relevance is still unchecked. The source is verified; the inference is not being silently upgraded."));
}

export function BindEvidenceForm({ project, liveMode, claims, sources, onBound, onPreview }) {
  const canRun = liveMode && !!project;
  const options = (claims && claims.length) ? claims : [{ id: "thesis", label: "The thesis" }];
  const sourceOptions = (sources || [])
    .filter((source) => source && source.source_type === "source_evidence" && source.relative_raw_path)
    .map((source) => ({ value: source.relative_raw_path, label: source.relative_raw_path,
      chars: Number(source.chars) || 0 }));
  const [sourcePath, setSourcePath] = React.useState(sourceOptions[0] ? sourceOptions[0].value : "");
  const [excerpt, setExcerpt] = React.useState("");
  const [target, setTarget] = React.useState(options[0].id);
  const [busy, setBusy] = React.useState(false);
  const [result, setResult] = React.useState(null);
  const [sourceDocument, setSourceDocument] = React.useState({ loading: false, text: "", error: "" });
  const readerRef = React.useRef(null);
  React.useEffect(() => {
    if (!sourcePath && sourceOptions.length) setSourcePath(sourceOptions[0].value);
  }, [sourcePath, sourceOptions.length]);
  React.useEffect(() => {
    if (!canRun || !sourcePath) {
      setSourceDocument({ loading: false, text: "", error: "" });
      return undefined;
    }
    let cancelled = false;
    setSourceDocument({ loading: true, text: "", error: "" });
    fetch(`/api/file?path=${encodeURIComponent(sourcePath)}`, { headers: { Accept: "application/json" } })
      .then((response) => response.json())
      .then((payload) => {
        if (cancelled) return;
        if (payload && payload.ok === false) throw new Error(payload.error || "Source could not be opened");
        setSourceDocument({ loading: false, text: String((payload && payload.text) || ""), error: "" });
      })
      .catch((error) => {
        if (!cancelled) setSourceDocument({ loading: false, text: "", error: String(error.message || error) });
      });
    return () => { cancelled = true; };
  }, [canRun, sourcePath]);

  const ready = Boolean(canRun && sourcePath && excerpt.trim() && target);
  const targetLabel = (id) => (options.find((c) => c.id === id) || {}).label || id;
  const captureSelection = () => {
    const selection = window.getSelection && window.getSelection();
    const text = selection ? String(selection.toString() || "").trim() : "";
    const reader = readerRef.current;
    if (!text || !reader || !selection || !selection.anchorNode || !reader.contains(selection.anchorNode)) return;
    setExcerpt(text);
    setResult(null);
  };

  const submit = async () => {
    if (!ready) return;
    setBusy(true);
    setResult(null);
    try {
      const res = await fetch("/api/scenario-bind", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project, source_path: sourcePath, excerpt: excerpt.trim(), target }),
      });
      const data = await res.json();
      setResult(data);
      if (data && data.ok && onBound) onBound(data);
    } catch (e) { setResult({ ok: false, error: String(e) }); }
    setBusy(false);
  };

  return h("div", { className: "bind-evidence-form", "aria-label": "Verify claim support" },
    !canRun ? h("p", { className: "muted" }, "Open a project first.") : null,
    !(claims && claims.length)
      ? h("p", { className: "muted" }, "The full claim list isn't reachable here — binding to the thesis.")
      : null,

    h("label", { className: "form-label" }, "1. Choose a source"),
    sourceOptions.length
      ? h("div", { className: "bind-evidence-source" },
          h("select", { value: sourcePath, disabled: !canRun, className: "form-input",
            onChange: (e) => { setSourcePath(e.target.value); setExcerpt(""); setResult(null); } },
            sourceOptions.map((source) => h("option", { key: source.value, value: source.value }, source.label))),
          onPreview ? h("button", { type: "button", className: "chip ghost", disabled: !sourcePath,
            onClick: () => onPreview({ type: "file", value: sourcePath }) }, "Open source") : null)
      : h("p", { className: "muted" }, "No source files are ready to use as evidence yet."),

    h("label", { className: "form-label" }, "2. Highlight the passage that carries the claim"),
    h("p", { className: "bind-evidence-guide" },
      "Select the exact words in the source below. This proves what the source says; the next step checks which claim those words can support."),
    sourceDocument.loading
      ? h("div", { className: "bind-evidence-reader is-loading" }, "Loading source…")
      : sourceDocument.error
        ? h("p", { className: "decision-error" }, displayText(sourceDocument.error))
        : sourceDocument.text
          ? h("pre", { ref: readerRef, className: "bind-evidence-reader", tabIndex: 0,
              onMouseUp: captureSelection, onKeyUp: captureSelection }, sourceDocument.text)
          : null,
    excerpt
      ? h("div", { className: "bind-evidence-selection" },
          h("span", null, "Selected passage"),
          h("blockquote", null, excerpt))
      : sourceDocument.text
        ? h("p", { className: "bind-evidence-empty-selection" }, "No passage selected yet.")
        : null,
    h("details", { className: "bind-evidence-manual" },
      h("summary", null, "Paste a passage instead"),
      h("textarea", { value: excerpt, disabled: !canRun || !sourceOptions.length,
        className: "form-input bind-evidence-textarea", rows: 4,
        placeholder: "Paste exact words from the selected source.",
        onChange: (e) => { setExcerpt(e.target.value); setResult(null); } })),

    h("label", { className: "form-label" }, "3. Choose the claim it supports"),
    h("select", { value: target, disabled: !canRun, className: "form-input",
      onChange: (e) => { setTarget(e.target.value); setResult(null); } },
      options.map((c) => h("option", { key: c.id, value: c.id }, displayText(c.label).slice(0, 90)))),

    h("button", { type: "button", className: `chip primary ${busy ? "is-busy" : ""}`,
      disabled: !ready || busy, onClick: submit }, busy ? "Verifying…" : "Verify claim support"),

    bindResultView(result, targetLabel));
}
