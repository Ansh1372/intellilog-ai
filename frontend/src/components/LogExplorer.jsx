import React, { useState } from 'react'
import { useApi, postApi } from '../hooks/useApi'

const SEVERITY_BADGE = {
  Critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  High: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  Medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  Low: 'bg-green-500/20 text-green-400 border-green-500/30',
}

export default function LogExplorer() {
  const [search, setSearch] = useState('')
  const [source, setSource] = useState('')
  const [severity, setSeverity] = useState('')
  const [page, setPage] = useState(1)
  const [feedbackLog, setFeedbackLog] = useState(null)
  const [correctLabel, setCorrectLabel] = useState('')

  const params = { page, limit: 20 }
  if (search) params.q = search
  if (source) params.source = source
  if (severity) params.severity = severity

  const { data, loading, refetch } = useApi('/logs', { params, interval: 10000 })
  const { data: sources } = useApi('/sources')

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    refetch()
  }

  const handleFeedback = async () => {
    if (!feedbackLog || !correctLabel) return
    try {
      await postApi('/feedback', { log_id: feedbackLog, correct_label: correctLabel })
      setFeedbackLog(null)
      setCorrectLabel('')
      refetch()
    } catch (err) {
      alert(`Feedback failed: ${err.message}`)
    }
  }

  const logs = data?.logs || []
  const total = data?.total || 0
  const totalPages = data?.total_pages || 1

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800">
      <div className="p-4 border-b border-gray-800">
        <h3 className="text-sm font-medium text-gray-400 mb-3">Log Explorer</h3>
        <form onSubmit={handleSearch} className="flex flex-wrap gap-2">
          <input
            type="text"
            placeholder="Search logs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 min-w-[200px] px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          <select
            value={source}
            onChange={(e) => { setSource(e.target.value); setPage(1) }}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-sm text-gray-200"
          >
            <option value="">All Sources</option>
            {(sources?.sources || []).map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select
            value={severity}
            onChange={(e) => { setSeverity(e.target.value); setPage(1) }}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-sm text-gray-200"
          >
            <option value="">All Severities</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-md text-sm font-medium transition-colors"
          >
            Search
          </button>
        </form>
        <p className="text-xs text-gray-500 mt-2">{total} results</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400">
              <th className="px-4 py-3 text-left font-medium">Log</th>
              <th className="px-4 py-3 text-left font-medium">Classification</th>
              <th className="px-4 py-3 text-left font-medium">Severity</th>
              <th className="px-4 py-3 text-left font-medium">Source</th>
              <th className="px-4 py-3 text-left font-medium">Confidence</th>
              <th className="px-4 py-3 text-left font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {loading && !logs.length ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
            ) : logs.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No logs found</td></tr>
            ) : (
              logs.map((log) => (
                <tr key={log.log_id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="px-4 py-3 max-w-xs truncate text-gray-300" title={log.log}>
                    {log.log?.substring(0, 80)}{log.log?.length > 80 ? '...' : ''}
                  </td>
                  <td className="px-4 py-3 text-gray-300">{log.classification}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs border ${SEVERITY_BADGE[log.severity] || 'bg-gray-700 text-gray-400'}`}>
                      {log.severity || 'Unknown'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400">{log.source || log.prediction_source || '—'}</td>
                  <td className="px-4 py-3 text-gray-400">
                    {log.confidence ? `${(log.confidence * 100).toFixed(0)}%` : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => setFeedbackLog(log.log_id)}
                      className="text-xs text-red-400 hover:text-red-300 transition-colors"
                    >
                      Mark Wrong
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between p-4 border-t border-gray-800">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 text-sm bg-gray-800 rounded disabled:opacity-50 hover:bg-gray-700"
          >
            Previous
          </button>
          <span className="text-sm text-gray-400">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 text-sm bg-gray-800 rounded disabled:opacity-50 hover:bg-gray-700"
          >
            Next
          </button>
        </div>
      )}

      {/* Feedback Modal */}
      {feedbackLog && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium mb-4">Correct Classification</h3>
            <p className="text-sm text-gray-400 mb-3">Log ID: {feedbackLog}</p>
            <input
              type="text"
              placeholder="Enter correct label..."
              value={correctLabel}
              onChange={(e) => setCorrectLabel(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-sm mb-4 focus:outline-none focus:border-blue-500"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => { setFeedbackLog(null); setCorrectLabel('') }}
                className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 rounded-md"
              >
                Cancel
              </button>
              <button
                onClick={handleFeedback}
                disabled={!correctLabel}
                className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50"
              >
                Submit Correction
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
