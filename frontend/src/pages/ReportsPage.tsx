import { useState, useEffect } from 'react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { apiService } from '../services/api'

interface SummaryReport {
  total_surgeries: number
  complication_rate: number
  readmission_rate: number
  mortality_rate: number
  return_to_theatre_rate: number
  escalation_rate: number
  avg_length_of_stay_days: number
  urgency_breakdown: Record<string, number>
}

interface SurgeonPerformance {
  _id: string
  total_surgeries: number
  complication_rate: number
  readmission_rate: number
  avg_duration: number
  avg_los: number
}

export function ReportsPage() {
  const [summary, setSummary] = useState<SummaryReport | null>(null)
  const [surgeonPerf, setSurgeonPerf] = useState<SurgeonPerformance[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadReports()
  }, [])

  const loadReports = async () => {
    try {
      setLoading(true)
      const [summaryRes, surgeonRes] = await Promise.all([
        apiService.reports.summary(),
        apiService.reports.surgeonPerformance()
      ])
      setSummary(summaryRes.data)
      setSurgeonPerf(surgeonRes.data.surgeons || [])
    } catch (error) {
      console.error('Failed to load reports:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Reports & Analytics"
          subtitle="View comprehensive surgical outcomes and performance metrics"
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          }
        />
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  if (!summary || summary.total_surgeries === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Reports & Analytics"
          subtitle="View comprehensive surgical outcomes and performance metrics"
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          }
        />
        <Card>
          <div className="text-center py-12">
            <svg className="mx-auto w-16 h-16 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Data Available</h3>
            <p className="text-gray-500">Reports will be generated once surgery records are added to the system</p>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports & Analytics"
        subtitle="View comprehensive surgical outcomes and performance metrics"
        icon={
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        }
      />

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card hover>
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600 mb-2">{summary.total_surgeries}</div>
            <div className="text-sm text-gray-500">Total Procedures</div>
          </div>
        </Card>
        <Card hover>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600 mb-2">
              {(100 - summary.complication_rate).toFixed(1)}%
            </div>
            <div className="text-sm text-gray-500">Success Rate</div>
            <div className="text-xs text-gray-400 mt-1">
              {summary.complication_rate.toFixed(1)}% complication rate
            </div>
          </div>
        </Card>
        <Card hover>
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-600 mb-2">
              {summary.avg_length_of_stay_days.toFixed(1)} days
            </div>
            <div className="text-sm text-gray-500">Avg Length of Stay</div>
          </div>
        </Card>
        <Card hover>
          <div className="text-center">
            <div className="text-3xl font-bold text-orange-600 mb-2">
              {summary.readmission_rate.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-500">30-Day Readmission</div>
          </div>
        </Card>
      </div>

      {/* Outcome Metrics */}
      <Card>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Outcome Metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="border-l-4 border-yellow-500 pl-4">
            <div className="text-2xl font-bold text-gray-900">{summary.return_to_theatre_rate.toFixed(1)}%</div>
            <div className="text-sm text-gray-600">Return to Theatre</div>
          </div>
          <div className="border-l-4 border-red-500 pl-4">
            <div className="text-2xl font-bold text-gray-900">{summary.escalation_rate.toFixed(1)}%</div>
            <div className="text-sm text-gray-600">ICU/HDU Escalation</div>
          </div>
          <div className="border-l-4 border-gray-500 pl-4">
            <div className="text-2xl font-bold text-gray-900">{summary.mortality_rate.toFixed(1)}%</div>
            <div className="text-sm text-gray-600">30-Day Mortality</div>
          </div>
        </div>
      </Card>

      {/* Urgency Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Surgery Urgency</h3>
          <div className="space-y-3">
            {Object.entries(summary.urgency_breakdown).map(([urgency, count]) => {
              const percentage = (count / summary.total_surgeries * 100).toFixed(1)
              const colors: Record<string, string> = {
                elective: 'bg-green-500',
                urgent: 'bg-orange-500',
                emergency: 'bg-red-500'
              }
              return (
                <div key={urgency}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="capitalize font-medium text-gray-700">{urgency}</span>
                    <span className="text-gray-600">{count} ({percentage}%)</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${colors[urgency] || 'bg-gray-500'}`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      </div>

      {/* Surgeon Performance */}
      {surgeonPerf.length > 0 && (
        <Card>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Surgeon Performance</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Surgeon
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Total Cases
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Complication Rate
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Readmission Rate
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Avg Duration (min)
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Avg LOS (days)
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {surgeonPerf.map((surgeon) => (
                  <tr key={surgeon._id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {surgeon._id || 'Unknown'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {surgeon.total_surgeries}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                        surgeon.complication_rate < 5 ? 'bg-green-100 text-green-800' :
                        surgeon.complication_rate < 10 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {surgeon.complication_rate.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {surgeon.readmission_rate.toFixed(1)}%
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {surgeon.avg_duration?.toFixed(0) || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {surgeon.avg_los?.toFixed(1) || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
