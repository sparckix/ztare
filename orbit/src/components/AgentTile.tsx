/**
 * Spatial agent tile — one per agent on the canvas.
 * Shows: name, role, status, current task, metrics, session claims.
 */
import type { Member, Role, Assignment, Session } from '../types/org'

interface AgentTileProps {
  member: Member
  role: Role | undefined
  assignment: Assignment | undefined
  session: Session | undefined
  onClick: () => void
}

export function AgentTile({ member, role, assignment, session, onClick }: AgentTileProps) {
  const isActive = session && !session.end_utc
  const isHuman = member.kind === 'human'

  const statusColor = isActive ? '#34d399' : '#6b7394'
  const statusLabel = isActive ? 'active' : 'idle'

  const sessionDuration = isActive && session
    ? formatDuration(new Date(session.start_utc))
    : null

  return (
    <div
      onClick={onClick}
      style={{
        background: '#0f1117',
        borderRadius: 12,
        padding: 16,
        border: `1px solid ${isActive ? '#1e3a2a' : '#1e2030'}`,
        boxShadow: isActive ? '0 0 20px rgba(52,211,153,0.08)' : '0 4px 24px rgba(0,0,0,0.3)',
        cursor: 'pointer',
        transition: 'transform 0.15s, box-shadow 0.15s',
        minWidth: 200,
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLElement).style.transform = 'translateY(0)'
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e8eaf0' }}>
          {member.display_name}
        </span>
        <span style={{
          width: 10, height: 10, borderRadius: '50%',
          background: statusColor,
          boxShadow: isActive ? `0 0 8px ${statusColor}` : 'none',
          display: 'inline-block',
        }} />
      </div>

      {/* Role badge */}
      <span style={{
        fontSize: 10,
        color: isHuman ? '#34d399' : '#4f8ff7',
        background: isHuman ? 'rgba(52,211,153,0.1)' : 'rgba(79,143,247,0.1)',
        padding: '2px 8px',
        borderRadius: 10,
        display: 'inline-block',
        marginBottom: 8,
      }}>
        {role?.role_id || 'unassigned'} · {isHuman ? 'human' : 'ai'}
      </span>

      {/* Status */}
      <div style={{ fontSize: 11, color: '#6b7394', marginBottom: 8 }}>
        {statusLabel}
        {sessionDuration && ` · ${sessionDuration}`}
      </div>

      {/* Capabilities preview */}
      <div style={{ fontSize: 10, color: '#4a5070', lineHeight: 1.5 }}>
        {member.capabilities.slice(0, 3).join(' · ')}
        {member.capabilities.length > 3 && ` +${member.capabilities.length - 3}`}
      </div>

      {/* Budget (if role has one) */}
      {role?.budget && (
        <div style={{
          marginTop: 8,
          display: 'flex',
          gap: 12,
          fontSize: 10,
          color: '#6b7394',
        }}>
          <span>${role.budget.session_cap_usd}/session</span>
          <span>${role.budget.daily_cap_usd}/day</span>
        </div>
      )}
    </div>
  )
}

function formatDuration(start: Date): string {
  const ms = Date.now() - start.getTime()
  const hours = Math.floor(ms / 3600000)
  const mins = Math.floor((ms % 3600000) / 60000)
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}
