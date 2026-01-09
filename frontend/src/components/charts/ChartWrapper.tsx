import React, { useRef } from 'react'
import { Button } from '../common/Button'

interface ChartWrapperProps {
  title: string
  subtitle?: string
  children: React.ReactNode
  onExport?: () => void
  loading?: boolean
  empty?: boolean
  emptyMessage?: string
  height?: number
  className?: string
}

/**
 * Wrapper component for all charts
 * Provides consistent styling, loading states, and export functionality
 */
export function ChartWrapper({
  title,
  subtitle,
  children,
  onExport,
  loading = false,
  empty = false,
  emptyMessage = 'No data available',
  height = 300,
  className = ''
}: ChartWrapperProps) {
  const chartRef = useRef<HTMLDivElement>(null)

  const handleExport = () => {
    if (onExport) {
      onExport()
    } else {
      // Default export functionality - export as PNG using html2canvas if needed
      console.log('Export functionality not implemented for this chart')
    }
  }

  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-4 sm:p-6 ${className}`}>
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          {subtitle && (
            <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
        {onExport && !loading && !empty && (
          <Button
            variant="outline"
            size="small"
            onClick={handleExport}
            className="ml-4"
          >
            <svg
              className="w-4 h-4 mr-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            Export
          </Button>
        )}
      </div>

      {/* Content */}
      <div ref={chartRef} style={{ height: `${height}px` }} className="relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75">
            <div className="flex flex-col items-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="text-sm text-gray-500 mt-2">Loading chart...</p>
            </div>
          </div>
        )}

        {!loading && empty && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <svg
                className="w-12 h-12 mx-auto text-gray-400 mb-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
              <p className="text-sm text-gray-500">{emptyMessage}</p>
            </div>
          </div>
        )}

        {!loading && !empty && children}
      </div>
    </div>
  )
}
