import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'

const API_URL = 'http://localhost:8000'

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
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check for stored token on mount
    const storedToken = localStorage.getItem('token')
    const storedUser = localStorage.getItem('user')
    
    if (storedToken && storedUser) {
      setToken(storedToken)
      setUser(JSON.parse(storedUser))
      // Set default authorization header
      axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
    }
    setLoading(false)
  }, [])

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
      
      const { access_token, user: userData } = response.data
      setToken(access_token)
      setUser(userData)
      
      // Store in localStorage
      localStorage.setItem('token', access_token)
      localStorage.setItem('user', JSON.stringify(userData))
      
      // Set default authorization header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
    } catch (error: any) {
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail)
      }
      throw new Error('Login failed')
    }
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    delete axios.defaults.headers.common['Authorization']
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
    hasRole
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
