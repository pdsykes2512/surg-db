import { useState, useEffect } from 'react'
import { Button } from './Button'
import { AddTreatmentModal } from './AddTreatmentModal'
import { TumourModal } from './TumourModal'
import { TumourSummaryModal } from './TumourSummaryModal'
import { TreatmentSummaryModal } from './TreatmentSummaryModal'
import { formatFieldValue, formatFieldName, formatDate, formatStatus, formatCancerType, formatTreatmentType, formatSurgeon, capitalize } from '../utils/formatters'

interface Treatment {
  treatment_id: string
  treatment_type: string
  treatment_date?: string
  surgeon?: string
  notes?: string
  [key: string]: any
}

interface CancerEpisode {
  episode_id: string
  patient_id: string
  condition_type: string
  cancer_type?: string
  referral_date: string
  first_seen_date?: string
  mdt_discussion_date?: string
  lead_clinician: string
  episode_status: string
  cancer_data?: any
  treatments?: Treatment[]
  tumours?: any[]
  [key: string]: any
}

interface CancerEpisodeDetailModalProps {
  episode: CancerEpisode | null
  onClose: () => void
  onEdit?: (episode: CancerEpisode) => void
}

export function CancerEpisodeDetailModal({ episode, onClose, onEdit }: CancerEpisodeDetailModalProps) {
  const [treatments, setTreatments] = useState<Treatment[]>([])
  const [tumours, setTumours] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [showAddTreatment, setShowAddTreatment] = useState(false)
  const [editingTreatment, setEditingTreatment] = useState<Treatment | null>(null)
  const [showTumourModal, setShowTumourModal] = useState(false)
  const [editingTumour, setEditingTumour] = useState<any>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'tumours' | 'treatments'>('overview')
  const [viewingTumour, setViewingTumour] = useState<any>(null)
  const [viewingTreatment, setViewingTreatment] = useState<Treatment | null>(null)

  useEffect(() => {
    if (episode) {
      loadTreatments()
    }
  }, [episode])

  const loadTreatments = async () => {
    if (!episode) return
    
    try {
      setLoading(true)
      const response = await fetch(`http://localhost:8000/api/v2/episodes/${episode.episode_id}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setTreatments(data.treatments || [])
        setTumours(data.tumours || [])
      }
    } catch (error) {
      console.error('Failed to load treatments:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAddTreatment = async (treatment: any) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/v2/episodes/${episode.episode_id}/treatments`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify(treatment)
        }
      )
      
      if (response.ok) {
        await loadTreatments()
        setShowAddTreatment(false)
      } else {
        const error = await response.json()
        alert(`Failed to add treatment: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to add treatment:', error)
      alert('Failed to add treatment')
    }
  }

  const handleEditTreatment = async (treatment: any) => {
    if (!editingTreatment) return
    
    try {
      const response = await fetch(
        `http://localhost:8000/api/v2/episodes/${episode.episode_id}/treatments/${editingTreatment.treatment_id}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify(treatment)
        }
      )
      
      if (response.ok) {
        await loadTreatments()
        setEditingTreatment(null)
        setShowAddTreatment(false)
      } else {
        const error = await response.json()
        alert(`Failed to update treatment: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to update treatment:', error)
      alert('Failed to update treatment')
    }
  }

  const handleAddTumour = async (tumour: any) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/v2/episodes/${episode.episode_id}/tumours`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify(tumour)
        }
      )
      
      if (response.ok) {
        await loadTreatments()
        setShowTumourModal(false)
      } else {
        const error = await response.json()
        alert(`Failed to add tumour: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to add tumour:', error)
      alert('Failed to add tumour')
    }
  }

  const handleEditTumour = async (tumour: any) => {
    if (!editingTumour) return
    
    try {
      const response = await fetch(
        `http://localhost:8000/api/v2/episodes/${episode.episode_id}/tumours/${editingTumour.tumour_id}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify(tumour)
        }
      )
      
      if (response.ok) {
        await loadTreatments()
        setEditingTumour(null)
        setShowTumourModal(false)
      } else {
        const error = await response.json()
        alert(`Failed to update tumour: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to update tumour:', error)
      alert('Failed to update tumour')
    }
  }

  const handleDeleteTumour = async (tumourId: string) => {
    const userInput = prompt(`To confirm deletion, type this Tumour ID:\n\n${tumourId}`)
    
    if (userInput !== tumourId) {
      if (userInput !== null) {
        alert('Tumour ID does not match. Deletion cancelled.')
      }
      return
    }
    
    try {
      const response = await fetch(
        `http://localhost:8000/api/v2/episodes/${episode.episode_id}/tumours/${tumourId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      )
      
      if (response.ok) {
        await loadTreatments()
      } else {
        const error = await response.json()
        alert(`Failed to delete tumour: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to delete tumour:', error)
      alert('Failed to delete tumour')
    }
  }

  const handleDeleteTreatment = async (treatmentId: string) => {
    const userInput = prompt(`To confirm deletion, type this Treatment ID:\n\n${treatmentId}`)
    
    if (userInput !== treatmentId) {
      if (userInput !== null) {
        alert('Treatment ID does not match. Deletion cancelled.')
      }
      return
    }
    
    try {
      const response = await fetch(
        `http://localhost:8000/api/v2/episodes/${episode.episode_id}/treatments/${treatmentId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      )
      
      if (response.ok) {
        await loadTreatments()
      } else {
        const error = await response.json()
        alert(`Failed to delete treatment: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to delete treatment:', error)
      alert('Failed to delete treatment')
    }
  }

  if (!episode) return null

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '—'
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

  const formatCancerType = (type?: string) => {
    if (!type) return '—'
    return type.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())
  }

  const getTreatmentTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      surgery: 'bg-blue-100 text-blue-800',
      chemotherapy: 'bg-purple-100 text-purple-800',
      radiotherapy: 'bg-orange-100 text-orange-800',
      immunotherapy: 'bg-green-100 text-green-800',
      hormone_therapy: 'bg-pink-100 text-pink-800',
      targeted_therapy: 'bg-indigo-100 text-indigo-800',
      palliative: 'bg-gray-100 text-gray-800',
      surveillance: 'bg-yellow-100 text-yellow-800'
    }
    return colors[type] || 'bg-gray-100 text-gray-800'
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-3 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-white">Cancer Episode Details</h2>
            <p className="text-blue-100 text-sm mt-1">{episode.episode_id}</p>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:text-gray-200 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b bg-gray-50">
          <div className="flex space-x-4 px-6">
            <button
              onClick={() => setActiveTab('overview')}
              className={`py-3 px-2 border-b-2 font-medium text-sm ${
                activeTab === 'overview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('tumours')}
              className={`py-3 px-2 border-b-2 font-medium text-sm ${
                activeTab === 'tumours'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Tumours ({tumours.length})
            </button>
            <button
              onClick={() => setActiveTab('treatments')}
              className={`py-3 px-2 border-b-2 font-medium text-sm ${
                activeTab === 'treatments'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Treatments ({treatments.length})
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Basic Information */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Episode Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-500">Patient ID</label>
                    <p className="text-sm text-gray-900 mt-1">{episode.patient_id}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Cancer Type</label>
                    <p className="text-sm text-gray-900 mt-1">
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                        {formatCancerType(episode.cancer_type)}
                      </span>
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Status</label>
                    <p className="text-sm text-gray-900 mt-1">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                        episode.episode_status === 'active' ? 'bg-blue-100 text-blue-800' :
                        episode.episode_status === 'completed' ? 'bg-gray-100 text-gray-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {formatStatus(episode.episode_status)}
                      </span>
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Referral Date</label>
                    <p className="text-sm text-gray-900 mt-1">{formatDate(episode.referral_date)}</p>
                  </div>
                  {episode.referral_source && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">Referral Source</label>
                      <p className="text-sm text-gray-900 mt-1">
                        {episode.referral_source === '2ww' ? '2 Week Wait' : 
                         episode.referral_source.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                      </p>
                    </div>
                  )}
                  {episode.provider_first_seen && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">Provider First Seen</label>
                      <p className="text-sm text-gray-900 mt-1">{episode.provider_first_seen}</p>
                    </div>
                  )}
                  {episode.cns_involved && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">CNS Involved</label>
                      <p className="text-sm text-gray-900 mt-1">
                        {episode.cns_involved === 'yes' ? 'Yes' : 
                         episode.cns_involved === 'no' ? 'No' : 'Unknown'}
                      </p>
                    </div>
                  )}
                  <div>
                    <label className="text-sm font-medium text-gray-500">First Seen</label>
                    <p className="text-sm text-gray-900 mt-1">{formatDate(episode.first_seen_date)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">MDT Discussion</label>
                    <p className="text-sm text-gray-900 mt-1">{formatDate(episode.mdt_discussion_date)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Performance Status</label>
                    <p className="text-sm text-gray-900 mt-1">
                      {episode.performance_status ? `ECOG ${episode.performance_status}` : 'Not assessed'}
                    </p>
                  </div>
                  {episode.no_treatment_reason && (
                    <div className="md:col-span-3">
                      <label className="text-sm font-medium text-gray-500">No Treatment Reason</label>
                      <p className="text-sm text-gray-900 mt-1">
                        {episode.no_treatment_reason.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                      </p>
                    </div>
                  )}
                  <div className="md:col-span-3">
                    <label className="text-sm font-medium text-gray-500">Lead Clinician</label>
                    <p className="text-sm text-gray-900 mt-1">{episode.lead_clinician}</p>
                  </div>
                </div>
              </div>

              {/* Cancer-Specific Data */}
              {episode.cancer_data && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">Cancer Details</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.entries(episode.cancer_data).map(([key, value]) => {
                      if (typeof value === 'object' || !value) return null
                      return (
                        <div key={key}>
                          <label className="text-sm font-medium text-gray-500">
                            {formatFieldName(key)}
                          </label>
                          <p className="text-sm text-gray-900 mt-1">{formatFieldValue(value)}</p>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tumours Tab */}
          {activeTab === 'tumours' && (
            <div className="bg-white rounded-lg border">
              <div className="px-6 py-4 border-b flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">
                  Tumour Sites ({tumours.length})
                </h3>
                <button
                  onClick={() => {
                    setEditingTumour(null)
                    setShowTumourModal(true)
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                  + Add Tumour
                </button>
              </div>

              {loading ? (
                <div className="p-8 text-center text-gray-500">Loading tumours...</div>
              ) : tumours.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <p className="mb-2">No tumours recorded yet</p>
                  <p className="text-sm">Add individual tumour sites to track primaries, metastases, or recurrences</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Tumour ID
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Type
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Site
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          ICD-10
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          TNM (Clinical)
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          TNM (Path)
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {tumours.map((tumour: any) => (
                        <tr 
                          key={tumour.tumour_id} 
                          className="hover:bg-blue-50 cursor-pointer transition-colors"
                          onClick={() => setViewingTumour(tumour)}
                        >
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {tumour.tumour_id}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                              tumour.tumour_type === 'primary' ? 'bg-blue-100 text-blue-800' :
                              tumour.tumour_type === 'metastasis' ? 'bg-red-100 text-red-800' :
                              'bg-yellow-100 text-yellow-800'
                            }`}>
                              {capitalize(tumour.tumour_type)}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {tumour.site?.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {tumour.icd10_code || '—'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {tumour.clinical_t || tumour.clinical_n || tumour.clinical_m ? (
                              `${tumour.clinical_t || '?'}${tumour.clinical_n || '?'}${tumour.clinical_m || '?'}`
                            ) : '—'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {tumour.pathological_t || tumour.pathological_n || tumour.pathological_m ? (
                              `${tumour.pathological_t || '?'}${tumour.pathological_n || '?'}${tumour.pathological_m || '?'}`
                            ) : '—'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            <div className="flex space-x-2">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setEditingTumour(tumour)
                                  setShowTumourModal(true)
                                }}
                                className="text-blue-600 hover:text-blue-900"
                                title="Edit tumour"
                              >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleDeleteTumour(tumour.tumour_id)
                                }}
                                className="text-red-600 hover:text-red-900"
                                title="Delete tumour"
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
            </div>
          )}

          {/* Treatments Tab */}
          {activeTab === 'treatments' && (
            <div className="bg-white rounded-lg border">
              <div className="px-6 py-4 border-b flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">
                  Treatments ({treatments.length})
                </h3>
                <button
                  onClick={() => setShowAddTreatment(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                  + Add Treatment
                </button>
              </div>

              {loading ? (
                <div className="p-8 text-center text-gray-500">Loading treatments...</div>
              ) : treatments.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  No treatments recorded yet
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Treatment ID
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Type
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Date
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Details
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Clinician
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {treatments.map((treatment) => (
                        <tr 
                          key={treatment.treatment_id} 
                          className="hover:bg-blue-50 cursor-pointer transition-colors"
                          onClick={() => setViewingTreatment(treatment)}
                        >
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {treatment.treatment_id}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getTreatmentTypeColor(treatment.treatment_type)}`}>
                              {formatTreatmentType(treatment.treatment_type)}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {formatDate(treatment.treatment_date)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 max-w-xs truncate">
                            {treatment.treatment_type === 'surgery' && treatment.procedure_name ? (
                              treatment.procedure_name
                            ) : treatment.treatment_type === 'chemotherapy' && treatment.regimen ? (
                              `${treatment.regimen} (Cycle ${treatment.cycle_number || '?'})`
                            ) : treatment.treatment_type === 'radiotherapy' && treatment.site ? (
                              `${treatment.site} - ${treatment.total_dose || '?'}Gy`
                            ) : (
                              treatment.notes || '—'
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {formatSurgeon(treatment.surgeon || treatment.oncologist)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            <div className="flex space-x-2">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setEditingTreatment(treatment)
                                  setShowAddTreatment(true)
                                }}
                                className="text-blue-600 hover:text-blue-900"
                                title="Edit treatment"
                              >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleDeleteTreatment(treatment.treatment_id)
                                }}
                                className="text-red-600 hover:text-red-900"
                                title="Delete treatment"
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
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 flex justify-between">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
          {onEdit && (
            <Button onClick={() => {
              onEdit(episode)
              onClose()
            }}>
              Edit Episode
            </Button>
          )}
        </div>
      </div>

      {/* Nested Modals */}
      <div>
        {/* Tumour Modal */}
        {showTumourModal && (
          <TumourModal
            episodeId={episode.episode_id}
            onSubmit={editingTumour ? handleEditTumour : handleAddTumour}
            onCancel={() => {
              setShowTumourModal(false)
              setEditingTumour(null)
            }}
            mode={editingTumour ? 'edit' : 'create'}
            initialData={editingTumour}
          />
        )}

        {/* Add Treatment Modal */}
        {showAddTreatment && (
          <AddTreatmentModal
            episodeId={episode.episode_id}
            onSubmit={editingTreatment ? handleEditTreatment : handleAddTreatment}
            onCancel={() => {
              setShowAddTreatment(false)
              setEditingTreatment(null)
            }}
            mode={editingTreatment ? 'edit' : 'create'}
            initialData={editingTreatment}
          />
        )}

        {/* Tumour Summary Modal */}
        {viewingTumour && (
          <TumourSummaryModal
            tumour={viewingTumour}
            onClose={() => setViewingTumour(null)}
            onEdit={() => {
              setEditingTumour(viewingTumour)
              setViewingTumour(null)
              setShowTumourModal(true)
            }}
          />
        )}

        {/* Treatment Summary Modal */}
        {viewingTreatment && (
          <TreatmentSummaryModal
            treatment={viewingTreatment}
            onClose={() => setViewingTreatment(null)}
            onEdit={() => {
              setEditingTreatment(viewingTreatment)
              setViewingTreatment(null)
              setShowAddTreatment(true)
            }}
          />
        )}
      </div>
    </div>
  )
}
