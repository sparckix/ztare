/**
 * Right pane: fast-layer damage signal feed + attention budget.
 *
 * Renders any damage signal kind generically; signal *families* (per
 * GP-231/232 + C3) get a kind-prefix icon so a reviewer can scan the
 * feed and see at a glance which subsystem is unhealthy.
 */
import type { DamageSignal } from '../types/org'

interface Props {
  signals: DamageSignal[]
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  warn: '#f59e0b',
  info: '#4f8ff7',
}

const SEVERITY_ICONS: Record<string, string> = {
  critical: '🔴',
  warn: '🟡',
  info: '🔵',
}

/**
 * Signal-family icons. Matched by prefix on signal.kind. The first
 * matching prefix wins; signals that don't match any family fall back
 * to the severity icon.
 *
 * Sources:
 *   GP-231 MCP bridge: mcp_*
 *   GP-232 Phase A obligation lifecycle: agent_obligation_*
 *   GP-232 Phase B artifact deps: predicate_hash_drift, artifact_*
 *   GP-232 Phase C saga: saga_*
 *   C3 EU AI Act gate: eu_ai_act_*
 *   GP-195 debate runner: debate_*
 *   GP-228 portfolio: portfolio_*
 *   GP-128 daemon: agent_utilization_*, mandate_drift, daemon_*
 */
const FAMILY_PREFIXES: Array<[string, string, string]> = [
  // [prefix, icon, label]
  ['mcp_call_failed', '🔌❌', 'MCP'],
  ['mcp_call_dispatched_but_unverified', '🔌⏳', 'MCP'],
  ['mcp_response_unprojectable', '🔌🚫', 'MCP'],
  ['mcp_server_revoked', '🔌🚨', 'MCP'],
  ['external_observation_diverged', '🌐⚖️', 'MCP'],
  ['mcp_', '🔌', 'MCP'],
  ['capability_violation_attempt', '🔐🚨', 'CAPABILITY'],
  ['capability_', '🔐', 'CAPABILITY'],
  ['agent_obligation_', '📋', 'OBLIGATION'],
  ['saga_compensation_unfulfilled', '↩️🚨', 'SAGA'],
  ['saga_compensation_emitted', '↩️', 'SAGA'],
  ['saga_', '↩️', 'SAGA'],
  ['predicate_hash_drift', '🔑⚠️', 'DEPENDENCY'],
  ['artifact_', '📦', 'DEPENDENCY'],
  ['eu_ai_act_mapping_missing', '🇪🇺❌', 'EU-AI-ACT'],
  ['eu_ai_act_mapping_stale', '🇪🇺⚠️', 'EU-AI-ACT'],
  ['eu_ai_act_mapping_freshness_review_due', '🇪🇺📅', 'EU-AI-ACT'],
  ['eu_ai_act_', '🇪🇺', 'EU-AI-ACT'],
  ['debate_budget_exhausted', '💬💸', 'DEBATE'],
  ['debate_state_stuck', '💬🔒', 'DEBATE'],
  ['debate_mono_family', '💬⚠️', 'DEBATE'],
  ['debate_', '💬', 'DEBATE'],
  ['agent_utilization_', '⏱️', 'CAPACITY'],
  ['mandate_drift', '📜', 'MANDATE'],
  ['mandate_', '📜', 'MANDATE'],
  ['autonomous_scope_refused', '🚫', 'AUTH'],
  ['portfolio_', '🗂️', 'PORTFOLIO'],
]

function familyFor(kind: string): { icon: string; label: string } | null {
  for (const [prefix, icon, label] of FAMILY_PREFIXES) {
    if (kind === prefix || kind.startsWith(prefix)) {
      return { icon, label }
    }
  }
  return null
}

export function DamageSignalFeed({ signals }: Props) {
  const unresolved = signals.filter(s => !s.resolved)
  const resolved = signals.filter(s => s.resolved)

  return (
    <div style={{ padding: 16 }}>
      {/* Attention budget (Raskin) */}
      <div style={{
        background: '#161822',
        borderRadius: 8,
        padding: '10px 12px',
        marginBottom: 16,
      }}>
        <div style={{ fontSize: 10, color: '#6b7394', textTransform: 'uppercase', letterSpacing: 1 }}>
          Today's Attention Budget
        </div>
        <div style={{
          height: 6, background: '#1a1d2e', borderRadius: 3, marginTop: 6, overflow: 'hidden',
        }}>
          <div style={{
            height: '100%', width: `${Math.min(unresolved.length * 12, 100)}%`,
            background: unresolved.length > 6 ? '#ef4444' : unresolved.length > 3 ? '#f59e0b' : '#34d399',
            borderRadius: 3, transition: 'width 0.5s',
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#6b7394', marginTop: 4 }}>
          <span>{unresolved.length} unresolved signals</span>
          <span>{resolved.length} resolved</span>
        </div>
      </div>

      <h2 style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.5, color: '#6b7394', marginBottom: 12 }}>
        ⚡ Damage Signals
      </h2>

      {signals.slice(0, 30).map((s, i) => {
        const fam = familyFor(s.kind)
        const familyIcon = s.resolved
          ? '✓'
          : (fam ? fam.icon : (SEVERITY_ICONS[s.severity] || '●'))
        return (
        <div key={i} style={{
          padding: '10px 12px',
          borderRadius: 8,
          marginBottom: 6,
          fontSize: 11,
          lineHeight: 1.4,
          borderLeft: `3px solid ${s.resolved ? '#34d399' : (SEVERITY_COLORS[s.severity] || '#1e2030')}`,
          background: '#161822',
          opacity: s.resolved ? 0.5 : 1,
        }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            fontSize: 9, color: '#6b7394', fontFamily: 'monospace',
          }}>
            <span>{s.timestamp_utc}</span>
            {fam && !s.resolved && (
              <span style={{
                fontFamily: 'inherit', fontSize: 8, padding: '1px 6px',
                background: '#1e2030', borderRadius: 8, color: '#8a92b3',
                letterSpacing: 0.5,
              }}>{fam.label}</span>
            )}
          </div>
          <div style={{ fontWeight: 600, margin: '2px 0', color: s.resolved ? '#34d399' : '#e8eaf0' }}>
            {familyIcon} {s.kind}
          </div>
          <div style={{ color: '#6b7394' }}>
            {s.detail.slice(0, 150)}{s.detail.length > 150 ? '...' : ''}
          </div>
        </div>
        )
      })}

      {signals.length === 0 && (
        <div style={{ color: '#4a5070', fontSize: 12, textAlign: 'center', padding: 20 }}>
          No damage signals. System healthy.
        </div>
      )}
    </div>
  )
}
