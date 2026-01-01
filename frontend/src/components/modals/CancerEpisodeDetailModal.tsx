import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useModalShortcuts } from '../../hooks/useModalShortcuts'
import { Button } from '../common/Button'
import { ProviderDisplay } from '../common/ProviderDisplay'
import { AddTreatmentModal } from './AddTreatmentModal'
import { TumourModal } from './TumourModal'
import { TumourSummaryModal } from './TumourSummaryModal'
import { TreatmentSummaryModal } from './TreatmentSummaryModal'
import { InvestigationModal } from './InvestigationModal'
import { FollowUpModal } from './FollowUpModal'
import { formatStatus, formatTreatmentType, formatSurgeon, capitalize, formatTreatmentPlan, formatCodedValue, formatAnatomicalSite, formatClinicalTNM, formatPathologicalTNM, formatInvestigationType, formatDate } from '../../utils/formatters'
import { calculateStage, getStageColor, formatStage } from '../../utils/cancerStaging'

interface Treatment {
  treatment_id: string
  treatment_type: string
  treatment_date?: string
  surgeon?: string
  surgeon_name?: string
  anaesthetist_name?: string
  oncologist?: string
  procedure_name?: string
  regimen?: string
  cycle_number?: number
  site?: string
  total_dose?: number
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
  initialTab?: 'overview' | 'tumours' | 'treatments' | 'investigations' | 'followups'
  initialTreatmentId?: string
  initialTumourId?: string
  initialInvestigationId?: string
  openEditDirectly?: boolean
}

export function CancerEpisodeDetailModal({
  episode,
  onClose,
  onEdit,
  initialTab = 'overview',
  initialTreatmentId,
  initialTumourId,
  initialInvestigationId,
  openEditDirectly = false
}: CancerEpisodeDetailModalProps) {
  const [treatments, setTreatments] = useState<Treatment[]>([])
  const [tumours, setTumours] = useState<any[]>([])
  const [investigations, setInvestigations] = useState<any[]>([])
  const [followUps, setFollowUps] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [showAddTreatment, setShowAddTreatment] = useState(false)
  const [editingTreatment, setEditingTreatment] = useState<Treatment | null>(null)
  const [showTumourModal, setShowTumourModal] = useState(false)
  const [editingTumour, setEditingTumour] = useState<any>(null)
  const [showInvestigationModal, setShowInvestigationModal] = useState(false)
  const [editingInvestigation, setEditingInvestigation] = useState<any>(null)
  const [showFollowUpModal, setShowFollowUpModal] = useState(false)
  const [editingFollowUp, setEditingFollowUp] = useState<any>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'tumours' | 'treatments' | 'investigations' | 'followups'>(initialTab)
  const [viewingTumour, setViewingTumour] = useState<any>(null)
  const [viewingTreatment, setViewingTreatment] = useState<Treatment | null>(null)

  // Delete confirmation states
  const [deleteTumourConfirmation, setDeleteTumourConfirmation] = useState<{ show: boolean; tumour: any | null }>({ show: false, tumour: null })
  const [deleteTumourConfirmText, setDeleteTumourConfirmText] = useState('')
  const [deleteTreatmentConfirmation, setDeleteTreatmentConfirmation] = useState<{ show: boolean; treatment: Treatment | null }>({ show: false, treatment: null })
  const [deleteTreatmentConfirmText, setDeleteTreatmentConfirmText] = useState('')
  const [deleteInvestigationConfirmation, setDeleteInvestigationConfirmation] = useState<{ show: boolean; investigation: any | null }>({ show: false, investigation: null })
  const [deleteInvestigationConfirmText, setDeleteInvestigationConfirmText] = useState('')

  // Check if any nested modal is open
  const hasNestedModalOpen = showAddTreatment || showTumourModal || showInvestigationModal || showFollowUpModal ||
    editingTreatment || editingTumour || editingInvestigation || editingFollowUp ||
    viewingTumour || viewingTreatment ||
    deleteTumourConfirmation.show || deleteTreatmentConfirmation.show || deleteInvestigationConfirmation.show

  // Keyboard shortcuts: Escape to close (only when no nested modals are open)
  useModalShortcuts({
    onClose,
    isOpen: !hasNestedModalOpen
  })

  // Quick add keyboard shortcuts: I (investigation), P (tumour/primary), R (treatment)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if typing in an input field or if any modal is already open
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        return
      }

      // Don't trigger if any add/edit modal is already open
      if (hasNestedModalOpen) {
        return
      }

      // Check for modifier keys
      if (e.metaKey || e.ctrlKey || e.altKey) {
        return
      }

      switch (e.key.toLowerCase()) {
        case 'i':
          e.preventDefault()
          setShowInvestigationModal(true)
          break
        case 'p':
          e.preventDefault()
          setShowTumourModal(true)
          break
        case 'r':
          e.preventDefault()
          setShowAddTreatment(true)
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [hasNestedModalOpen])

  // Lock body scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    document.body.style.margin = '0'
    document.body.style.padding = '0'
    return () => {
      document.body.style.overflow = ''
      document.body.style.margin = ''
      document.body.style.padding = ''
    }
  }, [])


  useEffect(() => {
    if (episode) {
      loadTreatments()
    }
  }, [episode])

  // Handle opening specific treatment/tumour/investigation when provided
  useEffect(() => {
    if (!treatments.length && !tumours.length && !investigations.length) return

    if (initialTreatmentId && treatments.length > 0) {
      const treatment = treatments.find(t => t.treatment_id === initialTreatmentId)
      if (treatment) {
        // Open edit modal directly if requested (e.g., from recent activity update action)
        if (openEditDirectly) {
          setEditingTreatment(treatment)
          setShowAddTreatment(true)
        } else {
          setViewingTreatment(treatment)
        }
      }
    }

    if (initialTumourId && tumours.length > 0) {
      const tumour = tumours.find(t => t.tumour_id === initialTumourId)
      if (tumour) {
        setViewingTumour(tumour)
      }
    }

    if (initialInvestigationId && investigations.length > 0) {
      const investigation = investigations.find(i => i.investigation_id === initialInvestigationId)
      if (investigation) {
        setEditingInvestigation(investigation)
        setShowInvestigationModal(true)
      }
    }
  }, [treatments, tumours, investigations, initialTreatmentId, initialTumourId, initialInvestigationId, openEditDirectly])

  const loadTreatments = async () => {
    if (!episode) return
    
    try {
      setLoading(true)
      // Use /api for relative URLs when VITE_API_URL is /api (uses Vite proxy)
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const url = `${API_URL}/episodes/${episode.episode_id}`
      console.log('Loading episode data from:', url)
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      console.log('Response status:', response.status, response.ok)
      if (response.ok) {
        const data = await response.json()
        console.log('Episode data received:', {
          treatments: data.treatments?.length || 0,
          tumours: data.tumours?.length || 0,
          investigations: data.investigations?.length || 0,
          followUps: data.follow_ups?.length || 0
        })
        setTreatments(data.treatments || [])
        setTumours(data.tumours || [])
        setInvestigations(data.investigations || [])
        setFollowUps(data.follow_ups || [])
      } else {
        console.error('Failed to load episode data:', response.status, await response.text())
      }
    } catch (error) {
      console.error('Failed to load treatments:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAddTreatment = async (treatment: any) => {
    if (!episode) return
    try {
      // Use /api for relative URLs (uses Vite proxy)
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(
        `${API_URL}/episodes/${episode.episode_id}/treatments`,
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
    if (!editingTreatment || !episode) return

    try {
      // Use /api for relative URLs (uses Vite proxy)
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(
        `${API_URL}/episodes/${episode.episode_id}/treatments/${editingTreatment.treatment_id}`,
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
    if (!episode) return
    try {
      // Use /api for relative URLs (uses Vite proxy)
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(
        `${API_URL}/episodes/${episode.episode_id}/tumours`,
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
    if (!editingTumour || !episode) return
    
    try {
      // Use /api for relative URLs (uses Vite proxy)
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(
        `${API_URL}/episodes/${episode.episode_id}/tumours/${editingTumour.tumour_id}`,
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

  const handleDeleteTumourClick = (tumour: any) => {
    setDeleteTumourConfirmation({ show: true, tumour })
    setDeleteTumourConfirmText('')
  }

  const handleDeleteTumourConfirm = async () => {
    if (!deleteTumourConfirmation.tumour || !episode) return
    
    try {
      // Use /api for relative URLs (uses Vite proxy)
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(
        `${API_URL}/episodes/${episode.episode_id}/tumours/${deleteTumourConfirmation.tumour.tumour_id}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      )
      
      if (response.ok) {
        setDeleteTumourConfirmation({ show: false, tumour: null })
        setDeleteTumourConfirmText('')
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

  const handleDeleteTreatmentClick = (treatment: Treatment) => {
    setDeleteTreatmentConfirmation({ show: true, treatment })
    setDeleteTreatmentConfirmText('')
  }

  const handleDeleteTreatmentConfirm = async () => {
    if (!deleteTreatmentConfirmation.treatment || !episode) return
    
    try {
      // Use /api for relative URLs (uses Vite proxy)
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(
        `${API_URL}/episodes/${episode.episode_id}/treatments/${deleteTreatmentConfirmation.treatment.treatment_id}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      )
      
      if (response.ok) {
        setDeleteTreatmentConfirmation({ show: false, treatment: null })
        setDeleteTreatmentConfirmText('')
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

  const handleDeleteInvestigationClick = (investigation: any) => {
    setDeleteInvestigationConfirmation({ show: true, investigation })
    setDeleteInvestigationConfirmText('')
  }

  const handleDeleteInvestigationConfirm = async () => {
    if (!deleteInvestigationConfirmation.investigation || !episode) return
    
    try {
      // Use /api for relative URLs (uses Vite proxy)
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(
        `${API_URL}/investigations/${deleteInvestigationConfirmation.investigation.investigation_id}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      )
      
      if (response.ok) {
        setDeleteInvestigationConfirmation({ show: false, investigation: null })
        setDeleteInvestigationConfirmText('')
        await loadTreatments() // Reloads investigations too
      } else {
        const error = await response.json()
        alert(`Failed to delete investigation: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to delete investigation:', error)
      alert('Failed to delete investigation')
    }
  }

  // Investigation handlers
  const handleAddInvestigation = async (investigation: any) => {
    if (!episode) return
    
    try {
      // Use /api for relative URLs (uses Vite proxy)
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(`${API_URL}/investigations/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(investigation)
      })
      
      if (response.ok) {
        await loadTreatments() // Reloads investigations too
        setShowInvestigationModal(false)
      } else {
        const error = await response.json()
        alert(`Failed to add investigation: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to add investigation:', error)
      alert('Failed to add investigation')
    }
  }

  const handleEditInvestigation = async (investigation: any) => {
    if (!editingInvestigation || !episode) return
    
    try {
      // Use /api for relative URLs (uses Vite proxy)
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(
        `${API_URL}/investigations/${editingInvestigation.investigation_id}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify(investigation)
        }
      )
      
      if (response.ok) {
        await loadTreatments() // Reloads investigations too
        setEditingInvestigation(null)
        setShowInvestigationModal(false)
      } else {
        const error = await response.json()
        console.error('Investigation update error:', error)
        
        // Handle validation errors (422)
        if (error.detail && Array.isArray(error.detail)) {
          const errorMessages = error.detail.map((err: any) => 
            `${err.loc?.join('.')} - ${err.msg}`
          ).join(', ')
          alert(`Failed to update investigation: ${errorMessages}`)
        } else {
          alert(`Failed to update investigation: ${error.detail || JSON.stringify(error)}`)
        }
      }
    } catch (error) {
      console.error('Failed to update investigation:', error)
      alert('Failed to update investigation')
    }
  }

  // Follow-up handlers
  const handleAddFollowUp = async (followUp: any) => {
    if (!episode) return
    console.log('Adding follow-up:', followUp)
    // TODO: Implement API call when backend endpoint is ready
    setFollowUps([...followUps, followUp])
    setShowFollowUpModal(false)
    alert('Follow-up added (API integration pending)')
  }

  const handleEditFollowUp = async (followUp: any) => {
    if (!episode) return
    console.log('Editing follow-up:', followUp)
    // TODO: Implement API call when backend endpoint is ready
    const updated = followUps.map(fu => 
      fu.followup_id === followUp.followup_id ? followUp : fu
    )
    setFollowUps(updated)
    setEditingFollowUp(null)
    setShowFollowUpModal(false)
    alert('Follow-up updated (API integration pending)')
  }

  if (!episode) return null

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

  let modalRoot = document.getElementById('modal-root')
  if (!modalRoot) {
    modalRoot = document.createElement('div')
    modalRoot.setAttribute('id', 'modal-root')
    document.body.appendChild(modalRoot)
  }

  return createPortal(
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[100] p-4" style={{ margin: 0 }}>
      <div className="bg-white rounded-lg shadow-xl max-w-full sm:max-w-3xl md:max-w-4xl lg:max-w-5xl xl:max-w-6xl w-full max-h-[90vh] md:h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-4 sm:px-6 py-3 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-white">Cancer Episode Details</h2>
            <p className="text-blue-100 text-sm mt-1 tabular-nums">{episode.episode_id}</p>
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
          <div className="flex overflow-x-auto space-x-2 sm:space-x-4 px-4 sm:px-6">
            <button
              onClick={() => setActiveTab('overview')}
              className={`py-3 px-3 sm:px-4 border-b-2 font-medium text-xs sm:text-sm whitespace-nowrap ${
                activeTab === 'overview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('investigations')}
              className={`py-3 px-3 sm:px-4 border-b-2 font-medium text-xs sm:text-sm whitespace-nowrap ${
                activeTab === 'investigations'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Investigations ({investigations.length})
            </button>
            <button
              onClick={() => setActiveTab('tumours')}
              className={`py-3 px-3 sm:px-4 border-b-2 font-medium text-xs sm:text-sm whitespace-nowrap ${
                activeTab === 'tumours'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Pathology ({tumours.length})
            </button>
            <button
              onClick={() => setActiveTab('treatments')}
              className={`py-3 px-3 sm:px-4 border-b-2 font-medium text-xs sm:text-sm whitespace-nowrap ${
                activeTab === 'treatments'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Treatments ({treatments.length})
            </button>
            <button
              onClick={() => setActiveTab('followups')}
              className={`py-3 px-3 sm:px-4 border-b-2 font-medium text-xs sm:text-sm whitespace-nowrap ${
                activeTab === 'followups'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Follow-ups ({followUps.length})
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 sm:space-y-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Basic Information */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Episode Information</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-500">Patient ID</label>
                    <p className="text-sm text-gray-900 mt-1 tabular-nums">{episode.patient_id}</p>
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
                    <p className="text-sm text-gray-900 mt-1 tabular-nums">{formatDate(episode.referral_date)}</p>
                  </div>
                  {episode.referral_source && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">Referral Source</label>
                      <p className="text-sm text-gray-900 mt-1">
                        {episode.referral_source === '2ww' ? '2 Week Wait' : formatCodedValue(episode.referral_source)}
                      </p>
                    </div>
                  )}
                  {episode.referral_type && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">Referral Type</label>
                      <p className="text-sm text-gray-900 mt-1">
                        {formatCodedValue(episode.referral_type)}
                      </p>
                    </div>
                  )}
                  {episode.provider_first_seen && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">Provider First Seen</label>
                      <p className="text-sm text-gray-900 mt-1">
                        <ProviderDisplay code={episode.provider_first_seen} />
                      </p>
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
                    <p className="text-sm text-gray-900 mt-1 tabular-nums">{formatDate(episode.first_seen_date)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">MDT Discussion</label>
                    <p className="text-sm text-gray-900 mt-1 tabular-nums">{formatDate(episode.mdt_discussion_date || episode.mdt_outcome?.mdt_discussion_date)}</p>
                  </div>
                  {(episode.mdt_meeting_type || episode.mdt_outcome?.mdt_meeting_type) && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">MDT Meeting Type</label>
                      <p className="text-sm text-gray-900 mt-1">
                        {formatCodedValue(episode.mdt_meeting_type || episode.mdt_outcome?.mdt_meeting_type)}
                      </p>
                    </div>
                  )}
                  {(episode.treatment_intent || episode.mdt_outcome?.treatment_intent) && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">Treatment Intent</label>
                      <p className="text-sm text-gray-900 mt-1">
                        {formatCodedValue(episode.treatment_intent || episode.mdt_outcome?.treatment_intent)}
                      </p>
                    </div>
                  )}
                  {(episode.treatment_plan || episode.mdt_outcome?.treatment_plan) && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">Treatment Plan</label>
                      <p className="text-sm text-gray-900 mt-1">
                        {formatTreatmentPlan(episode.treatment_plan || episode.mdt_outcome?.treatment_plan)}
                      </p>
                    </div>
                  )}
                  <div>
                    <label className="text-sm font-medium text-gray-500">Performance Status</label>
                    <p className="text-sm text-gray-900 mt-1">
                      {episode.performance_status ? `ECOG ${episode.performance_status}` : 'Not assessed'}
                    </p>
                  </div>
                  {episode.surgery_performed !== null && episode.surgery_performed !== undefined && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">Surgery Performed</label>
                      <p className="text-sm text-gray-900 mt-1">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          episode.surgery_performed ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {episode.surgery_performed ? 'Yes' : 'No'}
                        </span>
                      </p>
                    </div>
                  )}
                  {episode.no_treatment_reason && (
                    <div className="md:col-span-3">
                      <label className="text-sm font-medium text-gray-500">No Treatment Reason</label>
                      <p className="text-sm text-gray-900 mt-1">
                        {episode.no_treatment_reason.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                      </p>
                      {episode.no_treatment_reason_detail && (
                        <p className="text-sm text-gray-600 mt-1 italic">
                          Detail: {episode.no_treatment_reason_detail}
                        </p>
                      )}
                    </div>
                  )}
                  <div className="md:col-span-3">
                    <label className="text-sm font-medium text-gray-500">Lead Clinician</label>
                    <p className="text-sm text-gray-900 mt-1">{episode.lead_clinician}</p>
                  </div>
                </div>
              </div>

              {/* Pathology and Treatment Summaries Side by Side */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Pathology Summary */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-semibold text-gray-900">Pathology Summary</h3>
                    <button
                      onClick={() => setActiveTab('tumours')}
                      className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                    >
                      View Details →
                    </button>
                  </div>
                  {tumours.length === 0 ? (
                    <p className="text-sm text-gray-500 italic">No pathology recorded</p>
                  ) : (
                    <div className="space-y-3">
                      {tumours.map((tumour: any) => (
                        <div key={tumour.tumour_id} className="bg-white rounded-md p-3 border border-gray-200">
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center space-x-2">
                              <span className={`px-2 py-1 text-xs font-semibold rounded ${
                                tumour.tumour_type === 'primary' ? 'bg-red-100 text-red-800' :
                                tumour.tumour_type === 'metastasis' ? 'bg-orange-100 text-orange-800' :
                                tumour.tumour_type === 'recurrence' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-gray-100 text-gray-800'
                              }`}>
                                {tumour.tumour_type?.replace('_', ' ').toUpperCase() || 'UNKNOWN'}
                              </span>
                              <span className="text-sm font-medium text-gray-900">{formatAnatomicalSite(tumour.site)}</span>
                              {tumour.screening?.bowel_cancer_screening_programme && (
                                <span className="px-2 py-0.5 text-xs font-medium rounded bg-blue-100 text-blue-800">BCSP</span>
                              )}
                            </div>
                          </div>
                          
                          {/* Pathology Info */}
                          <div className="grid grid-cols-2 gap-2 text-xs mb-2">
                            {tumour.size_mm && (
                              <div>
                                <span className="text-gray-500">Size:</span>
                                <span className="ml-1 text-gray-900">{tumour.size_mm}mm</span>
                              </div>
                            )}
                            {tumour.grade && (
                              <div>
                                <span className="text-gray-500">Grade:</span>
                                <span className="ml-1 text-gray-900">{tumour.grade.toUpperCase()}</span>
                              </div>
                            )}
                            {tumour.histology_type && (
                              <div>
                                <span className="text-gray-500">Histology:</span>
                                <span className="ml-1 text-gray-900">{capitalize(tumour.histology_type)}</span>
                              </div>
                            )}
                          </div>

                          {/* TNM Staging */}
                          {(tumour.clinical_t || tumour.clinical_n || tumour.clinical_m || 
                            tumour.pathological_t || tumour.pathological_n || tumour.pathological_m) && (
                            <div className="border-t border-gray-200 pt-2 mt-2">
                              <div className="text-xs font-medium text-gray-700 mb-1">TNM Staging</div>
                              <div className="space-y-1.5">
                                {(tumour.clinical_t || tumour.clinical_n || tumour.clinical_m) && (
                                  <div className="flex items-center justify-between text-xs">
                                    <div>
                                      <span className="text-gray-500">Clinical:</span>
                                      <span className="ml-1 text-gray-900 tabular-nums">
                                        {formatClinicalTNM(tumour.clinical_t, tumour.clinical_n, tumour.clinical_m)}
                                      </span>
                                    </div>
                                  </div>
                                )}
                                {(tumour.pathological_t || tumour.pathological_n || tumour.pathological_m) && (() => {
                                  const stage = calculateStage('bowel', tumour.pathological_t, tumour.pathological_n, tumour.pathological_m)
                                  return (
                                    <div className="flex items-center justify-between text-xs">
                                      <div>
                                        <span className="text-gray-500">Pathological:</span>
                                        <span className="ml-1 text-gray-900 tabular-nums">
                                          {formatPathologicalTNM(tumour.pathological_t, tumour.pathological_n, tumour.pathological_m)}
                                        </span>
                                      </div>
                                      {stage !== 'Unknown' && (
                                        <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${getStageColor(stage)}`}>
                                          {formatStage(stage)}
                                        </span>
                                      )}
                                    </div>
                                  )
                                })()}
                              </div>
                            </div>
                          )}

                          {/* Lymph Nodes & Margins */}
                          {(tumour.lymph_nodes_examined || tumour.lymph_nodes_positive || 
                            tumour.crm_status || tumour.proximal_margin_mm || tumour.distal_margin_mm) && (
                            <div className="border-t border-gray-200 pt-2 mt-2">
                              <div className="grid grid-cols-2 gap-2 text-xs">
                                {(tumour.lymph_nodes_examined || tumour.lymph_nodes_positive) && (
                                  <div>
                                    <span className="text-gray-500">Lymph nodes:</span>
                                    <span className="ml-1 text-gray-900">
                                      {tumour.lymph_nodes_positive || 0}/{tumour.lymph_nodes_examined || 0} positive
                                    </span>
                                  </div>
                                )}
                                {tumour.crm_status && (
                                  <div>
                                    <span className="text-gray-500">CRM:</span>
                                    <span className={`ml-1 font-medium ${
                                      tumour.crm_status === 'negative' || tumour.crm_status === 'no' ? 'text-green-600' : 'text-red-600'
                                    }`}>{capitalize(tumour.crm_status)}</span>
                                  </div>
                                )}
                                {tumour.proximal_margin_mm && (
                                  <div>
                                    <span className="text-gray-500">Proximal margin:</span>
                                    <span className="ml-1 text-gray-900">{tumour.proximal_margin_mm}mm</span>
                                  </div>
                                )}
                                {tumour.distal_margin_mm && (
                                  <div>
                                    <span className="text-gray-500">Distal margin:</span>
                                    <span className="ml-1 text-gray-900">{tumour.distal_margin_mm}mm</span>
                                  </div>
                                )}
                                {tumour.lymphovascular_invasion && (
                                  <div>
                                    <span className="text-gray-500">LVI:</span>
                                    <span className="ml-1 text-red-600 font-medium">Present</span>
                                  </div>
                                )}
                                {tumour.perineural_invasion && (
                                  <div>
                                    <span className="text-gray-500">PNI:</span>
                                    <span className="ml-1 text-red-600 font-medium">Present</span>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Treatment Summary */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-semibold text-gray-900">Treatment Summary</h3>
                    <button
                      onClick={() => setActiveTab('treatments')}
                      className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                    >
                      View Details →
                    </button>
                  </div>
                  {treatments.length === 0 ? (
                    <p className="text-sm text-gray-500 italic">No treatments recorded</p>
                  ) : (
                    <div className="space-y-3">
                      {treatments.map((treatment: Treatment) => (
                        <div key={treatment.treatment_id} className="bg-white rounded-md p-3 border border-gray-200">
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center space-x-2">
                              <span className={`px-2 py-1 text-xs font-semibold rounded ${getTreatmentTypeColor(treatment.treatment_type)}`}>
                                {formatTreatmentType(treatment.treatment_type)}
                              </span>
                              {treatment.treatment_date && (
                                <span className="text-sm text-gray-600 tabular-nums">{formatDate(treatment.treatment_date)}</span>
                              )}
                            </div>
                          </div>
                          <div className="space-y-1 text-xs">
                            {treatment.treatment_type === 'surgery' && treatment.procedure_name && (
                              <div>
                                <span className="text-gray-500">Procedure:</span>
                                <span className="ml-1 text-gray-900">{treatment.procedure_name}</span>
                              </div>
                            )}
                            {treatment.treatment_type === 'surgery' && treatment.approach && (
                              <div>
                                <span className="text-gray-500">Approach:</span>
                                <span className="ml-1 text-gray-900 capitalize">{treatment.approach}</span>
                              </div>
                            )}
                            {(treatment.treatment_type === 'surgery' || treatment.treatment_type === 'endoscopy') && (
                              <>
                                {(treatment.surgeon_name || treatment.surgeon) && (
                                  <div>
                                    <span className="text-gray-500">Surgeon:</span>
                                    <span className="ml-1 text-gray-900">{treatment.surgeon_name || (treatment.surgeon ? formatSurgeon(treatment.surgeon) : 'Not specified')}</span>
                                  </div>
                                )}
                                {treatment.anaesthetist_name && (
                                  <div>
                                    <span className="text-gray-500">Anaesthetist:</span>
                                    <span className="ml-1 text-gray-900">{treatment.anaesthetist_name}</span>
                                  </div>
                                )}
                              </>
                            )}
                            {treatment.treatment_type === 'chemotherapy' && treatment.regimen && (
                              <div>
                                <span className="text-gray-500">Regimen:</span>
                                <span className="ml-1 text-gray-900">{treatment.regimen}</span>
                                {treatment.cycle_number && (
                                  <span className="ml-2 text-gray-500">(Cycle {treatment.cycle_number})</span>
                                )}
                              </div>
                            )}
                            {treatment.treatment_type === 'radiotherapy' && (
                              <>
                                {treatment.site && (
                                  <div>
                                    <span className="text-gray-500">Site:</span>
                                    <span className="ml-1 text-gray-900">{formatAnatomicalSite(treatment.site)}</span>
                                  </div>
                                )}
                                {treatment.total_dose && (
                                  <div>
                                    <span className="text-gray-500">Total Dose:</span>
                                    <span className="ml-1 text-gray-900">{treatment.total_dose} Gy</span>
                                  </div>
                                )}
                              </>
                            )}
                            {treatment.oncologist && (
                              <div>
                                <span className="text-gray-500">Oncologist:</span>
                                <span className="ml-1 text-gray-900">{treatment.oncologist}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Pathology Tab */}
          {activeTab === 'tumours' && (
            <div className="bg-white rounded-lg border">
              <div className="px-4 sm:px-6 py-3 sm:py-4 border-b flex flex-col sm:flex-row gap-2 sm:gap-0 items-start sm:items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">
                  Pathology ({tumours.length})
                </h3>
                <button
                  onClick={() => {
                    setEditingTumour(null)
                    setShowTumourModal(true)
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                  + Add Tumour <span className="text-xs opacity-70 ml-1">(P)</span>
                </button>
              </div>

              {loading ? (
                <div className="p-8 text-center text-gray-500">Loading pathology...</div>
              ) : tumours.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <p className="mb-2">No pathology recorded yet</p>
                  <p className="text-sm">Add tumours to track primaries, metastases, or recurrences</p>
                </div>
              ) : (
                <div className="overflow-x-auto shadow-sm">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Tumour ID
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Type
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Site
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          ICD-10
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          TNM (Clinical)
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          TNM (Path)
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
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
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm font-medium text-gray-900 tabular-nums">
                            {tumour.tumour_id}
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm text-gray-900">
                            <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                              tumour.tumour_type === 'primary' ? 'bg-blue-100 text-blue-800' :
                              tumour.tumour_type === 'metastasis' ? 'bg-red-100 text-red-800' :
                              'bg-yellow-100 text-yellow-800'
                            }`}>
                              {capitalize(tumour.tumour_type)}
                            </span>
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm text-gray-900">
                            {formatAnatomicalSite(tumour.site)}
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm text-gray-900 tabular-nums">
                            {tumour.icd10_code || '—'}
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm text-gray-900 tabular-nums">
                            {tumour.clinical_t || tumour.clinical_n || tumour.clinical_m ? (
                              formatClinicalTNM(tumour.clinical_t, tumour.clinical_n, tumour.clinical_m)
                            ) : '—'}
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm text-gray-900 tabular-nums">
                            {tumour.pathological_t || tumour.pathological_n || tumour.pathological_m ? (
                              formatPathologicalTNM(tumour.pathological_t, tumour.pathological_n, tumour.pathological_m)
                            ) : '—'}
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm text-gray-500">
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
                                  handleDeleteTumourClick(tumour)
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
              <div className="px-4 sm:px-6 py-3 sm:py-4 border-b flex flex-col sm:flex-row gap-2 sm:gap-0 items-start sm:items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">
                  Treatments ({treatments.length})
                </h3>
                <button
                  onClick={() => setShowAddTreatment(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                  + Add Treatment <span className="text-xs opacity-70 ml-1">(R)</span>
                </button>
              </div>

              {loading ? (
                <div className="p-8 text-center text-gray-500">Loading treatments...</div>
              ) : treatments.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  No treatments recorded yet
                </div>
              ) : (
                <div className="overflow-x-auto shadow-sm">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Treatment ID
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Type
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Date
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Details
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Clinician
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
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
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm font-medium text-gray-900 tabular-nums">
                            {treatment.treatment_id}
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm text-gray-900">
                            <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getTreatmentTypeColor(treatment.treatment_type)}`}>
                              {formatTreatmentType(treatment.treatment_type)}
                            </span>
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm text-gray-900 tabular-nums">
                            {formatDate(treatment.treatment_date)}
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm text-gray-900 max-w-xs truncate">
                            {treatment.treatment_type === 'surgery' && treatment.procedure_name ? (
                              treatment.procedure_name
                            ) : treatment.treatment_type === 'chemotherapy' && treatment.regimen ? (
                              `${treatment.regimen} (Cycle ${treatment.cycle_number || '?'})`
                            ) : treatment.treatment_type === 'radiotherapy' && treatment.site ? (
                              `${formatAnatomicalSite(treatment.site)} - ${treatment.total_dose || '?'}Gy`
                            ) : (
                              treatment.notes || '—'
                            )}
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm text-gray-900">
                            {formatSurgeon((treatment.surgeon_name || treatment.anaesthetist_name || treatment.surgeon || treatment.oncologist) || 'Not specified')}
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm text-gray-500">
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
                                  handleDeleteTreatmentClick(treatment)
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

          {/* Investigations Tab */}
          {activeTab === 'investigations' && (
            <div className="bg-white rounded-lg border">
              <div className="px-4 sm:px-6 py-3 sm:py-4 border-b flex flex-col sm:flex-row gap-2 sm:gap-0 items-start sm:items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">
                  Investigations & Imaging ({investigations.length})
                </h3>
                <button
                  onClick={() => setShowInvestigationModal(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                  + Add Investigation <span className="text-xs opacity-70 ml-1">(I)</span>
                </button>
              </div>

              {loading ? (
                <div className="p-8 text-center text-gray-500">Loading investigations...</div>
              ) : investigations.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <p className="mb-2">No investigations recorded yet</p>
                  <p className="text-sm">Add imaging, endoscopy, or laboratory investigations</p>
                </div>
              ) : (
                <div className="overflow-x-auto shadow-sm">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Date
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Type
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Investigation
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Result
                        </th>
                        <th className="px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {investigations.map((inv) => (
                        <tr key={inv.investigation_id} className="hover:bg-blue-50 cursor-pointer transition-colors">
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm text-gray-900 tabular-nums">
                            {inv.date ? formatDate(inv.date) : '—'}
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm text-gray-900">
                            <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                              inv.type === 'imaging' ? 'bg-blue-100 text-blue-800' :
                              inv.type === 'endoscopy' ? 'bg-green-100 text-green-800' :
                              'bg-purple-100 text-purple-800'
                            }`}>
                              {capitalize(inv.type)}
                            </span>
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 text-sm text-gray-900">
                            {formatInvestigationType(inv.subtype)}
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 text-sm text-gray-900">
                            {inv.result || '—'}
                          </td>
                          <td className="px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm text-gray-500">
                            <div className="flex space-x-2">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setEditingInvestigation(inv)
                                  setShowInvestigationModal(true)
                                }}
                                className="text-blue-600 hover:text-blue-900"
                                title="Edit investigation"
                              >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleDeleteInvestigationClick(inv)
                                }}
                                className="text-red-600 hover:text-red-900"
                                title="Delete investigation"
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

          {/* Follow-ups Tab */}
          {activeTab === 'followups' && (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-semibold text-gray-900">
                  Follow-up Visits
                </h3>
                <Button 
                  onClick={() => setShowFollowUpModal(true)}
                  size="small"
                >
                  + Add Follow-up
                </Button>
              </div>

              {followUps.length === 0 ? (
                <div className="text-center py-12 bg-gray-50 rounded-lg">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <p className="mt-2 text-sm text-gray-500">No follow-up visits recorded</p>
                  <p className="text-xs text-gray-400">Track clinic appointments and surveillance visits</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {followUps.map((fu) => (
                    <div key={fu.followup_id} className="border rounded-lg p-4 hover:bg-gray-50">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-gray-900">
                              {fu.date ? formatDate(fu.date) : 'Date not recorded'}
                            </span>
                            <span className="px-2 py-1 text-xs font-semibold rounded-full bg-purple-100 text-purple-800">
                              {fu.type.split('_').map((w: string) => capitalize(w)).join(' ')}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600">
                            Seen by: {fu.clinician}
                          </p>
                        </div>
                        <button
                          onClick={() => {
                            setEditingFollowUp(fu)
                            setShowFollowUpModal(true)
                          }}
                          className="text-blue-600 hover:text-blue-900"
                          title="Edit follow-up"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                      </div>

                      {fu.outcome && (
                        <div className="mb-2">
                          <span className="text-sm font-medium text-gray-700">Outcome: </span>
                          <span className="text-sm text-gray-900">
                            {fu.outcome.split('_').map((w: string) => capitalize(w)).join(' ')}
                          </span>
                        </div>
                      )}

                      {fu.clinical_status && (
                        <div className="mb-2">
                          <p className="text-sm text-gray-700">{fu.clinical_status}</p>
                        </div>
                      )}

                      <div className="grid grid-cols-3 gap-4 text-sm mt-3">
                        {fu.cea_level && (
                          <div>
                            <span className="text-gray-500">CEA:</span>
                            <span className="ml-1 font-medium">{fu.cea_level} ng/mL</span>
                          </div>
                        )}
                        {fu.weight_kg && (
                          <div>
                            <span className="text-gray-500">Weight:</span>
                            <span className="ml-1 font-medium">{fu.weight_kg} kg</span>
                          </div>
                        )}
                        {fu.performance_status && (
                          <div>
                            <span className="text-gray-500">ECOG:</span>
                            <span className="ml-1 font-medium">{fu.performance_status}</span>
                          </div>
                        )}
                      </div>

                      {fu.investigations_ordered && fu.investigations_ordered.length > 0 && (
                        <div className="mt-3 pt-3 border-t">
                          <p className="text-xs text-gray-500 mb-1">Investigations Ordered:</p>
                          <div className="flex flex-wrap gap-1">
                            {fu.investigations_ordered.map((inv: string, idx: number) => (
                              <span key={idx} className="px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded">
                                {inv}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {fu.next_appointment && (
                        <div className="mt-3 pt-3 border-t text-sm">
                          <span className="text-gray-500">Next appointment: </span>
                          <span className="font-medium">{formatDate(fu.next_appointment)}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 px-4 sm:px-6 py-3 sm:py-4 bg-gray-50 flex justify-between">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
          {onEdit && (
            <Button variant="primary" onClick={() => {
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

        {/* Investigation Modal */}
        {showInvestigationModal && (
          <InvestigationModal
            episodeId={episode.episode_id}
            patientId={episode.patient_id}
            onSubmit={editingInvestigation ? handleEditInvestigation : handleAddInvestigation}
            onCancel={() => {
              setShowInvestigationModal(false)
              setEditingInvestigation(null)
            }}
            mode={editingInvestigation ? 'edit' : 'create'}
            initialData={editingInvestigation}
          />
        )}

        {/* Follow-up Modal */}
        {showFollowUpModal && (
          <FollowUpModal
            episodeId={episode.episode_id}
            patientId={episode.patient_id}
            onSubmit={editingFollowUp ? handleEditFollowUp : handleAddFollowUp}
            onCancel={() => {
              setShowFollowUpModal(false)
              setEditingFollowUp(null)
            }}
            mode={editingFollowUp ? 'edit' : 'create'}
            initialData={editingFollowUp}
          />
        )}

        {/* Delete Tumour Confirmation Modal */}
        {deleteTumourConfirmation.show && deleteTumourConfirmation.tumour && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-[60]">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <div className="flex items-center mb-4">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <h3 className="ml-3 text-lg font-medium text-gray-900">Delete Tumour</h3>
              </div>
              
              <div className="mb-4">
                <p className="text-sm text-gray-500 mb-4">
                  You are about to delete the following tumour:
                </p>
                
                <div className="bg-gray-50 rounded-md p-4 mb-4">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-gray-500">Tumour ID:</div>
                    <div className="font-medium text-gray-900 tabular-nums">{deleteTumourConfirmation.tumour.tumour_id}</div>
                    
                    <div className="text-gray-500">Site:</div>
                    <div className="text-gray-900">{formatAnatomicalSite(deleteTumourConfirmation.tumour.site)}</div>
                    
                    {deleteTumourConfirmation.tumour.size && (
                      <>
                        <div className="text-gray-500">Size:</div>
                        <div className="text-gray-900">{deleteTumourConfirmation.tumour.size}mm</div>
                      </>
                    )}
                  </div>
                </div>

                <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
                  <p className="text-sm text-red-800 font-medium">
                    ⚠️ This action cannot be undone
                  </p>
                </div>

                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Type the tumour ID <span className="font-mono font-bold">{deleteTumourConfirmation.tumour.tumour_id}</span> to confirm:
                </label>
                <input
                  type="text"
                  value={deleteTumourConfirmText}
                  onChange={(e) => setDeleteTumourConfirmText(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="Enter tumour ID"
                  autoFocus
                />
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => {
                    setDeleteTumourConfirmation({ show: false, tumour: null })
                    setDeleteTumourConfirmText('')
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteTumourConfirm}
                  disabled={deleteTumourConfirmText !== deleteTumourConfirmation.tumour.tumour_id}
                  className={`px-4 py-2 text-sm font-medium text-white rounded-md ${
                    deleteTumourConfirmText === deleteTumourConfirmation.tumour.tumour_id
                      ? 'bg-red-600 hover:bg-red-700'
                      : 'bg-red-300 cursor-not-allowed'
                  }`}
                >
                  Delete Tumour
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Delete Treatment Confirmation Modal */}
        {deleteTreatmentConfirmation.show && deleteTreatmentConfirmation.treatment && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-[60]">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <div className="flex items-center mb-4">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <h3 className="ml-3 text-lg font-medium text-gray-900">Delete Treatment</h3>
              </div>
              
              <div className="mb-4">
                <p className="text-sm text-gray-500 mb-4">
                  You are about to delete the following treatment:
                </p>
                
                <div className="bg-gray-50 rounded-md p-4 mb-4">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-gray-500">Treatment ID:</div>
                    <div className="font-medium text-gray-900 tabular-nums">{deleteTreatmentConfirmation.treatment.treatment_id}</div>
                    
                    <div className="text-gray-500">Type:</div>
                    <div className="text-gray-900">{formatTreatmentType(deleteTreatmentConfirmation.treatment.treatment_type)}</div>
                    
                    {deleteTreatmentConfirmation.treatment.treatment_date && (
                      <>
                        <div className="text-gray-500">Date:</div>
                        <div className="text-gray-900 tabular-nums">{formatDate(deleteTreatmentConfirmation.treatment.treatment_date)}</div>
                      </>
                    )}
                  </div>
                </div>

                <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
                  <p className="text-sm text-red-800 font-medium">
                    ⚠️ This action cannot be undone
                  </p>
                </div>

                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Type the treatment ID <span className="font-mono font-bold">{deleteTreatmentConfirmation.treatment.treatment_id}</span> to confirm:
                </label>
                <input
                  type="text"
                  value={deleteTreatmentConfirmText}
                  onChange={(e) => setDeleteTreatmentConfirmText(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="Enter treatment ID"
                  autoFocus
                />
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => {
                    setDeleteTreatmentConfirmation({ show: false, treatment: null })
                    setDeleteTreatmentConfirmText('')
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteTreatmentConfirm}
                  disabled={deleteTreatmentConfirmText !== deleteTreatmentConfirmation.treatment.treatment_id}
                  className={`px-4 py-2 text-sm font-medium text-white rounded-md ${
                    deleteTreatmentConfirmText === deleteTreatmentConfirmation.treatment.treatment_id
                      ? 'bg-red-600 hover:bg-red-700'
                      : 'bg-red-300 cursor-not-allowed'
                  }`}
                >
                  Delete Treatment
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Delete Investigation Confirmation Modal */}
        {deleteInvestigationConfirmation.show && deleteInvestigationConfirmation.investigation && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-[60]">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <div className="flex items-center mb-4">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <h3 className="ml-3 text-lg font-medium text-gray-900">Delete Investigation</h3>
              </div>
              
              <div className="mb-4">
                <p className="text-sm text-gray-500 mb-4">
                  You are about to delete the following investigation:
                </p>
                
                <div className="bg-gray-50 rounded-md p-4 mb-4">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-gray-500">Investigation ID:</div>
                    <div className="font-medium text-gray-900">{deleteInvestigationConfirmation.investigation.investigation_id}</div>
                    
                    <div className="text-gray-500">Type:</div>
                    <div className="text-gray-900">{capitalize(deleteInvestigationConfirmation.investigation.type)}</div>
                    
                    <div className="text-gray-500">Investigation:</div>
                    <div className="text-gray-900">{formatInvestigationType(deleteInvestigationConfirmation.investigation.subtype)}</div>
                    
                    {deleteInvestigationConfirmation.investigation.date && (
                      <>
                        <div className="text-gray-500">Date:</div>
                        <div className="text-gray-900">{formatDate(deleteInvestigationConfirmation.investigation.date)}</div>
                      </>
                    )}
                  </div>
                </div>

                <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
                  <p className="text-sm text-red-800 font-medium">
                    ⚠️ This action cannot be undone
                  </p>
                </div>

                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Type the investigation ID <span className="font-mono font-bold">{deleteInvestigationConfirmation.investigation.investigation_id}</span> to confirm:
                </label>
                <input
                  type="text"
                  value={deleteInvestigationConfirmText}
                  onChange={(e) => setDeleteInvestigationConfirmText(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="Enter investigation ID"
                  autoFocus
                />
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => {
                    setDeleteInvestigationConfirmation({ show: false, investigation: null })
                    setDeleteInvestigationConfirmText('')
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteInvestigationConfirm}
                  disabled={deleteInvestigationConfirmText !== deleteInvestigationConfirmation.investigation.investigation_id}
                  className={`px-4 py-2 text-sm font-medium text-white rounded-md ${
                    deleteInvestigationConfirmText === deleteInvestigationConfirmation.investigation.investigation_id
                      ? 'bg-red-600 hover:bg-red-700'
                      : 'bg-red-300 cursor-not-allowed'
                  }`}
                >
                  Delete Investigation
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>,
    modalRoot
  )
}
