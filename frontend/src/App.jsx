import React from 'react'
import { useApi } from './hooks/useApi'
import StatsCards from './components/StatsCards'
import RoutingChart from './components/RoutingChart'
import SeverityChart from './components/SeverityChart'
import TopClassifications from './components/TopClassifications'
import LogExplorer from './components/LogExplorer'
import HealthStatus from './components/HealthStatus'

export default function App() {
  const { data: metrics, loading: metricsLoading } = useApi('/dashboard', { interval: 15000 })
  const { data: health } = useApi('/health', { interval: 30000 })

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-sm font-bold">
              IL
            </div>
            <div>
              <h1 className="text-lg font-semibold">IntelliLog AI</h1>
              <p className="text-xs text-gray-500">Log Classification & Monitoring</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {health && (
              <span className={`px-2 py-1 rounded-full text-xs ${
                health.status === 'healthy' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
              }`}>
                {health.status}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Stats Cards Row */}
        {metricsLoading ? (
          <div className="text-center py-8 text-gray-500">Loading metrics...</div>
        ) : (
          <StatsCards metrics={metrics} />
        )}

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <RoutingChart metrics={metrics} />
          <SeverityChart metrics={metrics} />
          <TopClassifications metrics={metrics} />
        </div>

        {/* Health + Info Row */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-1">
            <HealthStatus health={health} />
          </div>
          <div className="lg:col-span-3">
            <LogExplorer />
          </div>
        </div>
      </main>
    </div>
  )
}
