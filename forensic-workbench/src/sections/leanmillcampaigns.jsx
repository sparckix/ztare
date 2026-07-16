import React from "react";
import { X } from "lucide-react";
import { displayText, Block, FactRow, Tag, StatusLine, EmptyState } from "../design-system.js";
import { ModalPortal, useModalBehavior } from "../modal-behavior.js";
import { campaignIsLive } from "../campaign-status.js";

const h = React.createElement;

// Axiom discovery — AxiomPack explore_axiom_space lifecycle (GP-251 §11/§12/§20 M6) projected into the Workbench. THIN
// PROJECTION ONLY: every fact here is read straight off the existing `frontier_campaign_status` /
// `inspect_frontier_campaign` / journal read-models, and every button calls the existing action
// functions or shells the existing `ztare leanmill` CLI. This component owns no campaign state of its
// own — only UI state (which row is selected, which form fields are being typed). Self-contained, like
// RicePanel/DeliverablesPanel: it fetches its own data and re-fetches after any action.

const STATUS_WORDS = {
  missing: "not started",
  retired: "retired",
  frontier_no_candidate: "no candidate found",
  frontier_candidates_frozen_awaiting_boundary_approval: "awaiting boundary approval",
  boundary_complete: "boundary complete",
  adapter_forge_complete: "building an adapter",
  budget_stopped: "stopped — out of budget",
  blocked_adapter_gap: "blocked — missing adapter",
  legacy_warm_route_required: "needs a warm route",
  unreadable: "can't read this attempt",
};

function statusWord(status) {
  const s = String(status || "missing");
  return STATUS_WORDS[s] || displayText(s);
}

function statusTone(status) {
  const s = String(status || "").toLowerCase();
  if (s === "retired" || s === "missing") return "neutral";
  if (s.includes("unreadable") || s.includes("blocked") || s.includes("refute")) return "danger";
  if (s.includes("stopped") || s.includes("gap")) return "warn";
  if (s.includes("complete") || s.includes("frozen") || s.includes("verified")) return "ok";
  return "warn"; // actively navigating
}

function shortId(dir) {
  const name = String(dir || "").split("/").filter(Boolean).pop() || "";
  return name.replace(/^attempt-/, "").slice(0, 12) || "campaign";
}

function elapsedText(ms) {
  const total = Math.round((Number(ms) || 0) / 1000);
  if (total < 60) return `${total}s`;
  const minutes = Math.floor(total / 60);
  if (minutes < 60) return `${minutes}m ${total % 60}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

function epochAgeText(value) {
  const epoch = Number(value);
  if (!Number.isFinite(epoch) || epoch <= 0) return "—";
  const age = Math.max(0, Math.round(Date.now() / 1000 - epoch));
  if (age < 60) return `${Math.max(1, age)}s ago`;
  if (age < 3600) return `${Math.floor(age / 60)}m ago`;
  return `${Math.floor(age / 3600)}h ago`;
}

function campaignPhase(status) {
  const lease = (status && status.attempt_lease) || {};
  const run = (status && status.run) || {};
  const state = String((status && status.status) || run.status || "");
  const action = String(lease.action || "");
  if (action.includes("boundary") || state.includes("boundary")) return "Checking the boundary";
  if (action.includes("forge") || state.includes("adapter")) return "Building the adapter gap";
  if (action.includes("interpret")) return "Interpreting the frozen frontier";
  if (action.includes("resume") || action.includes("recover")) return "Resuming navigation";
  if (run.status === "running" || lease.active) return "Exploring candidate theories";
  if (state.includes("frozen")) return "Awaiting boundary approval";
  return statusWord(state);
}

function CampaignProgress({ status, budget, caps }) {
  if (!status || !campaignIsLive(status)) return null;
  const run = status.run || {};
  const lease = status.attempt_lease || {};
  const elapsed = Number((budget || {}).elapsed_ms) || 0;
  const wallClock = Number(caps && caps.wall_clock_s) * 1000;
  const determinate = wallClock > 0;
  const percent = determinate ? Math.min(100, Math.round((elapsed / wallClock) * 100)) : 38;
  const heartbeat = lease.heartbeat_at || lease.queue_updated_at;
  const heartbeatFresh = lease.active && heartbeat && (Date.now() / 1000 - Number(heartbeat)) < 180;
  const statusToneName = lease.active ? "accent" : "warn";
  return h(
    "div",
    { className: `campaign-progress ${lease.active ? "is-live" : "is-unconfirmed"}`, "aria-live": "polite" },
    h(
      "div",
      { className: "campaign-progress-head" },
      h(
        "div",
        { className: "campaign-progress-title" },
        h("span", { className: "runconsole-spinner", "aria-hidden": "true" }),
        h("div", null,
          h("span", { className: "eyebrow" }, "Live campaign"),
          h("strong", null, campaignPhase(status)),
          h("small", null, run.provider_calls !== undefined
            ? `${run.provider_calls} provider call${run.provider_calls === 1 ? "" : "s"} · ${run.finalist_count || 0} finalist${run.finalist_count === 1 ? "" : "s"}`
            : "The campaign state is being updated from its attempt ledger."))),
      h(Tag, { tone: statusToneName }, lease.active ? "running" : "needs attention")
    ),
    h("div", { className: `campaign-progress-track ${determinate ? "" : "is-indeterminate"}`, role: "progressbar", "aria-valuemin": 0, "aria-valuemax": determinate ? wallClock : undefined, "aria-valuenow": determinate ? elapsed : undefined, "aria-label": determinate ? `${elapsedText(elapsed)} of ${elapsedText(wallClock)}` : "Campaign progress" },
      h("div", { className: "campaign-progress-fill", style: { width: `${percent}%` } })),
    h("div", { className: "campaign-progress-meta" },
      h("span", null, determinate ? `${elapsedText(elapsed)} of ${elapsedText(wallClock)}` : "Budget ledger is live"),
      h("span", null, heartbeat ? `last heartbeat ${epochAgeText(heartbeat)}` : "waiting for heartbeat")),
    h("p", { className: `campaign-progress-note ${heartbeatFresh ? "" : "warn"}` }, heartbeatFresh
      ? "You can leave this page. The attempt folder and journal are durable."
      : "The attempt still reports work, but its heartbeat is not fresh. Keep this view open while the next receipt lands.")
  );
}

function formatFactValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

// A plain object -> one FactRow per key. The generic renderer for "usage" / raw-JSON action results, so
// every resource kind (§13.2's hard-cap list) shows up without hardcoding each one by name.
function objectFactRows(obj) {
  if (!obj || typeof obj !== "object") return null;
  const keys = Object.keys(obj).filter((k) => formatFactValue(obj[k]) !== "—");
  if (!keys.length) return null;
  return keys.map((key) => h(FactRow, { key, label: displayText(key) }, formatFactValue(obj[key])));
}

function Meter({ value, total }) {
  const pct = total > 0 ? Math.min(100, Math.round((value / total) * 100)) : 0;
  return h(
    "div",
    { className: "meter", role: "img", "aria-label": `${value} of ${total}` },
    h("div", { className: "meter-fill", style: { width: `${pct}%` } })
  );
}

export function LeanMillCampaignsPanel({ liveMode }) {
  const [list, setList] = React.useState(null);
  const [selected, setSelected] = React.useState("");
  const [detail, setDetail] = React.useState(null);
  const [busy, setBusy] = React.useState("");
  const [actionResult, setActionResult] = React.useState(null);
  const [preflightBlueprint, setPreflightBlueprint] = React.useState("");
  const [preflightResult, setPreflightResult] = React.useState(null);
  const [runBlueprint, setRunBlueprint] = React.useState("");
  const [runResult, setRunResult] = React.useState(null);
  const [authorityRef, setAuthorityRef] = React.useState("");
  const [retireReason, setRetireReason] = React.useState("");
  const [leanRoot, setLeanRoot] = React.useState("");
  const [blueprints, setBlueprints] = React.useState(null);
  const [blueprintName, setBlueprintName] = React.useState("");
  const [blueprintText, setBlueprintText] = React.useState("");
  const [blueprintSaveResult, setBlueprintSaveResult] = React.useState(null);
  // NL-first authoring: describe a direction, AxiomPack's own frontier compiler + independent reviewer
  // (explore_axiom_space's compile step, via `ztare leanmill draft`) turns it into a structure_first
  // blueprint + typed_blueprint.json. The result opens in editorModal below for inspect/edit/Preflight/Run.
  const [draftDirection, setDraftDirection] = React.useState("");
  const [draftName, setDraftName] = React.useState("");
  const [draftStatus, setDraftStatus] = React.useState(null);
  const [draftModalOpen, setDraftModalOpen] = React.useState(false);
  const draftCloseRef = React.useRef(null);
  const closeDraftModal = React.useCallback(() => {
    if (!busy) setDraftModalOpen(false);
  }, [busy]);
  const draftDialogRef = useModalBehavior({
    open: draftModalOpen,
    onClose: closeDraftModal,
    initialFocusRef: draftCloseRef,
  });

  const loadList = React.useCallback(async ({ silent = false } = {}) => {
    if (!liveMode) return;
    if (!silent) setList((prev) => ({ data: prev && prev.data, running: true }));
    try {
      const res = await fetch("/api/leanmill/campaigns", { headers: { Accept: "application/json" } });
      setList({ running: false, data: await res.json() });
    } catch (e) {
      setList({ running: false, error: String(e) });
    }
  }, [liveMode]);

  const loadDetail = React.useCallback(
    async (dir, { silent = false } = {}) => {
      if (!liveMode || !dir) return;
      if (!silent) setDetail({ running: true });
      try {
        const res = await fetch(`/api/leanmill/campaign?dir=${encodeURIComponent(dir)}`, { headers: { Accept: "application/json" } });
        setDetail({ running: false, data: await res.json() });
      } catch (e) {
        setDetail({ running: false, error: String(e) });
      }
    },
    [liveMode]
  );

  const loadBlueprints = React.useCallback(async () => {
    if (!liveMode) return;
    try {
      const res = await fetch("/api/leanmill/blueprints", { headers: { Accept: "application/json" } });
      setBlueprints(await res.json());
    } catch (e) {
      setBlueprints({ ok: false, error: String(e) });
    }
  }, [liveMode]);

  React.useEffect(() => { loadList(); }, [liveMode]); // eslint-disable-line
  React.useEffect(() => { loadBlueprints(); }, [liveMode]); // eslint-disable-line
  React.useEffect(() => { if (selected) loadDetail(selected); }, [selected]); // eslint-disable-line
  // Campaigns are deliberately long-lived. Keep the list and selected attempt
  // fresh without making the user click Refresh to discover a new receipt.
  React.useEffect(() => {
    if (!liveMode) return undefined;
    const id = setInterval(() => {
      loadList({ silent: true });
      if (selected) loadDetail(selected, { silent: true });
    }, 4500);
    return () => clearInterval(id);
  }, [liveMode, selected, loadList, loadDetail]);
  // Land on a ready-to-edit sample scaffold: when nothing is saved yet and the editor is untouched, prefill the
  // concrete template so the author edits a real example instead of hunting an empty box + a "New" button.
  React.useEffect(() => {
    if (!blueprints || !blueprints.template) return;
    const saved = (blueprints.blueprints || []).filter((b) => b.lane === "axiompack");
    if (!saved.length && !blueprintText && !blueprintName) {
      setBlueprintName("my_discovery");
      setBlueprintText(blueprints.template);
    }
  }, [blueprints]); // eslint-disable-line

  const selectRow = (dir) => {
    setSelected(dir);
    setActionResult(null);
  };

  // Blueprint authoring — the picker loads a saved blueprint's Markdown into the editor and points
  // Preflight/Run at its saved path; Save writes it back and refreshes the picker.
  const openBlueprint = async (path) => {
    setBlueprintSaveResult(null);
    try {
      const res = await fetch(`/api/leanmill/blueprint-read?path=${encodeURIComponent(path)}`, { headers: { Accept: "application/json" } });
      const out = await res.json();
      if (out && out.ok !== false) {
        setBlueprintName(String(out.name || "").replace(/\.md$/, ""));
        setBlueprintText(out.text || "");
        setPreflightBlueprint(out.path || path);
        setRunBlueprint(out.path || path);
        setDraftModalOpen(true);
      } else {
        setBlueprintSaveResult(out);
      }
    } catch (e) {
      setBlueprintSaveResult({ ok: false, error: String(e) });
    }
  };

  const newBlueprint = () => {
    setBlueprintName("new_discovery_blueprint");
    setBlueprintText((blueprints && blueprints.template) || "");
    setPreflightBlueprint("");
    setRunBlueprint("");
    setBlueprintSaveResult(null);
    setDraftModalOpen(true);
  };

  // Poll the drafted path with the existing read route until the background `leanmill draft` job
  // (a live compiler + independent reviewer call) lands the file, then open it for inspect/edit — the
  // same door a saved-blueprint click uses. Gives up after ~2 minutes; the saved list still finds it later.
  const pollForDraft = React.useCallback((path, attempt) => {
    const tries = attempt || 0;
    fetch(`/api/leanmill/blueprint-read?path=${encodeURIComponent(path)}`, { headers: { Accept: "application/json" } })
      .then((res) => res.json())
      .then((out) => {
        if (out && out.ok !== false) {
          setBlueprintName(String(out.name || "").replace(/\.md$/, ""));
          setBlueprintText(out.text || "");
          setPreflightBlueprint(out.path || path);
          setRunBlueprint(out.path || path);
          setDraftModalOpen(true);
          setDraftStatus(null);
          setBusy("");
          loadBlueprints();
          return;
        }
        throw new Error("not ready");
      })
      .catch(() => {
        if (tries >= 40) {
          setBusy("");
          setDraftStatus({ ok: false, error: "Still drafting after 2 minutes — check “Saved discovery blueprints” below shortly, or try again." });
          return;
        }
        setTimeout(() => pollForDraft(path, tries + 1), 3000);
      });
  }, []); // eslint-disable-line

  const draftFromDescription = async () => {
    const direction = draftDirection.trim();
    if (!direction) return;
    setBusy("Draft");
    setDraftStatus(null);
    try {
      const res = await fetch("/api/leanmill/blueprint-draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ direction, name: draftName.trim(), confirmed: true }),
      });
      const out = await res.json();
      const path = out && out.job && out.job.blueprint_path;
      if (out && out.accepted && path) {
        setDraftStatus({ ok: true, message: "Compiling with the subscription runtime — a real compiler and an independent reviewer both have to agree, so this can take a minute…" });
        pollForDraft(path, 0);
      } else {
        setBusy("");
        setDraftStatus({ ok: false, error: (out && out.error) || "Could not start drafting." });
      }
    } catch (e) {
      setBusy("");
      setDraftStatus({ ok: false, error: String(e) });
    }
  };

  const saveBlueprint = async () => {
    setBusy("Save blueprint");
    setBlueprintSaveResult(null);
    try {
      const res = await fetch("/api/leanmill/blueprint-save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: blueprintName.trim(), text: blueprintText }),
      });
      const out = await res.json();
      setBlueprintSaveResult(out);
      if (out && out.ok !== false && out.path) {
        setBlueprintName(String(out.name || blueprintName).replace(/\.md$/, ""));
        setPreflightBlueprint(out.path);
        setRunBlueprint(out.path);
        loadBlueprints();
      }
    } catch (e) {
      setBlueprintSaveResult({ ok: false, error: String(e) });
    }
    setBusy("");
  };

  const postAction = async (route, body, label) => {
    setBusy(label);
    setActionResult(null);
    try {
      const res = await fetch(route, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const out = await res.json();
      setActionResult({ label, ok: out && out.ok !== false, data: out });
    } catch (e) {
      setActionResult({ label, ok: false, data: { error: String(e) } });
    }
    setBusy("");
    if (selected) loadDetail(selected);
    loadList();
  };

  const listData = list && list.data;
  const rows = (listData && listData.campaigns) || [];
  const detailData = detail && detail.data;
  const status = (detailData && detailData.status) || {};
  const run = status.run || {};
  const boundary = status.boundary_completion;
  const forge = status.adapter_forge_completion;
  const interpretation = status.post_freeze_interpretation;
  const budget = status.budget || {};
  const caps = (detailData && detailData.budget_caps) || null;
  const journalEvents = (detailData && detailData.journal && detailData.journal.events) || [];
  const journalTotal = (detailData && detailData.journal && detailData.journal.total_count) || 0;

  return h(
    Block,
    {
      title: "Campaigns",
      lead: "Current discovery runs, their boundaries, budgets, and stop reasons.",
      actions: h(
        "button",
        { type: "button", className: `chip ${list && list.running ? "is-busy" : ""}`, disabled: !liveMode, onClick: loadList },
        list && list.running ? "Loading…" : "Refresh"
      ),
    },
    !liveMode ? h("p", { className: "muted" }, "Campaigns will appear when the live project connection is ready.") : null,
    list && list.error ? h("p", { className: "decision-error" }, displayText(list.error)) : null,

    liveMode && listData
      ? rows.length
        ? h(
            "ul",
            { className: "campaign-list" },
            rows.map((row) =>
              h(
                "li",
                {
                  key: row.attempt_dir,
                  className: `campaign-row ${row.attempt_dir === selected ? "is-selected" : ""} ${campaignIsLive({ status: row.status, run: row.run, attempt_lease: row.attempt_lease }) ? "is-live" : ""}`,
                  onClick: () => selectRow(row.attempt_dir),
                },
                h(
                  "div",
                  { className: "campaign-row-head" },
                  h("div", { className: "campaign-row-id-wrap" },
                    campaignIsLive({ status: row.status, run: row.run, attempt_lease: row.attempt_lease })
                      ? h("span", { className: "campaign-live-dot", "aria-label": "campaign running" })
                      : null,
                    h("code", { className: "campaign-row-id" }, shortId(row.attempt_dir))),
                  h(Tag, { tone: statusTone(row.status) }, statusWord(row.status))
                ),
                h(
                  "div",
                  { className: "campaign-row-meta" },
                  row.campaign_id ? h("span", null, displayText(row.campaign_id)) : null,
                  (row.budget || {}).elapsed_ms ? h("span", null, `${elapsedText(row.budget.elapsed_ms)} elapsed`) : null,
                  row.run && row.run.provider_calls !== undefined ? h("span", null, `${row.run.provider_calls} calls`) : null,
                  campaignIsLive({ status: row.status, run: row.run, attempt_lease: row.attempt_lease }) ? h("span", { className: "campaign-row-phase" }, campaignPhase({ status: row.status, run: row.run, attempt_lease: row.attempt_lease })) : null
                )
              )
            )
          )
        : h(EmptyState, { text: "No campaigns running yet — launch one below with a saved blueprint." })
      : null,

    selected
      ? h(
          Block,
          { title: `Campaign ${shortId(selected)}`, className: "campaign-detail" },
          detail && detail.running ? h("p", { className: "muted" }, "Loading…") : null,
          detail && detail.error ? h("p", { className: "decision-error" }, displayText(detail.error)) : null,
          detailData && detailData.ok === false ? h("p", { className: "muted" }, displayText(detailData.error) || "Can't read this campaign.") : null,
            detailData && detailData.ok !== false
            ? h(
                React.Fragment,
                null,
                h(CampaignProgress, { status, budget, caps }),
                h("p", null, h(StatusLine, { tone: statusTone(status.status) }, statusWord(status.status))),
                run.blueprint_id ? h(FactRow, { label: "Blueprint" }, run.blueprint_id) : null,
                run.finalist_count !== undefined ? h(FactRow, { label: "Finalists" }, String(run.finalist_count)) : null,
                run.provider_calls !== undefined ? h(FactRow, { label: "Provider calls" }, String(run.provider_calls)) : null,
                boundary ? h(FactRow, { label: "Boundary queries" }, String(boundary.query_count || 0)) : null,
                boundary && boundary.stop_reason ? h(FactRow, { label: "Boundary stopped" }, displayText(boundary.stop_reason)) : null,
                forge ? h(FactRow, { label: "Adapter gap" }, forge.gap_id || "—") : null,
                budget.soft_stop_reason ? h(FactRow, { label: "Stop reason" }, displayText(budget.soft_stop_reason)) : null,
                caps && caps.wall_clock_s
                  ? h(
                      React.Fragment,
                      null,
                      h(FactRow, { label: "Elapsed" }, `${elapsedText(budget.elapsed_ms || 0)} of ${elapsedText(caps.wall_clock_s * 1000)}`),
                      h(Meter, { value: budget.elapsed_ms || 0, total: caps.wall_clock_s * 1000 })
                    )
                  : null,
                objectFactRows(budget.usage),
                interpretation
                  ? h(
                      React.Fragment,
                      null,
                      h(FactRow, { label: "Interpretation" }, displayText(interpretation.status || "")),
                      interpretation.novelty_assessment ? h(FactRow, { label: "Novelty" }, displayText(interpretation.novelty_assessment)) : null
                    )
                  : null
              )
            : null,

          h(
            "div",
            { className: "campaign-actions" },
            h(
              "button",
              {
                type: "button",
                title: "Calls execute_frontier_campaign_verification (boundary checks, no Lean by default)",
                className: `chip ${busy === "Verify" ? "is-busy" : ""}`,
                disabled: !liveMode || !!busy,
                onClick: () => postAction("/api/leanmill/campaign-verify", { dir: selected }, "Verify"),
              },
              "Verify"
            ),
            h(
              "button",
              {
                type: "button",
                title: "Calls replay_frontier_campaign — revalidates the frozen navigation without new provider calls",
                className: `chip ${busy === "Replay" ? "is-busy" : ""}`,
                disabled: !liveMode || !!busy,
                onClick: () => postAction("/api/leanmill/campaign-replay", { dir: selected }, "Replay"),
              },
              "Replay"
            ),
            h("input", {
              type: "text",
              className: "form-input-inline campaign-authority-input",
              placeholder: "your name/id (authority)",
              value: authorityRef,
              disabled: !liveMode,
              onChange: (e) => setAuthorityRef(e.target.value),
            }),
            h(
              "button",
              {
                type: "button",
                title: "Calls request_frontier_campaign_stop",
                className: `chip ${busy === "Stop" ? "is-busy" : ""}`,
                disabled: !liveMode || !!busy || !authorityRef.trim(),
                onClick: () => postAction("/api/leanmill/campaign-stop", { dir: selected, authority_ref: authorityRef.trim() }, "Stop"),
              },
              "Request stop"
            ),
            h("input", {
              type: "text",
              className: "form-input-inline campaign-authority-input",
              placeholder: "reason for retiring",
              value: retireReason,
              disabled: !liveMode,
              onChange: (e) => setRetireReason(e.target.value),
            }),
            h(
              "button",
              {
                type: "button",
                title: "Calls retire_frontier_campaign — permanent, records who and why",
                className: `chip ghost ${busy === "Retire" ? "is-busy" : ""}`,
                disabled: !liveMode || !!busy || !authorityRef.trim() || !retireReason.trim(),
                onClick: () =>
                  postAction(
                    "/api/leanmill/campaign-retire",
                    { dir: selected, authority_ref: authorityRef.trim(), reason: retireReason.trim() },
                    "Retire"
                  ),
              },
              "Retire"
            ),
            h(
              "button",
              {
                type: "button",
                title: "Calls resume_frontier_campaign_navigation — continues an interrupted navigator from durable calls",
                className: `chip ${busy === "Resume" ? "is-busy" : ""}`,
                disabled: !liveMode || !!busy,
                onClick: () => postAction("/api/leanmill/campaign-resume", { dir: selected }, "Resume"),
              },
              "Resume"
            ),
            h(
              "button",
              {
                type: "button",
                title: "Calls materialize_frontier_navigation_from_journal — recovers a capped/crashed navigator from frozen events",
                className: `chip ${busy === "Recover" ? "is-busy" : ""}`,
                disabled: !liveMode || !!busy,
                onClick: () => postAction("/api/leanmill/campaign-recover", { dir: selected }, "Recover"),
              },
              "Recover"
            ),
            h("input", {
              type: "text",
              className: "form-input-inline campaign-authority-input",
              placeholder: "lean root (for Recheck)",
              value: leanRoot,
              disabled: !liveMode,
              onChange: (e) => setLeanRoot(e.target.value),
            }),
            h(
              "button",
              {
                type: "button",
                title: "Calls recheck_frontier_boundary_governance — re-governs saved Lean proof bytes, no new agent call",
                className: `chip ${busy === "Recheck" ? "is-busy" : ""}`,
                disabled: !liveMode || !!busy || !leanRoot.trim(),
                onClick: () => postAction("/api/leanmill/campaign-recheck", { dir: selected, lean_root: leanRoot.trim() }, "Recheck"),
              },
              "Recheck"
            ),
            h(
              "button",
              {
                type: "button",
                title: "Calls run_post_freeze_literature_review — one budgeted, source-backed interpretation after freeze",
                className: `chip ${busy === "Interpret" ? "is-busy" : ""}`,
                disabled: !liveMode || !!busy,
                onClick: () => postAction("/api/leanmill/campaign-interpret", { dir: selected }, "Interpret"),
              },
              "Interpret"
            )
          ),
          actionResult
            ? h(
                "div",
                { className: `campaign-action-result ${actionResult.ok ? "" : "decision-error"}` },
                h("strong", null, `${actionResult.label}: `),
                actionResult.ok ? "done. " : "failed. ",
                objectFactRows(actionResult.data)
              )
            : null,

          h(
            "div",
            null,
            h("span", { className: "eyebrow" }, `Journal (${journalTotal} event${journalTotal === 1 ? "" : "s"})`),
            journalEvents.length
              ? h(
                  "ul",
                  { className: "campaign-journal-list" },
                  journalEvents
                    .slice()
                    .reverse()
                    .map((event) =>
                      h(
                        "li",
                        { key: event.event_id, className: "campaign-journal-row" },
                        h("span", { className: "campaign-journal-type" }, displayText(event.event_type)),
                        h("span", { className: "campaign-journal-meta" }, `${event.authority} · ${displayText(event.evidence_status)}`)
                      )
                    )
                )
              : h("p", { className: "muted" }, "No journal events recorded yet.")
          )
        )
      : null,

    h(
      Block,
      {
        title: "Author & launch a discovery",
        lead: "Describe the region you want AxiomPack to explore in plain language and it drafts the blueprint for you, or pick a saved one. Preflight validates it with zero provider calls before Run starts it.",
      },
      // NL-first authoring — the PRIMARY door. Calls POST /api/leanmill/blueprint-draft, which shells
      // `ztare leanmill draft`: the real explore_axiom_space compiler + independent reviewer role pair
      // (frontier_agent_role + compile_frontier_blueprint), compile-only — no navigation, no context
      // build. Needs a live subscription runtime (codex/claude on PATH); fails closed with a clear error
      // otherwise. The drafted file opens below in editorModal for inspect/edit before Preflight/Run.
      h(
        "div",
        null,
        h("span", { className: "eyebrow" }, "Describe the region / direction to explore (plain language)"),
        h("textarea", {
          className: "form-input",
          rows: 4,
          placeholder: "e.g. Explore anonymous two-law theories over one binary operation; find small independent axiom pairs whose conjunction forces new structure.",
          value: draftDirection,
          disabled: !liveMode,
          onChange: (e) => setDraftDirection(e.target.value),
        }),
        h("input", {
          type: "text",
          className: "form-input-inline",
          style: { marginTop: 8 },
          placeholder: "optional name (defaults to a slug from your description)",
          value: draftName,
          disabled: !liveMode,
          onChange: (e) => setDraftName(e.target.value),
        }),
        h(
          "div",
          { className: "campaign-actions" },
          h(
            "button",
            {
              type: "button",
              title: "Calls POST /api/leanmill/blueprint-draft — a live compiler + independent reviewer call",
              className: `chip primary ${busy === "Draft" ? "is-busy" : ""}`,
              disabled: !liveMode || !!busy || !draftDirection.trim(),
              onClick: draftFromDescription,
            },
            busy === "Draft" ? "Starting…" : "Draft from description"
          )
        ),
        draftStatus
          ? h(
              "div",
              { className: draftStatus.ok === false ? "decision-error" : "muted" },
              draftStatus.ok === false ? displayText(draftStatus.error) : draftStatus.message
            )
          : null
      ),
      // Only lane:axiompack blueprints belong in the discovery picker — the blueprints dir also holds the
      // everyday formalize-lane blueprints (Draft target), which are a different job and would just be noise here.
      (() => {
        const saved = ((blueprints && blueprints.blueprints) || []).filter((row) => row.lane === "axiompack");
        return h(
          "div",
          null,
          h("span", { className: "eyebrow" }, `Saved discovery blueprints (${saved.length})`),
          saved.length
            ? h(
                "ul",
                { className: "campaign-list" },
                saved.map((row) =>
                  h(
                    "li",
                    {
                      key: row.path,
                      className: `campaign-row ${row.path === preflightBlueprint ? "is-selected" : ""}`,
                      onClick: () => openBlueprint(row.path),
                    },
                    h(
                      "div",
                      { className: "campaign-row-head" },
                      h("code", { className: "campaign-row-id" }, row.name),
                      h(Tag, { tone: "neutral" }, row.lane)
                    )
                  )
                )
              )
            : h(EmptyState, { text: "No saved discovery blueprints yet — draft one above, or start with “New discovery blueprint.”" })
        );
      })(),
      h(
        "div",
        { className: "campaign-actions" },
        h(
          "button",
          {
            type: "button",
            title: "Open the starting sample scaffold in the blueprint editor",
            className: "chip ghost",
            disabled: !liveMode,
            onClick: newBlueprint,
          },
          "New discovery blueprint"
        )
      ),
      draftModalOpen
        ? editorModal({
            liveMode,
            busy,
            blueprintName,
            blueprintText,
            setBlueprintName,
            setBlueprintText,
            saveBlueprint,
            blueprintSaveResult,
            preflightBlueprint,
            runBlueprint,
            preflightResult,
            runResult,
            setBusy,
            setPreflightResult,
            setRunResult,
            loadList,
            dialogRef: draftDialogRef,
            closeButtonRef: draftCloseRef,
            onClose: closeDraftModal,
          })
        : null
    )
  );
}

// The blueprint editor — inspect/edit the generated or saved Markdown, then Preflight/Run — opened as a
// design-system modal (the same .modal-backdrop/.modal-shell pattern as pluginmanager.jsx/main.js) from
// either a drafted file (auto-open once `leanmill draft` lands it) or the saved-blueprint picker/"New".
function editorModal({
  liveMode, busy, blueprintName, blueprintText, setBlueprintName, setBlueprintText, saveBlueprint,
  blueprintSaveResult, preflightBlueprint, runBlueprint, preflightResult, runResult,
  setBusy, setPreflightResult, setRunResult, loadList, dialogRef, closeButtonRef, onClose,
}) {
  return h(
    ModalPortal,
    null,
    h(
      "div",
      { className: "modal-backdrop", role: "presentation", onMouseDown: (e) => e.target === e.currentTarget && onClose() },
      h(
        "div",
        { ref: dialogRef, className: "modal-shell", role: "dialog", "aria-modal": "true", "aria-label": "Discovery blueprint", tabIndex: -1 },
        h(
          "div",
          { className: "modal-head discovery-modal-head" },
          h("h3", { style: { margin: 0 } }, "Discovery blueprint"),
          h("div", { className: "modal-header-actions" },
            h("button", {
              ref: closeButtonRef,
              type: "button",
              className: "icon-button",
              onClick: onClose,
              disabled: !!busy,
              "aria-label": "Close discovery blueprint",
              title: "Close",
            }, h(X, { size: 17, "aria-hidden": "true" })))
        ),
        h(
          "div",
          { className: "modal-body" },
          h("input", {
          type: "text",
          className: "form-input",
          placeholder: "filename (saved as blueprints/<name>.md)",
          value: blueprintName,
          disabled: !liveMode,
          onChange: (e) => setBlueprintName(e.target.value),
        }),
        h("textarea", {
          className: "form-input",
          style: { fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace", marginTop: 8 },
          rows: 16,
          placeholder: "leanmill.campaign.v1 frontmatter + the research direction in prose",
          value: blueprintText,
          disabled: !liveMode,
          onChange: (e) => setBlueprintText(e.target.value),
        }),
        h(
          "div",
          { className: "campaign-actions" },
          h(
            "button",
            {
              type: "button",
              title: "Calls POST /api/leanmill/blueprint-save",
              className: `chip ${busy === "Save blueprint" ? "is-busy" : ""}`,
              disabled: !liveMode || !!busy || !blueprintName.trim() || !blueprintText.trim(),
              onClick: saveBlueprint,
            },
            busy === "Save blueprint" ? "Saving…" : "Save"
          )
        ),
        blueprintSaveResult
          ? h(
              "div",
              { className: blueprintSaveResult.ok === false ? "decision-error" : "muted" },
              blueprintSaveResult.ok === false
                ? displayText(blueprintSaveResult.error || "Could not save the blueprint.")
                : `Saved to ${blueprintSaveResult.path}.`
            )
          : null,
        h(FactRow, { label: "Preflight/Run target" }, preflightBlueprint || runBlueprint || "— save this blueprint first —"),
        h(
          "div",
          { className: "campaign-actions" },
          h(
            "button",
            {
              type: "button",
              title: "Shells `ztare leanmill preflight` — validates the contract, zero provider calls",
              className: `chip ${busy === "Preflight" ? "is-busy" : ""}`,
              disabled: !liveMode || !!busy || !preflightBlueprint.trim(),
              onClick: async () => {
                setBusy("Preflight");
                setPreflightResult(null);
                try {
                  const res = await fetch("/api/leanmill/campaign-preflight", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ blueprint: preflightBlueprint.trim() }),
                  });
                  setPreflightResult(await res.json());
                } catch (e) {
                  setPreflightResult({ ok: false, error: String(e) });
                }
                setBusy("");
              },
            },
            busy === "Preflight" ? "Checking…" : "Preflight"
          ),
          h(
            "button",
            {
              type: "button",
              title: "Shells `ztare leanmill campaign` in the background — the real, budgeted orchestration",
              className: `chip primary ${busy === "Run" ? "is-busy" : ""}`,
              disabled: !liveMode || !!busy || !runBlueprint.trim(),
              onClick: async () => {
                setBusy("Run");
                setRunResult(null);
                try {
                  const res = await fetch("/api/leanmill/campaign-run", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ blueprint: runBlueprint.trim(), confirmed: true }),
                  });
                  const out = await res.json();
                  setRunResult(out);
                  if (out && out.accepted) loadList();
                } catch (e) {
                  setRunResult({ ok: false, error: String(e) });
                }
                setBusy("");
              },
            },
            busy === "Run" ? "Starting…" : "Run"
          )
        ),
        preflightResult
          ? h(
              "div",
              { className: preflightResult.ok === false ? "decision-error" : "muted" },
              preflightResult.ok === false ? displayText(preflightResult.error || "Preflight failed.") : objectFactRows(preflightResult)
            )
          : null,
        runResult
          ? h(
              "div",
              { className: runResult.accepted ? "campaign-launch-progress" : "decision-error", role: runResult.accepted ? "status" : undefined, "aria-live": runResult.accepted ? "polite" : undefined },
              runResult.accepted
                ? h(React.Fragment, null,
                    h("span", { className: "campaign-live-dot", "aria-hidden": "true" }),
                    h("span", null, "Campaign accepted. Watching for its attempt folder, budget ledger, and first heartbeat."))
                : displayText(runResult.error || "Could not start the campaign.")
            )
          : null
        )
      )
    )
  );
}
