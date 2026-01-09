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
 * Format: EPI-{patientId}-{count} (e.g., "EPI-A1B2C3-01")
 *
 * @param {string} patientId - The patient's unique ID
 * @param {number} episodeCount - Current count of episodes for this patient
 * @returns {string} Episode ID
 * @example
 * const episodeId = generateEpisodeId("A1B2C3", 0)
 * // Returns: "EPI-A1B2C3-01"
 */
export function generateEpisodeId(patientId: string, episodeCount: number): string {
  return `EPI-${patientId}-${String(episodeCount + 1).padStart(2, '0')}`
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
 * Format: INV-{patientId}-{count} (e.g., "INV-A1B2C3-01")
 *
 * @param {string} patientId - The patient's unique ID
 * @param {number} investigationCount - Current count of investigations for this patient
 * @returns {string} Investigation ID
 * @example
 * const investigationId = generateInvestigationId("A1B2C3", 0)
 * // Returns: "INV-A1B2C3-01"
 */
export function generateInvestigationId(patientId: string, investigationCount: number): string {
  return `INV-${patientId}-${String(investigationCount + 1).padStart(2, '0')}`
}
