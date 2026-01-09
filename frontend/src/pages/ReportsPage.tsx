import { useState, useEffect } from 'react'
import { PageHeader } from '../components/common/PageHeader'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Table, TableHeader, TableBody, TableRow, TableHeadCell, TableCell } from '../components/common/Table'
import { apiService } from '../services/api'
import { 
  OutcomeTrendsChart, 
  ComplicationRateChart, 
  SurgeonPerformanceChart 
} from '../components/charts'

interface SummaryReport {
  total_surgeries: number
  complication_rate: number
  readmission_rate: number
  mortality_30d_rate: number
  mortality_90d_rate: number
  return_to_theatre_rate: number
  escalation_rate: number
  median_length_of_stay_days: number
  yearly_breakdown?: {
    [year: string]: {
      total_surgeries: number
      complication_rate: number
      readmission_rate: number
      mortality_30d_rate: number
      mortality_90d_rate: number
      return_to_theatre_rate: number
      escalation_rate: number
      median_length_of_stay_days: number
    }
  }
  urgency_breakdown?: Record<string, number>
  asa_breakdown?: Record<string, number>
}

interface SurgeonPerformance {
  _id: string
  total_surgeries: number
  complication_rate: number
  readmission_rate: number
  return_to_theatre_rate: number
  mortality_30d_rate: number
  mortality_90d_rate: number
  median_duration: number | null
  median_los: number | null
}

interface FieldStat {
  field: string
  category: string
  complete_count: number
  total_count: number
  completeness: number
  missing_count: number
}

interface CategoryStat {
  name: string
  total_fields: number
  avg_completeness: number
  fields: FieldStat[]
}

interface DataQualityReport {
  total_episodes: number
  total_treatments: number
  total_tumours: number
  overall_completeness: number
  categories: CategoryStat[]
  episode_fields?: Array<{
    field: string
    completeness: number
    complete_count: number
    total_count: number
  }>
  treatment_fields?: Array<{
    field: string
    completeness: number
    complete_count: number
    total_count: number
  }>
}

interface COSDField {
  field: string
  category: string
  complete_count: number
  total_count: number
  completeness: number
  missing_count: number
}

interface COSDCategory {
  category: string
  field_count: number
  avg_completeness: number
  fields: COSDField[]
}

interface COSDReport {
  year: number | null
  total_treatments: number
  total_episodes: number
  total_patients: number
  overall_completeness: number
  categories: COSDCategory[]
}

type Tab = 'outcomes' | 'quality'

export function ReportsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('outcomes')
  const [summary, setSummary] = useState<SummaryReport | null>(null)
  const [surgeonPerf, setSurgeonPerf] = useState<SurgeonPerformance[]>([])
  const [dataQuality, setDataQuality] = useState<DataQualityReport | null>(null)
  const [cosdData, setCosdData] = useState<COSDReport | null>(null)
  const [cosdYear, setCosdYear] = useState<number | null>(2024)
  const [loading, setLoading] = useState(true)
  const [chartData, setChartData] = useState<{
    outcomeTrends: any[]
    complicationByCategory: any[]
    surgeonPerformance: any[]
    loading: boolean
  }>({
    outcomeTrends: [],
    complicationByCategory: [],
    surgeonPerformance: [],
    loading: true
  })
  const [selectedMetric, setSelectedMetric] = useState<'complicationRate' | 'mortality30d' | 'readmissionRate' | 'rttRate'>('complicationRate')

  useEffect(() => {
    loadReports()
    if (activeTab === 'outcomes') {
      loadChartData()
    }
  }, [activeTab])

  const loadChartData = async () => {
    try {
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      
      // Fetch outcome trends and complication breakdown
      const [trendsRes, complicationsRes] = await Promise.all([
        fetch(`${API_URL}/reports/outcome-trends?period=quarterly&start_year=2023&end_year=2025`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        }),
        fetch(`${API_URL}/reports/complication-by-category`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        })
      ])

      const trendsData = await trendsRes.json()
      const complicationsData = await complicationsRes.json()

      // Transform surgeon performance data  
      const surgeonData = surgeonPerf
        .filter(s => s.total_surgeries >= 10) // Only show surgeons with 10+ cases
        .map(s => ({
          surgeon: s._id,
          totalCases: s.total_surgeries,
          complicationRate: s.complication_rate,
          mortality30d: s.mortality_30d_rate,
          readmissionRate: s.readmission_rate,
          rttRate: s.return_to_theatre_rate
        }))

      setChartData({
        outcomeTrends: trendsData.trends || [],
        complicationByCategory: complicationsData.byUrgency || [],
        surgeonPerformance: surgeonData,
        loading: false
      })
    } catch (error) {
      console.error('Failed to load chart data:', error)
      setChartData(prev => ({ ...prev, loading: false }))
    }
  }

  useEffect(() => {
    loadReports()
  }, [activeTab])

  useEffect(() => {
    if (activeTab === 'quality') {
      loadCOSDData()
    }
  }, [cosdYear, activeTab])

  const loadReports = async () => {
    try {
      setLoading(true)
      if (activeTab === 'outcomes') {
        const [summaryRes, surgeonRes] = await Promise.all([
          apiService.reports.summary(),
          apiService.reports.surgeonPerformance()
        ])
        setSummary(summaryRes.data)
        setSurgeonPerf(surgeonRes.data.surgeons || [])
        
        // Load chart data after surgeon data is available
        setTimeout(() => loadChartData(), 100)
      } else {
        // Use /api for relative URLs (uses Vite proxy)
        const API_URL = import.meta.env.VITE_API_URL || '/api'
        const response = await fetch(`${API_URL}/reports/data-quality`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        const data = await response.json()
        setDataQuality(data)
      }
    } catch (error) {
      console.error('Failed to load reports:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadCOSDData = async () => {
    try {
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const yearParam = cosdYear ? `?year=${cosdYear}` : ''
      const response = await fetch(`${API_URL}/reports/cosd-completeness${yearParam}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      const data = await response.json()
      setCosdData(data)
    } catch (error) {
      console.error('Failed to load COSD data:', error)
    }
  }

  const downloadExcel = async (endpoint: string, filename: string) => {
    try {
      // Endpoint already includes /api prefix, so use empty string for relative URLs
      const API_BASE = import.meta.env.VITE_API_URL === '/api' ? '' : (import.meta.env.VITE_API_URL?.replace('/api', '') || 'http://localhost:8000')
      const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      
      if (!response.ok) throw new Error('Failed to download')
      
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Failed to download Excel:', error)
      alert('Failed to download report. Please try again.')
    }
  }

  // For data quality: higher is better
  const getCompletenessColor = (percentage: number) => {
    if (percentage >= 90) return 'text-green-600 bg-green-100'
    if (percentage >= 70) return 'text-yellow-600 bg-yellow-100'
    if (percentage >= 50) return 'text-orange-600 bg-orange-100'
    return 'text-red-600 bg-red-100'
  }

  const getCompletenessBarColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-green-500'
    if (percentage >= 70) return 'bg-yellow-500'
    if (percentage >= 50) return 'bg-orange-500'
    return 'bg-red-500'
  }

  const getCompletenessCardColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-green-50 border-green-200'
    if (percentage >= 70) return 'bg-yellow-50 border-yellow-200'
    if (percentage >= 50) return 'bg-orange-50 border-orange-200'
    return 'bg-red-50 border-red-200'
  }

  const getCompletenessTextColor = (percentage: number) => {
    if (percentage >= 90) return 'text-green-600'
    if (percentage >= 70) return 'text-yellow-600'
    if (percentage >= 50) return 'text-orange-600'
    return 'text-red-600'
  }

  // For outcomes: lower is better
  // Based on published NBOCA and colorectal surgery benchmarks
  const getOutcomeColor = (rate: number, metric: 'complication' | 'readmission' | 'mortality' | 'return_to_theatre') => {
    if (metric === 'complication') {
      // Complications: <15% excellent, 15-25% acceptable, >25% concerning
      if (rate < 15) return 'text-green-600 bg-green-100'
      if (rate < 25) return 'text-yellow-600 bg-yellow-100'
      return 'text-red-600 bg-red-100'
    } else if (metric === 'readmission') {
      // 30-day readmissions: <8% excellent, 8-12% acceptable, >12% concerning
      if (rate < 8) return 'text-green-600 bg-green-100'
      if (rate < 12) return 'text-yellow-600 bg-yellow-100'
      return 'text-red-600 bg-red-100'
    } else if (metric === 'return_to_theatre') {
      // Return to theatre: <5% excellent, 5-10% acceptable, >10% concerning
      if (rate < 5) return 'text-green-600 bg-green-100'
      if (rate < 10) return 'text-yellow-600 bg-yellow-100'
      return 'text-red-600 bg-red-100'
    } else {
      // 30-day mortality: <2% excellent, 2-5% acceptable, >5% concerning
      if (rate < 2) return 'text-green-600 bg-green-100'
      if (rate < 5) return 'text-yellow-600 bg-yellow-100'
      return 'text-red-600 bg-red-100'
    }
  }

  // Text-only color for yearly breakdown (no background)
  const getYearlyTextColor = (rate: number, metric: 'complication' | 'readmission' | 'mortality' | 'return_to_theatre') => {
    if (metric === 'complication') {
      if (rate < 15) return 'text-green-600'
      if (rate < 25) return 'text-yellow-600'
      return 'text-red-600'
    } else if (metric === 'readmission') {
      if (rate < 8) return 'text-green-600'
      if (rate < 12) return 'text-yellow-600'
      return 'text-red-600'
    } else if (metric === 'return_to_theatre') {
      if (rate < 5) return 'text-green-600'
      if (rate < 10) return 'text-yellow-600'
      return 'text-red-600'
    } else {
      // mortality
      if (rate < 2) return 'text-green-600'
      if (rate < 5) return 'text-yellow-600'
      return 'text-red-600'
    }
  }

  const getOutcomeCardColor = (rate: number, metric: 'complication' | 'readmission' | 'mortality') => {
    if (metric === 'complication') {
      if (rate < 15) return 'bg-green-50 border-green-200'
      if (rate < 25) return 'bg-yellow-50 border-yellow-200'
      return 'bg-red-50 border-red-200'
    } else if (metric === 'readmission') {
      if (rate < 8) return 'bg-green-50 border-green-200'
      if (rate < 12) return 'bg-yellow-50 border-yellow-200'
      return 'bg-red-50 border-red-200'
    } else {
      if (rate < 2) return 'bg-green-50 border-green-200'
      if (rate < 5) return 'bg-yellow-50 border-yellow-200'
      return 'bg-red-50 border-red-200'
    }
  }

  const getOutcomeTextColor = (rate: number, metric: 'complication' | 'readmission' | 'mortality') => {
    if (metric === 'complication') {
      if (rate < 15) return 'text-green-600'
      if (rate < 25) return 'text-yellow-600'
      return 'text-red-600'
    } else if (metric === 'readmission') {
      if (rate < 8) return 'text-green-600'
      if (rate < 12) return 'text-yellow-600'
      return 'text-red-600'
    } else {
      if (rate < 2) return 'text-green-600'
      if (rate < 5) return 'text-yellow-600'
      return 'text-red-600'
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Reports & Analytics" />

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('outcomes')}
            className={`${
              activeTab === 'outcomes'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
          >
            Surgery Outcomes
          </button>
          <button
            onClick={() => setActiveTab('quality')}
            className={`${
              activeTab === 'quality'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
          >
            Data Quality
          </button>
        </nav>
      </div>

      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-600">Loading reports...</p>
        </div>
      )}

      {/* Outcomes Tab */}
      {!loading && activeTab === 'outcomes' && summary && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-6">
              <h3 className="text-sm font-medium text-gray-500">Total Resections</h3>
              <p className="mt-2 text-3xl font-bold text-gray-900">{summary.total_surgeries}</p>
              {summary.yearly_breakdown && (
                <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-600 space-y-1">
                  <div className="flex justify-between">
                    <span>2025:</span>
                    <span className="font-semibold">{summary.yearly_breakdown['2025']?.total_surgeries || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2024:</span>
                    <span className="font-semibold">{summary.yearly_breakdown['2024']?.total_surgeries || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2023:</span>
                    <span className="font-semibold">{summary.yearly_breakdown['2023']?.total_surgeries || 0}</span>
                  </div>
                </div>
              )}
            </Card>

            <Card className="p-6">
              <h3 className="text-sm font-medium text-gray-500">Median Length of Stay</h3>
              <p className="mt-2 text-3xl font-bold text-gray-900">
                {summary.median_length_of_stay_days 
                  ? (summary.median_length_of_stay_days % 1 === 0 
                      ? summary.median_length_of_stay_days.toFixed(0) 
                      : summary.median_length_of_stay_days.toFixed(1))
                  : 'N/A'} days
              </p>
              {summary.yearly_breakdown && (
                <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-600 space-y-1">
                  <div className="flex justify-between">
                    <span>2025:</span>
                    <span className="font-semibold">
                      {summary.yearly_breakdown['2025']?.median_length_of_stay_days 
                        ? (summary.yearly_breakdown['2025'].median_length_of_stay_days % 1 === 0
                            ? summary.yearly_breakdown['2025'].median_length_of_stay_days.toFixed(0)
                            : summary.yearly_breakdown['2025'].median_length_of_stay_days.toFixed(1))
                        : '0'} days
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>2024:</span>
                    <span className="font-semibold">
                      {summary.yearly_breakdown['2024']?.median_length_of_stay_days 
                        ? (summary.yearly_breakdown['2024'].median_length_of_stay_days % 1 === 0
                            ? summary.yearly_breakdown['2024'].median_length_of_stay_days.toFixed(0)
                            : summary.yearly_breakdown['2024'].median_length_of_stay_days.toFixed(1))
                        : '0'} days
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>2023:</span>
                    <span className="font-semibold">
                      {summary.yearly_breakdown['2023']?.median_length_of_stay_days 
                        ? (summary.yearly_breakdown['2023'].median_length_of_stay_days % 1 === 0
                            ? summary.yearly_breakdown['2023'].median_length_of_stay_days.toFixed(0)
                            : summary.yearly_breakdown['2023'].median_length_of_stay_days.toFixed(1))
                        : '0'} days
                    </span>
                  </div>
                </div>
              )}
            </Card>

            <Card className={`p-6 border-2 ${getOutcomeCardColor(summary.readmission_rate, 'readmission')}`}>
              <h3 className="text-sm font-medium text-gray-600">Readmission Rate</h3>
              <p className={`mt-2 text-3xl font-bold ${getOutcomeTextColor(summary.readmission_rate, 'readmission')}`}>
                {summary.readmission_rate.toFixed(1)}%
              </p>
              {summary.yearly_breakdown && (
                <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-600 space-y-1">
                  <div className="flex justify-between">
                    <span>2025:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2025']?.readmission_rate || 0, 'readmission')}`}>{summary.yearly_breakdown['2025']?.readmission_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2024:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2024']?.readmission_rate || 0, 'readmission')}`}>{summary.yearly_breakdown['2024']?.readmission_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2023:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2023']?.readmission_rate || 0, 'readmission')}`}>{summary.yearly_breakdown['2023']?.readmission_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                </div>
              )}
            </Card>

            <Card className={`p-6 border-2 ${getOutcomeCardColor(summary.escalation_rate, 'complication')}`}>
              <h3 className="text-sm font-medium text-gray-600">ICU Escalation</h3>
              <p className={`mt-2 text-3xl font-bold ${getOutcomeTextColor(summary.escalation_rate, 'complication')}`}>
                {summary.escalation_rate.toFixed(1)}%
              </p>
              {summary.yearly_breakdown && (
                <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-600 space-y-1">
                  <div className="flex justify-between">
                    <span>2025:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2025']?.escalation_rate || 0, 'complication')}`}>{summary.yearly_breakdown['2025']?.escalation_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2024:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2024']?.escalation_rate || 0, 'complication')}`}>{summary.yearly_breakdown['2024']?.escalation_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2023:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2023']?.escalation_rate || 0, 'complication')}`}>{summary.yearly_breakdown['2023']?.escalation_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                </div>
              )}
            </Card>

            <Card className={`p-6 border-2 ${getOutcomeCardColor(summary.complication_rate, 'complication')}`}>
              <h3 className="text-sm font-medium text-gray-600">Complication Rate</h3>
              <p className={`mt-2 text-3xl font-bold ${getOutcomeTextColor(summary.complication_rate, 'complication')}`}>
                {summary.complication_rate.toFixed(1)}%
              </p>
              {summary.yearly_breakdown && (
                <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-600 space-y-1">
                  <div className="flex justify-between">
                    <span>2025:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2025']?.complication_rate || 0, 'complication')}`}>{summary.yearly_breakdown['2025']?.complication_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2024:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2024']?.complication_rate || 0, 'complication')}`}>{summary.yearly_breakdown['2024']?.complication_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2023:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2023']?.complication_rate || 0, 'complication')}`}>{summary.yearly_breakdown['2023']?.complication_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                </div>
              )}
            </Card>

            <Card className={`p-6 border-2 ${getOutcomeCardColor(summary.return_to_theatre_rate, 'complication')}`}>
              <h3 className="text-sm font-medium text-gray-600">Return to Theatre</h3>
              <p className={`mt-2 text-3xl font-bold ${getOutcomeTextColor(summary.return_to_theatre_rate, 'complication')}`}>
                {summary.return_to_theatre_rate.toFixed(1)}%
              </p>
              {summary.yearly_breakdown && (
                <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-600 space-y-1">
                  <div className="flex justify-between">
                    <span>2025:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2025']?.return_to_theatre_rate || 0, 'return_to_theatre')}`}>{summary.yearly_breakdown['2025']?.return_to_theatre_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2024:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2024']?.return_to_theatre_rate || 0, 'return_to_theatre')}`}>{summary.yearly_breakdown['2024']?.return_to_theatre_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2023:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2023']?.return_to_theatre_rate || 0, 'return_to_theatre')}`}>{summary.yearly_breakdown['2023']?.return_to_theatre_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                </div>
              )}
            </Card>

            <Card className={`p-6 border-2 ${getOutcomeCardColor(summary.mortality_30d_rate, 'mortality')}`}>
              <h3 className="text-sm font-medium text-gray-600">30-Day Mortality</h3>
              <p className={`mt-2 text-3xl font-bold ${getOutcomeTextColor(summary.mortality_30d_rate, 'mortality')}`}>
                {summary.mortality_30d_rate.toFixed(1)}%
              </p>
              {summary.yearly_breakdown && (
                <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-600 space-y-1">
                  <div className="flex justify-between">
                    <span>2025:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2025']?.mortality_30d_rate || 0, 'mortality')}`}>{summary.yearly_breakdown['2025']?.mortality_30d_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2024:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2024']?.mortality_30d_rate || 0, 'mortality')}`}>{summary.yearly_breakdown['2024']?.mortality_30d_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2023:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2023']?.mortality_30d_rate || 0, 'mortality')}`}>{summary.yearly_breakdown['2023']?.mortality_30d_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                </div>
              )}
            </Card>

            <Card className={`p-6 border-2 ${getOutcomeCardColor(summary.mortality_90d_rate, 'mortality')}`}>
              <h3 className="text-sm font-medium text-gray-600">90-Day Mortality</h3>
              <p className={`mt-2 text-3xl font-bold ${getOutcomeTextColor(summary.mortality_90d_rate, 'mortality')}`}>
                {summary.mortality_90d_rate.toFixed(1)}%
              </p>
              {summary.yearly_breakdown && (
                <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-600 space-y-1">
                  <div className="flex justify-between">
                    <span>2025:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2025']?.mortality_90d_rate || 0, 'mortality')}`}>{summary.yearly_breakdown['2025']?.mortality_90d_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2024:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2024']?.mortality_90d_rate || 0, 'mortality')}`}>{summary.yearly_breakdown['2024']?.mortality_90d_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2023:</span>
                    <span className={`font-semibold ${getYearlyTextColor(summary.yearly_breakdown['2023']?.mortality_90d_rate || 0, 'mortality')}`}>{summary.yearly_breakdown['2023']?.mortality_90d_rate?.toFixed(1) || '0.0'}%</span>
                  </div>
                </div>
              )}
            </Card>
          </div>

          {/* Urgency Breakdown */}
          {summary.urgency_breakdown && Object.keys(summary.urgency_breakdown).length > 0 && (
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Surgery Urgency Breakdown</h3>
              <div className="grid grid-cols-3 gap-4">
                {['elective', 'urgent', 'emergency'].map((urgency) => {
                  const count = summary.urgency_breakdown?.[urgency] || 0
                  const percentage = ((count / summary.total_surgeries) * 100).toFixed(1)
                  return (
                    <div key={urgency} className="text-center p-4 bg-gray-50 rounded-lg">
                      <p className="text-3xl font-bold text-gray-900">{count}</p>
                      <p className="text-sm text-gray-500 capitalize mt-1">{urgency}</p>
                      <p className="text-xs text-gray-400 mt-1">{percentage}%</p>
                    </div>
                  )
                })}
              </div>
            </Card>
          )}

          {/* ASA Grade Breakdown */}
          {summary.asa_breakdown && Object.keys(summary.asa_breakdown).length > 0 && (
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">ASA Grade Stratification</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 sm:gap-4">
                {['I', 'II', 'III', 'IV', 'V'].map((grade) => {
                  const count = summary.asa_breakdown?.[grade] || 0
                  const percentage = ((count / summary.total_surgeries) * 100).toFixed(1)

                  // Color coding based on ASA grade risk
                  const getAsaColor = (asaGrade: string) => {
                    if (asaGrade === 'I') return 'bg-green-50 border-green-200'
                    if (asaGrade === 'II') return 'bg-blue-50 border-blue-200'
                    if (asaGrade === 'III') return 'bg-yellow-50 border-yellow-200'
                    if (asaGrade === 'IV') return 'bg-orange-50 border-orange-200'
                    return 'bg-red-50 border-red-200'
                  }

                  const getAsaTextColor = (asaGrade: string) => {
                    if (asaGrade === 'I') return 'text-green-700'
                    if (asaGrade === 'II') return 'text-blue-700'
                    if (asaGrade === 'III') return 'text-yellow-700'
                    if (asaGrade === 'IV') return 'text-orange-700'
                    return 'text-red-700'
                  }

                  const getAsaDescription = (asaGrade: string) => {
                    if (asaGrade === 'I') return 'Healthy'
                    if (asaGrade === 'II') return 'Mild disease'
                    if (asaGrade === 'III') return 'Severe disease'
                    if (asaGrade === 'IV') return 'Life-threatening'
                    return 'Moribund'
                  }

                  return (
                    <div key={grade} className={`text-center p-4 rounded-lg border-2 ${getAsaColor(grade)}`}>
                      <p className={`text-lg font-bold ${getAsaTextColor(grade)}`}>ASA {grade}</p>
                      <p className={`text-3xl font-bold mt-2 ${getAsaTextColor(grade)}`}>{count}</p>
                      <p className="text-xs text-gray-600 mt-1">{percentage}%</p>
                      <p className="text-xs text-gray-500 mt-1">{getAsaDescription(grade)}</p>
                    </div>
                  )
                })}
              </div>
              <p className="text-xs text-gray-500 mt-4 text-center">
                ASA Physical Status Classification: Risk stratification for surgical patients
              </p>
            </Card>
          )}

          {/* Data Visualizations */}
          <div className="space-y-6">
            {/* Outcome Trends Over Time */}
            <OutcomeTrendsChart
              data={chartData.outcomeTrends}
              loading={chartData.loading}
              height={400}
            />

            {/* Complication Rates by Category */}
            <ComplicationRateChart
              data={chartData.complicationByCategory}
              loading={chartData.loading}
              height={350}
              title="Complication Rates by Surgical Urgency"
              subtitle="Comparison of complication rates across urgency categories"
            />

            {/* Surgeon Performance Comparison */}
            {chartData.surgeonPerformance.length > 0 && (
              <div className="space-y-4">
                <Card className="p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">Surgeon Performance Comparison</h3>
                    <div className="flex gap-2">
                      <Button
                        size="small"
                        variant={selectedMetric === 'complicationRate' ? 'primary' : 'outline'}
                        onClick={() => setSelectedMetric('complicationRate')}
                      >
                        Complications
                      </Button>
                      <Button
                        size="small"
                        variant={selectedMetric === 'mortality30d' ? 'primary' : 'outline'}
                        onClick={() => setSelectedMetric('mortality30d')}
                      >
                        Mortality
                      </Button>
                      <Button
                        size="small"
                        variant={selectedMetric === 'readmissionRate' ? 'primary' : 'outline'}
                        onClick={() => setSelectedMetric('readmissionRate')}
                      >
                        Readmissions
                      </Button>
                      <Button
                        size="small"
                        variant={selectedMetric === 'rttRate' ? 'primary' : 'outline'}
                        onClick={() => setSelectedMetric('rttRate')}
                      >
                        RTT
                      </Button>
                    </div>
                  </div>
                </Card>
                <SurgeonPerformanceChart
                  data={chartData.surgeonPerformance}
                  loading={chartData.loading}
                  height={400}
                  metric={selectedMetric}
                />
              </div>
            )}
          </div>

          {/* Surgeon Performance */}
          {surgeonPerf.length > 0 && (
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Surgeon Performance</h3>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHeadCell>Surgeon</TableHeadCell>
                    <TableHeadCell>Surgeries</TableHeadCell>
                    <TableHeadCell>Complication Rate</TableHeadCell>
                    <TableHeadCell>Readmission Rate</TableHeadCell>
                    <TableHeadCell>RTT</TableHeadCell>
                    <TableHeadCell>30d Mortality</TableHeadCell>
                    <TableHeadCell>90d Mortality</TableHeadCell>
                    <TableHeadCell>Median Duration (min)</TableHeadCell>
                    <TableHeadCell>Median LOS (days)</TableHeadCell>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {surgeonPerf.map((surgeon) => (
                    <TableRow key={surgeon._id}>
                      <TableCell className="font-medium text-gray-900">
                        {surgeon._id}
                      </TableCell>
                      <TableCell className="text-gray-500">
                        {surgeon.total_surgeries}
                      </TableCell>
                      <TableCell>
                        <span className={`text-sm font-semibold px-2 py-1 rounded ${getOutcomeColor(surgeon.complication_rate, 'complication')}`}>
                          {surgeon.complication_rate.toFixed(1)}%
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className={`text-sm font-semibold px-2 py-1 rounded ${getOutcomeColor(surgeon.readmission_rate, 'readmission')}`}>
                          {surgeon.readmission_rate.toFixed(1)}%
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className={`text-sm font-semibold px-2 py-1 rounded ${getOutcomeColor(surgeon.return_to_theatre_rate, 'return_to_theatre')}`}>
                          {surgeon.return_to_theatre_rate.toFixed(1)}%
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className={`text-sm font-semibold px-2 py-1 rounded ${getOutcomeColor(surgeon.mortality_30d_rate, 'mortality')}`}>
                          {surgeon.mortality_30d_rate.toFixed(1)}%
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className={`text-sm font-semibold px-2 py-1 rounded ${getOutcomeColor(surgeon.mortality_90d_rate, 'mortality')}`}>
                          {surgeon.mortality_90d_rate.toFixed(1)}%
                        </span>
                      </TableCell>
                      <TableCell className="text-gray-500">
                        {surgeon.median_duration?.toFixed(0) || 'N/A'}
                      </TableCell>
                      <TableCell className="text-gray-500">
                        {surgeon.median_los 
                          ? (surgeon.median_los % 1 === 0 
                              ? surgeon.median_los.toFixed(0) 
                              : surgeon.median_los.toFixed(1))
                          : 'N/A'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}

          {/* Export Buttons */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">NBOCA Data Exports</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <Button
                onClick={() => downloadExcel('/api/exports/nboca', 'nboca_export.xlsx')}
                variant="outline"
              >
                Download NBOCA Dataset
              </Button>
              <Button
                onClick={() => downloadExcel('/api/exports/cosd', 'cosd_export.xlsx')}
                variant="outline"
              >
                Download COSD Dataset
              </Button>
              <Button
                onClick={() => downloadExcel('/api/exports/monthly-summary', 'monthly_summary.xlsx')}
                variant="outline"
              >
                Download Monthly Summary
              </Button>
            </div>
          </Card>
        </>
      )}

      {/* Data Quality Tab */}
      {!loading && activeTab === 'quality' && dataQuality && (
        <>
          {/* Overall Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="p-6">
              <h3 className="text-sm font-medium text-gray-500">Total Episodes</h3>
              <p className="mt-2 text-3xl font-bold text-gray-900">{dataQuality.total_episodes}</p>
            </Card>

            <Card className="p-6">
              <h3 className="text-sm font-medium text-gray-500">Total Tumours</h3>
              <p className="mt-2 text-3xl font-bold text-gray-900">{dataQuality.total_tumours}</p>
            </Card>

            <Card className={`p-6 border-2 ${getCompletenessCardColor(dataQuality.overall_completeness)}`}>
              <h3 className="text-sm font-medium text-gray-600">Overall Completeness</h3>
              <p className={`mt-2 text-3xl font-bold ${getCompletenessTextColor(dataQuality.overall_completeness)}`}>
                {dataQuality.overall_completeness.toFixed(1)}%
              </p>
            </Card>
          </div>

          {/* COSD Data Quality */}
          {cosdData && (
            <Card className="p-6">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h3 className="text-lg font-semibold">COSD Dataset Completeness</h3>
                  <p className="text-xs text-gray-500 mt-1">Cancer Outcomes and Services Dataset (NHS England mandatory fields)</p>
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium text-gray-700">Year:</label>
                  <select
                    value={cosdYear || ''}
                    onChange={(e) => setCosdYear(e.target.value ? parseInt(e.target.value) : null)}
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Years</option>
                    <option value="2025">2025</option>
                    <option value="2024">2024</option>
                    <option value="2023">2023</option>
                    <option value="2022">2022</option>
                    <option value="2021">2021</option>
                    <option value="2020">2020</option>
                  </select>
                </div>
              </div>

              {/* COSD Summary Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold text-gray-900">{cosdData.total_treatments}</p>
                  <p className="text-xs text-gray-500 mt-1">Treatments</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold text-gray-900">{cosdData.total_episodes}</p>
                  <p className="text-xs text-gray-500 mt-1">Episodes</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold text-gray-900">{cosdData.total_patients}</p>
                  <p className="text-xs text-gray-500 mt-1">Patients</p>
                </div>
                <div className={`text-center p-4 rounded-lg border-2 ${getCompletenessCardColor(cosdData.overall_completeness)}`}>
                  <p className={`text-2xl font-bold ${getCompletenessTextColor(cosdData.overall_completeness)}`}>
                    {cosdData.overall_completeness.toFixed(1)}%
                  </p>
                  <p className="text-xs text-gray-600 mt-1">Overall Completeness</p>
                </div>
              </div>

              {/* COSD Category Breakdown */}
              <div className="space-y-4 mb-6">
                <h4 className="text-md font-semibold text-gray-700">COSD Categories</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {cosdData.categories.map((category) => (
                    <div key={category.category} className={`p-3 rounded-lg border-2 ${getCompletenessCardColor(category.avg_completeness)}`}>
                      <div className="flex justify-between items-center mb-2">
                        <h5 className="text-sm font-semibold text-gray-700">{category.category}</h5>
                        <span className={`text-lg font-bold ${getCompletenessTextColor(category.avg_completeness)}`}>
                          {category.avg_completeness.toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${getCompletenessBarColor(category.avg_completeness)}`}
                          style={{ width: `${category.avg_completeness}%` }}
                        ></div>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{category.field_count} fields</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* COSD Field Details */}
              <div>
                <h4 className="text-md font-semibold text-gray-700 mb-3">COSD Field Details</h4>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHeadCell>Field</TableHeadCell>
                        <TableHeadCell>Category</TableHeadCell>
                        <TableHeadCell>Complete</TableHeadCell>
                        <TableHeadCell>Missing</TableHeadCell>
                        <TableHeadCell>Completeness</TableHeadCell>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {cosdData.categories.flatMap(cat =>
                        cat.fields.map(field => ({...field, category: cat.category}))
                      )
                      .sort((a, b) => a.completeness - b.completeness)
                      .map((field, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium text-gray-900">
                            {field.field}
                          </TableCell>
                          <TableCell className="text-gray-500 text-sm">
                            {field.category}
                          </TableCell>
                          <TableCell className="text-gray-500">
                            {field.complete_count.toLocaleString()}
                          </TableCell>
                          <TableCell className="text-red-600">
                            {field.missing_count.toLocaleString()}
                          </TableCell>
                          <TableCell>
                            <span className={`text-sm font-semibold px-2 py-1 rounded ${getCompletenessColor(field.completeness)}`}>
                              {field.completeness.toFixed(1)}%
                            </span>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </Card>
          )}

          {/* Category Breakdown */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-6">Data Completeness by Category</h3>
            <div className="space-y-4">
              {dataQuality.categories.map((category) => (
                <div key={category.name} className={`p-4 rounded-lg border-2 ${getCompletenessCardColor(category.avg_completeness)}`}>
                  <div className="flex justify-between items-center mb-3">
                    <h4 className="text-base font-semibold text-gray-700">{category.name}</h4>
                    <span className={`text-lg font-bold ${getCompletenessTextColor(category.avg_completeness)}`}>
                      {category.avg_completeness.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                    <div
                      className={`h-2.5 rounded-full ${getCompletenessBarColor(category.avg_completeness)}`}
                      style={{ width: `${category.avg_completeness}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-gray-500">{category.total_fields} fields</p>
                </div>
              ))}
            </div>
          </Card>

          {/* Episode Fields Detail */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Episode Data Fields</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHeadCell>Field</TableHeadCell>
                  <TableHeadCell>Category</TableHeadCell>
                  <TableHeadCell>Complete</TableHeadCell>
                  <TableHeadCell>Missing</TableHeadCell>
                  <TableHeadCell>Completeness</TableHeadCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dataQuality.episode_fields
                  ?.sort((a: any, b: any) => a.completeness - b.completeness)
                  .map((field: any) => (
                    <TableRow key={field.field}>
                      <TableCell className="font-medium text-gray-900">
                        {field.field}
                      </TableCell>
                      <TableCell className="text-gray-500">
                        {field.category}
                      </TableCell>
                      <TableCell className="text-gray-500">
                        {field.complete_count}
                      </TableCell>
                      <TableCell className="text-red-600">
                        {field.missing_count}
                      </TableCell>
                      <TableCell>
                        <span className={`text-sm font-semibold px-2 py-1 rounded ${getCompletenessColor(field.completeness)}`}>
                            {field.completeness.toFixed(1)}%
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
          </Card>

          {/* Treatment Fields Detail */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Treatment Data Fields</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHeadCell>Field</TableHeadCell>
                  <TableHeadCell>Category</TableHeadCell>
                  <TableHeadCell>Complete</TableHeadCell>
                  <TableHeadCell>Missing</TableHeadCell>
                  <TableHeadCell>Completeness</TableHeadCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dataQuality.treatment_fields
                  ?.sort((a: any, b: any) => a.completeness - b.completeness)
                  .map((field: any) => (
                    <TableRow key={field.field}>
                      <TableCell className="font-medium text-gray-900">
                        {field.field}
                      </TableCell>
                      <TableCell className="text-gray-500">
                        {field.category}
                      </TableCell>
                      <TableCell className="text-gray-500">
                        {field.complete_count}
                      </TableCell>
                      <TableCell className="text-red-600">
                        {field.missing_count}
                      </TableCell>
                      <TableCell>
                        <span className={`text-sm font-semibold px-2 py-1 rounded ${getCompletenessColor(field.completeness)}`}>
                          {field.completeness.toFixed(1)}%
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </Card>
        </>
      )}
    </div>
  )
}
