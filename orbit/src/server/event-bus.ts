// Licensed under Business Source License 1.1 — see LICENSE-BSL
/**
 * Event Bus — the communication layer for human-AI symbiotic orgs.
 *
 * Every action in the system is an immutable Event. Events are:
 *   - Written to org/events/ as append-only JSONL (the event store)
 *   - Broadcast to all connected clients via WebSocket (real-time)
 *   - Routed to subscribers based on event type + target role
 *   - Persisted in git (audit trail)
 *
 * This replaces:
 *   - org/gates/pending/ and org/gates/resolved/ (now gate.proposed / gate.resolved events)
 *   - org/directives/ (now directive.issued events)
 *   - org/controls/ (now control.issued events)
 *   - Telegram inbound (now directive.issued from telegram source)
 *
 * Architecture:
 *   Event producers (dashboard, telegram, daemon, agents)
 *       ↓
 *   Event store (org/events/YYYY-MM-DD.jsonl, append-only)
 *       ↓
 *   Event bus (in-memory, WebSocket broadcast)
 *       ↓
 *   Subscribers (dashboard view, daemon tick, telegram bot, dead letter queue)
 *
 * This is Event Sourcing (Fowler) + Content-Based Routing (Hohpe) +
 * Lamport Timestamps (Lamport) in one module.
 *
 * Why not Kafka/Redis/NATS? Because the invariant is: git is the
 * system of record. Events must be files in a git repo. Any external
 * broker is a cache, not a source of truth. This module IS the broker,
 * backed by the filesystem.
 */

import { readFileSync, appendFileSync, mkdirSync, existsSync, readdirSync } from 'fs'
import { join } from 'path'
import { WebSocket } from 'ws'

// ── Event types ────────────────────────────────────────────────────

export interface Event {
  id: string                    // UUID
  timestamp: string             // ISO 8601
  lamport: number               // Lamport logical clock (monotonic per source)
  source: string                // who produced: 'dashboard' | 'daemon:manager' | 'telegram' | 'agent:claude'
  type: string                  // event type (see catalog below)
  target_role?: string          // content-based routing: which role should see this
  payload: Record<string, any>  // type-specific data
  ttl_minutes?: number          // auto-expire (for controls like PAUSE)
}

/**
 * Event type catalog:
 *
 * GOVERNANCE (slow layer):
 *   mandate.updated      — a mandate file changed
 *   role.created         — new role added
 *   assignment.changed   — role assignment modified
 *
 * COORDINATION (working layer):
 *   gate.proposed        — agent requests human approval
 *   gate.resolved        — human approves/rejects
 *   directive.issued     — human sends instruction to agent
 *   directive.consumed   — agent acknowledges directive
 *   task.claimed         — agent claims a task (membrane exclusion)
 *   task.released        — agent releases a task
 *   session.opened       — agent session started
 *   session.closed       — agent session ended
 *
 * SIGNALS (fast layer):
 *   damage.emitted       — something went wrong
 *   damage.resolved      — damage signal cleared
 *   control.issued       — STOP/PAUSE/RESUME
 *   audit.fired          — M-form alignment audit triggered
 *   audit.result         — audit completed
 *
 * WORK DISCOVERY:
 *   work.discovered      — daemon found a candidate
 *   work.proposed        — candidate proposed to human
 *   work.approved        — human approved execution
 *   work.completed       — execution finished
 *   work.failed          — execution failed
 *
 * PREFERENCE:
 *   preference.updated   — human preference model changed
 *   attention.spent      — human governance time tracked
 */

// ── Event store ────────────────────────────────────────────────────

export class EventStore {
  private dir: string
  private lamportClock: number = 0
  private subscribers: Map<string, Set<(event: Event) => void>> = new Map()
  private wsClients: Set<WebSocket> = new Set()

  constructor(orgDir: string) {
    this.dir = join(orgDir, 'events')
    mkdirSync(this.dir, { recursive: true })
    this.lamportClock = this.recoverClock()
  }

  /** Recover Lamport clock from latest event file */
  private recoverClock(): number {
    try {
      const files = readdirSync(this.dir).filter(f => f.endsWith('.jsonl')).sort()
      if (files.length === 0) return 0
      const lastFile = join(this.dir, files[files.length - 1])
      const lines = readFileSync(lastFile, 'utf-8').trim().split('\n').filter(Boolean)
      if (lines.length === 0) return 0
      const lastEvent = JSON.parse(lines[lines.length - 1]) as Event
      return lastEvent.lamport + 1
    } catch { return 0 }
  }

  /** Emit an event — persists to file + broadcasts to subscribers + WebSocket */
  emit(event: Omit<Event, 'id' | 'lamport' | 'timestamp'>): Event {
    const full: Event = {
      ...event,
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      lamport: this.lamportClock++,
    }

    // Persist to daily JSONL file
    const dateKey = full.timestamp.slice(0, 10)  // YYYY-MM-DD
    const filePath = join(this.dir, `${dateKey}.jsonl`)
    appendFileSync(filePath, JSON.stringify(full) + '\n')

    // Route to type subscribers
    const typeHandlers = this.subscribers.get(full.type)
    if (typeHandlers) {
      for (const handler of typeHandlers) {
        try { handler(full) } catch {}
      }
    }

    // Route to wildcard subscribers
    const wildcardHandlers = this.subscribers.get('*')
    if (wildcardHandlers) {
      for (const handler of wildcardHandlers) {
        try { handler(full) } catch {}
      }
    }

    // Broadcast to WebSocket clients
    const msg = JSON.stringify({ type: 'event', data: full })
    for (const ws of this.wsClients) {
      if (ws.readyState === WebSocket.OPEN) {
        try { ws.send(msg) } catch {}
      }
    }

    return full
  }

  /** Subscribe to events by type. Use '*' for all events. */
  on(eventType: string, handler: (event: Event) => void): () => void {
    if (!this.subscribers.has(eventType)) {
      this.subscribers.set(eventType, new Set())
    }
    this.subscribers.get(eventType)!.add(handler)
    return () => this.subscribers.get(eventType)?.delete(handler)
  }

  /** Register a WebSocket client for real-time broadcast */
  addClient(ws: WebSocket): void {
    this.wsClients.add(ws)
    ws.on('close', () => this.wsClients.delete(ws))
  }

  /** Read recent events (for dashboard initial load) */
  recent(limit: number = 100): Event[] {
    const events: Event[] = []
    const files = readdirSync(this.dir).filter(f => f.endsWith('.jsonl')).sort().reverse()
    for (const file of files) {
      if (events.length >= limit) break
      try {
        const lines = readFileSync(join(this.dir, file), 'utf-8').trim().split('\n').filter(Boolean)
        for (const line of lines.reverse()) {
          if (events.length >= limit) break
          try { events.push(JSON.parse(line)) } catch {}
        }
      } catch {}
    }
    return events.reverse() // oldest first
  }

  /** Read events for a specific role (content-based routing) */
  forRole(roleId: string, limit: number = 50): Event[] {
    return this.recent(500).filter(e =>
      !e.target_role || e.target_role === roleId
    ).slice(-limit)
  }

  /** Dead letter queue: events with target_role that no daemon has consumed */
  deadLetters(maxAgeMinutes: number = 60): Event[] {
    const cutoff = new Date(Date.now() - maxAgeMinutes * 60000).toISOString()
    return this.recent(500).filter(e =>
      e.target_role &&
      e.timestamp > cutoff &&
      !['gate.resolved', 'directive.consumed', 'damage.resolved', 'work.completed'].includes(e.type)
    )
  }
}
