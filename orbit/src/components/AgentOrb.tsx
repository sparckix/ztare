// Licensed under Business Source License 1.1 — see LICENSE-BSL
/**
 * Agent Orb — professional orbital state indicator.
 *
 * Each agent is a luminous orb with:
 *   - Color halo encoding state (green/blue/amber/red/gray)
 *   - Breathing animation for active agents
 *   - Pulsing ring when the agent needs human attention
 *   - Inner glyph: first letter of role (M/E/R/D/P)
 *   - Orbital position encodes activity (closer to center = more active)
 *   - Size encodes recent output volume
 *
 * Click → expands into detail card below.
 * Hover → shows one-sentence status tooltip.
 */

import { useState } from 'react'

type OrbState = 'active' | 'focused' | 'blocked' | 'error' | 'idle'

interface AgentOrbProps {
  name: string
  role: string
  state: OrbState
  needsHuman: boolean
  statusLine: string
  onClick: () => void
  size?: number
  selected?: boolean
}

const STATE_COLORS: Record<OrbState, { core: string; halo: string }> = {
  active:  { core: '#34d399', halo: 'rgba(52, 211, 153, 0.15)' },
  focused: { core: '#4f8ff7', halo: 'rgba(79, 143, 247, 0.12)' },
  blocked: { core: '#f59e0b', halo: 'rgba(245, 158, 11, 0.12)' },
  error:   { core: '#ef4444', halo: 'rgba(239, 68, 68, 0.15)' },
  idle:    { core: '#4a5070', halo: 'rgba(74, 80, 112, 0.08)' },
}

const ROLE_GLYPHS: Record<string, string> = {
  principal: 'P',
  manager: 'M',
  engineer: 'E',
  reviewer: 'R',
  research_director: 'D',
}

export function AgentOrb({
  name, role, state, needsHuman, statusLine, onClick, size = 80, selected = false
}: AgentOrbProps) {
  const [hovered, setHovered] = useState(false)
  const { core, halo } = STATE_COLORS[state]
  const glyph = ROLE_GLYPHS[role] || role[0]?.toUpperCase() || '?'
  const isAlive = state !== 'idle'

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        cursor: 'pointer',
        position: 'relative',
        transition: 'transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
        transform: hovered ? 'scale(1.08)' : selected ? 'scale(1.04)' : 'scale(1)',
      }}
    >
      <svg width={size} height={size} viewBox="0 0 80 80">
        <defs>
          {/* Radial gradient for the halo */}
          <radialGradient id={`halo-${name}`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={core} stopOpacity={isAlive ? 0.25 : 0.05} />
            <stop offset="70%" stopColor={core} stopOpacity={isAlive ? 0.08 : 0.02} />
            <stop offset="100%" stopColor={core} stopOpacity="0" />
          </radialGradient>

          {/* Glow filter */}
          <filter id={`glow-${name}`}>
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Outer halo */}
        <circle cx="40" cy="40" r="38" fill={`url(#halo-${name})`}>
          {isAlive && (
            <animate
              attributeName="r"
              values="36;39;36"
              dur="4s"
              repeatCount="indefinite"
            />
          )}
        </circle>

        {/* Needs-human pulsing ring */}
        {needsHuman && (
          <circle cx="40" cy="40" r="32" fill="none" stroke={core} strokeWidth="1" opacity="0.4">
            <animate attributeName="r" values="30;36;30" dur="2s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.4;0.1;0.4" dur="2s" repeatCount="indefinite" />
          </circle>
        )}

        {/* Selection ring */}
        {selected && (
          <circle cx="40" cy="40" r="30" fill="none" stroke={core} strokeWidth="1.5" opacity="0.6" />
        )}

        {/* Core orb */}
        <circle
          cx="40" cy="40" r="24"
          fill="#0f1117"
          stroke={core}
          strokeWidth={isAlive ? 1.5 : 0.5}
          filter={isAlive ? `url(#glow-${name})` : undefined}
        />

        {/* Inner glow */}
        <circle cx="40" cy="40" r="20" fill={halo} />

        {/* Role glyph */}
        <text
          x="40" y="44"
          textAnchor="middle"
          fill={core}
          fontSize="16"
          fontWeight="600"
          fontFamily="Inter, -apple-system, sans-serif"
          opacity={isAlive ? 0.9 : 0.4}
        >
          {glyph}
        </text>

        {/* Activity indicator dot */}
        {isAlive && (
          <circle cx="58" cy="22" r="4" fill={core}>
            <animate attributeName="opacity" values="1;0.3;1" dur="3s" repeatCount="indefinite" />
          </circle>
        )}
      </svg>

      {/* Name + role label */}
      <div style={{ marginTop: 2, textAlign: 'center' }}>
        <div style={{
          fontSize: 12,
          fontWeight: 600,
          color: isAlive ? '#e8eaf0' : '#4a5070',
          letterSpacing: '0.3px',
        }}>
          {name}
        </div>
        <div style={{
          fontSize: 9,
          color: '#4a5070',
          textTransform: 'uppercase',
          letterSpacing: '1px',
          marginTop: 1,
        }}>
          {role}
        </div>
      </div>

      {/* Hover tooltip — one sentence */}
      {hovered && (
        <div style={{
          position: 'absolute',
          top: size + 32,
          left: '50%',
          transform: 'translateX(-50%)',
          background: '#1a1d2e',
          border: `1px solid ${core}33`,
          borderRadius: 8,
          padding: '6px 12px',
          fontSize: 11,
          color: '#c8cdd8',
          whiteSpace: 'nowrap',
          maxWidth: 280,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          zIndex: 20,
          boxShadow: `0 4px 20px rgba(0,0,0,0.5), 0 0 15px ${core}11`,
          pointerEvents: 'none',
        }}>
          {statusLine}
        </div>
      )}
    </div>
  )
}

/**
 * Derive orb state from agent data.
 */
export function deriveOrbState(params: {
  isActive: boolean
  hasError: boolean
  needsHuman: boolean
  isIdle: boolean
}): OrbState {
  if (params.isIdle && !params.isActive) return 'idle'
  if (params.hasError) return 'error'
  if (params.needsHuman) return 'blocked'
  if (params.isActive) return 'active'
  return 'focused'
}
