import { ReactNode } from 'react'

/**
 * Universal Table Components
 *
 * Standardized table components with consistent styling across the application.
 * All tables should use these components to maintain uniform appearance.
 *
 * Responsive Styling:
 * - Table headers: px-2 sm:px-4 md:px-6 py-2 md:py-3, uppercase text, gray background
 * - Table cells: px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm
 * - Clickable rows: hover:bg-blue-50 cursor-pointer transition-colors
 * - Summary modal fields: py-2 (8px vertical padding)
 *
 * Mobile Optimizations:
 * - Reduced horizontal padding on small screens (px-2 → px-6)
 * - Overflow-x-auto for horizontal scrolling when needed
 * - Scroll indicator shadow for better UX
 *
 * All cells include whitespace-nowrap by default to prevent text wrapping
 * and maintain consistent row heights. Override with className if needed.
 *
 * Usage:
 * <Table>
 *   <TableHeader>
 *     <TableRow>
 *       <TableHeadCell>Column 1</TableHeadCell>
 *       <TableHeadCell>Column 2</TableHeadCell>
 *     </TableRow>
 *   </TableHeader>
 *   <TableBody>
 *     <TableRow onClick={() => {}}>
 *       <TableCell className="text-gray-900">Data 1</TableCell>
 *       <TableCell className="text-gray-500">Data 2</TableCell>
 *     </TableRow>
 *   </TableBody>
 * </Table>
 */

interface TableProps {
  children: ReactNode
  className?: string
}

export function Table({ children, className = '' }: TableProps) {
  return (
    <div className={`overflow-x-auto shadow-sm ${className}`}>
      <table className="min-w-full divide-y divide-gray-200">
        {children}
      </table>
    </div>
  )
}

interface TableHeaderProps {
  children: ReactNode
}

export function TableHeader({ children }: TableHeaderProps) {
  return (
    <thead className="bg-gray-50">
      {children}
    </thead>
  )
}

interface TableBodyProps {
  children: ReactNode
}

export function TableBody({ children }: TableBodyProps) {
  return (
    <tbody className="bg-white divide-y divide-gray-200">
      {children}
    </tbody>
  )
}

interface TableRowProps {
  children: ReactNode
  onClick?: () => void
  className?: string
}

export function TableRow({ children, onClick, className = '' }: TableRowProps) {
  const baseClass = onClick ? 'hover:bg-blue-50 cursor-pointer transition-colors' : ''
  return (
    <tr className={`${baseClass} ${className}`} onClick={onClick}>
      {children}
    </tr>
  )
}

interface TableHeadCellProps {
  children: ReactNode
  className?: string
}

export function TableHeadCell({ children, className = '' }: TableHeadCellProps) {
  return (
    <th className={`px-2 sm:px-4 md:px-6 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${className}`}>
      {children}
    </th>
  )
}

interface TableCellProps {
  children: ReactNode
  className?: string
  onClick?: (e: React.MouseEvent) => void
  colSpan?: number
}

export function TableCell({ children, className = '', onClick, colSpan }: TableCellProps) {
  return (
    <td className={`px-2 sm:px-4 md:px-6 py-3 md:py-4 whitespace-nowrap text-sm ${className}`} onClick={onClick} colSpan={colSpan}>
      {children}
    </td>
  )
}
