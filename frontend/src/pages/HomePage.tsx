import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../contexts/AuthContext'
import { PageHeader } from '../components/common/PageHeader'
import { Card } from '../components/common/Card'
import { formatDate } from '../utils/formatters'
import api from '../services/api'

export function HomePage() {
  const { user: _user } = useAuth()
  const navigate = useNavigate()

  // Use React Query for dashboard stats - automatic caching and deduplication
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const response = await api.get('/episodes/dashboard-stats')
      return response.data
    },
    staleTime: 5 * 60 * 1000, // Fresh for 5 minutes
  })

  // Use React Query for recent activity
  const { data: recentActivity = [], isLoading: activityLoading } = useQuery({
    queryKey: ['recent-activity'],
    queryFn: async () => {
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(`${API_URL}/audit/recent?limit=10`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      if (!response.ok) {
        throw new Error('Failed to fetch recent activity')
      }
      return response.json()
    },
    staleTime: 2 * 60 * 1000, // Fresh for 2 minutes (activity changes more frequently)
  })

  // Helper to check if treatment is a surgery type
  const isSurgeryType = (treatmentType: string) => {
    return ['surgery', 'surgery_primary', 'surgery_rtt', 'surgery_reversal'].includes(treatmentType)
  }

  const handleActivityClick = (activity: any) => {
    // Navigate based on entity type and pass state to open appropriate modal
    if (activity.entity_type === 'episode') {
      // Navigate to episodes page and open episode detail modal
      navigate('/episodes', {
        state: {
          openEpisode: activity.entity_id,
          action: activity.action
        }
      })
    } else if (activity.entity_type === 'patient') {
      // Navigate to patients page and open patient detail
      navigate('/patients', {
        state: {
          openPatient: activity.entity_id,
          action: activity.action
        }
      })
    } else if (activity.entity_type === 'treatment') {
      // Navigate to episodes and open treatment modal
      navigate('/episodes', {
        state: {
          openTreatment: activity.entity_id,
          action: activity.action
        }
      })
    } else if (activity.entity_type === 'tumour') {
      // Navigate to episodes and open tumour modal
      navigate('/episodes', {
        state: {
          openTumour: activity.entity_id,
          action: activity.action
        }
      })
    } else if (activity.entity_type === 'investigation') {
      // Navigate to episodes and open investigation modal
      navigate('/episodes', {
        state: {
          openInvestigation: activity.entity_id,
          action: activity.action
        }
      })
    }
  }

  const formatRelativeTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)
    
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return formatDate(dateStr)
  }

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Dashboard" 
        subtitle="Integrated Monitoring Platform for Audit Care & Treatment"
        icon={
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 sm:gap-6">
        <Card hover>
          <div className="relative pt-2">
            <div className="absolute top-0 left-0 bg-blue-100 rounded-md p-3">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <div className="text-center">
              <h3 className="text-sm font-medium text-gray-500 mb-1">Total Patients</h3>
              <p className="text-2xl font-semibold text-gray-900">
                {isLoading ? '—' : stats?.totalPatients ?? 0}
              </p>
            </div>
          </div>
        </Card>

        <Card hover>
          <div className="relative pt-2">
            <div className="absolute top-0 left-0 bg-green-100 rounded-md p-3">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
            </div>
            <div className="text-center">
              <h3 className="text-sm font-medium text-gray-500 mb-1">Total Episodes</h3>
              <p className="text-2xl font-semibold text-gray-900">
                {isLoading ? '—' : stats?.totalEpisodes ?? 0}
              </p>
            </div>
            {!isLoading && stats && (
              <div className="mt-3 pt-3 border-t border-gray-200 w-full">
                <div className="grid grid-cols-2 gap-4">
                  {/* Surgery Treatments */}
                  <div>
                    <div className="text-xs font-medium text-gray-700 mb-1 text-center">Surgery</div>
                    <div className="text-center">
                      {stats.treatmentBreakdown
                        .filter(item => isSurgeryType(item.treatment_type))
                        .map((item, idx) => (
                          <div key={idx} className="text-lg font-semibold text-gray-900">{item.count}</div>
                        ))}
                      {stats.treatmentBreakdown.filter(item => isSurgeryType(item.treatment_type)).length === 0 && (
                        <div className="text-sm text-gray-400">None</div>
                      )}
                    </div>
                  </div>
                  
                  {/* Oncology Treatments */}
                  <div>
                    <div className="text-xs font-medium text-gray-700 mb-1 text-center">Oncology</div>
                    <div className="grid grid-cols-2 gap-2">
                        {stats.treatmentBreakdown
                          .filter(item => ['chemotherapy', 'radiotherapy', 'immunotherapy'].includes(item.treatment_type))
                          .map((item, idx) => (
                            <div key={idx} className="text-center">
                              <div className="text-xs text-gray-500 capitalize">{item.treatment_type}</div>
                              <div className="text-lg font-semibold text-gray-900">{item.count}</div>
                            </div>
                          ))}
                        {stats.treatmentBreakdown.filter(item => ['chemotherapy', 'radiotherapy', 'immunotherapy'].includes(item.treatment_type)).length === 0 && (
                          <div className="text-center col-span-2 text-sm text-gray-400">No oncology treatments yet</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
          </div>
        </Card>

        <Card hover>
          <div className="relative pt-2">
            <div className="absolute top-0 left-0 bg-purple-100 rounded-md p-3">
              <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <div className="text-center">
              <h3 className="text-sm font-medium text-gray-500 mb-1">Monthly Operations</h3>
              {isLoading ? (
                <p className="text-2xl font-semibold text-gray-900">—</p>
              ) : stats ? (
                <>
                  <div>
                    <div className="text-xs text-gray-500">Year Total</div>
                    <div className="text-2xl font-semibold text-gray-900">
                      {stats.yearToDateEpisodes}
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="grid grid-cols-4 gap-2 w-full">
                      {stats.monthlyEpisodes.map((data, idx) => (
                        <div key={idx} className="text-center">
                          <div className="text-xs text-gray-500">{data.month}</div>
                          <div className="text-lg font-semibold text-gray-900">{data.count}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : null}
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
        <Card>
          <div className="border-b border-gray-200 pb-4 mb-4">
            <h3 className="text-lg font-medium text-gray-900">Quick Actions</h3>
          </div>
          <div className="space-y-3">
            <button
              onClick={() => navigate('/patients', { state: { addNew: true } })}
              className="w-full flex items-center p-3 rounded-lg hover:bg-blue-50 transition-colors"
            >
              <svg className="w-5 h-5 text-gray-400 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span className="text-sm font-medium text-gray-900">Add New Patient</span>
            </button>
            <button
              onClick={() => navigate('/episodes', { state: { addNew: true } })}
              className="w-full flex items-center p-3 rounded-lg hover:bg-blue-50 transition-colors"
            >
              <svg className="w-5 h-5 text-gray-400 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span className="text-sm font-medium text-gray-900">Record Episode</span>
            </button>
            <button
              onClick={() => navigate('/reports')}
              className="w-full flex items-center p-3 rounded-lg hover:bg-blue-50 transition-colors"
            >
              <svg className="w-5 h-5 text-gray-400 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-sm font-medium text-gray-900">View Reports</span>
            </button>
          </div>
        </Card>

        <Card>
          <div className="border-b border-gray-200 pb-4 mb-4">
            <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
          </div>
          {activityLoading ? (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : recentActivity.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <svg className="mx-auto w-12 h-12 text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm">No recent activity</p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentActivity.map((activity, index) => (
                <button
                  key={activity.log_id || index}
                  onClick={() => handleActivityClick(activity)}
                  className="w-full text-left p-3 rounded-lg hover:bg-blue-50 transition-colors border border-gray-200"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                          activity.action === 'create' ? 'bg-green-100 text-green-800' :
                          activity.action === 'update' ? 'bg-blue-100 text-blue-800' :
                          activity.action === 'delete' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {activity.action.toUpperCase()}
                        </span>
                        <span className="text-xs text-gray-500">
                          {activity.entity_type.replace('_', ' ')}
                        </span>
                      </div>
                      <p className="text-sm text-gray-900 mt-1 font-medium">
                        {activity.message}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {activity.entity_id}
                      </p>
                    </div>
                    <div className="ml-4 flex-shrink-0 text-right">
                      <p className="text-xs text-gray-500">
                        {formatRelativeTime(activity.timestamp)}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
