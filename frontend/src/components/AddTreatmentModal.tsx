import { useState, useEffect } from 'react'
import { Button } from './Button'
import { DateInput } from './DateInput'
import { SurgeonSearch } from './SurgeonSearch'
import { SearchableSelect } from './SearchableSelect'
import { NHS_TRUST_OPTIONS } from '../utils/nhsTrusts'

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
  const [treatmentType, setTreatmentType] = useState(initialData?.treatment_type || 'surgery')
  const [procedureSearch, setProcedureSearch] = useState(initialData?.procedure_name || '')
  const [showProcedureDropdown, setShowProcedureDropdown] = useState(false)
  const [patientNhsNumber, setPatientNhsNumber] = useState<string>('')
  const [treatmentCount, setTreatmentCount] = useState<number>(0)
  
  // Fetch episode to get patient NHS number
  useEffect(() => {
    const fetchEpisodeData = async () => {
      try {
        // Fetch episode to get patient_id
        const episodeResponse = await fetch(`http://localhost:8000/api/episodes/${episodeId}`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        })
        const episodeData = await episodeResponse.json()
        
        // Fetch patient to get NHS number
        const patientResponse = await fetch(`http://localhost:8000/api/patients/${episodeData.patient_id}`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        })
        const patientData = await patientResponse.json()
        setPatientNhsNumber(patientData.nhs_number)
        
        // Fetch existing treatments for this patient to get count
        const treatmentsResponse = await fetch(`http://localhost:8000/api/treatments/?episode_id=${episodeId}`, {
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
    
    // Common fields
    notes: ''
  }
  })

  // Generate treatment ID when NHS number is available
  useEffect(() => {
    if (patientNhsNumber && mode === 'create' && !formData.treatment_id) {
      const newTreatmentId = generateTreatmentId(treatmentType, patientNhsNumber, treatmentCount)
      setFormData(prev => ({ ...prev, treatment_id: newTreatmentId }))
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
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
      
      // Team
      treatment.surgeon = formData.surgeon
      if (formData.anaesthetist) treatment.anaesthetist = formData.anaesthetist
      
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
      
      // Complications
      if (formData.clavien_dindo_grade) treatment.clavien_dindo_grade = formData.clavien_dindo_grade
      treatment.return_to_theatre = formData.return_to_theatre
      if (formData.return_to_theatre_reason) treatment.return_to_theatre_reason = formData.return_to_theatre_reason
      treatment.readmission_30d = formData.readmission_30d
      if (formData.readmission_reason) treatment.readmission_reason = formData.readmission_reason
      if (formData.complications?.length > 0) treatment.complications = formData.complications
      
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
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">{mode === 'edit' ? 'Edit Treatment' : 'Add Treatment'}</h2>
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Treatment Type Selection */}
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
              onChange={(e) => setFormData({ ...formData, treatment_date: e.target.value })}
            />
          </div>

          {/* Provider Organisation - NBOCA CR1450 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Provider Organisation
            </label>
            <SearchableSelect
              value={formData.provider_organisation}
              onChange={(value) => setFormData({ ...formData, provider_organisation: value })}
              options={NHS_TRUST_OPTIONS}
              getOptionValue={(opt) => opt.value}
              getOptionLabel={(opt) => opt.label}
              placeholder="Select NHS Trust..."
              className="w-full"
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
                        setFormData({ ...formData, procedure_name: '', opcs4_code: '' })
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
                          setFormData({ 
                            ...formData, 
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
                    onChange={(value) => setFormData({ ...formData, urgency: value })}
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
                    onChange={(value) => setFormData({ ...formData, complexity: value })}
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
                    onChange={(value) => setFormData({ ...formData, approach: value })}
                    options={[
                      { value: 'open', label: 'Open' },
                      { value: 'laparoscopic', label: 'Laparoscopic' },
                      { value: 'robotic', label: 'Robotic' },
                      { value: 'endoscopic', label: 'Endoscopic' }
                    ]}
                    getOptionValue={(opt) => opt.value}
                    getOptionLabel={(opt) => opt.label}
                    placeholder="Search approach..."
                    required
                  />
                </div>
              </div>

              {/* Patient Fitness */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ASA Score *
                </label>
                <SearchableSelect
                  value={formData.asa_score}
                  onChange={(value) => setFormData({ ...formData, asa_score: value })}
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

              {/* Timeline */}
              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-gray-900">Timeline</h4>
                <div className="grid grid-cols-2 gap-4">
                  <DateInput
                    label="Admission Date"
                    value={formData.admission_date}
                    onChange={(e) => setFormData({ ...formData, admission_date: e.target.value })}
                  />
                  <DateInput
                    label="Discharge Date"
                    value={formData.discharge_date}
                    onChange={(e) => setFormData({ ...formData, discharge_date: e.target.value })}
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
                      onChange={(value) => setFormData({ ...formData, anesthesia_type: value })}
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
                      onChange={(e) => setFormData({ ...formData, operation_duration_minutes: e.target.value })}
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
                      onChange={(e) => setFormData({ ...formData, blood_loss_ml: e.target.value })}
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
                      onChange={(e) => setFormData({ ...formData, units_transfused: e.target.value })}
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
                    onChange={(e) => setFormData({ ...formData, findings: e.target.value })}
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
                      onChange={(e) => setFormData({ ...formData, drains_placed: e.target.checked })}
                      className="mr-2 h-4 w-4"
                    />
                    <span className="text-sm text-gray-700">Drains Placed</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.transfusion_required}
                      onChange={(e) => setFormData({ ...formData, transfusion_required: e.target.checked })}
                      className="mr-2 h-4 w-4"
                    />
                    <span className="text-sm text-gray-700">Transfusion Required</span>
                  </label>
                </div>
              </div>

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
                    onChange={(value) => setFormData({ ...formData, clavien_dindo_grade: value })}
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
                      onChange={(e) => setFormData({ ...formData, return_to_theatre: e.target.checked })}
                      className="mr-2 h-4 w-4"
                    />
                    <span className="text-sm font-medium text-gray-700">Return to Theatre</span>
                  </label>
                  {formData.return_to_theatre && (
                    <input
                      type="text"
                      value={formData.return_to_theatre_reason}
                      onChange={(e) => setFormData({ ...formData, return_to_theatre_reason: e.target.value })}
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
                      onChange={(e) => setFormData({ ...formData, readmission_30d: e.target.checked })}
                      className="mr-2 h-4 w-4"
                    />
                    <span className="text-sm font-medium text-gray-700">30-Day Readmission</span>
                  </label>
                  {formData.readmission_30d && (
                    <input
                      type="text"
                      value={formData.readmission_reason}
                      onChange={(e) => setFormData({ ...formData, readmission_reason: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="Reason for readmission..."
                    />
                  )}
                </div>
              </div>
            </>
          )}

          {/* Chemotherapy-Specific Fields */}
          {treatmentType === 'chemotherapy' && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Regimen *
                  </label>
                  <input
                    type="text"
                    value={formData.regimen}
                    onChange={(e) => setFormData({ ...formData, regimen: e.target.value })}
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
                    onChange={(e) => setFormData({ ...formData, cycle_number: e.target.value })}
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
                    onChange={(e) => setFormData({ ...formData, dose: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., 85mg/m²"
                  />
                </div>
                <SurgeonSearch
                  value={formData.surgeon}
                  onChange={(name) => setFormData({ ...formData, surgeon: name })}
                  label="Oncologist"
                  placeholder="Type to search oncologists..."
                />
              </div>
            </>
          )}

          {/* Radiotherapy-Specific Fields */}
          {treatmentType === 'radiotherapy' && (
            <>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Site *
                  </label>
                  <input
                    type="text"
                    value={formData.site}
                    onChange={(e) => setFormData({ ...formData, site: e.target.value })}
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
                    onChange={(e) => setFormData({ ...formData, total_dose: e.target.value })}
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
                    onChange={(e) => setFormData({ ...formData, fractions: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="25"
                    required
                  />
                </div>
              </div>
              <SurgeonSearch
                value={formData.surgeon}
                onChange={(name) => setFormData({ ...formData, surgeon: name })}
                label="Oncologist"
                placeholder="Type to search oncologists..."
              />
            </>
          )}

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              rows={3}
              placeholder="Additional notes..."
            />
          </div>

          {/* Actions */}
          <div className="flex justify-end space-x-3 pt-4 border-t">
            <Button type="button" variant="secondary" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              {mode === 'edit' ? 'Update Treatment' : 'Add Treatment'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
