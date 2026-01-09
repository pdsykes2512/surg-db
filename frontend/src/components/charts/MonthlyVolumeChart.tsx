import React from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { ChartWrapper } from './ChartWrapper'

interface MonthlyVolumeData {
  month: string
  surgeries: number
}

interface MonthlyVolumeChartProps {
  data: MonthlyVolumeData[]
  loading?: boolean
  height?: number
}

/**
 * Area chart showing monthly surgical volumes
 */
export function MonthlyVolumeChart({
  data,
  loading = false,
  height = 300
}: MonthlyVolumeChartProps) {
  const empty = !data || data.length === 0

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-semibold text-gray-900 mb-1">{label}</p>
          <p className="text-sm text-gray-700">
            Surgeries: <span className="font-medium">{payload[0].value}</span>
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <ChartWrapper
      title="Monthly Surgical Volume"
      subtitle="Number of surgeries performed per month"
      loading={loading}
      empty={empty}
      emptyMessage="No volume data available"
      height={height}
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorSurgeries" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="month"
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            label={{ value: 'Number of Surgeries', angle: -90, position: 'insideLeft', style: { fontSize: '12px' } }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="surgeries"
            stroke="#3b82f6"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorSurgeries)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartWrapper>
  )
}
