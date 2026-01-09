import { useState, useEffect } from 'react'
import api from '../services/api'

export interface Clinician {
  _id: string
  name?: string
  first_name?: string
  surname?: string
  role?: string
  specialty?: string
  gmc_number?: string
}

interface UseCliniciansReturn {
  clinicians: Clinician[]
  isLoading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

/**
 * Custom hook to fetch and manage clinicians list
 *
 * @returns {UseCliniciansReturn} Clinicians data, isLoading state, error, and refetch function
 *
 * @example
 * const { clinicians, isLoading, error, refetch } = useClinicians()
 *
 * if (isLoading) return <LoadingSpinner />
 * if (error) return <ErrorMessage error={error} />
 *
 * return (
 *   <SearchableSelect
 *     options={clinicians}
 *     getOptionValue={(c) => c._id}
 *     getOptionLabel={(c) => `${c.first_name} ${c.surname}`}
 *   />
 * )
 */
export function useClinicians(): UseCliniciansReturn {
  const [clinicians, setClinicians] = useState<Clinician[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const fetchClinicians = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await api.get('/clinicians/')
      setClinicians(response.data)
    } catch (err) {
      const error = err as Error
      setError(error)
      console.error('Error fetching clinicians:', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchClinicians()
  }, [])

  return {
    clinicians,
    isLoading,
    error,
    refetch: fetchClinicians
  }
}
