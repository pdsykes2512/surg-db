import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { DateInput } from '../components/DateInput'
import { CancerEpisodeForm } from '../components/CancerEpisodeForm'
import { CancerEpisodeDetailModal } from '../components/CancerEpisodeDetailModal'
import { ToastContainer } from '../components/Toast'
import { apiService } from '../services/api'
import api from '../services/api'
import { formatDate, formatCancerType, formatSurgeon } from '../utils/formatters'

// @ts-ignore - Unused but kept for potential future use
const _capitalize = (str: string) => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

const formatNHSNumber = (nhsNumber: string | undefined) => {
  if (!nhsNumber) return '-';
  const digits = nhsNumber.replace(/\D/g, '');
  if (digits.length === 10) {
    return `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6)}`;
  }
  return nhsNumber;
};

export function EpisodesPage() {
  const { patientId } = useParams<{ patientId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const [episodes, setEpisodes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [selectedEpisode, setSelectedEpisode] = useState<any>(null)
  const [editingEpisode, setEditingEpisode] = useState<any>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [toasts, setToasts] = useState<Array<{ id: string; message: string; type: 'success' | 'error' | 'info' | 'warning' }>>([])
  const [patientInfo, setPatientInfo] = useState<any>(null)
  
  // Filters
  const [startDateFilter, setStartDateFilter] = useState('')
  const [endDateFilter, setEndDateFilter] = useState('')

  // Delete confirmation state
  const [deleteConfirmation, setDeleteConfirmation] = useState<{ show: boolean; episode: any | null }>({ 
    show: false, 
    episode: null 
  })
  const [deleteConfirmText, setDeleteConfirmText] = useState('')

  const showToast = useCallback((message: string, type: 'success' | 'error' | 'info' | 'warning' = 'info') => {
    const id = Date.now().toString()
    setToasts(prev => [...prev, { id, message, type }])
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id))
  }, [])

  const loadEpisodes = useCallback(async () => {
    try {
      setLoading(true)
      const params: any = {}
      if (patientId) {
        params.patient_id = patientId
      }
      if (searchTerm) {
        params.search = searchTerm
      }
      if (startDateFilter) params.start_date = startDateFilter
      if (endDateFilter) params.end_date = endDateFilter

      // Load cancer episodes from API
      const response = await apiService.episodes.list(params)
      const allEpisodes = response.data
      
      // Filter for cancer episodes only
      const cancer = allEpisodes.filter((ep: any) => ep.episode_id && ep.condition_type === 'cancer')
      
      setEpisodes(cancer)
    } catch (error) {
      console.error('Failed to load episodes:', error)
    } finally {
      setLoading(false)
    }
  }, [patientId, searchTerm, startDateFilter, endDateFilter])

  const loadPatientInfo = useCallback(async () => {
    if (!patientId) return
    try {
      const response = await api.get(`/patients/${patientId}`)
      setPatientInfo(response.data)
    } catch (error) {
      console.error('Failed to load patient info:', error)
      showToast('Failed to load patient information', 'error')
    }
  }, [patientId, showToast])

  useEffect(() => {
    loadEpisodes()
    if (patientId) {
      loadPatientInfo()
    }
  }, [loadEpisodes, patientId, loadPatientInfo])

  // Debounce search to avoid too many API calls
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      loadEpisodes()
    }, 300) // Wait 300ms after user stops typing
    
    return () => clearTimeout(timeoutId)
  }, [searchTerm, loadEpisodes])

  // Handle opening edit modal from navigation state
  useEffect(() => {
    const state = location.state as { editEpisodeId?: string }
    if (state?.editEpisodeId && episodes.length > 0) {
      const episode = episodes.find(ep => ep.episode_id === state.editEpisodeId)
      if (episode) {
        setEditingEpisode(episode)
        setShowModal(true)
        // Clear the state to avoid reopening on refresh
        navigate(location.pathname, { replace: true, state: {} })
      }
    }
  }, [location.state, episodes, navigate, location.pathname])

  const handleCreate = async (data: any) => {
    try {
      console.log('Creating cancer episode with data:', data)
      
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
      const response = await fetch(`${API_URL}/episodes/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(data)
      })

      if (!response.ok) {
        const error = await response.json()
        console.error('Server error:', error)
        
        // Handle different error formats
        let errorMessage = 'Failed to create cancer episode'
        
        if (typeof error.detail === 'string') {
          errorMessage = error.detail
        } else if (Array.isArray(error.detail)) {
          // Pydantic validation errors
          errorMessage = error.detail.map((err: any) => 
            `${err.loc?.join('.') || 'Field'}: ${err.msg}`
          ).join('\n')
        } else if (error.detail && typeof error.detail === 'object') {
          errorMessage = JSON.stringify(error.detail, null, 2)
        }
        
        throw new Error(errorMessage)
      }

      setShowModal(false)
      setSelectedEpisode(null)
      loadEpisodes()
      showToast('Cancer episode created successfully', 'success')
    } catch (error: any) {
      console.error('Failed to create cancer episode:', error)
      const errorMessage = error.message || 'Failed to create cancer episode'
      
      // For multi-line errors, show an alert instead of toast
      if (errorMessage.includes('\n')) {
        alert(`Failed to create cancer episode:\n\n${errorMessage}`)
      } else {
        showToast(errorMessage, 'error')
      }
    }
  }

  const handleEdit = async (data: any) => {
    if (!editingEpisode) return
    
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
      const response = await fetch(`${API_URL}/episodes/${editingEpisode.episode_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(data)
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to update cancer episode')
      }

      setEditingEpisode(null)
      setShowModal(false)
      setSelectedEpisode(null)
      loadEpisodes()
      showToast('Cancer episode updated successfully', 'success')
    } catch (error: any) {
      console.error('Failed to update cancer episode:', error)
      showToast(error.message || 'Failed to update cancer episode', 'error')
    }
  }

  const handleDeleteClick = (episode: any) => {
    setDeleteConfirmation({ show: true, episode })
    setDeleteConfirmText('')
  }

  const handleDeleteConfirm = async () => {
    if (!deleteConfirmation.episode) return
    
    try {
      await api.delete(`/episodes/${deleteConfirmation.episode.episode_id}`)
      setDeleteConfirmation({ show: false, episode: null })
      setDeleteConfirmText('')
      loadEpisodes()
      showToast('Episode deleted successfully', 'success')
    } catch (error) {
      console.error('Failed to delete episode:', error)
      showToast('Failed to delete episode', 'error')
    }
  }

  // No need for local filtering - backend handles search
  const filteredEpisodes = episodes

  // @ts-ignore - Unused but kept for potential future use
  const _getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'emergency': return 'bg-red-100 text-red-800'
      case 'urgent': return 'bg-orange-100 text-orange-800'
      case 'elective': return 'bg-green-100 text-green-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <>
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      <div className="space-y-6">
        <PageHeader
          title={patientId ? `Episodes for Patient ${patientId}` : 'Episode Records'}
          subtitle={patientInfo 
            ? `${patientInfo.demographics?.gender || ''} | DOB: ${formatDate(patientInfo.demographics?.date_of_birth)} | NHS: ${formatNHSNumber(patientInfo.nhs_number)}`
            : 'Track cancer episodes and patient outcomes'}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
          }
          action={
            <div className="flex space-x-3">
              {patientId && (
                <Button 
                  variant="secondary"
                  onClick={() => navigate('/episodes')}
                >
                  ← All Episodes
                </Button>
              )}
              <Button 
                variant="primary"
                onClick={() => setShowModal(true)}
              >
                + Cancer Episode
              </Button>
            </div>
          }
        />

      {/* Patient Info Card */}
      {patientId && patientInfo && (
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Patient Information</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Record Number:</span>
                  <p className="font-medium text-gray-900">{patientInfo.record_number}</p>
                </div>
                <div>
                  <span className="text-gray-500">NHS Number:</span>
                  <p className="font-medium text-gray-900">{formatNHSNumber(patientInfo.nhs_number)}</p>
                </div>
                <div>
                  <span className="text-gray-500">Date of Birth:</span>
                  <p className="font-medium text-gray-900">{formatDate(patientInfo.demographics?.date_of_birth)}</p>
                </div>
                <div>
                  <span className="text-gray-500">Gender:</span>
                  <p className="font-medium text-gray-900 capitalize">{patientInfo.demographics?.gender}</p>
                </div>
              </div>
            </div>
            <Button
              variant="secondary"
              onClick={() => navigate('/patients')}
            >
              Back to Patients
            </Button>
          </div>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <div className="space-y-4">
          <div className="flex items-center space-x-4">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
            <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
          </div>

          {/* Search and Date Filters */}
          <div className="grid grid-cols-1 md:grid-cols-7 gap-4 items-center">
            <div className="md:col-span-4">
              <input
                type="text"
                placeholder="Search by Episode ID, Patient ID, Cancer Type, or Clinician..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full h-10 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div className="md:col-span-1.5 flex items-center gap-2">
              <span className="text-sm text-gray-600 whitespace-nowrap">From:</span>
              <DateInput
                value={startDateFilter}
                onChange={(e) => setStartDateFilter(e.target.value)}
              />
            </div>

            <div className="md:col-span-1.5 flex items-center gap-2">
              <span className="text-sm text-gray-600 whitespace-nowrap">To:</span>
              <DateInput
                value={endDateFilter}
                onChange={(e) => setEndDateFilter(e.target.value)}
              />
            </div>
          </div>

          {(startDateFilter || endDateFilter) && (
            <div className="flex justify-end">
              <Button
                variant="secondary"
                onClick={() => {
                  setStartDateFilter('')
                  setEndDateFilter('')
                }}
              >
                Clear Filters
              </Button>
            </div>
          )}
        </div>
      </Card>

      {/* Episodes List */}
      <Card>
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : filteredEpisodes.length === 0 ? (
          <div className="text-center py-12">
            <svg className="mx-auto w-16 h-16 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Episode Records</h3>
            <p className="text-gray-500">
              {searchTerm || startDateFilter || endDateFilter
                ? 'No episodes match your search criteria'
                : 'No episodes recorded yet'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Episode ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    MRN
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Clinician
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredEpisodes.map((episode) => (
                  <tr 
                    key={episode.episode_id} 
                    onClick={() => {
                      setSelectedEpisode(episode)
                      setShowDetailModal(true)
                    }}
                    className="hover:bg-blue-50 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {episode.episode_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {episode.patient_mrn || episode.patient_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(episode.referral_date)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatSurgeon(episode.lead_clinician)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                        {formatCancerType(episode.cancer_type)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex space-x-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setEditingEpisode(episode)
                            setShowModal(true)
                          }}
                          className="text-blue-600 hover:text-blue-900"
                          title="Edit episode"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeleteClick(episode)
                          }}
                          className="text-red-600 hover:text-red-900"
                          title="Delete episode"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Cancer Episode Detail Modal */}
      {showDetailModal && selectedEpisode && (
        <CancerEpisodeDetailModal
          episode={selectedEpisode}
          onClose={() => {
            setShowDetailModal(false)
            setSelectedEpisode(null)
          }}
          onEdit={(episode) => {
            setEditingEpisode(episode)
            setShowModal(true)
          }}
        />
      )}

      {/* Cancer Episode Modal */}
      {showModal && (
        <CancerEpisodeForm
          onSubmit={editingEpisode ? handleEdit : handleCreate}
          onCancel={() => {
            setShowModal(false)
            setEditingEpisode(null)
          }}
          mode={editingEpisode ? 'edit' : 'create'}
          initialData={editingEpisode || (patientId ? { patient_id: patientId } : undefined)}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmation.show && deleteConfirmation.episode && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center mb-4">
              <div className="flex-shrink-0">
                <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="ml-3 text-lg font-medium text-gray-900">Delete Episode</h3>
            </div>
            
            <div className="mb-4">
              <p className="text-sm text-gray-500 mb-4">
                You are about to delete the following episode and all associated treatments and tumours:
              </p>
              
              <div className="bg-gray-50 rounded-md p-4 mb-4">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="text-gray-500">Episode ID:</div>
                  <div className="font-medium text-gray-900">{deleteConfirmation.episode.episode_id}</div>
                  
                  <div className="text-gray-500">Patient ID:</div>
                  <div className="text-gray-900">{deleteConfirmation.episode.patient_id}</div>
                  
                  <div className="text-gray-500">Type:</div>
                  <div className="text-gray-900">{formatCancerType(deleteConfirmation.episode.cancer_type)}</div>
                  
                  <div className="text-gray-500">Date:</div>
                  <div className="text-gray-900">{formatDate(deleteConfirmation.episode.referral_date)}</div>
                </div>
              </div>

              <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
                <p className="text-sm text-red-800 font-medium">
                  ⚠️ This action cannot be undone
                </p>
                <p className="text-sm text-red-600 mt-1">
                  All associated treatments and tumour data will also be permanently deleted.
                </p>
              </div>

              <label className="block text-sm font-medium text-gray-700 mb-2">
                Type the episode ID <span className="font-mono font-bold">{deleteConfirmation.episode.episode_id}</span> to confirm:
              </label>
              <input
                type="text"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                placeholder="Enter episode ID"
                autoFocus
              />
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setDeleteConfirmation({ show: false, episode: null })
                  setDeleteConfirmText('')
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={deleteConfirmText !== deleteConfirmation.episode.episode_id}
                className={`px-4 py-2 text-sm font-medium text-white rounded-md ${
                  deleteConfirmText === deleteConfirmation.episode.episode_id
                    ? 'bg-red-600 hover:bg-red-700'
                    : 'bg-red-300 cursor-not-allowed'
                }`}
              >
                Delete Episode
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </>
  )
}
