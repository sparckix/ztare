/**
 * Right pane: fast-layer damage signal feed + attention budget.
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

      {signals.slice(0, 30).map((s, i) => (
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
          <div style={{ fontSize: 9, color: '#6b7394', fontFamily: 'monospace' }}>
            {s.timestamp_utc}
          </div>
          <div style={{ fontWeight: 600, margin: '2px 0', color: s.resolved ? '#34d399' : '#e8eaf0' }}>
            {s.resolved ? '✓' : SEVERITY_ICONS[s.severity] || '●'} {s.kind}
          </div>
          <div style={{ color: '#6b7394' }}>
            {s.detail.slice(0, 150)}{s.detail.length > 150 ? '...' : ''}
          </div>
        </div>
      ))}

      {signals.length === 0 && (
        <div style={{ color: '#4a5070', fontSize: 12, textAlign: 'center', padding: 20 }}>
          No damage signals. System healthy.
        </div>
      )}
    </div>
  )
}
