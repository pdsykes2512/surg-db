import { createPortal } from 'react-dom'
import { Button } from '../common/Button'
import { useModalShortcuts } from '../../hooks/useModalShortcuts'

interface Shortcut {
  category: string
  key: string
  description: string
  context?: string
}

interface HelpDialogProps {
  onClose: () => void
}

export function HelpDialog({ onClose }: HelpDialogProps) {
  // Detect platform for correct key symbols
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
  const modKey = isMac ? '⌘' : 'Ctrl'
  const shiftKey = isMac ? '⇧' : 'Shift'

  // Enable keyboard shortcuts for the help dialog itself
  useModalShortcuts({
    onClose,
    isOpen: true
  })

  // All available keyboard shortcuts
  const shortcuts: Shortcut[] = [
    // Modal Actions
    { category: 'Modal Actions', key: 'Esc', description: 'Close modal or dialog' },
    { category: 'Modal Actions', key: `${modKey} + Enter`, description: 'Submit form in modal' },

    // Quick Actions
    { category: 'Quick Actions', key: `${modKey} + ${shiftKey} + P`, description: 'Add Patient', context: 'Patients page' },
    { category: 'Quick Actions', key: `${modKey} + ${shiftKey} + E`, description: 'Add Episode', context: 'Episodes page' },
    { category: 'Quick Actions', key: `${modKey} + K`, description: 'Focus search input' },

    // Page Navigation
    { category: 'Page Navigation', key: `${modKey} + 1`, description: 'Go to Dashboard' },
    { category: 'Page Navigation', key: `${modKey} + 2`, description: 'Go to Patients' },
    { category: 'Page Navigation', key: `${modKey} + 3`, description: 'Go to Episodes' },
    { category: 'Page Navigation', key: `${modKey} + 4`, description: 'Go to Reports' },

    // Table Navigation
    { category: 'Table Navigation', key: '[', description: 'Previous page' },
    { category: 'Table Navigation', key: ']', description: 'Next page' },
    { category: 'Table Navigation', key: '↑ / ↓', description: 'Select row' },
    { category: 'Table Navigation', key: 'Enter', description: 'View selected row (open summary)' },
    { category: 'Table Navigation', key: 'E', description: 'Edit selected row' },
    { category: 'Table Navigation', key: `${shiftKey} + D`, description: 'Delete selected row' },

    // Summary Modals
    { category: 'Summary Modals', key: 'E', description: 'Edit from summary modal', context: 'Treatment/Tumour summary' },

    // Episode Detail Modal
    { category: 'Episode Detail Modal', key: 'I', description: 'Add Investigation', context: 'Episode detail' },
    { category: 'Episode Detail Modal', key: 'P', description: 'Add Pathology (Tumour)', context: 'Episode detail' },
    { category: 'Episode Detail Modal', key: 'S', description: 'Add Surgical Treatment', context: 'Episode detail' },
    { category: 'Episode Detail Modal', key: 'O', description: 'Add Oncology Treatment', context: 'Episode detail' },

    // Help
    { category: 'Help', key: '?', description: 'Show this help dialog' },
  ]

  // Group shortcuts by category
  const groupedShortcuts = shortcuts.reduce((acc, shortcut) => {
    if (!acc[shortcut.category]) {
      acc[shortcut.category] = []
    }
    acc[shortcut.category].push(shortcut)
    return acc
  }, {} as Record<string, Shortcut[]>)

  // Ensure modal root exists
  let modalRoot = document.getElementById('modal-root')
  if (!modalRoot) {
    modalRoot = document.createElement('div')
    modalRoot.id = 'modal-root'
    document.body.appendChild(modalRoot)
  }

  const content = (
    <div className="hidden md:flex fixed inset-0 bg-black bg-opacity-50 items-center justify-center z-50 p-4">
      <div
        className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-xl"
        role="dialog"
        aria-labelledby="help-dialog-title"
        aria-modal="true"
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between rounded-t-lg">
          <h2 id="help-dialog-title" className="text-xl font-semibold text-gray-900">
            Keyboard Shortcuts
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close help dialog"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          <p className="text-sm text-gray-600 mb-6">
            Use these keyboard shortcuts to navigate the IMPACT application more efficiently.
          </p>

          {Object.entries(groupedShortcuts).map(([category, items]) => (
            <div key={category} className="mb-6 last:mb-0">
              <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">
                {category}
              </h3>
              <div className="space-y-2">
                {items.map((shortcut, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
                  >
                    <div className="flex items-center space-x-4 flex-1">
                      <kbd className="px-3 py-1.5 bg-gray-100 border border-gray-300 rounded text-sm font-mono text-gray-800 min-w-[120px] text-center shadow-sm">
                        {shortcut.key}
                      </kbd>
                      <span className="text-sm text-gray-700">{shortcut.description}</span>
                    </div>
                    {shortcut.context && (
                      <span className="text-xs text-gray-500 italic ml-4">{shortcut.context}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="border-t px-6 py-4 bg-gray-50 rounded-b-lg">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500">
              Shortcuts automatically adapt to your platform ({isMac ? 'Mac' : 'Windows/Linux'})
            </p>
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </div>
    </div>
  )

  return createPortal(content, modalRoot)
}
