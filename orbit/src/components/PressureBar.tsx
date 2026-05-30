/**
 * GP-168 pressure indicator.
 *
 * Visual closure-clock or budget-burn bar. Colored by band:
 *   cool   — gray (<warn threshold)
 *   warn   — amber (>=warn, <escalate)
 *   urgent — red (>=escalate, <100%)
 *   critical — red filled (>=100% expired/exhausted)
 *
 * Used by DamageSignalFeed, ClosureClockPane, and any future
 * row that needs to communicate "how close is this to being
 * forced shut by the daemon."
 */
import type { Pressure } from '../types/org'
import { BAND_COLOR } from '../lib/pressure'

interface Props {
  pressure: Pressure
  width?: number       // px, default 80
  height?: number      // px, default 6
  label?: 'remaining' | 'pct' | 'none'
  inline?: boolean     // if true, render label to the right; else below
}

export function PressureBar({ pressure, width = 80, height = 6, label = 'remaining', inline = true }: Props) {
  const colors = BAND_COLOR[pressure.band]
  const fillPct = Math.min(100, Math.round(pressure.pct * 100))
  const labelText = label === 'pct'
    ? `${fillPct}%`
    : label === 'remaining'
    ? pressure.remaining_label
    : ''

  const bar = (
    <div
      style={{
        width,
        height,
        background: colors.fill,
        border: `1px solid ${colors.border}`,
        borderRadius: 3,
        overflow: 'hidden',
        position: 'relative',
      }}
      title={`${fillPct}% — ${pressure.remaining_label}`}
    >
      <div
        style={{
          width: `${fillPct}%`,
          height: '100%',
          background: colors.border,
          transition: 'width 0.4s ease',
        }}
      />
    </div>
  )

  if (label === 'none') return bar

  return (
    <div
      style={{
        display: inline ? 'inline-flex' : 'flex',
        flexDirection: inline ? 'row' : 'column',
        alignItems: inline ? 'center' : 'flex-start',
        gap: inline ? 8 : 4,
      }}
    >
      {bar}
      <span style={{ fontSize: 10, color: colors.text, fontFamily: 'ui-monospace, monospace' }}>
        {labelText}
      </span>
    </div>
  )
}
