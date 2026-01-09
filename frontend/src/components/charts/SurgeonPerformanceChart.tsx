import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { ChartWrapper } from './ChartWrapper'

interface SurgeonPerformanceData {
  surgeon: string
  totalCases: number
  complicationRate: number
  mortality30d: number
  readmissionRate: number
  rttRate: number
}

interface SurgeonPerformanceChartProps {
  data: SurgeonPerformanceData[]
  loading?: boolean
  height?: number
  metric?: 'complicationRate' | 'mortality30d' | 'readmissionRate' | 'rttRate'
}

const metricConfig = {
  complicationRate: {
    label: 'Complication Rate',
    color: '#ef4444',
    dataKey: 'complicationRate'
  },
  mortality30d: {
    label: '30-day Mortality',
    color: '#dc2626',
    dataKey: 'mortality30d'
  },
  readmissionRate: {
    label: 'Readmission Rate',
    color: '#f59e0b',
    dataKey: 'readmissionRate'
  },
  rttRate: {
    label: 'Return to Theatre',
    color: '#3b82f6',
    dataKey: 'rttRate'
  }
}

/**
 * Bar chart comparing surgeon performance metrics
 */
export function SurgeonPerformanceChart({
  data,
  loading = false,
  height = 400,
  metric = 'complicationRate'
}: SurgeonPerformanceChartProps) {
  const empty = !data || data.length === 0
  const config = metricConfig[metric]

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-semibold text-gray-900 mb-2">{data.surgeon}</p>
          <p className="text-sm text-gray-700">
            {config.label}: <span className="font-medium">{data[metric].toFixed(2)}%</span>
          </p>
          <p className="text-sm text-gray-500">
            Total cases: {data.totalCases}
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <ChartWrapper
      title={`Surgeon Performance: ${config.label}`}
      subtitle="Comparison across surgeons (minimum 10 cases)"
      loading={loading}
      empty={empty}
      emptyMessage="No surgeon performance data available"
      height={height}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 5, right: 30, left: 20, bottom: 80 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="surgeon"
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            angle={-45}
            textAnchor="end"
            height={100}
          />
          <YAxis
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            label={{ value: 'Rate (%)', angle: -90, position: 'insideLeft', style: { fontSize: '12px' } }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
          />
          <Bar
            dataKey={metric}
            name={config.label}
            fill={config.color}
            radius={[8, 8, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  )
}
