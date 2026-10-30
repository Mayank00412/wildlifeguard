import { useEffect, useState } from 'react'
import { fetchHealth } from '../services/api'
import type { HealthResponse } from '../types/api'

type Status = 'idle' | 'loading' | 'ok' | 'error'

export function useBackendHealth() {
  const [status, setStatus] = useState<Status>('idle')
  const [data, setData] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function check() {
    setStatus('loading')
    setError(null)
    try {
      const payload = await fetchHealth()
      setData(payload)
      setStatus(payload.status === 'ok' ? 'ok' : 'error')
    } catch (err) {
      setData(null)
      setStatus('error')
      setError(err instanceof Error ? err.message : 'Unable to reach the backend')
    }
  }

  useEffect(() => {
    void check()
  }, [])

  return { status, data, error, refresh: check }
}
