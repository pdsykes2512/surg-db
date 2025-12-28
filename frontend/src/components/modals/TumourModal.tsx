import { useState, useEffect } from 'react'
import { Button } from '../common/Button'
import { DateInput } from '../common/DateInput'
import { SearchableSelect } from '../common/SearchableSelect'
import { calculateStage, formatStage, getStageColor } from '../../utils/cancerStaging'

interface TumourModalProps {
  episodeId: string
  onSubmit: (tumour: any) => void
  onCancel: () => void
  mode?: 'create' | 'edit'
  initialData?: any
}

const generateTumourId = (nhsNumber: string, count: number) => {
  // Clean NHS number (remove spaces)
  const cleanNHS = nhsNumber.replace(/\s/g, '')
  
  // Format count as 2-digit number
  const incrementalNum = String(count + 1).padStart(2, '0')
  
  return `TUM-${cleanNHS}-${incrementalNum}`
}

const TUMOUR_TYPES = [
  { value: 'primary', label: 'Primary Tumour' },
  { value: 'metastasis', label: 'Metastasis' },
  { value: 'recurrence', label: 'Recurrence' }
]

const COLORECTAL_SITES = [
  { value: 'caecum', label: 'Caecum (C18.0)', icd10: 'C18.0' },
  { value: 'appendix', label: 'Appendix (C18.1)', icd10: 'C18.1' },
  { value: 'ascending_colon', label: 'Ascending Colon (C18.2)', icd10: 'C18.2' },
  { value: 'hepatic_flexure', label: 'Hepatic Flexure (C18.3)', icd10: 'C18.3' },
  { value: 'transverse_colon', label: 'Transverse Colon (C18.4)', icd10: 'C18.4' },
  { value: 'splenic_flexure', label: 'Splenic Flexure (C18.5)', icd10: 'C18.5' },
  { value: 'descending_colon', label: 'Descending Colon (C18.6)', icd10: 'C18.6' },
  { value: 'sigmoid_colon', label: 'Sigmoid Colon (C18.7)', icd10: 'C18.7' },
  { value: 'rectosigmoid_junction', label: 'Rectosigmoid Junction (C19)', icd10: 'C19' },
  { value: 'rectum', label: 'Rectum (C20)', icd10: 'C20' },
  { value: 'colon_unspecified', label: 'Colon Unspecified (C18.9)', icd10: 'C18.9' }
]

const METASTATIC_SITES = [
  { value: 'liver', label: 'Liver' },
  { value: 'lung', label: 'Lung' },
  { value: 'peritoneum', label: 'Peritoneum' },
  { value: 'lymph_node', label: 'Lymph Node' },
  { value: 'bone', label: 'Bone' },
  { value: 'brain', label: 'Brain' },
  { value: 'other', label: 'Other' }
]

const TNM_VERSIONS = [
  { value: '8', label: 'TNM Version 8 (2018+)' },
  { value: '7', label: 'TNM Version 7 (before 2018)' }
]

const T_STAGES = ['Tx', 'T0', 'Tis', 'T1', 'T2', 'T3', 'T4', 'T4a', 'T4b']
const N_STAGES = ['Nx', 'N0', 'N1', 'N1a', 'N1b', 'N1c', 'N2', 'N2a', 'N2b']
const M_STAGES = ['Mx', 'M0', 'M1', 'M1a', 'M1b', 'M1c']

// Convert database TNM format to display format
// Database: "3", "1", "x" -> Display: "T3", "N1", "Tx"
const dbToDisplayTNM = (value: string | null | undefined, prefix: 'T' | 'N' | 'M'): string => {
  if (!value) return ''
  // Check if already has prefix (shouldn't happen but defensive)
  if (value.toUpperCase().startsWith(prefix)) return value
  // Handle special cases
  if (value.toLowerCase() === 'x') return `${prefix}x`
  if (value.toLowerCase() === 'is') return 'Tis'
  // Normal case: add prefix and ensure proper case
  return `${prefix}${value}`
}

// Convert display TNM format to database format
// Display: "T3", "N1", "Tx" -> Database: "3", "1", "x"
const displayToDbTNM = (value: string | null | undefined): string | null => {
  if (!value) return null
  // Remove T/N/M prefix
  const cleaned = value.replace(/^[TNM]/i, '')
  // Return lowercase for consistency
  return cleaned.toLowerCase()
}

const GRADES = [
  { value: 'well', label: 'Well differentiated (G1)' },
  { value: 'moderate', label: 'Moderately differentiated (G2)' },
  { value: 'poor', label: 'Poorly differentiated (G3)' },
  { value: 'undifferentiated', label: 'Undifferentiated (G4)' }
]

const HISTOLOGY_TYPES = [
  { value: 'Adenocarcinoma', label: 'Adenocarcinoma' },
  { value: 'Mucinous adenocarcinoma', label: 'Mucinous adenocarcinoma' },
  { value: 'Signet ring cell carcinoma', label: 'Signet ring cell carcinoma' },
  { value: 'Squamous cell carcinoma', label: 'Squamous cell carcinoma' },
  { value: 'Adenosquamous carcinoma', label: 'Adenosquamous carcinoma' },
  { value: 'Neuroendocrine carcinoma', label: 'Neuroendocrine carcinoma' },
  { value: 'Small cell carcinoma', label: 'Small cell carcinoma' },
  { value: 'Large cell carcinoma', label: 'Large cell carcinoma' },
  { value: 'Medullary carcinoma', label: 'Medullary carcinoma' },
  { value: 'Sarcomatoid carcinoma', label: 'Sarcomatoid carcinoma' },
  { value: 'Undifferentiated carcinoma', label: 'Undifferentiated carcinoma' },
  { value: 'Mixed histology', label: 'Mixed histology' },
  { value: 'Other', label: 'Other' }
]

const CRM_STATUS = [
  { value: 'clear', label: 'Clear (>1mm)' },
  { value: 'involved', label: 'Involved (≤1mm)' },
  { value: 'uncertain', label: 'Uncertain' },
  { value: 'not_applicable', label: 'Not Applicable' }
]

export function TumourModal({ episodeId, onSubmit, onCancel, mode = 'create', initialData }: TumourModalProps) {
  const [patientNhsNumber, setPatientNhsNumber] = useState<string>('')
  const [tumourCount, setTumourCount] = useState<number>(0)
  
  // Fetch episode to get patient NHS number
  useEffect(() => {
    const fetchEpisodeData = async () => {
      try {
        // Fetch episode to get patient_id
        // Use /api for relative URLs (uses Vite proxy)
        const API_URL = import.meta.env.VITE_API_URL || '/api'
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
        
        // Fetch existing tumours for this episode to get count
        const tumoursResponse = await fetch(`${API_URL}/tumours/?episode_id=${episodeId}`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        })
        const tumours = await tumoursResponse.json()
        setTumourCount(Array.isArray(tumours) ? tumours.length : 0)
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
        // Convert TNM values from database format to display format
        clinical_t: dbToDisplayTNM(initialData.clinical_t, 'T'),
        clinical_n: dbToDisplayTNM(initialData.clinical_n, 'N'),
        clinical_m: dbToDisplayTNM(initialData.clinical_m, 'M'),
        pathological_t: dbToDisplayTNM(initialData.pathological_t, 'T'),
        pathological_n: dbToDisplayTNM(initialData.pathological_n, 'N'),
        pathological_m: dbToDisplayTNM(initialData.pathological_m, 'M'),
        treated_by_treatment_ids: initialData.treated_by_treatment_ids || []
      }
    }
    return {
      tumour_id: '', // Will be generated when NHS number is available
      tumour_type: 'primary',
      site: '',
      diagnosis_date: '',
      icd10_code: '',
      snomed_morphology: '',
      tnm_version: '8',
      clinical_t: '',
      clinical_n: '',
      clinical_m: '',
      clinical_stage_date: '',
      pathological_t: '',
      pathological_n: '',
      pathological_m: '',
      pathological_stage_date: '',
      grade: '',
      histology_type: '',
      size_mm: '',
      distance_from_anal_verge_cm: '',
      mesorectal_involvement: false,
      lymph_nodes_examined: '',
      lymph_nodes_positive: '',
      lymphovascular_invasion: false,
      perineural_invasion: false,
      crm_status: '',
      crm_distance_mm: '',
      proximal_margin_mm: '',
      distal_margin_mm: '',
      mismatch_repair_status: '',
      kras_status: '',
      braf_status: '',
      treated_by_treatment_ids: [],
      notes: ''
    }
  })

  const [activeTab, setActiveTab] = useState<'basic' | 'staging' | 'pathology' | 'molecular'>('basic')

  // Generate tumour ID when NHS number is available
  useEffect(() => {
    if (patientNhsNumber && mode === 'create' && !formData.tumour_id) {
      const newTumourId = generateTumourId(patientNhsNumber, tumourCount)
      setFormData((prev: any) => ({ ...prev, tumour_id: newTumourId }))
    }
  }, [patientNhsNumber, tumourCount, mode])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Clean up empty fields and convert strings to numbers where needed
    const cleanedData = { ...formData }
    
    // Convert TNM values from display format to database format
    cleanedData.clinical_t = displayToDbTNM(cleanedData.clinical_t)
    cleanedData.clinical_n = displayToDbTNM(cleanedData.clinical_n)
    cleanedData.clinical_m = displayToDbTNM(cleanedData.clinical_m)
    cleanedData.pathological_t = displayToDbTNM(cleanedData.pathological_t)
    cleanedData.pathological_n = displayToDbTNM(cleanedData.pathological_n)
    cleanedData.pathological_m = displayToDbTNM(cleanedData.pathological_m)
    
    Object.keys(cleanedData).forEach(key => {
      if (cleanedData[key] === '' || cleanedData[key] === null) {
        delete cleanedData[key]
      } else if (['size_mm', 'distance_from_anal_verge_cm', 'crm_distance_mm', 'proximal_margin_mm', 'distal_margin_mm'].includes(key)) {
        if (cleanedData[key]) {
          cleanedData[key] = parseFloat(cleanedData[key])
        }
      } else if (['lymph_nodes_examined', 'lymph_nodes_positive'].includes(key)) {
        if (cleanedData[key]) {
          cleanedData[key] = parseInt(cleanedData[key])
        }
      }
    })
    
    onSubmit(cleanedData)
  }

  const handleSiteChange = (site: string) => {
    const siteInfo = COLORECTAL_SITES.find(s => s.value === site) || METASTATIC_SITES.find(s => s.value === site)
    setFormData({
      ...formData,
      site,
      icd10_code: siteInfo && 'icd10' in siteInfo ? siteInfo.icd10 : formData.icd10_code
    })
  }

  const isRectal = formData.site === 'rectum'
  const isPrimary = formData.tumour_type === 'primary'
  const availableSites = isPrimary ? COLORECTAL_SITES : [...COLORECTAL_SITES, ...METASTATIC_SITES]

  // Calculate clinical and pathological stages
  const clinicalStage = calculateStage('bowel', formData.clinical_t, formData.clinical_n, formData.clinical_m)
  const pathologicalStage = calculateStage('bowel', formData.pathological_t, formData.pathological_n, formData.pathological_m)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" style={{ margin: 0 }}>
      <div className="bg-white rounded-lg max-w-full sm:max-w-2xl md:max-w-3xl lg:max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="sticky top-0 bg-white border-b px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              {mode === 'edit' ? 'Edit Tumour' : 'Add Tumour'}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Track individual tumour sites (primaries, metastases, recurrences)
            </p>
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

        {/* Tabs */}
        <div className="border-b bg-gray-50">
          <div className="flex space-x-4 px-6">
            <button
              onClick={() => setActiveTab('basic')}
              className={`py-3 px-2 border-b-2 font-medium text-sm ${
                activeTab === 'basic'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Basic Information
            </button>
            <button
              onClick={() => setActiveTab('staging')}
              className={`py-3 px-2 border-b-2 font-medium text-sm ${
                activeTab === 'staging'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              TNM Staging
            </button>
            <button
              onClick={() => setActiveTab('pathology')}
              className={`py-3 px-2 border-b-2 font-medium text-sm ${
                activeTab === 'pathology'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Pathology
            </button>
            <button
              onClick={() => setActiveTab('molecular')}
              className={`py-3 px-2 border-b-2 font-medium text-sm ${
                activeTab === 'molecular'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Molecular
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto">
          <div className="p-6 space-y-6">
            {/* Basic Information Tab */}
            {activeTab === 'basic' && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Tumour Type <span className="text-red-500">*</span>
                    </label>
                    <SearchableSelect
                      value={formData.tumour_type}
                      onChange={(value) => setFormData({ ...formData, tumour_type: value })}
                      options={TUMOUR_TYPES}
                      getOptionValue={(opt) => opt.value}
                      getOptionLabel={(opt) => opt.label}
                      placeholder="Search tumour type..."
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Anatomical Site <span className="text-red-500">*</span>
                    </label>
                    <SearchableSelect
                      value={formData.site}
                      onChange={handleSiteChange}
                      options={availableSites}
                      getOptionValue={(opt) => opt.value}
                      getOptionLabel={(opt) => opt.label}
                      placeholder="Search anatomical site..."
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      ICD-10 Code
                    </label>
                    <input
                      type="text"
                      value={formData.icd10_code}
                      onChange={(e) => setFormData({ ...formData, icd10_code: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., C18.7, C20"
                    />
                    <p className="mt-1 text-xs text-gray-500">NBOCA (CR0370)</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SNOMED Morphology Code
                    </label>
                    <input
                      type="text"
                      value={formData.snomed_morphology}
                      onChange={(e) => setFormData({ ...formData, snomed_morphology: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., 81403"
                    />
                    <p className="mt-1 text-xs text-gray-500">NBOCA (CR6400) - Required for pathological diagnosis</p>
                  </div>

                  <div>
                    <DateInput
                      label="Diagnosis Date"
                      value={formData.diagnosis_date}
                      onChange={(e) => setFormData({ ...formData, diagnosis_date: e.target.value })}
                    />
                    <p className="mt-1 text-xs text-gray-500">NBOCA (CR2030)</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Histology Type
                    </label>
                    <SearchableSelect
                      value={formData.histology_type}
                      onChange={(value) => setFormData({ ...formData, histology_type: value })}
                      options={HISTOLOGY_TYPES}
                      getOptionValue={(opt) => opt.value}
                      getOptionLabel={(opt) => opt.label}
                      placeholder="Search histology type..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Grade (Differentiation)
                    </label>
                    <SearchableSelect
                      value={formData.grade}
                      onChange={(value) => setFormData({ ...formData, grade: value })}
                      options={GRADES}
                      getOptionValue={(opt) => opt.value}
                      getOptionLabel={(opt) => opt.label}
                      placeholder="Search grade..."
                    />
                    <p className="mt-1 text-xs text-gray-500">Tumour differentiation - important for staging</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Tumour Size (mm)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      value={formData.size_mm}
                      onChange={(e) => setFormData({ ...formData, size_mm: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="Maximum dimension"
                    />
                  </div>

                  {isRectal && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Distance from Anal Verge (cm)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={formData.distance_from_anal_verge_cm}
                        onChange={(e) => setFormData({ ...formData, distance_from_anal_verge_cm: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="Height above anal verge"
                      />
                      <p className="mt-1 text-xs text-gray-500">Recommended for NBOCA (CO5160)</p>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SNOMED Morphology Code
                    </label>
                    <input
                      type="text"
                      value={formData.snomed_morphology}
                      onChange={(e) => setFormData({ ...formData, snomed_morphology: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="SNOMED code"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Notes
                  </label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="Additional clinical notes..."
                  />
                </div>
              </div>
            )}

            {/* TNM Staging Tab */}
            {activeTab === 'staging' && (
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    TNM Version
                  </label>
                  <SearchableSelect
                    value={formData.tnm_version}
                    onChange={(value) => setFormData({ ...formData, tnm_version: value })}
                    options={TNM_VERSIONS}
                    getOptionValue={(opt) => opt.value}
                    getOptionLabel={(opt) => opt.label}
                    placeholder="Search TNM version..."
                  />
                  <p className="mt-1 text-xs text-gray-500">NBOCA requires version for all submissions (CR2070)</p>
                </div>

                {/* Clinical Staging */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Clinical (Pretreatment) Staging</h4>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Clinical T
                      </label>
                      <SearchableSelect
                        value={formData.clinical_t}
                        onChange={(value) => setFormData({ ...formData, clinical_t: value })}
                        options={T_STAGES.map(s => ({ value: s, label: s }))}
                        getOptionValue={(opt) => opt.value}
                        getOptionLabel={(opt) => opt.label}
                        placeholder="Search T stage..."
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Clinical N
                      </label>
                      <SearchableSelect
                        value={formData.clinical_n}
                        onChange={(value) => setFormData({ ...formData, clinical_n: value })}
                        options={N_STAGES.map(s => ({ value: s, label: s }))}
                        getOptionValue={(opt) => opt.value}
                        getOptionLabel={(opt) => opt.label}
                        placeholder="Search N stage..."
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Clinical M
                      </label>
                      <SearchableSelect
                        value={formData.clinical_m}
                        onChange={(value) => setFormData({ ...formData, clinical_m: value })}
                        options={M_STAGES.map(s => ({ value: s, label: s }))}
                        getOptionValue={(opt) => opt.value}
                        getOptionLabel={(opt) => opt.label}
                        placeholder="Search M stage..."
                      />
                    </div>

                    <DateInput
                      label="Staging Date"
                      value={formData.clinical_stage_date}
                      onChange={(e) => setFormData({ ...formData, clinical_stage_date: e.target.value })}
                    />
                  </div>
                  
                  {/* Calculated Clinical Stage */}
                  {clinicalStage !== 'Unknown' && (
                    <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-blue-900">Calculated Clinical Stage</p>
                          <p className="text-xs text-blue-700 mt-1">Auto-calculated from TNM components (AJCC 8th Edition)</p>
                        </div>
                        <span className={`px-4 py-2 text-lg font-bold rounded-lg ${getStageColor(clinicalStage)}`}>
                          {formatStage(clinicalStage)}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Pathological Staging */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Pathological (Post-Surgery) Staging</h4>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Pathological T
                      </label>
                      <SearchableSelect
                        value={formData.pathological_t}
                        onChange={(value) => setFormData({ ...formData, pathological_t: value })}
                        options={T_STAGES.map(s => ({ value: s, label: s }))}
                        getOptionValue={(opt) => opt.value}
                        getOptionLabel={(opt) => opt.label}
                        placeholder="Search T stage..."
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Pathological N
                      </label>
                      <SearchableSelect
                        value={formData.pathological_n}
                        onChange={(value) => setFormData({ ...formData, pathological_n: value })}
                        options={N_STAGES.map(s => ({ value: s, label: s }))}
                        getOptionValue={(opt) => opt.value}
                        getOptionLabel={(opt) => opt.label}
                        placeholder="Search N stage..."
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Pathological M
                      </label>
                      <SearchableSelect
                        value={formData.pathological_m}
                        onChange={(value) => setFormData({ ...formData, pathological_m: value })}
                        options={M_STAGES.map(s => ({ value: s, label: s }))}
                        getOptionValue={(opt) => opt.value}
                        getOptionLabel={(opt) => opt.label}
                        placeholder="Search M stage..."
                      />
                    </div>

                    <DateInput
                      label="Staging Date"
                      value={formData.pathological_stage_date}
                      onChange={(e) => setFormData({ ...formData, pathological_stage_date: e.target.value })}
                    />
                  </div>
                  
                  {/* Calculated Pathological Stage */}
                  {pathologicalStage !== 'Unknown' && (
                    <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-green-900">Calculated Pathological Stage</p>
                          <p className="text-xs text-green-700 mt-1">Auto-calculated from pathological TNM (AJCC 8th Edition)</p>
                        </div>
                        <span className={`px-4 py-2 text-lg font-bold rounded-lg ${getStageColor(pathologicalStage)}`}>
                          {formatStage(pathologicalStage)}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Pathology Tab */}
            {activeTab === 'pathology' && (
              <div className="space-y-6">
                {/* Lymph Nodes */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Lymph Node Assessment</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Nodes Examined
                      </label>
                      <input
                        type="number"
                        value={formData.lymph_nodes_examined}
                        onChange={(e) => setFormData({ ...formData, lymph_nodes_examined: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="Total nodes examined"
                      />
                      <p className="mt-1 text-xs text-gray-500">NBOCA (pCR0890)</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Nodes Positive
                      </label>
                      <input
                        type="number"
                        value={formData.lymph_nodes_positive}
                        onChange={(e) => setFormData({ ...formData, lymph_nodes_positive: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="Positive nodes"
                      />
                      <p className="mt-1 text-xs text-gray-500">NBOCA (pCR0900)</p>
                    </div>
                  </div>
                </div>

                {/* Resection Margins */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Resection Margins</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        CRM Status
                      </label>
                      <SearchableSelect
                        value={formData.crm_status}
                        onChange={(value) => setFormData({ ...formData, crm_status: value })}
                        options={CRM_STATUS}
                        getOptionValue={(opt) => opt.value}
                        getOptionLabel={(opt) => opt.label}
                        placeholder="Search CRM status..."
                      />
                      <p className="mt-1 text-xs text-gray-500">NBOCA (pCR1150)</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        CRM Distance (mm)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={formData.crm_distance_mm}
                        onChange={(e) => setFormData({ ...formData, crm_distance_mm: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="Distance to CRM"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Proximal Margin (mm)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={formData.proximal_margin_mm}
                        onChange={(e) => setFormData({ ...formData, proximal_margin_mm: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Distal Margin (mm)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={formData.distal_margin_mm}
                        onChange={(e) => setFormData({ ...formData, distal_margin_mm: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>

                {/* Invasion */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Invasion Features</h4>
                  <div className="space-y-3">
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={formData.lymphovascular_invasion}
                        onChange={(e) => setFormData({ ...formData, lymphovascular_invasion: e.target.checked })}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700">Lymphovascular Invasion</span>
                    </label>

                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={formData.perineural_invasion}
                        onChange={(e) => setFormData({ ...formData, perineural_invasion: e.target.checked })}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700">Perineural Invasion</span>
                    </label>

                    {isRectal && (
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={formData.mesorectal_involvement}
                          onChange={(e) => setFormData({ ...formData, mesorectal_involvement: e.target.checked })}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="text-sm text-gray-700">Mesorectal Involvement</span>
                      </label>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Molecular Tab */}
            {activeTab === 'molecular' && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Mismatch Repair Status
                    </label>
                    <SearchableSelect
                      value={formData.mismatch_repair_status}
                      onChange={(value) => setFormData({ ...formData, mismatch_repair_status: value })}
                      options={[
                        { value: 'MSI-H', label: 'MSI-H (Microsatellite Instability High)' },
                        { value: 'MSS', label: 'MSS (Microsatellite Stable)' },
                        { value: 'Unknown', label: 'Unknown' }
                      ]}
                      getOptionValue={(opt) => opt.value}
                      getOptionLabel={(opt) => opt.label}
                      placeholder="Search MMR status..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      KRAS Status
                    </label>
                    <SearchableSelect
                      value={formData.kras_status}
                      onChange={(value) => setFormData({ ...formData, kras_status: value })}
                      options={[
                        { value: 'Wild-type', label: 'Wild-type' },
                        { value: 'Mutant', label: 'Mutant' },
                        { value: 'Unknown', label: 'Unknown' }
                      ]}
                      getOptionValue={(opt) => opt.value}
                      getOptionLabel={(opt) => opt.label}
                      placeholder="Search KRAS status..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      BRAF Status
                    </label>
                    <SearchableSelect
                      value={formData.braf_status}
                      onChange={(value) => setFormData({ ...formData, braf_status: value })}
                      options={[
                        { value: 'Wild-type', label: 'Wild-type' },
                        { value: 'Mutant', label: 'Mutant' },
                        { value: 'Unknown', label: 'Unknown' }
                      ]}
                      getOptionValue={(opt) => opt.value}
                      getOptionLabel={(opt) => opt.label}
                      placeholder="Search BRAF status..."
                    />
                  </div>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h4 className="font-medium text-blue-900 mb-2">Molecular Testing Importance</h4>
                  <ul className="text-sm text-blue-800 space-y-1">
                    <li>• MMR status guides immunotherapy decisions</li>
                    <li>• KRAS/BRAF status determines anti-EGFR therapy eligibility</li>
                    <li>• MSI-H tumours may respond to checkpoint inhibitors</li>
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="sticky bottom-0 bg-white border-t px-4 sm:px-6 py-3 sm:py-4 flex justify-between items-center">
            <Button type="button" variant="secondary" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              {mode === 'edit' ? 'Update Tumour' : 'Add Tumour'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
