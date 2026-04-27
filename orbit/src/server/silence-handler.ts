// Licensed under Business Source License 1.1 — see LICENSE-BSL
/**
 * Silence-as-Consent Handler (Suchman, GP-167 Turn 3)
 *
 * Distinguishes "human approved by inaction" from "human did not see."
 * Every gate.proposed event starts a timeout. When it expires:
 *
 *   - If attention_budget shows the human was active during the window
 *     → classify as "approved_by_inaction" (human saw it, chose not to act)
 *   - If no dashboard/telegram activity during the window
 *     → classify as "not_seen" and re-escalate with higher priority
 *
 * This prevents the death spiral: silence → self-authorization → drift.
 */

import type { Event, EventStore } from './event-bus.js'

interface PendingGate {
  event: Event
  proposed_at: number   // epoch ms
  timeout_ms: number
  escalation_count: number
}

export class SilenceHandler {
  private pending: Map<string, PendingGate> = new Map()
  private lastHumanActivity: number = 0
  private store: EventStore

  constructor(store: EventStore, defaultTimeoutMinutes: number = 30) {
    this.store = store
    const timeoutMs = defaultTimeoutMinutes * 60 * 1000

    // Watch for gate proposals
    store.on('gate.proposed', (event) => {
      this.pending.set(event.id, {
        event,
        proposed_at: Date.now(),
        timeout_ms: timeoutMs,
        escalation_count: 0,
      })
    })

    // Watch for gate resolutions (clear pending)
    store.on('gate.resolved', (event) => {
      const gateId = event.payload?.gate_id
      for (const [id, pg] of this.pending) {
        if (pg.event.payload?.gate_id === gateId) {
          this.pending.delete(id)
        }
      }
    })

    // Track human activity (any event from dashboard or telegram source)
    store.on('*', (event) => {
      if (event.source === 'dashboard' || event.source === 'telegram') {
        this.lastHumanActivity = Date.now()
      }
    })

    // Check timeouts every minute
    setInterval(() => this.checkTimeouts(), 60 * 1000)
  }

  private checkTimeouts(): void {
    const now = Date.now()

    for (const [id, pg] of this.pending) {
      if (now - pg.proposed_at < pg.timeout_ms) continue

      // Timeout expired — classify the silence
      const humanWasActive = (this.lastHumanActivity > pg.proposed_at)

      if (humanWasActive) {
        // Human was active but didn't respond → approved by inaction
        this.store.emit({
          source: 'silence_handler',
          type: 'gate.silence_classified',
          target_role: pg.event.target_role,
          payload: {
            gate_id: pg.event.payload?.gate_id,
            original_event_id: id,
            classification: 'approved_by_inaction',
            human_was_active: true,
            elapsed_minutes: Math.round((now - pg.proposed_at) / 60000),
            note: 'Human was active during timeout window but did not respond. Classified as implicit approval. Logged for audit.',
          },
        })
        this.pending.delete(id)

      } else if (pg.escalation_count < 2) {
        // Human was NOT active → re-escalate
        pg.escalation_count++
        pg.proposed_at = now  // reset timer
        pg.timeout_ms = pg.timeout_ms * 0.5  // shorter timeout on re-escalation

        this.store.emit({
          source: 'silence_handler',
          type: 'gate.re_escalated',
          target_role: pg.event.target_role,
          payload: {
            gate_id: pg.event.payload?.gate_id,
            original_event_id: id,
            classification: 'not_seen',
            escalation_count: pg.escalation_count,
            note: 'Human was NOT active during timeout window. Re-escalating with higher priority.',
          },
        })

      } else {
        // Max escalations reached → defer
        this.store.emit({
          source: 'silence_handler',
          type: 'gate.deferred',
          target_role: pg.event.target_role,
          payload: {
            gate_id: pg.event.payload?.gate_id,
            original_event_id: id,
            classification: 'deferred_max_escalation',
            note: 'Human did not respond after 2 re-escalations. Gate deferred to next active session.',
          },
        })
        this.pending.delete(id)
      }
    }
  }

  /** Get current pending gates with time remaining */
  status(): Array<{ gate_id: string; elapsed_min: number; timeout_min: number; escalations: number }> {
    const now = Date.now()
    return Array.from(this.pending.values()).map(pg => ({
      gate_id: pg.event.payload?.gate_id || pg.event.id,
      elapsed_min: Math.round((now - pg.proposed_at) / 60000),
      timeout_min: Math.round(pg.timeout_ms / 60000),
      escalations: pg.escalation_count,
    }))
  }
}
