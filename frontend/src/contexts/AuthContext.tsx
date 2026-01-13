import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback, useRef } from 'react'
import axios from 'axios'
import { useNavigate, useLocation } from 'react-router-dom'
import { getSessionManager, destroySessionManager, SessionEventType } from '../utils/sessionManager'
import { SessionWarningModal } from '../components/modals/SessionWarningModal'

// Use empty string for relative URLs when VITE_API_URL is /api (uses Vite proxy)
// Otherwise fall back to localhost for direct backend access
const API_URL = import.meta.env.VITE_API_URL === '/api' ? '' : (import.meta.env.VITE_API_URL?.replace('/api', '') || 'http://localhost:8000')

interface User {
  _id: string
  email: string
  full_name: string
  role: 'admin' | 'surgeon' | 'data_entry' | 'viewer'
  is_active: boolean
  department?: string
  job_title?: string
  created_at: string
  last_login?: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  register: (email: string, password: string, full_name: string) => Promise<void>
  loading: boolean
  isAuthenticated: boolean
  hasRole: (roles: string[]) => boolean
  extendSession: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [refreshToken, setRefreshToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [showWarning, setShowWarning] = useState(false)
  const [timeRemaining, setTimeRemaining] = useState(0)
  const navigate = useNavigate()
  const location = useLocation()
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Clear any existing tokens and session
  const clearAuth = useCallback(() => {
    setToken(null)
    setUser(null)
    setRefreshToken(null)
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('tokenExpiry')
    delete axios.defaults.headers.common['Authorization']
    
    // Stop session manager
    destroySessionManager()
    
    // Clear refresh interval
    if (refreshIntervalRef.current) {
      clearInterval(refreshIntervalRef.current)
      refreshIntervalRef.current = null
    }
  }, [])

  // Refresh access token using refresh token
  const refreshAccessToken = useCallback(async () => {
    const storedRefreshToken = localStorage.getItem('refreshToken')
    if (!storedRefreshToken) {
      clearAuth()
      return false
    }

    try {
      const response = await axios.post(`${API_URL}/api/auth/refresh`, {
        refresh_token: storedRefreshToken
      })

      const { access_token, refresh_token: new_refresh_token, expires_in, user: userData } = response.data
      
      setToken(access_token)
      setRefreshToken(new_refresh_token)
      setUser(userData)
      
      // Store in localStorage
      localStorage.setItem('token', access_token)
      localStorage.setItem('refreshToken', new_refresh_token)
      localStorage.setItem('user', JSON.stringify(userData))
      localStorage.setItem('tokenExpiry', String(Date.now() + expires_in * 1000))
      
      // Set default authorization header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      
      return true
    } catch (error) {
      console.error('Failed to refresh token:', error)
      clearAuth()
      return false
    }
  }, [clearAuth])

  // Handle session events
  const handleSessionEvent = useCallback((event: SessionEventType) => {
    if (event === 'warning') {
      // Show warning dialog
      setShowWarning(true)
      const manager = getSessionManager()
      setTimeRemaining(manager.getTimeRemaining())
    } else if (event === 'timeout') {
      // Session has expired
      setShowWarning(false)
      clearAuth()
      // Save intended destination
      const intendedPath = location.pathname !== '/login' ? location.pathname : '/'
      localStorage.setItem('intendedPath', intendedPath)
      navigate('/login', { state: { sessionExpired: true } })
    } else if (event === 'refreshed') {
      // Auto-refresh token when nearing expiry
      refreshAccessToken()
    }
  }, [clearAuth, navigate, location.pathname, refreshAccessToken])

  // Extend session (refresh token)
  const extendSession = useCallback(async () => {
    setShowWarning(false)
    const success = await refreshAccessToken()
    if (success) {
      // Reset session manager - force record activity to bypass throttling
      const manager = getSessionManager()
      manager.recordActivity(true) // Force parameter bypasses throttling
    }
  }, [refreshAccessToken])

  // Logout
  const logout = useCallback(() => {
    clearAuth()
    navigate('/login')
  }, [clearAuth, navigate])

  useEffect(() => {
    // Check for stored token on mount
    const storedToken = localStorage.getItem('token')
    const storedUser = localStorage.getItem('user')
    const storedRefreshToken = localStorage.getItem('refreshToken')
    const tokenExpiry = localStorage.getItem('tokenExpiry')
    
    if (storedToken && storedUser && storedRefreshToken) {
      // Check if token has expired
      if (tokenExpiry && Date.now() > parseInt(tokenExpiry)) {
        // Try to refresh
        refreshAccessToken().then(success => {
          if (!success) {
            clearAuth()
            navigate('/login')
          }
          setLoading(false)
        })
      } else {
        setToken(storedToken)
        setUser(JSON.parse(storedUser))
        setRefreshToken(storedRefreshToken)
        // Set default authorization header
        axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
        setLoading(false)
      }
    } else {
      setLoading(false)
    }
  }, [clearAuth, navigate, refreshAccessToken])

  // Start session manager when user is authenticated
  useEffect(() => {
    if (user && token) {
      // Initialize session manager with configurable timeouts from environment variables
      const manager = getSessionManager({
        timeoutMinutes: parseInt(import.meta.env.VITE_SESSION_TIMEOUT_MINUTES || '30'),
        warningMinutes: parseInt(import.meta.env.VITE_SESSION_WARNING_MINUTES || '5'),
        refreshThresholdMinutes: parseInt(import.meta.env.VITE_SESSION_REFRESH_THRESHOLD_MINUTES || '10')
      })
      
      manager.on(handleSessionEvent)
      manager.start()
      
      return () => {
        manager.off(handleSessionEvent)
        manager.stop()
      }
    } else {
      destroySessionManager()
    }
  }, [user, token, handleSessionEvent])

  const login = async (email: string, password: string) => {
    try {
      const formData = new FormData()
      formData.append('username', email) // OAuth2 expects 'username'
      formData.append('password', password)
      
      const response = await axios.post(`${API_URL}/api/auth/login`, formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      })
      
      const { access_token, refresh_token, expires_in, user: userData } = response.data
      setToken(access_token)
      setRefreshToken(refresh_token)
      setUser(userData)
      
      // Store in localStorage
      localStorage.setItem('token', access_token)
      localStorage.setItem('refreshToken', refresh_token)
      localStorage.setItem('user', JSON.stringify(userData))
      localStorage.setItem('tokenExpiry', String(Date.now() + expires_in * 1000))
      
      // Set default authorization header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      
      // Check for intended destination
      const intendedPath = localStorage.getItem('intendedPath')
      if (intendedPath) {
        localStorage.removeItem('intendedPath')
        navigate(intendedPath)
      }
    } catch (error: any) {
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail)
      }
      throw new Error('Login failed')
    }
  }

  const register = async (email: string, password: string, full_name: string) => {
    try {
      await axios.post(`${API_URL}/api/auth/register`, {
        email,
        password,
        full_name,
        role: 'viewer' // Default role
      })
      
      // Auto-login after registration
      await login(email, password)
    } catch (error: any) {
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail)
      }
      throw new Error('Registration failed')
    }
  }

  const hasRole = (roles: string[]): boolean => {
    if (!user) return false
    return roles.includes(user.role)
  }

  const value = {
    user,
    token,
    login,
    logout,
    register,
    loading,
    isAuthenticated: !!user && !!token,
    hasRole,
    extendSession
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
      <SessionWarningModal
        isOpen={showWarning}
        timeRemaining={timeRemaining}
        onExtend={extendSession}
        onLogout={logout}
      />
    </AuthContext.Provider>
  )
}
