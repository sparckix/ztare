/** Types mirroring the org/ directory YAML schema. */

export interface Member {
  member_id: string
  kind: 'ai' | 'human'
  display_name: string
  description: string
  substrates: Substrate[]
  capabilities: string[]
}

export interface Substrate {
  name: string
  kind: 'session_bound' | 'persistent'
  current_model: string
  invocation: string
}

export interface Role {
  role_id: string
  role_class: string
  description: string
  authorized_paths: string[]
  forbidden_paths: string[]
  delegates_to: string[]
  escalates_to: string[]
  budget: Budget
  /** Optional agent-CLI utilization caps. Added 2026-05-02 to track
   * Claude-Code / Codex / Gemini-CLI capacity per role per day,
   * orthogonal to USD spend. Consumed by
   * src/ztare/supervisor/agent_utilization_tracker.py. */
  agent_utilization?: AgentUtilization
  mandate_path: string
}

export interface Budget {
  daily_cap_usd: number
  session_cap_usd: number
  single_action_cap_usd: number
  warn_threshold_frac: number
  absolute_ceiling_usd?: number
}

/**
 * Agent-CLI utilization caps. Capacity dimension; separate from USD.
 * One block per role; warn-threshold trip emits a Telegram push (GP-128b)
 * AND a damage signal at org/signals/damage/agent_utilization_warn_*.json.
 *
 * All seconds-based fields are wall-clock seconds. Token fields are
 * output-token counts (input tokens are tracked but not capped because
 * the bottleneck on subscription quota is generated tokens).
 */
export interface AgentUtilization {
  daily_cap_seconds: number
  daily_cap_output_tokens: number
  daily_cap_turn_count: number
  session_cap_seconds: number
  absolute_ceiling_seconds: number
  warn_threshold_frac: number
}

/** Live utilization snapshot for the GovernancePane bar chart. Shape
 * mirrors get_daily_totals() return + per-role-per-cli rollup from the
 * tracker's persisted JSON at ztare_workspace/agent_utilization/<date>.json. */
export interface AgentUtilizationSnapshot {
  date: string             // 'YYYY-MM-DD'
  by_role: Record<string, AgentUtilizationBucket>
  by_cli: Record<string, AgentUtilizationBucket>
  by_role_cli: Record<string, AgentUtilizationBucket>
}

export interface AgentUtilizationBucket {
  duration_seconds: number
  output_tokens: number
  input_tokens: number
  turn_count: number
  session_count: number
}

export interface Assignment {
  member: string
  role: string
  substrate: string
  is_primary: boolean
  valid_from: string
  valid_until: string | null
  notes: string
}

export interface Session {
  session_id: string
  member_id: string
  role_id: string
  substrate: string
  start_utc: string
  end_utc: string | null
  mandate_hash: string
}

export interface DamageSignal {
  timestamp_utc: string
  source: string
  kind: string
  detail: string
  session_id: string
  severity: 'info' | 'warn' | 'critical'
  resolved?: boolean
}

export interface WorkCandidate {
  source: string
  intent: string
  scarcity_signal: string
  severity: string
  age_days: number | null
}

/* ---------------- GP-168 Addendum (2026-04-27) — OKR layer ---------------- */

/**
 * Top tier — Objective. The "why" the org is doing anything. Durable;
 * may outlive quarters. Frontmatter is a small machine-maintainable
 * projection; the body of the markdown is canonical.
 */
export interface Objective {
  objective_id: string
  title?: string
  horizon?: 'target_date' | 'open'
  target_date?: string | null
  status?: 'active' | 'done' | 'abandoned'
  created_by?: string
  created_utc?: string
  closure_deadline?: string | null
  auto_resolution?: 'archive_with_postmortem' | string
  authoring_mode?: 'human' | 'agent_proposed'
}

/**
 * Mid tier — Key Result. Measurable outcome under an Objective.
 * First-class file (not a YAML array) so it can be reassigned, audited,
 * and linked individually.
 */
export interface KeyResult {
  kr_id: string
  objective_id: string
  description?: string
  measurement?: string
  measurement_source?: 'daemon' | 'principal'
  measurement_locus?: 'self' | 'world'
  kr_type?: 'output' | 'outcome' | 'health_metric'
  target?: string
  status?: 'pending' | 'on_track' | 'at_risk' | 'done' | 'failed'
  score?: number | null
  score_rationale?: string | null
  last_measured_utc?: string | null
  review_overdue_threshold_days?: number
  check_ins?: { utc: string; confidence: number; note?: string }[]
  created_utc?: string
}

/**
 * Bottom tier — Task. Concrete unit of work. Renamed from `goals/` on
 * 2026-04-27. Carries closure-pressure fields per Panel A synthesis.
 */
export interface Task {
  task_id: string
  objective_id?: string | null
  kr_id?: string | null
  title?: string
  priority?: 'low' | 'medium' | 'high' | 'urgent'
  assigned_to?: string
  autonomous_scope_ok?: boolean
  status: 'pending' | 'active' | 'done' | 'abandoned'
  closure_deadline?: string | null
  warn_at_pct?: number
  escalate_at_pct?: number
  auto_resolution?: 'deny' | 'approve' | 'escalate' | 'archive' | 'defer'
  budget_cap_usd?: number | null
  budget_spent_usd?: number
  budget_exhaust_action?: 'close_partial' | 'escalate' | 'kill'
  created_by?: string
  created_utc?: string
}

/**
 * GP-168 single executive inbox. The closure daemon writes gates here
 * when pressure thresholds fire; the principal resolves them in Orbit
 * or via Telegram inline buttons.
 */
export interface Gate {
  gate_id: string
  kind: string
  subject?: string
  summary?: string
  options?: { id: string; consequence: string }[]
  default_after_days?: number
  auto_resolution_on_default?: string
  task_path?: string
  kr_path?: string
  objective_path?: string
  honesty?: { score: number; measured: number; total: number }
  owner?: string
  created_utc: string
  status: 'pending' | 'resolved'
}

export interface AgentMessage {
  schema_version: number
  message_id: string
  thread_id: string
  kind: 'inform' | 'request' | 'proposal' | 'handoff' | 'clarification' | 'refusal' | 'status'
  from_role: string
  to_role: string
  subject: string
  body: string
  status: 'open' | 'acknowledged' | 'closed'
  created_utc: string
  causality_id?: string | null
  expects_response?: boolean
  expires_utc?: string | null
  references?: string[]
  artifacts?: string[]
  metadata?: Record<string, unknown>
}

/**
 * Computed pressure for a task or KR — convenience type the UI
 * derives locally rather than storing on disk.
 */
export interface Pressure {
  pct: number              // 0.0 – 1.0+ (>=1 means expired/exhausted)
  band: 'cool' | 'warn' | 'urgent' | 'critical'
  remaining_label: string  // "4h 12m" or "$8.50 left" etc.
}

export interface OrgState {
  members: Member[]
  roles: Role[]
  assignments: Assignment[]
  sessions: Session[]
  damage_signals: DamageSignal[]
  work_candidates: WorkCandidate[]
  objectives: Objective[]
  key_results: KeyResult[]
  tasks: Task[]
  gates: Gate[]
  agent_messages: AgentMessage[]
  last_sync: string
}
