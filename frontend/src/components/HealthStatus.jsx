import React from 'react'

function StatusDot({ active }) {
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${active ? 'bg-green-400' : 'bg-red-400'}`} />
  )
}

export default function HealthStatus({ health }) {
  if (!health) return null

  const uptime = health.uptime_seconds
  const hours = Math.floor(uptime / 3600)
  const mins = Math.floor((uptime % 3600) / 60)

  return (
    <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-400">System Health</h3>
        <span className={`px-2 py-0.5 rounded-full text-xs ${
          health.status === 'healthy' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
        }`}>
          {health.status}
        </span>
      </div>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-400"><StatusDot active={health.db_connected} /> Database</span>
          <span className="text-gray-300">{health.db_connected ? 'Connected' : 'Disconnected'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400"><StatusDot active={health.model_loaded} /> ML Model</span>
          <span className="text-gray-300">{health.model_loaded ? 'Loaded' : 'Not loaded'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400"><StatusDot active={health.regex_engine} /> Regex Engine</span>
          <span className="text-gray-300">{health.regex_engine ? 'Active' : 'Inactive'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400"><StatusDot active={health.anomaly_detection} /> Anomaly Detection</span>
          <span className="text-gray-300">{health.anomaly_detection ? 'Active' : 'Inactive'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400"><StatusDot active={health.email_alerts} /> Email Alerts</span>
          <span className="text-gray-300">{health.email_alerts ? 'Configured' : 'Disabled'}</span>
        </div>
        <div className="flex justify-between mt-3 pt-3 border-t border-gray-800">
          <span className="text-gray-400">Uptime</span>
          <span className="text-gray-300">{hours}h {mins}m</span>
        </div>
        {health.disk && (
          <div className="flex justify-between">
            <span className="text-gray-400">Disk Usage</span>
            <span className={`text-gray-300 ${health.disk.usage_percent > 80 ? 'text-red-400' : ''}`}>
              {health.disk.usage_percent}%
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
