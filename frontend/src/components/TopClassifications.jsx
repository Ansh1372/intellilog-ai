import React from 'react'

export default function TopClassifications({ metrics }) {
  if (!metrics || !metrics.top_classifications) return null

  const items = metrics.top_classifications || []

  return (
    <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
      <h3 className="text-sm font-medium text-gray-400 mb-4">Top Classifications</h3>
      {items.length === 0 ? (
        <p className="text-gray-500 text-center py-4">No data yet</p>
      ) : (
        <div className="space-y-3">
          {items.map((item, i) => {
            const max = items[0].count
            const percent = (item.count / max) * 100
            return (
              <div key={i}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-300">{item.classification}</span>
                  <span className="text-gray-500">{item.count}</span>
                </div>
                <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all"
                    style={{ width: `${percent}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
