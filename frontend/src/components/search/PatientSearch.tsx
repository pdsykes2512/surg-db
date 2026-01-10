import { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import api from '../../services/api'
import { formatNHSNumber } from '../../utils/formatters'

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
  const [searchTerm, setSearchTerm] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0 })
  const inputRef = useRef<HTMLInputElement>(null)
  const initialPatientFetched = useRef(false)

  // Get the selected patient for display
  const selectedPatient = patients.find(p => p.patient_id === value)

  // Fetch initial patient if value is provided (e.g., when navigating from patient page)
  useEffect(() => {
    const fetchInitialPatient = async () => {
      if (value && !patients.find(p => p.patient_id === value) && !initialPatientFetched.current) {
        initialPatientFetched.current = true
        try {
          const response = await api.get(`/patients/${value}`)
          const patient = response.data
          setPatients([patient])
          // Trigger onChange to populate patient data in parent component
          onChange(value, patient)
        } catch (error) {
          console.error('Error fetching initial patient:', error)
          initialPatientFetched.current = false // Reset on error so we can retry
        }
      }
    }
    fetchInitialPatient()
  }, [value, onChange])

  // Fetch patients with server-side search (debounced)
  useEffect(() => {
    if (!isSearching) return

    const fetchPatients = async () => {
      setLoading(true)
      try {
        // Use server-side search with hash-based lookup for encrypted fields
        const searchParam = searchTerm ? `?search=${encodeURIComponent(searchTerm)}&limit=50` : '?limit=100'
        const response = await api.get(`/patients/${searchParam}`)
        setPatients(response.data)
      } catch (error) {
        console.error('Error fetching patients:', error)
      } finally {
        setLoading(false)
      }
    }

    // Debounce search to avoid too many API calls
    const timer = setTimeout(() => {
      fetchPatients()
    }, 300)

    return () => clearTimeout(timer)
  }, [searchTerm, isSearching])

  // Keep input focused after loading state changes
  useEffect(() => {
    if (isSearching && inputRef.current && document.activeElement !== inputRef.current) {
      inputRef.current.focus()
    }
  }, [loading, isSearching])

  // Update dropdown position when shown
  useEffect(() => {
    if (!showDropdown) return

    let rafId: number

    const updatePosition = () => {
      if (inputRef.current) {
        const rect = inputRef.current.getBoundingClientRect()
        setDropdownPosition({
          top: rect.bottom + 4,
          left: rect.left,
          width: rect.width
        })
      }
      rafId = requestAnimationFrame(updatePosition)
    }

    rafId = requestAnimationFrame(updatePosition)

    return () => {
      if (rafId) {
        cancelAnimationFrame(rafId)
      }
    }
  }, [showDropdown])

  const handleSelectPatient = (patient: Patient) => {
    onChange(patient.patient_id, patient)
    setSearchTerm('')
    setShowDropdown(false)
    setIsSearching(false)
  }

  const handleClear = () => {
    onChange('')
    setSearchTerm('')
    setShowDropdown(false)
    setIsSearching(false)
  }

  const handleStartSearch = () => {
    setIsSearching(true)
    setShowDropdown(true)
    setTimeout(() => inputRef.current?.focus(), 0)
  }

  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label} {required && <span className="text-red-500">*</span>}
        </label>
      )}

      <div className="relative">
        {/* Display selected patient or search input */}
        {value && selectedPatient && !isSearching ? (
          <div className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg bg-white">
            <div className="font-medium">MRN: {selectedPatient.mrn || selectedPatient.patient_id}</div>
            <div className="text-xs text-gray-500">NHS: {formatNHSNumber(selectedPatient.nhs_number)}</div>
          </div>
        ) : (
          <input
            ref={inputRef}
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onFocus={() => {
              setIsSearching(true)
              setShowDropdown(true)
            }}
            onBlur={() => {
              // Delay to allow click on dropdown items
              setTimeout(() => setShowDropdown(false), 200)
            }}
            className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder={placeholder}
          />
        )}

        {/* Clear/Edit button */}
        {value && (
          <button
            type="button"
            onMouseDown={(e) => {
              e.preventDefault()
              if (isSearching) {
                handleClear()
              } else {
                handleStartSearch()
              }
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            {isSearching ? (
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            )}
          </button>
        )}

        {/* Dropdown results */}
        {showDropdown && patients.length > 0 && createPortal(
          <div
            className="fixed z-[9999] bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto"
            style={{
              top: `${dropdownPosition.top}px`,
              left: `${dropdownPosition.left}px`,
              width: `${dropdownPosition.width}px`
            }}
          >
            {patients.map((patient, index) => (
              <div
                key={index}
                onMouseDown={() => handleSelectPatient(patient)}
                className="px-4 py-2 hover:bg-blue-50 cursor-pointer"
              >
                <div className="font-medium">MRN: {patient.mrn || patient.patient_id}</div>
                <div className="text-xs text-gray-500">NHS: {formatNHSNumber(patient.nhs_number)}</div>
              </div>
            ))}
          </div>,
          document.body
        )}

        {/* Loading indicator */}
        {loading && (
          <div className="absolute right-10 top-1/2 -translate-y-1/2">
            <svg className="animate-spin h-4 w-4 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
        )}
      </div>
    </div>
  )
}
