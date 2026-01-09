import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts'
import { ChartWrapper } from './ChartWrapper'

interface ComplicationData {
  category: string
  rate: number
  count: number
  total: number
}

interface ComplicationRateChartProps {
  data: ComplicationData[]
  loading?: boolean
  height?: number
  title?: string
  subtitle?: string
}

// Color scale from green (low) to red (high)
const getColorByRate = (rate: number): string => {
  if (rate < 5) return '#10b981' // green-500
  if (rate < 10) return '#84cc16' // lime-500
  if (rate < 15) return '#fbbf24' // yellow-400
  if (rate < 20) return '#f59e0b' // amber-500
  if (rate < 25) return '#f97316' // orange-500
  return '#ef4444' // red-500
}

/**
 * Bar chart showing complication rates across different categories
 */
export function ComplicationRateChart({
  data,
  loading = false,
  height = 350,
  title = 'Complication Rates by Category',
  subtitle = 'Comparison of complication rates across different surgical categories'
}: ComplicationRateChartProps) {
  const empty = !data || data.length === 0

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-semibold text-gray-900 mb-2">{data.category}</p>
          <p className="text-sm text-gray-700">
            Rate: <span className="font-medium">{data.rate.toFixed(2)}%</span>
          </p>
          <p className="text-sm text-gray-500">
            {data.count} complications out of {data.total} cases
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <ChartWrapper
      title={title}
      subtitle={subtitle}
      loading={loading}
      empty={empty}
      emptyMessage="No complication data available"
      height={height}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 5, right: 30, left: 20, bottom: 60 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="category"
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            label={{ value: 'Complication Rate (%)', angle: -90, position: 'insideLeft', style: { fontSize: '12px' } }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
            payload={[{ value: 'Complication Rate', type: 'square', color: '#3b82f6' }]}
          />
          <Bar dataKey="rate" name="Complication Rate" radius={[8, 8, 0, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getColorByRate(entry.rate)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  )
}
