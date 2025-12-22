import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { EpisodeForm } from '../components/EpisodeForm'
import { EpisodeDetailModal } from '../components/EpisodeDetailModal'
import { ToastContainer } from '../components/Toast'
import { apiService } from '../services/api'
import api from '../services/api'

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
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [selectedEpisode, setSelectedEpisode] = useState<Episode | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [toasts, setToasts] = useState<Array<{ id: string; message: string; type: 'success' | 'error' | 'info' | 'warning' }>>([])
  const [patientInfo, setPatientInfo] = useState<any>(null)
  
  // Filters
  const [urgencyFilter, setUrgencyFilter] = useState('')
  const [surgeonFilter, setSurgeonFilter] = useState('')
  const [startDateFilter, setStartDateFilter] = useState('')
  const [endDateFilter, setEndDateFilter] = useState('')
  const [surgeons, setSurgeons] = useState<any[]>([])
  const [surgeonSearch, setSurgeonSearch] = useState('')
  const [showSurgeonDropdown, setShowSurgeonDropdown] = useState(false)

  const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'info') => {
    const id = Date.now().toString()
    setToasts(prev => [...prev, { id, message, type }])
  }

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id))
  }

  // Fetch surgeons list
  useEffect(() => {
    const fetchSurgeons = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/admin/surgeons', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        if (response.ok) {
          const data = await response.json()
          setSurgeons(data)
        }
      } catch (error) {
        console.error('Error fetching surgeons:', error)
      }
    }
    fetchSurgeons()
  }, [])

  useEffect(() => {
    loadEpisodes()
    if (patientId) {
      loadPatientInfo()
    }
  }, [urgencyFilter, surgeonFilter, startDateFilter, endDateFilter, patientId])

  const loadPatientInfo = async () => {
    if (!patientId) return
    try {
      const response = await api.get(`/patients/${patientId}`)
      setPatientInfo(response.data)
    } catch (error) {
      console.error('Failed to load patient info:', error)
      showToast('Failed to load patient information', 'error')
    }
  }

  const loadEpisodes = async () => {
    try {
      setLoading(true)
      const params: any = {}
      if (patientId) {
        params.patient_id = patientId
      }
      if (urgencyFilter) params.urgency = urgencyFilter
      if (surgeonFilter) params.primary_surgeon = surgeonFilter
      if (startDateFilter) params.start_date = startDateFilter
      if (endDateFilter) params.end_date = endDateFilter

      const response = await apiService.episodes.list(params)
      setEpisodes(response.data)
    } catch (error) {
      console.error('Failed to load episodes:', error)
    } finally {
      setLoading(false)
    }
  }

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

  const filteredEpisodes = episodes.filter(episode => {
    if (!searchTerm) return true
    const search = searchTerm.toLowerCase()
    return (
      episode.surgery_id.toLowerCase().includes(search) ||
      episode.patient_id.toLowerCase().includes(search) ||
      episode.procedure.primary_procedure.toLowerCase().includes(search) ||
      episode.team.primary_surgeon.toLowerCase().includes(search)
    )
  })

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      })
    } catch {
      return dateStr
    }
  }

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
                onClick={() => {
                  setSelectedEpisode(null)
                  setShowModal(true)
                }}
              >
                + Record Surgery
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

          {/* Search */}
          <div>
            <input
              type="text"
              placeholder="Search by Surgery ID, Patient ID, Procedure, or Surgeon..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full h-10 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Filter dropdowns */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Urgency</label>
              <select
                value={urgencyFilter}
                onChange={(e) => setUrgencyFilter(e.target.value)}
                className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 appearance-none bg-white"
              >
                <option value="">All Urgencies</option>
                <option value="elective">Elective</option>
                <option value="urgent">Urgent</option>
                <option value="emergency">Emergency</option>
              </select>
            </div>

            <div className="relative">
              <label className="block text-sm font-medium text-gray-700 mb-1">Surgeon</label>
              <input
                type="text"
                placeholder="Type to search surgeons..."
                value={surgeonSearch || surgeonFilter}
                onChange={(e) => {
                  setSurgeonSearch(e.target.value)
                  setShowSurgeonDropdown(true)
                }}
                onFocus={() => setShowSurgeonDropdown(true)}
                onBlur={() => setTimeout(() => setShowSurgeonDropdown(false), 200)}
                className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              {showSurgeonDropdown && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                  <div
                    onClick={() => {
                      setSurgeonFilter('')
                      setSurgeonSearch('')
                      setShowSurgeonDropdown(false)
                    }}
                    className="px-3 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 text-gray-500 italic"
                  >
                    All Surgeons
                  </div>
                  {surgeons
                    .filter(surgeon => {
                      const searchLower = (surgeonSearch || '').toLowerCase()
                      const fullName = `${surgeon.first_name} ${surgeon.surname}`.toLowerCase()
                      const reverseName = `${surgeon.surname} ${surgeon.first_name}`.toLowerCase()
                      return fullName.includes(searchLower) || reverseName.includes(searchLower)
                    })
                    .map((surgeon) => (
                      <div
                        key={surgeon._id}
                        onClick={() => {
                          const surgeonName = `${surgeon.first_name} ${surgeon.surname}`
                          setSurgeonFilter(surgeonName)
                          setSurgeonSearch('')
                          setShowSurgeonDropdown(false)
                        }}
                        className="px-3 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                      >
                        <div className="font-medium text-gray-900">
                          {surgeon.surname}, {surgeon.first_name}
                        </div>
                        {surgeon.gmc_number && (
                          <div className="text-xs text-gray-500">GMC: {surgeon.gmc_number}</div>
                        )}
                      </div>
                    ))}
                  {surgeons.filter(surgeon => {
                    const searchLower = (surgeonSearch || '').toLowerCase()
                    const fullName = `${surgeon.first_name} ${surgeon.surname}`.toLowerCase()
                    const reverseName = `${surgeon.surname} ${surgeon.first_name}`.toLowerCase()
                    return fullName.includes(searchLower) || reverseName.includes(searchLower)
                  }).length === 0 && (
                    <div className="px-3 py-2 text-sm text-gray-500">No surgeons found</div>
                  )}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
              <input
                type="date"
                value={startDateFilter}
                onChange={(e) => setStartDateFilter(e.target.value)}
                className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
              <input
                type="date"
                value={endDateFilter}
                onChange={(e) => setEndDateFilter(e.target.value)}
                className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {(urgencyFilter || surgeonFilter || startDateFilter || endDateFilter) && (
            <div className="flex justify-end">
              <Button
                variant="secondary"
                onClick={() => {
                  setUrgencyFilter('')
                  setSurgeonFilter('')
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
            <p className="text-gray-500 mb-4">
              {searchTerm || urgencyFilter || surgeonFilter || startDateFilter || endDateFilter
                ? 'No episodes match your search criteria'
                : 'Begin tracking surgical outcomes by recording your first surgery'}
            </p>
            {!searchTerm && !urgencyFilter && !surgeonFilter && !startDateFilter && !endDateFilter && (
              <Button 
                variant="primary"
                onClick={() => {
                  setSelectedEpisode(null)
                  setShowModal(true)
                }}
              >
                Record Your First Surgery
              </Button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Surgery ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Patient ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Procedure
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Surgeon
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Urgency
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredEpisodes.map((episode) => (
                  <tr key={episode.surgery_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                      {episode.surgery_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {episode.patient_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(episode.perioperative_timeline.surgery_date)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                      {episode.procedure.primary_procedure}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {episode.team.primary_surgeon}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getUrgencyColor(episode.classification.urgency)}`}>
                        {episode.classification.urgency}
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
      </div>
    </>
  )
}
