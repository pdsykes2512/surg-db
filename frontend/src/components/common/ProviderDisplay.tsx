import { useState, useEffect } from 'react'

interface ProviderDisplayProps {
  code: string | null | undefined
  showCode?: boolean
  className?: string
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
 * Display NHS provider name with dynamic lookup
 * Fetches the full provider name from the API and displays it
 */
export function ProviderDisplay({ code, showCode = true, className = '' }: ProviderDisplayProps) {
  const [providerName, setProviderName] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    const fetchProviderName = async () => {
      if (!code) {
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        setError(false)

        const API_URL = import.meta.env.VITE_API_URL || '/api'
        const response = await fetch(`${API_URL}/nhs-providers/${code}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })

        if (response.ok) {
          const provider = await response.json()
          const formatted = formatProviderName(provider.name)
          setProviderName(formatted)
        } else {
          setError(true)
        }
      } catch (err) {
        console.error('Error fetching provider name:', err)
        setError(true)
      } finally {
        setLoading(false)
      }
    }

    fetchProviderName()
  }, [code])

  if (!code) return null

  if (loading) {
    return <span className={className}>{code}</span>
  }

  if (error || !providerName) {
    return <span className={className}>{code}</span>
  }

  return (
    <span className={className}>
      {providerName}
      {showCode && <span className="text-gray-500"> ({code})</span>}
    </span>
  )
}
