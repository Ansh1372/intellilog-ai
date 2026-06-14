import React from 'react'

function StatCard({ title, value, subtitle, color = 'blue' }) {
  const colors = {
    blue: 'border-blue-500 bg-blue-500/10',
    green: 'border-green-500 bg-green-500/10',
    yellow: 'border-yellow-500 bg-yellow-500/10',
    red: 'border-red-500 bg-red-500/10',
    purple: 'border-purple-500 bg-purple-500/10',
  }

  return (
    <div className={`rounded-lg border-l-4 ${colors[color]} p-4`}>
      <p className="text-sm text-gray-400">{title}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
    </div>
  )
}

export default function StatsCards({ metrics }) {
  if (!metrics) return null

  const total = metrics.total_logs || 0
  const regex = metrics.regex_hits || 0
  const ml = metrics.ml_hits || 0
  const llm = metrics.llm_hits || 0

  // Cost savings estimate: $0.003 per LLM call saved
  const llmSaved = total - llm
  const costSaved = (llmSaved * 0.003).toFixed(2)

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      <StatCard
        title="Total Logs"
        value={total.toLocaleString()}
        subtitle="All classified logs"
        color="blue"
      />
      <StatCard
        title="Regex (Stage 1)"
        value={regex.toLocaleString()}
        subtitle={total ? `${((regex / total) * 100).toFixed(1)}% of traffic` : '0%'}
        color="green"
      />
      <StatCard
        title="ML (Stage 2)"
        value={ml.toLocaleString()}
        subtitle={total ? `${((ml / total) * 100).toFixed(1)}% of traffic` : '0%'}
        color="yellow"
      />
      <StatCard
        title="LLM (Stage 3)"
        value={llm.toLocaleString()}
        subtitle={total ? `${((llm / total) * 100).toFixed(1)}% of traffic` : '0%'}
        color="red"
      />
      <StatCard
        title="Cost Saved"
        value={`$${costSaved}`}
        subtitle={`${llmSaved.toLocaleString()} LLM calls avoided`}
        color="purple"
      />
    </div>
  )
}
