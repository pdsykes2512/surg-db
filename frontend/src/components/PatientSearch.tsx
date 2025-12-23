import { useState, useEffect } from 'react'

interface Patient {
  record_number: string
  nhs_number: string
  demographics?: {
    date_of_birth?: string
  }
}

interface PatientSearchProps {
  value: string
  onChange: (mrn: string, patient?: Patient) => void
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
  const [searchTerm, setSearchTerm] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [loading, setLoading] = useState(false)

  // Fetch patients on mount
  useEffect(() => {
    const fetchPatients = async () => {
      setLoading(true)
      try {
        const response = await fetch('http://localhost:8000/api/patients/', {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        })
        if (response.ok) {
          setPatients(await response.json())
        }
      } catch (error) {
        console.error('Error fetching patients:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchPatients()
  }, [])

  // Filter patients based on search (by MRN or NHS number)
  const filteredPatients = patients.filter((p) => {
    const searchLower = searchTerm.toLowerCase()
    const mrn = p.record_number?.toLowerCase() || ''
    const nhsNumber = p.nhs_number?.toLowerCase().replace(/\s/g, '') || ''
    const searchNoSpaces = searchLower.replace(/\s/g, '')
    
    return mrn.includes(searchLower) || nhsNumber.includes(searchNoSpaces)
  })

  const handleSelect = (patient: Patient) => {
    onChange(patient.record_number, patient)
    setSearchTerm(patient.record_number)
    setShowDropdown(false)
  }

  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label} {required && <span className="text-red-500">*</span>}
        </label>
      )}
      <div className="relative">
        <input
          type="text"
          value={searchTerm || value}
          onChange={(e) => {
            setSearchTerm(e.target.value)
            setShowDropdown(true)
          }}
          onFocus={() => setShowDropdown(true)}
          onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder={placeholder}
          disabled={loading}
        />
        {showDropdown && filteredPatients.length > 0 && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
            {filteredPatients.map((patient) => (
              <div
                key={patient.record_number}
                onMouseDown={() => handleSelect(patient)}
                className="px-4 py-2 hover:bg-blue-50 cursor-pointer"
              >
                <div className="font-medium">MRN: {patient.record_number}</div>
                <div className="text-xs text-gray-500">NHS: {patient.nhs_number}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
