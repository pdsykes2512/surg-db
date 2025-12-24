import { useState } from 'react'
import { Button } from './Button'
import { DateInput } from './DateInput'
import { SurgeonSearch } from './SurgeonSearch'

interface FollowUpModalProps {
  episodeId: string
  patientId: string
  onSubmit: (followUp: any) => void
  onCancel: () => void
  mode?: 'create' | 'edit'
  initialData?: any
}

const generateFollowUpId = (patientId: string, count: number) => {
  const cleanPatientId = patientId.replace(/[^a-zA-Z0-9]/g, '')
  const incrementalNum = String(count + 1).padStart(2, '0')
  return `FU-${cleanPatientId}-${incrementalNum}`
}

const FOLLOW_UP_TYPES = [
  { value: 'clinic', label: 'Clinic Appointment' },
  { value: 'telephone', label: 'Telephone Consultation' },
  { value: 'video', label: 'Video Consultation' },
  { value: 'surveillance', label: 'Surveillance Visit' },
  { value: 'review', label: 'Treatment Review' }
]

const OUTCOME_OPTIONS = [
  { value: 'satisfactory', label: 'Satisfactory Progress' },
  { value: 'stable', label: 'Stable Disease' },
  { value: 'improved', label: 'Improved' },
  { value: 'deteriorated', label: 'Deteriorated' },
  { value: 'recurrence', label: 'Recurrence Detected' },
  { value: 'complications', label: 'Complications' },
  { value: 'further_investigation', label: 'Further Investigation Required' },
  { value: 'discharge', label: 'Discharged from Service' }
]

export function FollowUpModal({ episodeId, patientId, onSubmit, onCancel, mode = 'create', initialData }: FollowUpModalProps) {
  const [formData, setFormData] = useState({
    followup_id: initialData?.followup_id || '',
    type: initialData?.type || 'clinic',
    date: initialData?.date || '',
    clinician: initialData?.clinician || '',
    outcome: initialData?.outcome || '',
    clinical_status: initialData?.clinical_status || '',
    cea_level: initialData?.cea_level || '',
    weight_kg: initialData?.weight_kg || '',
    performance_status: initialData?.performance_status || '',
    complications: initialData?.complications || '',
    next_appointment: initialData?.next_appointment || '',
    investigations_ordered: initialData?.investigations_ordered || [],
    treatment_changes: initialData?.treatment_changes || '',
    notes: initialData?.notes || ''
  })

  const [investigationInput, setInvestigationInput] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    const followUp = {
      ...formData,
      followup_id: mode === 'create' 
        ? generateFollowUpId(patientId, 0) // TODO: Get proper count
        : formData.followup_id,
      patient_id: patientId,
      episode_id: episodeId,
      cea_level: formData.cea_level ? parseFloat(formData.cea_level) : null,
      weight_kg: formData.weight_kg ? parseFloat(formData.weight_kg) : null
    }
    
    onSubmit(followUp)
  }

  const addInvestigation = () => {
    if (investigationInput.trim()) {
      setFormData({
        ...formData,
        investigations_ordered: [...formData.investigations_ordered, investigationInput.trim()]
      })
      setInvestigationInput('')
    }
  }

  const removeInvestigation = (index: number) => {
    setFormData({
      ...formData,
      investigations_ordered: formData.investigations_ordered.filter((_, i) => i !== index)
    })
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-900">
            {mode === 'create' ? 'Add Follow-up Visit' : 'Edit Follow-up Visit'}
          </h2>
          <button onClick={onCancel} className="text-gray-400 hover:text-gray-500">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Follow-up Type */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Follow-up Type *
              </label>
              <select
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                required
              >
                {FOLLOW_UP_TYPES.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Date *
              </label>
              <DateInput
                value={formData.date}
                onChange={(value) => setFormData({ ...formData, date: value })}
                required
              />
            </div>
          </div>

          {/* Clinician */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Clinician Seen *
            </label>
            <SurgeonSearch
              value={formData.clinician}
              onChange={(value) => setFormData({ ...formData, clinician: value })}
              placeholder="Search for clinician..."
              required
            />
          </div>

          {/* Outcome */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Visit Outcome *
            </label>
            <select
              value={formData.outcome}
              onChange={(e) => setFormData({ ...formData, outcome: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">Select outcome...</option>
              {OUTCOME_OPTIONS.map(outcome => (
                <option key={outcome.value} value={outcome.value}>{outcome.label}</option>
              ))}
            </select>
          </div>

          {/* Clinical Status */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Clinical Status
            </label>
            <textarea
              value={formData.clinical_status}
              onChange={(e) => setFormData({ ...formData, clinical_status: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Overall clinical status, symptoms, functional status"
            />
          </div>

          {/* Clinical Measurements */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                CEA Level (ng/mL)
              </label>
              <input
                type="number"
                step="0.1"
                value={formData.cea_level}
                onChange={(e) => setFormData({ ...formData, cea_level: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Weight (kg)
              </label>
              <input
                type="number"
                step="0.1"
                value={formData.weight_kg}
                onChange={(e) => setFormData({ ...formData, weight_kg: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                ECOG Performance Status
              </label>
              <select
                value={formData.performance_status}
                onChange={(e) => setFormData({ ...formData, performance_status: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select...</option>
                <option value="0">0 - Fully active</option>
                <option value="1">1 - Restricted activity</option>
                <option value="2">2 - Ambulatory, self-care</option>
                <option value="3">3 - Limited self-care</option>
                <option value="4">4 - Completely disabled</option>
                <option value="5">5 - Dead</option>
              </select>
            </div>
          </div>

          {/* Complications */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Complications or Issues
            </label>
            <textarea
              value={formData.complications}
              onChange={(e) => setFormData({ ...formData, complications: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Any complications, side effects, or concerns"
            />
          </div>

          {/* Investigations Ordered */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Investigations Ordered
            </label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={investigationInput}
                onChange={(e) => setInvestigationInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addInvestigation())}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., CT TAP, CEA blood test"
              />
              <Button type="button" onClick={addInvestigation} variant="outline">
                Add
              </Button>
            </div>
            {formData.investigations_ordered.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {formData.investigations_ordered.map((inv, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                  >
                    {inv}
                    <button
                      type="button"
                      onClick={() => removeInvestigation(index)}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Treatment Changes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Treatment Changes
            </label>
            <textarea
              value={formData.treatment_changes}
              onChange={(e) => setFormData({ ...formData, treatment_changes: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Any changes to treatment plan, medications, etc."
            />
          </div>

          {/* Next Appointment */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Next Appointment Date
            </label>
            <DateInput
              value={formData.next_appointment}
              onChange={(value) => setFormData({ ...formData, next_appointment: value })}
            />
          </div>

          {/* Additional Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Additional Notes
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Any other relevant information"
            />
          </div>
        </form>

        <div className="flex justify-end gap-3 p-6 border-t bg-gray-50">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={handleSubmit}>
            {mode === 'create' ? 'Add Follow-up' : 'Save Changes'}
          </Button>
        </div>
      </div>
    </div>
  )
}
