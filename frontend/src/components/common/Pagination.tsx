import { Button } from './Button'

export interface PaginationProps {
  currentPage: number
  totalItems: number
  pageSize: number
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
  pageSizeOptions?: number[]
  loading?: boolean
}

export function Pagination({
  currentPage,
  totalItems,
  pageSize,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [25, 50, 100],
  loading = false
}: PaginationProps) {
  // Calculate total pages
  const totalPages = Math.ceil(totalItems / pageSize) || 1

  // Calculate current range
  const startItem = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1
  const endItem = Math.min(currentPage * pageSize, totalItems)

  // Don't show pagination if only one page
  if (totalPages <= 1 && totalItems <= pageSize) {
    return null
  }

  // Generate page numbers with smart ellipsis
  const getPageNumbers = (): (number | 'ellipsis')[] => {
    const pages: (number | 'ellipsis')[] = []

    if (totalPages <= 7) {
      // Show all pages if 7 or fewer
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i)
      }
    } else {
      // Always show first page
      pages.push(1)

      if (currentPage <= 3) {
        // Near the beginning: 1 2 3 4 5 ... 10
        pages.push(2, 3, 4, 5, 'ellipsis', totalPages)
      } else if (currentPage >= totalPages - 2) {
        // Near the end: 1 ... 6 7 8 9 10
        pages.push('ellipsis', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages)
      } else {
        // In the middle: 1 ... 4 5 6 7 8 ... 10
        pages.push('ellipsis', currentPage - 2, currentPage - 1, currentPage, currentPage + 1, currentPage + 2, 'ellipsis', totalPages)
      }
    }

    return pages
  }

  const pageNumbers = getPageNumbers()

  return (
    <div className="bg-gray-50 border-t border-gray-200 px-6 py-4">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        {/* Range display */}
        <div className="text-sm text-gray-700">
          Showing <span className="font-medium">{startItem}</span> to{' '}
          <span className="font-medium">{endItem}</span> of{' '}
          <span className="font-medium">{totalItems}</span>{' '}
          {totalItems === 1 ? 'result' : 'results'}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="secondary"
            size="small"
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1 || loading}
          >
            ← Previous
          </Button>

          {/* Page numbers */}
          {pageNumbers.map((page, index) => {
            if (page === 'ellipsis') {
              return (
                <span key={`ellipsis-${index}`} className="px-2 text-gray-500">
                  ...
                </span>
              )
            }

            return (
              <button
                key={page}
                onClick={() => onPageChange(page)}
                disabled={loading}
                className={`min-w-[2.5rem] h-10 px-3 text-sm font-medium rounded-lg transition-colors ${
                  currentPage === page
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {page}
              </button>
            )
          })}

          <Button
            variant="secondary"
            size="small"
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages || loading}
          >
            Next →
          </Button>
        </div>

        {/* Page size selector */}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-600">Show</span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            disabled={loading}
            className={`border border-gray-300 rounded-lg px-2 py-1.5 focus:ring-2 focus:ring-blue-500 focus:outline-none ${
              loading ? 'opacity-50 cursor-not-allowed bg-gray-100' : 'bg-white'
            }`}
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
          <span className="text-gray-600">per page</span>
        </div>
      </div>

      {/* Loading indicator on separate row below pagination */}
      {loading && (
        <div className="flex items-center justify-center gap-2 text-blue-600 pt-3 mt-3 border-t border-gray-200">
          <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-xs font-medium">Loading...</span>
        </div>
      )}
    </div>
  )
}
