/**
 * SpatialCanvas (Orbit v2) — TLDraw-backed spatial layout of org/.
 *
 * Per GP-167 panel verdict: Bret Victor advocated for a spatial canvas
 * (each agent is a persistent tile showing mandate, current task, pending
 * gates; relationships as edges; directly manipulable). Stewart Brand's
 * pace-layer concept is preserved by colour-coding tiles by cadence
 * (slow=role-config, working=tasks, fast=signals).
 *
 * v2 minimum scope:
 *   - Roles laid out spatially as draggable tiles
 *   - Active sessions render as orbiting halos
 *   - Pending gates render as floating cards near their owner role
 *   - Damage signals render in a "fast" lane along the bottom
 *
 * Defers (v3+): edges between roles (delegation graph), tldraw user
 * collaboration (Yjs), persisted layout in org/runtime/orbit_layout.yaml.
 */
import { useMemo } from 'react'
import { Tldraw, createShapeId, type TLAssetStore, type Editor, type TLOnMountHandler } from '@tldraw/tldraw'
import '@tldraw/tldraw/tldraw.css'
import type { OrgState, Role, Session, Gate, DamageSignal } from '../types/org'

interface Props {
  state: OrgState
  onClose: () => void
}

// Pace-layer colour map (Brand)
const PACE_COLOURS = {
  slow: '#1e3a8a',     // role configs (governance — weeks)
  working: '#16a34a',  // tasks + sessions (hours)
  fast: '#dc2626',     // damage signals (seconds)
}

function tileForRole(
  role: Role,
  index: number,
  totalRoles: number,
  sessions: Session[],
  gates: Gate[],
): {
  id: string
  x: number
  y: number
  text: string
  color: keyof typeof PACE_COLOURS
} {
  // Lay out roles in a circle at the centre
  const cx = 600
  const cy = 400
  const radius = 250
  const angle = (index / totalRoles) * Math.PI * 2 - Math.PI / 2
  const x = cx + Math.cos(angle) * radius
  const y = cy + Math.sin(angle) * radius

  const activeSessions = sessions.filter(s => !s.end_utc && (s as any).role_id === role.role_id).length
  const pendingGates = gates.filter(g => (g as any).owner === role.role_id).length

  const text = (
    `${role.role_id}\n` +
    `${role.role_class}\n` +
    `─────\n` +
    `cap: $${role.budget?.daily_cap_usd?.toFixed(0) ?? '∞'}/day\n` +
    `${activeSessions} active session${activeSessions !== 1 ? 's' : ''}\n` +
    `${pendingGates} pending gate${pendingGates !== 1 ? 's' : ''}`
  )

  return {
    id: `role:${role.role_id}`,
    x,
    y,
    text,
    color: 'slow',
  }
}

export function SpatialCanvas({ state, onClose }: Props) {
  const pendingGates = useMemo(
    () => state.gates.filter(g => g.status !== 'resolved'),
    [state.gates],
  )
  const tiles = useMemo(() => {
    return state.roles.map((role, i) =>
      tileForRole(role, i, state.roles.length, state.sessions, pendingGates),
    )
  }, [state, pendingGates])

  const onMount: TLOnMountHandler = (editor: Editor) => {
    editor.updateInstanceState({ isReadonly: true })
    // Place each role as a geo shape with the tile text
    const shapes = tiles.map(t => ({
      id: createShapeId(t.id),
      type: 'geo' as const,
      x: t.x - 80,
      y: t.y - 60,
      props: {
        geo: 'rectangle' as const,
        w: 160,
        h: 120,
        color: t.color === 'slow' ? 'blue' : t.color === 'working' ? 'green' : 'red',
        fill: 'semi' as const,
        text: t.text,
        size: 's' as const,
      },
    }))

    // Damage-signal "fast lane" along the bottom
    const damageY = 700
    state.damage_signals
      .filter(d => !d.resolved)
      .slice(0, 8)
      .forEach((d, i) => {
        shapes.push({
          id: createShapeId(`damage:${d.timestamp_utc}_${i}`),
          type: 'geo' as const,
          x: 100 + i * 130,
          y: damageY,
          props: {
            geo: 'rectangle' as const,
            w: 120,
            h: 60,
            color: 'red' as any,
            fill: 'semi' as const,
            text: `${d.kind}\n${d.source ?? ''}`.slice(0, 60),
            size: 's' as const,
          },
        })
      })

    editor.createShapes(shapes)
    editor.zoomToFit()
  }

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      zIndex: 999, background: '#0a0a0a',
    }}>
      <div style={{
        position: 'absolute', top: '12px', right: '12px', zIndex: 1001,
        display: 'flex', gap: '8px',
      }}>
        <span style={{ color: '#888', fontSize: '12px', alignSelf: 'center', fontFamily: 'monospace' }}>
          Spatial Canvas (v2 PoC) — {state.roles.length} roles, {state.damage_signals.filter(d => !d.resolved).length} unresolved signals
        </span>
        <button
          onClick={onClose}
          style={{ background: '#222', color: '#e8e8e8', border: '1px solid #444', padding: '4px 12px', cursor: 'pointer', fontFamily: 'monospace' }}
        >
          ← back to panes
        </button>
      </div>
      <Tldraw onMount={onMount} hideUi={false} />
    </div>
  )
}
