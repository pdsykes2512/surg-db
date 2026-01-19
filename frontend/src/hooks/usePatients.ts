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

export interface PaginationParams {
  page?: number
  limit?: number
  search?: string
}

interface UsePatientsReturn {
  patients: Patient[]
  isLoading: boolean
  error: Error | null
  refetch: (params?: PaginationParams) => Promise<void>
  pagination: {
    page: number
    limit: number
    total: number
    totalPages: number
  }
  setPage: (page: number) => void
  setLimit: (limit: number) => void
}

/**
 * Custom hook to fetch and manage patients list with pagination
 *
 * @param initialParams - Initial pagination parameters (page, limit, search)
 * @returns {UsePatientsReturn} Patients data, loading state, error, pagination info, and control functions
 *
 * @example
 * const { patients, isLoading, error, pagination, setPage, refetch } = usePatients()
 *
 * if (isLoading) return <LoadingSpinner />
 * if (error) return <ErrorMessage error={error} />
 *
 * return (
 *   <div>
 *     {patients.map(patient => (
 *       <PatientCard key={patient.patient_id} patient={patient} />
 *     ))}
 *     <Pagination
 *       currentPage={pagination.page}
 *       totalPages={pagination.totalPages}
 *       onPageChange={setPage}
 *     />
 *   </div>
 * )
 */
export function usePatients(initialParams?: PaginationParams): UsePatientsReturn {
  const [patients, setPatients] = useState<Patient[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [page, setPageState] = useState(initialParams?.page || 1)
  const [limit, setLimitState] = useState(initialParams?.limit || 50)
  const [total, setTotal] = useState(0)

  const fetchPatients = async (params?: PaginationParams) => {
    setIsLoading(true)
    setError(null)

    try {
      const currentPage = params?.page || page
      const currentLimit = params?.limit || limit
      const searchQuery = params?.search || ''

      const queryParams: Record<string, string | number> = {
        page: currentPage,
        limit: currentLimit
      }

      if (searchQuery) {
        queryParams.search = searchQuery
      }

      const response = await api.get('/patients/', { params: queryParams })

      // Backend should return { data: Patient[], total: number, page: number, limit: number }
      // For now, assume it returns an array directly (backward compatible)
      if (Array.isArray(response.data)) {
        setPatients(response.data)
        setTotal(response.data.length) // Fallback if no pagination metadata
      } else {
        setPatients(response.data.data || response.data.patients || [])
        setTotal(response.data.total || 0)
      }
    } catch (err) {
      const error = err as Error
      setError(error)
      console.error('Error fetching patients:', error)
      setPatients([])
      setTotal(0)
    } finally {
      setIsLoading(false)
    }
  }

  const setPage = (newPage: number) => {
    setPageState(newPage)
    fetchPatients({ page: newPage, limit })
  }

  const setLimit = (newLimit: number) => {
    setLimitState(newLimit)
    setPageState(1) // Reset to first page when changing limit
    fetchPatients({ page: 1, limit: newLimit })
  }

  useEffect(() => {
    fetchPatients(initialParams)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    patients,
    isLoading,
    error,
    refetch: fetchPatients,
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit)
    },
    setPage,
    setLimit
  }
}
