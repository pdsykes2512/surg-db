import { useState, useEffect } from 'react'

interface Surgeon {
  _id: string
  first_name: string
  surname: string
  gmc_number?: string
  is_consultant: boolean
}

interface SurgeonSearchProps {
  value: string
  onChange: (name: string) => void
  label?: string
  required?: boolean
  consultantsOnly?: boolean
  placeholder?: string
  className?: string
}

export function SurgeonSearch({
  value,
  onChange,
  label = 'Surgeon',
  required = false,
  consultantsOnly = false,
  placeholder = 'Search surgeon...',
  className = ''
}: SurgeonSearchProps) {
  const [surgeons, setSurgeons] = useState<Surgeon[]>([])
  const [searchTerm, setSearchTerm] = useState(value || '')
  const [showDropdown, setShowDropdown] = useState(false)
  const [loading, setLoading] = useState(false)

  // Sync searchTerm with value prop when it changes
  useEffect(() => {
    setSearchTerm(value || '')
  }, [value])

  // Fetch surgeons on mount
  useEffect(() => {
    const fetchSurgeons = async () => {
      setLoading(true)
      try {
        const url = consultantsOnly 
          ? 'http://localhost:8000/api/admin/surgeons?consultants_only=true'
          : 'http://localhost:8000/api/admin/surgeons'
        
        const response = await fetch(url, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        })
        if (response.ok) {
          setSurgeons(await response.json())
        }
      } catch (error) {
        console.error('Error fetching surgeons:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchSurgeons()
  }, [consultantsOnly])

  // Filter surgeons based on search
  const filteredSurgeons = surgeons.filter((s) =>
    `${s.first_name} ${s.surname}`.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleSelect = (surgeon: Surgeon) => {
    const fullName = `${surgeon.first_name} ${surgeon.surname}`
    onChange(fullName)
    setSearchTerm(fullName)
    setShowDropdown(false)
  }

  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label} {required && <span className="text-red-500">*</span>}
        </label>
      )}
      <div className="relative">
        <input
          type="text"
          value={searchTerm || value}
          onChange={(e) => {
            setSearchTerm(e.target.value)
            setShowDropdown(true)
          }}
          onFocus={() => setShowDropdown(true)}
          onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder={placeholder}
          disabled={loading}
        />
        {showDropdown && filteredSurgeons.length > 0 && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
            {filteredSurgeons.map((surgeon) => (
              <div
                key={surgeon._id}
                onMouseDown={() => handleSelect(surgeon)}
                className="px-4 py-2 hover:bg-blue-50 cursor-pointer"
              >
                <div className="font-medium">{surgeon.first_name} {surgeon.surname}</div>
                {surgeon.gmc_number && (
                  <div className="text-xs text-gray-500">GMC: {surgeon.gmc_number}</div>
                )}
                {surgeon.is_consultant && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 mt-1">
                    Consultant
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
