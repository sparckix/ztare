/**
 * BatchGateReview (Orbit v2) — aggregate pending gates into one review session.
 *
 * Per GP-167 panel verdict synthesis:
 *   - Lanier friction: tap-Approve must require context-loading first
 *   - Raskin attention budget: review block is N gates, not interrupt-driven
 *   - Dunbar squad clustering: group by role/severity (humans track ~5 entities)
 *
 * Replaces the per-gate one-Telegram-message-per-decision pattern with a
 * 10-min batch review modal. Operator opens the modal (button on dashboard),
 * sees all pending gates clustered, expands each for context, decides each.
 *
 * Resolution still goes through /api/gate/resolve (same backend as before).
 */
import { useMemo, useState } from 'react'
import type { Gate } from '../types/org'

interface Props {
  gates: Gate[]
  onResolve: (gateId: string, optionId: string) => Promise<void>
  onClose: () => void
}

type Severity = 'critical' | 'high' | 'normal' | 'low'

function severityOf(g: Gate): Severity {
  // Heuristic: gate priority field, or fall back to summary heuristics
  const prio = (g as any).priority || (g as any).candidate?.metadata?.priority || ''
  if (prio === 'critical') return 'critical'
  if (prio === 'high') return 'high'
  if (prio === 'low') return 'low'
  return 'normal'
}

const SEVERITY_RANK: Record<Severity, number> = {
  critical: 0, high: 1, normal: 2, low: 3,
}

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: '🚨 critical',
  high: '⚠️ high',
  normal: '📩 normal',
  low: 'ℹ️ low',
}

export function BatchGateReview({ gates, onResolve, onClose }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [resolving, setResolving] = useState<Set<string>>(new Set())
  const [resolved, setResolved] = useState<Set<string>>(new Set())

  // Group by severity then by owner role
  const groups = useMemo(() => {
    const buckets: Record<Severity, Record<string, Gate[]>> = {
      critical: {}, high: {}, normal: {}, low: {},
    }
    for (const g of gates) {
      if (resolved.has(g.gate_id)) continue
      const sev = severityOf(g)
      const owner = (g as any).owner || 'unassigned'
      buckets[sev][owner] = buckets[sev][owner] || []
      buckets[sev][owner].push(g)
    }
    return buckets
  }, [gates, resolved])

  const totalRemaining = Object.values(groups).reduce(
    (sum, byOwner) => sum + Object.values(byOwner).reduce((s, gs) => s + gs.length, 0), 0,
  )

  const toggleExpand = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleResolve = async (gate: Gate, option: string) => {
    setResolving(prev => new Set(prev).add(gate.gate_id))
    try {
      await onResolve(gate.gate_id, option)
      setResolved(prev => new Set(prev).add(gate.gate_id))
    } finally {
      setResolving(prev => {
        const next = new Set(prev)
        next.delete(gate.gate_id)
        return next
      })
    }
  }

  const overlay: React.CSSProperties = {
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(0, 0, 0, 0.85)', zIndex: 1000,
    display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
    paddingTop: '5vh',
  }
  const modal: React.CSSProperties = {
    background: '#0a0a0a', color: '#e8e8e8', padding: '20px',
    borderRadius: '8px', maxWidth: '900px', width: '95%',
    maxHeight: '85vh', overflowY: 'auto',
    border: '1px solid #333', fontFamily: 'monospace',
  }
  const sevHeader: React.CSSProperties = {
    fontSize: '13px', fontWeight: 'bold', marginTop: '12px', marginBottom: '4px',
    paddingBottom: '4px', borderBottom: '1px solid #333',
  }

  return (
    <div style={overlay} onClick={onClose}>
      <div style={modal} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: '16px' }}>
            Batch Gate Review — {totalRemaining} pending
          </h2>
          <button onClick={onClose} style={{ background: 'none', border: '1px solid #444', color: '#aaa', padding: '4px 12px', cursor: 'pointer', fontFamily: 'inherit' }}>
            close
          </button>
        </div>
        <div style={{ fontSize: '11px', color: '#888', marginTop: '4px', marginBottom: '12px' }}>
          Per GP-167 attention discipline: review each gate's context before deciding. No silent batch-approve.
        </div>

        {totalRemaining === 0 && (
          <div style={{ padding: '40px', textAlign: 'center', color: '#888' }}>
            ✓ All gates resolved.
          </div>
        )}

        {(['critical', 'high', 'normal', 'low'] as Severity[]).map(sev => {
          const ownersInSev = groups[sev]
          const sevTotal = Object.values(ownersInSev).reduce((s, gs) => s + gs.length, 0)
          if (sevTotal === 0) return null
          return (
            <div key={sev}>
              <div style={sevHeader}>
                {SEVERITY_LABEL[sev]} ({sevTotal})
              </div>
              {Object.entries(ownersInSev).map(([owner, gs]) => (
                <div key={owner} style={{ marginBottom: '8px' }}>
                  <div style={{ fontSize: '11px', color: '#888', margin: '8px 0 4px' }}>
                    {owner} squad ({gs.length})
                  </div>
                  {gs.map(g => {
                    const isExpanded = expanded.has(g.gate_id)
                    const isResolving = resolving.has(g.gate_id)
                    const summary: string = (g as any).summary || (g as any).candidate?.intent || g.gate_id
                    const intent = (g as any).candidate?.intent || ''
                    return (
                      <div key={g.gate_id} style={{ border: '1px solid #222', borderRadius: '4px', marginBottom: '6px', padding: '8px', background: '#0e0e0e' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: '12px', fontWeight: 'bold' }}>
                              {intent.slice(0, 100) || g.gate_id}
                            </div>
                            <div style={{ fontSize: '10px', color: '#666', marginTop: '2px' }}>
                              {g.gate_id}
                            </div>
                          </div>
                          <button
                            onClick={() => toggleExpand(g.gate_id)}
                            style={{ background: 'none', border: '1px solid #333', color: '#aaa', padding: '2px 8px', cursor: 'pointer', fontSize: '11px', fontFamily: 'inherit' }}
                          >
                            {isExpanded ? 'hide' : 'context'}
                          </button>
                        </div>
                        {isExpanded && (
                          <pre style={{ fontSize: '11px', whiteSpace: 'pre-wrap', wordBreak: 'break-word', marginTop: '8px', padding: '8px', background: '#080808', borderRadius: '4px', color: '#bbb' }}>
                            {summary}
                          </pre>
                        )}
                        <div style={{ marginTop: '8px', display: 'flex', gap: '6px' }}>
                          <button
                            disabled={isResolving || !isExpanded}
                            onClick={() => handleResolve(g, 'approve')}
                            style={{ background: isExpanded ? '#16a34a' : '#0e2e1c', color: 'white', border: 'none', padding: '6px 12px', cursor: isExpanded ? 'pointer' : 'not-allowed', fontSize: '11px', fontFamily: 'inherit', borderRadius: '4px' }}
                            title={isExpanded ? '' : 'Lanier discipline — expand context first'}
                          >
                            ✅ Approve
                          </button>
                          <button
                            disabled={isResolving}
                            onClick={() => handleResolve(g, 'skip')}
                            style={{ background: '#444', color: 'white', border: 'none', padding: '6px 12px', cursor: 'pointer', fontSize: '11px', fontFamily: 'inherit', borderRadius: '4px' }}
                          >
                            ⏭ Skip
                          </button>
                          <button
                            disabled={isResolving}
                            onClick={() => handleResolve(g, 'stop')}
                            style={{ background: '#7f1d1d', color: 'white', border: 'none', padding: '6px 12px', cursor: 'pointer', fontSize: '11px', fontFamily: 'inherit', borderRadius: '4px' }}
                          >
                            🛑 Stop daemon
                          </button>
                          {isResolving && <span style={{ fontSize: '11px', color: '#888' }}>resolving…</span>}
                        </div>
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}
