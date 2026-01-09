/**
 * Style mapping utilities for consistent UI styling across components
 */

export const URGENCY_STYLES = {
  emergency: 'bg-red-100 text-red-800',
  urgent: 'bg-orange-100 text-orange-800',
  elective: 'bg-green-100 text-green-800'
} as const

export const STATUS_STYLES = {
  active: 'bg-green-100 text-green-800',
  completed: 'bg-blue-100 text-blue-800',
  cancelled: 'bg-gray-100 text-gray-800',
  planned: 'bg-yellow-100 text-yellow-800',
  pending: 'bg-orange-100 text-orange-800'
} as const

export const COMPLEXITY_STYLES = {
  routine: 'bg-green-100 text-green-800',
  intermediate: 'bg-yellow-100 text-yellow-800',
  complex: 'bg-orange-100 text-orange-800'
} as const

export const APPROACH_STYLES = {
  open: 'bg-blue-100 text-blue-800',
  laparoscopic: 'bg-purple-100 text-purple-800',
  robotic: 'bg-indigo-100 text-indigo-800',
  converted: 'bg-orange-100 text-orange-800'
} as const

/**
 * Get Tailwind CSS classes for urgency styling
 * @param urgency - The urgency level (emergency, urgent, elective)
 * @returns Tailwind CSS class string
 */
export function getUrgencyStyle(urgency: string): string {
  return URGENCY_STYLES[urgency as keyof typeof URGENCY_STYLES] || URGENCY_STYLES.elective
}

/**
 * Get Tailwind CSS classes for status styling
 * @param status - The status (active, completed, cancelled, planned, pending)
 * @returns Tailwind CSS class string
 */
export function getStatusStyle(status: string): string {
  return STATUS_STYLES[status as keyof typeof STATUS_STYLES] || STATUS_STYLES.active
}

/**
 * Get Tailwind CSS classes for complexity styling
 * @param complexity - The complexity level (routine, intermediate, complex)
 * @returns Tailwind CSS class string
 */
export function getComplexityStyle(complexity: string): string {
  return COMPLEXITY_STYLES[complexity as keyof typeof COMPLEXITY_STYLES] || COMPLEXITY_STYLES.routine
}

/**
 * Get Tailwind CSS classes for surgical approach styling
 * @param approach - The surgical approach (open, laparoscopic, robotic, converted)
 * @returns Tailwind CSS class string
 */
export function getApproachStyle(approach: string): string {
  return APPROACH_STYLES[approach as keyof typeof APPROACH_STYLES] || APPROACH_STYLES.open
}
