/**
 * Domain Model Type Definitions
 *
 * These types match the Pydantic models defined in backend/app/models/
 * and provide type safety for medical data throughout the frontend.
 */

// ============================================================================
// Patient Models
// ============================================================================

export interface PatientDemographics {
  first_name?: string
  last_name?: string
  date_of_birth?: string  // ISO date string
  age?: number
  sex?: 'M' | 'F' | 'Other' | 'Unknown'
  ethnicity?: string
  postcode?: string
  deceased?: boolean
  deceased_date?: string  // ISO date string
}

export interface ContactInfo {
  phone?: string
  email?: string
  address?: string
  postcode?: string
  next_of_kin?: string
  next_of_kin_phone?: string
}

export interface Patient {
  _id?: string
  patient_id: string
  nhs_number?: string
  mrn?: string
  hospital_number?: string
  demographics?: PatientDemographics
  contact?: ContactInfo
  created_at?: string  // ISO datetime string
  updated_at?: string  // ISO datetime string
  episode_count?: number
  most_recent_referral?: string  // ISO date string
}

// ============================================================================
// Episode Models
// ============================================================================

export type ConditionType = 'cancer' | 'benign' | 'inflammatory'
export type CancerType =
  | 'oesophageal'
  | 'gastric'
  | 'colorectal'
  | 'hepatobiliary'
  | 'pancreatic'
  | 'sarcoma'
  | 'other'

export interface CancerData {
  site?: string
  histology?: string
  grade?: string
  staging?: {
    clinical_t?: string
    clinical_n?: string
    clinical_m?: string
    clinical_stage?: string
    pathological_t?: string
    pathological_n?: string
    pathological_m?: string
    pathological_stage?: string
  }
  mdt_decision?: string
  mdt_decision_date?: string
}

export interface Episode {
  _id?: string
  episode_id: string
  patient_id: string
  condition_type: ConditionType
  cancer_type?: CancerType
  cancer_data?: CancerData
  referral_date?: string  // ISO date string
  first_seen_date?: string  // ISO date string
  diagnosis_date?: string  // ISO date string
  lead_clinician?: string
  referring_hospital?: string
  notes?: string
  created_at?: string
  updated_at?: string
  treatments?: Treatment[]
  tumours?: Tumour[]
  investigations?: Investigation[]
}

// ============================================================================
// Treatment Models
// ============================================================================

export type TreatmentIntent =
  | 'curative'
  | 'palliative'
  | 'diagnostic'
  | 'emergency'
  | 'other'

export type Urgency = 'elective' | 'urgent' | 'emergency' | 'expedited'
export type Approach = 'open' | 'laparoscopic' | 'robotic' | 'hybrid' | 'other'

export interface Team {
  primary_surgeon?: string
  primary_surgeon_text?: string
  assistant_surgeon?: string
  anaesthetist?: string
  scrub_nurse?: string
  odu_nurse?: string
}

export interface Complication {
  type?: string
  grade?: string  // Clavien-Dindo grade
  description?: string
  date?: string
  intervention_required?: boolean
}

// Treatment Types
export type TreatmentType =
  | 'surgery_primary'
  | 'surgery_rtt'
  | 'surgery_reversal'
  | 'chemotherapy'
  | 'radiotherapy'
  | 'immunotherapy'
  | 'hormone_therapy'
  | 'targeted_therapy'
  | 'palliative'
  | 'surveillance'

// Related surgery reference
export interface RelatedSurgery {
  treatment_id: string
  treatment_type: 'surgery_rtt' | 'surgery_reversal'
  date_created: string
}

export interface Treatment {
  _id?: string
  treatment_id: string
  episode_id: string
  patient_id: string
  treatment_type?: TreatmentType  // NEW: Treatment type enum
  treatment_date?: string  // ISO date string
  admission_date?: string  // ISO date string
  discharge_date?: string  // ISO date string
  surgeon?: string  // Flattened from team.primary_surgeon_text
  team?: Team
  procedure_name?: string
  opcs4_code?: string
  intent?: TreatmentIntent
  urgency?: Urgency
  approach?: Approach
  asa_grade?: string
  complications?: Complication[]
  return_to_theatre?: boolean
  return_to_theatre_date?: string
  return_to_theatre_reason?: string
  escalation_of_care?: boolean
  mortality_30d?: boolean
  mortality_90d?: boolean
  mortality_1y?: boolean
  readmission_30d?: boolean
  length_of_stay?: number
  itu_admission?: boolean
  itu_los_days?: number
  notes?: string
  vitals?: {
    height_cm?: number
    weight_kg?: number
    bmi?: number
  }

  // NEW: Surgery relationship fields (for RTT and reversal)
  parent_surgery_id?: string
  parent_episode_id?: string
  rtt_reason?: string
  reversal_notes?: string
  related_surgery_ids?: RelatedSurgery[]

  created_at?: string
  updated_at?: string
}

// ============================================================================
// Tumour (Pathology) Models
// ============================================================================

export interface Tumour {
  _id?: string
  tumour_id: string
  episode_id: string
  site?: string
  laterality?: 'left' | 'right' | 'bilateral' | 'midline'
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
  resection_margins?: 'R0' | 'R1' | 'R2'
  notes?: string
  created_at?: string
  updated_at?: string
}

// ============================================================================
// Investigation Models
// ============================================================================

export type InvestigationType =
  | 'ct_scan'
  | 'mri_scan'
  | 'pet_scan'
  | 'ultrasound'
  | 'endoscopy'
  | 'colonoscopy'
  | 'biopsy'
  | 'blood_test'
  | 'other'

export interface Investigation {
  _id?: string
  investigation_id: string
  episode_id: string
  investigation_type: InvestigationType
  investigation_date?: string  // ISO date string
  findings?: string
  imaging_findings?: string
  pathology_findings?: string
  recommendations?: string
  notes?: string
  created_at?: string
  updated_at?: string
}

// ============================================================================
// Follow-up Models
// ============================================================================

export interface FollowUp {
  _id?: string
  followup_id: string
  episode_id: string
  followup_date?: string  // ISO date string
  clinician?: string
  status?: 'alive_no_disease' | 'alive_with_disease' | 'deceased' | 'lost_to_followup'
  recurrence?: boolean
  recurrence_date?: string
  recurrence_site?: string
  notes?: string
  created_at?: string
  updated_at?: string
}

// ============================================================================
// Clinician Models
// ============================================================================

export interface Clinician {
  _id?: string
  surname: string
  first_name: string
  title?: string
  specialty?: string
  grade?: string
  gmc_number?: string
  email?: string
  active?: boolean
  created_at?: string
  updated_at?: string
}

// ============================================================================
// Report Models
// ============================================================================

export interface SurgicalMetrics {
  total_surgeries: number
  complication_rate: number
  readmission_rate: number
  mortality_30d_rate: number
  mortality_90d_rate: number
  return_to_theatre_rate: number
  escalation_rate: number
  median_length_of_stay_days: number
  urgency_breakdown: Record<string, number>
  asa_breakdown: Record<string, number>
}

export interface YearlyMetrics {
  overall: SurgicalMetrics
  2023?: SurgicalMetrics
  2024?: SurgicalMetrics
  2025?: SurgicalMetrics
}

// ============================================================================
// User/Auth Models
// ============================================================================

export type UserRole = 'admin' | 'surgeon' | 'data_entry' | 'viewer'

export interface User {
  username: string
  email?: string
  full_name?: string
  role: UserRole
  active: boolean
  created_at?: string
}

export interface AuthToken {
  access_token: string
  token_type: string
}

// ============================================================================
// Backup Models
// ============================================================================

export interface BackupInfo {
  filename: string
  path: string
  size_bytes: number
  size_human: string
  created: string  // ISO datetime
  type: 'manual' | 'daily' | 'weekly' | 'monthly'
  notes?: string
  retention_days: number
  collections: {
    patients: number
    episodes: number
    treatments: number
    tumours: number
    investigations: number
    followups: number
    clinicians: number
    audit_logs: number
  }
}

// ============================================================================
// Audit Log Models
// ============================================================================

export type AuditAction =
  | 'create'
  | 'update'
  | 'delete'
  | 'view'
  | 'export'
  | 'login'
  | 'logout'

export type EntityType =
  | 'patient'
  | 'episode'
  | 'treatment'
  | 'tumour'
  | 'investigation'
  | 'followup'
  | 'user'
  | 'backup'

export interface AuditLog {
  _id?: string
  timestamp: string  // ISO datetime
  user_id: string
  user_role: UserRole
  action: AuditAction
  entity_type: EntityType
  entity_id?: string
  changes?: Record<string, unknown>
  ip_address?: string
  user_agent?: string
  success: boolean
  error_message?: string
}
