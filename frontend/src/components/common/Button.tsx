import { ButtonHTMLAttributes, ReactNode } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'outline'
  size?: 'small' | 'medium' | 'large'
  children: ReactNode
  icon?: ReactNode
}

export function Button({ 
  variant = 'primary', 
  size = 'medium', 
  children, 
  icon,
  className = '',
  disabled,
  type = 'button',
  ...props 
}: ButtonProps) {
  const baseClasses = 'inline-flex items-center justify-center font-medium rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2'
  
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500 disabled:bg-blue-300',
    secondary: 'bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500 disabled:bg-gray-300',
    success: 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500 disabled:bg-green-300',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500 disabled:bg-red-300',
    outline: 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 focus:ring-blue-500 disabled:bg-gray-100'
  }
  
  const sizeClasses = {
    small: 'px-3 py-2 text-sm min-h-[44px]',  // Meets WCAG 44px minimum touch target
    medium: 'px-4 py-2 text-sm min-h-[44px]',
    large: 'px-6 py-3 text-base min-h-[48px]'
  }

  return (
    <button
      type={type}
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className} ${disabled ? 'cursor-not-allowed opacity-50' : ''}`}
      disabled={disabled}
      {...props}
    >
      {icon && <span className="mr-2">{icon}</span>}
      {children}
    </button>
  )
}
