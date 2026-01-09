# React Components

This directory contains all React components for the IMPACT frontend application.

## Structure

Components are organized by function and complexity:

```
components/
├── common/          # Reusable UI primitives
├── forms/           # Complex multi-step forms
├── layout/          # Page layout and navigation
├── modals/          # Dialog/modal components
└── search/          # Search and autocomplete components
```

## Component Categories

### Common Components (`common/`)
Reusable UI primitives used throughout the application:

- **`Button.tsx`** - Styled button with variants (primary, secondary, danger)
- **`Table.tsx`** - Responsive data table with sorting and pagination
- **`Card.tsx`** - Container component with consistent styling
- **`LoadingSpinner.tsx`** - Loading indicator
- **`Pagination.tsx`** - Pagination controls for lists
- **`DateInput.tsx`** - Date picker with validation
- **`DateInputTypeable.tsx`** - Date input with typing support
- **`SearchableSelect.tsx`** - Dropdown with search/filter
- **`Toast.tsx`** - Notification/toast messages
- **`PageHeader.tsx`** - Page title with actions

### Forms (`forms/`)
Complex multi-step forms for data entry:

- **`EpisodeForm.tsx`** - Simple episode creation form
- **`CancerEpisodeForm.tsx`** - Comprehensive 6-step cancer episode form
  - Patient details, referral, tumour, diagnosis, treatment, investigation

### Layout (`layout/`)
Application layout and navigation:

- **`Layout.tsx`** - Main layout with header, nav, and content area
  - Responsive mobile navigation with hamburger menu
  - User authentication state display
- **`ProtectedRoute.tsx`** - Route guard for authenticated pages

### Modals (`modals/`)
Dialog components for viewing and editing data:

- **`PatientModal.tsx`** - Create/edit patient demographics
- **`CancerEpisodeDetailModal.tsx`** - View/edit full cancer episode with tabs
- **`EpisodeDetailModal.tsx`** - View/edit simple episode
- **`TumourModal.tsx`** - Create/edit tumour with TNM staging
- **`AddTreatmentModal.tsx`** - Multi-step treatment creation
- **`InvestigationModal.tsx`** - Create/edit investigation
- **`FollowUpModal.tsx`** - Schedule follow-up appointments
- **`TreatmentSummaryModal.tsx`** - View treatment details
- **`TumourSummaryModal.tsx`** - View tumour details
- **`HelpDialog.tsx`** - Contextual help and keyboard shortcuts
- **`SurgeryTypeSelectionModal.tsx`** - Select surgery type (primary/RTT/reversal)
- **`OncologyTypeSelectionModal.tsx`** - Select oncology treatment type

### Search (`search/`)
Specialized search and autocomplete components:

- **`PatientSearch.tsx`** - Patient lookup by MRN/NHS/ID
- **`SurgeonSearch.tsx`** - Clinician search with GMC code
- **`NHSProviderSelect.tsx`** - NHS trust and hospital selection

## Component Patterns

### TypeScript Interfaces
All components use TypeScript for type safety:

```typescript
/**
 * Props for the PatientModal component
 */
interface PatientModalProps {
  /** Existing patient data for edit mode, null for create mode */
  patient?: Patient | null;
  /** Callback fired when modal is closed */
  onClose: () => void;
  /** Callback fired when form is submitted */
  onSubmit: (data: PatientFormData) => void;
  /** Whether the form is currently submitting */
  loading?: boolean;
}
```

### State Management
Components use React hooks for local state:

```typescript
import { useState, useEffect } from 'react'

export function MyComponent() {
  // Form data state
  const [formData, setFormData] = useState<FormData>(initialState)
  
  // Loading state
  const [isLoading, setIsLoading] = useState(false)
  
  // Error state
  const [error, setError] = useState<string>('')
  
  // Effects
  useEffect(() => {
    // Load data on mount
    fetchData()
  }, [])
}
```

### Custom Hooks
Shared logic extracted into custom hooks:

- **`useModalShortcuts`** - Keyboard shortcuts for modals (Esc, Cmd+Enter)
- **`usePatients`** - Fetch and manage patient list
- **`useClinicians`** - Fetch and manage clinician list

### Modal Pattern
Modals use React Portals and consistent structure:

```typescript
import { createPortal } from 'react-dom'

export function MyModal({ onClose, onSubmit }: ModalProps) {
  return createPortal(
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-2 sm:p-4"
      style={{ margin: 0 }}  // Override browser defaults
    >
      <div className="bg-white rounded-lg shadow-xl max-w-full sm:max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-4 sm:px-6 py-3 sm:py-4">
          <h2>Modal Title</h2>
        </div>
        
        {/* Body */}
        <div className="p-4 sm:p-6">
          {/* Content */}
        </div>
        
        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 border-t px-4 sm:px-6 py-3 sm:py-4">
          <Button onClick={onSubmit}>Save</Button>
          <Button onClick={onClose} variant="secondary">Cancel</Button>
        </div>
      </div>
    </div>,
    document.body
  )
}
```

### Form Validation
Forms validate inputs and show errors:

```typescript
const [validationError, setValidationError] = useState<string>('')

const handleSubmit = () => {
  // Validate required fields
  if (!formData.required_field) {
    setValidationError('This field is required')
    return
  }
  
  // Validate format
  if (!/^pattern$/.test(formData.field)) {
    setValidationError('Invalid format')
    return
  }
  
  // Clear error and submit
  setValidationError('')
  onSubmit(formData)
}
```

## Responsive Design

All components follow mobile-first responsive design:

### Breakpoints
- **sm:** 640px (large phones)
- **md:** 768px (tablets)
- **lg:** 1024px (laptops)
- **xl:** 1280px (desktops)

### Responsive Patterns
```typescript
// Padding scales with screen size
className="px-4 sm:px-6 md:px-8"

// Grid columns adapt
className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4"

// Text size scales
className="text-base sm:text-lg md:text-xl"

// Show/hide elements
className="hidden md:block"  // Hidden on mobile
className="md:hidden"  // Hidden on desktop
```

### Touch Targets
All interactive elements meet WCAG 2.1 minimum touch target size (44×44px):

```typescript
<Button className="min-h-[44px]">Click Me</Button>
```

## Styling

Components use Tailwind CSS utility classes:

### Common Patterns
```typescript
// Cards
className="bg-white rounded-lg shadow-md p-4"

// Buttons
className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"

// Forms
className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"

// Grid layouts
className="grid grid-cols-1 sm:grid-cols-2 gap-4"
```

### Color Scheme
See `docs/development/STYLE_GUIDE.md` for comprehensive color palette and usage guidelines.

## API Integration

Components use centralized API service:

```typescript
import { apiService } from '../../services/api'

const fetchPatients = async () => {
  try {
    setIsLoading(true)
    const { data } = await apiService.patients.list({ search })
    setPatients(data)
  } catch (error) {
    console.error('Error fetching patients:', error)
    setError('Failed to load patients')
  } finally {
    setIsLoading(false)
  }
}
```

## Keyboard Shortcuts

Many components support keyboard shortcuts for power users:

- **Escape** - Close modal/dialog
- **Cmd/Ctrl + Enter** - Submit form
- **Cmd/Ctrl + S** - Save (preventDefault browser save)
- **Arrow keys** - Navigate dropdowns

Implemented via `useModalShortcuts` hook or custom event listeners.

## Accessibility

All components follow WCAG 2.1 Level AA standards:

- **Semantic HTML** - Use proper elements (button, input, label)
- **ARIA labels** - Add aria-label for icon-only buttons
- **Keyboard navigation** - All interactive elements focusable
- **Focus indicators** - Visible focus rings (focus:ring-2)
- **Color contrast** - Minimum 4.5:1 for text
- **Touch targets** - Minimum 44×44px

## Testing

Components should be tested for:
- Rendering with valid props
- User interactions (click, type, submit)
- Error states and validation
- Loading states
- Accessibility (keyboard navigation, screen reader)

## Adding New Components

When creating new components:

1. **Choose correct directory** - Based on function (modal, form, common, etc.)
2. **Use TypeScript** - Define all props and state interfaces
3. **Add JSDoc** - Document component purpose and props
4. **Follow patterns** - Use established patterns for modals, forms, etc.
5. **Responsive design** - Mobile-first with appropriate breakpoints
6. **Accessibility** - WCAG 2.1 compliance
7. **Error handling** - Show meaningful error messages
8. **Loading states** - Indicate async operations

### Component Template
```typescript
import { useState } from 'react'

/**
 * ComponentName - Brief description
 * 
 * Detailed description of component purpose and behavior.
 * 
 * @example
 * ```tsx
 * <ComponentName prop1="value" onAction={handleAction} />
 * ```
 */

/**
 * Props for the ComponentName component
 */
interface ComponentNameProps {
  /** Description of prop1 */
  prop1: string;
  /** Optional prop with default */
  prop2?: boolean;
  /** Callback function */
  onAction: (data: DataType) => void;
}

export function ComponentName({ prop1, prop2 = false, onAction }: ComponentNameProps) {
  const [state, setState] = useState<StateType>(initial)
  
  const handleAction = () => {
    // Implementation
    onAction(data)
  }
  
  return (
    <div className="component-container">
      {/* Component JSX */}
    </div>
  )
}
```

## Performance Optimization

- **Lazy loading** - Use React.lazy() for large components
- **Memoization** - Use useMemo() for expensive calculations
- **useCallback** - Prevent unnecessary re-renders
- **Virtual scrolling** - For long lists (>100 items)
- **Debounce** - For search inputs and API calls

## Common Issues

### Modal not closing on backdrop click
Ensure backdrop has `onClick={onClose}` and content div has `onClick={(e) => e.stopPropagation()}`

### Form not submitting on Enter
Add `onSubmit={handleSubmit}` to form element and `e.preventDefault()` in handler

### Responsive layout broken
Check that all grid/flex containers have proper responsive classes with breakpoints

### TypeScript errors
Ensure all props are properly typed and optional props have `?` or default values
