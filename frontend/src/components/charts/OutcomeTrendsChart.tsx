import React from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { ChartWrapper } from './ChartWrapper'

interface OutcomeTrendsData {
  period: string
  complicationRate: number
  mortality30d: number
  mortality90d: number
  readmissionRate: number
  rttRate: number
}

interface OutcomeTrendsChartProps {
  data: OutcomeTrendsData[]
  loading?: boolean
  height?: number
}

/**
 * Line chart showing trends in surgical outcome metrics over time
 */
export function OutcomeTrendsChart({ data, loading = false, height = 400 }: OutcomeTrendsChartProps) {
  const empty = !data || data.length === 0

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-semibold text-gray-900 mb-2">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {entry.value.toFixed(2)}%
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <ChartWrapper
      title="Surgical Outcome Trends"
      subtitle="Track key outcome metrics over time"
      loading={loading}
      empty={empty}
      emptyMessage="No outcome data available for the selected period"
      height={height}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="period"
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            label={{ value: 'Rate (%)', angle: -90, position: 'insideLeft', style: { fontSize: '12px' } }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: '12px' }}
            iconType="line"
          />
          <Line
            type="monotone"
            dataKey="complicationRate"
            name="Complications"
            stroke="#ef4444"
            strokeWidth={2}
            dot={{ fill: '#ef4444', r: 4 }}
            activeDot={{ r: 6 }}
          />
          <Line
            type="monotone"
            dataKey="mortality30d"
            name="30-day Mortality"
            stroke="#dc2626"
            strokeWidth={2}
            dot={{ fill: '#dc2626', r: 4 }}
            activeDot={{ r: 6 }}
          />
          <Line
            type="monotone"
            dataKey="mortality90d"
            name="90-day Mortality"
            stroke="#991b1b"
            strokeWidth={2}
            dot={{ fill: '#991b1b', r: 4 }}
            activeDot={{ r: 6 }}
          />
          <Line
            type="monotone"
            dataKey="readmissionRate"
            name="Readmissions"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={{ fill: '#f59e0b', r: 4 }}
            activeDot={{ r: 6 }}
          />
          <Line
            type="monotone"
            dataKey="rttRate"
            name="Return to Theatre"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ fill: '#3b82f6', r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartWrapper>
  )
}
