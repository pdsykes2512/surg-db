import React from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { ChartWrapper } from './ChartWrapper'

interface TreatmentDistributionData {
  name: string
  value: number
  color?: string
}

interface TreatmentDistributionChartProps {
  data: TreatmentDistributionData[]
  loading?: boolean
  height?: number
}

// Default color palette
const DEFAULT_COLORS = [
  '#3b82f6', // blue-500
  '#10b981', // green-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#8b5cf6', // purple-500
  '#ec4899', // pink-500
  '#14b8a6', // teal-500
  '#f97316', // orange-500
]

/**
 * Pie chart showing distribution of treatment types
 */
export function TreatmentDistributionChart({
  data,
  loading = false,
  height = 350
}: TreatmentDistributionChartProps) {
  const empty = !data || data.length === 0

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0]
      const total = payload[0].payload.percent
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-semibold text-gray-900 mb-1">{data.name}</p>
          <p className="text-sm text-gray-700">
            Count: <span className="font-medium">{data.value}</span>
          </p>
          <p className="text-sm text-gray-500">
            {total ? `${total.toFixed(1)}%` : ''}
          </p>
        </div>
      )
    }
    return null
  }

  const renderLabel = (entry: any) => {
    return `${entry.name}: ${entry.value}`
  }

  return (
    <ChartWrapper
      title="Treatment Type Distribution"
      subtitle="Breakdown of treatments by type"
      loading={loading}
      empty={empty}
      emptyMessage="No treatment data available"
      height={height}
    >
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderLabel}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
            style={{ fontSize: '12px' }}
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: '12px' }}
            layout="horizontal"
            verticalAlign="bottom"
            align="center"
          />
        </PieChart>
      </ResponsiveContainer>
    </ChartWrapper>
  )
}
