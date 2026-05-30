/**
 * MetaConfigPane — the "Settings" surface for cross-cutting org-runtime knobs.
 *
 * Houses configuration that doesn't belong on a single role's card but
 * needs an editing UI:
 *   - Per-role agent-CLI utilization caps (capacity dimension, separate
 *     from USD spend; see src/ztare/supervisor/agent_utilization_tracker.py)
 *   - (Future) Per-role budget caps editor
 *   - (Future) Notification channel preferences (Telegram on/off, etc.)
 *   - (Future) Sync architecture flags (laptop ↔ VPS exec node)
 *
 * Edit semantics: Orbit POSTs to git-sync's /api/role/<role>/agent_utilization
 * endpoint; the server writes back to org/roles/<role>.yaml and broadcasts
 * the new state via WebSocket. Audit trail lands in
 * ztare_workspace/transitions.jsonl.
 */
import { useEffect, useState } from 'react'
import type { Role, AgentUtilization, AgentUtilizationSnapshot } from '../types/org'

interface Props {
  roles: Role[]
  apiBase?: string  // default same-origin '/api'
  onClose?: () => void
}

const DEFAULT_API = '/api'

const FIELD_META: Array<{
  key: keyof AgentUtilization
  label: string
  unit: string
  hint: string
}> = [
  { key: 'daily_cap_seconds',         label: 'Daily wall-clock cap', unit: 'seconds',
    hint: 'Maximum total agent-CLI session time per UTC day for this role.' },
  { key: 'daily_cap_output_tokens',   label: 'Daily output tokens',  unit: 'tokens',
    hint: 'Total output tokens emitted by the agent CLI per UTC day.' },
  { key: 'daily_cap_turn_count',      label: 'Daily turn count',     unit: 'turns',
    hint: 'Total agent steps (turns) per UTC day.' },
  { key: 'session_cap_seconds',       label: 'Single-session cap',   unit: 'seconds',
    hint: 'Maximum wall-clock time for any single agent-CLI session.' },
  { key: 'absolute_ceiling_seconds',  label: 'Absolute hard ceiling', unit: 'seconds',
    hint: 'Never-exceed daily duration. Used as a runaway-loop circuit-breaker.' },
  { key: 'warn_threshold_frac',       label: 'Warn at fraction',     unit: '0.0–1.0',
    hint: 'Push a Telegram + damage-signal warning when any cap reaches this fraction.' },
]

const DEFAULTS: AgentUtilization = {
  daily_cap_seconds: 7200,
  daily_cap_output_tokens: 300000,
  daily_cap_turn_count: 100,
  session_cap_seconds: 3600,
  absolute_ceiling_seconds: 14400,
  warn_threshold_frac: 0.80,
}


export function MetaConfigPane({ roles, apiBase = DEFAULT_API, onClose }: Props) {
  const [snapshot, setSnapshot] = useState<AgentUtilizationSnapshot | null>(null)
  const [selectedRole, setSelectedRole] = useState<string | null>(null)
  const [draft, setDraft] = useState<AgentUtilization>(DEFAULTS)
  const [saving, setSaving] = useState(false)
  const [savedNote, setSavedNote] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Load today's utilization snapshot.
  useEffect(() => {
    const url = `${apiBase}/agent_utilization/snapshot`
    fetch(url)
      .then(r => r.json())
      .then((data: any) => {
        if (data && (data.totals || data.entries)) {
          setSnapshot({
            date: data.date,
            by_role: data.totals?.by_role || {},
            by_cli: data.totals?.by_cli || {},
            by_role_cli: data.totals?.by_role_cli || {},
          })
        }
      })
      .catch(() => {})  // no-op; show no-data state instead
  }, [apiBase])

  // When a role is selected, prefill draft from its current caps.
  useEffect(() => {
    if (!selectedRole) {
      setDraft(DEFAULTS)
      setSavedNote(null)
      return
    }
    const role = roles.find(r => r.role_id === selectedRole)
    if (role?.agent_utilization) {
      setDraft({ ...role.agent_utilization })
    } else {
      setDraft({ ...DEFAULTS })
    }
    setSavedNote(null)
    setError(null)
  }, [selectedRole, roles])

  const handleField = (key: keyof AgentUtilization, value: string) => {
    const num = Number(value)
    if (Number.isFinite(num)) {
      setDraft(prev => ({ ...prev, [key]: num }))
    }
  }

  const handleSave = async () => {
    if (!selectedRole) return
    setSaving(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/role/${selectedRole}/agent_utilization`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draft),
      })
      const data = await res.json()
      if (data.ok) {
        setSavedNote(`saved → ${data.path}`)
      } else {
        setError(data.error || 'unknown server error')
      }
    } catch (e: any) {
      setError(String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(8,10,18,0.92)',
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{
        width: 720,
        maxHeight: '85vh',
        overflowY: 'auto',
        background: '#0e1018',
        border: '1px solid #1e2030',
        borderRadius: 12,
        padding: 24,
        color: '#e8eaf0',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ fontSize: 14, textTransform: 'uppercase', letterSpacing: 1.5, color: '#6b7394', margin: 0 }}>
            ⚙ Meta Config
          </h2>
          {onClose && (
            <button onClick={onClose} style={{ background: 'transparent', border: 0, color: '#6b7394', cursor: 'pointer', fontSize: 18 }}>
              ×
            </button>
          )}
        </div>

        {/* Live snapshot */}
        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 11, color: '#6b7394', textTransform: 'uppercase', marginBottom: 8 }}>
            Today's agent-CLI utilization {snapshot?.date ? `(${snapshot.date})` : ''}
          </h3>
          {snapshot && Object.keys(snapshot.by_role).length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 8 }}>
              {Object.entries(snapshot.by_role).map(([roleId, bucket]) => {
                const role = roles.find(r => r.role_id === roleId)
                const cap = role?.agent_utilization?.daily_cap_seconds || 0
                const pct = cap > 0 ? Math.min(1, bucket.duration_seconds / cap) : 0
                const warnAt = role?.agent_utilization?.warn_threshold_frac ?? 0.8
                const color = pct >= 1 ? '#ef4444' : pct >= warnAt ? '#f59e0b' : '#34d399'
                return (
                  <div key={roleId} style={{ background: '#161822', borderRadius: 8, padding: 10 }}>
                    <div style={{ fontSize: 11, color: '#c8cdd8', marginBottom: 4 }}>{roleId}</div>
                    <div style={{ fontSize: 10, color: '#6b7394', marginBottom: 4 }}>
                      {Math.round(bucket.duration_seconds)}s / {cap || '∞'}s · {bucket.session_count} sessions
                    </div>
                    <div style={{ height: 4, background: '#1e2030', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{ width: `${pct * 100}%`, height: '100%', background: color }} />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div style={{ color: '#6b7394', fontSize: 11 }}>No utilization recorded today.</div>
          )}
        </section>

        {/* Per-role cap editor */}
        <section style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 11, color: '#6b7394', textTransform: 'uppercase', marginBottom: 8 }}>
            Edit caps per role
          </h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            {roles.map(r => (
              <button
                key={r.role_id}
                onClick={() => setSelectedRole(r.role_id)}
                style={{
                  padding: '6px 10px',
                  fontSize: 11,
                  background: selectedRole === r.role_id ? '#4f8ff7' : '#161822',
                  color: selectedRole === r.role_id ? '#fff' : '#c8cdd8',
                  border: '1px solid #1e2030',
                  borderRadius: 6,
                  cursor: 'pointer',
                }}>
                {r.role_id}{r.agent_utilization ? '' : ' *'}
              </button>
            ))}
          </div>
          {selectedRole && (
            <div style={{
              background: '#161822',
              borderRadius: 8,
              padding: 12,
              border: '1px solid #1e2030',
            }}>
              {FIELD_META.map(meta => (
                <div key={meta.key} style={{ marginBottom: 10 }}>
                  <label style={{ display: 'block', fontSize: 10, color: '#6b7394', marginBottom: 2 }}>
                    {meta.label} <span style={{ color: '#8a93b8' }}>({meta.unit})</span>
                  </label>
                  <input
                    type="number"
                    value={draft[meta.key]}
                    step={meta.key === 'warn_threshold_frac' ? 0.05 : 60}
                    onChange={e => handleField(meta.key, e.target.value)}
                    style={{
                      width: '100%',
                      padding: '6px 8px',
                      fontSize: 12,
                      background: '#0e1018',
                      color: '#e8eaf0',
                      border: '1px solid #1e2030',
                      borderRadius: 4,
                    }}
                  />
                  <div style={{ fontSize: 10, color: '#6b7394', marginTop: 2 }}>{meta.hint}</div>
                </div>
              ))}
              <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  style={{
                    padding: '8px 14px',
                    fontSize: 12,
                    background: saving ? '#1e2030' : '#4f8ff7',
                    color: '#fff',
                    border: 0,
                    borderRadius: 6,
                    cursor: saving ? 'wait' : 'pointer',
                  }}>
                  {saving ? 'Saving…' : `Save → org/roles/${selectedRole}.yaml`}
                </button>
              </div>
              {savedNote && (
                <div style={{ marginTop: 10, fontSize: 11, color: '#34d399' }}>{savedNote}</div>
              )}
              {error && (
                <div style={{ marginTop: 10, fontSize: 11, color: '#ef4444' }}>error: {error}</div>
              )}
            </div>
          )}
        </section>

        <div style={{ fontSize: 10, color: '#6b7394', borderTop: '1px solid #1e2030', paddingTop: 12 }}>
          * Roles without an agent_utilization block in their YAML inherit module
          defaults. Saving here writes the block back; subsequent daemon ticks will
          load the new caps via _role_caps() in agent_utilization_tracker.py.
        </div>
      </div>
    </div>
  )
}
