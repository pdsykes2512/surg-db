/**
 * Utility functions for formatting display values
 */

/**
 * Capitalize the first letter of a string
 */
export const capitalize = (str: string): string => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

/**
 * Convert snake_case to Title Case
 */
export const snakeToTitle = (str: string): string => {
  if (!str) return ''
  return str
    .split('_')
    .map(word => capitalize(word))
    .join(' ')
}

/**
 * Format field names for display (snake_case to Title Case)
 */
export const formatFieldName = (field: string): string => {
  if (!field) return ''
  return snakeToTitle(field)
}

/**
 * Format field values for display
 * Handles various types of values and formats them appropriately
 */
export const formatFieldValue = (value: any): string => {
  if (value === null || value === undefined || value === '') return '-'
  
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }
  
  if (typeof value === 'string') {
    // Check if it looks like a snake_case value
    if (value.includes('_')) {
      return snakeToTitle(value)
    }
    return capitalize(value)
  }
  
  if (typeof value === 'number') {
    return value.toString()
  }
  
  return String(value)
}

/**
 * Format date strings consistently
 */
export const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '-'
  
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    })
  } catch {
    return dateStr
  }
}

/**
 * Format status values with proper casing
 */
export const formatStatus = (status: string): string => {
  if (!status) return '-'
  
  const statusMap: Record<string, string> = {
    'active': 'Active',
    'completed': 'Completed',
    'cancelled': 'Cancelled',
    'pending': 'Pending',
    'in_progress': 'In Progress',
    'on_hold': 'On Hold'
  }
  
  return statusMap[status.toLowerCase()] || capitalize(status)
}

/**
 * Format cancer type for display
 */
export const formatCancerType = (type: string): string => {
  if (!type) return '-'
  
  const typeMap: Record<string, string> = {
    'bowel': 'Bowel (Colorectal)',
    'kidney': 'Kidney (Renal)',
    'breast_primary': 'Breast (Primary)',
    'breast_metastatic': 'Breast (Metastatic)',
    'oesophageal': 'Oesophageal',
    'ovarian': 'Ovarian',
    'prostate': 'Prostate'
  }
  
  return typeMap[type.toLowerCase()] || snakeToTitle(type)
}

/**
 * Format treatment type for display
 */
export const formatTreatmentType = (type: string): string => {
  if (!type) return '-'
  
  const typeMap: Record<string, string> = {
    'surgery': 'Surgery',
    'chemotherapy': 'Chemotherapy',
    'radiotherapy': 'Radiotherapy',
    'immunotherapy': 'Immunotherapy',
    'hormone_therapy': 'Hormone Therapy',
    'targeted_therapy': 'Targeted Therapy',
    'palliative': 'Palliative Care',
    'surveillance': 'Surveillance'
  }
  
  return typeMap[type.toLowerCase()] || snakeToTitle(type)
}

/**
 * Format surgeon/clinician name for display
 * Handles various formats: "FirstName LastName", "LastName", or "FirstName M LastName"
 * Always returns full name if available, or just surname if that's all we have
 */
export const formatSurgeon = (name: string): string => {
  if (!name) return '-'
  
  // If it's already formatted (contains a space), return as-is
  // Otherwise, return the single name (surname)
  return name.trim()
}
