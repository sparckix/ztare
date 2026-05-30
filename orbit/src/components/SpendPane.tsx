/**
 * SpendPane (Orbit v2) — daily spend visibility.
 *
 * Shows today's total LLM spend, breakdown by category + model, and
 * compares to per-role daily caps (from role yaml). Renders inside
 * the Orbit dashboard or as a modal.
 *
 * Per GP-167 panel verdict (Tufte data-ink + Edward's small multiples),
 * the layout is dense + monochrome with one accent color per cap-bucket.
 *
 * Ref: deploy/README.md "Auth model — important to understand"
 *      docs/concepts/ztare_research_company_architecture.md §"Backend Decision"
 *      research_areas/private/seams/protocol/GP-192_enterprise_grade_org_runtime_seam.md §Axis 7
 */
import { useEffect, useState } from 'react'
import type { Role } from '../types/org'

interface SpendData {
  date: string
  total_usd: number
  entries_count: number
  by_category: Record<string, { count: number; usd: number }>
  by_model: Record<string, { count: number; usd: number }>
  recent: Array<{
    timestamp_utc: string
    cost_usd: number
    category: string
    action: string
    model_name: string
    session_id: string
  }>
}

interface Props {
  roles: Role[]
}

function fmtUSD(n: number): string {
  if (n < 0.01) return '<$0.01'
  return `$${n.toFixed(2)}`
}

function capBarColor(spent: number, cap: number): string {
  const frac = cap > 0 ? spent / cap : 0
  if (frac >= 1) return '#dc2626'      // red — at/over cap
  if (frac >= 0.8) return '#f59e0b'    // amber — warn threshold
  if (frac >= 0.5) return '#facc15'    // yellow
  return '#16a34a'                      // green — comfortable
}

export function SpendPane({ roles }: Props) {
  const [data, setData] = useState<SpendData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    const fetchSpend = async () => {
      try {
        const r = await fetch('/api/spend/today')
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const d = await r.json()
        if (mounted) {
          setData(d)
          setLoading(false)
        }
      } catch (e) {
        if (mounted) {
          setError(String(e))
          setLoading(false)
        }
      }
    }
    fetchSpend()
    const t = setInterval(fetchSpend, 30000) // 30s refresh
    return () => {
      mounted = false
      clearInterval(t)
    }
  }, [])

  if (loading) return <div className="spend-pane loading">Loading spend…</div>
  if (error) return <div className="spend-pane error">Spend feed unavailable: {error}</div>
  if (!data) return null

  // Compute fleet-wide daily cap (sum of role daily_cap_usd; principal uncapped excluded)
  const fleetCap = roles
    .filter(r => r.budget?.daily_cap_usd != null && r.budget.daily_cap_usd > 0)
    .reduce((s, r) => s + r.budget.daily_cap_usd, 0)

  return (
    <div className="spend-pane" style={{ padding: '12px', fontFamily: 'monospace', fontSize: '13px' }}>
      <h3 style={{ margin: '0 0 8px 0', fontSize: '14px' }}>
        💰 Spend — {data.date}
      </h3>

      {/* Top-line: today's total + fleet cap */}
      <div style={{ marginBottom: '12px' }}>
        <div style={{ fontSize: '20px', fontWeight: 'bold' }}>
          {fmtUSD(data.total_usd)}
          <span style={{ fontSize: '12px', fontWeight: 'normal', color: '#888', marginLeft: '8px' }}>
            of {fmtUSD(fleetCap)} fleet daily cap
          </span>
        </div>
        <div style={{ fontSize: '11px', color: '#888' }}>
          {data.entries_count} LLM call{data.entries_count !== 1 ? 's' : ''} today
        </div>
        {/* Fleet cap progress bar */}
        <div style={{ height: '6px', background: '#1a1a1a', borderRadius: '3px', marginTop: '4px', overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${Math.min(100, (data.total_usd / Math.max(0.01, fleetCap)) * 100)}%`,
              background: capBarColor(data.total_usd, fleetCap),
              transition: 'width 0.3s, background 0.3s',
            }}
          />
        </div>
      </div>

      {/* Per-role caps (small multiples per Tufte) */}
      <div style={{ marginBottom: '12px' }}>
        <div style={{ fontSize: '11px', color: '#888', marginBottom: '4px' }}>Role caps (daily)</div>
        {roles
          .filter(r => r.budget?.daily_cap_usd != null && r.budget.daily_cap_usd > 0)
          .sort((a, b) => b.budget.daily_cap_usd - a.budget.daily_cap_usd)
          .map(r => {
            // We don't have per-role attribution in spend data yet — show role's cap unfilled.
            // When spend tracker adds role_id, this becomes a real bar.
            return (
              <div key={r.role_id} style={{ marginBottom: '4px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
                  <span>{r.role_id}</span>
                  <span style={{ color: '#888' }}>{fmtUSD(r.budget.daily_cap_usd)}</span>
                </div>
                <div style={{ height: '4px', background: '#1a1a1a', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: '0%', background: '#444' }} />
                </div>
              </div>
            )
          })}
        <div style={{ fontSize: '10px', color: '#666', fontStyle: 'italic', marginTop: '4px' }}>
          per-role attribution not yet wired in spend_tracker; today shows fleet-wide only
        </div>
      </div>

      {/* By category */}
      {Object.keys(data.by_category).length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '11px', color: '#888', marginBottom: '4px' }}>By category</div>
          {Object.entries(data.by_category)
            .sort((a, b) => b[1].usd - a[1].usd)
            .map(([cat, { count, usd }]) => (
              <div key={cat} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span>{cat} ({count})</span>
                <span>{fmtUSD(usd)}</span>
              </div>
            ))}
        </div>
      )}

      {/* By model */}
      {Object.keys(data.by_model).length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '11px', color: '#888', marginBottom: '4px' }}>By model</div>
          {Object.entries(data.by_model)
            .sort((a, b) => b[1].usd - a[1].usd)
            .slice(0, 5)
            .map(([model, { count, usd }]) => (
              <div key={model} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '70%' }}>
                  {model}
                </span>
                <span>{fmtUSD(usd)} ({count})</span>
              </div>
            ))}
        </div>
      )}

      {/* Recent entries */}
      {data.recent && data.recent.length > 0 && (
        <details style={{ fontSize: '11px' }}>
          <summary style={{ cursor: 'pointer', color: '#888' }}>
            Recent {data.recent.length} entries
          </summary>
          <div style={{ marginTop: '4px', maxHeight: '200px', overflowY: 'auto' }}>
            {data.recent.map((e, i) => (
              <div key={i} style={{ borderBottom: '1px solid #222', padding: '2px 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#888' }}>
                    {new Date(e.timestamp_utc).toLocaleTimeString()}
                  </span>
                  <span>{fmtUSD(e.cost_usd)}</span>
                </div>
                <div style={{ fontSize: '10px', color: '#666', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {e.action.split(':').pop()?.slice(0, 80)}
                </div>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}
