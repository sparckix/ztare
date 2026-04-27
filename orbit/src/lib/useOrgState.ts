/**
 * React hook that connects to the git-sync daemon and provides
 * live OrgState. Falls back to HTTP polling if WebSocket fails.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import type { OrgState } from '../types/org'

const WS_URL = 'ws://localhost:3001/ws'
const HTTP_URL = 'http://localhost:3001/api/state'
const POLL_INTERVAL = 5000

export function useOrgState(): { state: OrgState | null; connected: boolean; error: string | null } {
  const [state, setState] = useState<OrgState | null>(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchState = useCallback(async () => {
    try {
      const res = await fetch(HTTP_URL)
      if (res.ok) {
        const data = await res.json()
        setState(data)
        setError(null)
      }
    } catch (e) {
      setError('Cannot reach git-sync daemon. Run: npm run sync')
    }
  }, [])

  useEffect(() => {
    // Try WebSocket first
    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        setError(null)
        // Stop polling if active
        if (pollRef.current) {
          clearInterval(pollRef.current)
          pollRef.current = null
        }
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'state') setState(msg.data)
        } catch {}
      }

      ws.onclose = () => {
        setConnected(false)
        // Fall back to polling
        if (!pollRef.current) {
          pollRef.current = setInterval(fetchState, POLL_INTERVAL)
        }
      }

      ws.onerror = () => {
        setConnected(false)
        setError('WebSocket failed — falling back to polling')
        if (!pollRef.current) {
          pollRef.current = setInterval(fetchState, POLL_INTERVAL)
        }
      }
    } catch {
      // WebSocket not available, poll
      fetchState()
      pollRef.current = setInterval(fetchState, POLL_INTERVAL)
    }

    return () => {
      wsRef.current?.close()
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [fetchState])

  return { state, connected, error }
}
