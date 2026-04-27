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
  mandate_path: string
}

export interface Budget {
  daily_cap_usd: number
  session_cap_usd: number
  single_action_cap_usd: number
  warn_threshold_frac: number
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

export interface OrgState {
  members: Member[]
  roles: Role[]
  assignments: Assignment[]
  sessions: Session[]
  damage_signals: DamageSignal[]
  work_candidates: WorkCandidate[]
  last_sync: string
}
