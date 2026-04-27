/**
 * Orbit — Governance for Human-AI Organizations.
 *
 * Three-pane layout (Brand pace layers):
 *   Left:   Governance (slow) — roles, mandates, closure map
 *   Center: Agent constellation (working) — faces, review queue
 *   Right:  Damage signals (fast) — real-time feed, attention budget
 */
import { useState } from 'react'
import { useOrgState } from './lib/useOrgState'
import { GovernancePane } from './components/GovernancePane'
import { AgentTile } from './components/AgentTile'
import { AgentOrb, deriveOrbState } from './components/AgentOrb'
import { DamageSignalFeed } from './components/DamageSignalFeed'

export function App() {
  const { state, connected, error } = useOrgState()
  const [selectedRole, setSelectedRole] = useState<string | null>(null)

  if (!state) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', flexDirection: 'column', gap: 12,
      }}>
        <div style={{ fontSize: 24 }}>🛡</div>
        <div style={{ color: '#6b7394', fontSize: 14 }}>
          {error || 'Connecting to git-sync daemon...'}
        </div>
        <div style={{ color: '#4a5070', fontSize: 12 }}>
          Run: <code style={{ color: '#4f8ff7' }}>cd dashboard && npm run sync</code>
        </div>
      </div>
    )
  }

  const activeSessions = state.sessions.filter(s => !s.end_utc)

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top bar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 24px', background: '#0f1117', borderBottom: '1px solid #1e2030',
      }}>
        <h1 style={{ fontSize: 16, fontWeight: 600, color: '#e8eaf0', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 20 }}>◉</span> Orbit
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 12, color: '#6b7394' }}>
          <span>
            System of record: <code style={{ color: '#4f8ff7' }}>org/</code>
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              background: connected ? '#34d399' : '#f59e0b',
              boxShadow: connected ? '0 0 8px #34d399' : 'none',
              display: 'inline-block',
            }} />
            {connected ? 'live' : 'polling'}
          </span>
          <span>
            {state.members.length} members · {activeSessions.length} active sessions
          </span>
          <span style={{ color: '#4a5070' }}>
            Last sync: {new Date(state.last_sync).toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Three-pane layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr 320px', flex: 1, overflow: 'hidden' }}>

        {/* Left: Governance (slow layer) */}
        <div style={{ background: '#0f1117', borderRight: '1px solid #1e2030', overflowY: 'auto' }}>
          <GovernancePane
            members={state.members}
            roles={state.roles}
            assignments={state.assignments}
            onSelectRole={setSelectedRole}
          />
        </div>

        {/* Center: Agent canvas (working layer) */}
        <div style={{ padding: 16, overflowY: 'auto' }}>
          {/* Active sessions bar */}
          {activeSessions.length > 0 && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '8px 12px', background: '#161822', borderRadius: 8,
              marginBottom: 12, fontSize: 11,
            }}>
              <span>Active sessions:</span>
              {activeSessions.map((s, i) => (
                <span key={i} style={{ color: '#4f8ff7', fontFamily: 'monospace' }}>
                  {s.member_id}@{s.role_id}
                </span>
              ))}
              <span style={{ marginLeft: 'auto', color: '#34d399' }}>● live</span>
            </div>
          )}

          {/* Agent constellation — orbital view */}
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: 40,
            padding: '32px 0',
            minHeight: 180,
            background: 'radial-gradient(ellipse at center, rgba(79,143,247,0.03) 0%, transparent 70%)',
            borderRadius: 16,
          }}>
            {state.members.map(member => {
              const assignment = state.assignments.find(
                a => `member.${member.member_id}` === a.member && a.is_primary
              )
              const role = assignment
                ? state.roles.find(r => `role.${r.role_id}` === assignment.role)
                : undefined
              const session = activeSessions.find(s => s.member_id === member.member_id)
              const isActive = !!(session && !session.end_utc)
              const hasDamage = state.damage_signals.some(
                s => !s.resolved && s.severity === 'critical'
              )

              const orbState = deriveOrbState({
                isActive,
                hasError: hasDamage,
                needsHuman: false,
                isIdle: !isActive,
              })

              return (
                <AgentOrb
                  key={member.member_id}
                  name={(member.display_name || member.member_id).split('(')[0].trim().split(' ')[0]}
                  role={role?.role_id || 'unassigned'}
                  state={orbState}
                  needsHuman={false}
                  statusLine={isActive ? 'Working on current task...' : 'Idle — no active session'}
                  onClick={() => setSelectedRole(role?.role_id || null)}
                  size={member.kind === 'human' ? 72 : 80}
                  selected={selectedRole === role?.role_id}
                />
              )
            })}
          </div>

          {/* Detailed tiles below the faces */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: 12,
            marginTop: 12,
          }}>
            {state.members.filter(m => m.kind === 'ai').map(member => {
              const assignment = state.assignments.find(
                a => `member.${member.member_id}` === a.member && a.is_primary
              )
              const role = assignment
                ? state.roles.find(r => `role.${r.role_id}` === assignment.role)
                : undefined
              const session = activeSessions.find(s => s.member_id === member.member_id)

              return (
                <AgentTile
                  key={member.member_id}
                  member={member}
                  role={role}
                  assignment={assignment}
                  session={session}
                  onClick={() => setSelectedRole(role?.role_id || null)}
                />
              )
            })}
          </div>

          {/* Review queue placeholder */}
          <div style={{ marginTop: 24 }}>
            <h2 style={{
              fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.5,
              color: '#6b7394', marginBottom: 12,
              display: 'flex', alignItems: 'center', gap: 8,
            }}>
              ⚖ Gate Review Queue
              <span style={{
                background: '#4f8ff7', color: '#fff', fontSize: 10,
                padding: '1px 6px', borderRadius: 8,
              }}>
                0
              </span>
            </h2>
            <div style={{ color: '#4a5070', fontSize: 12, textAlign: 'center', padding: 20 }}>
              No pending gates. All agents operating within mandate.
            </div>
          </div>
        </div>

        {/* Right: Damage signals (fast layer) */}
        <div style={{ background: '#0f1117', borderLeft: '1px solid #1e2030', overflowY: 'auto' }}>
          <DamageSignalFeed signals={state.damage_signals} />
        </div>
      </div>
    </div>
  )
}
