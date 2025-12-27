import { useState, useEffect } from 'react'
import { SearchableSelect } from '../common/SearchableSelect'

interface Surgeon {
  _id: string
  first_name: string
  surname: string
  gmc_number?: string
  subspecialty_leads?: string[]
  clinical_role?: string
}

interface SurgeonSearchProps {
  value: string
  onChange: (name: string) => void
  label?: string
  required?: boolean
  consultantsOnly?: boolean
  subspecialtyFilter?: string
  roleFilter?: string
  placeholder?: string
  className?: string
}

export function SurgeonSearch({
  value,
  onChange,
  label = 'Surgeon',
  required = false,
  consultantsOnly: _consultantsOnly = false,
  subspecialtyFilter,
  roleFilter,
  placeholder = 'Search surgeon...',
  className = ''
}: SurgeonSearchProps) {
  const [surgeons, setSurgeons] = useState<Surgeon[]>([])
  const [loading, setLoading] = useState(false)

  // Fetch surgeons on mount
  useEffect(() => {
    const fetchSurgeons = async () => {
      setLoading(true)
      try {
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
        const baseUrl = API_URL.endsWith('/api') ? API_URL.slice(0, -4) : API_URL
        const url = `${baseUrl}/api/admin/clinicians`
        
        const response = await fetch(url, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        })
        if (response.ok) {
          const data = await response.json()
          setSurgeons(data)
        } else {
          console.error('Failed to fetch surgeons:', response.status)
        }
      } catch (error) {
        console.error('Error fetching surgeons:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchSurgeons()
  }, [])

  // Filter surgeons based on subspecialty and role
  // Default to showing only surgeons (not anaesthetists, nurses, etc) unless roleFilter specified
  const filteredSurgeons = surgeons.filter((s) => {
    const matchesSubspecialty = !subspecialtyFilter || 
      (s.subspecialty_leads && s.subspecialty_leads.includes(subspecialtyFilter))
    // Default to surgeon role if not specified
    const clinicianRole = s.clinical_role || 'surgeon'
    const targetRole = roleFilter || 'surgeon'
    const matchesRole = clinicianRole === targetRole
    return matchesSubspecialty && matchesRole
  })
  
  // If role filter is active but no matches found, show all clinicians (backward compatibility)
  const finalFilteredSurgeons = (roleFilter && filteredSurgeons.length === 0) ? surgeons : filteredSurgeons

  // Convert surgeons to options format
  const options = finalFilteredSurgeons.map(surgeon => ({
    value: `${surgeon.first_name} ${surgeon.surname}`,
    label: `${surgeon.first_name} ${surgeon.surname}`,
    surgeon: surgeon
  }))

  // Custom filter that searches name, GMC, and subspecialty
  const filterOption = (opt: typeof options[0], search: string) => {
    const searchLower = search.toLowerCase()
    const surgeon = opt.surgeon
    
    // Search in name
    if (opt.label.toLowerCase().includes(searchLower)) {
      return true
    }
    
    // Search in GMC number
    if (surgeon.gmc_number && surgeon.gmc_number.toLowerCase().includes(searchLower)) {
      return true
    }
    
    // Search in subspecialties
    if (surgeon.subspecialty_leads) {
      return surgeon.subspecialty_leads.some(lead => 
        lead.toLowerCase().replace('_', ' ').includes(searchLower)
      )
    }
    
    return false
  }

  return (
    <SearchableSelect
      value={value}
      onChange={onChange}
      options={options}
      getOptionValue={(opt) => opt.value}
      getOptionLabel={(opt) => opt.label}
      filterOption={filterOption}
      renderOption={(opt) => (
        <div>
          <div className="font-medium">{opt.label}</div>
          {opt.surgeon.gmc_number && (
            <div className="text-xs text-gray-500">GMC: {opt.surgeon.gmc_number}</div>
          )}
          {opt.surgeon.subspecialty_leads && opt.surgeon.subspecialty_leads.length > 0 && (
            <div className="flex gap-1 mt-1 flex-wrap">
              {opt.surgeon.subspecialty_leads.map(lead => (
                <span key={lead} className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 capitalize">
                  {lead.replace('_', ' ')}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
      label={label}
      required={required}
      placeholder={placeholder}
      className={className}
      disabled={loading}
    />
  )
}
