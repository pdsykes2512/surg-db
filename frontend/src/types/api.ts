/**
 * API Request/Response Type Definitions
 *
 * Types for API endpoint parameters, request bodies, and response formats
 */

import type {
  Patient,
  Episode,
  Treatment,
  Tumour,
  Investigation,
  FollowUp,
  Clinician,
  User,
  BackupInfo,
  AuditLog,
  YearlyMetrics,
  AuthToken
} from './models'

// ============================================================================
// Generic API Types
// ============================================================================

export interface ApiListParams {
  skip?: number
  limit?: number
  search?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface ApiCountResponse {
  count: number
}

export interface ApiError {
  error: {
    code: string
    message: string
    field?: string
    details?: Record<string, unknown>
  }
}

// ============================================================================
// Patient API Types
// ============================================================================

export interface PatientListParams extends ApiListParams {
  // Add patient-specific filters here if needed
}

export type PatientListResponse = Patient[]

export interface PatientCreateRequest {
  patient_id?: string  // Auto-generated if not provided
  nhs_number?: string
  mrn?: string
  hospital_number?: string
  demographics?: Patient['demographics']
  contact?: Patient['contact']
}

export interface PatientUpdateRequest {
  nhs_number?: string
  mrn?: string
  hospital_number?: string
  demographics?: Patient['demographics']
  contact?: Patient['contact']
}

export type PatientResponse = Patient

// ============================================================================
// Episode API Types
// ============================================================================

export interface EpisodeListParams extends ApiListParams {
  patient_id?: string
  condition_type?: string
  cancer_type?: string
  start_date?: string
  end_date?: string
}

export type EpisodeListResponse = Episode[]

export interface EpisodeCreateRequest {
  episode_id?: string
  patient_id: string
  condition_type: Episode['condition_type']
  cancer_type?: Episode['cancer_type']
  cancer_data?: Episode['cancer_data']
  referral_date?: string
  first_seen_date?: string
  diagnosis_date?: string
  lead_clinician?: string
  referring_hospital?: string
  notes?: string
}

export interface EpisodeUpdateRequest {
  condition_type?: Episode['condition_type']
  cancer_type?: Episode['cancer_type']
  cancer_data?: Episode['cancer_data']
  referral_date?: string
  first_seen_date?: string
  diagnosis_date?: string
  lead_clinician?: string
  referring_hospital?: string
  notes?: string
}

export type EpisodeResponse = Episode

// ============================================================================
// Treatment API Types
// ============================================================================

export interface TreatmentListParams extends ApiListParams {
  episode_id?: string
  patient_id?: string
  surgeon?: string
  start_date?: string
  end_date?: string
}

export type TreatmentListResponse = Treatment[]

export interface TreatmentCreateRequest {
  treatment_id?: string
  episode_id: string
  patient_id: string
  treatment_date?: string
  admission_date?: string
  discharge_date?: string
  team?: Treatment['team']
  procedure_name?: string
  opcs4_code?: string
  intent?: Treatment['intent']
  urgency?: Treatment['urgency']
  approach?: Treatment['approach']
  asa_grade?: string
  complications?: Treatment['complications']
  return_to_theatre?: boolean
  return_to_theatre_date?: string
  escalation_of_care?: boolean
  mortality_30d?: boolean
  mortality_90d?: boolean
  mortality_1y?: boolean
  readmission_30d?: boolean
  length_of_stay?: number
  itu_admission?: boolean
  itu_los_days?: number
  vitals?: Treatment['vitals']
  notes?: string
}

export interface TreatmentUpdateRequest {
  treatment_date?: string
  admission_date?: string
  discharge_date?: string
  team?: Treatment['team']
  procedure_name?: string
  opcs4_code?: string
  intent?: Treatment['intent']
  urgency?: Treatment['urgency']
  approach?: Treatment['approach']
  asa_grade?: string
  complications?: Treatment['complications']
  return_to_theatre?: boolean
  return_to_theatre_date?: string
  escalation_of_care?: boolean
  mortality_30d?: boolean
  mortality_90d?: boolean
  mortality_1y?: boolean
  readmission_30d?: boolean
  length_of_stay?: number
  itu_admission?: boolean
  itu_los_days?: number
  vitals?: Treatment['vitals']
  notes?: string
}

export type TreatmentResponse = Treatment

// ============================================================================
// Tumour API Types
// ============================================================================

export interface TumourCreateRequest {
  tumour_id?: string
  episode_id: string
  site?: string
  laterality?: Tumour['laterality']
  histology?: string
  grade?: string
  diagnosis_date?: string
  t_stage?: string
  n_stage?: string
  m_stage?: string
  overall_stage?: string
  tumour_size_mm?: number
  lymph_nodes_examined?: number
  lymph_nodes_positive?: number
  resection_margins?: Tumour['resection_margins']
  notes?: string
}

export interface TumourUpdateRequest extends Omit<TumourCreateRequest, 'tumour_id' | 'episode_id'> {}

export type TumourResponse = Tumour

// ============================================================================
// Investigation API Types
// ============================================================================

export interface InvestigationCreateRequest {
  investigation_id?: string
  episode_id: string
  investigation_type: Investigation['investigation_type']
  investigation_date?: string
  findings?: string
  imaging_findings?: string
  pathology_findings?: string
  recommendations?: string
  notes?: string
}

export interface InvestigationUpdateRequest extends Omit<InvestigationCreateRequest, 'investigation_id' | 'episode_id'> {}

export type InvestigationResponse = Investigation

// ============================================================================
// Follow-up API Types
// ============================================================================

export interface FollowUpCreateRequest {
  followup_id?: string
  episode_id: string
  followup_date?: string
  clinician?: string
  status?: FollowUp['status']
  recurrence?: boolean
  recurrence_date?: string
  recurrence_site?: string
  notes?: string
}

export interface FollowUpUpdateRequest extends Omit<FollowUpCreateRequest, 'followup_id' | 'episode_id'> {}

export type FollowUpResponse = FollowUp

// ============================================================================
// Clinician API Types
// ============================================================================

export interface ClinicianCreateRequest {
  surname: string
  first_name: string
  title?: string
  specialty?: string
  grade?: string
  gmc_number?: string
  email?: string
  active?: boolean
}

export interface ClinicianUpdateRequest extends Partial<ClinicianCreateRequest> {}

export type ClinicianListResponse = Clinician[]
export type ClinicianResponse = Clinician

// ============================================================================
// Auth API Types
// ============================================================================

export interface LoginRequest {
  username: string
  password: string
}

export type LoginResponse = AuthToken

export interface UserCreateRequest {
  username: string
  password: string
  email?: string
  full_name?: string
  role: User['role']
  active?: boolean
}

export interface UserUpdateRequest {
  email?: string
  full_name?: string
  role?: User['role']
  active?: boolean
  password?: string
}

export type UserListResponse = User[]
export type UserResponse = User

// ============================================================================
// Reports API Types
// ============================================================================

export type SummaryReportResponse = YearlyMetrics

export interface SurgeonPerformanceParams {
  surgeon?: string
  start_date?: string
  end_date?: string
}

// ============================================================================
// Backup API Types
// ============================================================================

export interface BackupCreateRequest {
  notes?: string
  type?: 'manual' | 'daily' | 'weekly' | 'monthly'
}

export interface BackupRestoreRequest {
  filename: string
  confirm?: boolean
}

export type BackupListResponse = BackupInfo[]
export type BackupResponse = BackupInfo

// ============================================================================
// Audit API Types
// ============================================================================

export interface AuditLogParams extends ApiListParams {
  user_id?: string
  entity_type?: string
  entity_id?: string
  action?: string
  start_date?: string
  end_date?: string
}

export type AuditLogListResponse = AuditLog[]

// ============================================================================
// Export API Types
// ============================================================================

export interface ExportParams {
  format?: 'excel' | 'csv' | 'json'
  start_date?: string
  end_date?: string
  surgeon?: string
  condition_type?: string
}

// ============================================================================
// Code Validation API Types
// ============================================================================

export interface ICD10Code {
  code: string
  description: string
  valid: boolean
}

export interface OPCS4Code {
  code: string
  description: string
  valid: boolean
}

export interface CodeValidationResponse {
  valid: boolean
  code: string
  description?: string
  suggestions?: string[]
}

// ============================================================================
// NHS Provider API Types
// ============================================================================

export interface NHSProvider {
  code: string
  name: string
  type: string
  address?: {
    line1?: string
    line2?: string
    line3?: string
    city?: string
    county?: string
    postcode?: string
  }
  phone?: string
  website?: string
}

export interface NHSProviderSearchParams {
  query: string
  type?: string
  limit?: number
}

export type NHSProviderListResponse = NHSProvider[]
