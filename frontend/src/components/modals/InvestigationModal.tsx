import { useState, useEffect } from 'react'
import { Button } from '../common/Button'
import { DateInput } from '../common/DateInput'

interface InvestigationModalProps {
  episodeId: string
  patientId: string
  onSubmit: (investigation: any) => void
  onCancel: () => void
  mode?: 'create' | 'edit'
  initialData?: any
  existingInvestigations?: any[]
}

const generateInvestigationId = (patientId: string, type: string, count: number) => {
  const cleanPatientId = patientId.replace(/[^a-zA-Z0-9]/g, '')
  const typePrefix = type === 'imaging' ? 'IMG' : type === 'endoscopy' ? 'END' : 'LAB'
  const incrementalNum = String(count + 1).padStart(2, '0')
  return `${typePrefix}-${cleanPatientId}-${incrementalNum}`
}

const INVESTIGATION_TYPES = [
  { value: 'imaging', label: 'Imaging' },
  { value: 'endoscopy', label: 'Endoscopy' },
  { value: 'laboratory', label: 'Laboratory' }
]

const IMAGING_SUBTYPES = [
  { value: 'ct_chest', label: 'CT Chest' },
  { value: 'ct_abdomen', label: 'CT Abdomen/Pelvis' },
  { value: 'ct_tap', label: 'CT Thorax/Abdomen/Pelvis' },
  { value: 'ct_colonography', label: 'CT Colonography' },
  { value: 'mri_pelvis_rectum', label: 'MRI Pelvis/Rectum' },
  { value: 'mri_primary', label: 'MRI Primary Tumour' },
  { value: 'mri_liver', label: 'MRI Liver' },
  { value: 'mri_brain', label: 'MRI Brain' },
  { value: 'pet_ct', label: 'PET-CT' },
  { value: 'ultrasound', label: 'Ultrasound' },
  { value: 'xray_chest', label: 'X-ray Chest' },
  { value: 'bone_scan', label: 'Bone Scan' }
]

const ENDOSCOPY_SUBTYPES = [
  { value: 'colonoscopy', label: 'Colonoscopy' },
  { value: 'sigmoidoscopy', label: 'Flexible Sigmoidoscopy' },
  { value: 'gastroscopy', label: 'Gastroscopy (OGD)' },
  { value: 'ercp', label: 'ERCP' },
  { value: 'eus', label: 'Endoscopic Ultrasound (EUS)' },
  { value: 'bronchoscopy', label: 'Bronchoscopy' },
  { value: 'cystoscopy', label: 'Cystoscopy' }
]

const LABORATORY_SUBTYPES = [
  { value: 'cea', label: 'CEA (Carcinoembryonic Antigen)' },
  { value: 'ca19_9', label: 'CA 19-9' },
  { value: 'ca125', label: 'CA 125' },
  { value: 'psa', label: 'PSA' },
  { value: 'fbc', label: 'Full Blood Count' },
  { value: 'lft', label: 'Liver Function Tests' },
  { value: 'u_e', label: 'U&Es' },
  { value: 'tumour_markers', label: 'Tumour Markers Panel' },
  { value: 'genetic_testing', label: 'Genetic Testing' },
  { value: 'histopathology', label: 'Histopathology' }
]

export function InvestigationModal({ episodeId, patientId, onSubmit, onCancel, mode = 'create', initialData, existingInvestigations = [] }: InvestigationModalProps) {
  const [formData, setFormData] = useState({
    investigation_id: '',
    type: 'imaging',
    subtype: '',
    date: '',
    result: '',
    findings: {},
    notes: '',
    report_url: ''
  })

  // Update form data when initialData changes (for edit mode)
  useEffect(() => {
    if (mode === 'edit' && initialData) {
      console.log('Loading investigation data:', initialData)
      setFormData({
        investigation_id: initialData.investigation_id || '',
        type: initialData.type || 'imaging',
        subtype: initialData.subtype || '',
        date: initialData.date || '',
        result: initialData.result || '',
        findings: initialData.findings || {},
        notes: initialData.notes || '',
        report_url: initialData.report_url || ''
      })
    } else if (mode === 'create') {
      // Reset to default values for create mode
      setFormData({
        investigation_id: '',
        type: 'imaging',
        subtype: '',
        date: '',
        result: '',
        findings: {},
        notes: '',
        report_url: ''
      })
    }
  }, [mode, initialData])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Calculate count for new investigation ID
    const sameTypeCount = mode === 'create' 
      ? existingInvestigations.filter(inv => inv.type === formData.type).length
      : 0
    
    const investigation = {
      ...formData,
      investigation_id: mode === 'create' 
        ? generateInvestigationId(patientId, formData.type, sameTypeCount)
        : formData.investigation_id,
      patient_id: patientId,
      episode_id: episodeId
    }
    
    onSubmit(investigation)
  }

  const getSubtypeOptions = () => {
    switch (formData.type) {
      case 'imaging':
        return IMAGING_SUBTYPES
      case 'endoscopy':
        return ENDOSCOPY_SUBTYPES
      case 'laboratory':
        return LABORATORY_SUBTYPES
      default:
        return []
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" style={{ margin: 0 }}>
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-900">
            {mode === 'create' ? 'Add Investigation' : 'Edit Investigation'}
          </h2>
          <button onClick={onCancel} className="text-gray-400 hover:text-gray-500">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Investigation Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Investigation Type *
            </label>
            <select
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value, subtype: '' })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            >
              {INVESTIGATION_TYPES.map(type => (
                <option key={type.value} value={type.value}>{type.label}</option>
              ))}
            </select>
          </div>

          {/* Investigation Subtype */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Specific Investigation *
            </label>
            <select
              value={formData.subtype}
              onChange={(e) => setFormData({ ...formData, subtype: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">Select...</option>
              {getSubtypeOptions().map(subtype => (
                <option key={subtype.value} value={subtype.value}>{subtype.label}</option>
              ))}
            </select>
          </div>

          {/* Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Investigation Date *
            </label>
            <DateInput
              value={formData.date}
              onChange={(e) => setFormData({ ...formData, date: e.target.value })}
              required
            />
          </div>

          {/* Result */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Primary Result/Finding
            </label>
            <input
              type="text"
              value={formData.result}
              onChange={(e) => setFormData({ ...formData, result: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., T3N1 disease, No evidence of metastases"
            />
          </div>

          {/* Report URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Report Link (Optional)
            </label>
            <input
              type="url"
              value={formData.report_url}
              onChange={(e) => setFormData({ ...formData, report_url: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="https://..."
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Additional Notes
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Detailed findings, recommendations, etc."
            />
          </div>
        </form>

        <div className="flex justify-between items-center p-6 border-t bg-gray-50">
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSubmit}>
            {mode === 'create' ? 'Add Investigation' : 'Save Changes'}
          </Button>
        </div>
      </div>
    </div>
  )
}
