import { ReactNode, useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import axios from 'axios'
import packageJson from '../../../package.json'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [version, setVersion] = useState(packageJson.version)

  useEffect(() => {
    // Fetch version from backend API to verify sync
    // When using Vite proxy (VITE_API_URL=/api), access root endpoint through proxy
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
    const rootUrl = API_URL === '/api' ? '/' : API_URL.replace('/api', '')

    axios.get(rootUrl)
      .then(response => {
        if (response.data?.version) {
          // Use backend version if available and different
          if (response.data.version !== packageJson.version) {
            setVersion(`${packageJson.version} (API: ${response.data.version})`)
          }
        }
      })
      .catch(() => {
        // Silent fail - use package.json version
      })
  }, [])

  const isActive = (path: string) => {
    if (path === '/episodes') {
      return location.pathname === path || location.pathname.startsWith('/episodes/')
    }
    return location.pathname === path
  }

  const navLinkClass = (path: string) => {
    const base = "px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-200"
    return isActive(path)
      ? `${base} bg-blue-600 text-white`
      : `${base} text-gray-700 hover:bg-gray-100`
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo and Title */}
            <Link to="/" className="flex items-center hover:opacity-80 transition-opacity">
              <div className="flex-shrink-0">
                <svg className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div className="ml-2 sm:ml-3">
                <h1 className="text-lg sm:text-xl font-bold text-gray-900">IMPACT</h1>
                <p className="text-xs text-gray-500 hidden sm:block">Audit Care & Treatment</p>
              </div>
            </Link>

            {/* Navigation */}
            <nav className="hidden md:flex space-x-2">
              <Link to="/" className={navLinkClass('/')}>
                Dashboard
              </Link>
              <Link to="/patients" className={navLinkClass('/patients')}>
                Patients
              </Link>
              <Link to="/episodes" className={navLinkClass('/episodes')}>
                Episodes
              </Link>
              <Link to="/reports" className={navLinkClass('/reports')}>
                Reports
              </Link>
              {user?.role === 'admin' && (
                <Link to="/admin" className={navLinkClass('/admin')}>
                  Admin
                </Link>
              )}
            </nav>

            {/* User Menu */}
            <div className="flex items-center space-x-2 sm:space-x-4">
              <div className="hidden sm:flex flex-col items-end">
                <span className="text-sm font-medium text-gray-900">{user?.full_name}</span>
                <span className="text-xs text-gray-500">{user?.email}</span>
              </div>
              <button
                onClick={logout}
                className="hidden sm:block px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Logout
              </button>
              {/* Mobile Menu Button */}
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="md:hidden p-2 rounded-lg text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label="Toggle mobile menu"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {mobileMenuOpen ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  )}
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-gray-200 bg-white shadow-lg">
            <nav className="py-2 space-y-1">
              <Link
                to="/"
                className={`block px-4 py-2 text-sm font-medium transition-colors duration-200 ${
                  isActive('/')
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
                onClick={() => setMobileMenuOpen(false)}
              >
                Dashboard
              </Link>
              <Link
                to="/patients"
                className={`block px-4 py-2 text-sm font-medium transition-colors duration-200 ${
                  isActive('/patients')
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
                onClick={() => setMobileMenuOpen(false)}
              >
                Patients
              </Link>
              <Link
                to="/episodes"
                className={`block px-4 py-2 text-sm font-medium transition-colors duration-200 ${
                  isActive('/episodes')
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
                onClick={() => setMobileMenuOpen(false)}
              >
                Episodes
              </Link>
              <Link
                to="/reports"
                className={`block px-4 py-2 text-sm font-medium transition-colors duration-200 ${
                  isActive('/reports')
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
                onClick={() => setMobileMenuOpen(false)}
              >
                Reports
              </Link>
              {user?.role === 'admin' && (
                <Link
                  to="/admin"
                  className={`block px-4 py-2 text-sm font-medium transition-colors duration-200 ${
                    isActive('/admin')
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Admin
                </Link>
              )}
              <div className="pt-2 border-t border-gray-200 mt-2">
                <div className="px-4 py-2 text-sm">
                  <p className="font-medium text-gray-900">{user?.full_name}</p>
                  <p className="text-xs text-gray-500">{user?.email}</p>
                </div>
                <button
                  onClick={() => {
                    logout()
                    setMobileMenuOpen(false)
                  }}
                  className="w-full text-left px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
                >
                  Logout
                </button>
              </div>
            </nav>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-grow w-full">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center flex-wrap gap-2">
            <div className="flex items-center gap-4">
              <p className="text-sm text-gray-500">
                © 2025 IMPACT. All rights reserved.
              </p>
              <span className="text-sm text-gray-400 hidden sm:inline">•</span>
              <button
                onClick={() => {
                  const event = new KeyboardEvent('keydown', { key: '?', shiftKey: true, code: 'Slash' });
                  document.dispatchEvent(event);
                }}
                className="text-sm text-blue-600 hover:text-blue-800 transition-colors hidden sm:inline"
                title="Show keyboard shortcuts help"
              >
                Press <kbd className="px-1.5 py-0.5 text-xs font-mono bg-gray-100 border border-gray-300 rounded">?</kbd> for shortcuts
              </button>
            </div>
            <div className="flex space-x-4 text-sm text-gray-500">
              <span>Version {version}</span>
              <span className="hidden sm:inline">•</span>
              <span className="hidden sm:inline">Logged in as {user?.email}</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
