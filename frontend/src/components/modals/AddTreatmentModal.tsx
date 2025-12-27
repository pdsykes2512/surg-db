import { useState, useEffect } from 'react'
import { Button } from '../common/Button'
import { DateInput } from '../common/DateInput'
import { SurgeonSearch } from '../search/SurgeonSearch'
import { SearchableSelect } from '../common/SearchableSelect'
import { NHSProviderSelect } from '../search/NHSProviderSelect'

interface AddTreatmentModalProps {
  episodeId: string
  onSubmit: (treatment: any) => void
  onCancel: () => void
  mode?: 'create' | 'edit'
  initialData?: any
}

const generateTreatmentId = (type: string, nhsNumber: string, count: number) => {
  // Clean NHS number (remove spaces)
  const cleanNHS = nhsNumber.replace(/\s/g, '')
  
  // Format count as 2-digit number
  const incrementalNum = String(count + 1).padStart(2, '0')
  
  // Map treatment type to prefix
  const prefixMap: Record<string, string> = {
    'surgery': 'SUR',
    'chemotherapy': 'ONC',
    'radiotherapy': 'DXT',
    'immunotherapy': 'IMM'
  }
  
  const prefix = prefixMap[type] || 'TRE'
  return `${prefix}-${cleanNHS}-${incrementalNum}`
}

// OPCS-4 Procedure codes - common colorectal and general surgery procedures
const OPCS4_PROCEDURES = [
  // Colorectal
  { code: 'H04', name: 'Right hemicolectomy' },
  { code: 'H05', name: 'Left hemicolectomy' },
  { code: 'H06', name: 'Sigmoid colectomy' },
  { code: 'H07', name: 'Transverse colectomy' },
  { code: 'H08', name: 'Subtotal colectomy' },
  { code: 'H09', name: 'Total colectomy' },
  { code: 'H10', name: 'Proctocolectomy' },
  { code: 'H11', name: 'Panproctocolectomy' },
  { code: 'H33', name: 'Anterior resection of rectum' },
  { code: 'H34', name: 'Abdominoperineal excision of rectum' },
  { code: 'H35', name: 'Hartmann procedure' },
  { code: 'H46', name: 'Ileostomy' },
  { code: 'H47', name: 'Colostomy' },
  { code: 'H48', name: 'Closure of stoma' },
  { code: 'H49', name: 'Reversal of Hartmann procedure' },
  
  // Upper GI
  { code: 'G01', name: 'Oesophagectomy' },
  { code: 'G02', name: 'Ivor Lewis oesophagectomy' },
  { code: 'G03', name: 'Total gastrectomy' },
  { code: 'G04', name: 'Partial gastrectomy' },
  { code: 'G27', name: 'Gastrectomy and excision of lesion' },
  { code: 'G28', name: 'Gastrostomy' },
  { code: 'G29', name: 'Feeding jejunostomy' },
  
  // Hepatobiliary
  { code: 'J18', name: 'Cholecystectomy' },
  { code: 'J19', name: 'Cholecystectomy with exploration of common bile duct' },
  { code: 'J27', name: 'Hepatic resection' },
  { code: 'J38', name: 'Excision of lesion of liver' },
  { code: 'J54', name: 'Pancreatectomy' },
  { code: 'J55', name: 'Whipple procedure' },
  
  // Hernia
  { code: 'T19', name: 'Inguinal hernia repair' },
  { code: 'T20', name: 'Femoral hernia repair' },
  { code: 'T21', name: 'Umbilical hernia repair' },
  { code: 'T22', name: 'Incisional hernia repair' },
  { code: 'T23', name: 'Paraumbilical hernia repair' },
  { code: 'T24', name: 'Epigastric hernia repair' },
  { code: 'T27', name: 'Repair of hiatus hernia' },
  
  // Appendix
  { code: 'H01', name: 'Appendicectomy' },
  { code: 'H02', name: 'Laparoscopic appendicectomy' },
  
  // Breast
  { code: 'B27', name: 'Mastectomy' },
  { code: 'B28', name: 'Wide local excision of breast' },
  { code: 'B29', name: 'Simple mastectomy' },
  { code: 'B30', name: 'Modified radical mastectomy' },
  { code: 'B31', name: 'Breast reconstruction' },
  
  // Urological
  { code: 'M34', name: 'Nephrectomy' },
  { code: 'M35', name: 'Partial nephrectomy' },
  { code: 'M36', name: 'Radical nephrectomy' },
  { code: 'M42', name: 'Cystectomy' },
  { code: 'M61', name: 'Transurethral resection of prostate' },
]

// NHS Trust ODS Codes - Common NHS Trusts
// NHS Trust options imported from centralized utils

// Calculate length of stay from admission to discharge
const calculateLengthOfStay = (admissionDate: string, dischargeDate: string): number | null => {
  if (!admissionDate || !dischargeDate) return null
  
  const admission = new Date(admissionDate)
  const discharge = new Date(dischargeDate)
  
  const diffTime = discharge.getTime() - admission.getTime()
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
  
  return diffDays >= 0 ? diffDays : null
}

export function AddTreatmentModal({ episodeId, onSubmit, onCancel, mode = 'create', initialData }: AddTreatmentModalProps) {
  const [currentStep, setCurrentStep] = useState(1)
  const [treatmentType, setTreatmentType] = useState(initialData?.treatment_type || 'surgery')
  const [procedureSearch, setProcedureSearch] = useState(initialData?.procedure_name || '')
  const [showProcedureDropdown, setShowProcedureDropdown] = useState(false)
  const [patientNhsNumber, setPatientNhsNumber] = useState<string>('')
  const [treatmentCount, setTreatmentCount] = useState<number>(0)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  // Update form data and track changes in edit mode
  const updateFormData = (updates: any) => {
    setFormData((prev: any) => ({ ...prev, ...updates }))
    if (mode === 'edit' && !hasUnsavedChanges) {
      setHasUnsavedChanges(true)
    }
  }

  // Fetch episode to get patient NHS number
  useEffect(() => {
    const fetchEpisodeData = async () => {
      try {
        // Fetch episode to get patient_id
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
        const episodeResponse = await fetch(`${API_URL}/episodes/${episodeId}`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        })
        const episodeData = await episodeResponse.json()
        
        // Fetch patient to get NHS number
        const patientResponse = await fetch(`${API_URL}/patients/${episodeData.patient_id}`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        })
        const patientData = await patientResponse.json()
        setPatientNhsNumber(patientData.nhs_number)
        
        // Fetch existing treatments for this patient to get count
        const treatmentsResponse = await fetch(`${API_URL}/treatments/?episode_id=${episodeId}`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        })
        const treatments = await treatmentsResponse.json()
        setTreatmentCount(Array.isArray(treatments) ? treatments.length : 0)
      } catch (error) {
        console.error('Failed to fetch episode data:', error)
      }
    }
    
    if (mode === 'create') {
      fetchEpisodeData()
    }
  }, [episodeId, mode])
  
  const [formData, setFormData] = useState(() => {
    if (initialData) {
      return {
        ...initialData,
        // Ensure arrays are properly initialized
        additional_procedures: initialData.additional_procedures || [],
        assistant_surgeons: initialData.assistant_surgeons || [],
        specimens_sent: initialData.specimens_sent || [],
        drain_types: initialData.drain_types || [],
        complications: initialData.complications || [],
        // Convert numeric fields to strings for form inputs
        asa_score: initialData.asa_score ? String(initialData.asa_score) : '',
        blood_loss_ml: initialData.blood_loss_ml ? String(initialData.blood_loss_ml) : '',
        units_transfused: initialData.units_transfused ? String(initialData.units_transfused) : '',
        anesthesia_duration_minutes: initialData.anesthesia_duration_minutes ? String(initialData.anesthesia_duration_minutes) : '',
        operation_duration_minutes: initialData.operation_duration_minutes ? String(initialData.operation_duration_minutes) : ''
      }
    }
    return {
    treatment_id: '', // Will be generated when NHS number is available
    treatment_type: 'surgery',
    treatment_date: new Date().toISOString().split('T')[0],
    provider_organisation: 'RYR',
    
    // Surgery fields - comprehensive
    procedure_name: '',
    opcs4_code: '',
    additional_procedures: [] as string[],
    approach: '',
    urgency: 'elective',
    complexity: 'routine',
    asa_score: '',
    surgeon: '',
    assistant_surgeons: [] as string[],
    anaesthetist: '',
    
    // Timing
    admission_date: '',
    induction_time: '',
    knife_to_skin_time: '',
    surgery_end_time: '',
    discharge_date: '',
    anesthesia_duration_minutes: '',
    operation_duration_minutes: '',
    
    // Intraoperative
    anesthesia_type: 'general',
    blood_loss_ml: '',
    transfusion_required: false,
    units_transfused: '',
    findings: '',
    specimens_sent: [] as string[],
    drains_placed: false,
    drain_types: [] as string[],
    
    // Colorectal-specific: Stoma
    stoma_created: false,
    stoma_type: '',
    planned_reversal_date: '',
    stoma_closure_date: '',
    reverses_stoma_from_treatment_id: '',
    
    // Colorectal-specific: Anastomosis
    anastomosis_performed: false,
    anastomosis_type: '',
    anastomosis_configuration: '',
    anastomosis_height_cm: '',
    anastomosis_location: '',
    anterior_resection_type: '',
    defunctioning_stoma: false,
    
    // Colorectal-specific: Surgical Intent
    surgical_intent: '',
    palliative_reason: '',
    
    // Conversion Reason (when approach is 'converted_to_open')
    conversion_reason: '',
    
    // Surgical Team
    assistant_surgeon: '',
    assistant_grade: '',
    second_assistant: '',
    
    // Chemotherapy fields
    regimen: '',
    cycle_number: '',
    dose: '',
    
    // Radiotherapy fields
    site: '',
    total_dose: '',
    fractions: '',
    
    // Complications
    clavien_dindo_grade: '',
    return_to_theatre: false,
    return_to_theatre_reason: '',
    readmission_30d: false,
    readmission_reason: '',
    complications: [] as string[],
    
    // Anastomotic Leak (detailed tracking)
    anastomotic_leak_occurred: false,
    anastomotic_leak_severity: '',
    anastomotic_leak_date: '',
    anastomotic_leak_days_post_surgery: '',
    anastomotic_leak_presentation: '',
    anastomotic_leak_clinical_signs: [] as string[],
    anastomotic_leak_ct_finding: '',
    anastomotic_leak_endoscopy_finding: '',
    anastomotic_leak_management: '',
    anastomotic_leak_reoperation: false,
    anastomotic_leak_reoperation_procedure: '',
    anastomotic_leak_reoperation_date: '',
    anastomotic_leak_icu_admission: false,
    anastomotic_leak_icu_los_days: '',
    anastomotic_leak_total_hospital_stay: '',
    anastomotic_leak_mortality: false,
    anastomotic_leak_resolved: false,
    anastomotic_leak_resolution_date: '',
    anastomotic_leak_defunctioning_stoma_present: false,
    anastomotic_leak_notes: '',
    
    // Common fields
    notes: ''
  }
  })

  // Generate treatment ID when NHS number is available
  useEffect(() => {
    if (patientNhsNumber && mode === 'create' && !formData.treatment_id) {
      const newTreatmentId = generateTreatmentId(treatmentType, patientNhsNumber, treatmentCount)
      setFormData((prev: any) => ({ ...prev, treatment_id: newTreatmentId }))
    }
  }, [patientNhsNumber, treatmentCount, mode, treatmentType])
  
  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (!target.closest('.relative')) {
        setShowProcedureDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleTreatmentTypeChange = (type: string) => {
    setTreatmentType(type)
    const updatedFormData: any = {
      ...formData,
      treatment_type: type
    }
    
    // Regenerate treatment ID with new type prefix if NHS number is available
    if (patientNhsNumber && mode === 'create') {
      updatedFormData.treatment_id = generateTreatmentId(type, patientNhsNumber, treatmentCount)
    }
    
    setFormData(updatedFormData)
  }

  // Step navigation
  const totalSteps = treatmentType === 'surgery' ? 4 : 2
  const nextStep = (e?: React.MouseEvent) => {
    e?.preventDefault()
    e?.stopPropagation()
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1)
    }
  }
  const prevStep = (e?: React.MouseEvent) => {
    e?.preventDefault()
    e?.stopPropagation()
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const getStepTitle = (step: number) => {
    if (treatmentType === 'surgery') {
      const titles = ['Treatment Details', 'Personnel & Timeline', 'Intraoperative Details', 'Post-operative & Complications']
      return titles[step - 1]
    } else {
      return step === 1 ? 'Treatment Details' : 'Additional Information'
    }
  }

  const handleSubmit = (e: React.FormEvent, forceSubmit: boolean = false) => {
    e.preventDefault()

    // Only submit if on the final step (unless forceSubmit is true for Update Record button)
    if (!forceSubmit && currentStep < totalSteps) {
      return
    }
    
    // Build treatment object based on type
    const treatment: any = {
      treatment_id: formData.treatment_id,
      treatment_type: formData.treatment_type,
      treatment_date: formData.treatment_date,
      provider_organisation: formData.provider_organisation || undefined,
      notes: formData.notes
    }

    if (treatmentType === 'surgery') {
      // Procedure details
      treatment.procedure_name = formData.procedure_name
      if (formData.opcs4_code) treatment.opcs4_code = formData.opcs4_code
      treatment.approach = formData.approach
      treatment.urgency = formData.urgency
      treatment.complexity = formData.complexity
      if (formData.asa_score) treatment.asa_score = parseInt(formData.asa_score)
      if (formData.conversion_reason) treatment.conversion_reason = formData.conversion_reason
      
      // Team
      treatment.surgeon = formData.surgeon
      if (formData.anaesthetist) treatment.anaesthetist = formData.anaesthetist
      if (formData.assistant_surgeon) treatment.assistant_surgeon = formData.assistant_surgeon
      if (formData.assistant_grade) treatment.assistant_grade = formData.assistant_grade
      if (formData.second_assistant) treatment.second_assistant = formData.second_assistant
      
      // Timeline
      if (formData.admission_date) treatment.admission_date = formData.admission_date
      if (formData.discharge_date) treatment.discharge_date = formData.discharge_date
      if (formData.operation_duration_minutes) treatment.operation_duration_minutes = parseInt(formData.operation_duration_minutes)
      
      // Calculate length of stay if both dates are present
      if (formData.admission_date && formData.discharge_date) {
        const los = calculateLengthOfStay(formData.admission_date, formData.discharge_date)
        if (los !== null) {
          treatment.length_of_stay = los
        }
      }
      
      // Intraoperative
      treatment.anesthesia_type = formData.anesthesia_type
      if (formData.blood_loss_ml) treatment.blood_loss_ml = parseInt(formData.blood_loss_ml)
      treatment.transfusion_required = formData.transfusion_required
      if (formData.units_transfused) treatment.units_transfused = parseInt(formData.units_transfused)
      if (formData.findings) treatment.findings = formData.findings
      treatment.drains_placed = formData.drains_placed
      
      // Colorectal-specific: Stoma
      treatment.stoma_created = formData.stoma_created
      if (formData.stoma_type) treatment.stoma_type = formData.stoma_type
      if (formData.planned_reversal_date) treatment.planned_reversal_date = formData.planned_reversal_date
      if (formData.stoma_closure_date) treatment.stoma_closure_date = formData.stoma_closure_date
      if (formData.reverses_stoma_from_treatment_id) treatment.reverses_stoma_from_treatment_id = formData.reverses_stoma_from_treatment_id
      
      // Colorectal-specific: Anastomosis
      treatment.anastomosis_performed = formData.anastomosis_performed
      if (formData.anastomosis_type) treatment.anastomosis_type = formData.anastomosis_type
      if (formData.anastomosis_configuration) treatment.anastomosis_configuration = formData.anastomosis_configuration
      if (formData.anastomosis_height_cm) treatment.anastomosis_height_cm = parseFloat(formData.anastomosis_height_cm)
      if (formData.anastomosis_location) treatment.anastomosis_location = formData.anastomosis_location
      if (formData.anterior_resection_type) treatment.anterior_resection_type = formData.anterior_resection_type
      treatment.defunctioning_stoma = formData.defunctioning_stoma
      
      // Colorectal-specific: Surgical Intent
      if (formData.surgical_intent) treatment.surgical_intent = formData.surgical_intent
      if (formData.palliative_reason) treatment.palliative_reason = formData.palliative_reason
      
      // Complications
      if (formData.clavien_dindo_grade) treatment.clavien_dindo_grade = formData.clavien_dindo_grade
      treatment.return_to_theatre = formData.return_to_theatre
      if (formData.return_to_theatre_reason) treatment.return_to_theatre_reason = formData.return_to_theatre_reason
      treatment.readmission_30d = formData.readmission_30d
      if (formData.readmission_reason) treatment.readmission_reason = formData.readmission_reason
      if (formData.complications?.length > 0) treatment.complications = formData.complications
      
      // Anastomotic Leak detailed tracking
      if (formData.anastomotic_leak_occurred) {
        treatment.anastomotic_leak = {
          occurred: formData.anastomotic_leak_occurred,
          severity: formData.anastomotic_leak_severity,
          date_identified: formData.anastomotic_leak_date || null,
          days_post_surgery: formData.anastomotic_leak_days_post_surgery ? parseInt(formData.anastomotic_leak_days_post_surgery) : null,
          presentation: formData.anastomotic_leak_presentation,
          clinical_signs: formData.anastomotic_leak_clinical_signs,
          ct_finding: formData.anastomotic_leak_ct_finding,
          endoscopy_finding: formData.anastomotic_leak_endoscopy_finding,
          management: formData.anastomotic_leak_management,
          reoperation_performed: formData.anastomotic_leak_reoperation,
          reoperation_procedure: formData.anastomotic_leak_reoperation_procedure || null,
          reoperation_date: formData.anastomotic_leak_reoperation_date || null,
          icu_admission: formData.anastomotic_leak_icu_admission,
          icu_length_of_stay_days: formData.anastomotic_leak_icu_los_days ? parseInt(formData.anastomotic_leak_icu_los_days) : null,
          total_hospital_stay_days: formData.anastomotic_leak_total_hospital_stay ? parseInt(formData.anastomotic_leak_total_hospital_stay) : null,
          mortality: formData.anastomotic_leak_mortality,
          resolved: formData.anastomotic_leak_resolved,
          resolution_date: formData.anastomotic_leak_resolution_date || null,
          defunctioning_stoma_present: formData.anastomotic_leak_defunctioning_stoma_present,
          notes: formData.anastomotic_leak_notes || null
        }
      }
      
    } else if (treatmentType === 'chemotherapy') {
      treatment.regimen = formData.regimen
      treatment.cycle_number = parseInt(formData.cycle_number)
      treatment.dose = formData.dose
      treatment.oncologist = formData.surgeon
    } else if (treatmentType === 'radiotherapy') {
      treatment.site = formData.site
      treatment.total_dose = formData.total_dose
      treatment.fractions = parseInt(formData.fractions)
      treatment.oncologist = formData.surgeon
    }

    onSubmit(treatment)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" style={{ margin: 0 }}>
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b z-10">
          {/* Header */}
          <div className="px-6 py-4 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">{mode === 'edit' ? 'Edit Treatment' : 'Add Treatment'}</h2>
              <p className="text-xs text-gray-500 mt-1">Step {currentStep} of {totalSteps} • {treatmentType}</p>
            </div>
            <button
              onClick={onCancel}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* Progress Bar */}
          <div className="px-6 pb-4">
            <div className="flex items-center justify-between mb-2">
              {Array.from({ length: totalSteps }, (_, i) => i + 1).map((step) => (
                <div key={step} className="flex items-center flex-1">
                  <div className="flex flex-col items-center flex-1">
                    <button
                      type="button"
                      onClick={() => mode === 'edit' ? setCurrentStep(step) : undefined}
                      disabled={mode === 'create'}
                      className={`w-8 h-8 rounded-full flex items-center justify-center font-semibold text-sm transition-all ${
                        currentStep === step ? 'bg-blue-600 text-white' :
                        currentStep > step ? 'bg-green-600 text-white' :
                        'bg-gray-200 text-gray-600'
                      } ${mode === 'edit' ? 'cursor-pointer hover:ring-2 hover:ring-blue-400' : 'cursor-default'}`}
                      title={mode === 'edit' ? `Jump to ${getStepTitle(step)}` : ''}
                    >
                      {currentStep > step ? '✓' : step}
                    </button>
                    <div className={`text-xs mt-1 text-center font-medium ${mode === 'edit' ? 'cursor-pointer' : ''}`}>
                      {getStepTitle(step)}
                    </div>
                  </div>
                  {step < totalSteps && (
                    <div className={`h-1 flex-1 mx-2 rounded ${
                      currentStep > step ? 'bg-green-600' : 'bg-gray-200'
                    }`} />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6" onKeyDown={(e) => {
          // Prevent Enter key from submitting form unless on final step
          if (e.key === 'Enter' && e.target instanceof HTMLInputElement && currentStep < totalSteps) {
            e.preventDefault()
            nextStep()
          }
        }}>
          {/* Treatment Type Selection - Only show when creating and on Step 1 */}
          {mode === 'create' && currentStep === 1 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Treatment Type *
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { value: 'surgery', label: 'Surgery', icon: '🔪' },
                  { value: 'chemotherapy', label: 'Chemotherapy', icon: '💊' },
                  { value: 'radiotherapy', label: 'Radiotherapy', icon: '☢️' },
                  { value: 'immunotherapy', label: 'Immunotherapy', icon: '🧬' }
                ].map((type) => (
                  <button
                    key={type.value}
                    type="button"
                    onClick={() => handleTreatmentTypeChange(type.value)}
                    className={`p-3 border-2 rounded-lg text-center transition-all ${
                      treatmentType === type.value
                        ? 'border-blue-600 bg-blue-50 text-blue-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="text-2xl mb-1">{type.icon}</div>
                    <div className="text-sm font-medium">{type.label}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* STEP 1: Treatment Details */}
          {currentStep === 1 && (
            <>
              {/* Common Fields */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Treatment ID
                  </label>
                  <input
                    type="text"
                    value={formData.treatment_id}
                    disabled
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                  />
                </div>
                <DateInput
                  label="Treatment Date"
                  required
                  value={formData.treatment_date}
                  onChange={(e) => updateFormData({ treatment_date: e.target.value })}
                />
              </div>

              {/* Provider Organisation - NBOCA CR1450 */}
              <div>
                <NHSProviderSelect
                  label="Provider Organisation"
                  value={formData.provider_organisation}
                  onChange={(value) => updateFormData({ provider_organisation: value })}
                  placeholder="Search NHS Trust..."
                />
                <p className="mt-1 text-xs text-gray-500">NBOCA (CR1450) - NHS Trust Code where treatment provided</p>
              </div>

              {/* Surgery-Specific Fields */}
              {treatmentType === 'surgery' && (
                <>
              {/* Procedure Details */}
              <div className="relative">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Primary Procedure (OPCS-4) *
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={procedureSearch}
                    onChange={(e) => {
                      setProcedureSearch(e.target.value)
                      setShowProcedureDropdown(true)
                    }}
                    onFocus={() => setShowProcedureDropdown(true)}
                    placeholder="Type to search procedures..."
                    className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 ${procedureSearch ? 'pr-10' : ''}`}
                    required
                  />
                  {procedureSearch && (
                    <button
                      type="button"
                      onClick={() => {
                        setProcedureSearch('')
                        updateFormData({ procedure_name: '', opcs4_code: '' })
                        setShowProcedureDropdown(false)
                      }}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                      aria-label="Clear procedure"
                    >
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>
                {showProcedureDropdown && (
                  <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                    {OPCS4_PROCEDURES.filter(proc =>
                      proc.name.toLowerCase().includes(procedureSearch.toLowerCase()) ||
                      proc.code.toLowerCase().includes(procedureSearch.toLowerCase())
                    ).slice(0, 50).map((proc) => (
                      <button
                        key={proc.code}
                        type="button"
                        onClick={() => {
                          updateFormData({
                            procedure_name: proc.name,
                            opcs4_code: proc.code
                          })
                          setProcedureSearch(`${proc.code} - ${proc.name}`)
                          setShowProcedureDropdown(false)
                        }}
                        className="w-full px-3 py-2 text-left hover:bg-gray-100 focus:bg-gray-100 focus:outline-none"
                      >
                        <span className="font-medium text-blue-600">{proc.code}</span> - {proc.name}
                      </button>
                    ))}
                    {OPCS4_PROCEDURES.filter(proc =>
                      proc.name.toLowerCase().includes(procedureSearch.toLowerCase()) ||
                      proc.code.toLowerCase().includes(procedureSearch.toLowerCase())
                    ).length === 0 && (
                      <div className="px-3 py-2 text-gray-500 text-sm">No matching procedures</div>
                    )}
                  </div>
                )}
              </div>

              {/* Classification */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Urgency *
                  </label>
                  <SearchableSelect
                    value={formData.urgency}
                    onChange={(value) => updateFormData({ urgency: value })}
                    options={[
                      { value: 'elective', label: 'Elective' },
                      { value: 'urgent', label: 'Urgent' },
                      { value: 'emergency', label: 'Emergency' }
                    ]}
                    getOptionValue={(opt) => opt.value}
                    getOptionLabel={(opt) => opt.label}
                    placeholder="Search urgency..."
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Complexity
                  </label>
                  <SearchableSelect
                    value={formData.complexity}
                    onChange={(value) => updateFormData({ complexity: value })}
                    options={[
                      { value: 'routine', label: 'Routine' },
                      { value: 'intermediate', label: 'Intermediate' },
                      { value: 'complex', label: 'Complex' }
                    ]}
                    getOptionValue={(opt) => opt.value}
                    getOptionLabel={(opt) => opt.label}
                    placeholder="Search complexity..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Approach *
                  </label>
                  <SearchableSelect
                    value={formData.approach}
                    onChange={(value) => updateFormData({ approach: value })}
                    options={[
                      { value: 'open', label: 'Open' },
                      { value: 'laparoscopic', label: 'Laparoscopic' },
                      { value: 'robotic', label: 'Robotic' },
                      { value: 'converted_to_open', label: 'Converted to Open' },
                      { value: 'endoscopic', label: 'Endoscopic' }
                    ]}
                    getOptionValue={(opt) => opt.value}
                    getOptionLabel={(opt) => opt.label}
                    placeholder="Search approach..."
                    required
                  />
                </div>
              </div>
              
              {/* Conversion Reason */}
              {formData.approach === 'converted_to_open' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Conversion Reason
                  </label>
                  <SearchableSelect
                    value={formData.conversion_reason}
                    onChange={(value) => updateFormData({ conversion_reason: value })}
                    options={[
                      { value: 'oncological', label: 'Oncological' },
                      { value: 'adhesions', label: 'Adhesions' },
                      { value: 'bleeding', label: 'Bleeding' },
                      { value: 'fat', label: 'Fat/Body Habitus' },
                      { value: 'difficult_op', label: 'Difficult Operation' },
                      { value: 'time', label: 'Time Constraints (Anaesthetic)' },
                      { value: 'technical', label: 'Technical' },
                      { value: 'other', label: 'Other' }
                    ]}
                    getOptionValue={(opt) => opt.value}
                    getOptionLabel={(opt) => opt.label}
                    placeholder="Select reason..."
                  />
                </div>
              )}
              
              {/* Surgical Intent (for cancer cases) */}
              <div className="bg-purple-50 p-4 rounded-lg space-y-4">
                <h4 className="text-sm font-semibold text-gray-900">Surgical Intent (Cancer Cases)</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Intent
                    </label>
                    <SearchableSelect
                      value={formData.surgical_intent}
                      onChange={(value) => updateFormData({ surgical_intent: value })}
                      options={[
                        { value: '', label: 'Not specified' },
                        { value: 'curative', label: 'Curative' },
                        { value: 'palliative', label: 'Palliative' },
                        { value: 'uncertain', label: 'Uncertain' }
                      ]}
                      getOptionValue={(opt) => opt.value}
                      getOptionLabel={(opt) => opt.label}
                      placeholder="Select intent..."
                    />
                  </div>
                  {formData.surgical_intent === 'palliative' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Palliative Reason
                      </label>
                      <SearchableSelect
                        value={formData.palliative_reason}
                        onChange={(value) => updateFormData({ palliative_reason: value })}
                        options={[
                          { value: 'local_disease', label: 'Local Disease' },
                          { value: 'distant_disease', label: 'Distant Disease' },
                          { value: 'other', label: 'Other' }
                        ]}
                        getOptionValue={(opt) => opt.value}
                        getOptionLabel={(opt) => opt.label}
                        placeholder="Select reason..."
                      />
                    </div>
                  )}
                </div>
              </div>
                </>
              )}
            </>
          )}

          {/* STEP 2: Personnel & Timeline */}
          {currentStep === 2 && treatmentType === 'surgery' && (
            <>
              {/* Team */}
              <div className="grid grid-cols-2 gap-4">
                <SurgeonSearch
                  value={formData.surgeon}
                  onChange={(name) => {
                    setFormData({ ...formData, surgeon: name })
                  }}
                  label="Primary Surgeon"
                  roleFilter="surgeon"
                  required
                  placeholder="Type to search surgeons..."
                />
                <SurgeonSearch
                  value={formData.anaesthetist}
                  onChange={(name) => {
                    setFormData({ ...formData, anaesthetist: name })
                  }}
                  label="Anaesthetist"
                  roleFilter="anaesthetist"
                  placeholder="Type to search anaesthetists..."
                />
              </div>
              
              {/* Additional Team Members */}
              <div className="grid grid-cols-3 gap-4">
                <SurgeonSearch
                  value={formData.assistant_surgeon}
                  onChange={(name) => {
                    setFormData({ ...formData, assistant_surgeon: name })
                  }}
                  label="Assistant Surgeon"
                  roleFilter="surgeon"
                  placeholder="Type to search..."
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Assistant Grade
                  </label>
                  <input
                    type="text"
                    value={formData.assistant_grade}
                    onChange={(e) => updateFormData({ assistant_grade: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
                    placeholder="e.g., ST5, Consultant"
                  />
                </div>
                <SurgeonSearch
                  value={formData.second_assistant}
                  onChange={(name) => {
                    setFormData({ ...formData, second_assistant: name })
                  }}
                  label="Second Assistant"
                  roleFilter="surgeon"
                  placeholder="Type to search..."
                />
              </div>

              {/* Timeline */}
              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-gray-900">Timeline</h4>
                <div className="grid grid-cols-2 gap-4">
                  <DateInput
                    label="Admission Date"
                    value={formData.admission_date}
                    onChange={(e) => updateFormData({ admission_date: e.target.value })}
                  />
                  <DateInput
                    label="Discharge Date"
                    value={formData.discharge_date}
                    onChange={(e) => updateFormData({ discharge_date: e.target.value })}
                  />
                </div>
                
                {/* Length of Stay Display */}
                {formData.admission_date && formData.discharge_date && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-blue-900">Length of Stay</span>
                      <span className="text-lg font-bold text-blue-700">
                        {(() => {
                          const los = calculateLengthOfStay(formData.admission_date, formData.discharge_date)
                          return los !== null ? `${los} ${los === 1 ? 'day' : 'days'}` : 'N/A'
                        })()}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* STEP 3: Intraoperative Details */}
          {currentStep === 3 && treatmentType === 'surgery' && (
            <>
              {/* Patient Fitness */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ASA Score *
                </label>
                <SearchableSelect
                  value={formData.asa_score}
                  onChange={(value) => updateFormData({ asa_score: value })}
                  options={[
                    { value: '1', label: 'ASA I - Normal healthy patient' },
                    { value: '2', label: 'ASA II - Mild systemic disease' },
                    { value: '3', label: 'ASA III - Severe systemic disease' },
                    { value: '4', label: 'ASA IV - Severe disease, constant threat to life' },
                    { value: '5', label: 'ASA V - Moribund, not expected to survive' }
                  ]}
                  getOptionValue={(opt) => opt.value}
                  getOptionLabel={(opt) => opt.label}
                  placeholder="Select ASA grade..."
                  required
                />
              </div>

              {/* Intraoperative Details */}
              <div className="bg-gray-50 p-4 rounded-lg space-y-4">
                <h4 className="text-sm font-semibold text-gray-900">Intraoperative Details</h4>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Anesthesia Type
                    </label>
                    <SearchableSelect
                      value={formData.anesthesia_type}
                      onChange={(value) => updateFormData({ anesthesia_type: value })}
                      options={[
                        { value: 'general', label: 'General' },
                        { value: 'spinal', label: 'Spinal' },
                        { value: 'epidural', label: 'Epidural' },
                        { value: 'local', label: 'Local' },
                        { value: 'sedation', label: 'Sedation' }
                      ]}
                      getOptionValue={(opt) => opt.value}
                      getOptionLabel={(opt) => opt.label}
                      placeholder="Search anesthesia type..."
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Operation Duration (min)
                    </label>
                    <input
                      type="number"
                      value={formData.operation_duration_minutes}
                      onChange={(e) => updateFormData({ operation_duration_minutes: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
                      placeholder="120"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Blood Loss (ml)
                    </label>
                    <input
                      type="number"
                      value={formData.blood_loss_ml}
                      onChange={(e) => updateFormData({ blood_loss_ml: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
                      placeholder="150"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Units Transfused
                    </label>
                    <input
                      type="number"
                      value={formData.units_transfused}
                      onChange={(e) => updateFormData({ units_transfused: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
                      placeholder="0"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Findings
                  </label>
                  <textarea
                    value={formData.findings}
                    onChange={(e) => updateFormData({ findings: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
                    rows={2}
                    placeholder="Intraoperative findings..."
                  />
                </div>

                <div className="flex items-center space-x-4">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.drains_placed}
                      onChange={(e) => updateFormData({ drains_placed: e.target.checked })}
                      className="mr-2 h-4 w-4"
                    />
                    <span className="text-sm text-gray-700">Drains Placed</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.transfusion_required}
                      onChange={(e) => updateFormData({ transfusion_required: e.target.checked })}
                      className="mr-2 h-4 w-4"
                    />
                    <span className="text-sm text-gray-700">Transfusion Required</span>
                  </label>
                </div>
              </div>

              {/* Colorectal-Specific Fields */}
              <div className="bg-amber-50 p-4 rounded-lg space-y-4">
                <h4 className="text-sm font-semibold text-gray-900">Colorectal-Specific Details</h4>
                
                {/* Anastomosis */}
                <div className="space-y-3">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.anastomosis_performed}
                      onChange={(e) => updateFormData({ anastomosis_performed: e.target.checked })}
                      className="mr-2 h-4 w-4"
                    />
                    <span className="text-sm font-medium text-gray-700">Anastomosis Performed</span>
                  </label>
                  
                  {formData.anastomosis_performed && (
                    <div className="grid grid-cols-2 gap-4 ml-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Anastomosis Type
                        </label>
                        <SearchableSelect
                          value={formData.anastomosis_type}
                          onChange={(value) => updateFormData({ anastomosis_type: value })}
                          options={[
                            { value: 'hand_sewn', label: 'Hand-Sewn' },
                            { value: 'stapled', label: 'Stapled' },
                            { value: 'hybrid', label: 'Hybrid (hand-sewn + stapled)' }
                          ]}
                          getOptionValue={(opt) => opt.value}
                          getOptionLabel={(opt) => opt.label}
                          placeholder="Select type..."
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Configuration
                        </label>
                        <SearchableSelect
                          value={formData.anastomosis_configuration}
                          onChange={(value) => updateFormData({ anastomosis_configuration: value })}
                          options={[
                            { value: 'end_to_end', label: 'End-to-End' },
                            { value: 'end_to_side', label: 'End-to-Side' },
                            { value: 'side_to_side', label: 'Side-to-Side' },
                            { value: 'side_to_end', label: 'Side-to-End' }
                          ]}
                          getOptionValue={(opt) => opt.value}
                          getOptionLabel={(opt) => opt.label}
                          placeholder="Select configuration..."
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Anatomical Location
                        </label>
                        <SearchableSelect
                          value={formData.anastomosis_location}
                          onChange={(value) => updateFormData({ anastomosis_location: value })}
                          options={[
                            { value: 'colorectal', label: 'Colorectal' },
                            { value: 'coloanal', label: 'Coloanal' },
                            { value: 'ileocolic', label: 'Ileocolic' },
                            { value: 'ileorectal', label: 'Ileorectal' },
                            { value: 'colocolic', label: 'Colocolic' },
                            { value: 'ileoanal_pouch', label: 'Ileoanal Pouch (J-pouch)' },
                            { value: 'other', label: 'Other' }
                          ]}
                          getOptionValue={(opt) => opt.value}
                          getOptionLabel={(opt) => opt.label}
                          placeholder="Select location..."
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Height from Anal Verge (cm)
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          value={formData.anastomosis_height_cm}
                          onChange={(e) => updateFormData({ anastomosis_height_cm: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
                          placeholder="e.g., 8.5"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Anterior Resection Type
                        </label>
                        <SearchableSelect
                          value={formData.anterior_resection_type}
                          onChange={(value) => updateFormData({ anterior_resection_type: value })}
                          options={[
                            { value: 'high', label: 'High (>12cm from anal verge)' },
                            { value: 'low', label: 'Low (<12cm from anal verge)' }
                          ]}
                          getOptionValue={(opt) => opt.value}
                          getOptionLabel={(opt) => opt.label}
                          placeholder="Select type..."
                        />
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Stoma */}
                <div className="space-y-3">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.stoma_created}
                      onChange={(e) => updateFormData({ stoma_created: e.target.checked })}
                      className="mr-2 h-4 w-4"
                    />
                    <span className="text-sm font-medium text-gray-700">Stoma Created</span>
                  </label>
                  
                  {formData.stoma_created && (
                    <div className="space-y-4 ml-6">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Stoma Type *
                          </label>
                          <SearchableSelect
                            value={formData.stoma_type}
                            onChange={(value) => updateFormData({ stoma_type: value })}
                            options={[
                              { value: 'ileostomy_temporary', label: 'Ileostomy (Temporary)' },
                              { value: 'ileostomy_permanent', label: 'Ileostomy (Permanent)' },
                              { value: 'colostomy_temporary', label: 'Colostomy (Temporary)' },
                              { value: 'colostomy_permanent', label: 'Colostomy (Permanent)' }
                            ]}
                            getOptionValue={(opt) => opt.value}
                            getOptionLabel={(opt) => opt.label}
                            placeholder="Select type..."
                          />
                        </div>
                        <div>
                          <label className="flex items-center h-full items-end pb-2">
                            <input
                              type="checkbox"
                              checked={formData.defunctioning_stoma}
                              onChange={(e) => updateFormData({ defunctioning_stoma: e.target.checked })}
                              className="mr-2 h-4 w-4"
                            />
                            <span className="text-sm font-medium text-gray-700">Defunctioning/Protective Stoma</span>
                          </label>
                          <p className="text-xs text-gray-500 mt-1">Created to protect an anastomosis</p>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Link to Reversal Surgery
                          </label>
                          <input
                            type="text"
                            value={formData.reverses_stoma_from_treatment_id}
                            onChange={(e) => updateFormData({ reverses_stoma_from_treatment_id: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
                            placeholder="Treatment ID of original stoma"
                          />
                          <p className="mt-1 text-xs text-gray-500">
                            If this surgery reverses a previous stoma, enter the treatment ID
                          </p>
                        </div>
                      </div>
                      
                      {formData.stoma_type?.includes('temporary') && (
                        <div className="grid grid-cols-2 gap-4">
                          <DateInput
                            label="Planned Reversal Date"
                            value={formData.planned_reversal_date}
                            onChange={(e) => updateFormData({ planned_reversal_date: e.target.value })}
                          />
                          <div className="text-xs text-gray-500 flex items-center">
                            <svg className="w-4 h-4 mr-1 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            Should be within 2 years of surgery date
                          </div>
                        </div>
                      )}
                      
                      <div>
                        <DateInput
                          label="Actual Stoma Closure Date (if already closed)"
                          value={formData.stoma_closure_date}
                          onChange={(e) => updateFormData({ stoma_closure_date: e.target.value })}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          {/* STEP 4: Post-operative & Complications */}
          {currentStep === 4 && treatmentType === 'surgery' && (
            <>
              {/* Complications Section */}
              <div className="border-t pt-4 space-y-4">
                <h3 className="text-md font-semibold text-gray-900">Post-Operative Complications</h3>
                
                {/* Clavien-Dindo Grade */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Clavien-Dindo Grade
                  </label>
                  <SearchableSelect
                    value={formData.clavien_dindo_grade}
                    onChange={(value) => updateFormData({ clavien_dindo_grade: value })}
                    options={[
                      { value: '', label: 'None' },
                      { value: 'I', label: 'Grade I - Any deviation from normal without intervention' },
                      { value: 'II', label: 'Grade II - Requiring pharmacological treatment' },
                      { value: 'IIIa', label: 'Grade IIIa - Requiring intervention without GA' },
                      { value: 'IIIb', label: 'Grade IIIb - Requiring intervention under GA' },
                      { value: 'IVa', label: 'Grade IVa - Single organ dysfunction (inc. dialysis)' },
                      { value: 'IVb', label: 'Grade IVb - Multi-organ dysfunction' },
                      { value: 'V', label: 'Grade V - Death of patient' }
                    ]}
                    getOptionValue={(opt) => opt.value}
                    getOptionLabel={(opt) => opt.label}
                    placeholder="Select grade..."
                  />
                  <p className="mt-1 text-xs text-gray-500">Classification of surgical complications</p>
                </div>

                {/* Return to Theatre */}
                <div>
                  <label className="flex items-center mb-2">
                    <input
                      type="checkbox"
                      checked={formData.return_to_theatre}
                      onChange={(e) => updateFormData({ return_to_theatre: e.target.checked })}
                      className="mr-2 h-4 w-4"
                    />
                    <span className="text-sm font-medium text-gray-700">Return to Theatre</span>
                  </label>
                  {formData.return_to_theatre && (
                    <input
                      type="text"
                      value={formData.return_to_theatre_reason}
                      onChange={(e) => updateFormData({ return_to_theatre_reason: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="Reason for return to theatre..."
                    />
                  )}
                </div>

                {/* 30-Day Readmission */}
                <div>
                  <label className="flex items-center mb-2">
                    <input
                      type="checkbox"
                      checked={formData.readmission_30d}
                      onChange={(e) => updateFormData({ readmission_30d: e.target.checked })}
                      className="mr-2 h-4 w-4"
                    />
                    <span className="text-sm font-medium text-gray-700">30-Day Readmission</span>
                  </label>
                  {formData.readmission_30d && (
                    <input
                      type="text"
                      value={formData.readmission_reason}
                      onChange={(e) => updateFormData({ readmission_reason: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="Reason for readmission..."
                    />
                  )}
                </div>

                {/* Anastomotic Leak Detailed Tracking (NBOCA Requirement) */}
                {formData.anastomosis_performed && (
                  <div className="border-t pt-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-md font-semibold text-gray-900">Anastomotic Leak Tracking</h4>
                      <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">NBOCA Required</span>
                    </div>
                    
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={formData.anastomotic_leak_occurred}
                        onChange={(e) => updateFormData({ anastomotic_leak_occurred: e.target.checked })}
                        className="mr-2 h-4 w-4"
                      />
                      <span className="text-sm font-medium text-gray-700">Anastomotic Leak Occurred</span>
                    </label>

                    {formData.anastomotic_leak_occurred && (
                      <div className="ml-6 space-y-4 border-l-2 border-red-200 pl-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Leak Severity (ISGPS Grade) *
                            </label>
                            <SearchableSelect
                              value={formData.anastomotic_leak_severity}
                              onChange={(value) => updateFormData({ anastomotic_leak_severity: value })}
                              options={[
                                { value: 'A', label: 'Grade A - Asymptomatic (radiological only)' },
                                { value: 'B', label: 'Grade B - Requires medical intervention' },
                                { value: 'C', label: 'Grade C - Requires reoperation' }
                              ]}
                              getOptionValue={(opt) => opt.value}
                              getOptionLabel={(opt) => opt.label}
                              placeholder="Select severity..."
                            />
                          </div>
                          <DateInput
                            label="Date Identified *"
                            value={formData.anastomotic_leak_date}
                            onChange={(e) => updateFormData({ anastomotic_leak_date: e.target.value })}
                          />
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Days Post-Surgery
                            </label>
                            <input
                              type="number"
                              value={formData.anastomotic_leak_days_post_surgery}
                              onChange={(e) => updateFormData({ anastomotic_leak_days_post_surgery: e.target.value })}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                              placeholder="e.g., 7"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              How Detected
                            </label>
                            <SearchableSelect
                              value={formData.anastomotic_leak_presentation}
                              onChange={(value) => updateFormData({ anastomotic_leak_presentation: value })}
                              options={[
                                { value: 'clinical', label: 'Clinical signs' },
                                { value: 'radiological', label: 'CT/imaging' },
                                { value: 'endoscopic', label: 'Endoscopy' },
                                { value: 'at_reoperation', label: 'At reoperation' }
                              ]}
                              getOptionValue={(opt) => opt.value}
                              getOptionLabel={(opt) => opt.label}
                              placeholder="Select..."
                            />
                          </div>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Clinical Signs (select all that apply)
                          </label>
                          <div className="grid grid-cols-3 gap-2 mt-2">
                            {['fever', 'tachycardia', 'peritonitis', 'sepsis', 'ileus', 'abdominal_pain'].map(sign => (
                              <label key={sign} className="flex items-center text-sm">
                                <input
                                  type="checkbox"
                                  checked={formData.anastomotic_leak_clinical_signs.includes(sign)}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      updateFormData({ anastomotic_leak_clinical_signs: [...formData.anastomotic_leak_clinical_signs, sign] })
                                    } else {
                                      updateFormData({ anastomotic_leak_clinical_signs: formData.anastomotic_leak_clinical_signs.filter((s: string) => s !== sign) })
                                    }
                                  }}
                                  className="mr-2 h-4 w-4"
                                />
                                {sign.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                              </label>
                            ))}
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              CT Finding
                            </label>
                            <SearchableSelect
                              value={formData.anastomotic_leak_ct_finding}
                              onChange={(value) => updateFormData({ anastomotic_leak_ct_finding: value })}
                              options={[
                                { value: 'free_fluid', label: 'Free fluid' },
                                { value: 'gas', label: 'Extraluminal gas' },
                                { value: 'contrast_leak', label: 'Contrast extravasation' },
                                { value: 'collection', label: 'Pelvic collection' },
                                { value: 'none', label: 'None/normal' }
                              ]}
                              getOptionValue={(opt) => opt.value}
                              getOptionLabel={(opt) => opt.label}
                              placeholder="Select..."
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Endoscopy Finding
                            </label>
                            <SearchableSelect
                              value={formData.anastomotic_leak_endoscopy_finding}
                              onChange={(value) => updateFormData({ anastomotic_leak_endoscopy_finding: value })}
                              options={[
                                { value: 'defect_visible', label: 'Defect visible' },
                                { value: 'dehiscence', label: 'Dehiscence' },
                                { value: 'ischemia', label: 'Ischemia' },
                                { value: 'normal', label: 'Normal' }
                              ]}
                              getOptionValue={(opt) => opt.value}
                              getOptionLabel={(opt) => opt.label}
                              placeholder="Select..."
                            />
                          </div>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Management Strategy *
                          </label>
                          <SearchableSelect
                            value={formData.anastomotic_leak_management}
                            onChange={(value) => updateFormData({ anastomotic_leak_management: value })}
                            options={[
                              { value: 'conservative', label: 'Conservative (antibiotics/NBM)' },
                              { value: 'percutaneous_drainage', label: 'Percutaneous drainage' },
                              { value: 'endoscopic_intervention', label: 'Endoscopic intervention (stent/clip)' },
                              { value: 'reoperation', label: 'Reoperation' }
                            ]}
                            getOptionValue={(opt) => opt.value}
                            getOptionLabel={(opt) => opt.label}
                            placeholder="Select..."
                          />
                        </div>

                        <div className="space-y-3">
                          <label className="flex items-center">
                            <input
                              type="checkbox"
                              checked={formData.anastomotic_leak_reoperation}
                              onChange={(e) => updateFormData({ anastomotic_leak_reoperation: e.target.checked })}
                              className="mr-2 h-4 w-4"
                            />
                            <span className="text-sm font-medium text-gray-700">Reoperation Performed</span>
                          </label>
                          
                          {formData.anastomotic_leak_reoperation && (
                            <div className="grid grid-cols-2 gap-4 ml-6">
                              <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                  Procedure Performed
                                </label>
                                <SearchableSelect
                                  value={formData.anastomotic_leak_reoperation_procedure}
                                  onChange={(value) => updateFormData({ anastomotic_leak_reoperation_procedure: value })}
                                  options={[
                                    { value: 'washout', label: 'Washout/drainage' },
                                    { value: 'resection', label: 'Resection' },
                                    { value: 'stoma_formation', label: 'Stoma formation' },
                                    { value: 'anastomotic_revision', label: 'Anastomotic revision' },
                                    { value: 'hartmann', label: 'Hartmann\'s procedure' }
                                  ]}
                                  getOptionValue={(opt) => opt.value}
                                  getOptionLabel={(opt) => opt.label}
                                  placeholder="Select..."
                                />
                              </div>
                              <DateInput
                                label="Reoperation Date"
                                value={formData.anastomotic_leak_reoperation_date}
                                onChange={(e) => updateFormData({ anastomotic_leak_reoperation_date: e.target.value })}
                              />
                            </div>
                          )}
                        </div>

                        <div className="grid grid-cols-3 gap-4">
                          <label className="flex items-center">
                            <input
                              type="checkbox"
                              checked={formData.anastomotic_leak_icu_admission}
                              onChange={(e) => updateFormData({ anastomotic_leak_icu_admission: e.target.checked })}
                              className="mr-2 h-4 w-4"
                            />
                            <span className="text-sm font-medium text-gray-700">ICU/HDU Admission</span>
                          </label>
                          {formData.anastomotic_leak_icu_admission && (
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                ICU Length of Stay (days)
                              </label>
                              <input
                                type="number"
                                value={formData.anastomotic_leak_icu_los_days}
                                onChange={(e) => updateFormData({ anastomotic_leak_icu_los_days: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                placeholder="Days"
                              />
                            </div>
                          )}
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Total Hospital Stay (days)
                            </label>
                            <input
                              type="number"
                              value={formData.anastomotic_leak_total_hospital_stay}
                              onChange={(e) => updateFormData({ anastomotic_leak_total_hospital_stay: e.target.value })}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                              placeholder="From surgery to discharge"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <label className="flex items-center">
                            <input
                              type="checkbox"
                              checked={formData.anastomotic_leak_defunctioning_stoma_present}
                              onChange={(e) => updateFormData({ anastomotic_leak_defunctioning_stoma_present: e.target.checked })}
                              className="mr-2 h-4 w-4"
                            />
                            <span className="text-sm font-medium text-gray-700">Protective Stoma Present at Time of Leak</span>
                          </label>
                          <label className="flex items-center">
                            <input
                              type="checkbox"
                              checked={formData.anastomotic_leak_mortality}
                              onChange={(e) => updateFormData({ anastomotic_leak_mortality: e.target.checked })}
                              className="mr-2 h-4 w-4"
                            />
                            <span className="text-sm font-medium text-gray-700 text-red-600">Mortality</span>
                          </label>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <label className="flex items-center">
                            <input
                              type="checkbox"
                              checked={formData.anastomotic_leak_resolved}
                              onChange={(e) => updateFormData({ anastomotic_leak_resolved: e.target.checked })}
                              className="mr-2 h-4 w-4"
                            />
                            <span className="text-sm font-medium text-gray-700">Leak Resolved</span>
                          </label>
                          {formData.anastomotic_leak_resolved && (
                            <DateInput
                              label="Resolution Date"
                              value={formData.anastomotic_leak_resolution_date}
                              onChange={(e) => updateFormData({ anastomotic_leak_resolution_date: e.target.value })}
                            />
                          )}
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Additional Notes
                          </label>
                          <textarea
                            value={formData.anastomotic_leak_notes}
                            onChange={(e) => updateFormData({ anastomotic_leak_notes: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                            rows={3}
                            placeholder="Additional clinical details..."
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </>
          )}

          {/* Chemotherapy-Specific Fields - Step 1 */}
          {treatmentType === 'chemotherapy' && currentStep === 1 && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Regimen *
                  </label>
                  <input
                    type="text"
                    value={formData.regimen}
                    onChange={(e) => updateFormData({ regimen: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., FOLFOX"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cycle Number *
                  </label>
                  <input
                    type="number"
                    value={formData.cycle_number}
                    onChange={(e) => updateFormData({ cycle_number: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="1"
                    required
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Dose
                  </label>
                  <input
                    type="text"
                    value={formData.dose}
                    onChange={(e) => updateFormData({ dose: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., 85mg/m²"
                  />
                </div>
                <SurgeonSearch
                  value={formData.surgeon}
                  onChange={(name) => updateFormData({ surgeon: name })}
                  label="Oncologist"
                  placeholder="Type to search oncologists..."
                />
              </div>
            </>
          )}

          {/* Radiotherapy-Specific Fields - Step 1 */}
          {treatmentType === 'radiotherapy' && currentStep === 1 && (
            <>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Site *
                  </label>
                  <input
                    type="text"
                    value={formData.site}
                    onChange={(e) => updateFormData({ site: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., Pelvis"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Total Dose (Gy) *
                  </label>
                  <input
                    type="text"
                    value={formData.total_dose}
                    onChange={(e) => updateFormData({ total_dose: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="50"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Fractions *
                  </label>
                  <input
                    type="number"
                    value={formData.fractions}
                    onChange={(e) => updateFormData({ fractions: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="25"
                    required
                  />
                </div>
              </div>
              <SurgeonSearch
                value={formData.surgeon}
                onChange={(name) => updateFormData({ surgeon: name })}
                label="Oncologist"
                placeholder="Type to search oncologists..."
              />
            </>
          )}

          {/* STEP 2: Additional Information (for non-surgery treatments) */}
          {currentStep === 2 && (treatmentType === 'chemotherapy' || treatmentType === 'radiotherapy' || treatmentType === 'immunotherapy') && (
            <>
              {treatmentType === 'immunotherapy' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Therapy Name *
                  </label>
                  <input
                    type="text"
                    value={formData.regimen}
                    onChange={(e) => updateFormData({ regimen: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., Pembrolizumab"
                    required
                  />
                </div>
              )}
              
              <SurgeonSearch
                value={formData.surgeon}
                onChange={(name) => updateFormData({ surgeon: name })}
                label={treatmentType === 'surgery' ? 'Lead Surgeon' : 'Clinician'}
                placeholder={`Type to search ${treatmentType === 'surgery' ? 'surgeons' : 'clinicians'}...`}
              />
            </>
          )}

          {/* Notes - Show on last step for all treatment types */}
          {((treatmentType === 'surgery' && currentStep === 4) || 
            ((treatmentType === 'chemotherapy' || treatmentType === 'radiotherapy' || treatmentType === 'immunotherapy') && currentStep === 2)) && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => updateFormData({ notes: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              rows={3}
              placeholder="Additional notes..."
            />
          </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between items-center pt-4 border-t">
            <div className="flex items-center gap-2">
              <Button type="button" variant="secondary" onClick={onCancel}>
                Cancel
              </Button>
              {mode === 'edit' && hasUnsavedChanges && (
                <span className="text-xs text-amber-600 font-medium whitespace-nowrap">
                  (unsaved changes)
                </span>
              )}
            </div>
            <div className="flex space-x-3">
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
                <Button type="button" variant="secondary" onClick={(e) => prevStep(e)}>
                  ← Previous
                </Button>
              )}
              {currentStep < totalSteps ? (
                <Button type="button" variant="primary" onClick={(e) => nextStep(e)}>
                  Next →
                </Button>
              ) : (
                !hasUnsavedChanges && (
                  <Button type="submit" variant="primary">
                    {mode === 'edit' ? 'Update Treatment' : 'Add Treatment'}
                  </Button>
                )
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
