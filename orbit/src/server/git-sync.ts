// Licensed under Business Source License 1.1 — see LICENSE-BSL
/**
 * Git-sync daemon — reads org/ directory, serves state via HTTP + WebSocket.
 *
 * The dashboard's backend. Watches the org/ directory for changes,
 * parses YAML/JSON files into typed OrgState, and serves it:
 *   - GET /api/state → full OrgState JSON
 *   - WebSocket /ws → push updates on file changes
 *
 * The daemon NEVER writes to org/ — it is read-only. All mutations
 * go through git (CLI or the dashboard's mutation endpoint, which
 * creates commits). This preserves the invariant: git is the system
 * of record, the dashboard is a projection.
 */

import { readFileSync, readdirSync, existsSync, statSync, writeFileSync, mkdirSync } from 'fs'
import { join, resolve } from 'path'
import { createServer } from 'http'
import { parse as parseYaml } from 'yaml'
import { WebSocketServer, WebSocket } from 'ws'
import { watch } from 'chokidar'

import type {
  OrgState, Member, Role, Assignment, Session, DamageSignal, WorkCandidate
} from '../types/org.js'

const REPO_ROOT = resolve(import.meta.dirname, '..', '..', '..')
const ORG_DIR = join(REPO_ROOT, 'org')
const PORT = 3001

// ── YAML/JSON file readers ─────────────────────────────────────────

function readYaml<T>(path: string): T | null {
  try {
    return parseYaml(readFileSync(path, 'utf-8')) as T
  } catch { return null }
}

function readJson<T>(path: string): T | null {
  try {
    return JSON.parse(readFileSync(path, 'utf-8')) as T
  } catch { return null }
}

// ── Org state builder ──────────────────────────────────────────────

function buildState(): OrgState {
  const members: Member[] = []
  const roles: Role[] = []
  const sessions: Session[] = []
  const damageSignals: DamageSignal[] = []

  // Members
  const membersDir = join(ORG_DIR, 'members')
  if (existsSync(membersDir)) {
    for (const f of readdirSync(membersDir).filter(f => f.endsWith('.yaml'))) {
      const m = readYaml<any>(join(membersDir, f))
      if (m) members.push({
        member_id: m.member_id,
        kind: m.kind,
        display_name: m.display_name,
        description: m.description || '',
        substrates: m.substrates || [],
        capabilities: m.capabilities || [],
      })
    }
  }

  // Roles
  const rolesDir = join(ORG_DIR, 'roles')
  if (existsSync(rolesDir)) {
    for (const f of readdirSync(rolesDir).filter(f => f.endsWith('.yaml'))) {
      const r = readYaml<any>(join(rolesDir, f))
      if (r) roles.push({
        role_id: r.role_id,
        role_class: r.role_class || r.role_id,
        description: r.description || '',
        authorized_paths: r.authorized_paths || [],
        forbidden_paths: r.forbidden_paths || [],
        delegates_to: r.delegates_to || [],
        escalates_to: r.escalates_to || [],
        budget: r.budget || { daily_cap_usd: 0, session_cap_usd: 0, single_action_cap_usd: 0, warn_threshold_frac: 0.8 },
        mandate_path: r.mandate_path || '',
      })
    }
  }

  // Assignments
  const assignmentsFile = join(ORG_DIR, 'assignments.yaml')
  const assignmentsRaw = readYaml<any>(assignmentsFile)
  const assignments: Assignment[] = (assignmentsRaw?.assignments || []).map((a: any) => ({
    member: a.member,
    role: a.role,
    substrate: a.substrate,
    is_primary: a.is_primary ?? true,
    valid_from: a.valid_from,
    valid_until: a.valid_until,
    notes: a.notes || '',
  }))

  // Sessions (walk org/sessions/**/meta.json)
  const sessionsDir = join(ORG_DIR, 'sessions')
  if (existsSync(sessionsDir)) {
    walkDir(sessionsDir, (path) => {
      if (path.endsWith('meta.json')) {
        const s = readJson<any>(path)
        if (s) sessions.push({
          session_id: s.session_id,
          member_id: s.member_id,
          role_id: s.role_id,
          substrate: s.substrate,
          start_utc: s.start_utc,
          end_utc: s.end_utc,
          mandate_hash: s.mandate_hash || '',
        })
      }
    })
  }

  // Damage signals (walk org/signals/damage/)
  const damageDir = join(ORG_DIR, 'signals', 'damage')
  if (existsSync(damageDir)) {
    walkDir(damageDir, (path) => {
      if (path.endsWith('.json') && !path.includes('_reason')) {
        const d = readJson<any>(path)
        if (d) damageSignals.push({
          timestamp_utc: d.timestamp_utc,
          source: d.source || '',
          kind: d.kind || 'unknown',
          detail: d.detail || '',
          session_id: d.session_id || '',
          severity: d.severity || 'info',
          resolved: path.includes('_cleared'),
        })
      }
    })
  }

  // Sort damage signals newest first
  damageSignals.sort((a, b) => b.timestamp_utc.localeCompare(a.timestamp_utc))

  return {
    members,
    roles,
    assignments,
    sessions,
    damage_signals: damageSignals.slice(0, 50), // last 50
    work_candidates: [], // populated by work_discovery.py call
    last_sync: new Date().toISOString(),
  }
}

function walkDir(dir: string, cb: (path: string) => void) {
  try {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name)
      if (entry.isDirectory()) walkDir(full, cb)
      else cb(full)
    }
  } catch { /* permission or broken symlink */ }
}

// ── HTTP server ────────────────────────────────────────────────────

let cachedState: OrgState = buildState()

const server = createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Headers', '*')

  if (req.method === 'OPTIONS') {
    res.writeHead(204)
    res.end()
    return
  }

  if (req.url === '/api/state') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(cachedState))
    return
  }

  if (req.url === '/api/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ ok: true, last_sync: cachedState.last_sync }))
    return
  }

  // ── ACTION ENDPOINTS (write to org/) ──────────────────────────────

  // Gate approval: POST /api/gate/resolve
  if (req.url === '/api/gate/resolve' && req.method === 'POST') {
    let body = ''
    req.on('data', chunk => { body += chunk })
    req.on('end', () => {
      try {
        const { gate_id, verdict, reason } = JSON.parse(body)
        const ts = new Date().toISOString().replace(/[:.]/g, '-')
        const outPath = join(ORG_DIR, 'gates', 'resolved', `${ts}_${gate_id}.json`)
        
        mkdirSync(join(ORG_DIR, 'gates', 'resolved'), { recursive: true })
        writeFileSync(outPath, JSON.stringify({
          gate_id, verdict, reason,
          resolved_by: 'dashboard',
          resolved_utc: new Date().toISOString(),
        }, null, 2))
        res.writeHead(200, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ ok: true, path: outPath }))
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ ok: false, error: String(e) }))
      }
    })
    return
  }

  // Directive: POST /api/directive
  if (req.url === '/api/directive' && req.method === 'POST') {
    let body = ''
    req.on('data', chunk => { body += chunk })
    req.on('end', () => {
      try {
        const { target_role, message } = JSON.parse(body)
        const ts = new Date().toISOString().replace(/[:.]/g, '-')
        const outDir = join(ORG_DIR, 'directives')
        
        mkdirSync(outDir, { recursive: true })
        writeFileSync(join(outDir, `${ts}_${target_role}.json`), JSON.stringify({
          target_role, message,
          from: 'principal',
          created_utc: new Date().toISOString(),
          consumed: false,
        }, null, 2))
        res.writeHead(200, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ ok: true }))
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ ok: false, error: String(e) }))
      }
    })
    return
  }

  // Control: POST /api/control (STOP/PAUSE/RESUME)
  if (req.url === '/api/control' && req.method === 'POST') {
    let body = ''
    req.on('data', chunk => { body += chunk })
    req.on('end', () => {
      try {
        const { target_role, action } = JSON.parse(body)
        if (!['STOP', 'PAUSE', 'RESUME'].includes(action)) {
          res.writeHead(400)
          res.end(JSON.stringify({ ok: false, error: 'action must be STOP, PAUSE, or RESUME' }))
          return
        }
        const outDir = join(ORG_DIR, 'controls')
        
        mkdirSync(outDir, { recursive: true })
        writeFileSync(join(outDir, `${target_role}.json`), JSON.stringify({
          action, target_role,
          issued_by: 'principal',
          issued_utc: new Date().toISOString(),
        }, null, 2))
        res.writeHead(200, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ ok: true, action, target_role }))
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ ok: false, error: String(e) }))
      }
    })
    return
  }

  // Pending gates: GET /api/gates/pending
  if (req.url === '/api/gates/pending') {
    const pendingDir = join(ORG_DIR, 'gates', 'pending')
    const gates: any[] = []
    if (existsSync(pendingDir)) {
      walkDir(pendingDir, (path) => {
        if (path.endsWith('.json')) {
          const g = readJson<any>(path)
          if (g) gates.push(g)
        }
      })
    }
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(gates))
    return
  }

  res.writeHead(404)
  res.end('Not found')
})

// ── WebSocket for push updates ─────────────────────────────────────

const wss = new WebSocketServer({ server, path: '/ws' })
const clients = new Set<WebSocket>()

wss.on('connection', (ws) => {
  clients.add(ws)
  ws.send(JSON.stringify({ type: 'state', data: cachedState }))
  ws.on('close', () => clients.delete(ws))
})

function broadcast(state: OrgState) {
  const msg = JSON.stringify({ type: 'state', data: state })
  for (const ws of clients) {
    if (ws.readyState === WebSocket.OPEN) ws.send(msg)
  }
}

// ── File watcher ───────────────────────────────────────────────────

const watcher = watch(ORG_DIR, {
  ignoreInitial: true,
  persistent: true,
  depth: 10,
  awaitWriteFinish: { stabilityThreshold: 500 },
})

let debounceTimer: ReturnType<typeof setTimeout> | null = null

watcher.on('all', (event, path) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    console.log(`[sync] ${event}: ${path.replace(REPO_ROOT, '')}`)
    cachedState = buildState()
    broadcast(cachedState)
  }, 1000)
})

// ── Start ──────────────────────────────────────────────────────────

server.listen(PORT, () => {
  console.log(`[git-sync] Serving org/ state at http://localhost:${PORT}`)
  console.log(`[git-sync] WebSocket at ws://localhost:${PORT}/ws`)
  console.log(`[git-sync] Watching ${ORG_DIR} for changes`)
  console.log(`[git-sync] Members: ${cachedState.members.map(m => m.member_id).join(', ')}`)
  console.log(`[git-sync] Roles: ${cachedState.roles.map(r => r.role_id).join(', ')}`)
  console.log(`[git-sync] Sessions: ${cachedState.sessions.length} (${cachedState.sessions.filter(s => !s.end_utc).length} active)`)
  console.log(`[git-sync] Damage signals: ${cachedState.damage_signals.length} (${cachedState.damage_signals.filter(d => !d.resolved).length} unresolved)`)
})
