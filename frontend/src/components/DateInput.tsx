import { InputHTMLAttributes } from 'react'

interface DateInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  label?: string
  required?: boolean
  placeholder?: string
  error?: string
}

export function DateInput({
  value,
  onChange,
  label,
  required = false,
  placeholder,
  error,
  className = '',
  ...props
}: DateInputProps) {
  // If no placeholder provided, use label as placeholder
  const displayPlaceholder = placeholder || label

  return (
    <div className="relative">
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <div className="relative">
        {!value && displayPlaceholder && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none text-sm">
            {displayPlaceholder}
          </span>
        )}
        <input
          type="date"
          value={value}
          onChange={onChange}
          className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent [&::-webkit-calendar-picker-indicator]:opacity-100 ${
            error ? 'border-red-500' : ''
          } ${className}`}
          style={!value ? { color: 'transparent' } : {}}
          {...props}
        />
      </div>
      {error && (
        <p className="mt-1 text-sm text-red-600">{error}</p>
      )}
    </div>
  )
}
