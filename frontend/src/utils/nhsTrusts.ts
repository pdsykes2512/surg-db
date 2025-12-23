// NHS Trust data and utilities
// Trusts are fetched dynamically from the NHS ODS API via backend
// See: execution/fetch_nhs_provider_codes.py
export const NHS_TRUSTS: Array<{ code: string; name: string }> = []

// Create a lookup map for quick access
const trustMap = new Map(NHS_TRUSTS.map(trust => [trust.code, trust.name]))

/**
 * Format provider name to Title Case with NHS properly capitalized
 * @param name - Provider name in lowercase (e.g., "portsmouth hospitals university nhs trust")
 * @returns Formatted string like "Portsmouth Hospitals University NHS Trust"
 */
function formatProviderName(name: string): string {
  if (!name) return ''
  
  // Split into words and capitalize each
  const words = name.split(' ').map(word => {
    // Always capitalize NHS
    if (word.toLowerCase() === 'nhs') return 'NHS'
    // Title case for other words
    return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
  })
  
  return words.join(' ')
}

/**
 * Format trust code as "Trust Name (Code)"
 * @param code - NHS Trust code (e.g., "RYR")
 * @returns Formatted string like "Portsmouth Hospitals University NHS Trust (RYR)" or just the code if not found
 */
export function formatTrustName(code: string | undefined | null): string {
  if (!code) return ''
  const name = trustMap.get(code)
  return name ? `${formatProviderName(name)} (${code})` : code
}

/**
 * Get options for SearchableSelect components
 * Format: "Trust Name (Code)" for better readability
 */
export const NHS_TRUST_OPTIONS = NHS_TRUSTS.map(trust => ({
  value: trust.code,
  label: `${formatProviderName(trust.name)} (${trust.code})`
}))
