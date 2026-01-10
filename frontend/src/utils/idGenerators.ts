/**
 * ID generation utilities for creating unique identifiers
 * Used across the application for patients, episodes, treatments, and tumours
 */

/**
 * Generate a unique timestamp-based hash
 * @returns {string} 6-character uppercase hash
 */
function generateTimestampHash(): string {
  const timestamp = Date.now().toString(36)
  const random = Math.random().toString(36).substring(2, 8)
  return (timestamp + random).toUpperCase().substring(0, 6)
}

/**
 * Generate a unique patient ID
 * Format: 6-character alphanumeric hash (e.g., "A1B2C3")
 *
 * @returns {string} Patient ID
 * @example
 * const patientId = generatePatientId()
 * // Returns: "A1B2C3"
 */
export function generatePatientId(): string {
  return generateTimestampHash()
}

/**
 * Generate an episode ID for a patient
 * Format: E-{patientId}-{count} (e.g., "E-A1B2C3-01")
 *
 * @param {string} patientId - The patient's unique ID
 * @param {number} episodeCount - Current count of episodes for this patient
 * @returns {string} Episode ID
 * @example
 * const episodeId = generateEpisodeId("A1B2C3", 0)
 * // Returns: "E-A1B2C3-01"
 */
export function generateEpisodeId(patientId: string, episodeCount: number): string {
  return `E-${patientId}-${String(episodeCount + 1).padStart(2, '0')}`
}

/**
 * Generate a treatment ID for a patient
 * Format: {prefix}-{patientId}-{count} (e.g., "SUR-A1B2C3-01")
 *
 * @param {string} prefix - Treatment type prefix (e.g., "SUR", "CHE", "RAD")
 * @param {string} patientId - The patient's unique ID
 * @param {number} count - Current count of treatments for this patient
 * @returns {string} Treatment ID
 * @example
 * const treatmentId = generateTreatmentId("SUR", "A1B2C3", 0)
 * // Returns: "SUR-A1B2C3-01"
 */
export function generateTreatmentId(prefix: string, patientId: string, count: number): string {
  return `${prefix}-${patientId}-${String(count + 1).padStart(2, '0')}`
}

/**
 * Generate a tumour ID for a patient
 * Format: TUM-{patientId}-{count} (e.g., "TUM-A1B2C3-01")
 *
 * @param {string} patientId - The patient's unique ID
 * @param {number} tumourCount - Current count of tumours for this patient
 * @returns {string} Tumour ID
 * @example
 * const tumourId = generateTumourId("A1B2C3", 0)
 * // Returns: "TUM-A1B2C3-01"
 */
export function generateTumourId(patientId: string, tumourCount: number): string {
  return `TUM-${patientId}-${String(tumourCount + 1).padStart(2, '0')}`
}

/**
 * Generate an investigation ID for a patient
 * Format: {prefix}-{patientId}-{count} (e.g., "INV-A1B2C3-01")
 *
 * @param {string} patientId - The patient's unique ID
 * @param {number} investigationCount - Current count of investigations for this patient
 * @param {string} prefix - Optional investigation type prefix (defaults to "INV")
 *                          Common prefixes: "IMG" (imaging), "END" (endoscopy), "LAB" (laboratory)
 * @returns {string} Investigation ID
 * @example
 * const investigationId = generateInvestigationId("A1B2C3", 0)
 * // Returns: "INV-A1B2C3-01"
 * const imagingId = generateInvestigationId("A1B2C3", 0, "IMG")
 * // Returns: "IMG-A1B2C3-01"
 */
export function generateInvestigationId(patientId: string, investigationCount: number, prefix: string = 'INV'): string {
  const cleanPatientId = patientId.replace(/[^a-zA-Z0-9]/g, '')
  return `${prefix}-${cleanPatientId}-${String(investigationCount + 1).padStart(2, '0')}`
}

/**
 * Generate a follow-up ID for a patient
 * Format: FU-{patientId}-{count} (e.g., "FU-A1B2C3-01")
 *
 * @param {string} patientId - The patient's unique ID
 * @param {number} followUpCount - Current count of follow-ups for this patient
 * @returns {string} Follow-up ID
 * @example
 * const followUpId = generateFollowUpId("A1B2C3", 0)
 * // Returns: "FU-A1B2C3-01"
 */
export function generateFollowUpId(patientId: string, followUpCount: number): string {
  const cleanPatientId = patientId.replace(/[^a-zA-Z0-9]/g, '')
  return `FU-${cleanPatientId}-${String(followUpCount + 1).padStart(2, '0')}`
}

/**
 * Get the prefix for a treatment type
 * Maps treatment types to their standard prefixes
 *
 * @param {string} type - Treatment type (e.g., "surgery", "chemotherapy", "radiotherapy")
 * @returns {string} Treatment prefix (e.g., "SUR", "ONC", "DXT")
 * @example
 * const prefix = getTreatmentPrefix("surgery")
 * // Returns: "SUR"
 */
export function getTreatmentPrefix(type: string): string {
  const prefixMap: Record<string, string> = {
    'surgery': 'SUR',
    'surgery_primary': 'SUR',
    'surgery_rtt': 'SUR',
    'surgery_reversal': 'SUR',
    'chemotherapy': 'ONC',
    'radiotherapy': 'DXT',
    'immunotherapy': 'IMM'
  }
  return prefixMap[type] || 'TRE'
}

/**
 * Get the prefix for an investigation type
 * Maps investigation types to their standard prefixes
 *
 * @param {string} type - Investigation type (e.g., "imaging", "endoscopy", "laboratory")
 * @returns {string} Investigation prefix (e.g., "IMG", "END", "LAB")
 * @example
 * const prefix = getInvestigationPrefix("imaging")
 * // Returns: "IMG"
 */
export function getInvestigationPrefix(type: string): string {
  const prefixMap: Record<string, string> = {
    'imaging': 'IMG',
    'endoscopy': 'END',
    'laboratory': 'LAB'
  }
  return prefixMap[type] || 'INV'
}
