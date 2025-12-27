import { useState, useEffect, useCallback } from 'react'

interface NHSProvider {
  code: string
  name: string
  type?: string
  active?: boolean
}

interface NHSProviderSelectProps {
  value: string
  onChange: (value: string) => void
  label?: string
  required?: boolean
  placeholder?: string
  className?: string
  disabled?: boolean
}

/**
 * Format provider name to Title Case with NHS properly capitalized
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
 * NHS Provider searchable select component with dynamic lookup via ODS API
 * Searches local cache first, then queries NHS ODS API if needed
 */
export function NHSProviderSelect({
  value,
  onChange,
  label,
  required = false,
  placeholder = 'Search NHS Trust...',
  className = '',
  disabled = false
}: NHSProviderSelectProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [providers, setProviders] = useState<NHSProvider[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Sync searchTerm with value prop when it changes
  useEffect(() => {
    if (value) {
      // If we have a value (code), fetch the name to display
      const fetchProviderName = async () => {
        try {
          // Use /api for relative URLs (uses Vite proxy)
          const API_URL = import.meta.env.VITE_API_URL || '/api'
          const response = await fetch(`${API_URL}/nhs-providers/${value}`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          })
          if (response.ok) {
            const provider = await response.json()
            setSearchTerm(`${formatProviderName(provider.name)} (${provider.code})`)
          } else {
            // If lookup fails, just show the code
            setSearchTerm(value)
          }
        } catch (err) {
          setSearchTerm(value)
        }
      }
      fetchProviderName()
    } else {
      setSearchTerm('')
    }
  }, [value])

  // Debounced search function
  const searchProviders = useCallback(async (query: string) => {
    if (query.length < 2) {
      setProviders([])
      return
    }

    setLoading(true)
    setError(null)

    try {
      // Use /api for relative URLs (uses Vite proxy)
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(
        `${API_URL}/nhs-providers/search?query=${encodeURIComponent(query)}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      )

      if (!response.ok) {
        throw new Error('Failed to search NHS providers')
      }

      const results = await response.json()
      setProviders(results)
    } catch (err) {
      console.error('Error searching NHS providers:', err)
      setError('Failed to search NHS providers. Please try again.')
      setProviders([])
    } finally {
      setLoading(false)
    }
  }, [])

  // Debounce search
  useEffect(() => {
    if (showDropdown && searchTerm.length >= 2) {
      const timer = setTimeout(() => {
        searchProviders(searchTerm)
      }, 300)
      return () => clearTimeout(timer)
    } else {
      setProviders([])
    }
  }, [searchTerm, showDropdown, searchProviders])

  const handleSelect = (provider: NHSProvider) => {
    onChange(provider.code)
    setSearchTerm(`${provider.name} (${provider.code})`)
    setShowDropdown(false)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    setSearchTerm(newValue)
    setShowDropdown(true)
    
    // If user clears the input, clear the selection
    if (!newValue) {
      onChange('')
    }
  }

  return (
    <div className={`relative ${className}`}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      
      <input
        type="text"
        value={searchTerm}
        onChange={handleInputChange}
        onFocus={() => setShowDropdown(true)}
        onBlur={() => {
          // Delay to allow click on dropdown
          setTimeout(() => setShowDropdown(false), 200)
        }}
        placeholder={placeholder}
        disabled={disabled}
        required={required}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
      />

      {/* Dropdown */}
      {showDropdown && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {loading && (
            <div className="px-4 py-3 text-sm text-gray-500 text-center">
              Searching NHS providers...
            </div>
          )}
          
          {error && (
            <div className="px-4 py-3 text-sm text-red-600">
              {error}
            </div>
          )}
          
          {!loading && !error && providers.length === 0 && searchTerm.length >= 2 && (
            <div className="px-4 py-3 text-sm text-gray-500 text-center">
              No NHS providers found. Try a different search.
            </div>
          )}
          
          {!loading && !error && searchTerm.length < 2 && (
            <div className="px-4 py-3 text-sm text-gray-500 text-center">
              Type at least 2 characters to search
            </div>
          )}
          
          {providers.map((provider) => (
            <div
              key={provider.code}
              onClick={() => handleSelect(provider)}
              className="px-4 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
            >
              <div className="font-medium text-gray-900">
                {formatProviderName(provider.name)}
              </div>
              <div className="text-sm text-gray-500">
                Code: {provider.code}
                {provider.type && ` • ${formatProviderName(provider.type)}`}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
