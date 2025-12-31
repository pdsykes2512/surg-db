import { useState, useCallback } from 'react'
import { useHotkeys } from 'react-hotkeys-hook'

interface UseTableNavigationOptions<T> {
  items: T[]
  onView?: (item: T) => void
  onEdit?: (item: T) => void
  onDelete?: (item: T) => void
  onPrevPage?: () => void
  onNextPage?: () => void
  canGoPrev?: boolean
  canGoNext?: boolean
  enabled?: boolean
}

/**
 * Custom hook for table keyboard navigation
 * - Arrow Up/Down: Select row
 * - Enter: View selected row (summary modal)
 * - E: Edit selected row
 * - Shift+D: Delete selected row
 * - [: Previous page
 * - ]: Next page
 *
 * @param options - Configuration for table navigation
 * @returns selectedIndex and reset function
 */
export function useTableNavigation<T>(options: UseTableNavigationOptions<T>) {
  const {
    items,
    onView,
    onEdit,
    onDelete,
    onPrevPage,
    onNextPage,
    canGoPrev = false,
    canGoNext = false,
    enabled = true
  } = options

  const [selectedIndex, setSelectedIndex] = useState<number>(-1)

  // Reset selection when items change (e.g., after pagination)
  const resetSelection = useCallback(() => {
    setSelectedIndex(-1)
  }, [])

  // Arrow Up - Select previous row
  // Note: Don't enable on form tags so arrow keys work normally in input fields
  useHotkeys(
    'up',
    (e) => {
      e.preventDefault()
      if (items.length === 0) return
      setSelectedIndex((prev) => {
        if (prev <= 0) return items.length - 1 // Wrap to bottom
        return prev - 1
      })
    },
    {
      enabled: enabled && items.length > 0,
      preventDefault: true
    },
    [items, enabled]
  )

  // Arrow Down - Select next row
  // Note: Don't enable on form tags so arrow keys work normally in input fields
  useHotkeys(
    'down',
    (e) => {
      e.preventDefault()
      if (items.length === 0) return
      setSelectedIndex((prev) => {
        if (prev >= items.length - 1) return 0 // Wrap to top
        return prev + 1
      })
    },
    {
      enabled: enabled && items.length > 0,
      preventDefault: true
    },
    [items, enabled]
  )

  // Enter - View selected row (summary modal)
  // Note: Don't enable on form tags so Enter works normally in input fields
  useHotkeys(
    'enter',
    (e) => {
      e.preventDefault()
      if (selectedIndex >= 0 && selectedIndex < items.length && onView) {
        onView(items[selectedIndex])
      }
    },
    {
      enabled: enabled && selectedIndex >= 0 && !!onView,
      preventDefault: true
    },
    [selectedIndex, items, onView, enabled]
  )

  // E - Edit selected row
  // Note: Don't enable on form tags so 'e' can be typed in filter boxes
  useHotkeys(
    'e',
    (e) => {
      e.preventDefault()
      if (selectedIndex >= 0 && selectedIndex < items.length && onEdit) {
        onEdit(items[selectedIndex])
      }
    },
    {
      enabled: enabled && selectedIndex >= 0 && !!onEdit,
      preventDefault: true
    },
    [selectedIndex, items, onEdit, enabled]
  )

  // Shift+D - Delete selected row
  useHotkeys(
    'shift+d',
    (e) => {
      e.preventDefault()
      if (selectedIndex >= 0 && selectedIndex < items.length && onDelete) {
        onDelete(items[selectedIndex])
      }
    },
    {
      enabled: enabled && selectedIndex >= 0 && !!onDelete,
      preventDefault: true,
      enableOnFormTags: ['INPUT', 'TEXTAREA', 'SELECT']
    },
    [selectedIndex, items, onDelete, enabled]
  )

  // [ - Previous page
  useHotkeys(
    'bracketleft',
    (e) => {
      e.preventDefault()
      if (canGoPrev && onPrevPage) {
        onPrevPage()
        resetSelection()
      }
    },
    {
      enabled: enabled && canGoPrev && !!onPrevPage,
      preventDefault: true,
      enableOnFormTags: ['INPUT', 'TEXTAREA', 'SELECT']
    },
    [canGoPrev, onPrevPage, resetSelection, enabled]
  )

  // ] - Next page
  useHotkeys(
    'bracketright',
    (e) => {
      e.preventDefault()
      if (canGoNext && onNextPage) {
        onNextPage()
        resetSelection()
      }
    },
    {
      enabled: enabled && canGoNext && !!onNextPage,
      preventDefault: true,
      enableOnFormTags: ['INPUT', 'TEXTAREA', 'SELECT']
    },
    [canGoNext, onNextPage, resetSelection, enabled]
  )

  return {
    selectedIndex,
    resetSelection
  }
}
