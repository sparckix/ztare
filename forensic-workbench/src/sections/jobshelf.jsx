import React from "react";
import { Activity, CheckCircle2, AlertTriangle, Clock3, ArrowRight, RefreshCw } from "lucide-react";
import { displayMessage, displayText, IconButton, SectionHeader, Tag } from "../design-system.js";
import { campaignIsLive } from "../campaign-status.js";

const h = React.createElement;
const LIVE = new Set(["queued", "running", "claimed", "active", "in_progress"]);
const LAST_VISIT_KEY = "ztare.workbench.activity.last-visit";

function tone(status) {
  const value = String(status || "").toLowerCase();
  if (LIVE.has(value)) return "accent";
  if (/complete|success|verified|frozen/.test(value)) return "ok";
  if (/fail|error|unreadable/.test(value)) return "danger";
  if (/block|stop|interrupt|stale|budget/.test(value)) return "warn";
  return "neutral";
}

function isLive(row) {
  return LIVE.has(String(row && row.status || "").toLowerCase()) || Boolean(row && row.lease_active);
}

function timestampMs(row) {
  const raw = row.finished_at || row.updated_at || row.started_at || row.created_at;
  if (!raw) return 0;
  const numeric = Number(raw);
  if (Number.isFinite(numeric) && numeric > 0) return numeric < 1e12 ? numeric * 1000 : numeric;
  const parsed = new Date(raw).getTime();
  return Number.isNaN(parsed) ? 0 : parsed;
}

function timeLabel(row) {
  const timestamp = timestampMs(row);
  if (!timestamp) return "No timestamp recorded";
  const date = new Date(timestamp);
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(date);
}

function campaignRows(payload) {
  return ((payload && payload.campaigns) || []).map((row) => ({
    id: `campaign:${row.attempt_dir}`,
    lane: "Axiom discovery",
    label: row.campaign_id ? `Campaign ${String(row.campaign_id).slice(0, 12)}` : "Axiom discovery campaign",
    detail: row.attempt_dir,
    status: row.status || (row.run && row.run.status) || "unknown",
    lease_active: campaignIsLive(row),
    updated_at: (row.attempt_lease && (row.attempt_lease.heartbeat_at || row.attempt_lease.queue_updated_at)) || "",
    destination: ["leanmill", "Axiom discovery"],
  }));
}

function leanMillRows(payload) {
  const recent = payload && payload.jobs && Array.isArray(payload.jobs.recent) ? payload.jobs.recent : [];
  return recent.map((row, index) => ({
    id: `leanmill:${row.job_path || row.created_at || index}`,
    lane: "LeanMill",
    label: row.label || displayText(row.action || "Proof work"),
    detail: row.target_name || row.notes_path || row.source_file || row.job_path || "LeanMill job",
    status: row.status || "unknown",
    created_at: row.created_at,
    started_at: row.started_at,
    finished_at: row.finished_at,
    destination: ["leanmill", "Proof status"],
  }));
}

function projectRows(jobs) {
  return (Array.isArray(jobs) ? jobs : []).map((row, index) => {
    const evidenceFetch = row.kind === "evidence_fetch";
    return {
      ...row,
      id: `project:${row.id || index}`,
      lane: evidenceFetch ? "Evidence" : "Autoresearch",
      label: row.label || displayText(row.kind || "Project run"),
      detail: row.message || (row.context && row.context.target) || row.project || "Project background job",
      destination: evidenceFetch ? ["sources", "Prepare files"] : ["run", "Ready to run"],
    };
  });
}

function JobRow({ row, onOpenDetail, isNew = false }) {
  const live = isLive(row);
  const rowTone = tone(row.status);
  const Icon = live ? Activity : rowTone === "ok" ? CheckCircle2 : rowTone === "danger" ? AlertTriangle : Clock3;
  return h("li", { className: `job-shelf-row${live ? " is-live" : ""}` },
    h("span", { className: `job-shelf-icon tone-${rowTone}`, "aria-hidden": "true" }, h(Icon, { size: 17, strokeWidth: 1.8 })),
    h("div", { className: "job-shelf-copy" },
      h("div", null,
        h("strong", null, displayMessage(row.label)),
        isNew ? h(Tag, { tone: "accent" }, "finished while away") : null,
        h(Tag, { tone: rowTone }, live ? "in progress" : displayText(row.status || "unknown"))),
      h("p", null, displayMessage(row.detail)),
      h("small", null, `${row.lane} · ${timeLabel(row)}`)),
    h(IconButton, { label: `Open ${row.label || row.lane}`,
      onClick: () => onOpenDetail && onOpenDetail(row.destination[0], row.destination[1]) },
      h(ArrowRight, { size: 17, "aria-hidden": "true" })));
}

export function JobShelf({ liveMode, projectJobs, onOpenDetail }) {
  const [leanMill, setLeanMill] = React.useState(null);
  const [campaigns, setCampaigns] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const enteredAt = React.useRef(Date.now());
  const [lastVisit] = React.useState(() => {
    try { return Number(window.localStorage.getItem(LAST_VISIT_KEY) || 0); }
    catch { return 0; }
  });

  const refresh = React.useCallback(() => {
    if (!liveMode) return Promise.resolve();
    setLoading(true);
    return Promise.all([
      fetch("/api/leanmill", { headers: { Accept: "application/json" }, __wbSilent: true }).then((response) => response.ok ? response.json() : null),
      fetch("/api/leanmill/campaigns", { headers: { Accept: "application/json" }, __wbSilent: true }).then((response) => response.ok ? response.json() : null),
    ]).then(([leanPayload, campaignPayload]) => {
      setLeanMill(leanPayload);
      setCampaigns(campaignPayload);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [liveMode]);

  React.useEffect(() => {
    refresh();
    if (!liveMode) return undefined;
    const id = window.setInterval(refresh, 10000);
    return () => window.clearInterval(id);
  }, [liveMode, refresh]);

  React.useEffect(() => () => {
    try { window.localStorage.setItem(LAST_VISIT_KEY, String(enteredAt.current)); }
    catch { /* Activity remains usable when browser storage is unavailable. */ }
  }, []);

  const rows = [...projectRows(projectJobs), ...leanMillRows(leanMill), ...campaignRows(campaigns)];
  const newestFirst = (a, b) => timestampMs(b) - timestampMs(a);
  const active = rows.filter(isLive).sort(newestFirst);
  const recent = rows.filter((row) => !isLive(row)).sort(newestFirst).slice(0, 12);
  const newCount = lastVisit ? recent.filter((row) => timestampMs(row) > lastVisit).length : 0;

  return h("section", { className: "job-shelf", "aria-label": "Background activity" },
    h(SectionHeader, { className: "job-shelf-head", title: "Background activity",
      description: "Long research and proof work continues outside this page. Return here to see the last durable state and resume in the lane that owns it.",
      actions: h(IconButton, { label: "Refresh activity", busy: loading, disabled: !liveMode || loading, onClick: refresh },
        h(RefreshCw, { size: 16, "aria-hidden": "true" })) }),
    active.length
      ? h("section", { className: "job-shelf-group" }, h("div", { className: "job-shelf-group-head" }, h("h3", null, "In progress"), h("span", null, `${active.length} active`)),
          h("ul", null, active.map((row) => h(JobRow, { key: row.id, row, onOpenDetail }))))
      : h("div", { className: "job-shelf-empty" }, h(CheckCircle2, { size: 19, "aria-hidden": "true" }), h("div", null, h("strong", null, "No work is currently running"), h("p", null, "Research runs, evidence recovery, proof jobs, and discovery campaigns will appear here."))),
    recent.length
      ? h("section", { className: "job-shelf-group" },
          h("div", { className: "job-shelf-group-head" },
            h("h3", null, newCount ? "Finished since your last visit" : "Recently finished"),
            h("span", null, newCount ? `${newCount} new · newest first` : "Newest first")),
          h("ul", null, recent.map((row) => h(JobRow, { key: row.id, row, onOpenDetail,
            isNew: Boolean(lastVisit && timestampMs(row) > lastVisit) }))))
      : null);
}
