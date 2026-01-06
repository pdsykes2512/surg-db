/**
 * Utility functions for formatting display values
 */

/**
 * Medical and clinical acronyms that should be fully uppercase
 */
const MEDICAL_ACRONYMS = ['CT', 'MRI', 'PET', 'US', 'XR', 'MRCP', 'ERCP', 'EUS', 'OGD', 'CT-CAP', 'CAP', 'MDT', 'NHS', 'ICU', 'HDU', 'ITU']

/**
 * Capitalize the first letter of a string
 */
export const capitalize = (str: string): string => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

/**
 * Normalize string to lowercase for backend storage
 * Should be used before sending data to API
 */
export const normalizeForStorage = (str: string): string => {
  if (!str) return ''
  return str.toLowerCase().trim()
}

/**
 * Format string for display (capitalize first letter)
 * Should be used when displaying data from backend
 */
export const formatForDisplay = (str: string): string => {
  if (!str) return ''
  return capitalize(str)
}

/**
 * Convert snake_case to Title Case with acronym awareness
 */
export const snakeToTitle = (str: string): string => {
  if (!str) return ''
  return str
    .split('_')
    .map(word => {
      const upperWord = word.toUpperCase()
      // Check if this word is a known acronym
      if (MEDICAL_ACRONYMS.includes(upperWord)) {
        return upperWord
      }
      // Otherwise capitalize normally
      return capitalize(word)
    })
    .join(' ')
}

/**
 * Format coded values for display (universal formatter)
 * Handles: lowercase, snake_case, UPPERCASE, mixed case, acronyms
 * Examples:
 *   'colorectal' -> 'Colorectal'
 *   'upper_gi' -> 'Upper Gi'
 *   'COLORECTAL_MDT' -> 'Colorectal MDT'
 *   'colorectal mdt' -> 'Colorectal MDT'
 *   'surgery' -> 'Surgery'
 */
export const formatCodedValue = (value: string | undefined | null): string => {
  if (!value) return ''

  // If it contains underscore, convert snake_case to Title Case with acronyms
  if (value.includes('_')) {
    return snakeToTitle(value)
  }

  // If it contains spaces, handle each word separately with acronym awareness
  if (value.includes(' ')) {
    return value
      .split(' ')
      .map(word => {
        const upperWord = word.toUpperCase()
        // Check if this word is a known acronym
        if (MEDICAL_ACRONYMS.includes(upperWord)) {
          return upperWord
        }
        // Otherwise capitalize normally
        return capitalize(word)
      })
      .join(' ')
  }

  // Single word - check if it's an acronym first
  const upperValue = value.toUpperCase()
  if (MEDICAL_ACRONYMS.includes(upperValue)) {
    return upperValue
  }

  // Otherwise, just capitalize first letter
  return capitalize(value)
}

/**
 * Format field names for display (snake_case to Title Case)
 */
export const formatFieldName = (field: string): string => {
  if (!field) return ''
  return snakeToTitle(field)
}

/**
 * Format anatomical site for display
 * Maps site values to readable format without ICD-10 codes
 */
export const formatAnatomicalSite = (site: string | undefined | null): string => {
  if (!site) return '-'
  
  const siteMap: Record<string, string> = {
    'caecum': 'Caecum',
    'appendix': 'Appendix',
    'ascending_colon': 'Ascending Colon',
    'hepatic_flexure': 'Hepatic Flexure',
    'transverse_colon': 'Transverse Colon',
    'splenic_flexure': 'Splenic Flexure',
    'descending_colon': 'Descending Colon',
    'sigmoid_colon': 'Sigmoid Colon',
    'rectosigmoid_junction': 'Rectosigmoid Junction',
    'rectum': 'Rectum',
    'colon_unspecified': 'Colon Unspecified',
    // Metastatic sites
    'liver': 'Liver',
    'lung': 'Lung',
    'peritoneum': 'Peritoneum',
    'lymph_node': 'Lymph Node',
    'bone': 'Bone',
    'brain': 'Brain',
    'other': 'Other'
  }
  
  return siteMap[site.toLowerCase()] || snakeToTitle(site)
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
 * Format date strings consistently as DD MMM YYYY (e.g., 01 Dec 2025)
 */
export const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '-'

  try {
    const date = new Date(dateStr)
    const day = date.getDate().toString().padStart(2, '0')
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    const month = monthNames[date.getMonth()]
    const year = date.getFullYear()
    return `${day} ${month} ${year}`
  } catch {
    return dateStr
  }
}

/**
 * Format NHS number consistently as XXX XXX XXXX
 * Accepts 10-digit NHS numbers with or without spaces
 */
export const formatNHSNumber = (nhsNumber: string | undefined | null): string => {
  if (!nhsNumber) return '-'

  // Remove all non-digit characters
  const digits = nhsNumber.replace(/\D/g, '')

  // Only format if we have exactly 10 digits
  if (digits.length === 10) {
    return `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6)}`
  }

  // Return original value if not 10 digits
  return nhsNumber
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
    'surgery_primary': 'Primary Surgery',
    'surgery_rtt': 'RTT Surgery',
    'surgery_reversal': 'Reversal Surgery',
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
 * Format urgency level for display
 */
export const formatUrgency = (urgency: string): string => {
  if (!urgency) return '-'
  
  const urgencyMap: Record<string, string> = {
    'elective': 'Elective',
    'urgent': 'Urgent',
    'emergency': 'Emergency',
    'expedited': 'Expedited'
  }
  
  return urgencyMap[urgency.toLowerCase()] || capitalize(urgency)
}

/**
 * Format approach for display
 */
export const formatApproach = (approach: string): string => {
  if (!approach) return '-'
  
  const approachMap: Record<string, string> = {
    'open': 'Open',
    'laparoscopic': 'Laparoscopic',
    'robotic': 'Robotic',
    'endoscopic': 'Endoscopic',
    'converted': 'Converted'
  }
  
  return approachMap[approach.toLowerCase()] || capitalize(approach)
}

/**
 * Normalize object fields for backend storage
 * Converts specified string fields to lowercase
 */
export const normalizeObjectForStorage = (obj: any, fields: string[]): any => {
  if (!obj) return obj
  
  const normalized = { ...obj }
  fields.forEach(field => {
    if (normalized[field] && typeof normalized[field] === 'string') {
      normalized[field] = normalizeForStorage(normalized[field])
    }
  })
  
  return normalized
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

/**
 * Format treatment plan for display (Title Case)
 */
export const formatTreatmentPlan = (plan: string | undefined | null): string => {
  if (!plan) return ''
  // Convert to title case: 'surgery' -> 'Surgery', 'chemotherapy' -> 'Chemotherapy'
  return plan
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

/**
 * Format individual TNM component (T, N, or M stage)
 * Examples: 'x' -> 'x', '1' -> '1', '3' -> '3', null -> '-'
 */
export const formatTNMComponent = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') return '-'
  return String(value).toLowerCase()
}

/**
 * Format clinical TNM staging: T1 N0 M0
 * Takes individual T, N, M values and formats them with proper spacing
 */
export const formatClinicalTNM = (
  t: string | number | null | undefined,
  n: string | number | null | undefined,
  m: string | number | null | undefined
): string => {
  const tFormatted = formatTNMComponent(t)
  const nFormatted = formatTNMComponent(n)
  const mFormatted = formatTNMComponent(m)
  
  // Only show if at least one component is present
  if (tFormatted === '-' && nFormatted === '-' && mFormatted === '-') {
    return '-'
  }
  
  return `T${tFormatted} N${nFormatted} M${mFormatted}`
}

/**
 * Format pathological TNM staging: pT1 pN0 pM0
 * Takes individual T, N, M values and formats them with 'p' prefix
 */
export const formatPathologicalTNM = (
  t: string | number | null | undefined,
  n: string | number | null | undefined,
  m: string | number | null | undefined
): string => {
  const tFormatted = formatTNMComponent(t)
  const nFormatted = formatTNMComponent(n)
  const mFormatted = formatTNMComponent(m)
  
  // Only show if at least one component is present
  if (tFormatted === '-' && nFormatted === '-' && mFormatted === '-') {
    return '-'
  }
  
  return `pT${tFormatted} pN${nFormatted} pM${mFormatted}`
}

/**
 * Format investigation subtype with proper acronym capitalization
 * Handles medical acronyms like CT, MRI, PET, etc.
 */
export const formatInvestigationType = (subtype: string | undefined | null): string => {
  if (!subtype) return '—'

  // Split by underscore and process each word
  const words = subtype.split('_').map(word => {
    const upperWord = word.toUpperCase()
    // Check if this word is a known acronym
    if (MEDICAL_ACRONYMS.includes(upperWord)) {
      return upperWord
    }
    // Otherwise capitalize normally
    return capitalize(word)
  })

  return words.join(' ')
}
