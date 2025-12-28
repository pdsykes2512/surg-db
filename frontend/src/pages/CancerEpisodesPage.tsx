import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/common/PageHeader'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Table, TableHeader, TableBody, TableRow, TableHeadCell, TableCell } from '../components/common/Table'
import { CancerEpisodeForm } from '../components/forms/CancerEpisodeForm'
import { CancerEpisodeDetailModal } from '../components/modals/CancerEpisodeDetailModal'
import { formatDate, formatCancerType } from '../utils/formatters'
import api from '../services/api'

interface Episode {
  episode_id: string
  patient_id: string
  condition_type: string
  cancer_type: string
  referral_date: string
  first_seen_date: string
  lead_clinician: string
  episode_status: string
  cancer_data: any
}

export function CancerEpisodesPage() {
  // @ts-ignore - Unused but kept for potential future use
  const _navigate = useNavigate()
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [selectedEpisode, setSelectedEpisode] = useState<Episode | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [cancerTypeFilter, setCancerTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Delete confirmation state
  const [deleteConfirmation, setDeleteConfirmation] = useState<{ show: boolean; episode: Episode | null }>({ show: false, episode: null })
  const [deleteConfirmText, setDeleteConfirmText] = useState('')

  const loadEpisodes = useCallback(async () => {
    try {
      setLoading(true)
      const response = await api.get('/episodes/')
      setEpisodes(response.data)
      setError('')
    } catch (err: any) {
      console.error('Failed to load episodes:', err)
      setError('Failed to load episodes')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadEpisodes()
  }, [loadEpisodes])

  const filteredEpisodes = useMemo(() => {
    return episodes.filter(episode => {
      const matchesSearch = !searchTerm || 
        episode.episode_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        episode.patient_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        episode.lead_clinician?.toLowerCase().includes(searchTerm.toLowerCase())
      
      const matchesCancerType = !cancerTypeFilter || episode.cancer_type === cancerTypeFilter
      const matchesStatus = !statusFilter || episode.episode_status === statusFilter

      return matchesSearch && matchesCancerType && matchesStatus
    })
  }, [episodes, searchTerm, cancerTypeFilter, statusFilter])

  const handleCreate = async (data: any) => {
    try {
      await api.post('/episodes/', data)
      setShowForm(false)
      setSelectedEpisode(null)
      setEditMode(false)
      loadEpisodes()
      setSuccess('Episode created successfully')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      console.error('Failed to create episode:', err)
      setError(err.response?.data?.detail || 'Failed to create episode')
      setTimeout(() => setError(''), 5000)
    }
  }

  const handleEdit = async (data: any) => {
    if (!selectedEpisode) return
    
    try {
      await api.put(`/episodes/${selectedEpisode.episode_id}`, data)
      setShowForm(false)
      setSelectedEpisode(null)
      setEditMode(false)
      loadEpisodes()
      setSuccess('Episode updated successfully')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      console.error('Failed to update episode:', err)
      setError(err.response?.data?.detail || 'Failed to update episode')
      setTimeout(() => setError(''), 5000)
    }
  }

  const handleDeleteClick = (episode: Episode) => {
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
      setSuccess('Episode deleted successfully')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      console.error('Failed to delete episode:', err)
      setError(err.response?.data?.detail || 'Failed to delete episode')
      setTimeout(() => setError(''), 5000)
    }
  }

  const handleViewDetails = (episode: Episode) => {
    setSelectedEpisode(episode)
    setShowDetailModal(true)
  }

  const handleEditClick = (episode: Episode) => {
    setSelectedEpisode(episode)
    setEditMode(true)
    setShowForm(true)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800'
      case 'completed': return 'bg-blue-100 text-blue-800'
      case 'cancelled': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Cancer Episodes"
        subtitle="Manage cancer care episodes and treatments"
        icon={
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
        }
        action={
          !showForm && (
            <Button 
              variant="primary" 
              className="w-full sm:w-auto"
              onClick={() => {
                setSelectedEpisode(null)
                setEditMode(false)
                setShowForm(true)
              }}
            >
              + Add Episode
            </Button>
          )
        }
      />

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
          {success}
        </div>
      )}

      {showForm ? (
        <Card>
          <CancerEpisodeForm
            mode={editMode ? 'edit' : 'create'}
            initialData={selectedEpisode}
            onSubmit={editMode ? handleEdit : handleCreate}
            onCancel={() => {
              setShowForm(false)
              setSelectedEpisode(null)
              setEditMode(false)
            }}
          />
        </Card>
      ) : (
        <>
          {/* Filters */}
          <Card>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
                <input
                  type="text"
                  placeholder="Episode ID, Patient ID, Clinician..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Cancer Type</label>
                <select
                  value={cancerTypeFilter}
                  onChange={(e) => setCancerTypeFilter(e.target.value)}
                  className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Types</option>
                  <option value="bowel">Bowel (Colorectal)</option>
                  <option value="kidney">Kidney (Renal)</option>
                  <option value="breast_primary">Breast (Primary)</option>
                  <option value="breast_metastatic">Breast (Metastatic)</option>
                  <option value="oesophageal">Oesophageal</option>
                  <option value="ovarian">Ovarian</option>
                  <option value="prostate">Prostate</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Statuses</option>
                  <option value="active">Active</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
              <div className="flex items-end">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setSearchTerm('')
                    setCancerTypeFilter('')
                    setStatusFilter('')
                  }}
                  className="w-full"
                >
                  Clear Filters
                </Button>
              </div>
            </div>
          </Card>

          {/* Episodes Table */}
          <Card>
            {loading ? (
              <div className="text-center py-12 text-gray-500">Loading episodes...</div>
            ) : filteredEpisodes.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                No episodes found. {searchTerm || cancerTypeFilter || statusFilter ? 'Try adjusting your filters.' : 'Click "+ Add Episode" to create one.'}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHeadCell>Episode ID</TableHeadCell>
                    <TableHeadCell>Patient</TableHeadCell>
                    <TableHeadCell>Cancer Type</TableHeadCell>
                    <TableHeadCell>Referral Date</TableHeadCell>
                    <TableHeadCell>Lead Clinician</TableHeadCell>
                    <TableHeadCell>Status</TableHeadCell>
                    <TableHeadCell className="text-right">Actions</TableHeadCell>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredEpisodes.map((episode) => (
                    <TableRow key={episode.episode_id} onClick={() => handleViewDetails(episode)}>
                      <TableCell className="font-medium text-gray-900">
                        {episode.episode_id}
                      </TableCell>
                      <TableCell className="text-gray-900">
                        {episode.patient_id}
                      </TableCell>
                      <TableCell className="text-gray-900">
                        {formatCancerType(episode.cancer_type)}
                      </TableCell>
                      <TableCell className="text-gray-900">
                        {formatDate(episode.referral_date)}
                      </TableCell>
                      <TableCell className="text-gray-900">
                        {episode.lead_clinician || '—'}
                      </TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(episode.episode_status)}`}>
                          {episode.episode_status}
                        </span>
                      </TableCell>
                      <TableCell className="text-right space-x-2">
                          <Button
                            size="small"
                            variant="secondary"
                            onClick={() => handleViewDetails(episode)}
                          >
                            View
                          </Button>
                          <Button
                            size="small"
                            variant="secondary"
                            onClick={() => handleEditClick(episode)}
                          >
                            Edit
                          </Button>
                          <Button
                            size="small"
                            variant="danger"
                            onClick={() => handleDeleteClick(episode)}
                          >
                            Delete
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
          </Card>
        </>
      )}

      {/* Detail Modal */}
      {showDetailModal && selectedEpisode && (
        <CancerEpisodeDetailModal
          episode={selectedEpisode}
          onClose={() => {
            setShowDetailModal(false)
            setSelectedEpisode(null)
          }}
          onEdit={() => {
            setShowDetailModal(false)
            handleEditClick(selectedEpisode)
          }}
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
  )
}
