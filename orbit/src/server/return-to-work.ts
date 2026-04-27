// Licensed under Business Source License 1.1 — see LICENSE-BSL
/**
 * Return-to-Work Summary Generator (Nardi, GP-167 Turn 3)
 *
 * When the principal opens the dashboard after a break, this module
 * generates a 30-second briefing answering three questions:
 *   1. What broke or needs me?
 *   2. What's the best result since I last checked?
 *   3. What decisions are waiting?
 *
 * Format: 3 bullet points max, then drill in.
 *
 * Reads from the event store, not from scattered files. The event
 * stream IS the organizational memory.
 */

import type { Event, EventStore } from './event-bus.js'

export interface ReturnToWorkSummary {
  generated_at: string
  since: string  // last human activity timestamp
  needs_you: string[]       // what broke or needs approval
  best_result: string | null  // highest-signal positive event
  waiting: string[]         // pending gates / directives
  attention_spent_today_min: number
}

export function generateReturnToWork(
  store: EventStore,
  lastActivity: string,  // ISO timestamp of last human interaction
): ReturnToWorkSummary {
  const since = new Date(lastActivity)
  const events = store.recent(200).filter(e =>
    new Date(e.timestamp) > since
  )

  // 1. What broke or needs me?
  const needs: string[] = []

  const unresolvedDamage = events.filter(e =>
    e.type === 'damage.emitted' && e.payload?.severity === 'critical'
  )
  for (const d of unresolvedDamage.slice(0, 3)) {
    needs.push(`🔴 ${d.payload?.kind || 'damage'}: ${(d.payload?.detail || '').slice(0, 80)}`)
  }

  const pendingGates = events.filter(e =>
    e.type === 'gate.proposed' &&
    !events.some(r => r.type === 'gate.resolved' && r.payload?.gate_id === e.payload?.gate_id)
  )
  for (const g of pendingGates.slice(0, 3)) {
    needs.push(`⚖ Gate pending: ${(g.payload?.description || g.payload?.gate_id || '').slice(0, 80)}`)
  }

  const reEscalated = events.filter(e => e.type === 'gate.re_escalated')
  for (const r of reEscalated.slice(0, 2)) {
    needs.push(`⚠ Re-escalated (you didn't see it): ${(r.payload?.gate_id || '').slice(0, 60)}`)
  }

  // 2. What's the best result?
  let bestResult: string | null = null
  const completions = events.filter(e =>
    e.type === 'work.completed' && e.payload?.success
  )
  if (completions.length > 0) {
    const best = completions[completions.length - 1]
    bestResult = `✅ ${(best.payload?.task || '').slice(0, 100)}`
  }

  // Also check for champion promotions in experiment runs
  const champions = events.filter(e =>
    e.payload?.champion_score && e.payload.champion_score > 0
  )
  if (champions.length > 0) {
    const best = champions.reduce((a, b) =>
      (a.payload?.champion_score || 0) > (b.payload?.champion_score || 0) ? a : b
    )
    const score = best.payload?.champion_score
    const project = best.payload?.project || ''
    if (!bestResult || score > 80) {
      bestResult = `🏆 Champion score ${score} on ${project}`
    }
  }

  // 3. What decisions are waiting?
  const waiting: string[] = []
  for (const g of pendingGates) {
    waiting.push(`Gate: ${g.payload?.gate_id || 'unknown'}`)
  }
  const pendingDirectives = events.filter(e =>
    e.type === 'work.proposed' &&
    !events.some(a => a.type === 'work.approved' && a.payload?.candidate_id === e.payload?.candidate_id)
  )
  for (const p of pendingDirectives.slice(0, 3)) {
    waiting.push(`Proposal: ${(p.payload?.intent || '').slice(0, 60)}`)
  }

  // Attention tracking
  const todayStart = new Date()
  todayStart.setHours(0, 0, 0, 0)
  const humanEvents = store.recent(500).filter(e =>
    e.source === 'dashboard' &&
    new Date(e.timestamp) > todayStart
  )
  // Rough estimate: each human event = ~2 min of attention
  const attentionMin = humanEvents.length * 2

  return {
    generated_at: new Date().toISOString(),
    since: lastActivity,
    needs_you: needs.slice(0, 3),
    best_result: bestResult,
    waiting: waiting.slice(0, 3),
    attention_spent_today_min: attentionMin,
  }
}
