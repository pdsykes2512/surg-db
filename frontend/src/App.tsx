import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useHotkeys } from 'react-hotkeys-hook'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'
import { AuthProvider } from './contexts/AuthContext'
import { HomePage } from './pages/HomePage'
import { PatientsPage } from './pages/PatientsPage'
import { EpisodesPage } from './pages/EpisodesPage'
import { ReportsPage } from './pages/ReportsPage'
import { LoginPage } from './pages/LoginPage'
import { AdminPage } from './pages/AdminPage'
import { ProtectedRoute } from './components/layout/ProtectedRoute'
import { Layout } from './components/layout/Layout'
import { HelpDialog } from './components/modals/HelpDialog'

// Configure React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // Data fresh for 5 minutes
      gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes (formerly cacheTime)
      refetchOnWindowFocus: false, // Don't refetch on window focus
      retry: 1, // Retry failed requests once
    },
  },
})

function AppContent() {
  const [showHelpDialog, setShowHelpDialog] = useState(false)

  // Global keyboard shortcuts: ? to open help dialog, Cmd+1-4 for page navigation
  useHotkeys('shift+slash', () => {
    console.log('Help dialog shortcut triggered')
    setShowHelpDialog(true)
  }, { 
    preventDefault: true,
    enableOnFormTags: ['INPUT', 'TEXTAREA', 'SELECT']
  })
  useKeyboardShortcuts() // Page navigation (Cmd+1-4) - works here because we're inside Router

  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout>
                <HomePage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/patients"
          element={
            <ProtectedRoute requiredRoles={['data_entry', 'surgeon', 'admin']}>
              <Layout>
                <PatientsPage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/episodes/:patientId"
          element={
            <ProtectedRoute requiredRoles={['data_entry', 'surgeon', 'admin']}>
              <Layout>
                <EpisodesPage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/episodes"
          element={
            <ProtectedRoute requiredRoles={['data_entry', 'surgeon', 'admin']}>
              <Layout>
                <EpisodesPage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/reports"
          element={
            <ProtectedRoute>
              <Layout>
                <ReportsPage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRoles={['admin']}>
              <Layout>
                <AdminPage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      {showHelpDialog && <HelpDialog onClose={() => setShowHelpDialog(false)} />}
    </>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true
        }}
      >
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </Router>
    </QueryClientProvider>
  )
}

export default App
