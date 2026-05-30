/**
 * Principal Cockpit — directive sender + daemon controls.
 *
 * Surfaces the two write endpoints that exist on the git-sync server but had
 * no UI before Org-5: `/api/directive` and `/api/control`. See
 * docs/internal/orbit_dashboard_audit_2026-04-30.md S1.
 *
 * Kernel discipline (per GP-191): this component is domain-neutral. It lists
 * roles and lets the principal send a typed directive or a typed control
 * action. The semantic interpretation of those messages is the role daemon's
 * concern, not the cockpit's.
 */
import { useState } from 'react'
import type { Role } from '../types/org'

interface Props {
  roles: Role[]
  apiPost: (path: string, body: unknown) => Promise<Response>
}

type ControlAction = 'PAUSE' | 'RESUME' | 'STOP'

const DAEMON_ROLE_CLASSES = new Set(['manager', 'director', 'specialist'])

export function PrincipalCockpit({ roles, apiPost }: Props) {
  const daemonRoles = roles.filter(r => DAEMON_ROLE_CLASSES.has(r.role_class))
  const [open, setOpen] = useState(false)
  const [target, setTarget] = useState<string>(daemonRoles[0]?.role_id ?? '')
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null)

  if (daemonRoles.length === 0) return null

  async function sendDirective() {
    if (!target || !body.trim()) {
      setStatus({ kind: 'err', text: 'Pick a role and type a message.' })
      return
    }
    setBusy(true)
    setStatus(null)
    try {
      const res = await apiPost('/api/directive', { target_role: target, message: body.trim() })
      if (res.ok) {
        setBody('')
        setStatus({ kind: 'ok', text: `Directive queued for ${target}.` })
      } else {
        setStatus({ kind: 'err', text: `${res.status}: ${await res.text()}` })
      }
    } catch (e) {
      setStatus({ kind: 'err', text: String(e) })
    } finally {
      setBusy(false)
    }
  }

  async function control(roleId: string, action: ControlAction) {
    if (action === 'STOP') {
      const ok = window.confirm(`STOP ${roleId} daemon? It will not pick up new tasks until you RESUME.`)
      if (!ok) return
    }
    setBusy(true)
    setStatus(null)
    try {
      const res = await apiPost('/api/control', { target_role: roleId, action })
      if (res.ok) {
        setStatus({ kind: 'ok', text: `${action} → ${roleId}` })
      } else {
        setStatus({ kind: 'err', text: `${res.status}: ${await res.text()}` })
      }
    } catch (e) {
      setStatus({ kind: 'err', text: String(e) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ marginTop: 16 }}>
      <h3
        onClick={() => setOpen(o => !o)}
        style={{
          fontSize: 10, color: '#6b7394', textTransform: 'uppercase', letterSpacing: 1,
          marginBottom: 8, cursor: 'pointer', userSelect: 'none',
          display: 'flex', alignItems: 'center', gap: 6,
        }}
      >
        {open ? '▼' : '▶'} 🎛 Principal Cockpit
      </h3>

      {open && (
        <div style={{
          background: '#161822', borderRadius: 8, padding: 10,
          border: '1px solid #1e2030', fontSize: 11,
        }}>
          {/* Directive form */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 10, color: '#6b7394', marginBottom: 4 }}>
              Send directive (free-text → role inbox)
            </div>
            <select
              value={target}
              onChange={e => setTarget(e.target.value)}
              disabled={busy}
              style={{
                width: '100%', marginBottom: 6, padding: '4px 6px',
                background: '#0f1117', color: '#e8eaf0',
                border: '1px solid #1e2030', borderRadius: 4, fontSize: 11,
              }}
            >
              {daemonRoles.map(r => (
                <option key={r.role_id} value={r.role_id}>{r.role_id}</option>
              ))}
            </select>
            <textarea
              value={body}
              onChange={e => setBody(e.target.value)}
              disabled={busy}
              placeholder={`e.g., ${target}: switch focus to gp168 next iter`}
              rows={3}
              style={{
                width: '100%', padding: '4px 6px',
                background: '#0f1117', color: '#e8eaf0',
                border: '1px solid #1e2030', borderRadius: 4, fontSize: 11,
                resize: 'vertical', fontFamily: 'inherit',
              }}
            />
            <button
              onClick={sendDirective}
              disabled={busy || !body.trim()}
              style={{
                marginTop: 6, padding: '4px 10px',
                background: busy ? '#1e2030' : 'rgba(79,143,247,0.2)',
                color: busy ? '#6b7394' : '#4f8ff7',
                border: '1px solid rgba(79,143,247,0.4)',
                borderRadius: 4, fontSize: 11, cursor: busy ? 'wait' : 'pointer',
              }}
            >
              Send directive
            </button>
          </div>

          {/* Daemon controls */}
          <div>
            <div style={{ fontSize: 10, color: '#6b7394', marginBottom: 4 }}>
              Daemon controls
            </div>
            {daemonRoles.map(r => (
              <div
                key={r.role_id}
                style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  padding: '4px 6px', marginBottom: 4,
                  background: '#0f1117', borderRadius: 4,
                  border: '1px solid #1e2030',
                }}
              >
                <span style={{ flex: 1, color: '#cbd0e0', fontFamily: 'monospace', fontSize: 11 }}>
                  {r.role_id}
                </span>
                <button
                  onClick={() => control(r.role_id, 'PAUSE')}
                  disabled={busy}
                  title="Pause: daemon ticks no-op until RESUME"
                  style={controlBtn('#f59e0b', busy)}
                >
                  PAUSE
                </button>
                <button
                  onClick={() => control(r.role_id, 'RESUME')}
                  disabled={busy}
                  title="Resume: clear PAUSE/STOP"
                  style={controlBtn('#34d399', busy)}
                >
                  RESUME
                </button>
                <button
                  onClick={() => control(r.role_id, 'STOP')}
                  disabled={busy}
                  title="Stop: daemon refuses new tasks until RESUME (confirms before action)"
                  style={controlBtn('#ef4444', busy)}
                >
                  STOP
                </button>
              </div>
            ))}
          </div>

          {status && (
            <div style={{
              marginTop: 10, padding: '4px 8px', borderRadius: 4,
              fontSize: 10,
              color: status.kind === 'ok' ? '#34d399' : '#ef4444',
              background: status.kind === 'ok' ? 'rgba(52,211,153,0.10)' : 'rgba(239,68,68,0.10)',
              border: `1px solid ${status.kind === 'ok' ? 'rgba(52,211,153,0.3)' : 'rgba(239,68,68,0.3)'}`,
            }}>
              {status.text}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function controlBtn(color: string, busy: boolean): React.CSSProperties {
  return {
    padding: '2px 6px',
    fontSize: 9,
    background: busy ? '#1e2030' : `${color}22`,
    color: busy ? '#6b7394' : color,
    border: `1px solid ${color}55`,
    borderRadius: 3,
    cursor: busy ? 'wait' : 'pointer',
    fontFamily: 'monospace',
    fontWeight: 600,
  }
}
