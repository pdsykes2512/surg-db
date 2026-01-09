import { useState, useEffect } from 'react'
import api from '../services/api'

export interface Patient {
  _id: string
  patient_id: string
  mrn?: string
  nhs_number?: string
  first_name: string
  last_name: string
  date_of_birth?: string
  gender?: string
  demographics?: {
    dob?: string
    gender?: string
    ethnicity?: string
    postcode?: string
  }
}

interface UsePatientsReturn {
  patients: Patient[]
  isLoading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

/**
 * Custom hook to fetch and manage patients list
 *
 * @returns {UsePatientsReturn} Patients data, loading state, error, and refetch function
 *
 * @example
 * const { patients, isLoading, error, refetch } = usePatients()
 *
 * if (isLoading) return <LoadingSpinner />
 * if (error) return <ErrorMessage error={error} />
 *
 * return (
 *   <div>
 *     {patients.map(patient => (
 *       <PatientCard key={patient.patient_id} patient={patient} />
 *     ))}
 *   </div>
 * )
 */
export function usePatients(): UsePatientsReturn {
  const [patients, setPatients] = useState<Patient[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const fetchPatients = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await api.get('/patients/')
      setPatients(response.data)
    } catch (err) {
      const error = err as Error
      setError(error)
      console.error('Error fetching patients:', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchPatients()
  }, [])

  return {
    patients,
    isLoading,
    error,
    refetch: fetchPatients
  }
}
