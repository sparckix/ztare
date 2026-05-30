// Licensed under Business Source License 1.1 — see LICENSE-BSL
/**
 * Git-sync daemon — reads org/ directory, serves state via HTTP + WebSocket.
 *
 * The dashboard's backend. Watches the org/ directory for changes,
 * parses YAML/JSON files into typed OrgState, and serves it:
 *   - GET /api/state → full OrgState JSON
 *   - WebSocket /ws → push updates on file changes
 *
 * This is the local/solo control-plane projection. It reads org/ and
 * ztare_workspace/, exposes state to Orbit, and writes approved governance
 * decisions back into the canonical filesystem backend. Git is audit/sync/
 * rollback, not the low-latency coordination substrate.
 */

import { readFileSync, readdirSync, existsSync, statSync, writeFileSync, mkdirSync, renameSync } from 'fs'
import { dirname, join, resolve } from 'path'
import { createServer } from 'http'
import { parse as parseYaml } from 'yaml'
import { WebSocketServer, WebSocket } from 'ws'
import { watch } from 'chokidar'

import type {
  OrgState, Member, Role, Assignment, Session, DamageSignal, WorkCandidate,
  Objective, KeyResult, Task, Gate, AgentMessage
} from '../types/org.js'

const REPO_ROOT = resolve(import.meta.dirname, '..', '..', '..')
const ORG_DIR = join(REPO_ROOT, 'org')
const GATES_DIR = join(REPO_ROOT, 'ztare_workspace', 'gates', 'pending')
const GATES_RESOLVED_DIR = join(REPO_ROOT, 'ztare_workspace', 'gates', 'resolved')
const TRANSITIONS_LOG = join(REPO_ROOT, 'ztare_workspace', 'transitions.jsonl')
const CHANNELS_DIR = join(ORG_DIR, 'channels')
const PORT = Number(process.env.ORBIT_BACKEND_PORT || 3001)
const HOST = process.env.ORBIT_BACKEND_HOST || '127.0.0.1'
const CORS_ORIGIN = process.env.ORBIT_CORS_ORIGIN || 'http://localhost:5173'
const API_TOKEN = process.env.ORBIT_API_TOKEN || ''

// ── Markdown frontmatter reader (GP-168 OKR layer uses md+YAML) ─────

const FM_RE = /^---\n([\s\S]*?)\n---\n?/

function readFrontmatter<T extends Record<string, any>>(path: string): T | null {
  try {
    const text = readFileSync(path, 'utf-8')
    const m = text.match(FM_RE)
    if (!m) return null
    const fm = parseYaml(m[1])
    return (fm && typeof fm === 'object') ? (fm as T) : null
  } catch { return null }
}

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
        // 2026-05-02: optional agent-CLI utilization caps. Pass through if present
        // in the role yaml; consumed by Orbit's MetaConfigPane (Settings) for editing
        // and visualized in the GovernancePane utilization bar.
        ...(r.agent_utilization ? { agent_utilization: r.agent_utilization } : {}),
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

  // GP-168 addendum (2026-04-27): OKR tree from org/objectives/, org/key_results/, org/tasks/
  const objectives: Objective[] = []
  const objectivesDir = join(ORG_DIR, 'objectives')
  if (existsSync(objectivesDir)) {
    for (const f of readdirSync(objectivesDir).filter(f => f.endsWith('.md') && f !== 'README.md')) {
      const o = readFrontmatter<Objective>(join(objectivesDir, f))
      if (o && o.objective_id) objectives.push(o)
    }
  }

  const keyResults: KeyResult[] = []
  const krDir = join(ORG_DIR, 'key_results')
  if (existsSync(krDir)) {
    for (const f of readdirSync(krDir).filter(f => f.endsWith('.md') && f !== 'README.md')) {
      const k = readFrontmatter<KeyResult>(join(krDir, f))
      if (k && k.kr_id) keyResults.push(k)
    }
  }

  // Tasks: walk pending/, active/, done/ — set status from the directory
  const tasks: Task[] = []
  const tasksRoot = join(ORG_DIR, 'tasks')
  for (const stateDir of ['pending', 'active', 'done'] as const) {
    const d = join(tasksRoot, stateDir)
    if (!existsSync(d)) continue
    for (const f of readdirSync(d).filter(f => f.endsWith('.md'))) {
      const t = readFrontmatter<Task>(join(d, f))
      if (!t) continue
      // Directory wins over frontmatter status (filesystem is authoritative)
      const taskWithStatus: Task = { ...t, task_id: t.task_id || f.replace(/\.md$/, ''), status: stateDir }
      tasks.push(taskWithStatus)
    }
  }

  // GP-168 single executive inbox at ztare_workspace/gates/pending/
  const gates: Gate[] = []
  if (existsSync(GATES_DIR)) {
    for (const f of readdirSync(GATES_DIR).filter(f => f.endsWith('.json'))) {
      const g = readJson<Gate>(join(GATES_DIR, f))
      if (g) {
        gates.push({
          ...g,
          gate_id: g.gate_id || f.replace(/\.json$/, ''),
          status: g.status || 'pending',
        })
      }
    }
  }

  const agentMessages: AgentMessage[] = []
  if (existsSync(CHANNELS_DIR)) {
    walkDir(CHANNELS_DIR, (path) => {
      if (!path.endsWith('.json')) return
      if (!path.includes('/inbox/')) return
      const msg = readJson<AgentMessage>(path)
      if (msg && msg.message_id && msg.status !== 'closed') {
        agentMessages.push(msg)
      }
    })
  }
  agentMessages.sort((a, b) => b.created_utc.localeCompare(a.created_utc))

  return {
    members,
    roles,
    assignments,
    sessions,
    damage_signals: damageSignals.slice(0, 50), // last 50
    work_candidates: [], // populated by work_discovery.py call
    objectives,
    key_results: keyResults,
    tasks,
    gates,
    agent_messages: agentMessages.slice(0, 50),
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

function requestAuthorized(req: any, res: any): boolean {
  if (!API_TOKEN) return true
  const expected = `Bearer ${API_TOKEN}`
  if (req.headers.authorization === expected) return true
  res.writeHead(401, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify({ ok: false, error: 'unauthorized' }))
  return false
}

function validGateId(gateId: unknown): gateId is string {
  return typeof gateId === 'string' && /^[A-Za-z0-9_.:-]+$/.test(gateId)
}

const server = createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', CORS_ORIGIN)
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization')

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

  // ── /api/chat/* — per-role two-way chat (Orbit v2 ChatPane) ──────
  // GET /api/chat/:role_id?day=YYYY-MM-DD → list messages for that role+day
  // POST /api/chat/send body: { role_id, text } → append principal message
  //   to org/sessions/<role_id>/chat/<today>.jsonl. Daemon picks it up next
  //   tick and generates a cheap-tier reply (subscription via claude/gemini).
  if (req.url && req.url.startsWith('/api/chat/') && req.method === 'GET') {
    const m = req.url.match(/^\/api\/chat\/([A-Za-z0-9_]+)(?:\?day=([0-9-]+))?/)
    if (!m) {
      res.writeHead(400, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ ok: false, error: 'bad url' }))
      return
    }
    const roleId = m[1]
    const day = m[2] || new Date().toISOString().slice(0, 10)
    const chatFile = join(REPO_ROOT, 'org', 'sessions', roleId, 'chat', `${day}.jsonl`)
    if (!existsSync(chatFile)) {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ role_id: roleId, day, messages: [] }))
      return
    }
    try {
      const lines = readFileSync(chatFile, 'utf-8').split('\n').filter((l: string) => l.trim())
      const messages = lines.map((l: string) => { try { return JSON.parse(l) } catch { return null } }).filter(Boolean)
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ role_id: roleId, day, messages }))
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ ok: false, error: String(err) }))
    }
    return
  }

  if (req.url === '/api/chat/send' && req.method === 'POST') {
    if (!requestAuthorized(req, res)) return
    let body = ''
    req.on('data', chunk => { body += chunk })
    req.on('end', () => {
      try {
        const { role_id, text } = JSON.parse(body)
        if (!role_id || typeof role_id !== 'string' || !/^[A-Za-z0-9_]+$/.test(role_id)) {
          res.writeHead(400, { 'Content-Type': 'application/json' })
          res.end(JSON.stringify({ ok: false, error: 'invalid role_id' }))
          return
        }
        if (!text || typeof text !== 'string' || text.length > 4000) {
          res.writeHead(400, { 'Content-Type': 'application/json' })
          res.end(JSON.stringify({ ok: false, error: 'text required (≤4000 chars)' }))
          return
        }
        const day = new Date().toISOString().slice(0, 10)
        const chatDir = join(REPO_ROOT, 'org', 'sessions', role_id, 'chat')
        mkdirSync(chatDir, { recursive: true })
        const chatFile = join(chatDir, `${day}.jsonl`)
        const msg = {
          id: Math.random().toString(36).substring(2, 14),
          ts: new Date().toISOString(),
          sender: 'principal',
          text,
        }
        writeFileSync(chatFile, JSON.stringify(msg) + '\n', { flag: 'a' })
        res.writeHead(200, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ ok: true, message: msg }))
      } catch (err) {
        res.writeHead(500, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ ok: false, error: String(err) }))
      }
    })
    return
  }

  // ── /api/spend/today — Orbit v2 SpendPane ─────────────────────────
  // Reads ztare_workspace/spend/<today>.json and aggregates by category +
  // by model. Frontend can compare against per-role budget caps from cachedState.roles.
  if (req.url === '/api/spend/today') {
    const today = new Date().toISOString().slice(0, 10) // YYYY-MM-DD
    const spendFile = join(REPO_ROOT, 'ztare_workspace', 'spend', `${today}.json`)
    if (!existsSync(spendFile)) {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ date: today, total_usd: 0, entries: [], by_category: {}, by_model: {} }))
      return
    }
    try {
      const raw: { date: string; entries: any[] } = JSON.parse(readFileSync(spendFile, 'utf-8'))
      const entries = raw.entries || []
      const byCategory: Record<string, { count: number; usd: number }> = {}
      const byModel: Record<string, { count: number; usd: number }> = {}
      let total = 0
      for (const e of entries) {
        const usd = Number(e.cost_usd) || 0
        total += usd
        const cat = e.category || 'unknown'
        byCategory[cat] = byCategory[cat] || { count: 0, usd: 0 }
        byCategory[cat].count += 1
        byCategory[cat].usd += usd
        const model = e.model_name || 'unknown'
        byModel[model] = byModel[model] || { count: 0, usd: 0 }
        byModel[model].count += 1
        byModel[model].usd += usd
      }
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({
        date: today,
        total_usd: total,
        entries_count: entries.length,
        by_category: byCategory,
        by_model: byModel,
        // Most recent 10 entries — frontend renders as a feed
        recent: entries.slice(-10).reverse(),
      }))
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ ok: false, error: String(err) }))
    }
    return
  }

  // ── ACTION ENDPOINTS (write to canonical filesystem backend) ──────

  // Gate approval: POST /api/gate/resolve
  if (req.url === '/api/gate/resolve' && req.method === 'POST') {
    if (!requestAuthorized(req, res)) return
    let body = ''
    req.on('data', chunk => { body += chunk })
    req.on('end', () => {
      try {
        const { gate_id, option_id, verdict, reason } = JSON.parse(body)
        if (!validGateId(gate_id)) {
          res.writeHead(400, { 'Content-Type': 'application/json' })
          res.end(JSON.stringify({ ok: false, error: 'invalid gate_id' }))
          return
        }
        const srcPath = join(GATES_DIR, `${gate_id}.json`)
        const outPath = join(GATES_RESOLVED_DIR, `${gate_id}.json`)
        if (existsSync(outPath)) {
          res.writeHead(200, { 'Content-Type': 'application/json' })
          res.end(JSON.stringify({ ok: true, path: outPath, already_resolved: true }))
          return
        }
        if (!existsSync(srcPath)) {
          res.writeHead(404, { 'Content-Type': 'application/json' })
          res.end(JSON.stringify({ ok: false, error: 'pending gate not found' }))
          return
        }
        const gate = readJson<any>(srcPath) || { gate_id }
        const chosen = option_id ?? verdict ?? 'resolved'
        const tmpPath = `${outPath}.tmp`

        mkdirSync(GATES_RESOLVED_DIR, { recursive: true })
        mkdirSync(dirname(TRANSITIONS_LOG), { recursive: true })
        writeFileSync(tmpPath, JSON.stringify({
          ...gate,
          status: 'resolved',
          resolution: {
            chosen_option: chosen,
            reason: reason ?? '',
            resolved_by: 'orbit',
            resolved_utc: new Date().toISOString(),
          },
        }, null, 2))
        renameSync(tmpPath, outPath)
        try { renameSync(srcPath, `${srcPath}.handled`) } catch {}
        writeFileSync(
          TRANSITIONS_LOG,
          JSON.stringify({
            ts: new Date().toISOString(),
            event: 'gate.resolved',
            gate_id,
            chosen_option: chosen,
            resolved_by: 'orbit',
          }) + '\n',
          { flag: 'a' },
        )
        cachedState = buildState()
        broadcast(cachedState)
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
    if (!requestAuthorized(req, res)) return
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
    if (!requestAuthorized(req, res)) return
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
    const gates: any[] = []
    if (existsSync(GATES_DIR)) {
      walkDir(GATES_DIR, (path) => {
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

  // ── Frontier-state (RD-1.12, 2026-05-02) ─────────────────────────
  // Reads ztare_workspace/frontier_state/<slug>.json so the FrontierStatePane
  // can render route ranking / obstruction counters / pending actions / history.

  // GET /api/frontier_state → { projects: [{ slug, state }] }
  if (req.url === '/api/frontier_state' || req.url?.startsWith('/api/frontier_state?')) {
    const dir = join(REPO_ROOT, 'ztare_workspace', 'frontier_state')
    const projects: Array<{ slug: string, state: any }> = []
    if (existsSync(dir)) {
      try {
        for (const f of readdirSync(dir)) {
          if (!f.endsWith('.json')) continue
          const slug = f.replace(/\.json$/, '')
          try {
            const state = readJson<any>(join(dir, f))
            if (state) projects.push({ slug, state })
          } catch { /* skip unreadable */ }
        }
      } catch { /* dir empty or unreadable */ }
    }
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ projects }))
    return
  }

  // GET /api/frontier_state/<slug> → single-project state
  if (req.url?.startsWith('/api/frontier_state/')) {
    const m = req.url.match(/^\/api\/frontier_state\/([a-z0-9_\-]+)$/)
    if (!m) {
      res.writeHead(400, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ ok: false, error: 'invalid slug' }))
      return
    }
    const slug = m[1]
    const path = join(REPO_ROOT, 'ztare_workspace', 'frontier_state', `${slug}.json`)
    if (!existsSync(path)) {
      res.writeHead(404, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ ok: false, error: 'not found', slug }))
      return
    }
    try {
      const state = readJson<any>(path)
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ slug, state }))
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ ok: false, error: String(e) }))
    }
    return
  }

  // ── Agent-utilization (2026-05-02) ───────────────────────────────
  // Snapshot of today's per-role / per-cli utilization, plus an editor
  // for the agent_utilization caps in org/roles/<role>.yaml.

  // GET /api/agent_utilization/snapshot[?date=YYYY-MM-DD]
  if (req.url?.startsWith('/api/agent_utilization/snapshot')) {
    const url = new URL(req.url, `http://${req.headers.host}`)
    const dateParam = url.searchParams.get('date')
    const date = dateParam || new Date().toISOString().slice(0, 10)
    const utilPath = join(REPO_ROOT, 'ztare_workspace', 'agent_utilization', `${date}.json`)
    if (!existsSync(utilPath)) {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({
        date,
        entries: [],
        totals: { by_role: {}, by_cli: {}, by_role_cli: {} },
      }))
      return
    }
    try {
      const payload = readJson<any>(utilPath)
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify(payload || { date, entries: [] }))
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ ok: false, error: String(e) }))
    }
    return
  }

  // POST /api/role/<role_id>/agent_utilization
  // Body: AgentUtilization (the cap block). Writes back to org/roles/<role>.yaml.
  if (req.url?.startsWith('/api/role/') && req.url.endsWith('/agent_utilization') && req.method === 'POST') {
    if (!requestAuthorized(req, res)) return
    const m = req.url.match(/^\/api\/role\/([a-z_]+)\/agent_utilization$/)
    if (!m) {
      res.writeHead(400, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ ok: false, error: 'invalid role_id in url' }))
      return
    }
    const roleId = m[1]
    const rolePath = join(REPO_ROOT, 'org', 'roles', `${roleId}.yaml`)
    if (!existsSync(rolePath)) {
      res.writeHead(404, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ ok: false, error: `role ${roleId} not found` }))
      return
    }
    let body = ''
    req.on('data', chunk => { body += chunk })
    req.on('end', () => {
      try {
        const caps = JSON.parse(body)
        // Validate required numeric keys
        const required = [
          'daily_cap_seconds', 'daily_cap_output_tokens', 'daily_cap_turn_count',
          'session_cap_seconds', 'absolute_ceiling_seconds', 'warn_threshold_frac',
        ]
        for (const k of required) {
          if (typeof caps[k] !== 'number') {
            res.writeHead(400, { 'Content-Type': 'application/json' })
            res.end(JSON.stringify({ ok: false, error: `missing or non-numeric field: ${k}` }))
            return
          }
        }
        // Read role yaml as text, parse, splice in agent_utilization, write back.
        // We use the yaml package's full parse+stringify to preserve top-level
        // structure but lose comments — acceptable for this dogfood pass.
        const yamlPkg = require('yaml')
        const text = readFileSync(rolePath, 'utf8')
        const data = yamlPkg.parse(text) || {}
        data.agent_utilization = {
          daily_cap_seconds: caps.daily_cap_seconds,
          daily_cap_output_tokens: caps.daily_cap_output_tokens,
          daily_cap_turn_count: caps.daily_cap_turn_count,
          session_cap_seconds: caps.session_cap_seconds,
          absolute_ceiling_seconds: caps.absolute_ceiling_seconds,
          warn_threshold_frac: caps.warn_threshold_frac,
        }
        const newText = yamlPkg.stringify(data)
        const tmpPath = `${rolePath}.tmp`
        writeFileSync(tmpPath, newText)
        renameSync(tmpPath, rolePath)
        // Audit trail in transitions.jsonl
        mkdirSync(dirname(TRANSITIONS_LOG), { recursive: true })
        writeFileSync(
          TRANSITIONS_LOG,
          JSON.stringify({
            ts: new Date().toISOString(),
            event: 'role.agent_utilization.updated',
            role_id: roleId,
            new_caps: data.agent_utilization,
            updated_by: 'orbit',
          }) + '\n',
          { flag: 'a' },
        )
        cachedState = buildState()
        broadcast(cachedState)
        res.writeHead(200, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ ok: true, path: rolePath, agent_utilization: data.agent_utilization }))
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ ok: false, error: String(e) }))
      }
    })
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

const watcher = watch([ORG_DIR, GATES_DIR], {
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

server.listen(PORT, HOST, () => {
  console.log(`[git-sync] Serving org/ state at http://${HOST}:${PORT}`)
  console.log(`[git-sync] WebSocket at ws://${HOST}:${PORT}/ws`)
  console.log(`[git-sync] Watching ${ORG_DIR} and ${GATES_DIR} for changes`)
  console.log(`[git-sync] Members: ${cachedState.members.map(m => m.member_id).join(', ')}`)
  console.log(`[git-sync] Roles: ${cachedState.roles.map(r => r.role_id).join(', ')}`)
  console.log(`[git-sync] Sessions: ${cachedState.sessions.length} (${cachedState.sessions.filter(s => !s.end_utc).length} active)`)
  console.log(`[git-sync] Damage signals: ${cachedState.damage_signals.length} (${cachedState.damage_signals.filter(d => !d.resolved).length} unresolved)`)
})
