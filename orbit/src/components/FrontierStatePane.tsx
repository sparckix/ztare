/**
 * FrontierStatePane — RD-1.12 live co-drive visualization (2026-05-02).
 *
 * Reads /api/frontier_state and renders, per active project:
 *   - current champion meaning (1-line summary)
 *   - route ranking with obstruction counters
 *   - pending actions queue (drained by iter_action_executor)
 *   - last N history entries (rule fires + outcomes)
 *
 * The pane is read-only. Writes happen through the daemon's executor
 * which is the single authority for state mutation per RD-1.12 design.
 */
import { useEffect, useState, useMemo } from 'react'

interface RouteEntry {
  route_id: string
  label?: string
  rank: number
  obstruction_count?: number
  last_obstructed_iter?: number
}

interface HistoryEntry {
  ts: string
  rule_id?: string
  action_kind?: string
  outcome?: string
  ok?: boolean
  detail?: string
}

interface ProjectFrontier {
  slug: string
  state: {
    project_slug?: string
    last_iter_observed?: number
    champion_meaning?: string
    route_ranking?: RouteEntry[]
    pending_actions?: any[]
    history?: HistoryEntry[]
    escapes?: any[]
    updated_utc?: string
  }
}

interface Props {
  apiBase?: string
  refreshIntervalMs?: number
}

export function FrontierStatePane({
  apiBase = 'http://127.0.0.1:3001',
  refreshIntervalMs = 5000,
}: Props) {
  const [projects, setProjects] = useState<ProjectFrontier[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastFetchTs, setLastFetchTs] = useState<number | null>(null)

  useEffect(() => {
    let alive = true
    const fetchOnce = async () => {
      try {
        const r = await fetch(`${apiBase}/api/frontier_state`)
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const j = await r.json()
        if (!alive) return
        setProjects(j.projects || [])
        setError(null)
        setLastFetchTs(Date.now())
      } catch (e: any) {
        if (!alive) return
        setError(e?.message || String(e))
      } finally {
        if (alive) setLoading(false)
      }
    }
    fetchOnce()
    const id = setInterval(fetchOnce, refreshIntervalMs)
    return () => { alive = false; clearInterval(id) }
  }, [apiBase, refreshIntervalMs])

  if (loading) {
    return <div style={{ padding: 16, fontFamily: 'monospace' }}>loading frontier state…</div>
  }
  if (error) {
    return (
      <div style={{ padding: 16, fontFamily: 'monospace', color: '#c33' }}>
        frontier state error: {error}
      </div>
    )
  }
  if (projects.length === 0) {
    return (
      <div style={{ padding: 16, fontFamily: 'monospace', color: '#888' }}>
        no active frontier-state projects.{' '}
        <span style={{ fontSize: 11 }}>
          (RD-1.12 daemon hasn't observed any iter activity yet, or no projects under projects/.)
        </span>
      </div>
    )
  }

  return (
    <div style={{ padding: 16, fontFamily: 'monospace', fontSize: 13 }}>
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
        <strong>RD-1.12 Frontier State — {projects.length} project{projects.length !== 1 ? 's' : ''}</strong>
        {lastFetchTs && (
          <span style={{ color: '#888', fontSize: 11 }}>
            updated {new Date(lastFetchTs).toLocaleTimeString()}
          </span>
        )}
      </div>
      {projects.map(p => <ProjectCard key={p.slug} project={p} />)}
    </div>
  )
}

function ProjectCard({ project }: { project: ProjectFrontier }) {
  const s = project.state || {}
  const ranking = s.route_ranking || []
  const pending = s.pending_actions || []
  const history = s.history || []
  const lastN = useMemo(() => history.slice(-8).reverse(), [history])

  return (
    <div style={{
      border: '1px solid #ddd', borderRadius: 6, padding: 12,
      marginBottom: 12, background: '#fafafa',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <strong>📊 {project.slug}</strong>
        <span style={{ color: '#666', fontSize: 11 }}>
          last_iter={s.last_iter_observed ?? '—'}
        </span>
      </div>

      {s.champion_meaning && (
        <div style={{
          background: '#fff', padding: 8, borderRadius: 4,
          marginBottom: 8, fontSize: 12,
        }}>
          <span style={{ color: '#888' }}>champion meaning:</span> {s.champion_meaning}
        </div>
      )}

      <div style={{ display: 'flex', gap: 16 }}>
        <div style={{ flex: 1 }}>
          <div style={{ color: '#888', fontSize: 11, marginBottom: 4 }}>route ranking</div>
          {ranking.length === 0 ? (
            <span style={{ color: '#aaa', fontSize: 11 }}>(none)</span>
          ) : (
            <div>
              {ranking.slice().sort((a, b) => a.rank - b.rank).map(r => (
                <div key={r.route_id} style={{
                  display: 'flex', justifyContent: 'space-between',
                  fontSize: 12, padding: '2px 0',
                  color: (r.obstruction_count || 0) >= 2 ? '#c33' : '#333',
                }}>
                  <span>#{r.rank} {r.label || r.route_id}</span>
                  {(r.obstruction_count || 0) > 0 && (
                    <span title={`obstructed at iter ${r.last_obstructed_iter ?? '?'}`}>
                      🚧 {r.obstruction_count}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ flex: 1 }}>
          <div style={{ color: '#888', fontSize: 11, marginBottom: 4 }}>
            pending actions ({pending.length})
          </div>
          {pending.length === 0 ? (
            <span style={{ color: '#aaa', fontSize: 11 }}>(empty)</span>
          ) : (
            pending.slice(0, 5).map((a, i) => (
              <div key={i} style={{ fontSize: 11, padding: '2px 0' }}>
                ⏳ {a.action_kind} <span style={{ color: '#999' }}>({a.rule_id || '?'})</span>
              </div>
            ))
          )}
        </div>
      </div>

      {lastN.length > 0 && (
        <details style={{ marginTop: 8 }}>
          <summary style={{ cursor: 'pointer', fontSize: 11, color: '#666' }}>
            recent history ({lastN.length} of {history.length})
          </summary>
          <div style={{ marginTop: 4, fontSize: 11 }}>
            {lastN.map((h, i) => (
              <div key={i} style={{
                padding: '2px 0',
                color: h.ok === false ? '#c33' : (h.ok === true ? '#393' : '#666'),
              }}>
                <span style={{ color: '#aaa' }}>{(h.ts || '').slice(11, 19)}</span>{' '}
                {h.ok === true ? '✓' : h.ok === false ? '✗' : '·'}{' '}
                <strong>{h.action_kind || h.rule_id || '?'}</strong>
                {h.outcome && <span style={{ color: '#888' }}> — {h.outcome}</span>}
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}
