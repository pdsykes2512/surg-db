/**
 * API Service Module
 * 
 * Centralized API client for communicating with the IMPACT backend.
 * Provides type-safe methods for all REST endpoints with automatic JWT authentication.
 * 
 * @module services/api
 * 
 * Features:
 * - Automatic JWT token injection via axios interceptors
 * - Centralized base URL configuration from environment variables
 * - Organized service methods by resource (patients, episodes, reports)
 * - Consistent error handling across all requests
 * 
 * @example
 * ```typescript
 * import { apiService } from './services/api'
 * 
 * // List patients with search
 * const { data } = await apiService.patients.list({ search: 'John' })
 * 
 * // Create new patient
 * const patient = await apiService.patients.create({ mrn: '12345678', ... })
 * ```
 */
import axios from 'axios'

/** Base URL for all API requests, from environment or defaults to localhost:8000 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

/**
 * Configured axios instance with authentication interceptor
 * Automatically adds JWT token from localStorage to all requests
 */
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Request interceptor to inject JWT authentication token
 * Retrieves token from localStorage and adds to Authorization header
 */
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/**
 * Centralized API service object with methods for all backend endpoints
 * Organized by resource type for easy discovery and maintenance
 */
export const apiService = {
  /**
   * Patient resource endpoints
   * Handles CRUD operations for patient records
   */
  patients: {
    /** List patients with pagination and optional search filter */
    list: (params?: any) => api.get('/patients/', { params }),
    /** Count total patients matching search criteria */
    count: (params?: any) => api.get('/patients/count', { params }),
    /** Get single patient by patient_id */
    get: (patientId: string) => api.get(`/patients/${patientId}`),
    /** Create new patient record */
    create: (data: any) => api.post('/patients/', data),
    /** Update existing patient by patient_id */
    update: (patientId: string, data: any) => api.put(`/patients/${patientId}`, data),
    /** Delete patient by patient_id (admin only) */
    delete: (patientId: string) => api.delete(`/patients/${patientId}`),
  },
  
  /**
   * Episode resource endpoints
   * Handles care episodes including tumours, treatments, and investigations
   */
  episodes: {
    /** List episodes with pagination and optional filters */
    list: (params?: any) => api.get('/episodes/', { params }),
    /** Count total episodes matching filter criteria */
    count: (params?: any) => api.get('/episodes/count', { params }),
    /** Get single episode by episode_id with all related data */
    get: (episodeId: string) => api.get(`/episodes/${episodeId}`),
    /** Create new cancer care episode */
    create: (data: any) => api.post('/episodes/', data),
    /** Update existing episode by episode_id */
    update: (episodeId: string, data: any) => api.put(`/episodes/${episodeId}`, data),
    /** Delete episode by episode_id (admin only) */
    delete: (episodeId: string) => api.delete(`/episodes/${episodeId}`),
  },
  
  /**
   * Reports and analytics endpoints
   * Provides aggregated statistics and performance metrics
   */
  reports: {
    /** Get overall system summary statistics */
    summary: () => api.get('/reports/summary'),
    /** Get complication rates and breakdown by type */
    complications: () => api.get('/reports/complications'),
    /** Get outcome trends over specified number of days */
    trends: (days?: number) => api.get('/reports/trends', { params: { days } }),
    /** Get surgeon performance comparison metrics */
    surgeonPerformance: () => api.get('/reports/surgeon-performance'),
  },
}

/**
 * Export both the structured service object and raw axios instance
 * 
 * @exports apiService - Structured service with organized endpoint methods
 * @exports default - Raw axios instance for custom requests
 */
export default api