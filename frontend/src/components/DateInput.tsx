import { InputHTMLAttributes } from 'react'
import { X } from 'lucide-react'

interface DateInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  label?: string
  required?: boolean
  error?: string
}

export function DateInput({
  value,
  onChange,
  label,
  required = false,
  error,
  className = '',
  ...props
}: DateInputProps) {
  // Ensure value is a string (handle undefined/null)
  const normalizedValue = value || ''

  const handleClear = () => {
    onChange({ target: { value: '' } } as React.ChangeEvent<HTMLInputElement>)
  }

  return (
    <div className="relative">
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <div className="relative">
        <input
          type="date"
          value={normalizedValue}
          onChange={onChange}
          className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent
            ${!normalizedValue ? '[&::-webkit-datetime-edit-month-field]:text-transparent [&::-webkit-datetime-edit-day-field]:text-transparent [&::-webkit-datetime-edit-year-field]:text-transparent [&::-webkit-datetime-edit-text]:text-gray-400' : ''}
            ${error ? 'border-red-500' : ''} ${normalizedValue ? 'pr-10' : ''} ${className}`}
          {...props}
        />
        {normalizedValue && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Clear date"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
      {error && (
        <p className="mt-1 text-sm text-red-600">{error}</p>
      )}
    </div>
  )
}
