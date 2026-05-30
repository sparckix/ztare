/**
 * Orbit — Governance for Human-AI Organizations.
 *
 * Three-pane layout (Brand pace layers):
 *   Left:   Governance (slow) — roles, mandates, closure map
 *   Center: Agent constellation (working) — faces, review queue
 *   Right:  Damage signals (fast) — real-time feed, attention budget
 */
import { useState, useCallback } from 'react'
import { useOrgState } from './lib/useOrgState'
import { GovernancePane } from './components/GovernancePane'
import { AgentTile } from './components/AgentTile'
import { AgentOrb, deriveOrbState } from './components/AgentOrb'
import { DamageSignalFeed } from './components/DamageSignalFeed'
import { ObjectiveTreePane } from './components/ObjectiveTreePane'
import { PrincipalCockpit } from './components/PrincipalCockpit'
import { MetaConfigPane } from './components/MetaConfigPane'
import { FrontierStatePane } from './components/FrontierStatePane'
import { SpendPane } from './components/SpendPane'
import { BatchGateReview } from './components/BatchGateReview'
import { SpatialCanvas } from './components/SpatialCanvas'
import { ChatPane } from './components/ChatPane'

// Optional Bearer token for the orbit API (matches ORBIT_API_TOKEN on the
// server). When empty (default), the server treats requests as authorized,
// which is the right behavior for solo-principal localhost. When set, the
// frontend sends `Authorization: Bearer <token>` on all POSTs. Configure via
// `VITE_ORBIT_API_TOKEN` in `.env.local` for a production deployment.
const API_TOKEN: string = (import.meta as any).env?.VITE_ORBIT_API_TOKEN ?? ''

async function apiPost(path: string, body: unknown): Promise<Response> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (API_TOKEN) headers['Authorization'] = `Bearer ${API_TOKEN}`
  return fetch(path, { method: 'POST', headers, body: JSON.stringify(body) })
}

export function App() {
  const { state, connected, error } = useOrgState()
  const [selectedRole, setSelectedRole] = useState<string | null>(null)
  const [gateError, setGateError] = useState<string | null>(null)
  const [metaConfigOpen, setMetaConfigOpen] = useState(false)
  const [frontierOpen, setFrontierOpen] = useState(false)
  const [spendOpen, setSpendOpen] = useState(false)
  const [batchReviewOpen, setBatchReviewOpen] = useState(false)
  const [spatialCanvasOpen, setSpatialCanvasOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)

  // useCallback MUST be before any early return — Rules of Hooks.
  // (Was after the early-return historically; was a latent bug masked by
  // synchronous-on-first-render timing.)
  const resolveGate = useCallback(async (gateId: string, optionId: string, reason?: string) => {
    setGateError(null)
    const res = await apiPost('/api/gate/resolve', {
      gate_id: gateId,
      option_id: optionId,
      reason: reason ?? '',
    })
    if (!res.ok) {
      const text = await res.text()
      setGateError(text || `gate resolve failed: ${res.status}`)
    }
  }, [])

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
          Run: <code style={{ color: '#4f8ff7' }}>cd orbit && npm run sync</code>
        </div>
      </div>
    )
  }

  const activeSessions = state.sessions.filter(s => !s.end_utc)
  const pendingGates = state.gates.filter(g => g.status !== 'resolved')
  const openAgentMessages = state.agent_messages ?? []

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
              background: connected ? ((pendingGates.length || openAgentMessages.length) ? '#f59e0b' : '#34d399') : '#f59e0b',
              boxShadow: connected ? ((pendingGates.length || openAgentMessages.length) ? '0 0 8px #f59e0b' : '0 0 8px #34d399') : 'none',
              display: 'inline-block',
            }} />
            {connected ? ((pendingGates.length || openAgentMessages.length) ? 'needs attention' : 'live') : 'polling'}
          </span>
          <span>
            {state.members.length} members · {activeSessions.length} active sessions
          </span>
          <span style={{ color: '#4a5070' }}>
            Last sync: {new Date(state.last_sync).toLocaleTimeString()}
          </span>
          <button
            onClick={() => setSpendOpen(true)}
            style={{
              background: 'transparent', border: '1px solid #1e2030', borderRadius: 6,
              padding: '4px 10px', fontSize: 11, color: '#c8cdd8', cursor: 'pointer', marginRight: 6,
            }}
            title="Spend — daily LLM cost, role caps, breakdown by category/model"
          >
            💰 Spend
          </button>
          <button
            onClick={() => setBatchReviewOpen(true)}
            disabled={pendingGates.length === 0}
            style={{
              background: pendingGates.length > 0 ? '#7c2d12' : 'transparent',
              border: '1px solid #1e2030', borderRadius: 6,
              padding: '4px 10px', fontSize: 11,
              color: pendingGates.length > 0 ? '#fef3c7' : '#6b7394',
              cursor: pendingGates.length > 0 ? 'pointer' : 'not-allowed',
              marginRight: 6,
            }}
            title="Batch gate review — aggregate pending gates into one review session (GP-167)"
          >
            🗳 Review ({pendingGates.length})
          </button>
          <button
            onClick={() => setSpatialCanvasOpen(true)}
            style={{
              background: 'transparent', border: '1px solid #1e2030', borderRadius: 6,
              padding: '4px 10px', fontSize: 11, color: '#c8cdd8', cursor: 'pointer', marginRight: 6,
            }}
            title="Spatial canvas — TLDraw view of org/ state (GP-167 v2)"
          >
            🌐 Canvas
          </button>
          <button
            onClick={() => setChatOpen(true)}
            style={{
              background: 'transparent', border: '1px solid #1e2030', borderRadius: 6,
              padding: '4px 10px', fontSize: 11, color: '#c8cdd8', cursor: 'pointer', marginRight: 6,
            }}
            title="Per-role chat — dialog with SRO/RD/manager via cheap-tier subscription LLM"
          >
            💬 Chat
          </button>
          <button
            onClick={() => setFrontierOpen(true)}
            style={{
              background: 'transparent',
              border: '1px solid #1e2030',
              borderRadius: 6,
              padding: '4px 10px',
              fontSize: 11,
              color: '#c8cdd8',
              cursor: 'pointer',
              marginRight: 6,
            }}
            title="RD-1.12 frontier state — route ranking, obstructions, pending actions"
          >
            🧭 Frontier
          </button>
          <button
            onClick={() => setMetaConfigOpen(true)}
            style={{
              background: 'transparent',
              border: '1px solid #1e2030',
              borderRadius: 6,
              padding: '4px 10px',
              fontSize: 11,
              color: '#c8cdd8',
              cursor: 'pointer',
            }}
            title="Meta config — agent utilization caps, sync flags, etc."
          >
            ⚙ Settings
          </button>
        </div>
      </div>

      {metaConfigOpen && (
        <MetaConfigPane
          roles={state.roles}
          onClose={() => setMetaConfigOpen(false)}
        />
      )}

      {spendOpen && (
        <div
          onClick={() => setSpendOpen(false)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
            zIndex: 1000, display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
            paddingTop: '5vh',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              background: '#0a0a0a', color: '#e8e8e8', borderRadius: 8,
              width: 'min(720px, 92vw)', maxHeight: '85vh', overflowY: 'auto',
              border: '1px solid #333',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 12px', borderBottom: '1px solid #222' }}>
              <span style={{ fontFamily: 'monospace', fontSize: 13 }}>Daily Spend (auto-refresh 30s)</span>
              <button
                onClick={() => setSpendOpen(false)}
                style={{ background: 'none', border: '1px solid #444', color: '#aaa', padding: '2px 10px', cursor: 'pointer', fontFamily: 'monospace', fontSize: 11 }}
              >
                close
              </button>
            </div>
            <SpendPane roles={state.roles} />
          </div>
        </div>
      )}

      {batchReviewOpen && (
        <BatchGateReview
          gates={pendingGates}
          onResolve={(gid, opt) => resolveGate(gid, opt)}
          onClose={() => setBatchReviewOpen(false)}
        />
      )}

      {spatialCanvasOpen && (
        <SpatialCanvas
          state={state}
          onClose={() => setSpatialCanvasOpen(false)}
        />
      )}

      {chatOpen && (
        <ChatPane
          roles={state.roles}
          apiPost={apiPost}
          onClose={() => setChatOpen(false)}
        />
      )}

      {frontierOpen && (
        <div
          onClick={() => setFrontierOpen(false)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
            zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              background: '#fff', color: '#222', borderRadius: 8,
              width: 'min(900px, 92vw)', maxHeight: '88vh',
              overflowY: 'auto',
              boxShadow: '0 12px 48px rgba(0,0,0,0.5)',
            }}
          >
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '12px 16px', borderBottom: '1px solid #ddd',
            }}>
              <strong>🧭 RD-1.12 Frontier State</strong>
              <button
                onClick={() => setFrontierOpen(false)}
                style={{
                  background: 'transparent', border: '1px solid #ccc',
                  borderRadius: 4, padding: '2px 8px', cursor: 'pointer',
                }}
              >close</button>
            </div>
            <FrontierStatePane />
          </div>
        </div>
      )}

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
          <div style={{ padding: '0 16px 16px 16px' }}>
            <PrincipalCockpit roles={state.roles} apiPost={apiPost} />
          </div>
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
              const roleNeedsHuman =
                pendingGates.some(g => g.owner === role?.role_id || g.subject?.includes(role?.role_id || '')) ||
                openAgentMessages.some(m => m.to_role === role?.role_id && (m.expects_response || ['request', 'handoff', 'clarification'].includes(m.kind)))

              const orbState = deriveOrbState({
                isActive,
                hasError: hasDamage,
                needsHuman: roleNeedsHuman,
                isIdle: !isActive,
              })

              return (
                <AgentOrb
                  key={member.member_id}
                  name={(member.display_name || member.member_id).split('(')[0].trim().split(' ')[0]}
                  role={role?.role_id || 'unassigned'}
                  state={orbState}
                  needsHuman={roleNeedsHuman}
                  statusLine={
                    roleNeedsHuman ? 'Decision required in Executive Inbox' :
                    isActive ? 'Working on current task...' :
                    'Idle — no active session'
                  }
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
                {pendingGates.length}
              </span>
            </h2>
            <div style={{ color: gateError ? '#ef4444' : '#4a5070', fontSize: 12, textAlign: 'center', padding: 20 }}>
              {gateError || (
                pendingGates.length === 0
                  ? 'No pending gates. All agents operating within mandate.'
                  : 'Resolve gates in the Executive Inbox pane.'
              )}
            </div>
          </div>
        </div>

        {/* Right: OKR tree (GP-168 addendum 2026-04-27) + damage signals (fast layer) */}
        <div style={{ background: '#0f1117', borderLeft: '1px solid #1e2030', overflowY: 'auto' }}>
          <ObjectiveTreePane
            objectives={state.objectives ?? []}
            keyResults={state.key_results ?? []}
            tasks={state.tasks ?? []}
            gates={state.gates ?? []}
            agentMessages={openAgentMessages}
            onResolveGate={resolveGate}
          />
          <div style={{ borderTop: '1px solid #1e2030' }} />
          <DamageSignalFeed signals={state.damage_signals} />
        </div>
      </div>
    </div>
  )
}
