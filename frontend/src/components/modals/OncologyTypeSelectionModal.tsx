/**
 * Oncology Treatment Type Selection Modal
 * Allows user to select between Chemotherapy, Radiotherapy, Immunotherapy, etc.
 */
import React, { useState, useEffect } from 'react'
import { useModalShortcuts } from '../../hooks/useModalShortcuts'

interface OncologyTypeSelectionModalProps {
  isOpen: boolean
  onClose: () => void
  onSelectType: (type: 'chemotherapy' | 'radiotherapy' | 'immunotherapy' | 'hormone_therapy' | 'targeted_therapy') => void
}

export function OncologyTypeSelectionModal({
  isOpen,
  onClose,
  onSelectType
}: OncologyTypeSelectionModalProps) {
  const [focusedIndex, setFocusedIndex] = useState(0)

  // Enable Escape key to close modal
  useModalShortcuts({
    onClose,
    isOpen
  })

  const treatmentTypes = [
    {
      type: 'chemotherapy' as const,
      title: 'Chemotherapy',
      description: 'Systemic chemotherapy regimen',
      icon: '💊',
      color: 'purple'
    },
    {
      type: 'radiotherapy' as const,
      title: 'Radiotherapy',
      description: 'Radiation therapy',
      icon: '☢️',
      color: 'orange'
    },
    {
      type: 'immunotherapy' as const,
      title: 'Immunotherapy',
      description: 'Immune checkpoint inhibitors',
      icon: '🛡️',
      color: 'indigo'
    },
    {
      type: 'hormone_therapy' as const,
      title: 'Hormone Therapy',
      description: 'Hormonal treatment',
      icon: '💉',
      color: 'pink'
    },
    {
      type: 'targeted_therapy' as const,
      title: 'Targeted Therapy',
      description: 'Targeted molecular therapy',
      icon: '🎯',
      color: 'cyan'
    }
  ]

  // Keyboard navigation for treatment type selection
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
        e.preventDefault()
        setFocusedIndex(prev => (prev + 1) % treatmentTypes.length)
      } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
        e.preventDefault()
        setFocusedIndex(prev => (prev - 1 + treatmentTypes.length) % treatmentTypes.length)
      } else if (e.key === 'Enter') {
        e.preventDefault()
        onSelectType(treatmentTypes[focusedIndex].type)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, focusedIndex, treatmentTypes, onSelectType])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="relative w-full max-w-3xl bg-white rounded-lg shadow-xl">
          {/* Header */}
          <div className="border-b border-gray-200 px-6 py-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Select Oncology Treatment
            </h2>
            <button
              onClick={onClose}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {treatmentTypes.map((treatment, index) => (
                <button
                  key={treatment.type}
                  onClick={() => onSelectType(treatment.type)}
                  className={`p-6 border-2 rounded-lg hover:border-${treatment.color}-500 hover:bg-${treatment.color}-50 transition text-left group ${
                    focusedIndex === index
                      ? `border-${treatment.color}-500 bg-${treatment.color}-50 ring-2 ring-${treatment.color}-500`
                      : `border-${treatment.color}-200`
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className={`text-lg font-semibold text-gray-900 group-hover:text-${treatment.color}-700`}>
                        {treatment.title}
                      </h3>
                      <p className="text-sm text-gray-600 mt-1">
                        {treatment.description}
                      </p>
                    </div>
                    <span className="text-3xl ml-4">{treatment.icon}</span>
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>Note:</strong> For surgical treatments (primary surgery, RTT, stoma reversal),
                please use the "Add Surgical Rx" button instead.
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="border-t border-gray-200 px-6 py-4 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
