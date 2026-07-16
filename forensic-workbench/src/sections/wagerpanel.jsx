import React from "react";
import { CalendarClock, Plus, RefreshCw, X } from "lucide-react";
import { ActionButton, displayText, Block, Tag, EmptyState, IconButton, StatusLine } from "../design-system.js";

const h = React.createElement;

// Decision tests are the "what would settle it" worklist on Open points (PRD §4.2a). WagerPanel renders the
// unified agenda (`/api/scenario-next-agenda` = implicit assumptions + declared tests + loop-proposed
// discriminators, one admission gate, Pareto frontier). The stable kernel type is still `wager`, but it is not
// the operator's concept. Defining a test is modal-only so the worklist remains a worklist, not a second editor.

const SOURCE_LABEL = { implicit: "untested assumption", declared: "your test", "loop-proposed": "loop-suggested test" };
const SOURCE_TONE = { implicit: "neutral", declared: "accent", "loop-proposed": "neutral" };

// Resolve the operator action for a decision-state `next_test` or selected map claim. Home, Map, and
// Open points must agree about whether this test still needs defining or has an outcome ready to record.
export function decisionTestContext(agenda, wagers, claimRef) {
  const rows = (agenda && agenda.result && agenda.result.agenda) || [];
  const wagerRows = (wagers && wagers.result && wagers.result.wagers) || [];
  const row = rows.find((candidate) => candidate && candidate.claim_ref === claimRef) || null;
  const wager = row ? wagerRows.find((candidate) => candidate && candidate.id === row.id) || null : null;
  const mode = row && row.source === "declared" && wager && wager.lifecycle === "open"
    ? "record"
    : row && row.source !== "declared"
      ? "define"
      : row ? "review" : "none";
  return { row, wager, mode };
}

function slug(s) {
  return String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 40);
}

// Decision-language rows -> the kernel's typed outcome->edit contract. A result that "supports" the claim binds
// a (hypothetical) evidence node SUPPORTING it; "contradicts" binds one CONTRADICTING it. The kernel recompiles
// each and reports whether it flips the decision.
function assembleWager(claimId, test, rows, cost, deadline, exhaustive, stakes) {
  const seen = {};
  const outcomes = rows.filter((r) => (r.label || "").trim()).map((row, i) => {
    let oid = slug(row.label) || ("o" + i);
    while (seen[oid]) oid = oid + "_" + i;
    seen[oid] = 1;
    if (row.consequence === "inconclusive") return { id: oid, label: row.label.trim(), edits: [] };
    const evId = oid + "_ev";
    const edits = [{ op: "add_evidence", target: evId, text: row.label }];
    if (row.consequence === "support") edits.push({ op: "support", source: evId, target: claimId, warrant: row.warrant });
    else edits.push({ op: "attack", source: evId, target: claimId, relation: "CONTRADICTS", warrant: row.warrant });
    return { id: oid, label: row.label.trim(), edits };
  });
  const declaredCost = String(cost || "").trim() ? Math.max(0, Number(cost) || 0) : -1;
  return { id: slug(test) || "bet", claim_ref: claimId, test: test, declared_cost: declaredCost,
    deadline: deadline, exhaustive: exhaustive, stakes: stakes, outcomes: outcomes };
}

function agendaRow(r, { wager, onPrefill, onExecute } = {}) {
  const costText = r.cost == null ? "cost not declared" : `cost ${r.cost}`;
  const deadlineText = wager && wager.deadline ? ` · by ${wager.deadline}` : "";
  // The kernel ranks every row by expected information gain (in Shannon bits) — real, computed, but the
  // raw unit is jargon to a lay reader. Keep the number honest by putting it in a tooltip; the visible
  // copy uses the same kernel-computed rank instead (equally real, more legible: "best of N" vs "0.34 bits").
  const bitsTitle = `Expected information gain if this test runs: ${(Number(r.bits) || 0).toFixed(2)} bits (Shannon information)`;
  const declaredOpen = r.source === "declared" && wager && wager.lifecycle === "open";
  const implicit = r.source === "implicit";
  const primaryText = implicit && r.claim_text ? r.claim_text : r.test;
  const contextText = implicit ? "Gather evidence" : r.claim_text ? `Decision under test: ${displayText(r.claim_text)}` : "";
  return h("li", { key: r.id, className: "agenda-row" },
    h("div", { className: "agenda-row-head" },
      h(Tag, { tone: SOURCE_TONE[r.source] || "neutral" }, SOURCE_LABEL[r.source] || r.source),
      r.on_frontier ? h(Tag, { tone: "ok" }, "best tradeoff") : null,
      r.flips_crisp ? h(Tag, { tone: "warn" }, "could flip the verdict") : null,
      r.status_change && !r.flips_crisp ? h(Tag, { tone: "warn" }, "changes the standing") : null),
    h("p", { className: "agenda-row-test" }, displayText(primaryText)),
    contextText ? h("p", { className: "agenda-row-claim" }, displayText(contextText)) : null,
    Array.isArray(r.outcome_specs) && r.outcome_specs.length
      ? h("details", { className: "agenda-row-outcome-disclosure" },
          h("summary", null, `${r.outcome_specs.length} possible result${r.outcome_specs.length === 1 ? "" : "s"}`),
          h("ul", { className: "agenda-row-outcomes", "aria-label": "Possible results" },
            r.outcome_specs.slice(0, 4).map((outcome) => h("li", { key: outcome.id || outcome.label },
              h("span", null, displayText(outcome.label || outcome.id)),
              h("small", null, outcome.consequence === "contradict" ? "would weaken it" : outcome.consequence === "support" ? "would strengthen it" : "would leave it open")))
              .concat(r.outcome_specs.length > 4
                ? [h("li", { className: "muted", key: "more-outcomes" }, `+${r.outcome_specs.length - 4} more possible result${r.outcome_specs.length - 4 === 1 ? "" : "s"}`)]
                : [])))
      : null,
    h("div", { className: "agenda-row-foot" },
      h("p", { className: "agenda-row-meta", title: bitsTitle },
        `Ranked #${r.rank || "—"} for settling this · ${costText}${deadlineText}`),
      declaredOpen
        ? h(ActionButton, { onClick: () => onExecute && onExecute(wager) }, "Record outcome")
        : r.source !== "declared"
          ? h(ActionButton, { onClick: () => onPrefill && onPrefill(r) }, "Define this test")
          : null));
}

// Defining a decision test is a modal (PRD §4.2a), never an inline form on the worklist.
export function RegisterBetForm({ project, liveMode, wagers, onRefresh, onRegister, onAgendaRefresh, prefill }) {
  const canRun = liveMode && !!project;
  const [claimId, setClaimId] = React.useState("");
  const [test, setTest] = React.useState("");
  const [rows, setRows] = React.useState([
    { label: "", consequence: "support", warrant: "W3" },
    { label: "", consequence: "contradict", warrant: "W3" },
  ]);
  const [cost, setCost] = React.useState("");
  const [deadline, setDeadline] = React.useState("");
  const [stakes, setStakes] = React.useState("");
  const [exhaustive, setExhaustive] = React.useState(false);
  const [receipt, setReceipt] = React.useState(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => { if (canRun && !wagers && onRefresh) onRefresh(); }, [project, liveMode]);  // eslint-disable-line
  React.useEffect(() => {
    if (!prefill) {
      setClaimId("");
      setTest("");
      setRows([
        { label: "", consequence: "support", warrant: "W3" },
        { label: "", consequence: "contradict", warrant: "W3" },
      ]);
      setCost("");
      setDeadline("");
      setStakes("");
      setExhaustive(false);
      setReceipt(null);
      return;
    }
    setClaimId(String(prefill.claim_ref || ""));
    setTest(String(prefill.test || ""));
    if (Array.isArray(prefill.outcomes) && prefill.outcomes.length) {
      setRows(prefill.outcomes.map((outcome) => ({
        label: String(outcome.label || ""),
        consequence: String(outcome.consequence || "inconclusive"),
        warrant: String(outcome.warrant || "W3"),
      })));
      setExhaustive(true);
    }
    setReceipt(null);
  }, [prefill && prefill.key]);

  const data = (wagers && wagers.result) || null;
  const blocked = (data && data.blocked_claims) || [];
  const filledOutcomeCount = rows.filter((row) => row.label.trim()).length;
  const setRow = (i, patch) => setRows(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  const submit = () => {
    if (!canRun || !claimId || !test.trim() || !exhaustive || filledOutcomeCount < 2) return;
    setBusy(true);
    Promise.resolve(onRegister && onRegister(assembleWager(claimId, test, rows, cost, deadline, exhaustive, stakes)))
      .then((res) => { setReceipt(res); setBusy(false); if (res && res.registered && onAgendaRefresh) onAgendaRefresh(); });
  };

  const badEdit = receipt && receipt.receipt && (receipt.receipt.outcomes || []).find((o) => o.edits_valid === false);
  const registeredOutcomes = receipt && receipt.receipt && Array.isArray(receipt.receipt.outcomes)
    ? receipt.receipt.outcomes.filter((outcome) => outcome && outcome.edits_valid)
    : [];

  return h("div", { className: "register-bet-form", "aria-label": "Define a decision test" },
    !canRun ? h("p", { className: "muted" }, "Open a project first.") : null,
    h("p", { className: "register-bet-guide" }, "Define one test you are willing to be wrong about. The workbench simulates every result first and only admits it if at least one result would change the decision."),

    h("label", { className: "form-label" }, "Decision under test"),
    h("select", { value: claimId, disabled: !canRun, className: "form-input",
      onChange: (e) => setClaimId(e.target.value) },
      h("option", { value: "" }, blocked.length ? "— pick a claim —" : "no blocked claims on this map"),
      blocked.map((c) => h("option", { key: c.id, value: c.id }, displayText(c.text).slice(0, 90)))),

    h("label", { className: "form-label" }, "Test or observation"),
    h("input", { type: "text", value: test, disabled: !canRun, className: "form-input",
      placeholder: "e.g. run the metered-vs-billed audit", onChange: (e) => setTest(e.target.value) }),

    h("div", { className: "form-label" }, "What could you observe?"),
    h("p", { className: "muted register-bet-help" }, "Name each observable result, then say whether it would strengthen, weaken, or leave the decision open."),
    rows.map((row, i) => h("div", { key: i, className: "register-bet-row" },
      h("input", { type: "text", value: row.label, disabled: !canRun, className: "form-input",
        placeholder: `result ${i + 1} (e.g. "material gap found")`, onChange: (e) => setRow(i, { label: e.target.value }) }),
      h("select", { value: row.consequence, disabled: !canRun, className: "form-input",
        onChange: (e) => setRow(i, { consequence: e.target.value }) },
        h("option", { value: "support" }, "would support the claim"),
        h("option", { value: "contradict" }, "would contradict the claim"),
        h("option", { value: "inconclusive" }, "would leave the decision open")),
      h("select", { value: row.warrant, disabled: !canRun, className: "form-input", title: "How checkable this result would be",
        onChange: (e) => setRow(i, { warrant: e.target.value }) },
        [{ v: "W3", label: "unchecked (a stated result)" }, { v: "W2", label: "cited (a source says so)" },
          { v: "W1", label: "reproducible (recomputes from data)" }].map((w) => h("option", { key: w.v, value: w.v }, w.label))),
      rows.length > 2 ? h(IconButton, { label: `Remove result ${i + 1}`, disabled: !canRun,
        onClick: () => setRows(rows.filter((_, j) => j !== i)) },
        h(X, { size: 16, "aria-hidden": true })) : null)),
    h(ActionButton, { variant: "quiet", className: "register-bet-add",
      icon: h(Plus, { size: 16, "aria-hidden": true }), disabled: !canRun,
      onClick: () => setRows([...rows, { label: "", consequence: "support", warrant: "W3" }]) }, "Another result"),

    h("div", { className: "register-bet-inline" },
      h("label", { className: "form-label-inline" }, "Effort / cost ",
        h("input", { type: "number", min: 0, value: cost, disabled: !canRun, className: "form-input-inline",
          onChange: (e) => setCost(e.target.value) })),
      h("label", { className: "form-label-inline" }, "Target date ",
        h("input", { type: "date", value: deadline, disabled: !canRun, className: "form-input-inline",
          onChange: (e) => setDeadline(e.target.value) }))),
    h("label", { className: "form-label" }, "Why this test matters (optional)"),
    h("input", { type: "text", value: stakes, disabled: !canRun, className: "form-input",
      "aria-label": "Why this test matters (optional)", placeholder: "e.g. decides whether to ship", onChange: (e) => setStakes(e.target.value) }),

    h("label", { className: "register-bet-check" },
      h("input", { type: "checkbox", checked: exhaustive, disabled: !canRun,
        onChange: (e) => setExhaustive(e.target.checked) }),
      "I have listed the plausible outcomes"),
    filledOutcomeCount < 2
      ? h("p", { className: "muted register-bet-help" }, "Add at least two plausible results; include an inconclusive result when the test could fail to resolve the question.")
      : null,

    h(ActionButton, { variant: "primary", busy, className: "register-bet-submit",
      disabled: !canRun || busy || !claimId || !test.trim() || !exhaustive || filledOutcomeCount < 2,
      onClick: submit }, busy ? "Checking…" : "Check & register test"),

    receipt
      ? (receipt.ok === false
          ? h("p", { className: "decision-error" }, displayText(receipt.error || "register failed"))
          : receipt.registered
            ? h("div", { className: "register-bet-ok" },
                h("strong", null, "Registered — this test now ranks in the worklist."),
                h("p", { title: `Information yield: ${(Number((receipt.receipt || {}).identification_bits) || 0).toFixed(2)} Shannon bits` },
                  "Each declared result was checked against the current decision before the test was admitted."),
                registeredOutcomes.length
                  ? h("ul", { className: "register-bet-outcome-preview", "aria-label": "Accepted possible outcomes" },
                      registeredOutcomes.map((outcome) => h("li", { key: outcome.id || outcome.label },
                        h("span", null, displayText(outcome.label || outcome.id || "Observed result")),
                        h("small", null, outcome.flips
                          ? `would change the decision to ${displayText(outcome.verdict || "a new standing")}`
                          : `would leave it ${displayText(outcome.verdict || "open")}`))))
                  : null,
                h("p", { className: "register-bet-help" }, "When you observe a result, preview it before recording it. The preview does not change the project."))
            : h("div", { className: "register-bet-rejected" },
                h("p", null, "Not admitted — " + displayText((receipt.receipt || {}).reason || "")),
                badEdit ? h("p", { className: "muted" }, `A result names something the graph doesn't have: ${displayText(badEdit.error || "")}`) : null,
                h("p", { className: "muted" },
                  "A decision test only counts if a declared result would actually change the decision. Adjust the results so at "
                  + "least one supports or contradicts the claim in a way that moves it.")))
      : null);
}

const DECISION_TONE = { SUPPORTED: "ok", BLOCKED: "warn", REFUTED: "danger" };
const DECISION_WORD = { SUPPORTED: "Supported", BLOCKED: "Not ready", REFUTED: "Refuted" };

function OutcomeDelta({ payload, preview = false }) {
  const delta = (payload && payload.decision_delta) || {};
  const status = delta.status || {};
  const nextTest = delta.next_test || {};
  if (!payload) return null;
  return h("div", { className: "wager-outcome-preview" },
    h("div", { className: "decision-delta-heading" },
      h("strong", null, preview
        ? (delta.decision_changed ? "If this result is recorded, the decision changes" : "If this result is recorded, the decision holds")
        : (delta.decision_changed ? "Decision changed" : "Decision held")),
      h("span", { className: "decision-delta-status" },
        h(StatusLine, { tone: DECISION_TONE[status.from] || "neutral" }, DECISION_WORD[status.from] || status.from || "Unknown"),
        h("span", { "aria-hidden": "true" }, "→"),
        h(StatusLine, { tone: DECISION_TONE[status.to] || "neutral" }, DECISION_WORD[status.to] || status.to || "Unknown"))),
    delta.summary ? h("p", null, displayText(delta.summary)) : null,
    nextTest.changed && nextTest.to && nextTest.to.text
      ? h("p", null, h("span", { className: "muted" }, "Next test becomes: "), displayText(nextTest.to.text))
      : null,
    h("p", { className: "wager-write-boundary" },
      preview
        ? `This preview writes nothing. Recording this result would add ${(payload.applied || {}).evidence || 0} evidence item(s) and ${(payload.applied || {}).edges || 0} relation(s).`
        : `Recorded ${(payload.applied || {}).evidence || 0} evidence item(s) and ${(payload.applied || {}).edges || 0} relation(s).`));
}

export function ExecuteWagerForm({ project, liveMode, wager, onPreview, onExecute }) {
  const [outcomeId, setOutcomeId] = React.useState("");
  const [preview, setPreview] = React.useState(null);
  const [result, setResult] = React.useState(null);
  const [busy, setBusy] = React.useState(false);
  const outcomes = (wager && wager.outcomes) || [];
  const canRun = Boolean(liveMode && project && wager && wager.lifecycle === "open");

  React.useEffect(() => {
    setOutcomeId("");
    setPreview(null);
    setResult(null);
    setBusy(false);
  }, [wager && wager.id]);

  const previewOutcome = async () => {
    if (!canRun || !outcomeId || !onPreview) return;
    setBusy(true);
    const response = await Promise.resolve(onPreview(wager.id, outcomeId));
    setPreview(response);
    setResult(null);
    setBusy(false);
  };
  const executeOutcome = async () => {
    if (!canRun || !outcomeId || !preview || !onExecute) return;
    setBusy(true);
    const response = await Promise.resolve(onExecute(wager.id, outcomeId));
    setResult(response);
    setBusy(false);
  };

  return h("section", { className: "wager-execute", "aria-label": "Record the test outcome" },
    wager
      ? h("div", { className: "wager-execute-context" },
          h("span", { className: "eyebrow" }, "Registered test"),
          h("h3", null, displayText(wager.test)),
          wager.claim_text ? h("p", null, displayText(wager.claim_text)) : null)
      : h(EmptyState, { text: "Choose a registered decision test from Open points first." }),
    wager && outcomes.length
      ? h("fieldset", { className: "wager-outcome-list", disabled: busy || Boolean(result && result.ok) },
          h("legend", null, "What did you observe?"),
          outcomes.map((outcome) =>
            h("label", { key: outcome.id, className: outcomeId === outcome.id ? "is-selected" : "" },
              h("input", { type: "radio", name: "wager-outcome", value: outcome.id, checked: outcomeId === outcome.id,
                onChange: () => { setOutcomeId(outcome.id); setPreview(null); setResult(null); } }),
              h("span", null,
                h("strong", null, displayText(outcome.label || outcome.id)),
                h("small", null, outcome.flips ? "Would change the compiled decision" : `Would leave it ${displayText(outcome.verdict || "unchanged")}`)))))
      : null,
    preview && preview.ok ? h(OutcomeDelta, { payload: preview, preview: true }) : null,
    preview && preview.ok === false ? h("p", { className: "decision-error" }, displayText(preview.error)) : null,
    result && result.ok
      ? h("div", { className: "wager-executed" },
          h(StatusLine, { tone: "ok" }, "Outcome recorded"),
          h(OutcomeDelta, { payload: result }))
      : result && result.ok === false
        ? h("p", { className: "decision-error" }, displayText(result.error))
        : null,
    wager
      ? h("div", { className: "wager-execute-actions" },
          !preview
            ? h(ActionButton, { variant: "primary", busy,
                disabled: !canRun || !outcomeId || busy, onClick: previewOutcome }, busy ? "Previewing" : "Preview this outcome")
            : !result
              ? h(ActionButton, { variant: "primary", busy,
                  disabled: !canRun || busy, onClick: executeOutcome }, busy ? "Recording" : "Record this observed outcome")
              : null)
      : null);
}

export function WagerPanel({ project, liveMode, agenda, onAgendaRefresh, onOpenModal, wagers, onWagersRefresh, onExpire, onPrefill, onNew, onExecute }) {
  const canRun = liveMode && !!project;
  const [expiring, setExpiring] = React.useState(false);

  React.useEffect(() => { if (canRun && onAgendaRefresh) onAgendaRefresh(); }, [project, liveMode]);  // eslint-disable-line
  React.useEffect(() => { if (canRun && onWagersRefresh) onWagersRefresh(); }, [project, liveMode]);  // eslint-disable-line

  const data = (agenda && agenda.result) || null;
  const rows = (data && data.agenda) || [];
  const busy = agenda && agenda.running;
  const inadmissible = ((wagers && wagers.result && wagers.result.inadmissible) || []);
  const wagerById = Object.fromEntries((((wagers && wagers.result && wagers.result.wagers) || [])).map((row) => [row.id, row]));

  const runExpire = async () => {
    if (!canRun || !onExpire) return;
    setExpiring(true);
    await Promise.resolve(onExpire());
    if (onAgendaRefresh) onAgendaRefresh();
    setExpiring(false);
  };
  const openNewTest = () => {
    if (onNew) onNew();
    if (onOpenModal) onOpenModal("review", "Define a decision test");
  };

  return h(Block, {
    title: "What would settle it",
    lead: "Choose one uncertainty, define what you would observe, and see which result would change the standing.",
    actions: h("div", { className: "decision-actions" },
      h(IconButton, { label: "Refresh decision tests", busy,
        disabled: !canRun || busy, onClick: () => onAgendaRefresh && onAgendaRefresh() },
        h(RefreshCw, { size: 16, "aria-hidden": true })),
      h(ActionButton, { variant: "primary", icon: h(Plus, { size: 16, "aria-hidden": true }),
        disabled: !canRun, onClick: openNewTest }, "Define a test"),
      onExpire
        ? h(ActionButton, { icon: h(CalendarClock, { size: 16, "aria-hidden": true }), disabled: !canRun || expiring,
            title: "Tests past their deadline return to the ordinary open-points backlog",
            onClick: runExpire }, expiring ? "Sweeping…" : "Sweep past-due tests")
        : null),
  },
    !canRun ? h("p", { className: "muted" }, "Open a project first (tests use its current decision state).") : null,
    agenda && agenda.error ? h("p", { className: "decision-error" }, displayText(agenda.error)) : null,
    data && data.ok === false ? h("p", { className: "muted" }, displayText(data.error) || "Run this project first.") : null,

    !data && !busy && !(agenda && agenda.error)
      ? h("p", { className: "muted" }, "Finding the next test that could change the decision…")
      : null,

    (data && rows.length)
      ? h("ol", { className: "agenda-list" }, rows.map((row) => agendaRow(row, {
          wager: wagerById[row.id], onPrefill, onExecute,
        })))
      : (data
          ? h(EmptyState, {
              text: "Nothing is admitted yet. Define a test that could change the standing.",
              action: h(ActionButton, { variant: "primary", icon: h(Plus, { size: 16, "aria-hidden": true }),
                disabled: !canRun, onClick: openNewTest }, "Define a test"),
            })
          : null),

    inadmissible.length
      ? h("details", { className: "agenda-inadmissible" },
              h("summary", null, `${inadmissible.length} test${inadmissible.length === 1 ? "" : "s"} not admitted`),
          inadmissible.map((x, i) => h("p", { key: i, className: "muted" }, `${x.id} — ${displayText(x.reason)}`)))
      : null);
}
