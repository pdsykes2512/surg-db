import { useState, useEffect } from 'react'
import { SearchableSelect } from '../common/SearchableSelect'
import api from '../../services/api'

interface Patient {
  patient_id: string
  mrn?: string
  nhs_number: string
  demographics?: {
    date_of_birth?: string
  }
}

interface PatientSearchProps {
  value: string
  onChange: (patientId: string, patient?: Patient) => void
  label?: string
  required?: boolean
  placeholder?: string
  className?: string
}

export function PatientSearch({
  value,
  onChange,
  label = 'Patient',
  required = false,
  placeholder = 'Search by MRN or NHS number...',
  className = ''
}: PatientSearchProps) {
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(false)

  const formatNHSNumber = (nhsNumber: string | undefined) => {
    if (!nhsNumber) return '-'
    const digits = nhsNumber.replace(/\D/g, '')
    if (digits.length === 10) {
      return `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6)}`
    }
    return nhsNumber
  }

  // Fetch patients on mount
  useEffect(() => {
    const fetchPatients = async () => {
      console.log('[PatientSearch] Starting to fetch patients...')
      setLoading(true)
      try {
        // Fetch patients for searching (respecting the 100 result limit)
        const response = await api.get('/patients/?limit=100')
        console.log('[PatientSearch] API response:', response)
        console.log('[PatientSearch] Loaded patients:', response.data.length)
        console.log('[PatientSearch] First patient:', response.data[0])
        setPatients(response.data)
      } catch (error) {
        console.error('[PatientSearch] Error fetching patients:', error)
      } finally {
        setLoading(false)
        console.log('[PatientSearch] Loading complete')
      }
    }
    fetchPatients()
  }, [])

  // Convert patients to options format
  const options = patients.map(patient => ({
    value: patient.patient_id,
    label: patient.patient_id,
    patient: patient
  }))

  // Custom filter that searches by MRN or NHS number
  const filterOption = (opt: typeof options[0], search: string) => {
    const searchLower = search.toLowerCase().replace(/\s/g, '')
    const patientId = opt.patient.patient_id?.toLowerCase() || ''
    const mrn = opt.patient.mrn?.toLowerCase() || ''
    const nhsNumber = opt.patient.nhs_number?.toLowerCase().replace(/\s/g, '') || ''

    return patientId.includes(searchLower) || mrn.includes(searchLower) || nhsNumber.includes(searchLower)
  }

  return (
    <SearchableSelect
      value={value}
      onChange={(patientId) => {
        const patient = patients.find(p => p.patient_id === patientId)
        onChange(patientId, patient)
      }}
      options={options}
      getOptionValue={(opt) => opt.value}
      getOptionLabel={(opt) => opt.label}
      filterOption={filterOption}
      renderOption={(opt) => (
        <div>
          <div className="font-medium">MRN: {opt.patient.mrn || opt.patient.patient_id}</div>
          <div className="text-xs text-gray-500">NHS: {formatNHSNumber(opt.patient.nhs_number)}</div>
        </div>
      )}
      label={label}
      required={required}
      placeholder={placeholder}
      className={className}
      disabled={loading}
    />
  )
}
