/**
 * Left pane: slow-layer governance view.
 * Roles, mandates, closure map.
 */
import type { Role, Assignment, Member } from '../types/org'

interface Props {
  members: Member[]
  roles: Role[]
  assignments: Assignment[]
  onSelectRole: (roleId: string) => void
}

export function GovernancePane({ members, roles, assignments, onSelectRole }: Props) {
  const getMember = (assignment: Assignment) =>
    members.find(m => `member.${m.member_id}` === assignment.member)

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.5, color: '#6b7394', marginBottom: 12 }}>
        🏛 Governance Layer
      </h2>

      {assignments.filter(a => a.is_primary).map((a, i) => {
        const member = getMember(a)
        const role = roles.find(r => `role.${r.role_id}` === a.role)
        const isHuman = member?.kind === 'human'

        return (
          <div
            key={i}
            onClick={() => role && onSelectRole(role.role_id)}
            style={{
              background: '#161822',
              borderRadius: 10,
              padding: 12,
              marginBottom: 8,
              cursor: 'pointer',
              border: '1px solid #1e2030',
              transition: 'border-color 0.2s',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = '#4f8ff7' }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = '#1e2030' }}
          >
            <div style={{ fontSize: 13, fontWeight: 600, color: '#e8eaf0' }}>
              {role?.role_id || 'unknown'}
            </div>
            <div style={{ fontSize: 11, color: '#6b7394', marginTop: 2 }}>
              {member?.display_name || a.member}
            </div>
            <span style={{
              display: 'inline-block',
              fontSize: 9,
              padding: '2px 6px',
              borderRadius: 10,
              marginTop: 6,
              background: isHuman ? 'rgba(52,211,153,0.15)' : 'rgba(79,143,247,0.15)',
              color: isHuman ? '#34d399' : '#4f8ff7',
            }}>
              {isHuman ? 'human' : 'ai'}
            </span>
          </div>
        )
      })}

      {/* Mandate summary for manager */}
      {roles.find(r => r.role_id === 'manager') && (
        <div style={{ marginTop: 16 }}>
          <h3 style={{ fontSize: 10, color: '#6b7394', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
            Manager Mandate
          </h3>
          {[
            { type: 'can', text: '✓ Run experiments within budget', color: '#34d399' },
            { type: 'can', text: '✓ Propose seams, specs, findings', color: '#34d399' },
            { type: 'must', text: '⚡ Escalate: budget > $10/action', color: '#f59e0b' },
            { type: 'must', text: '⚡ Escalate: gate approval needed', color: '#f59e0b' },
            { type: 'forbidden', text: '✕ Modify mandates', color: '#ef4444' },
            { type: 'forbidden', text: '✕ Push to main without review', color: '#ef4444' },
            { type: 'forbidden', text: '✕ Access credentials', color: '#ef4444' },
          ].map((item, i) => (
            <div key={i} style={{
              fontSize: 11,
              color: '#c8cdd8',
              padding: '6px 8px',
              background: '#161822',
              borderRadius: 6,
              marginBottom: 4,
              borderLeft: `3px solid ${item.color}`,
            }}>
              {item.text}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
