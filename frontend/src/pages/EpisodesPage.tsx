import { useState, useEffect, useMemo, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { EpisodeForm } from '../components/EpisodeForm'
import { CancerEpisodeForm } from '../components/CancerEpisodeForm'
import { EpisodeDetailModal } from '../components/EpisodeDetailModal'
import { CancerEpisodeDetailModal } from '../components/CancerEpisodeDetailModal'
import { ToastContainer } from '../components/Toast'
import { apiService } from '../services/api'
import api from '../services/api'
import { formatDate, formatStatus, formatCancerType, formatSurgeon } from '../utils/formatters'

const capitalize = (str: string) => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

interface Episode {
  surgery_id: string
  patient_id: string
  classification: {
    urgency: string
    primary_diagnosis: string
  }
  procedure: {
    primary_procedure: string
    approach: string
  }
  perioperative_timeline: {
    surgery_date: string
  }
  team: {
    primary_surgeon: string
  }
}

export function EpisodesPage() {
  const { patientId } = useParams<{ patientId: string }>()
  const navigate = useNavigate()
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [cancerEpisodes, setCancerEpisodes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [showCancerModal, setShowCancerModal] = useState(false)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [selectedEpisode, setSelectedEpisode] = useState<Episode | null>(null)
  const [showCancerDetailModal, setShowCancerDetailModal] = useState(false)
  const [selectedCancerEpisode, setSelectedCancerEpisode] = useState<any>(null)
  const [editingCancerEpisode, setEditingCancerEpisode] = useState<any>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [toasts, setToasts] = useState<Array<{ id: string; message: string; type: 'success' | 'error' | 'info' | 'warning' }>>([])
  const [patientInfo, setPatientInfo] = useState<any>(null)
  
  // Filters
  const [startDateFilter, setStartDateFilter] = useState('')
  const [endDateFilter, setEndDateFilter] = useState('')

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
      if (startDateFilter) params.start_date = startDateFilter
      if (endDateFilter) params.end_date = endDateFilter

      // Load legacy surgery episodes
      const response = await apiService.episodes.list(params)
      setEpisodes(response.data)

      // Load new cancer episodes from V2 API
      const cancerParams = new URLSearchParams()
      if (patientId) cancerParams.append('patient_id', patientId)
      if (startDateFilter) cancerParams.append('start_date', startDateFilter)
      if (endDateFilter) cancerParams.append('end_date', endDateFilter)

      const cancerResponse = await fetch(
        `http://localhost:8000/api/v2/episodes/?${cancerParams.toString()}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      )
      
      if (cancerResponse.ok) {
        const cancerData = await cancerResponse.json()
        setCancerEpisodes(cancerData)
      }
    } catch (error) {
      console.error('Failed to load episodes:', error)
    } finally {
      setLoading(false)
    }
  }, [patientId, startDateFilter, endDateFilter])

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

  const handleCreate = async (data: any) => {
    try {
      await apiService.episodes.create(data)
      setShowModal(false)
      setSelectedEpisode(null)
      loadEpisodes()
      showToast('Episode created successfully', 'success')
    } catch (error: any) {
      console.error('Failed to create episode:', error)
      showToast(error.response?.data?.detail || 'Failed to create episode', 'error')
    }
  }

  const handleCreateCancerEpisode = async (data: any) => {
    try {
      console.log('Creating cancer episode with data:', data)
      
      const response = await fetch('http://localhost:8000/api/v2/episodes/', {
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

      setShowCancerModal(false)
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
    if (!selectedEpisode) return
    
    try {
      await apiService.episodes.update(selectedEpisode.surgery_id, data)
      setShowModal(false)
      setSelectedEpisode(null)
      loadEpisodes()
      showToast('Episode updated successfully', 'success')
    } catch (error: any) {
      console.error('Failed to update episode:', error)
      showToast(error.response?.data?.detail || 'Failed to update episode', 'error')
    }
  }

  const handleEditCancerEpisode = async (data: any) => {
    if (!editingCancerEpisode) return
    
    try {
      const response = await fetch(`http://localhost:8000/api/v2/episodes/${editingCancerEpisode.episode_id}`, {
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

      setEditingCancerEpisode(null)
      setShowCancerModal(false)
      loadEpisodes()
      showToast('Cancer episode updated successfully', 'success')
    } catch (error: any) {
      console.error('Failed to update cancer episode:', error)
      showToast(error.message || 'Failed to update cancer episode', 'error')
    }
  }

  const handleDelete = async (surgeryId: string) => {
    if (!confirm('Are you sure you want to delete this episode?')) return
    
    try {
      await apiService.episodes.delete(surgeryId)
      loadEpisodes()
      showToast('Episode deleted successfully', 'success')
    } catch (error) {
      console.error('Failed to delete episode:', error)
      showToast('Failed to delete episode', 'error')
    }
  }

  const filteredEpisodes = useMemo(() => {
    return episodes.filter(episode => {
      // Search term filter
      if (searchTerm) {
        const search = searchTerm.toLowerCase()
        const matchesSearch = (
          episode.surgery_id.toLowerCase().includes(search) ||
          episode.patient_id.toLowerCase().includes(search) ||
          episode.procedure.primary_procedure.toLowerCase().includes(search) ||
          episode.team.primary_surgeon.toLowerCase().includes(search)
        )
        if (!matchesSearch) return false
      }

      return true
    })
  }, [episodes, searchTerm])

  const filteredCancerEpisodes = useMemo(() => {
    return cancerEpisodes.filter(episode => {
      // Search term filter
      if (searchTerm) {
        const search = searchTerm.toLowerCase()
        const matchesSearch = (
          episode.episode_id.toLowerCase().includes(search) ||
          episode.patient_id.toLowerCase().includes(search) ||
          (episode.cancer_type && episode.cancer_type.toLowerCase().includes(search)) ||
          (episode.lead_clinician && episode.lead_clinician.toLowerCase().includes(search))
        )
        if (!matchesSearch) return false
      }

      return true
    })
  }, [cancerEpisodes, searchTerm])

  const getUrgencyColor = (urgency: string) => {
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
            ? `${patientInfo.demographics?.gender || ''} | DOB: ${patientInfo.demographics?.date_of_birth || ''} | NHS: ${patientInfo.nhs_number || ''}`
            : 'Track surgical episodes and outcomes'}
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
                onClick={() => setShowCancerModal(true)}
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
                  <p className="font-medium text-gray-900">{patientInfo.nhs_number}</p>
                </div>
                <div>
                  <span className="text-gray-500">Date of Birth:</span>
                  <p className="font-medium text-gray-900">{patientInfo.demographics?.date_of_birth}</p>
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
          <div className="grid grid-cols-1 md:grid-cols-7 gap-4">
            <div className="md:col-span-4">
              <input
                type="text"
                placeholder="Search by Episode ID, Patient ID, Cancer Type, or Clinician..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full h-10 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div className="md:col-span-1.5 relative">
              {!startDateFilter && (
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none text-sm">
                  Start Date
                </span>
              )}
              <input
                type="date"
                value={startDateFilter}
                onChange={(e) => setStartDateFilter(e.target.value)}
                className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 [&::-webkit-calendar-picker-indicator]:opacity-100"
                style={!startDateFilter ? { color: 'transparent' } : {}}
              />
            </div>

            <div className="md:col-span-1.5 relative">
              {!endDateFilter && (
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none text-sm">
                  End Date
                </span>
              )}
              <input
                type="date"
                value={endDateFilter}
                onChange={(e) => setEndDateFilter(e.target.value)}
                className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 [&::-webkit-calendar-picker-indicator]:opacity-100"
                style={!endDateFilter ? { color: 'transparent' } : {}}
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
        ) : filteredEpisodes.length === 0 && filteredCancerEpisodes.length === 0 ? (
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
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Patient ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Clinician
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {/* Cancer Episodes */}
                {filteredCancerEpisodes.map((episode) => (
                  <tr 
                    key={episode.episode_id} 
                    onClick={() => {
                      setSelectedCancerEpisode(episode)
                      setShowCancerDetailModal(true)
                    }}
                    className="hover:bg-gray-50 bg-green-50 cursor-pointer"
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-green-600">
                      {episode.episode_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                        {formatCancerType(episode.cancer_type)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {episode.patient_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(episode.referral_date)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatSurgeon(episode.lead_clinician)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                        episode.episode_status === 'active' ? 'bg-blue-100 text-blue-800' :
                        episode.episode_status === 'completed' ? 'bg-gray-100 text-gray-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {formatStatus(episode.episode_status)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex space-x-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setEditingCancerEpisode(episode)
                            setShowCancerModal(true)
                          }}
                          className="text-blue-600 hover:text-blue-900"
                          title="Edit episode"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>                      </div>
                    </td>
                  </tr>
                ))}
                
                {/* Legacy Surgery Episodes */}
                {filteredEpisodes.map((episode) => (
                  <tr key={episode.surgery_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                      {episode.surgery_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                        Surgery
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {episode.patient_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(episode.perioperative_timeline.surgery_date)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {episode.team.primary_surgeon}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getUrgencyColor(episode.classification.urgency)}`}>
                        {capitalize(episode.classification.urgency)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => {
                            setSelectedEpisode(episode)
                            setShowDetailModal(true)
                          }}
                          className="text-indigo-600 hover:text-indigo-900"
                        >
                          View
                        </button>
                        <button
                          onClick={() => {
                            setSelectedEpisode(episode)
                            setShowModal(true)
                          }}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(episode.surgery_id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Delete
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

      {/* Modal for Create/Edit */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">
                {selectedEpisode ? 'Edit Episode' : 'Create New Episode'}
              </h2>
              <button
                onClick={() => {
                  setShowModal(false)
                  setSelectedEpisode(null)
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6">
              <EpisodeForm
                mode={selectedEpisode ? 'edit' : 'create'}
                initialData={selectedEpisode || (patientId ? { patient_id: patientId } : undefined)}
                onSubmit={selectedEpisode ? handleEdit : handleCreate}
                onCancel={() => {
                  setShowModal(false)
                  setSelectedEpisode(null)
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {showDetailModal && selectedEpisode && (
        <EpisodeDetailModal
          episode={selectedEpisode}
          onClose={() => {
            setShowDetailModal(false)
            setSelectedEpisode(null)
          }}
          onEdit={() => {
            setShowDetailModal(false)
            setShowModal(true)
          }}
        />
      )}

      {/* Cancer Episode Detail Modal */}
      {showCancerDetailModal && selectedCancerEpisode && (
        <CancerEpisodeDetailModal
          episode={selectedCancerEpisode}
          onClose={() => {
            setShowCancerDetailModal(false)
            setSelectedCancerEpisode(null)
          }}
          onEdit={(episode) => {
            setEditingCancerEpisode(episode)
            setShowCancerModal(true)
          }}
        />
      )}

      {/* Cancer Episode Modal */}
      {showCancerModal && (
        <CancerEpisodeForm
          onSubmit={editingCancerEpisode ? handleEditCancerEpisode : handleCreateCancerEpisode}
          onCancel={() => {
            setShowCancerModal(false)
            setEditingCancerEpisode(null)
          }}
          mode={editingCancerEpisode ? 'edit' : 'create'}
          initialData={editingCancerEpisode || (patientId ? { patient_id: patientId } : undefined)}
        />
      )}
      </div>
    </>
  )
}
