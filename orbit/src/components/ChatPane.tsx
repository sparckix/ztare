/**
 * ChatPane (Orbit v2) — per-role two-way chat surface.
 *
 * Backed by GET/POST /api/chat/* endpoints. Storage:
 *   org/sessions/<role_id>/chat/<YYYY-MM-DD>.jsonl
 *
 * Send flow:
 *   1. User picks role from dropdown (SRO, RD, manager, etc.)
 *   2. User types message + sends → POST /api/chat/send
 *   3. Backend appends to chat.jsonl (sender: principal)
 *   4. Daemon's next tick (≤30 min) calls chat_handler.generate_and_store_reply
 *      → cheap-tier LLM via subscription → appends sender: agent_<role_id>
 *   5. Frontend polls every 5s for new messages (WebSocket would be better
 *      but that's a v2.1 polish).
 *
 * Per principal direction (2026-05-07): chat is for DIALOG, not work
 * dispatch. For "do X" tasks, principal should use the official task/gate
 * surface (e.g., drop a task in org/tasks/pending/). Chat is the
 * conversational pane.
 */
import { useEffect, useState, useCallback } from 'react'
import type { Role } from '../types/org'

interface ChatMessage {
  id: string
  ts: string
  sender: string
  text: string
}

interface Props {
  roles: Role[]
  apiPost: (path: string, body: unknown) => Promise<Response>
  onClose: () => void
}

export function ChatPane({ roles, apiPost, onClose }: Props) {
  const [selectedRole, setSelectedRole] = useState<string>(
    roles.find(r => r.role_id === 'self_recursive_orchestrator')?.role_id || roles[0]?.role_id || ''
  )
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState<string>('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchMessages = useCallback(async () => {
    if (!selectedRole) return
    try {
      const r = await fetch(`/api/chat/${selectedRole}`)
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const d = await r.json()
      setMessages(d.messages || [])
      setError(null)
    } catch (e) {
      setError(String(e))
    }
  }, [selectedRole])

  useEffect(() => {
    fetchMessages()
    const t = setInterval(fetchMessages, 5000)
    return () => clearInterval(t)
  }, [fetchMessages])

  const handleSend = async () => {
    if (!input.trim() || sending) return
    setSending(true)
    setError(null)
    try {
      const r = await apiPost('/api/chat/send', { role_id: selectedRole, text: input.trim() })
      if (!r.ok) {
        const text = await r.text()
        setError(`send failed: ${r.status} ${text.slice(0, 200)}`)
      } else {
        setInput('')
        // Optimistic refresh
        fetchMessages()
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      handleSend()
    }
  }

  const overlay: React.CSSProperties = {
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(0, 0, 0, 0.8)', zIndex: 1000,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  }
  const modal: React.CSSProperties = {
    background: '#0a0a0a', color: '#e8e8e8', padding: '0',
    borderRadius: '8px', width: 'min(800px, 95vw)',
    maxHeight: '85vh', display: 'flex', flexDirection: 'column',
    border: '1px solid #333', fontFamily: 'monospace',
  }

  const senderColor = (sender: string): string => {
    if (sender === 'principal') return '#4f8ff7'
    if (sender.startsWith('agent_')) return '#34d399'
    return '#888'
  }

  return (
    <div style={overlay} onClick={onClose}>
      <div style={modal} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #222', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '14px', fontWeight: 'bold' }}>💬 Chat</span>
            <select
              value={selectedRole}
              onChange={e => setSelectedRole(e.target.value)}
              style={{ background: '#1a1a1a', color: '#e8e8e8', border: '1px solid #333', padding: '4px 8px', fontFamily: 'inherit', fontSize: '12px' }}
            >
              {roles.map(r => (
                <option key={r.role_id} value={r.role_id}>{r.role_id}</option>
              ))}
            </select>
            <span style={{ fontSize: '10px', color: '#666' }}>
              ({messages.length} msgs today)
            </span>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: '1px solid #444', color: '#aaa', padding: '4px 12px', cursor: 'pointer', fontFamily: 'inherit', fontSize: '11px' }}>
            close
          </button>
        </div>

        {error && (
          <div style={{ padding: '8px 16px', background: '#3a1a1a', color: '#fca5a5', fontSize: '11px' }}>
            {error}
          </div>
        )}

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', minHeight: '300px' }}>
          {messages.length === 0 && (
            <div style={{ color: '#666', textAlign: 'center', padding: '40px', fontSize: '12px' }}>
              No messages today. Send the first one to {selectedRole} below.
              <div style={{ marginTop: '12px', color: '#444' }}>
                Note: chat is for dialog. Replies use cheap-tier LLM via subscription
                (no API cost). For work dispatch, use the official task/gate surface.
              </div>
            </div>
          )}
          {messages.map(m => (
            <div key={m.id} style={{ marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
                <span style={{ color: senderColor(m.sender), fontSize: '11px', fontWeight: 'bold' }}>
                  {m.sender}
                </span>
                <span style={{ color: '#555', fontSize: '10px' }}>
                  {new Date(m.ts).toLocaleTimeString()}
                </span>
              </div>
              <div style={{ fontSize: '12px', whiteSpace: 'pre-wrap', color: '#ddd', paddingLeft: '4px', borderLeft: `2px solid ${senderColor(m.sender)}` }}>
                {m.text}
              </div>
            </div>
          ))}
        </div>

        {/* Input */}
        <div style={{ padding: '12px 16px', borderTop: '1px solid #222' }}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Message ${selectedRole}... (Cmd/Ctrl+Enter to send)`}
            rows={3}
            style={{ width: '100%', background: '#0e0e0e', color: '#e8e8e8', border: '1px solid #333', padding: '8px', fontFamily: 'inherit', fontSize: '12px', resize: 'vertical', boxSizing: 'border-box' }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
            <span style={{ fontSize: '10px', color: '#666' }}>
              Reply will appear within ~30 min (next daemon tick) via cheap-tier subscription LLM.
            </span>
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending}
              style={{
                background: input.trim() && !sending ? '#16a34a' : '#1a3a1a',
                color: 'white', border: 'none', padding: '6px 16px',
                cursor: input.trim() && !sending ? 'pointer' : 'not-allowed',
                fontFamily: 'inherit', fontSize: '12px', borderRadius: '4px',
              }}
            >
              {sending ? 'sending…' : 'Send'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
