/**
 * Agent Face — the child's specification made real.
 *
 * "I'd want each robot to have a face. Happy means doing good.
 * Confused means needs help. Scared means something wrong.
 * Tap the face, it tells me what it needs in one sentence."
 *
 * Each agent gets an expressive face rendered as SVG. The face
 * encodes state through:
 *   - Expression (happy / focused / confused / worried / asleep)
 *   - Color halo (green / blue / amber / red / gray)
 *   - Breathing animation (active = breathing, idle = still)
 *   - Size (scales with recent activity level)
 *
 * The face is the primary interface. Everything else unfolds from it.
 */

import { useState } from 'react'

type Expression = 'happy' | 'focused' | 'confused' | 'worried' | 'asleep'

interface AgentFaceProps {
  name: string
  expression: Expression
  role: string
  isActive: boolean
  needsHuman: boolean
  oneSentence: string  // what it needs, in one sentence
  onClick: () => void
  size?: number
}

const HALO_COLORS: Record<Expression, string> = {
  happy: '#34d399',
  focused: '#4f8ff7',
  confused: '#f59e0b',
  worried: '#ef4444',
  asleep: '#4a5070',
}

export function AgentFace({
  name, expression, role, isActive, needsHuman, oneSentence, onClick, size = 120
}: AgentFaceProps) {
  const [showSentence, setShowSentence] = useState(false)
  const color = HALO_COLORS[expression]
  const r = size / 2

  return (
    <div
      onClick={() => { setShowSentence(!showSentence); onClick() }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        cursor: 'pointer',
        transition: 'transform 0.2s',
        position: 'relative',
      }}
      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(1.05)' }}
      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(1)' }}
    >
      <svg width={size} height={size} viewBox="0 0 120 120">
        {/* Halo / aura */}
        <circle
          cx="60" cy="60" r="56"
          fill="none"
          stroke={color}
          strokeWidth="2"
          opacity={isActive ? 0.6 : 0.2}
          style={isActive ? {
            animation: 'breathe 3s ease-in-out infinite',
          } : undefined}
        />
        {needsHuman && (
          <circle
            cx="60" cy="60" r="58"
            fill="none"
            stroke={color}
            strokeWidth="1"
            opacity="0.3"
            style={{ animation: 'pulse 1.5s ease-in-out infinite' }}
          />
        )}

        {/* Head */}
        <circle cx="60" cy="60" r="40" fill="#161822" stroke={color} strokeWidth="1.5" opacity="0.9" />

        {/* Eyes */}
        {expression === 'asleep' ? (
          <>
            <line x1="42" y1="52" x2="52" y2="52" stroke={color} strokeWidth="2" strokeLinecap="round" />
            <line x1="68" y1="52" x2="78" y2="52" stroke={color} strokeWidth="2" strokeLinecap="round" />
          </>
        ) : expression === 'confused' ? (
          <>
            <circle cx="47" cy="50" r="4" fill={color} />
            <circle cx="73" cy="50" r="5" fill={color} />
            <circle cx="47" cy="50" r="1.5" fill="#161822" />
            <circle cx="73" cy="50" r="1.5" fill="#161822" />
          </>
        ) : expression === 'worried' ? (
          <>
            <circle cx="47" cy="52" r="4.5" fill={color} />
            <circle cx="73" cy="52" r="4.5" fill={color} />
            <circle cx="47" cy="53" r="2" fill="#161822" />
            <circle cx="73" cy="53" r="2" fill="#161822" />
          </>
        ) : (
          <>
            <circle cx="47" cy="50" r="4" fill={color} />
            <circle cx="73" cy="50" r="4" fill={color} />
            <circle cx="47" cy="49" r="1.5" fill="#161822" />
            <circle cx="73" cy="49" r="1.5" fill="#161822" />
          </>
        )}

        {/* Mouth */}
        {expression === 'happy' && (
          <path d="M 45 68 Q 60 80 75 68" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" />
        )}
        {expression === 'focused' && (
          <line x1="48" y1="70" x2="72" y2="70" stroke={color} strokeWidth="2" strokeLinecap="round" />
        )}
        {expression === 'confused' && (
          <path d="M 48 72 Q 55 66 62 72 Q 69 78 76 72" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" />
        )}
        {expression === 'worried' && (
          <path d="M 45 75 Q 60 65 75 75" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" />
        )}
        {expression === 'asleep' && (
          <ellipse cx="60" cy="70" rx="6" ry="3" fill="none" stroke={color} strokeWidth="1.5" />
        )}

        {/* Eyebrows for worried */}
        {expression === 'worried' && (
          <>
            <line x1="40" y1="42" x2="50" y2="44" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
            <line x1="80" y1="42" x2="70" y2="44" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          </>
        )}

        {/* Needs-human indicator */}
        {needsHuman && (
          <circle cx="95" cy="20" r="8" fill={color}>
            <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite" />
          </circle>
        )}
      </svg>

      {/* Name + role */}
      <div style={{ marginTop: 4, textAlign: 'center' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#e8eaf0' }}>{name}</div>
        <div style={{ fontSize: 10, color: '#6b7394' }}>{role}</div>
      </div>

      {/* One sentence (tap to reveal) */}
      {showSentence && (
        <div style={{
          position: 'absolute',
          bottom: -50,
          left: '50%',
          transform: 'translateX(-50%)',
          background: '#1a1d2e',
          border: `1px solid ${color}`,
          borderRadius: 8,
          padding: '8px 12px',
          fontSize: 11,
          color: '#e8eaf0',
          whiteSpace: 'nowrap',
          maxWidth: 250,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          zIndex: 10,
          boxShadow: `0 4px 16px rgba(0,0,0,0.4)`,
        }}>
          {oneSentence}
        </div>
      )}

      <style>{`
        @keyframes breathe {
          0%, 100% { r: 56; opacity: 0.6; }
          50% { r: 58; opacity: 0.3; }
        }
        @keyframes pulse {
          0%, 100% { r: 58; opacity: 0.3; }
          50% { r: 62; opacity: 0.1; }
        }
      `}</style>
    </div>
  )
}

/**
 * Derive expression from agent state.
 * This is the child's mapping made deterministic.
 */
export function deriveExpression(state: {
  isActive: boolean
  hasError: boolean
  needsHuman: boolean
  isIdle: boolean
  score?: number
}): Expression {
  if (!state.isActive && state.isIdle) return 'asleep'
  if (state.hasError) return 'worried'
  if (state.needsHuman) return 'confused'
  if (state.score && state.score >= 80) return 'happy'
  return 'focused'
}
