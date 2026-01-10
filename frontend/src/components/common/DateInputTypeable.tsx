import { useRef, useState, useEffect } from 'react'

interface DateInputTypeableProps {
  value: string // YYYY-MM-DD format
  onChange: (e: { target: { value: string } }) => void
  label?: string
  required?: boolean
  error?: string
  disabled?: boolean
}

/**
 * Custom date input component that allows manual typing with auto-advance
 * between day, month, and year fields. Converts to/from YYYY-MM-DD format.
 */
export function DateInputTypeable({
  value,
  onChange,
  label,
  required = false,
  error,
  disabled = false,
}: DateInputTypeableProps) {
  const dayRef = useRef<HTMLInputElement>(null)
  const monthRef = useRef<HTMLInputElement>(null)
  const yearRef = useRef<HTMLInputElement>(null)

  // Parse YYYY-MM-DD to DD/MM/YYYY
  const parseValue = (val: string) => {
    if (!val) return { day: '', month: '', year: '' }
    const match = val.match(/^(\d{4})-(\d{2})-(\d{2})$/)
    if (match) {
      return {
        day: match[3],
        month: match[2],
        year: match[1],
      }
    }
    return { day: '', month: '', year: '' }
  }

  const parsed = parseValue(value)
  const [day, setDay] = useState(parsed.day)
  const [month, setMonth] = useState(parsed.month)
  const [year, setYear] = useState(parsed.year)

  // Update local state when prop changes
  useEffect(() => {
    const parsed = parseValue(value)
    setDay(parsed.day)
    setMonth(parsed.month)
    setYear(parsed.year)
  }, [value])

  // Convert DD/MM/YYYY to YYYY-MM-DD and notify parent
  const emitChange = (d: string, m: string, y: string) => {
    if (d && m && y) {
      // Pad values
      const paddedDay = d.padStart(2, '0')
      const paddedMonth = m.padStart(2, '0')
      const fullYear = y.padStart(4, '0')

      // Validate basic ranges
      const dayNum = parseInt(paddedDay, 10)
      const monthNum = parseInt(paddedMonth, 10)
      const yearNum = parseInt(fullYear, 10)

      if (
        dayNum >= 1 &&
        dayNum <= 31 &&
        monthNum >= 1 &&
        monthNum <= 12 &&
        yearNum >= 1900 &&
        yearNum <= 2100
      ) {
        const isoDate = `${fullYear}-${paddedMonth}-${paddedDay}`
        onChange({ target: { value: isoDate } })
      }
    } else if (!d && !m && !y) {
      // All fields cleared
      onChange({ target: { value: '' } })
    }
  }

  const handleDayChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/\D/g, '') // Only digits
    if (val.length <= 2) {
      setDay(val)
      emitChange(val, month, year)

      // Auto-advance if 2 digits entered and valid
      if (val.length === 2 && parseInt(val, 10) >= 1 && parseInt(val, 10) <= 31) {
        monthRef.current?.focus()
      }
    }
  }

  const handleMonthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/\D/g, '')
    if (val.length <= 2) {
      setMonth(val)
      emitChange(day, val, year)

      // Auto-advance if 2 digits entered and valid
      if (val.length === 2 && parseInt(val, 10) >= 1 && parseInt(val, 10) <= 12) {
        yearRef.current?.focus()
      } else if (val.length === 1 && parseInt(val, 10) > 1) {
        // If user types 2-9, auto-advance (since month can't be >12)
        yearRef.current?.focus()
      }
    }
  }

  const handleYearChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/\D/g, '')
    if (val.length <= 4) {
      setYear(val)
      emitChange(day, month, val)

      // Blur when 4 digits entered
      if (val.length === 4) {
        yearRef.current?.blur()
      }
    }
  }

  const handleDayKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !day) {
      // Don't go back further
    } else if (e.key === 'ArrowRight' || e.key === '/') {
      e.preventDefault()
      monthRef.current?.focus()
    }
  }

  const handleMonthKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !month) {
      e.preventDefault()
      dayRef.current?.focus()
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault()
      dayRef.current?.focus()
    } else if (e.key === 'ArrowRight' || e.key === '/') {
      e.preventDefault()
      yearRef.current?.focus()
    }
  }

  const handleYearKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !year) {
      e.preventDefault()
      monthRef.current?.focus()
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault()
      monthRef.current?.focus()
    }
  }

  const handleClear = () => {
    setDay('')
    setMonth('')
    setYear('')
    onChange({ target: { value: '' } })
    dayRef.current?.focus()
  }

  const hasValue = day || month || year

  return (
    <div>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <div className="relative flex items-center gap-0.5 px-3 h-10 bg-white border border-gray-300 rounded-lg focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent">
        <input
          ref={dayRef}
          type="text"
          inputMode="numeric"
          placeholder="DD"
          value={day}
          onChange={handleDayChange}
          onKeyDown={handleDayKeyDown}
          disabled={disabled}
          className={`w-8 text-center bg-transparent border-none focus:outline-none focus:ring-0 p-0 ${
            error ? 'text-red-600' : 'text-gray-900'
          }`}
          maxLength={2}
        />
        <span className="text-gray-400">/</span>
        <input
          ref={monthRef}
          type="text"
          inputMode="numeric"
          placeholder="MM"
          value={month}
          onChange={handleMonthChange}
          onKeyDown={handleMonthKeyDown}
          disabled={disabled}
          className={`w-8 text-center bg-transparent border-none focus:outline-none focus:ring-0 p-0 ${
            error ? 'text-red-600' : 'text-gray-900'
          }`}
          maxLength={2}
        />
        <span className="text-gray-400">/</span>
        <input
          ref={yearRef}
          type="text"
          inputMode="numeric"
          placeholder="YYYY"
          value={year}
          onChange={handleYearChange}
          onKeyDown={handleYearKeyDown}
          disabled={disabled}
          className={`w-12 text-center bg-transparent border-none focus:outline-none focus:ring-0 p-0 ${
            error ? 'text-red-600' : 'text-gray-900'
          }`}
          maxLength={4}
        />
        {hasValue && !disabled && (
          <button
            type="button"
            onClick={handleClear}
            className="ml-auto text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
            aria-label="Clear date"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  )
}
