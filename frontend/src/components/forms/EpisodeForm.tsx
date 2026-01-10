import { useState, useEffect } from 'react'
import { Button } from '../common/Button'
import { DateInputTypeable } from '../common/DateInputTypeable'
import { formatNHSNumber } from '../../utils/formatters'
import { procedureToICD10, procedureToOPCS, standardProcedures } from '../../data/procedures'
import { commonDiagnoses } from '../../data/diagnoses'
import { generateTreatmentId } from '../../utils/idGenerators'

interface EpisodeFormProps {
  onSubmit: (data: any) => void
  onCancel: () => void
  initialData?: any
  mode?: 'create' | 'edit'
}

export function EpisodeForm({ onSubmit, onCancel, initialData, mode = 'create' }: EpisodeFormProps) {
  // Skip step 1 if creating from patient (patient_id is pre-filled)
  const initialStep = mode === 'create' && initialData?.patient_id ? 2 : 1
  const [step, setStep] = useState(initialStep)
  const [procedureSearch, setProcedureSearch] = useState('')
  const [showProcedureDropdown, setShowProcedureDropdown] = useState(false)
  const [additionalProcSearch, setAdditionalProcSearch] = useState('')
  const [showAdditionalProcDropdown, setShowAdditionalProcDropdown] = useState(false)
  const [diagnosisSearch, setDiagnosisSearch] = useState('')
  const [showDiagnosisDropdown, setShowDiagnosisDropdown] = useState(false)
  const [patientSearch, setPatientSearch] = useState('')
  const [showPatientDropdown, setShowPatientDropdown] = useState(false)
  const [patients, setPatients] = useState<any[]>([])
  const [surgeons, setSurgeons] = useState<any[]>([])
  const [surgeonSearch, setSurgeonSearch] = useState('')
  const [showSurgeonDropdown, setShowSurgeonDropdown] = useState(false)

  // Fetch patients list
  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
        const response = await fetch(`${API_URL}/patients/`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        if (response.ok) {
          const data = await response.json()
          setPatients(data)
        }
      } catch (error) {
        console.error('Error fetching patients:', error)
      }
    }
    fetchPatients()
  }, [])

  // Fetch surgeons list
  useEffect(() => {
    const fetchSurgeons = async () => {
      try {
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
        const response = await fetch(`${API_URL}/admin/surgeons`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        if (response.ok) {
          const data = await response.json()
          setSurgeons(data)
        }
      } catch (error) {
        console.error('Error fetching surgeons:', error)
      }
    }
    fetchSurgeons()
  }, [])

  // Track and retrieve procedure usage frequency
  const getProcedureUsage = (): Record<string, number> => {
    try {
      const stored = localStorage.getItem('procedureUsageCount')
      return stored ? JSON.parse(stored) : {}
    } catch {
      return {}
    }
  }

  const trackProcedureUsage = (procedureName: string) => {
    try {
      const usage = getProcedureUsage()
      usage[procedureName] = (usage[procedureName] || 0) + 1
      localStorage.setItem('procedureUsageCount', JSON.stringify(usage))
    } catch {
      // Silently fail if localStorage is unavailable
    }
  }

  const sortProceduresByUsage = (procedures: Array<{ proc: string; category: string }>) => {
    const usage = getProcedureUsage()
    return procedures.sort((a, b) => {
      const aCount = usage[a.proc] || 0
      const bCount = usage[b.proc] || 0
      if (bCount !== aCount) {
        return bCount - aCount // Sort by usage (descending)
      }
      return a.proc.localeCompare(b.proc) // Then alphabetically
    })
  }

  // Track and retrieve diagnosis usage frequency
  const getDiagnosisUsage = (): Record<string, number> => {
    try {
      const stored = localStorage.getItem('diagnosisUsageCount')
      return stored ? JSON.parse(stored) : {}
    } catch {
      return {}
    }
  }

  const trackDiagnosisUsage = (diagnosisName: string) => {
    try {
      const usage = getDiagnosisUsage()
      usage[diagnosisName] = (usage[diagnosisName] || 0) + 1
      localStorage.setItem('diagnosisUsageCount', JSON.stringify(usage))
    } catch {
      // Silently fail if localStorage is unavailable
    }
  }

  const sortDiagnosesByUsage = (diagnoses: Array<{ diagnosis: string; category: string }>) => {
    const usage = getDiagnosisUsage()
    return diagnoses.sort((a, b) => {
      const aCount = usage[a.diagnosis] || 0
      const bCount = usage[b.diagnosis] || 0
      if (bCount !== aCount) {
        return bCount - aCount // Sort by usage (descending)
      }
      return a.diagnosis.localeCompare(b.diagnosis) // Then alphabetically
    })
  }
  
  // Default form structure
  const defaultFormData = {
    surgery_id: '',
    patient_id: '',
    classification: {
      urgency: 'elective',
      complexity: 'routine',
      primary_diagnosis: '',
      indication: ''
    },
    procedure: {
      primary_procedure: '',
      additional_procedures: [],
      cpt_codes: [],
      icd10_codes: [],
      opcs4_code: '',
      approach: 'open',
      description: ''
    },
    perioperative_timeline: {
      admission_date: '',
      surgery_date: '',
      induction_time: '',
      knife_to_skin_time: '',
      surgery_end_time: '',
      anesthesia_duration_minutes: null,
      operation_duration_minutes: null,
      discharge_date: '',
      length_of_stay_days: null
    },
    team: {
      primary_surgeon: '',
      assistant_surgeons: [],
      anesthesiologist: '',
      scrub_nurse: '',
      circulating_nurse: ''
    },
    intraoperative: {
      anesthesia_type: 'general',
      blood_loss_ml: null,
      transfusion_required: false,
      units_transfused: null,
      findings: '',
      specimens_sent: [],
      drains_placed: false,
      drain_types: []
    }
  }
  
  // Merge initialData with defaults to ensure all nested objects exist
  const [formData, setFormData] = useState(() => {
    if (!initialData) return defaultFormData
    
    return {
      ...defaultFormData,
      ...initialData,
      classification: { ...defaultFormData.classification, ...(initialData.classification || {}) },
      procedure: { ...defaultFormData.procedure, ...(initialData.procedure || {}) },
      perioperative_timeline: { ...defaultFormData.perioperative_timeline, ...(initialData.perioperative_timeline || {}) },
      team: { ...defaultFormData.team, ...(initialData.team || {}) },
      intraoperative: { ...defaultFormData.intraoperative, ...(initialData.intraoperative || {}) }
    }
  })

  // Auto-generate surgery ID when creating new episode and patient_id is available
  useEffect(() => {
    const fetchAndGenerateId = async () => {
      if (mode === 'create' && formData.patient_id) {
        try {
          const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
          const response = await fetch(`${API_URL}/episodes/?patient_id=${formData.patient_id}`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          })
          if (response.ok) {
            const episodes = await response.json()
            // Count surgery episodes for this patient
            const surgeryCount = episodes.filter((ep: any) => ep.surgery_id?.startsWith('SUR-')).length
            const newId = generateTreatmentId('SUR', formData.patient_id, surgeryCount)
            updateSimpleField('surgery_id', newId)
          }
        } catch (error) {
          console.error('Error fetching episodes for ID generation:', error)
          // Fallback: use count 0 if fetch fails
          const newId = generateTreatmentId('SUR', formData.patient_id, 0)
          updateSimpleField('surgery_id', newId)
        }
      }
    }
    fetchAndGenerateId()
  }, [mode, formData.patient_id])

  const updateField = (section: string, field: string, value: any) => {
    setFormData((prev: any) => {
      const updated = {
        ...prev,
        [section]: {
          ...prev[section],
          [field]: value
        }
      }
      
      // Auto-combine time-only inputs with surgery_date for storage
      if (section === 'perioperative_timeline' && (field === 'induction_time' || field === 'knife_to_skin_time')) {
        const surgeryDate = updated.perioperative_timeline.surgery_date
        if (surgeryDate && value) {
          // If value is just a time (HH:MM), combine with surgery date for storage
          if (!value.includes('T') && value.match(/^\d{2}:\d{2}/)) {
            value = `${surgeryDate}T${value}`
          }
          updated.perioperative_timeline[field] = value
        }
      }
      
      // Auto-update time fields when surgery_date changes
      if (section === 'perioperative_timeline' && field === 'surgery_date' && value) {
        // Update induction_time date if it has a time component
        if (updated.perioperative_timeline.induction_time) {
          const timeMatch = updated.perioperative_timeline.induction_time.match(/T(.+)$/)
          if (timeMatch) {
            updated.perioperative_timeline.induction_time = `${value}T${timeMatch[1]}`
          }
        }
        // Update knife_to_skin_time date if it has a time component
        if (updated.perioperative_timeline.knife_to_skin_time) {
          const timeMatch = updated.perioperative_timeline.knife_to_skin_time.match(/T(.+)$/)
          if (timeMatch) {
            updated.perioperative_timeline.knife_to_skin_time = `${value}T${timeMatch[1]}`
          }
        }
        // Update or set surgery_end_time to use the surgery date
        if (updated.perioperative_timeline.surgery_end_time) {
          // If surgery_end_time already has a value, update its date portion
          const timeMatch = updated.perioperative_timeline.surgery_end_time.match(/T(.+)$/)
          if (timeMatch) {
            updated.perioperative_timeline.surgery_end_time = `${value}T${timeMatch[1]}`
          } else {
            // If it doesn't have a time component, set it to the date
            updated.perioperative_timeline.surgery_end_time = `${value}T00:00`
          }
        } else {
          // If surgery_end_time is empty, initialize it with the surgery date
          updated.perioperative_timeline.surgery_end_time = `${value}T00:00`
        }
      }
      
      // Auto-calculate durations when time fields change
      if (section === 'perioperative_timeline') {
        const timeline = updated.perioperative_timeline
        
        // Calculate anesthesia duration (induction to surgery end)
        if (timeline.induction_time && timeline.surgery_end_time) {
          const inductionDateTime = new Date(timeline.induction_time)
          const endDateTime = new Date(timeline.surgery_end_time)
          
          const diffMinutes = Math.round((endDateTime.getTime() - inductionDateTime.getTime()) / 60000)
          if (diffMinutes >= 0) {
            updated.perioperative_timeline.anesthesia_duration_minutes = diffMinutes
          }
        }
        
        // Calculate operation duration (knife to skin to surgery end)
        if (timeline.knife_to_skin_time && timeline.surgery_end_time) {
          const knifeDateTime = new Date(timeline.knife_to_skin_time)
          const endDateTime = new Date(timeline.surgery_end_time)
          
          const diffMinutes = Math.round((endDateTime.getTime() - knifeDateTime.getTime()) / 60000)
          if (diffMinutes >= 0) {
            updated.perioperative_timeline.operation_duration_minutes = diffMinutes
          }
        }
        
        // Calculate length of stay (admission to discharge in days)
        if (timeline.admission_date && timeline.discharge_date) {
          const admissionDate = new Date(timeline.admission_date)
          const dischargeDate = new Date(timeline.discharge_date)
          
          const diffDays = Math.round((dischargeDate.getTime() - admissionDate.getTime()) / (1000 * 60 * 60 * 24))
          if (diffDays >= 0) {
            updated.perioperative_timeline.length_of_stay_days = diffDays
          }
        }
      }
      
      return updated
    })
  }

  const updateSimpleField = (field: string, value: any) => {
    setFormData((prev: any) => ({
      ...prev,
      [field]: value
    }))
  }

  const handleArrayInput = (section: string, field: string, value: string) => {
    const items = value.split(',').map(item => item.trim()).filter(item => item)
    updateField(section, field, items)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Add audit trail
    const submitData = {
      ...formData,
      audit_trail: {
        created_at: new Date().toISOString(),
        created_by: localStorage.getItem('username') || 'unknown',
        updated_at: new Date().toISOString()
      }
    }
    
    onSubmit(submitData)
  }

  const totalSteps = 5

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Progress indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs sm:text-sm font-medium text-gray-700">
            <span className="hidden sm:inline">Step {step} of {totalSteps}</span>
            <span className="sm:hidden">{step}/{totalSteps}</span>
          </span>
          <span className="text-sm text-gray-500">
            {step === 1 && 'Basic Information'}
            {step === 2 && 'Classification & Procedure'}
            {step === 3 && 'Timeline'}
            {step === 4 && 'Team & Intraoperative'}
            {step === 5 && 'Review'}
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${(step / totalSteps) * 100}%` }}
          />
        </div>
      </div>

      {/* Step 1: Basic Information */}
      {step === 1 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Basic Information</h3>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Surgery ID <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.surgery_id}
              onChange={(e) => updateSimpleField('surgery_id', e.target.value)}
              className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50"
              placeholder="Auto-generated"
              readOnly
              title="Surgery ID is automatically generated"
            />
            {mode === 'create' && (
              <p className="mt-1 text-xs text-gray-500">Surgery ID is automatically generated for uniqueness</p>
            )}
          </div>

          <div className="relative">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Patient ID (MRN) <span className="text-red-500">*</span>
            </label>
            
            {initialData?.patient_id && mode === 'create' ? (
              // Show patient MRN when pre-filled
              <div>
                <input
                  type="text"
                  value={formData.patient_id}
                  readOnly
                  className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
                  title="Patient ID is pre-filled from patient selection"
                />
                <p className="mt-1 text-xs text-gray-500">Patient ID is pre-filled from selected patient</p>
              </div>
            ) : (
              // Searchable dropdown for selecting patient
              <div>
                <input
                  type="text"
                  required
                  value={formData.patient_id || patientSearch}
                  onChange={(e) => {
                    setPatientSearch(e.target.value)
                    setShowPatientDropdown(true)
                    if (!e.target.value) {
                      updateSimpleField('patient_id', '')
                    }
                  }}
                  onFocus={() => setShowPatientDropdown(true)}
                  onBlur={() => setTimeout(() => setShowPatientDropdown(false), 200)}
                  className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Search by MRN or NHS number..."
                />

                {showPatientDropdown && (() => {
                  const searchLower = patientSearch.toLowerCase()
                  const filtered = patients.filter((patient: any) => {
                    const recordMatch = patient.mrn?.toLowerCase().includes(searchLower)
                    const nhsMatch = patient.nhs_number?.replace(/\s/g, '').toLowerCase().includes(searchLower.replace(/\s/g, ''))
                    return recordMatch || nhsMatch || !searchLower
                  }).slice(0, 20) // Limit to 20 results

                  return filtered.length > 0 ? (
                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                      {filtered.map((patient: any) => (
                        <div
                          key={patient.patient_id}
                          onClick={() => {
                            updateSimpleField('patient_id', patient.patient_id)
                            setPatientSearch('')
                            setShowPatientDropdown(false)
                          }}
                          className="px-3 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                        >
                          <div className="font-medium text-gray-900">
                            {patient.first_name} {patient.last_name}
                          </div>
                          <div className="text-xs text-gray-500">
                            MRN: {patient.mrn} | NHS: {formatNHSNumber(patient.nhs_number)}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : searchLower ? (
                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg p-3 text-sm text-gray-500">
                      No patients found matching "{searchLower}"
                    </div>
                  ) : null
                })()}

                <p className="mt-1 text-xs text-gray-500">
                  Search by record number or NHS number
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Step 2: Classification & Procedure */}
      {step === 2 && (
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Classification</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Urgency <span className="text-red-500">*</span>
                </label>
                <select
                  required
                  value={formData.classification.urgency}
                  onChange={(e) => updateField('classification', 'urgency', e.target.value)}
                  className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 appearance-none bg-white"
                >
                  <option value="elective">Elective</option>
                  <option value="urgent">Urgent</option>
                  <option value="emergency">Emergency</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Complexity
                </label>
                <select
                  value={formData.classification.complexity}
                  onChange={(e) => updateField('classification', 'complexity', e.target.value)}
                  className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 appearance-none bg-white"
                >
                  <option value="routine">Routine</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="complex">Complex</option>
                </select>
              </div>
            </div>

            <div className="mt-4 relative">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Primary Diagnosis <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.classification.primary_diagnosis || diagnosisSearch}
                onChange={(e) => {
                  setDiagnosisSearch(e.target.value)
                  setShowDiagnosisDropdown(true)
                  if (!e.target.value) {
                    updateField('classification', 'primary_diagnosis', '')
                  }
                }}
                onFocus={() => setShowDiagnosisDropdown(true)}
                onBlur={() => setTimeout(() => setShowDiagnosisDropdown(false), 200)}
                className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="Type to search diagnoses..."
              />

              {showDiagnosisDropdown && (() => {
                const searchLower = (formData.classification.primary_diagnosis || diagnosisSearch).toLowerCase()
                const allDiagnoses = [
                  ...commonDiagnoses.malignant.map(d => ({ diagnosis: d, category: 'Malignant' })),
                  ...commonDiagnoses.inflammatory.map(d => ({ diagnosis: d, category: 'Inflammatory' })),
                  ...commonDiagnoses.benign.map(d => ({ diagnosis: d, category: 'Benign' })),
                  ...commonDiagnoses.hernia.map(d => ({ diagnosis: d, category: 'Hernia' })),
                  ...commonDiagnoses.other.map(d => ({ diagnosis: d, category: 'Other' }))
                ]
                const filtered = sortDiagnosesByUsage(
                  allDiagnoses.filter(({ diagnosis }) => diagnosis.toLowerCase().includes(searchLower))
                )
                
                return filtered.length > 0 ? (
                  <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                    {filtered.map(({ diagnosis, category }) => (
                      <div
                        key={diagnosis}
                        onClick={() => {
                          updateField('classification', 'primary_diagnosis', diagnosis)
                          trackDiagnosisUsage(diagnosis)
                          setDiagnosisSearch('')
                          setShowDiagnosisDropdown(false)
                        }}
                        className="px-3 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                      >
                        <div className="font-medium text-gray-900">{diagnosis}</div>
                        <div className="text-xs text-gray-500">{category}</div>
                      </div>
                    ))}
                  </div>
                ) : searchLower ? (
                  <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg p-3 text-sm text-gray-500">
                    No diagnoses found matching "{searchLower}"
                  </div>
                ) : null
              })()}

              <p className="mt-1 text-xs text-gray-500">
                Type to search standardised diagnoses
              </p>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Procedure</h3>
            
            <div className="space-y-4">
              <div className="relative">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Primary Procedure <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.procedure.primary_procedure || procedureSearch}
                  onChange={(e) => {
                    setProcedureSearch(e.target.value)
                    setShowProcedureDropdown(true)
                    if (!e.target.value) {
                      updateField('procedure', 'primary_procedure', '')
                    }
                  }}
                  onFocus={() => setShowProcedureDropdown(true)}
                  onBlur={() => setTimeout(() => setShowProcedureDropdown(false), 200)}
                  className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Type to search procedures..."
                />
                
                {showProcedureDropdown && (() => {
                  const searchLower = (formData.procedure.primary_procedure || procedureSearch).toLowerCase()
                  const allProcs = [
                    ...standardProcedures.upperGI.map(p => ({ proc: p, category: 'Upper GI' })),
                    ...standardProcedures.lowerGI.map(p => ({ proc: p, category: 'Lower GI' })),
                    ...standardProcedures.hernia.map(p => ({ proc: p, category: 'Hernia' }))
                  ]
                  const filtered = sortProceduresByUsage(
                    allProcs.filter(({ proc }) => proc.toLowerCase().includes(searchLower))
                  )
                  
                  return filtered.length > 0 ? (
                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                      {filtered.map(({ proc, category }) => (
                        <div
                          key={proc}
                          onClick={() => {
                            updateField('procedure', 'primary_procedure', proc)
                            // Auto-populate ICD-10 and OPCS-4 codes
                            const icd10Codes = procedureToICD10[proc] || []
                            const opcsCodes = procedureToOPCS[proc] || []
                            updateField('procedure', 'icd10_codes', icd10Codes)
                            // Take first OPCS-4 code as primary procedure code
                            updateField('procedure', 'opcs4_code', opcsCodes[0] || '')
                            trackProcedureUsage(proc)
                            setProcedureSearch('')
                            setShowProcedureDropdown(false)
                          }}
                          className="px-3 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                        >
                          <div className="font-medium text-gray-900">{proc}</div>
                          <div className="text-xs text-gray-500">{category}</div>
                        </div>
                      ))}
                    </div>
                  ) : searchLower ? (
                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg p-3 text-sm text-gray-500">
                      No procedures found matching "{searchLower}"
                    </div>
                  ) : null
                })()}
                
                <p className="mt-1 text-xs text-gray-500">
                  Type to search standardised procedure names
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Approach <span className="text-red-500">*</span>
                </label>
                <select
                  required
                  value={formData.procedure.approach}
                  onChange={(e) => updateField('procedure', 'approach', e.target.value)}
                  className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 appearance-none bg-white"
                >
                  <option value="open">Open</option>
                  <option value="laparoscopic">Laparoscopic</option>
                  <option value="robotic">Robotic</option>
                  <option value="converted">Converted</option>
                </select>
              </div>

              <div className="relative">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Additional Procedures
                </label>
                
                {/* Display selected procedures as chips */}
                {(formData.procedure.additional_procedures || []).length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-2">
                    {(formData.procedure.additional_procedures || []).map((proc: string, index: number) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
                      >
                        {proc}
                        <button
                          type="button"
                          onClick={() => {
                            const updated = (formData.procedure.additional_procedures || []).filter((_: any, i: number) => i !== index)
                            updateField('procedure', 'additional_procedures', updated)
                          }}
                          className="ml-2 text-blue-600 hover:text-blue-800"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                
                <input
                  type="text"
                  value={additionalProcSearch}
                  onChange={(e) => {
                    setAdditionalProcSearch(e.target.value)
                    setShowAdditionalProcDropdown(true)
                  }}
                  onFocus={() => setShowAdditionalProcDropdown(true)}
                  onBlur={() => setTimeout(() => setShowAdditionalProcDropdown(false), 200)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && additionalProcSearch.trim()) {
                      e.preventDefault()
                      const current = formData.procedure.additional_procedures || []
                      if (!current.includes(additionalProcSearch.trim())) {
                        updateField('procedure', 'additional_procedures', [...current, additionalProcSearch.trim()])
                      }
                      setAdditionalProcSearch('')
                      setShowAdditionalProcDropdown(false)
                    }
                  }}
                  className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Type to search or enter custom procedure..."
                />
                
                {showAdditionalProcDropdown && (() => {
                  const searchLower = additionalProcSearch.toLowerCase()
                  const allProcs = [
                    ...standardProcedures.upperGI.map(p => ({ proc: p, category: 'Upper GI' })),
                    ...standardProcedures.lowerGI.map(p => ({ proc: p, category: 'Lower GI' })),
                    ...standardProcedures.hernia.map(p => ({ proc: p, category: 'Hernia' }))
                  ]
                  const sorted = sortProceduresByUsage(allProcs)
                  const filtered = searchLower 
                    ? sortProceduresByUsage(allProcs.filter(({ proc }) => proc.toLowerCase().includes(searchLower)))
                    : sorted.slice(0, 10) // Show top 10 most used when empty
                  
                  return filtered.length > 0 ? (
                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                      {searchLower && !filtered.some(({ proc }) => proc.toLowerCase() === searchLower) && (
                        <div
                          onClick={() => {
                            const current = formData.procedure.additional_procedures || []
                            if (!current.includes(additionalProcSearch.trim())) {
                              updateField('procedure', 'additional_procedures', [...current, additionalProcSearch.trim()])
                            }
                            setAdditionalProcSearch('')
                            setShowAdditionalProcDropdown(false)
                          }}
                          className="px-3 py-2 bg-green-50 hover:bg-green-100 cursor-pointer border-b border-gray-200 text-green-800"
                        >
                          <div className="font-medium">+ Add custom: "{additionalProcSearch}"</div>
                          <div className="text-xs">Press Enter or click to add</div>
                        </div>
                      )}
                      {filtered.map(({ proc, category }) => (
                        <div
                          key={proc}
                          onClick={() => {
                            const current = formData.procedure.additional_procedures || []
                            if (!current.includes(proc)) {
                              updateField('procedure', 'additional_procedures', [...current, proc])
                              trackProcedureUsage(proc)
                            }
                            setAdditionalProcSearch('')
                            setShowAdditionalProcDropdown(false)
                          }}
                          className="px-3 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                        >
                          <div className="font-medium text-gray-900">{proc}</div>
                          <div className="text-xs text-gray-500">{category}</div>
                        </div>
                      ))}
                    </div>
                  ) : searchLower ? (
                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg">
                      <div
                        onClick={() => {
                          const current = formData.procedure.additional_procedures || []
                          if (!current.includes(additionalProcSearch.trim())) {
                            updateField('procedure', 'additional_procedures', [...current, additionalProcSearch.trim()])
                          }
                          setAdditionalProcSearch('')
                          setShowAdditionalProcDropdown(false)
                        }}
                        className="px-3 py-2 bg-green-50 hover:bg-green-100 cursor-pointer text-green-800"
                      >
                        <div className="font-medium">+ Add custom: "{additionalProcSearch}"</div>
                        <div className="text-xs">Press Enter or click to add</div>
                      </div>
                    </div>
                  ) : null
                })()}
                
                <p className="mt-1 text-xs text-gray-500">
                  Select from list or type custom procedure name. Press Enter to add.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    ICD-10 Procedure Codes
                  </label>
                  <input
                    type="text"
                    value={(formData.procedure.icd10_codes || []).join(', ')}
                    readOnly
                    className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
                    placeholder="Auto-populated"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Automatically populated from procedure
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    OPCS-4 Code
                  </label>
                  <input
                    type="text"
                    value={formData.procedure.opcs4_code || ''}
                    readOnly
                    className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
                    placeholder="Auto-populated"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    NHS procedural classification code (primary)
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Timeline */}
      {step === 3 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Perioperative Timeline</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <DateInputTypeable
                label="Admission Date"
                required
                value={formData.perioperative_timeline.admission_date}
                onChange={(e) => updateField('perioperative_timeline', 'admission_date', e.target.value)}
              />
            </div>

            <div>
              <DateInputTypeable
                label="Surgery Date"
                required
                value={formData.perioperative_timeline.surgery_date}
                onChange={(e) => updateField('perioperative_timeline', 'surgery_date', e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Induction Time
              </label>
              <input
                type="time"
                value={formData.perioperative_timeline.induction_time ? formData.perioperative_timeline.induction_time.split('T')[1] || '' : ''}
                onChange={(e) => updateField('perioperative_timeline', 'induction_time', e.target.value)}
                className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">When anaesthesia begins (automatically uses surgery date)</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Knife to Skin
              </label>
              <input
                type="time"
                value={formData.perioperative_timeline.knife_to_skin_time ? formData.perioperative_timeline.knife_to_skin_time.split('T')[1] || '' : ''}
                onChange={(e) => updateField('perioperative_timeline', 'knife_to_skin_time', e.target.value)}
                className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">When surgery incision begins (automatically uses surgery date)</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Surgery End Time
              </label>
              <input
                type="datetime-local"
                value={formData.perioperative_timeline.surgery_end_time || (formData.perioperative_timeline.surgery_date ? `${formData.perioperative_timeline.surgery_date}T` : '')}
                onChange={(e) => updateField('perioperative_timeline', 'surgery_end_time', e.target.value)}
                className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">Date and time when surgery ends</p>
            </div>

            <div>
              <DateInputTypeable
                label="Discharge Date"
                value={formData.perioperative_timeline.discharge_date}
                onChange={(e) => updateField('perioperative_timeline', 'discharge_date', e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Operation Duration (minutes)
              </label>
              <input
                type="number"
                value={formData.perioperative_timeline.operation_duration_minutes || ''}
                readOnly
                className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
                placeholder="Auto-calculated"
              />
              <p className="mt-1 text-xs text-gray-500">Calculated from knife to skin to end time</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Anaesthesia Duration (minutes)
              </label>
              <input
                type="number"
                value={formData.perioperative_timeline.anesthesia_duration_minutes || ''}
                readOnly
                className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
                placeholder="Auto-calculated"
              />
              <p className="mt-1 text-xs text-gray-500">Calculated from induction to end time</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Length of Stay (days)
              </label>
              <input
                type="number"
                min="0"
                value={formData.perioperative_timeline.length_of_stay_days || ''}
                readOnly
                className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
                placeholder="Auto-calculated"
              />
              <p className="mt-1 text-xs text-gray-500">Calculated from admission to discharge date</p>
            </div>
          </div>
        </div>
      )}

      {/* Step 4: Team & Intraoperative */}
      {step === 4 && (
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Surgical Team</h3>
            
            <div className="space-y-4">
              <div className="relative">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Primary Surgeon <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={surgeonSearch || formData.team.primary_surgeon}
                  onChange={(e) => {
                    setSurgeonSearch(e.target.value)
                    setShowSurgeonDropdown(true)
                  }}
                  onFocus={() => setShowSurgeonDropdown(true)}
                  onBlur={() => setTimeout(() => setShowSurgeonDropdown(false), 200)}
                  className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Type to search surgeons..."
                />
                {showSurgeonDropdown && (
                  <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                    {surgeons
                      .filter(surgeon => {
                        const searchLower = (surgeonSearch || '').toLowerCase()
                        const fullName = `${surgeon.first_name} ${surgeon.surname}`.toLowerCase()
                        const reverseName = `${surgeon.surname} ${surgeon.first_name}`.toLowerCase()
                        return fullName.includes(searchLower) || reverseName.includes(searchLower)
                      })
                      .map((surgeon) => (
                        <div
                          key={surgeon._id}
                          onClick={() => {
                            const surgeonName = `${surgeon.first_name} ${surgeon.surname}`
                            updateField('team', 'primary_surgeon', surgeonName)
                            setSurgeonSearch('')
                            setShowSurgeonDropdown(false)
                          }}
                          className="px-3 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                        >
                          <div className="font-medium text-gray-900">
                            {surgeon.surname}, {surgeon.first_name}
                          </div>
                          {surgeon.gmc_number && (
                            <div className="text-xs text-gray-500">GMC: {surgeon.gmc_number}</div>
                          )}
                        </div>
                      ))}
                    {surgeons.filter(surgeon => {
                      const searchLower = (surgeonSearch || '').toLowerCase()
                      const fullName = `${surgeon.first_name} ${surgeon.surname}`.toLowerCase()
                      const reverseName = `${surgeon.surname} ${surgeon.first_name}`.toLowerCase()
                      return fullName.includes(searchLower) || reverseName.includes(searchLower)
                    }).length === 0 && (
                      <div className="px-3 py-2 text-sm text-gray-500">No surgeons found</div>
                    )}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Assistant Surgeons
                </label>
                <input
                  type="text"
                  value={(formData.team.assistant_surgeons || []).join(', ')}
                  onChange={(e) => handleArrayInput('team', 'assistant_surgeons', e.target.value)}
                  className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Comma-separated names"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Anesthesiologist
                  </label>
                  <input
                    type="text"
                    value={formData.team.anesthesiologist}
                    onChange={(e) => updateField('team', 'anesthesiologist', e.target.value)}
                    className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Scrub Nurse
                  </label>
                  <input
                    type="text"
                    value={formData.team.scrub_nurse}
                    onChange={(e) => updateField('team', 'scrub_nurse', e.target.value)}
                    className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Circulating Nurse
                  </label>
                  <input
                    type="text"
                    value={formData.team.circulating_nurse}
                    onChange={(e) => updateField('team', 'circulating_nurse', e.target.value)}
                    className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Intraoperative Details</h3>
            
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Anesthesia Type
                  </label>
                  <select
                    value={formData.intraoperative.anesthesia_type}
                    onChange={(e) => updateField('intraoperative', 'anesthesia_type', e.target.value)}
                    className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 appearance-none bg-white"
                  >
                    <option value="general">General</option>
                    <option value="regional">Regional</option>
                    <option value="local">Local</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Blood Loss (mL)
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={formData.intraoperative.blood_loss_ml || ''}
                    onChange={(e) => updateField('intraoperative', 'blood_loss_ml', e.target.value ? parseInt(e.target.value) : null)}
                    className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="Milliliters"
                  />
                </div>
              </div>

              <div className="flex items-center space-x-6">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.intraoperative.transfusion_required}
                    onChange={(e) => updateField('intraoperative', 'transfusion_required', e.target.checked)}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Transfusion Required</span>
                </label>

                {formData.intraoperative.transfusion_required && (
                  <div className="flex-1 max-w-xs">
                    <input
                      type="number"
                      min="0"
                      value={formData.intraoperative.units_transfused || ''}
                      onChange={(e) => updateField('intraoperative', 'units_transfused', e.target.value ? parseInt(e.target.value) : null)}
                      className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="Units transfused"
                    />
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Operative Findings
                </label>
                <textarea
                  value={formData.intraoperative.findings}
                  onChange={(e) => updateField('intraoperative', 'findings', e.target.value)}
                  rows={3}
                  className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Description of operative findings..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Specimens Sent
                </label>
                <input
                  type="text"
                  value={(formData.intraoperative.specimens_sent || []).join(', ')}
                  onChange={(e) => handleArrayInput('intraoperative', 'specimens_sent', e.target.value)}
                  className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Comma-separated specimen types"
                />
              </div>

              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.intraoperative.drains_placed}
                    onChange={(e) => updateField('intraoperative', 'drains_placed', e.target.checked)}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Drains Placed</span>
                </label>

                {formData.intraoperative.drains_placed && (
                  <input
                    type="text"
                    value={(formData.intraoperative.drain_types || []).join(', ')}
                    onChange={(e) => handleArrayInput('intraoperative', 'drain_types', e.target.value)}
                    className="w-full h-10 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="Comma-separated drain types"
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Step 5: Review */}
      {step === 5 && (
        <div className="space-y-6">
          <h3 className="text-lg font-semibold text-gray-900">Review & Submit</h3>
          
          <div className="bg-gray-50 rounded-lg p-4 space-y-4">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Basic Information</h4>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <dt className="text-gray-600">Surgery ID:</dt>
                <dd className="text-gray-900">{formData.surgery_id}</dd>
                <dt className="text-gray-600">Patient ID:</dt>
                <dd className="text-gray-900">{formData.patient_id}</dd>
              </dl>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-2">Classification</h4>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <dt className="text-gray-600">Urgency:</dt>
                <dd className="text-gray-900">{formData.classification.urgency}</dd>
                <dt className="text-gray-600">Primary Diagnosis:</dt>
                <dd className="text-gray-900 col-span-1">{formData.classification.primary_diagnosis}</dd>
              </dl>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-2">Procedure</h4>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <dt className="text-gray-600">Primary Procedure:</dt>
                <dd className="text-gray-900">{formData.procedure.primary_procedure}</dd>
                <dt className="text-gray-600">Approach:</dt>
                <dd className="text-gray-900">{formData.procedure.approach}</dd>
              </dl>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-2">Timeline</h4>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <dt className="text-gray-600">Surgery Date:</dt>
                <dd className="text-gray-900">{formData.perioperative_timeline.surgery_date}</dd>
                <dt className="text-gray-600">Primary Surgeon:</dt>
                <dd className="text-gray-900">{formData.team.primary_surgeon}</dd>
              </dl>
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              Please review all information carefully before submitting. You can edit this record later if needed.
            </p>
          </div>
        </div>
      )}

      {/* Navigation buttons */}
      <div className="flex justify-between pt-6 border-t">
        <div>
          {step > 1 && (
            <Button 
              type="button" 
              variant="secondary"
              onClick={() => setStep(step - 1)}
            >
              ← Previous
            </Button>
          )}
        </div>

        <div className="flex space-x-3">
          <Button 
            type="button" 
            variant="secondary"
            onClick={onCancel}
          >
            Cancel
          </Button>

          {step < totalSteps ? (
            <Button 
              type="button" 
              variant="primary"
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                console.log('Next clicked, current step:', step, 'moving to:', step + 1)
                setStep(step + 1)
              }}
            >
              Next →
            </Button>
          ) : (
            <Button 
              type="submit" 
              variant="primary"
            >
              {mode === 'create' ? 'Create Episode' : 'Update Episode'}
            </Button>
          )}
        </div>
      </div>
    </form>
  )
}
