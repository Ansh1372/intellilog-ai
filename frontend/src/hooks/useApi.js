import { useState, useEffect, useCallback } from 'react'

const API_BASE = '/api'

export function useApi(endpoint, options = {}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const { interval = null, params = {} } = options

  const fetchData = useCallback(async () => {
    try {
      const queryString = new URLSearchParams(params).toString()
      const url = `${API_BASE}${endpoint}${queryString ? `?${queryString}` : ''}`
      const response = await fetch(url)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const result = await response.json()
      setData(result)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [endpoint, JSON.stringify(params)])

  useEffect(() => {
    fetchData()
    if (interval) {
      const timer = setInterval(fetchData, interval)
      return () => clearInterval(timer)
    }
  }, [fetchData, interval])

  return { data, loading, error, refetch: fetchData }
}

export async function postApi(endpoint, body) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${response.status}`)
  }
  return response.json()
}
