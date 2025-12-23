/**
 * API service for communicating with backend
 */
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const apiService = {
  // Patients
  patients: {
    list: () => api.get('/patients/'),
    get: (patientId: string) => api.get(`/patients/${patientId}`),
    create: (data: any) => api.post('/patients/', data),
    update: (patientId: string, data: any) => api.put(`/patients/${patientId}`, data),
    delete: (patientId: string) => api.delete(`/patients/${patientId}`),
  },
  
  // Episodes
  episodes: {
    list: (params?: any) => api.get('/episodes/', { params }),
    get: (episodeId: string) => api.get(`/episodes/${episodeId}`),
    create: (data: any) => api.post('/episodes/', data),
    update: (episodeId: string, data: any) => api.put(`/episodes/${episodeId}`, data),
    delete: (episodeId: string) => api.delete(`/episodes/${episodeId}`),
  },
  
  // Reports
  reports: {
    summary: () => api.get('/reports/summary'),
    complications: () => api.get('/reports/complications'),
    trends: (days?: number) => api.get('/reports/trends', { params: { days } }),
    surgeonPerformance: () => api.get('/reports/surgeon-performance'),
  },
}

// Export both the service object and raw axios instance
export default api