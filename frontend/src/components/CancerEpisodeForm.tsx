import { useState } from 'react'
import { Button } from './Button'
import { DateInput } from './DateInput'
import { PatientSearch } from './PatientSearch'
import { SurgeonSearch } from './SurgeonSearch'
import { SearchableSelect } from './SearchableSelect'
import { TumourModal } from './TumourModal'
import { AddTreatmentModal } from './AddTreatmentModal'
import { formatSurgeon, formatCancerType } from '../utils/formatters'
import { NHS_TRUST_OPTIONS } from '../utils/nhsTrusts'

interface CancerEpisodeFormProps {
  onSubmit: (data: any) => void
  onCancel: () => void
  initialData?: any
  mode?: 'create' | 'edit'
}

// Generate unique episode ID based on NHS Number and count
const generateEpisodeId = (nhsNumber: string, count: number) => {
  if (!nhsNumber) return ''
  const cleanNHS = nhsNumber.replace(/\s/g, '')
  const incrementalNum = (count + 1).toString().padStart(2, '0')
  return `EPI-${cleanNHS}-${incrementalNum}`
}

// NHS Trust ODS Codes - NBOCA requirement (CR1410, CR1450)
// NHS Trust options imported from centralized utils

export function CancerEpisodeForm({ onSubmit, onCancel, initialData, mode = 'create' }: CancerEpisodeFormProps) {
  const [step, setStep] = useState(1)
  const [addTumourNow, setAddTumourNow] = useState(false)
  const [addTreatmentNow, setAddTreatmentNow] = useState(false)
  const [showTumourModal, setShowTumourModal] = useState(false)
  const [showTreatmentModal, setShowTreatmentModal] = useState(false)

  const [formData, setFormData] = useState(() => {
    if (initialData) {
      // Format dates for date inputs (YYYY-MM-DD)
      const formatDateForInput = (dateStr: string | null | undefined) => {
        if (!dateStr) return ''
        return dateStr.split('T')[0] // Extract YYYY-MM-DD from ISO datetime
      }
      
      return {
        ...initialData,
        referral_date: formatDateForInput(initialData.referral_date),
        first_seen_date: formatDateForInput(initialData.first_seen_date),
        mdt_discussion_date: formatDateForInput(initialData.mdt_discussion_date),
      }
    }
    
    return {
      episode_id: '',
      patient_id: '',
      condition_type: 'cancer',
      cancer_type: '',
      referral_date: new Date().toISOString().split('T')[0],
      referral_source: '',
      provider_first_seen: '',
      cns_involved: '',
      first_seen_date: '',
      mdt_discussion_date: '',
      mdt_meeting_type: '',
      performance_status: '',
      no_treatment_reason: '',
      lead_clinician: '',
      mdt_team: [],
      episode_status: 'active',
      created_by: 'current_user',
      last_modified_by: 'current_user',
      cancer_data: null,
      treatments: [],
      tumours: []
    }
  })

  const updateFormData = (field: string, value: any) => {
    setFormData((prev: any) => ({ ...prev, [field]: value }))
  }

  // Map cancer type to subspecialty for filtering clinicians
  const getSubspecialtyForCancerType = (cancerType: string): string | undefined => {
    const mapping: { [key: string]: string } = {
      'bowel': 'colorectal',
      'kidney': 'urology',
      'prostate': 'urology',
      'breast_primary': 'breast',
      'breast_metastatic': 'breast',
      'oesophageal': 'upper_gi',
      'ovarian': 'gynae_onc'
    }
    return mapping[cancerType]
  }

  const updateCancerData = (field: string, value: any) => {
    setFormData((prev: any) => ({
      ...prev,
      cancer_data: { ...(prev.cancer_data || {}), [field]: value }
    }))
  }

  const handleTumourSubmit = (tumour: any) => {
    // Add the tumour to the formData
    setFormData((prev: any) => ({
      ...prev,
      tumours: [...(prev.tumours || []), tumour]
    }))
    setShowTumourModal(false)
    // After adding tumour, check if they want to add treatment
    if (addTreatmentNow) {
      setShowTreatmentModal(true)
    } else {
      setStep(3)
    }
  }

  const handleTreatmentSubmit = (treatment: any) => {
    // Add the treatment to the formData
    setFormData((prev: any) => ({
      ...prev,
      treatments: [...(prev.treatments || []), treatment]
    }))
    setShowTreatmentModal(false)
    // Proceed to review step
    setStep(3)
  }

  const handleSubmit = () => {
    // Validate required fields
    const missingFields = []
    
    if (!formData.patient_id) missingFields.push('Patient')
    if (!formData.cancer_type) missingFields.push('Cancer Type')
    if (!formData.lead_clinician) missingFields.push('Lead Clinician')
    
    if (missingFields.length > 0) {
      alert(`Please fill in the following required fields:\n- ${missingFields.join('\n- ')}`)
      return
    }

    // Clean up the data before sending - remove empty strings for optional dates
    const cleanedData = {
      ...formData,
      first_seen_date: formData.first_seen_date || null,
      mdt_discussion_date: formData.mdt_discussion_date || null
    }

    onSubmit(cleanedData)
  }

  const renderStep1 = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900">Patient & Episode Information</h3>

      {/* Patient Selection */}
      <PatientSearch
        value={formData.patient_id}
        onChange={async (mrn, patientData) => {
          updateFormData('patient_id', mrn)
          
          // Generate episode ID when patient is selected
          if (patientData?.nhs_number && mode === 'create') {
            try {
              // Fetch existing episodes for this patient to get count
              const response = await fetch(`http://localhost:8000/api/episodes/?patient_id=${mrn}`, {
                headers: {
                  'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
              })
              const episodes = await response.json()
              const episodeCount = Array.isArray(episodes) ? episodes.length : 0
              
              const newEpisodeId = generateEpisodeId(patientData.nhs_number, episodeCount)
              updateFormData('episode_id', newEpisodeId)
            } catch (error) {
              console.error('Failed to generate episode ID:', error)
            }
          }
        }}
        label="Patient"
        required
      />

      {/* Cancer Type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Cancer Type <span className="text-red-500">*</span>
        </label>
        <SearchableSelect
          value={formData.cancer_type}
          onChange={(value) => updateFormData('cancer_type', value)}
          options={[
            { value: 'bowel', label: 'Bowel (Colorectal)' },
            { value: 'kidney', label: 'Kidney (Renal)' },
            { value: 'breast_primary', label: 'Breast (Primary)' },
            { value: 'breast_metastatic', label: 'Breast (Metastatic)' },
            { value: 'oesophageal', label: 'Oesophageal' },
            { value: 'ovarian', label: 'Ovarian' },
            { value: 'prostate', label: 'Prostate' }
          ]}
          getOptionValue={(opt) => opt.value}
          getOptionLabel={(opt) => opt.label}
          placeholder="Search cancer type..."
          required
        />
      </div>

      {/* NBOCA Phase 4: Process Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Referral Source - CR1600 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Referral Source
          </label>
          <SearchableSelect
            value={formData.referral_source}
            onChange={(value) => updateFormData('referral_source', value)}
            options={[
              { value: '', label: 'Not recorded' },
              { value: 'gp', label: 'GP Referral' },
              { value: '2ww', label: '2 Week Wait Referral' },
              { value: 'screening', label: 'Bowel Screening Programme' },
              { value: 'emergency', label: 'Emergency Presentation' },
              { value: 'consultant', label: 'Consultant Referral' },
              { value: 'private', label: 'Private Referral' },
              { value: 'other', label: 'Other' }
            ]}
            getOptionValue={(opt) => opt.value}
            getOptionLabel={(opt) => opt.label}
            placeholder="Select referral source..."
          />
          <p className="mt-1 text-xs text-gray-500">NBOCA (CR1600)</p>
        </div>

        {/* Provider First Seen - CR1410 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Provider First Seen
          </label>
          <SearchableSelect
            value={formData.provider_first_seen}
            onChange={(value) => updateFormData('provider_first_seen', value)}
            options={NHS_TRUST_OPTIONS}
            getOptionValue={(opt) => opt.value}
            getOptionLabel={(opt) => opt.label}
            placeholder="Search NHS Trust..."
          />
          <p className="mt-1 text-xs text-gray-500">NBOCA (CR1410) - NHS Trust where first seen</p>
        </div>

        {/* CNS Involved - CR2050 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Clinical Nurse Specialist (CNS)
          </label>
          <SearchableSelect
            value={formData.cns_involved}
            onChange={(value) => updateFormData('cns_involved', value)}
            options={[
              { value: '', label: 'Not recorded' },
              { value: 'yes', label: 'Yes - CNS Involved' },
              { value: 'no', label: 'No - No CNS Involvement' },
              { value: 'unknown', label: 'Unknown' }
            ]}
            getOptionValue={(opt) => opt.value}
            getOptionLabel={(opt) => opt.label}
            placeholder="Select CNS involvement..."
          />
          <p className="mt-1 text-xs text-gray-500">NBOCA (CR2050)</p>
        </div>
      </div>

      {/* Dates */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <DateInput
          label="Referral Date"
          required
          value={formData.referral_date}
          onChange={(e) => updateFormData('referral_date', e.target.value)}
        />
        <DateInput
          label="First Seen Date"
          value={formData.first_seen_date}
          onChange={(e) => updateFormData('first_seen_date', e.target.value)}
        />
        <DateInput
          label="MDT Discussion Date"
          value={formData.mdt_discussion_date}
          onChange={(e) => updateFormData('mdt_discussion_date', e.target.value)}
        />

        {/* MDT Meeting Type - NBOCA CR3190 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            MDT Meeting Type
          </label>
          <SearchableSelect
            value={formData.mdt_meeting_type}
            onChange={(value) => updateFormData('mdt_meeting_type', value)}
            options={[
              { value: 'colorectal', label: 'Colorectal MDT' },
              { value: 'upper_gi', label: 'Upper GI MDT' },
              { value: 'lower_gi', label: 'Lower GI MDT' },
              { value: 'combined', label: 'Combined MDT' },
              { value: 'cancer_centre', label: 'Cancer Centre MDT' },
              { value: 'other', label: 'Other' }
            ]}
            getOptionValue={(opt) => opt.value}
            getOptionLabel={(opt) => opt.label}
            placeholder="Select MDT type..."
          />
          <p className="mt-1 text-xs text-gray-500">NBOCA (CR3190)</p>
        </div>
      </div>

      {/* Performance Status (ECOG) - NBOCA CR0510 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Performance Status (ECOG)
        </label>
        <SearchableSelect
          value={formData.performance_status}
          onChange={(value) => updateFormData('performance_status', value)}
          options={[
            { value: '', label: 'Not assessed' },
            { value: '0', label: 'ECOG 0 - Fully active, no restrictions' },
            { value: '1', label: 'ECOG 1 - Strenuous activity restricted' },
            { value: '2', label: 'ECOG 2 - Ambulatory, capable of self-care' },
            { value: '3', label: 'ECOG 3 - Limited self-care, confined to bed/chair >50% of waking hours' },
            { value: '4', label: 'ECOG 4 - Completely disabled, confined to bed/chair' },
            { value: '5', label: 'ECOG 5 - Dead' }
          ]}
          getOptionValue={(opt) => opt.value}
          getOptionLabel={(opt) => opt.label}
          placeholder="Select ECOG score..."
        />
        <p className="mt-1 text-xs text-gray-500">NBOCA (CR0510) - Patient fitness assessment</p>
      </div>

      {/* No Treatment Reason - NBOCA CR0490 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          No Treatment Reason (if applicable)
        </label>
        <SearchableSelect
          value={formData.no_treatment_reason}
          onChange={(value) => updateFormData('no_treatment_reason', value)}
          options={[
            { value: '', label: 'Treatment planned/given' },
            { value: 'patient_choice', label: 'Patient choice/declined' },
            { value: 'not_fit', label: 'Not fit for treatment' },
            { value: 'comorbidities', label: 'Comorbidities contraindicate treatment' },
            { value: 'too_advanced', label: 'Disease too advanced' },
            { value: 'died_before', label: 'Died before treatment' },
            { value: 'palliative_only', label: 'Palliative care only' },
            { value: 'other', label: 'Other reason' }
          ]}
          getOptionValue={(opt) => opt.value}
          getOptionLabel={(opt) => opt.label}
          placeholder="Select reason if no treatment given..."
        />
        <p className="mt-1 text-xs text-gray-500">NBOCA (CR0490) - Required if cancer treatment not provided</p>
      </div>

      {/* Lead Clinician - filtered by subspecialty */}
      <SurgeonSearch
        value={formData.lead_clinician}
        onChange={(name) => updateFormData('lead_clinician', name)}
        label="Lead Clinician (Consultant)"
        required
        consultantsOnly
        subspecialtyFilter={getSubspecialtyForCancerType(formData.cancer_type)}
        placeholder="Search consultant surgeon..."
      />
      {getSubspecialtyForCancerType(formData.cancer_type) && (
        <p className="-mt-4 text-xs text-gray-500">
          Showing {getSubspecialtyForCancerType(formData.cancer_type)?.replace('_', ' ')} consultants only
        </p>
      )}
    </div>
  )

  const renderBreastCancerFields = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900">
        {formData.cancer_type === 'breast_metastatic' ? 'Metastatic Breast Cancer Details' : 'Primary Breast Cancer Details'}
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Laterality <span className="text-red-500">*</span>
          </label>
          <SearchableSelect
            value={formData.cancer_data.laterality || ''}
            onChange={(value) => updateCancerData('laterality', value)}
            options={[
              { value: 'left', label: 'Left' },
              { value: 'right', label: 'Right' },
              { value: 'bilateral', label: 'Bilateral' }
            ]}
            getOptionValue={(opt) => opt.value}
            getOptionLabel={(opt) => opt.label}
            placeholder="Search laterality..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Detection Method <span className="text-red-500">*</span>
          </label>
          <SearchableSelect
            value={formData.cancer_data.detection_method || ''}
            onChange={(value) => updateCancerData('detection_method', value)}
            options={[
              { value: 'screening', label: 'Screening' },
              { value: 'symptomatic', label: 'Symptomatic' },
              { value: 'self_detected', label: 'Self-detected' },
              { value: 'incidental', label: 'Incidental' }
            ]}
            getOptionValue={(opt) => opt.value}
            getOptionLabel={(opt) => opt.label}
            placeholder="Search detection method..."
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Histological Type <span className="text-red-500">*</span>
          </label>
          <SearchableSelect
            value={formData.cancer_data.histological_type || ''}
            onChange={(value) => updateCancerData('histological_type', value)}
            options={[
              { value: 'ductal', label: 'Ductal' },
              { value: 'lobular', label: 'Lobular' },
              { value: 'mixed', label: 'Mixed' },
              { value: 'other', label: 'Other' }
            ]}
            getOptionValue={(opt) => opt.value}
            getOptionLabel={(opt) => opt.label}
            placeholder="Search histological type..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Histological Grade
          </label>
          <SearchableSelect
            value={formData.cancer_data.histological_grade?.toString() || ''}
            onChange={(value) => updateCancerData('histological_grade', value ? parseInt(value) : null)}
            options={[
              { value: '1', label: 'Grade 1' },
              { value: '2', label: 'Grade 2' },
              { value: '3', label: 'Grade 3' }
            ]}
            getOptionValue={(opt) => opt.value}
            getOptionLabel={(opt) => opt.label}
            placeholder="Search grade..."
          />
        </div>
      </div>

      <div className="border-t pt-4">
        <h4 className="font-medium text-gray-900 mb-4">Receptor Status</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              ER Status
            </label>
            <SearchableSelect
              value={formData.cancer_data.er_status || ''}
              onChange={(value) => updateCancerData('er_status', value)}
              options={[
                { value: 'positive', label: 'Positive' },
                { value: 'negative', label: 'Negative' },
                { value: 'unknown', label: 'Unknown' }
              ]}
              getOptionValue={(opt) => opt.value}
              getOptionLabel={(opt) => opt.label}
              placeholder="Search ER status..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              PR Status
            </label>
            <SearchableSelect
              value={formData.cancer_data.pr_status || ''}
              onChange={(value) => updateCancerData('pr_status', value)}
              options={[
                { value: 'positive', label: 'Positive' },
                { value: 'negative', label: 'Negative' },
                { value: 'unknown', label: 'Unknown' }
              ]}
              getOptionValue={(opt) => opt.value}
              getOptionLabel={(opt) => opt.label}
              placeholder="Search PR status..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              HER2 Status
            </label>
            <SearchableSelect
              value={formData.cancer_data.her2_status || ''}
              onChange={(value) => updateCancerData('her2_status', value)}
              options={[
                { value: 'positive', label: 'Positive' },
                { value: 'negative', label: 'Negative' },
                { value: 'equivocal', label: 'Equivocal' },
                { value: 'unknown', label: 'Unknown' }
              ]}
              getOptionValue={(opt) => opt.value}
              getOptionLabel={(opt) => opt.label}
              placeholder="Search HER2 status..."
            />
          </div>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          MDT Treatment Plan
        </label>
        <textarea
          value={formData.cancer_data.mdt_treatment_plan || ''}
          onChange={(e) => updateCancerData('mdt_treatment_plan', e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          rows={4}
          placeholder="MDT discussion outcome and treatment plan..."
        />
      </div>
    </div>
  )

  const renderProstateCancerFields = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900">Prostate Cancer Details</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Detection Method <span className="text-red-500">*</span>
          </label>
          <select
            value={formData.cancer_data.detection_method || ''}
            onChange={(e) => updateCancerData('detection_method', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select...</option>
            <option value="psa_screening">PSA Screening</option>
            <option value="symptomatic">Symptomatic</option>
            <option value="incidental">Incidental</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            PSA at Diagnosis (ng/mL)
          </label>
          <input
            type="number"
            step="0.1"
            value={formData.cancer_data.psa_at_diagnosis || ''}
            onChange={(e) => updateCancerData('psa_at_diagnosis', e.target.value ? parseFloat(e.target.value) : null)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            min="0"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Gleason Primary
          </label>
          <input
            type="number"
            value={formData.cancer_data.gleason_primary || ''}
            onChange={(e) => updateCancerData('gleason_primary', e.target.value ? parseInt(e.target.value) : null)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            min="1"
            max="5"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Gleason Secondary
          </label>
          <input
            type="number"
            value={formData.cancer_data.gleason_secondary || ''}
            onChange={(e) => updateCancerData('gleason_secondary', e.target.value ? parseInt(e.target.value) : null)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            min="1"
            max="5"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            ISUP Grade Group
          </label>
          <select
            value={formData.cancer_data.isup_grade_group || ''}
            onChange={(e) => updateCancerData('isup_grade_group', e.target.value ? parseInt(e.target.value) : null)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select...</option>
            <option value="1">Grade Group 1</option>
            <option value="2">Grade Group 2</option>
            <option value="3">Grade Group 3</option>
            <option value="4">Grade Group 4</option>
            <option value="5">Grade Group 5</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            PI-RADS Score
          </label>
          <input
            type="number"
            value={formData.cancer_data.pirads_score || ''}
            onChange={(e) => updateCancerData('pirads_score', e.target.value ? parseInt(e.target.value) : null)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            min="1"
            max="5"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Risk Group
        </label>
        <select
          value={formData.cancer_data.risk_group || ''}
          onChange={(e) => updateCancerData('risk_group', e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Select...</option>
          <option value="low">Low Risk</option>
          <option value="intermediate">Intermediate Risk</option>
          <option value="high">High Risk</option>
          <option value="very_high">Very High Risk</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          MDT Treatment Plan
        </label>
        <textarea
          value={formData.cancer_data.mdt_treatment_plan || ''}
          onChange={(e) => updateCancerData('mdt_treatment_plan', e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          rows={4}
          placeholder="MDT discussion outcome and treatment plan..."
        />
      </div>
    </div>
  )

  const renderGenericCancerFields = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900">
        {formData.cancer_type.charAt(0).toUpperCase() + formData.cancer_type.slice(1).replace('_', ' ')} Cancer Details
      </h3>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          MDT Treatment Plan
        </label>
        <textarea
          value={formData.cancer_data.mdt_treatment_plan || ''}
          onChange={(e) => updateCancerData('mdt_treatment_plan', e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          rows={6}
          placeholder="MDT discussion outcome and treatment plan..."
        />
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-900">
          <strong>Note:</strong> Additional cancer-specific fields for {formData.cancer_type} will be added in future updates.
          Please document key clinical information in the MDT treatment plan for now.
        </p>
      </div>
    </div>
  )

  const renderStep2 = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900">Add Clinical Data (Optional)</h3>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800 mb-3">
          Would you like to add clinical data now? You can add comprehensive pathology, staging, and treatment details for this cancer episode.
        </p>
        <p className="text-sm text-blue-700">
          <strong>Skip this step</strong> if you don't have the details yet - you can always add them later from the episode detail page.
        </p>
      </div>

      {/* Tumour Option */}
      <div className="flex items-center space-x-3 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <input
          type="checkbox"
          id="addTumourCheck"
          checked={addTumourNow}
          onChange={(e) => setAddTumourNow(e.target.checked)}
          className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
        />
        <label htmlFor="addTumourCheck" className="text-sm font-medium text-gray-900 cursor-pointer flex-1">
          <div className="font-semibold">Add Tumour Details</div>
          <div className="text-xs text-gray-600 mt-1">TNM staging, histology, grades, molecular markers</div>
        </label>
      </div>

      {/* Treatment Option */}
      <div className="flex items-center space-x-3 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <input
          type="checkbox"
          id="addTreatmentCheck"
          checked={addTreatmentNow}
          onChange={(e) => setAddTreatmentNow(e.target.checked)}
          className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
        />
        <label htmlFor="addTreatmentCheck" className="text-sm font-medium text-gray-900 cursor-pointer flex-1">
          <div className="font-semibold">Add Treatment/Operation</div>
          <div className="text-xs text-gray-600 mt-1">Surgery with OPCS-4 codes, chemotherapy, radiotherapy, etc.</div>
        </label>
      </div>

      {(addTumourNow || addTreatmentNow) && (
        <div className="border-t pt-4">
          <p className="text-sm text-gray-700">
            📝 Comprehensive forms will open on the next step:
          </p>
          <ul className="list-disc list-inside ml-4 mt-2 text-sm text-gray-600 space-y-1">
            {addTumourNow && <li>Tumour details form (4 tabs: Overview, Pathology, Staging, Molecular)</li>}
            {addTreatmentNow && <li>Treatment details form with OPCS-4 procedure codes</li>}
          </ul>
        </div>
      )}

      {!addTumourNow && !addTreatmentNow && (
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-sm text-gray-600">
            ✓ Click <strong>Next</strong> to proceed to review, or check the boxes above to add clinical data.
          </p>
        </div>
      )}
    </div>
  )

  const renderStep3 = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900">Review & Submit</h3>

      <div className="bg-gray-50 rounded-lg p-6 space-y-4">
        <div>
          <h4 className="font-medium text-gray-900 mb-2">Episode Information</h4>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-gray-600">Episode ID:</dt>
            <dd className="font-medium">{formData.episode_id}</dd>
            <dt className="text-gray-600">Patient:</dt>
            <dd className="font-medium">{formData.patient_id}</dd>
            <dt className="text-gray-600">Cancer Type:</dt>
            <dd className="font-medium">{formatCancerType(formData.cancer_type)}</dd>
            <dt className="text-gray-600">Lead Clinician:</dt>
            <dd className="font-medium">{formData.lead_clinician}</dd>
            <dt className="text-gray-600">Referral Date:</dt>
            <dd className="font-medium">{formData.referral_date}</dd>
          </dl>
        </div>

        {formData.tumours && formData.tumours.length > 0 && (
          <div className="border-t pt-4">
            <h4 className="font-medium text-gray-900 mb-2">Tumours Added</h4>
            <div className="bg-green-50 border border-green-200 rounded p-3">
              <p className="text-sm text-green-800">
                ✓ {formData.tumours.length} tumour{formData.tumours.length > 1 ? 's' : ''} will be added to this episode
              </p>
              {formData.tumours.map((tumour: any, index: number) => (
                <div key={index} className="text-sm text-green-700 mt-1">
                  • {tumour.site} ({tumour.tumour_type})
                </div>
              ))}
            </div>
          </div>
        )}

        {formData.treatments && formData.treatments.length > 0 && (
          <div className="border-t pt-4">
            <h4 className="font-medium text-gray-900 mb-2">Treatments Added</h4>
            <div className="bg-green-50 border border-green-200 rounded p-3">
              <p className="text-sm text-green-800">
                ✓ {formData.treatments.length} treatment{formData.treatments.length > 1 ? 's' : ''} will be added to this episode
              </p>
              {formData.treatments.map((treatment: any, index: number) => (
                <div key={index} className="text-sm text-green-700 mt-1">
                  • {treatment.treatment_type}: {treatment.procedure_name || 'Treatment'} 
                  {treatment.treatment_date && ` (${treatment.treatment_date})`}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
          <h4 className="font-medium text-blue-900 mb-2">📋 What Happens Next?</h4>
          <p className="text-sm text-blue-800 mb-2">
            After creating this episode, you can {(formData.tumours?.length > 0 || formData.treatments?.length > 0) ? 'add more:' : 'add:'}
          </p>
          <ul className="list-disc list-inside space-y-1 ml-4 text-sm text-blue-800">
            <li><strong>Tumours</strong> - Detailed pathology, TNM staging, histology, grades, and molecular markers</li>
            <li><strong>Treatments</strong> - Surgeries with OPCS-4 codes, chemotherapy, radiotherapy, etc.</li>
            <li><strong>MDT Discussions</strong> - Record multidisciplinary team decisions</li>
          </ul>
        </div>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-900">
          <strong>Important:</strong> Please review all information carefully before submitting.
          You can edit this episode later to add treatments (surgery, chemotherapy, etc.).
        </p>
      </div>
    </div>
  )

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 z-10">
          <h2 className="text-2xl font-bold text-gray-900">
            {mode === 'create' ? 'New Cancer Episode' : 'Edit Cancer Episode'}
          </h2>

          {/* Progress Steps */}
          <div className="mt-4 flex items-center justify-between">
            {(mode === 'edit' ? [1, 3] : [1, 2, 3]).map((stepNum, index, array) => (
              <div key={stepNum} className="flex items-center flex-1">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${
                    step >= stepNum
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-600'
                  }`}
                >
                  {mode === 'edit' ? index + 1 : stepNum}
                </div>
                <div className="ml-3 text-sm">
                  <div className={`font-medium ${step >= stepNum ? 'text-blue-600' : 'text-gray-600'}`}>
                    {stepNum === 1 && 'Patient & Episode'}
                    {stepNum === 2 && 'Clinical Data (Optional)'}
                    {stepNum === 3 && 'Review'}
                  </div>
                </div>
                {index < array.length - 1 && (
                  <div
                    className={`flex-1 h-1 mx-4 ${
                      step > stepNum ? 'bg-blue-600' : 'bg-gray-200'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-6">
          {step === 1 && renderStep1()}
          {step === 2 && mode === 'create' && renderStep2()}
          {step === 3 && renderStep3()}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-between">
          <Button onClick={onCancel} variant="secondary">
            Cancel
          </Button>

          <div className="flex gap-3">
            {step > 1 && (
              <Button onClick={() => setStep(mode === 'edit' && step === 3 ? 1 : step - 1)} variant="secondary">
                Previous
              </Button>
            )}
            {step < 3 ? (
              <Button 
                onClick={() => {
                  if (step === 1 && mode === 'edit') {
                    // Skip step 2 in edit mode
                    setStep(3)
                  } else if (step === 2) {
                    if (addTumourNow) {
                      // Show tumour modal first
                      setShowTumourModal(true)
                    } else if (addTreatmentNow) {
                      // Show treatment modal if no tumour
                      setShowTreatmentModal(true)
                    } else {
                      // Skip to review if nothing selected
                      setStep(3)
                    }
                  } else {
                    setStep(step + 1)
                  }
                }} 
                variant="primary"
              >
                Next
              </Button>
            ) : (
              <Button onClick={handleSubmit} variant="primary">
                {mode === 'create' ? 'Create Episode' : 'Update Episode'}
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Tumour Modal */}
      {showTumourModal && (
        <TumourModal
          episodeId={formData.episode_id}
          onSubmit={handleTumourSubmit}
          onCancel={() => {
            setShowTumourModal(false)
            // If they also wanted treatment, show that next, otherwise go to review
            if (addTreatmentNow) {
              setShowTreatmentModal(true)
            } else {
              setStep(3)
            }
          }}
          mode="create"
        />
      )}

      {/* Treatment Modal */}
      {showTreatmentModal && (
        <AddTreatmentModal
          episodeId={formData.episode_id}
          onSubmit={handleTreatmentSubmit}
          onCancel={() => {
            setShowTreatmentModal(false)
            setStep(3) // Go to review even if cancelled
          }}
          mode="create"
        />
      )}
    </div>
  )
}
