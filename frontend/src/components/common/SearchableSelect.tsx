import { useState, useEffect } from 'react'

interface SearchableSelectProps<T> {
  value: string
  onChange: (value: string) => void
  options: T[]
  getOptionValue: (option: T) => string
  getOptionLabel: (option: T) => string
  renderOption?: (option: T) => React.ReactNode
  filterOption?: (option: T, search: string) => boolean
  label?: string
  required?: boolean
  placeholder?: string
  className?: string
  disabled?: boolean
}

/**
 * Generic searchable dropdown component
 * Can be used for any type of autocomplete search
 */
export function SearchableSelect<T>({
  value,
  onChange,
  options,
  getOptionValue,
  getOptionLabel,
  renderOption,
  filterOption,
  label,
  required = false,
  placeholder = 'Search...',
  className = '',
  disabled = false
}: SearchableSelectProps<T>) {
  const [searchTerm, setSearchTerm] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [isEditing, setIsEditing] = useState(false)

  // Sync searchTerm with value prop when it changes (but not while user is actively editing)
  useEffect(() => {
    if (!isEditing) {
      if (value) {
        const selectedOption = options.find(opt => getOptionValue(opt) === value)
        if (selectedOption) {
          setSearchTerm(getOptionLabel(selectedOption))
        } else {
          // If no matching option found, display the raw value (for legacy/mismatched data)
          setSearchTerm(value)
        }
      } else {
        setSearchTerm('')
      }
    }
  }, [value, options, getOptionValue, getOptionLabel, isEditing])

  // Default filter function
  const defaultFilter = (option: T, search: string) => {
    return getOptionLabel(option).toLowerCase().includes(search.toLowerCase())
  }

  const filter = filterOption || defaultFilter

  // Filter options based on search
  // If search is empty, show all options (up to a reasonable limit)
  const filteredOptions = searchTerm.trim() === ''
    ? options.slice(0, 100)  // Show first 100 options when no search
    : options.filter((option) => filter(option, searchTerm))

  const handleSelect = (option: T) => {
    const val = getOptionValue(option)
    const label = getOptionLabel(option)
    onChange(val)
    setSearchTerm(label)
    setShowDropdown(false)
  }

  // Default render function
  const defaultRender = (option: T) => (
    <div className="font-medium">{getOptionLabel(option)}</div>
  )

  const render = renderOption || defaultRender

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
          value={searchTerm}
          onChange={(e) => {
            const newValue = e.target.value
            setSearchTerm(newValue)
            setShowDropdown(true)
            setIsEditing(true)
          }}
          onFocus={() => {
            setShowDropdown(true)
            setIsEditing(true)
          }}
          onBlur={() => {
            setTimeout(() => {
              setShowDropdown(false)
              setIsEditing(false)
              // Reset searchTerm to show selected value label when blurred
              if (value) {
                const selectedOption = options.find(opt => getOptionValue(opt) === value)
                if (selectedOption) {
                  setSearchTerm(getOptionLabel(selectedOption))
                }
              } else {
                setSearchTerm('')
              }
            }, 200)
          }}
          className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          placeholder={placeholder}
          disabled={disabled}
        />
        {value && !disabled && (
          <button
            type="button"
            onMouseDown={(e) => {
              e.preventDefault()
              onChange('')
              setSearchTerm('')
              setShowDropdown(false)
              setIsEditing(false)
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
        {showDropdown && filteredOptions.length > 0 && !disabled && (
          <div className="absolute z-[100] w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
            {filteredOptions.map((option, index) => (
              <div
                key={index}
                onMouseDown={() => handleSelect(option)}
                className="px-4 py-2 hover:bg-blue-50 cursor-pointer"
              >
                {render(option)}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
