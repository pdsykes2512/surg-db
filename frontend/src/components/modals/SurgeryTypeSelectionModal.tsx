/**
 * Surgery Type Selection Modal
 * Allows user to select between Primary Surgery, RTT, or Stoma Reversal
 */
import React from 'react'
import { Treatment } from '../../types/models'

interface SurgeryTypeSelectionModalProps {
  isOpen: boolean
  onClose: () => void
  onSelectType: (type: 'primary' | 'rtt' | 'reversal', parentSurgery?: Treatment) => void
  episodeTreatments: Treatment[]
  episodeId: string
}

export function SurgeryTypeSelectionModal({
  isOpen,
  onClose,
  onSelectType,
  episodeTreatments
}: SurgeryTypeSelectionModalProps) {
  if (!isOpen) return null

  // Get primary surgeries for RTT/reversal selection
  const primarySurgeries = episodeTreatments.filter(
    t => t.treatment_type === 'surgery_primary'
  )

  // Find surgeries with open stomas (for reversal)
  const surgeriesWithOpenStomas = primarySurgeries.filter(
    t => t.intraoperative?.stoma_created && !t.intraoperative?.stoma_closure_date
  )

  const [selectedPrimaryForRTT, setSelectedPrimaryForRTT] = React.useState<string | null>(null)
  const [selectedPrimaryForReversal, setSelectedPrimaryForReversal] = React.useState<string | null>(null)
  const [showRTTSelection, setShowRTTSelection] = React.useState(false)
  const [showReversalSelection, setShowReversalSelection] = React.useState(false)

  const handlePrimaryClick = () => {
    onSelectType('primary')
  }

  const handleRTTClick = () => {
    if (primarySurgeries.length === 0) return
    if (primarySurgeries.length === 1) {
      // Only one primary surgery, select it automatically
      onSelectType('rtt', primarySurgeries[0])
    } else {
      // Multiple primary surgeries, show selection
      setShowRTTSelection(true)
    }
  }

  const handleReversalClick = () => {
    if (surgeriesWithOpenStomas.length === 0) return
    if (surgeriesWithOpenStomas.length === 1) {
      // Only one surgery with open stoma, select it automatically
      onSelectType('reversal', surgeriesWithOpenStomas[0])
    } else {
      // Multiple surgeries with stomas, show selection
      setShowReversalSelection(true)
    }
  }

  const handleRTTParentSelect = (surgeryId: string) => {
    const surgery = primarySurgeries.find(s => s.treatment_id === surgeryId)
    if (surgery) {
      onSelectType('rtt', surgery)
    }
  }

  const handleReversalParentSelect = (surgeryId: string) => {
    const surgery = surgeriesWithOpenStomas.find(s => s.treatment_id === surgeryId)
    if (surgery) {
      onSelectType('reversal', surgery)
    }
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A'
    return new Date(dateStr).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    })
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="relative w-full max-w-2xl bg-white rounded-lg shadow-xl">
          {/* Header */}
          <div className="border-b border-gray-200 px-6 py-4">
            <h2 className="text-xl font-semibold text-gray-900">
              {showRTTSelection && 'Select Surgery for RTT'}
              {showReversalSelection && 'Select Surgery for Reversal'}
              {!showRTTSelection && !showReversalSelection && 'Select Surgery Type'}
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
            {!showRTTSelection && !showReversalSelection && (
              <div className="space-y-4">
                {/* Primary Surgery */}
                <button
                  onClick={handlePrimaryClick}
                  className="w-full p-6 border-2 border-blue-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition text-left group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 group-hover:text-blue-700">
                        Primary Surgery
                      </h3>
                      <p className="text-sm text-gray-600 mt-1">
                        New surgical procedure for this episode
                      </p>
                    </div>
                    <span className="text-4xl">🔪</span>
                  </div>
                </button>

                {/* Return to Theatre */}
                <button
                  onClick={handleRTTClick}
                  disabled={primarySurgeries.length === 0}
                  className="w-full p-6 border-2 border-amber-200 rounded-lg hover:border-amber-500 hover:bg-amber-50 transition text-left group disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:border-amber-200 disabled:hover:bg-white"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 group-hover:text-amber-700">
                        Return to Theatre (RTT)
                      </h3>
                      <p className="text-sm text-gray-600 mt-1">
                        Unplanned return for complication or issue
                      </p>
                      {primarySurgeries.length === 0 && (
                        <p className="text-xs text-red-600 mt-2 font-medium">
                          ⚠️ No primary surgeries in this episode
                        </p>
                      )}
                      {primarySurgeries.length > 0 && (
                        <p className="text-xs text-gray-500 mt-2">
                          {primarySurgeries.length} primary {primarySurgeries.length === 1 ? 'surgery' : 'surgeries'} available
                        </p>
                      )}
                    </div>
                    <span className="text-4xl">⚠️</span>
                  </div>
                </button>

                {/* Stoma Reversal */}
                <button
                  onClick={handleReversalClick}
                  disabled={surgeriesWithOpenStomas.length === 0}
                  className="w-full p-6 border-2 border-green-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition text-left group disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:border-green-200 disabled:hover:bg-white"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 group-hover:text-green-700">
                        Stoma Reversal
                      </h3>
                      <p className="text-sm text-gray-600 mt-1">
                        Planned reversal of previous stoma
                      </p>
                      {surgeriesWithOpenStomas.length === 0 && (
                        <p className="text-xs text-red-600 mt-2 font-medium">
                          ⚠️ No open stomas in this episode
                        </p>
                      )}
                      {surgeriesWithOpenStomas.length > 0 && (
                        <p className="text-xs text-gray-500 mt-2">
                          {surgeriesWithOpenStomas.length} open {surgeriesWithOpenStomas.length === 1 ? 'stoma' : 'stomas'} available
                        </p>
                      )}
                    </div>
                    <span className="text-4xl">✅</span>
                  </div>
                </button>
              </div>
            )}

            {/* RTT Parent Surgery Selection */}
            {showRTTSelection && (
              <div className="space-y-3">
                <p className="text-sm text-gray-600 mb-4">
                  Select the primary surgery this RTT is related to:
                </p>
                {primarySurgeries.map(surgery => (
                  <div
                    key={surgery.treatment_id}
                    onClick={() => handleRTTParentSelect(surgery.treatment_id)}
                    className="p-4 border-2 border-gray-200 rounded-lg hover:border-amber-500 hover:bg-amber-50 cursor-pointer transition"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-medium text-gray-900">
                          {surgery.procedure_name || 'Unknown procedure'}
                        </div>
                        <div className="text-sm text-gray-600 mt-1">
                          {formatDate(surgery.treatment_date)} - {surgery.surgeon || 'Unknown surgeon'}
                        </div>
                      </div>
                      <span className="text-sm font-medium text-gray-500">
                        {surgery.treatment_id}
                      </span>
                    </div>
                  </div>
                ))}
                <button
                  onClick={() => setShowRTTSelection(false)}
                  className="w-full mt-4 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  ← Back
                </button>
              </div>
            )}

            {/* Reversal Parent Surgery Selection */}
            {showReversalSelection && (
              <div className="space-y-3">
                <p className="text-sm text-gray-600 mb-4">
                  Select the surgery with the stoma to reverse:
                </p>
                {surgeriesWithOpenStomas.map(surgery => (
                  <div
                    key={surgery.treatment_id}
                    onClick={() => handleReversalParentSelect(surgery.treatment_id)}
                    className="p-4 border-2 border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 cursor-pointer transition"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-medium text-gray-900">
                          {surgery.procedure_name || 'Unknown procedure'}
                        </div>
                        <div className="text-sm text-gray-600 mt-1">
                          {formatDate(surgery.treatment_date)} - {surgery.surgeon || 'Unknown surgeon'}
                        </div>
                        {surgery.intraoperative?.stoma_type && (
                          <div className="text-sm text-gray-700 mt-1 font-medium">
                            Stoma: {surgery.intraoperative.stoma_type.replace(/_/g, ' ')}
                          </div>
                        )}
                      </div>
                      <span className="text-sm font-medium text-gray-500">
                        {surgery.treatment_id}
                      </span>
                    </div>
                  </div>
                ))}
                <button
                  onClick={() => setShowReversalSelection(false)}
                  className="w-full mt-4 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  ← Back
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
