/**
 * Cancer Staging Calculations
 * Automatically calculates overall stage from TNM components
 */

export type StageGroup = '0' | 'I' | 'IIA' | 'IIB' | 'IIC' | 'IIIA' | 'IIIB' | 'IIIC' | 'IVA' | 'IVB' | 'IVC' | 'Unknown'

/**
 * Calculate colorectal cancer stage from TNM components (8th Edition)
 * Based on AJCC Cancer Staging Manual, 8th Edition
 */
export function calculateColorectalStage(
  t: string,
  n: string,
  m: string
): StageGroup {
  if (!t || !n || !m) return 'Unknown'

  // Normalize stages (remove spaces, make lowercase)
  const tStage = t.trim().toLowerCase()
  const nStage = n.trim().toLowerCase()
  const mStage = m.trim().toLowerCase()

  // Unknown/Not assessed
  if (tStage === 'tx' || nStage === 'nx' || mStage === 'mx') {
    return 'Unknown'
  }

  // Stage IV - Any distant metastasis
  if (mStage === 'm1' || mStage === 'm1a' || mStage === 'm1b' || mStage === 'm1c') {
    if (mStage === 'm1a') return 'IVA'
    if (mStage === 'm1b') return 'IVB'
    if (mStage === 'm1c') return 'IVC'
    return 'IVA' // Default M1 to IVA
  }

  // All subsequent stages require M0
  if (mStage !== 'm0') return 'Unknown'

  // Stage 0 - Carcinoma in situ
  if (tStage === 'tis' && nStage === 'n0') {
    return '0'
  }

  // Stage I - T1-T2, N0, M0
  if ((tStage === 't1' || tStage === 't2') && nStage === 'n0') {
    return 'I'
  }

  // Stage II - T3-T4, N0, M0
  if (nStage === 'n0') {
    if (tStage === 't3') return 'IIA'
    if (tStage === 't4' || tStage === 't4a') return 'IIB'
    if (tStage === 't4b') return 'IIC'
  }

  // Stage III - Any T, N1-N2, M0
  // Stage IIIA
  if ((tStage === 't1' || tStage === 't2') && (nStage === 'n1' || nStage === 'n1a' || nStage === 'n1b' || nStage === 'n1c')) {
    return 'IIIA'
  }
  if (tStage === 't1' && nStage === 'n2a') {
    return 'IIIA'
  }

  // Stage IIIB
  if ((tStage === 't3' || tStage === 't4' || tStage === 't4a') && (nStage === 'n1' || nStage === 'n1a' || nStage === 'n1b' || nStage === 'n1c')) {
    return 'IIIB'
  }
  if ((tStage === 't2' || tStage === 't3') && nStage === 'n2a') {
    return 'IIIB'
  }
  if ((tStage === 't1' || tStage === 't2') && nStage === 'n2b') {
    return 'IIIB'
  }

  // Stage IIIC
  if (tStage === 't4a' && nStage === 'n2a') {
    return 'IIIC'
  }
  if ((tStage === 't3' || tStage === 't4' || tStage === 't4a') && nStage === 'n2b') {
    return 'IIIC'
  }
  if (tStage === 't4b' && (nStage === 'n1' || nStage === 'n1a' || nStage === 'n1b' || nStage === 'n1c' || nStage === 'n2' || nStage === 'n2a' || nStage === 'n2b')) {
    return 'IIIC'
  }

  return 'Unknown'
}

/**
 * Get stage display name with formatting
 */
export function formatStage(stage: StageGroup): string {
  if (stage === 'Unknown') return 'Unknown'
  return `Stage ${stage}`
}

/**
 * Get color coding for stage display
 */
export function getStageColor(stage: StageGroup): string {
  switch (stage) {
    case '0':
    case 'I':
      return 'bg-green-100 text-green-800'
    case 'IIA':
    case 'IIB':
    case 'IIC':
      return 'bg-yellow-100 text-yellow-800'
    case 'IIIA':
    case 'IIIB':
    case 'IIIC':
      return 'bg-orange-100 text-orange-800'
    case 'IVA':
    case 'IVB':
    case 'IVC':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

/**
 * Calculate stage based on cancer type
 * Extensible for other cancer types
 */
export function calculateStage(
  cancerType: string,
  t: string,
  n: string,
  m: string
): StageGroup {
  switch (cancerType.toLowerCase()) {
    case 'bowel':
    case 'colorectal':
    case 'colon':
    case 'rectal':
      return calculateColorectalStage(t, n, m)
    // Add other cancer types here
    default:
      return calculateColorectalStage(t, n, m) // Default to colorectal for now
  }
}
