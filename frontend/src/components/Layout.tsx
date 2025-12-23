import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth()
  const location = useLocation()

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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo and Title */}
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div className="ml-3">
                <h1 className="text-xl font-bold text-gray-900">Surgical Outcomes</h1>
                <p className="text-xs text-gray-500">Database & Analytics</p>
              </div>
            </div>

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
            <div className="flex items-center">
              <button
                onClick={logout}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-500">
              © 2025 Surgical Outcomes Database. All rights reserved.
            </p>
            <div className="flex space-x-4 text-sm text-gray-500">
              <span>Version 1.0.0</span>
              <span>•</span>
              <span>Logged in as {user?.email}</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
