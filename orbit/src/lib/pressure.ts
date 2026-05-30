/**
 * GP-168 pressure helpers (2026-04-27 addendum: now scoped to Tasks
 * and KRs, not standalone clock/budget objects).
 *
 * Compute the closure pressure (0–1+) for a Task (time + budget) or
 * a KR (measurement-overdue), classify into a band, and produce a
 * human-readable label. Used by ObjectiveTreePane and any row that
 * needs to show "how close is this to firing the daemon."
 */
import type { Task, KeyResult, Pressure } from '../types/org'

const SECOND = 1000
const MINUTE = 60 * SECOND
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

function band(pct: number, warnAt: number, escalateAt: number): Pressure['band'] {
  if (pct >= 1.0) return 'critical'
  if (pct >= escalateAt) return 'urgent'
  if (pct >= warnAt) return 'warn'
  return 'cool'
}

function formatDuration(ms: number): string {
  const abs = Math.abs(ms)
  if (abs < MINUTE) return `${Math.round(ms / SECOND)}s`
  if (abs < HOUR) return `${Math.round(ms / MINUTE)}m`
  if (abs < DAY) {
    const h = Math.floor(abs / HOUR)
    const m = Math.round((abs % HOUR) / MINUTE)
    return m > 0 ? `${h}h ${m}m` : `${h}h`
  }
  const d = Math.floor(abs / DAY)
  const h = Math.round((abs % DAY) / HOUR)
  return h > 0 ? `${d}d ${h}h` : `${d}d`
}

export function taskTimePressure(task: Task, now: Date = new Date()): Pressure | null {
  if (!task.created_utc || !task.closure_deadline) return null
  const created = Date.parse(task.created_utc)
  const expires = Date.parse(task.closure_deadline)
  const total = expires - created
  if (total <= 0) return { pct: 1.0, band: 'critical', remaining_label: 'expired' }
  const elapsed = now.getTime() - created
  const pct = Math.max(0, elapsed / total)
  const remainingMs = expires - now.getTime()
  const remaining_label = remainingMs <= 0
    ? `expired ${formatDuration(-remainingMs)} ago`
    : `${formatDuration(remainingMs)} left`
  const warnAt = task.warn_at_pct ?? 0.7
  const escalateAt = task.escalate_at_pct ?? 0.9
  return { pct, band: band(pct, warnAt, escalateAt), remaining_label }
}

export function taskBudgetPressure(task: Task): Pressure | null {
  const cap = task.budget_cap_usd
  const spent = task.budget_spent_usd ?? 0
  if (cap == null || cap <= 0) return null
  const pct = spent / cap
  const remaining = cap - spent
  const remaining_label = remaining <= 0
    ? `over by $${(-remaining).toFixed(2)}`
    : `$${remaining.toFixed(2)} left`
  return { pct, band: band(pct, 0.8, 0.95), remaining_label }
}

export function krOverduePressure(kr: KeyResult, now: Date = new Date()): Pressure | null {
  const last = kr.last_measured_utc || kr.created_utc
  if (!last) return null
  const lastT = Date.parse(last)
  const ageDays = (now.getTime() - lastT) / DAY
  const threshold = kr.review_overdue_threshold_days ?? 14
  if (threshold <= 0) return null
  const pct = ageDays / threshold
  const remaining_label = ageDays >= threshold
    ? `overdue ${Math.round(ageDays - threshold)}d`
    : `${Math.round(threshold - ageDays)}d to review`
  return { pct, band: band(pct, 0.7, 0.95), remaining_label }
}

/** Pick the worst (max pct, worst band) of two pressures, or the other if one is null. */
export function combinePressure(a: Pressure | null, b: Pressure | null): Pressure | null {
  if (!a) return b
  if (!b) return a
  const order: Pressure['band'][] = ['cool', 'warn', 'urgent', 'critical']
  const aIdx = order.indexOf(a.band)
  const bIdx = order.indexOf(b.band)
  return aIdx >= bIdx ? a : b
}

/** Color tokens for each band — matches Orbit's existing palette. */
export const BAND_COLOR: Record<Pressure['band'], { fill: string; text: string; border: string }> = {
  cool:     { fill: '#1e2030', text: '#6b7394', border: '#1e2030' },
  warn:     { fill: 'rgba(245,158,11,0.18)', text: '#f59e0b', border: 'rgba(245,158,11,0.4)' },
  urgent:   { fill: 'rgba(239,68,68,0.20)', text: '#ef4444', border: 'rgba(239,68,68,0.5)' },
  critical: { fill: 'rgba(239,68,68,0.35)', text: '#ffd1d1', border: '#ef4444' },
}
