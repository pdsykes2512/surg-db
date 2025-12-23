// NHS Trust data and utilities
export const NHS_TRUSTS = [
  { code: 'RH8', name: 'Barnsley Hospital NHS Foundation Trust' },
  { code: 'RFS', name: 'Royal Free London NHS Foundation Trust' },
  { code: 'RRV', name: 'University College London Hospitals NHS Foundation Trust' },
  { code: 'RJ1', name: "Guy's and St Thomas' NHS Foundation Trust" },
  { code: 'R1H', name: 'Imperial College Healthcare NHS Trust' },
  { code: 'RQM', name: "Chelsea and Westminster Hospital NHS Foundation Trust" },
  { code: 'RFW', name: "King's College Hospital NHS Foundation Trust" },
  { code: 'RJ7', name: "St George's University Hospitals NHS Foundation Trust" },
  { code: 'RAL', name: 'Royal Free London NHS Foundation Trust' },
  { code: 'RNJ', name: 'University Hospitals Birmingham NHS Foundation Trust' },
  { code: 'RWE', name: 'University Hospitals of Leicester NHS Trust' },
  { code: 'RHM', name: 'University Hospital Southampton NHS Foundation Trust' },
  { code: 'RTG', name: 'Leeds Teaching Hospitals NHS Trust' },
  { code: 'RR8', name: 'Sheffield Teaching Hospitals NHS Foundation Trust' },
  { code: 'RCU', name: 'Nottingham University Hospitals NHS Trust' },
  { code: 'RRK', name: 'University Hospitals of North Midlands NHS Trust' },
  { code: 'RXH', name: 'The Newcastle upon Tyne Hospitals NHS Foundation Trust' },
  { code: 'RA4', name: 'Gateshead Health NHS Foundation Trust' },
  { code: 'RCX', name: 'Cambridge University Hospitals NHS Foundation Trust' },
  { code: 'RNA', name: 'Sheffield Children\'s NHS Foundation Trust' },
  { code: 'RTH', name: 'Oxford University Hospitals NHS Foundation Trust' },
  { code: 'RJ2', name: 'Royal Berkshire NHS Foundation Trust' },
  { code: 'RDU', name: 'Frimley Health NHS Foundation Trust' },
  { code: 'RXC', name: 'Surrey and Sussex Healthcare NHS Trust' },
  { code: 'RWD', name: 'United Lincolnshire Hospitals NHS Trust' },
  { code: 'RJE', name: 'East Lancashire Hospitals NHS Trust' },
  { code: 'RW6', name: 'Blackpool Teaching Hospitals NHS Foundation Trust' },
  { code: 'RBN', name: 'Lancashire Teaching Hospitals NHS Foundation Trust' },
  { code: 'RBL', name: 'Royal Bolton Hospital NHS Foundation Trust' },
  { code: 'R0A', name: 'Manchester University NHS Foundation Trust' },
  { code: 'RW3', name: 'Wrightington, Wigan and Leigh NHS Foundation Trust' },
  { code: 'RMC', name: 'Stockport NHS Foundation Trust' },
  { code: 'RM3', name: 'Tameside and Glossop Integrated Care NHS Foundation Trust' },
  { code: 'REF', name: 'The Dudley Group NHS Foundation Trust' },
  { code: 'RBK', name: 'The Royal Wolverhampton NHS Trust' },
  { code: 'RXK', name: 'Walsall Healthcare NHS Trust' },
  { code: 'RLN', name: 'University Hospitals Coventry and Warwickshire NHS Trust' },
  { code: 'RWH', name: 'East Kent Hospitals University NHS Foundation Trust' },
  { code: 'RYJ', name: 'Northern Devon Healthcare NHS Trust' },
  { code: 'RH5', name: 'Royal Cornwall Hospitals NHS Trust' },
  { code: 'RD3', name: 'University Hospitals Dorset NHS Foundation Trust' },
  { code: 'RA7', name: 'University Hospitals Bristol and Weston NHS Foundation Trust' },
  { code: 'RVJ', name: 'North Bristol NHS Trust' },
  { code: 'RTE', name: 'Great Western Hospitals NHS Foundation Trust' },
  { code: 'RN7', name: 'Dartford and Gravesham NHS Trust' },
  { code: 'RPA', name: 'Medway NHS Foundation Trust' },
  { code: 'RN5', name: 'Maidstone and Tunbridge Wells NHS Trust' },
  { code: 'RVV', name: 'East Sussex Healthcare NHS Trust' },
  { code: 'RXQ', name: 'Brighton and Sussex University Hospitals NHS Trust' },
  { code: 'RYR', name: 'Portsmouth Hospitals University NHS Trust' },
  { code: 'RHW', name: 'Isle of Wight NHS Trust' },
  { code: 'RDZ', name: 'University Hospitals Sussex NHS Foundation Trust' },
]

// Create a lookup map for quick access
const trustMap = new Map(NHS_TRUSTS.map(trust => [trust.code, trust.name]))

/**
 * Format trust code as "Trust Name (Code)"
 * @param code - NHS Trust code (e.g., "RYR")
 * @returns Formatted string like "Portsmouth Hospitals University NHS Trust (RYR)" or just the code if not found
 */
export function formatTrustName(code: string | undefined | null): string {
  if (!code) return ''
  const name = trustMap.get(code)
  return name ? `${name} (${code})` : code
}

/**
 * Get options for SearchableSelect components
 */
export const NHS_TRUST_OPTIONS = NHS_TRUSTS.map(trust => ({
  value: trust.code,
  label: `${trust.code} - ${trust.name}`
}))
