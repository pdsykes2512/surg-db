import { useState } from 'react'

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

  // Default filter function
  const defaultFilter = (option: T, search: string) => {
    return getOptionLabel(option).toLowerCase().includes(search.toLowerCase())
  }

  const filter = filterOption || defaultFilter

  // Filter options based on search
  const filteredOptions = options.filter((option) => filter(option, searchTerm))

  const handleSelect = (option: T) => {
    const val = getOptionValue(option)
    onChange(val)
    setSearchTerm(getOptionLabel(option))
    setShowDropdown(false)
  }

  // Default render function
  const defaultRender = (option: T) => (
    <div className="font-medium">{getOptionLabel(option)}</div>
  )

  const render = renderOption || defaultRender

  // Find the display value for the current selection
  const getDisplayValue = () => {
    if (searchTerm) return searchTerm
    if (!value) return ''
    
    // Find the option that matches the current value
    const selectedOption = options.find(opt => getOptionValue(opt) === value)
    return selectedOption ? getOptionLabel(selectedOption) : value
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
          value={getDisplayValue()}
          onChange={(e) => {
            setSearchTerm(e.target.value)
            setShowDropdown(true)
          }}
          onFocus={() => setShowDropdown(true)}
          onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          placeholder={placeholder}
          disabled={disabled}
        />
        {showDropdown && filteredOptions.length > 0 && !disabled && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
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
