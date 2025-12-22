import { useState, useEffect } from 'react'
import { Button } from './Button'

interface EpisodeFormProps {
  onSubmit: (data: any) => void
  onCancel: () => void
  initialData?: any
  mode?: 'create' | 'edit'
}

// Generate unique surgery ID with hash-like format
const generateSurgeryId = () => {
  const timestamp = Date.now().toString(36)
  const randomStr = Math.random().toString(36).substring(2, 8)
  return `SUR-${timestamp}-${randomStr}`.toUpperCase()
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
        const response = await fetch('http://localhost:8000/api/patients', {
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
        const response = await fetch('http://localhost:8000/api/admin/surgeons', {
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
      category: 'other',
      complexity: 'routine',
      primary_diagnosis: '',
      indication: ''
    },
    procedure: {
      primary_procedure: '',
      additional_procedures: [],
      cpt_codes: [],
      icd10_codes: [],
      opcs_codes: [],
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

  // Auto-generate surgery ID when creating new episode
  useEffect(() => {
    if (mode === 'create' && !initialData?.surgery_id) {
      updateSimpleField('surgery_id', generateSurgeryId())
    }
  }, [])

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

  // Standard procedure list with ICD-10-PCS and OPCS-4 codes
  const procedureToICD10: Record<string, string[]> = {
    'Oesophagectomy (Ivor Lewis)': ['0DT50ZZ', '0DT54ZZ'],
    'Oesophagectomy (Transhiatal)': ['0DT50ZZ', '0DT54ZZ'],
    'Oesophagectomy (McKeown Three-Stage)': ['0DT50ZZ', '0DT54ZZ'],
    'Oesophagogastrectomy': ['0DT50ZZ', '0DT60ZZ'],
    'Total Gastrectomy': ['0DT60ZZ', '0DT64ZZ'],
    'Partial Gastrectomy': ['0DB60ZZ', '0DB64ZZ'],
    'Subtotal Gastrectomy': ['0DB60ZZ', '0DB64ZZ'],
    'Sleeve Gastrectomy': ['0DB64Z3', '0DB60Z3'],
    'Gastric Bypass (Roux-en-Y)': ['0D160ZA', '0D164ZA'],
    'Gastrojejunostomy': ['0D160ZA', '0D164ZA'],
    'Vagotomy (Truncal)': ['0D8X0ZZ', '0D8X4ZZ'],
    'Vagotomy (Selective)': ['0D8X0ZZ', '0D8X4ZZ'],
    'Fundoplication (Nissen)': ['0DU64JZ', '0DU60JZ'],
    'Fundoplication (Toupet)': ['0DU64JZ', '0DU60JZ'],
    'Fundoplication (Dor)': ['0DU64JZ', '0DU60JZ'],
    'Pyloroplasty': ['0D970ZZ', '0D974ZZ'],
    'Gastrostomy (PEG)': ['0DH60UZ', '0DH63UZ'],
    'Hiatal Hernia Repair': ['0DU64JZ', '0DU60JZ'],
    'Paraoesophageal Hernia Repair': ['0DU64JZ', '0DU60JZ'],
    'Whipple Procedure (Pancreaticoduodenectomy)': ['0FTG0ZZ', '0FT90ZZ', '0DT90ZZ'],
    'Distal Pancreatectomy': ['0FTG0ZZ', '0FTG4ZZ'],
    'Splenectomy': ['07TP0ZZ', '07TP4ZZ'],
    'Cholecystectomy': ['0FT40ZZ', '0FT44ZZ'],
    'Common Bile Duct Exploration': ['0F9C0ZZ', '0F9C4ZZ'],
    'Hepatectomy (Right)': ['0FT00ZZ', '0FT04ZZ'],
    'Hepatectomy (Left)': ['0FT10ZZ', '0FT14ZZ'],
    'Hepatectomy (Partial/Wedge)': ['0FTB0ZZ', '0FTB4ZZ'],
    'Liver Resection (Segmentectomy)': ['0FTB0ZZ', '0FTB4ZZ'],
    'Appendicectomy': ['0DTJ0ZZ', '0DTJ4ZZ'],
    'Right Hemicolectomy': ['0DTF0ZZ', '0DTF4ZZ'],
    'Extended Right Hemicolectomy': ['0DTF0ZZ', '0DTE0ZZ'],
    'Left Hemicolectomy': ['0DTG0ZZ', '0DTG4ZZ'],
    'Sigmoid Colectomy': ['0DTN0ZZ', '0DTN4ZZ'],
    'Transverse Colectomy': ['0DTL0ZZ', '0DTL4ZZ'],
    'Total Colectomy': ['0DTE0ZZ', '0DTE4ZZ'],
    'Total Colectomy with Ileorectal Anastomosis': ['0DTE0ZZ', '0D1E0ZA'],
    'Proctocolectomy with Ileostomy': ['0DTE0ZZ', '0DTP0ZZ'],
    'Proctocolectomy with IPAA (J-Pouch)': ['0DTE0ZZ', '0D1E0ZC'],
    'Anterior Resection': ['0DTP0ZZ', '0DTP4ZZ'],
    'Low Anterior Resection': ['0DTP0ZZ', '0DTP4ZZ'],
    'Ultra-Low Anterior Resection': ['0DTP0ZZ', '0DTP4ZZ'],
    'Abdominoperineal Resection (APR)': ['0DTQ0ZZ', '0DTQ4ZZ'],
    'Hartmann\'s Procedure': ['0DTN0ZZ', '0D1N0Z4'],
    'Hartmann\'s Reversal': ['0D1N0ZA', '0D1N4ZA'],
    'Ileostomy Formation (End)': ['0D1B0Z4', '0D1B4Z4'],
    'Ileostomy Formation (Loop)': ['0D1B0Z4', '0D1B4Z4'],
    'Colostomy Formation (End)': ['0D1L0Z4', '0D1N0Z4'],
    'Colostomy Formation (Loop)': ['0D1L0Z4', '0D1N0Z4'],
    'Stoma Reversal': ['0DQB0ZZ', '0DQN0ZZ'],
    'Small Bowel Resection': ['0DTB0ZZ', '0DTB4ZZ'],
    'Stricturoplasty': ['0D8B0ZZ', '0D8B4ZZ'],
    'Adhesiolysis': ['0DN80ZZ', '0DN84ZZ'],
    'Haemorrhoidectomy': ['0DBQ0ZZ', '0DBQ4ZZ'],
    'Stapled Haemorrhoidopexy (PPH)': ['0DUQ0ZZ', '0DUQ4ZZ'],
    'Lateral Internal Sphincterotomy': ['0D8R0ZZ', '0D8R4ZZ'],
    'Fistulotomy': ['0D9Q0ZZ', '0D9Q4ZZ'],
    'Fistula Repair (Advancement Flap)': ['0DUQ0ZZ', '0DUQ4ZZ'],
    'Seton Placement': ['0DHQ0ZZ', '0DHQ4ZZ'],
    'Pilonidal Sinus Excision': ['0HBU0ZZ', '0HBU4ZZ'],
    'Perianal Abscess Drainage': ['0D9Q0ZZ', '0D9Q4ZZ'],
    'Rectal Prolapse Repair (Perineal)': ['0DSQ0ZZ', '0DSQ4ZZ'],
    'Rectopexy (Ventral Mesh)': ['0DSP0ZZ', '0DSP4ZZ'],
    'Rectopexy (Laparoscopic Suture)': ['0DSP4ZZ', '0DSP0ZZ'],
    'STARR Procedure': ['0DBP0ZZ', '0DBP4ZZ'],
    'Inguinal Hernia Repair (Open)': ['0YU60JZ', '0YU50JZ'],
    'Inguinal Hernia Repair (Laparoscopic TEP)': ['0YU64JZ', '0YU54JZ'],
    'Inguinal Hernia Repair (Laparoscopic TAPP)': ['0YU64JZ', '0YU54JZ'],
    'Femoral Hernia Repair': ['0YU60JZ', '0YU64JZ'],
    'Incisional Hernia Repair': ['0WUF0JZ', '0WUF4JZ'],
    'Umbilical Hernia Repair': ['0WU90JZ', '0WU94JZ'],
    'Paraumbilical Hernia Repair': ['0WU90JZ', '0WU94JZ'],
    'Epigastric Hernia Repair': ['0WUF0JZ', '0WUF4JZ'],
    'Ventral Hernia Repair': ['0WUF0JZ', '0WUF4JZ'],
    'Spigelian Hernia Repair': ['0WUF0JZ', '0WUF4JZ'],
    'Component Separation (Anterior)': ['0KUM0JZ', '0KUM4JZ'],
    'Component Separation (Posterior - TAR)': ['0KUM0JZ', '0KUM4JZ']
  }

  const procedureToOPCS: Record<string, string[]> = {
    'Oesophagectomy (Ivor Lewis)': ['G01.1', 'G01.8'],
    'Oesophagectomy (Transhiatal)': ['G01.1', 'G01.8'],
    'Oesophagectomy (McKeown Three-Stage)': ['G01.1', 'G01.8'],
    'Oesophagogastrectomy': ['G01.2', 'G02.1'],
    'Total Gastrectomy': ['G02.1', 'G02.8'],
    'Partial Gastrectomy': ['G02.2', 'G02.3'],
    'Subtotal Gastrectomy': ['G02.2', 'G02.3'],
    'Sleeve Gastrectomy': ['G28.2', 'G27.2'],
    'Gastric Bypass (Roux-en-Y)': ['G28.1', 'G27.1'],
    'Gastrojejunostomy': ['G10.2', 'G10.8'],
    'Vagotomy (Truncal)': ['G41.1', 'G41.8'],
    'Vagotomy (Selective)': ['G41.2', 'G41.3'],
    'Fundoplication (Nissen)': ['G17.1', 'G17.8'],
    'Fundoplication (Toupet)': ['G17.1', 'G17.8'],
    'Fundoplication (Dor)': ['G17.1', 'G17.8'],
    'Pyloroplasty': ['G08.1', 'G08.8'],
    'Gastrostomy (PEG)': ['G43.1', 'G43.8'],
    'Hiatal Hernia Repair': ['G17.1', 'G17.8'],
    'Paraoesophageal Hernia Repair': ['G17.1', 'G17.8'],
    'Whipple Procedure (Pancreaticoduodenectomy)': ['J03.1', 'J03.2'],
    'Distal Pancreatectomy': ['J03.3', 'J03.5'],
    'Splenectomy': ['T86.1', 'T86.2'],
    'Cholecystectomy': ['J18.1', 'J18.5'],
    'Common Bile Duct Exploration': ['J15.1', 'J15.8'],
    'Hepatectomy (Right)': ['J02.1', 'J02.5'],
    'Hepatectomy (Left)': ['J02.2', 'J02.5'],
    'Hepatectomy (Partial/Wedge)': ['J02.8', 'J02.9'],
    'Liver Resection (Segmentectomy)': ['J02.3', 'J02.4'],
    'Appendicectomy': ['H01.1', 'H01.8'],
    'Right Hemicolectomy': ['H05.1', 'H05.2'],
    'Extended Right Hemicolectomy': ['H04.1', 'H05.1'],
    'Left Hemicolectomy': ['H06.1', 'H06.2'],
    'Sigmoid Colectomy': ['H08.1', 'H08.2'],
    'Transverse Colectomy': ['H07.1', 'H07.2'],
    'Total Colectomy': ['H04.1', 'H04.2'],
    'Total Colectomy with Ileorectal Anastomosis': ['H04.1', 'H10.2'],
    'Proctocolectomy with Ileostomy': ['H04.3', 'H04.8'],
    'Proctocolectomy with IPAA (J-Pouch)': ['H04.4', 'H04.5'],
    'Anterior Resection': ['H33.1', 'H33.2'],
    'Low Anterior Resection': ['H33.3', 'H33.4'],
    'Ultra-Low Anterior Resection': ['H33.5', 'H33.6'],
    'Abdominoperineal Resection (APR)': ['H33.8', 'H33.9'],
    'Hartmann\'s Procedure': ['H08.3', 'H08.4'],
    'Hartmann\'s Reversal': ['G62.1', 'G69.1'],
    'Ileostomy Formation (End)': ['G69.1', 'G69.2'],
    'Ileostomy Formation (Loop)': ['G69.3', 'G69.4'],
    'Colostomy Formation (End)': ['G62.1', 'G62.2'],
    'Colostomy Formation (Loop)': ['G62.3', 'G62.4'],
    'Stoma Reversal': ['G64.1', 'G71.1'],
    'Small Bowel Resection': ['G63.1', 'G63.8'],
    'Stricturoplasty': ['G61.1', 'G61.8'],
    'Adhesiolysis': ['T93.1', 'T93.8'],
    'Haemorrhoidectomy': ['H51.1', 'H51.8'],
    'Stapled Haemorrhoidopexy (PPH)': ['H51.2', 'H51.9'],
    'Lateral Internal Sphincterotomy': ['H52.1', 'H52.8'],
    'Fistulotomy': ['H53.1', 'H53.2'],
    'Fistula Repair (Advancement Flap)': ['H56.1', 'H56.8'],
    'Seton Placement': ['H59.1', 'H59.8'],
    'Pilonidal Sinus Excision': ['S56.1', 'S56.8'],
    'Perianal Abscess Drainage': ['H54.1', 'H54.8'],
    'Rectal Prolapse Repair (Perineal)': ['H42.1', 'H42.2'],
    'Rectopexy (Ventral Mesh)': ['H41.1', 'H41.8'],
    'Rectopexy (Laparoscopic Suture)': ['H41.2', 'H41.9'],
    'STARR Procedure': ['H33.7', 'H35.8'],
    'Inguinal Hernia Repair (Open)': ['T20.1', 'T20.2'],
    'Inguinal Hernia Repair (Laparoscopic TEP)': ['T20.3', 'T20.4'],
    'Inguinal Hernia Repair (Laparoscopic TAPP)': ['T20.5', 'T20.8'],
    'Femoral Hernia Repair': ['T21.1', 'T21.2'],
    'Incisional Hernia Repair': ['T27.1', 'T27.2'],
    'Umbilical Hernia Repair': ['T22.1', 'T22.2'],
    'Paraumbilical Hernia Repair': ['T22.3', 'T22.4'],
    'Epigastric Hernia Repair': ['T23.1', 'T23.2'],
    'Ventral Hernia Repair': ['T27.3', 'T27.4'],
    'Spigelian Hernia Repair': ['T27.8', 'T27.9'],
    'Component Separation (Anterior)': ['T28.1', 'T28.2'],
    'Component Separation (Posterior - TAR)': ['T28.3', 'T28.4']
  }

  // Common diagnoses for GI surgery
  const commonDiagnoses = {
    malignant: [
      'Colorectal Carcinoma',
      'Rectal Carcinoma',
      'Sigmoid Carcinoma',
      'Caecal Carcinoma',
      'Oesophageal Carcinoma',
      'Gastric Carcinoma',
      'Pancreatic Carcinoma',
      'Hepatocellular Carcinoma',
      'Cholangiocarcinoma',
      'Small Bowel Tumour',
      'Appendiceal Tumour',
      'Carcinoid Tumour',
      'GIST (Gastrointestinal Stromal Tumour)',
      'Metastatic Disease to Liver',
      'Peritoneal Carcinomatosis'
    ],
    inflammatory: [
      'Crohn\'s Disease',
      'Ulcerative Colitis',
      'Diverticulitis',
      'Diverticular Disease',
      'Acute Appendicitis',
      'Perforated Appendicitis',
      'Perianal Sepsis',
      'Perianal Abscess',
      'Perianal Fistula',
      'Anal Fissure',
      'Pilonidal Sinus',
      'Cholecystitis (Acute)',
      'Cholecystitis (Chronic)',
      'Pancreatitis (Chronic)',
      'Ischaemic Colitis'
    ],
    benign: [
      'Haemorrhoids',
      'Rectal Prolapse',
      'Gallstones (Cholelithiasis)',
      'Common Bile Duct Stones (Choledocholithiasis)',
      'Gastro-Oesophageal Reflux Disease (GORD)',
      'Hiatus Hernia',
      'Paraoesophageal Hernia',
      'Peptic Ulcer Disease',
      'Gastric Ulcer (Perforated)',
      'Duodenal Ulcer (Perforated)',
      'Bowel Obstruction',
      'Small Bowel Obstruction',
      'Large Bowel Obstruction',
      'Adhesional Obstruction',
      'Sigmoid Volvulus',
      'Caecal Volvulus',
      'Intestinal Perforation',
      'Colonic Perforation',
      'Faecal Impaction',
      'Rectal Bleeding',
      'Lower GI Bleeding'
    ],
    hernia: [
      'Inguinal Hernia',
      'Femoral Hernia',
      'Umbilical Hernia',
      'Paraumbilical Hernia',
      'Epigastric Hernia',
      'Incisional Hernia',
      'Ventral Hernia',
      'Spigelian Hernia',
      'Strangulated Hernia',
      'Obstructed Hernia'
    ],
    other: [
      'Morbid Obesity',
      'Achalasia',
      'Barrett\'s Oesophagus',
      'Oesophageal Stricture',
      'Gastric Outlet Obstruction',
      'Splenic Injury/Rupture',
      'Mesenteric Ischaemia',
      'Intestinal Ischaemia',
      'Anastomotic Leak',
      'Stoma Complications',
      'Ventral Hernia',
      'Enterocutaneous Fistula'
    ]
  }

  const standardProcedures = {
    upperGI: [
      'Oesophagectomy (Ivor Lewis)',
      'Oesophagectomy (Transhiatal)',
      'Oesophagectomy (McKeown Three-Stage)',
      'Oesophagogastrectomy',
      'Total Gastrectomy',
      'Partial Gastrectomy',
      'Subtotal Gastrectomy',
      'Sleeve Gastrectomy',
      'Gastric Bypass (Roux-en-Y)',
      'Gastrojejunostomy',
      'Vagotomy (Truncal)',
      'Vagotomy (Selective)',
      'Fundoplication (Nissen)',
      'Fundoplication (Toupet)',
      'Fundoplication (Dor)',
      'Pyloroplasty',
      'Gastrostomy (PEG)',
      'Hiatal Hernia Repair',
      'Paraoesophageal Hernia Repair',
      'Whipple Procedure (Pancreaticoduodenectomy)',
      'Distal Pancreatectomy',
      'Splenectomy',
      'Cholecystectomy',
      'Common Bile Duct Exploration',
      'Hepatectomy (Right)',
      'Hepatectomy (Left)',
      'Hepatectomy (Partial/Wedge)',
      'Liver Resection (Segmentectomy)'
    ],
    lowerGI: [
      'Appendicectomy',
      'Right Hemicolectomy',
      'Extended Right Hemicolectomy',
      'Left Hemicolectomy',
      'Sigmoid Colectomy',
      'Transverse Colectomy',
      'Total Colectomy',
      'Total Colectomy with Ileorectal Anastomosis',
      'Proctocolectomy with Ileostomy',
      'Proctocolectomy with IPAA (J-Pouch)',
      'Anterior Resection',
      'Low Anterior Resection',
      'Ultra-Low Anterior Resection',
      'Abdominoperineal Resection (APR)',
      'Hartmann\'s Procedure',
      'Hartmann\'s Reversal',
      'Ileostomy Formation (End)',
      'Ileostomy Formation (Loop)',
      'Colostomy Formation (End)',
      'Colostomy Formation (Loop)',
      'Stoma Reversal',
      'Small Bowel Resection',
      'Stricturoplasty',
      'Adhesiolysis',
      'Haemorrhoidectomy',
      'Stapled Haemorrhoidopexy (PPH)',
      'Lateral Internal Sphincterotomy',
      'Fistulotomy',
      'Fistula Repair (Advancement Flap)',
      'Seton Placement',
      'Pilonidal Sinus Excision',
      'Perianal Abscess Drainage',
      'Rectal Prolapse Repair (Perineal)',
      'Rectopexy (Ventral Mesh)',
      'Rectopexy (Laparoscopic Suture)',
      'STARR Procedure'
    ],
    hernia: [
      'Inguinal Hernia Repair (Open)',
      'Inguinal Hernia Repair (Laparoscopic TEP)',
      'Inguinal Hernia Repair (Laparoscopic TAPP)',
      'Femoral Hernia Repair',
      'Incisional Hernia Repair',
      'Umbilical Hernia Repair',
      'Paraumbilical Hernia Repair',
      'Epigastric Hernia Repair',
      'Ventral Hernia Repair',
      'Spigelian Hernia Repair',
      'Component Separation (Anterior)',
      'Component Separation (Posterior - TAR)'
    ]
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Progress indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Step {step} of {totalSteps}</span>
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
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Search by record number or NHS number..."
                />

                {showPatientDropdown && (() => {
                  const searchLower = patientSearch.toLowerCase()
                  const filtered = patients.filter((patient: any) => {
                    const recordMatch = patient.record_number?.toLowerCase().includes(searchLower)
                    const nhsMatch = patient.nhs_number?.replace(/\s/g, '').toLowerCase().includes(searchLower.replace(/\s/g, ''))
                    return recordMatch || nhsMatch || !searchLower
                  }).slice(0, 20) // Limit to 20 results

                  return filtered.length > 0 ? (
                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                      {filtered.map((patient: any) => (
                        <div
                          key={patient.record_number}
                          onClick={() => {
                            updateSimpleField('patient_id', patient.record_number)
                            setPatientSearch('')
                            setShowPatientDropdown(false)
                          }}
                          className="px-3 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                        >
                          <div className="font-medium text-gray-900">
                            {patient.first_name} {patient.last_name}
                          </div>
                          <div className="text-xs text-gray-500">
                            MRN: {patient.record_number} | NHS: {patient.nhs_number || 'N/A'}
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                            // Auto-populate ICD-10 and OPCS codes
                            const icd10Codes = procedureToICD10[proc] || []
                            const opcsCodes = procedureToOPCS[proc] || []
                            updateField('procedure', 'icd10_codes', icd10Codes)
                            updateField('procedure', 'opcs_codes', opcsCodes)
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
                    placeholder="Auto-populated"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Automatically populated from procedure
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    OPCS-4 Codes
                  </label>
                  <input
                    type="text"
                    value={(formData.procedure.opcs_codes || []).join(', ')}
                    readOnly
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
                    placeholder="Auto-populated"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    NHS procedural classification codes
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
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Admission Date <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                required
                value={formData.perioperative_timeline.admission_date}
                onChange={(e) => updateField('perioperative_timeline', 'admission_date', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Surgery Date <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                required
                value={formData.perioperative_timeline.surgery_date}
                onChange={(e) => updateField('perioperative_timeline', 'surgery_date', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">Date and time when surgery ends</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Discharge Date
              </label>
              <input
                type="date"
                value={formData.perioperative_timeline.discharge_date}
                onChange={(e) => updateField('perioperative_timeline', 'discharge_date', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
                <dt className="text-gray-600">Category:</dt>
                <dd className="text-gray-900">{formData.classification.category}</dd>
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
              onClick={() => setStep(step + 1)}
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
