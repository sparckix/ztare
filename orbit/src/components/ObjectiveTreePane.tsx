/**
 * Objective tree pane (GP-168 addendum 2026-04-27).
 *
 * Renders the OKR tree by joining org/objectives/, org/key_results/,
 * org/tasks/ in the dashboard. Pressure indicators on every level.
 *
 * Layout per Objective:
 *   🎯 <title>                    pressure-bar (closure_deadline)
 *      📊 KR1 (status, score)     pressure-bar (review-overdue)
 *         📋 task1                pressure-bar (max of time + budget)
 *         📋 task2
 *      📊 KR2
 *   🎯 <title2>
 *   ...
 *   _N unattached tasks_
 *   _M open gates in inbox_
 */
import { useMemo, useState, useCallback } from 'react'
import type { Objective, KeyResult, Task, Gate, Pressure, AgentMessage } from '../types/org'
import {
  taskTimePressure, taskBudgetPressure, krOverduePressure, combinePressure, BAND_COLOR,
} from '../lib/pressure'
import { PressureBar } from './PressureBar'

interface Props {
  objectives: Objective[]
  keyResults: KeyResult[]
  tasks: Task[]
  gates: Gate[]
  agentMessages?: AgentMessage[]
  onResolveGate?: (gateId: string, optionId: string, reason?: string) => void
}

export function ObjectiveTreePane({ objectives, keyResults, tasks, gates, agentMessages = [], onResolveGate }: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const now = new Date()

  const krsByObj = useMemo(() => {
    const map: Record<string, KeyResult[]> = {}
    for (const k of keyResults) {
      if (!k.objective_id) continue
      ;(map[k.objective_id] ||= []).push(k)
    }
    return map
  }, [keyResults])

  const tasksByKR = useMemo(() => {
    const map: Record<string, Task[]> = {}
    for (const t of tasks) {
      if (!t.kr_id) continue
      ;(map[t.kr_id] ||= []).push(t)
    }
    return map
  }, [tasks])

  const tasksByObj = useMemo(() => {
    const map: Record<string, Task[]> = {}
    for (const t of tasks) {
      if (!t.objective_id) continue
      if (t.kr_id) continue   // already counted under KR
      ;(map[t.objective_id] ||= []).push(t)
    }
    return map
  }, [tasks])

  const unattachedTasks = useMemo(
    () => tasks.filter(t => !t.objective_id && t.status !== 'done' && t.status !== 'abandoned'),
    [tasks],
  )
  const activeObjectives = useMemo(
    () => objectives.filter(o => (o.status ?? 'active') === 'active'),
    [objectives],
  )

  const pendingGates = gates.filter(g => g.status !== 'resolved')

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{
        fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.5,
        color: '#6b7394', marginBottom: 12,
      }}>
        🎯 OKR Tree{activeObjectives.length > 0 && ` (${activeObjectives.length} active)`}
      </h2>

      {pendingGates.length > 0 && (
        <div style={{
          background: 'rgba(245,158,11,0.10)',
          border: '1px solid rgba(245,158,11,0.4)',
          padding: '8px 10px',
          borderRadius: 8,
          marginBottom: 12,
          fontSize: 11,
          color: '#f59e0b',
        }}>
          ⚡ {pendingGates.length} gate{pendingGates.length === 1 ? '' : 's'} awaiting decision
        </div>
      )}

      {agentMessages.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{
            fontSize: 10, color: '#6b7394', textTransform: 'uppercase',
            letterSpacing: 1, marginBottom: 6,
          }}>
            Agent inbox
          </div>
          {agentMessages.slice(0, 6).map(m => <AgentMessageRow key={m.message_id} message={m} />)}
          {agentMessages.length > 6 && (
            <div style={{ fontSize: 10, color: '#6b7394', marginTop: 4 }}>
              ... and {agentMessages.length - 6} more
            </div>
          )}
        </div>
      )}

      {activeObjectives.length === 0 && (
        <div style={{ fontSize: 12, color: '#6b7394', fontStyle: 'italic', marginBottom: 12 }}>
          No active Objectives. Author one in <code style={{ color: '#4f8ff7' }}>org/objectives/</code>.
        </div>
      )}

      {activeObjectives.map(obj => {
        const krs = krsByObj[obj.objective_id] || []
        const orphanTasks = tasksByObj[obj.objective_id] || []
        const isExpanded = expanded[obj.objective_id] ?? true
        return (
          <div
            key={obj.objective_id}
            style={{
              background: '#161822',
              borderRadius: 10,
              padding: 12,
              marginBottom: 10,
              border: '1px solid #1e2030',
            }}
          >
            <div
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', cursor: 'pointer' }}
              onClick={() => setExpanded({ ...expanded, [obj.objective_id]: !isExpanded })}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#e8eaf0', marginBottom: 2 }}>
                  {isExpanded ? '▼' : '▶'} 🎯 {obj.title || obj.objective_id}
                </div>
                <div style={{ fontSize: 10, color: '#6b7394' }}>
                  {krs.length} KR{krs.length === 1 ? '' : 's'} · {orphanTasks.length} task{orphanTasks.length === 1 ? '' : 's'} direct
                  {(obj.closure_deadline || obj.target_date) && (
                    <> · deadline {(obj.closure_deadline || obj.target_date)?.slice(0, 10)}</>
                  )}
                </div>
              </div>
            </div>

            {isExpanded && (
              <div style={{ marginTop: 10 }}>
                {krs.map(kr => (
                  <KRRow
                    key={kr.kr_id}
                    kr={kr}
                    tasks={tasksByKR[kr.kr_id] || []}
                    now={now}
                  />
                ))}
                {orphanTasks.length > 0 && (
                  <div style={{ marginTop: 6, paddingLeft: 12 }}>
                    <div style={{ fontSize: 10, color: '#6b7394', marginBottom: 4 }}>direct tasks (no KR)</div>
                    {orphanTasks.map(t => <TaskRow key={t.task_id} task={t} now={now} />)}
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}

      {unattachedTasks.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{
            fontSize: 10, color: '#f59e0b', textTransform: 'uppercase',
            letterSpacing: 1, marginBottom: 6,
          }}>
            {unattachedTasks.length} unattached task{unattachedTasks.length === 1 ? '' : 's'} (no objective_id)
          </div>
          {unattachedTasks.map(t => <TaskRow key={t.task_id} task={t} now={now} />)}
        </div>
      )}

      {pendingGates.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{
            fontSize: 10, color: '#6b7394', textTransform: 'uppercase',
            letterSpacing: 1, marginBottom: 6,
          }}>
            ⚡ Executive inbox
          </div>
          {pendingGates.slice(0, 8).map(g => (
            <GateRow key={g.gate_id} gate={g} onResolve={onResolveGate} />
          ))}
          {pendingGates.length > 8 && (
            <div style={{ fontSize: 10, color: '#6b7394', marginTop: 4 }}>
              ... and {pendingGates.length - 8} more
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function AgentMessageRow({ message }: { message: AgentMessage }) {
  const urgent = message.expects_response || ['request', 'handoff', 'clarification'].includes(message.kind)
  return (
    <div style={{
      background: urgent ? 'rgba(245,158,11,0.10)' : '#161822',
      border: urgent ? '1px solid rgba(245,158,11,0.45)' : '1px solid #1e2030',
      borderRadius: 8,
      padding: '7px 8px',
      marginBottom: 6,
      fontSize: 11,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 3 }}>
        <span style={{ color: urgent ? '#f59e0b' : '#4f8ff7', fontWeight: 600 }}>
          {message.kind}
        </span>
        <span style={{ color: '#6b7394', fontFamily: 'monospace', fontSize: 9 }}>
          {message.from_role} {'->'} {message.to_role}
        </span>
      </div>
      <div style={{ color: '#e8eaf0', fontWeight: 600, marginBottom: 3 }}>
        {message.subject}
      </div>
      <div style={{
        color: '#9aa3bd',
        lineHeight: 1.35,
        maxHeight: 42,
        overflow: 'hidden',
      }}>
        {message.body}
      </div>
    </div>
  )
}

function KRRow({ kr, tasks, now }: { kr: KeyResult; tasks: Task[]; now: Date }) {
  const pressure = krOverduePressure(kr, now)
  const colors = pressure ? BAND_COLOR[pressure.band] : BAND_COLOR.cool
  const statusColor =
    kr.status === 'on_track' ? '#34d399' :
    kr.status === 'at_risk' ? '#f59e0b' :
    kr.status === 'failed' ? '#ef4444' :
    kr.status === 'done' ? '#4f8ff7' : '#6b7394'
  return (
    <div style={{ marginLeft: 8, marginBottom: 8 }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '4px 6px',
        background: '#0f1117',
        borderRadius: 6,
        border: `1px solid ${colors.border}`,
      }}>
        <span style={{ fontSize: 11, color: statusColor, fontWeight: 600 }}>📊</span>
        <div style={{ fontSize: 11, color: '#e8eaf0', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {kr.description || kr.kr_id}
        </div>
        <span style={{
          fontSize: 9,
          padding: '1px 5px',
          borderRadius: 8,
          background: `${statusColor}22`,
          color: statusColor,
        }}>
          {kr.status || 'pending'}
        </span>
        {kr.measurement_locus === 'world' && (
          <span style={{ fontSize: 9, color: '#34d399' }} title="world-measured">🌍</span>
        )}
        {pressure && <PressureBar pressure={pressure} width={60} height={4} label="remaining" />}
      </div>
      {tasks.length > 0 && (
        <div style={{ marginTop: 4, marginLeft: 14 }}>
          {tasks.map(t => <TaskRow key={t.task_id} task={t} now={now} />)}
        </div>
      )}
    </div>
  )
}

function TaskRow({ task, now }: { task: Task; now: Date }) {
  const time = taskTimePressure(task, now)
  const budget = taskBudgetPressure(task)
  const pressure: Pressure | null = combinePressure(time, budget)
  const priorityColor =
    task.priority === 'urgent' ? '#ef4444' :
    task.priority === 'high' ? '#f59e0b' :
    task.priority === 'medium' ? '#4f8ff7' :
    '#6b7394'
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      padding: '3px 6px',
      fontSize: 10,
      color: '#cbd0e0',
      borderLeft: `2px solid ${priorityColor}`,
      marginBottom: 2,
    }}>
      <span>📋</span>
      <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {task.title || task.task_id}
      </span>
      {task.assigned_to && (
        <span style={{ fontSize: 9, color: '#6b7394', fontFamily: 'ui-monospace, monospace' }}>
          {task.assigned_to.replace('role.', '')}
        </span>
      )}
      {pressure && <PressureBar pressure={pressure} width={50} height={3} label="none" />}
    </div>
  )
}

function GateRow({
  gate,
  onResolve,
}: {
  gate: Gate
  onResolve?: (gateId: string, optionId: string, reason?: string) => void
}) {
  const [reasonOpen, setReasonOpen] = useState(false)
  const [reason, setReason] = useState('')

  const handleResolve = useCallback((optionId: string) => {
    onResolve?.(gate.gate_id, optionId, reason.trim() || undefined)
    setReason('')
    setReasonOpen(false)
  }, [onResolve, gate.gate_id, reason])

  // Audit S2: when gate.options is empty/missing, render a fallback "Resolve"
  // button instead of leaving the row un-actionable. The endpoint defaults
  // option_id to 'resolved' when none is supplied.
  const options = gate.options && gate.options.length > 0
    ? gate.options.slice(0, 4)
    : [{ id: 'resolved', consequence: 'mark resolved (no specific option)' }]

  return (
    <div style={{
      background: '#161822',
      borderRadius: 6,
      padding: '6px 8px',
      marginBottom: 4,
      border: '1px solid rgba(245,158,11,0.3)',
    }}>
      <div style={{ fontSize: 11, color: '#e8eaf0', marginBottom: 2 }}>
        ⚡ {gate.subject || gate.gate_id}
      </div>
      <div style={{ fontSize: 9, color: '#6b7394', marginBottom: 4 }}>
        {gate.kind} · {gate.summary?.slice(0, 80)}
      </div>
      {onResolve && (
        <>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
            {options.map(opt => (
              <button
                key={opt.id}
                onClick={() => handleResolve(opt.id)}
                title={opt.consequence}
                style={{
                  fontSize: 9,
                  padding: '2px 6px',
                  borderRadius: 4,
                  background: 'rgba(79,143,247,0.15)',
                  color: '#4f8ff7',
                  border: '1px solid rgba(79,143,247,0.3)',
                  cursor: 'pointer',
                }}
              >
                {opt.id}
              </button>
            ))}
            <button
              onClick={() => setReasonOpen(o => !o)}
              title={reasonOpen ? 'hide reason field' : 'add a reason for the audit trail'}
              style={{
                fontSize: 9,
                padding: '2px 6px',
                borderRadius: 4,
                background: reasonOpen ? 'rgba(107,115,148,0.25)' : 'transparent',
                color: '#6b7394',
                border: '1px solid #1e2030',
                cursor: 'pointer',
                marginLeft: 'auto',
              }}
            >
              ✎ {reasonOpen ? 'hide' : 'reason'}
            </button>
          </div>
          {reasonOpen && (
            <input
              type="text"
              value={reason}
              onChange={e => setReason(e.target.value)}
              placeholder="why this resolution? (recorded in resolved/<id>.json + transitions.jsonl)"
              style={{
                width: '100%',
                marginTop: 4,
                padding: '3px 6px',
                fontSize: 10,
                background: '#0f1117',
                color: '#e8eaf0',
                border: '1px solid #1e2030',
                borderRadius: 4,
              }}
            />
          )}
        </>
      )}
    </div>
  )
}
