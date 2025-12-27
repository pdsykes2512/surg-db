import { useState, useEffect } from 'react'
import { Button } from '../common/Button'
import { DateInput } from '../common/DateInput'
import { PatientSearch } from '../search/PatientSearch'
import { SurgeonSearch } from '../search/SurgeonSearch'
import { SearchableSelect } from '../common/SearchableSelect'
import { NHSProviderSelect } from '../search/NHSProviderSelect'
import { TumourModal } from '../modals/TumourModal'
import { AddTreatmentModal } from '../modals/AddTreatmentModal'
import { formatCancerType, formatAnatomicalSite } from '../../utils/formatters'

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
  const [currentStep, setCurrentStep] = useState(1)
  const [addTumourNow, setAddTumourNow] = useState(false)
  const [addTreatmentNow, setAddTreatmentNow] = useState(false)
  const [showTumourModal, setShowTumourModal] = useState(false)
  const [showTreatmentModal, setShowTreatmentModal] = useState(false)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [selectedPatientDetails, setSelectedPatientDetails] = useState<{ mrn?: string; nhs_number?: string } | null>(null)

  const [formData, setFormData] = useState(() => {
    if (initialData) {
      // Format dates for date inputs (YYYY-MM-DD)
      const formatDateForInput = (dateStr: string | null | undefined) => {
        if (!dateStr) return ''
        return dateStr.split('T')[0] // Extract YYYY-MM-DD from ISO datetime
      }
      
      // Flatten mdt_outcome object for form fields
      const mdtOutcome = initialData.mdt_outcome || {}
      
      return {
        ...initialData,
        referral_date: formatDateForInput(initialData.referral_date),
        first_seen_date: formatDateForInput(initialData.first_seen_date),
        mdt_discussion_date: formatDateForInput(mdtOutcome.mdt_discussion_date || initialData.mdt_discussion_date),
        mdt_meeting_type: mdtOutcome.mdt_meeting_type || initialData.mdt_meeting_type || '',
        treatment_intent: mdtOutcome.treatment_intent || '',
        treatment_plan: mdtOutcome.treatment_plan || '',
        cancer_data: initialData.cancer_data || {}, // Ensure cancer_data is always an object
        surgery_performed: initialData.surgery_performed ?? null,
        no_treatment_reason: initialData.no_treatment_reason || '',
        no_treatment_reason_detail: initialData.no_treatment_reason_detail || '',
        referral_type: initialData.referral_type || '',
        referral_source: initialData.referral_source || '',
        provider_first_seen: initialData.provider_first_seen || '',
        performance_status: initialData.performance_status?.toString() || '',
      }
    }
    
    return {
      episode_id: '',
      patient_id: '',
      condition_type: 'cancer',
      cancer_type: '',
      referral_date: new Date().toISOString().split('T')[0],
      referral_type: '',
      referral_source: '',
      provider_first_seen: '',
      cns_involved: '',
      first_seen_date: '',
      mdt_discussion_date: '',
      mdt_meeting_type: '',
      treatment_intent: '',
      treatment_plan: '',
      performance_status: '',
      surgery_performed: null,
      no_treatment_reason: '',
      no_treatment_reason_detail: '',
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

  // Update form data when initialData changes (for edit mode)
  useEffect(() => {
    if (initialData) {
      const formatDateForInput = (dateStr: string | null | undefined) => {
        if (!dateStr) return ''
        return dateStr.split('T')[0]
      }
      
      // Flatten mdt_outcome object for form fields
      const mdtOutcome = initialData.mdt_outcome || {}
      
      setFormData({
        ...initialData,
        referral_date: formatDateForInput(initialData.referral_date),
        first_seen_date: formatDateForInput(initialData.first_seen_date),
        mdt_discussion_date: formatDateForInput(mdtOutcome.mdt_discussion_date || initialData.mdt_discussion_date),
        mdt_meeting_type: mdtOutcome.mdt_meeting_type || initialData.mdt_meeting_type || '',
        treatment_intent: mdtOutcome.treatment_intent || '',
        treatment_plan: mdtOutcome.treatment_plan || '',
        cancer_data: initialData.cancer_data || {},
        surgery_performed: initialData.surgery_performed ?? null,
        no_treatment_reason: initialData.no_treatment_reason || '',
        no_treatment_reason_detail: initialData.no_treatment_reason_detail || '',
        referral_type: initialData.referral_type || '',
        referral_source: initialData.referral_source || '',
        provider_first_seen: initialData.provider_first_seen || '',
        performance_status: initialData.performance_status?.toString() || '',
      })
    }
  }, [initialData])

  const updateFormData = (field: string, value: any) => {
    setFormData((prev: any) => ({ ...prev, [field]: value }))
    // Mark as changed when in edit mode
    if (mode === 'edit' && !hasUnsavedChanges) {
      setHasUnsavedChanges(true)
    }
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

  // Calculate total steps based on mode
  const totalSteps = mode === 'edit' ? 5 : 6 // Skip clinical data step in edit mode

  // Step navigation with event prevention
  const nextStep = (e?: React.MouseEvent) => {
    e?.preventDefault()
    e?.stopPropagation()
    
    // Skip step 5 (clinical data) in edit mode
    if (mode === 'edit' && currentStep === 4) {
      setCurrentStep(6)
    } else {
      setCurrentStep(prev => Math.min(prev + 1, totalSteps))
    }
  }

  const prevStep = (e?: React.MouseEvent) => {
    e?.preventDefault()
    e?.stopPropagation()
    
    // Skip step 5 (clinical data) when going back in edit mode
    if (mode === 'edit' && currentStep === 6) {
      setCurrentStep(4)
    } else {
      setCurrentStep(prev => Math.max(prev - 1, 1))
    }
  }

  const getStepTitle = (stepNum: number): string => {
    const titles: { [key: number]: string } = {
      1: 'Patient Details',
      2: 'Referral Details',
      3: 'MDT & Planning',
      4: 'Treatment Status',
      5: 'Clinical Data',
      6: 'Review'
    }
    return titles[stepNum] || ''
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
      setCurrentStep(6) // Go to review step
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
    setCurrentStep(6)
  }

  const handleSubmit = (e?: React.FormEvent, forceSubmit: boolean = false) => {
    e?.preventDefault()
    e?.stopPropagation()

    // Only submit if on final step (unless forceSubmit is true for Update Record button)
    if (!forceSubmit && currentStep < totalSteps) {
      return
    }
    
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

  // Step 1: Patient & Basic Details
  const renderStep1 = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900">Patient & Basic Details</h3>

      {/* Patient Selection */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        {mode === 'edit' ? (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Patient <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.patient_id}
              readOnly
              className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-600 cursor-not-allowed"
              placeholder="Patient ID (Read-only)"
            />
            <p className="mt-1 text-xs text-gray-500">Patient cannot be changed in edit mode</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <PatientSearch
                value={formData.patient_id}
                onChange={async (patientId, patientData) => {
                  updateFormData('patient_id', patientId)

                  // Store patient details for display
                  if (patientData) {
                    setSelectedPatientDetails({
                      mrn: patientData.mrn,
                      nhs_number: patientData.nhs_number
                    })
                  } else {
                    setSelectedPatientDetails(null)
                  }

                  // Generate episode ID when patient is selected
                  if (patientData?.nhs_number && mode === 'create') {
                    try {
                      // Fetch existing episodes for this patient to get count
                      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
                      const response = await fetch(`${API_URL}/episodes/?patient_id=${patientId}`, {
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

              {/* Display selected patient details */}
              {selectedPatientDetails && formData.patient_id ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      MRN
                    </label>
                    <input
                      type="text"
                      value={selectedPatientDetails.mrn || '-'}
                      readOnly
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      NHS Number
                    </label>
                    <input
                      type="text"
                      value={selectedPatientDetails.nhs_number || '-'}
                      readOnly
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700 text-sm"
                    />
                  </div>
                </>
              ) : (
                <>
                  <div></div>
                  <div></div>
                </>
              )}
            </div>
          </div>
        )}
      </div>

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

      {/* Referral Date */}
      <div>
        <DateInput
          label="Referral Date"
          required
          value={formData.referral_date}
          onChange={(e) => updateFormData('referral_date', e.target.value)}
        />
      </div>

      {/* Lead Clinician - filtered by subspecialty */}
      <div>
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
          <p className="mt-2 text-xs text-gray-500">
            Showing {getSubspecialtyForCancerType(formData.cancer_type)?.replace('_', ' ')} consultants only
          </p>
        )}
      </div>
    </div>
  )

  // Step 2: Referral & Process Metrics
  const renderStep2 = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900">Referral & Process Metrics</h3>

      <div className="bg-gray-50 rounded-lg p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Referral Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Referral Type
            </label>
            <SearchableSelect
              value={formData.referral_type}
              onChange={(value) => updateFormData('referral_type', value)}
              options={[
                { value: '', label: 'Not recorded' },
                { value: 'Elective', label: 'Elective' },
                { value: 'Emergency', label: 'Emergency' },
                { value: 'Internal', label: 'Internal' },
                { value: 'Screening', label: 'Screening' },
                { value: 'Other', label: 'Other' }
              ]}
              getOptionValue={(opt) => opt.value}
              getOptionLabel={(opt) => opt.label}
              placeholder="Select referral type..."
            />
          </div>

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
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Provider First Seen - CR1410 */}
          <div>
            <NHSProviderSelect
              label="Provider First Seen"
              value={formData.provider_first_seen}
              onChange={(value) => updateFormData('provider_first_seen', value)}
              placeholder="Search NHS Trust..."
            />
            <p className="mt-1 text-xs text-gray-500">NBOCA (CR1410) - NHS Trust where first seen</p>
          </div>

          {/* First Seen Date */}
          <div>
            <DateInput
              label="First Seen Date"
              value={formData.first_seen_date}
              onChange={(e) => updateFormData('first_seen_date', e.target.value)}
            />
          </div>
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
    </div>
  )

  // Step 3: MDT & Treatment Planning
  const renderStep3 = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900">MDT & Treatment Planning</h3>

      <div className="bg-gray-50 rounded-lg p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* MDT Discussion Date */}
          <div>
            <DateInput
              label="MDT Discussion Date"
              value={formData.mdt_discussion_date}
              onChange={(e) => updateFormData('mdt_discussion_date', e.target.value)}
            />
          </div>

          {/* MDT Meeting Type - NBOCA CR3190 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              MDT Meeting Type
            </label>
            <SearchableSelect
              value={formData.mdt_meeting_type}
              onChange={(value) => updateFormData('mdt_meeting_type', value)}
              options={[
                { value: '', label: 'Not recorded' },
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

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Treatment Intent */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Treatment Intent
            </label>
            <SearchableSelect
              value={formData.treatment_intent}
              onChange={(value) => updateFormData('treatment_intent', value)}
              options={[
                { value: '', label: 'Not recorded' },
                { value: 'Curative', label: 'Curative' },
                { value: 'Palliative', label: 'Palliative' },
                { value: 'No Treatment', label: 'No Treatment' }
              ]}
              getOptionValue={(opt) => opt.value}
              getOptionLabel={(opt) => opt.label}
              placeholder="Select treatment intent..."
            />
          </div>

          {/* Treatment Plan */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Treatment Plan
            </label>
            <SearchableSelect
              value={formData.treatment_plan}
              onChange={(value) => updateFormData('treatment_plan', value)}
              options={[
                { value: '', label: 'Not recorded' },
                { value: 'Surgery', label: 'Surgery' },
                { value: 'Chemotherapy', label: 'Chemotherapy' },
                { value: 'Radiotherapy', label: 'Radiotherapy' },
                { value: 'Surgery + Chemotherapy', label: 'Surgery + Chemotherapy' },
                { value: 'Surgery + Radiotherapy', label: 'Surgery + Radiotherapy' },
                { value: 'Chemotherapy + Radiotherapy', label: 'Chemotherapy + Radiotherapy' },
                { value: 'Surgery + Chemotherapy + Radiotherapy', label: 'Surgery + Chemotherapy + Radiotherapy' },
                { value: 'Palliative Care', label: 'Palliative Care' }
              ]}
              getOptionValue={(opt) => opt.value}
              getOptionLabel={(opt) => opt.label}
              placeholder="Select treatment plan..."
            />
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
      </div>
    </div>
  )

  // Step 4: Treatment Status
  const renderStep4 = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900">Treatment Status</h3>

      <div className="bg-gray-50 rounded-lg p-4 space-y-4">
        {/* Surgery Performed */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Surgery Performed
          </label>
          <SearchableSelect
            value={formData.surgery_performed === null ? '' : formData.surgery_performed ? 'yes' : 'no'}
            onChange={(value) => updateFormData('surgery_performed', value === 'yes' ? true : value === 'no' ? false : null)}
            options={[
              { value: '', label: 'Not recorded' },
              { value: 'yes', label: 'Yes' },
              { value: 'no', label: 'No' }
            ]}
            getOptionValue={(opt) => opt.value}
            getOptionLabel={(opt) => opt.label}
            placeholder="Select..."
          />
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

        {/* No Treatment Reason Detail */}
        {formData.no_treatment_reason && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              No Treatment Reason Detail
            </label>
            <textarea
              value={formData.no_treatment_reason_detail || ''}
              onChange={(e) => updateFormData('no_treatment_reason_detail', e.target.value)}
              rows={3}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="Additional details about why treatment was not provided..."
            />
          </div>
        )}
      </div>
    </div>
  )

  // Step 5: Clinical Data (Optional) - Previously Step 2
  const renderStep5 = () => (
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

  // Step 6: Review & Submit
  const renderStep6 = () => (
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
                  • {formatAnatomicalSite(tumour.site)} ({tumour.tumour_type})
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
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" style={{ margin: 0 }}>
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 z-10">
          <h2 className="text-2xl font-bold text-gray-900">
            {mode === 'create' ? 'New Cancer Episode' : 'Edit Cancer Episode'}
          </h2>

          {/* Progress Indicator */}
          <div className="mt-4">
            <div className="flex items-center justify-between">
              {Array.from({ length: totalSteps }, (_, i) => i + 1)
                .filter(stepNum => mode === 'edit' ? stepNum !== 5 : true) // Skip step 5 in edit mode
                .map((stepNum, index, array) => {
                  return (
                    <div key={stepNum} className="flex items-center flex-1">
                      <button
                        onClick={() => mode === 'edit' ? setCurrentStep(stepNum) : undefined}
                        disabled={mode === 'create'}
                        className={`
                          w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all
                          ${currentStep === stepNum ? 'bg-blue-600 text-white' :
                            currentStep > stepNum ? 'bg-green-600 text-white' :
                            'bg-gray-200 text-gray-600'}
                          ${mode === 'edit' ? 'cursor-pointer hover:ring-2 hover:ring-blue-400' : 'cursor-default'}
                        `}
                        title={mode === 'edit' ? `Jump to ${getStepTitle(stepNum)}` : getStepTitle(stepNum)}
                      >
                        {currentStep > stepNum ? '✓' : index + 1}
                      </button>
                      <div className="ml-3 text-sm flex-1">
                        <div className={`font-medium ${currentStep >= stepNum ? 'text-blue-600' : 'text-gray-600'}`}>
                          {getStepTitle(stepNum)}
                        </div>
                      </div>
                      {index < array.length - 1 && (
                        <div className={`flex-1 h-1 mx-4 ${currentStep > stepNum ? 'bg-green-600' : 'bg-gray-200'}`} />
                      )}
                    </div>
                  )
                })}
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              Step {currentStep} of {totalSteps}{mode === 'edit' ? ' (skipping optional clinical data)' : ''}
            </p>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-6">
          {currentStep === 1 && renderStep1()}
          {currentStep === 2 && renderStep2()}
          {currentStep === 3 && renderStep3()}
          {currentStep === 4 && renderStep4()}
          {currentStep === 5 && mode === 'create' && renderStep5()}
          {currentStep === 6 && renderStep6()}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Button onClick={onCancel} variant="secondary">
                Cancel
              </Button>
              {mode === 'edit' && hasUnsavedChanges && (
                <span className="text-xs text-amber-600 font-medium whitespace-nowrap">
                  (unsaved changes)
                </span>
              )}
            </div>

            <div className="flex gap-3">
              {/* Show Update Record button when in edit mode with unsaved changes */}
              {mode === 'edit' && hasUnsavedChanges && (
                <Button
                  onClick={(e) => {
                    handleSubmit(e, true) // forceSubmit = true to bypass step check
                    setHasUnsavedChanges(false)
                  }}
                  variant="primary"
                  className="bg-green-600 hover:bg-green-700"
                >
                  ✓ Update Record
                </Button>
              )}

              {currentStep > 1 && (
                <Button onClick={(e) => prevStep(e)} variant="secondary">
                  ← Previous
                </Button>
              )}
              {currentStep < totalSteps ? (
                <Button
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()

                    if (currentStep === 5 && mode === 'create') {
                      // On step 5, handle clinical data modals
                      if (addTumourNow) {
                        setShowTumourModal(true)
                      } else if (addTreatmentNow) {
                        setShowTreatmentModal(true)
                      } else {
                        nextStep(e)
                      }
                    } else {
                      nextStep(e)
                    }
                  }}
                  variant="primary"
                >
                  Next →
                </Button>
              ) : (
                <Button onClick={(e) => handleSubmit(e)} variant="primary">
                  {mode === 'create' ? 'Create Episode' : 'Update Episode'}
                </Button>
              )}
            </div>
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
              setCurrentStep(6)
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
            setCurrentStep(6) // Go to review even if cancelled
          }}
          mode="create"
        />
      )}
    </div>
  )
}

