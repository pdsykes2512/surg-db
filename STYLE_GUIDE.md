# UI/UX Style Guide

> This document defines the design patterns and conventions for the surgical outcomes database frontend. **All new components and modifications must follow these guidelines to ensure consistency.**

## Table of Contents
- [Modals](#modals)
- [Buttons](#buttons)
- [Forms](#forms)
- [Tables](#tables)
- [Colors & Themes](#colors--themes)
- [Typography](#typography)
- [Layout & Spacing](#layout--spacing)

---

## Modals

### General Structure
All modals follow a three-section layout:
1. **Header** - Title, optional subtitle, close button
2. **Body** - Scrollable content area
3. **Footer** - Action buttons

### Form Modals (Create/Edit)
Used for: Adding or editing data (patients, treatments, investigations, etc.)

**Structure:**
```tsx
<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
  <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
    {/* Header */}
    <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
      <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
      <button onClick={onCancel} className="text-gray-400 hover:text-gray-600">
        {/* X icon */}
      </button>
    </div>
    
    {/* Body - Form Content */}
    <form onSubmit={handleSubmit} className="p-6 space-y-6">
      {/* Form fields */}
    </form>
    
    {/* Footer - Action Buttons */}
    <div className="flex justify-between items-center pt-4 border-t px-6 pb-6">
      <Button type="button" variant="secondary" onClick={onCancel}>
        Cancel
      </Button>
      <Button type="submit" variant="primary">
        {mode === 'edit' ? 'Update' : 'Add'} {Entity}
      </Button>
    </div>
  </div>
</div>
```

**Key Rules:**
- Cancel button on LEFT (secondary variant)
- Primary action button on RIGHT (primary variant)
- Use `justify-between` for button spacing
- Footer has `border-t` separator
- Delete button (if applicable) goes on LEFT next to Cancel

**Examples:** AddTreatmentModal, TumourModal, InvestigationModal, FollowUpModal, PatientModal

### Summary/Detail Modals (Read-Only)
Used for: Viewing details of existing records

**Structure:**
```tsx
<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
  <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
    {/* Header with gradient */}
    <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-3 flex justify-between items-center">
      <h2 className="text-xl font-semibold text-white">{title}</h2>
      <button onClick={onClose} className="text-white hover:text-gray-200">
        {/* X icon */}
      </button>
    </div>
    
    {/* Body - Read-only content */}
    <div className="p-6">
      {/* Display sections */}
    </div>
    
    {/* Footer */}
    <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 flex justify-between">
      <Button variant="secondary" onClick={onClose}>
        Close
      </Button>
      <Button variant="primary" onClick={onEdit}>
        Edit {Entity}
      </Button>
    </div>
  </div>
</div>
```

**Key Rules:**
- Colored gradient header for visual distinction
- Close button on LEFT (secondary variant)
- Edit button on RIGHT (primary variant)
- Gray background footer (`bg-gray-50`)
- Use `border-t border-gray-200` for footer separator

**Examples:** TreatmentSummaryModal, TumourSummaryModal, CancerEpisodeDetailModal

### Multi-Step Form Modals
Used for: Complex forms requiring multiple steps (e.g., surgery treatment recording)

**Additional Requirements:**
- **Progress indicator** in header showing steps
- **Step navigation** buttons (Previous/Next)
- **Conditional rendering** based on `currentStep` state
- **Clickable steps** in edit mode only (for jumping to specific sections)
- **Form submission guard** to prevent early submission

**Step Progress Indicator:**
```tsx
<div className="px-6 pb-4">
  <div className="flex items-center justify-between mb-2">
    {Array.from({ length: totalSteps }, (_, i) => i + 1).map((step) => (
      <div key={step} className="flex items-center flex-1">
        <button
          onClick={() => mode === 'edit' ? setCurrentStep(step) : undefined}
          disabled={mode === 'create'}
          className={`w-8 h-8 rounded-full ${
            currentStep === step ? 'bg-blue-600 text-white' :
            currentStep > step ? 'bg-green-600 text-white' :
            'bg-gray-200 text-gray-600'
          } ${mode === 'edit' ? 'cursor-pointer hover:ring-2' : 'cursor-default'}`}
        >
          {currentStep > step ? '✓' : step}
        </button>
        <div className="text-xs mt-1">{getStepTitle(step)}</div>
      </div>
    ))}
  </div>
</div>
```

**Navigation Buttons:**
```tsx
<div className="flex justify-between items-center pt-4 border-t">
  <Button type="button" variant="secondary" onClick={onCancel}>
    Cancel
  </Button>
  <div className="flex space-x-3">
    {currentStep > 1 && (
      <Button type="button" variant="secondary" onClick={prevStep}>
        ← Previous
      </Button>
    )}
    {currentStep < totalSteps ? (
      <Button type="button" variant="primary" onClick={nextStep}>
        Next →
      </Button>
    ) : (
      <Button type="submit" variant="primary">
        {mode === 'edit' ? 'Update' : 'Add'} {Entity}
      </Button>
    )}
  </div>
</div>
```

**Key Rules:**
- Cancel on LEFT, navigation buttons on RIGHT together
- Previous button only shows from step 2 onwards
- Submit button only appears on final step
- Prevent form submission unless on final step
- Use `e.preventDefault()` and `e.stopPropagation()` in step navigation

**Example:** AddTreatmentModal (4 steps for surgery, 2 steps for other treatments)

### Modal Sizing
- **Small forms:** `max-w-md` (e.g., simple input modals)
- **Standard forms:** `max-w-2xl` (e.g., most CRUD modals)
- **Large forms:** `max-w-4xl` (e.g., tumour, pathology)
- **Extra large:** `max-w-6xl` (e.g., episode details with multiple sections)
- **Always include:** `max-h-[90vh] overflow-y-auto` for scrolling

---

## Buttons

### Button Component
Use the `<Button>` component from `/components/Button.tsx` for all buttons.

### Variants
```tsx
<Button variant="primary">Primary Action</Button>    // Blue - Main action
<Button variant="secondary">Secondary</Button>       // Gray - Cancel/Close
<Button variant="success">Success</Button>           // Green - Confirm
<Button variant="danger">Delete</Button>             // Red - Destructive
<Button variant="outline">Outline</Button>           // White with border
```

### Sizes
```tsx
<Button size="small">Small</Button>
<Button size="medium">Medium</Button>   // Default
<Button size="large">Large</Button>
```

### Button Type
- **Submit buttons:** `type="submit"` (triggers form submission)
- **Action buttons:** `type="button"` (prevents form submission)
- **Navigation buttons:** `type="button"` with `onClick` handler

### Placement Rules
1. **Primary action** always on the RIGHT (blue/primary variant)
2. **Cancel/Close** always on the LEFT (gray/secondary variant)
3. **Destructive actions** (Delete) on the LEFT, separate from primary
4. **Navigation buttons** (Previous/Next) grouped together on the RIGHT
5. Use `justify-between` for left-right split, `space-x-3` for grouped buttons

---

## Forms

### Form Layout
```tsx
<form onSubmit={handleSubmit} className="p-6 space-y-6">
  {/* Use space-y-6 for vertical spacing between sections */}
</form>
```

### Field Grouping
```tsx
{/* Single field */}
<div>
  <label className="block text-sm font-medium text-gray-700 mb-1">
    Field Label {required && '*'}
  </label>
  <input className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
</div>

{/* Two columns */}
<div className="grid grid-cols-2 gap-4">
  <div>{/* Field 1 */}</div>
  <div>{/* Field 2 */}</div>
</div>

{/* Three columns */}
<div className="grid grid-cols-3 gap-4">
  <div>{/* Field 1 */}</div>
  <div>{/* Field 2 */}</div>
  <div>{/* Field 3 */}</div>
</div>
```

### Field Sections
Use colored backgrounds to group related fields:
```tsx
{/* Clinical section - Gray background */}
<div className="bg-gray-50 p-4 rounded-lg space-y-4">
  <h4 className="text-sm font-semibold text-gray-900">Section Title</h4>
  {/* Fields */}
</div>

{/* Important section - Amber background */}
<div className="bg-amber-50 p-4 rounded-lg space-y-4">
  <h4 className="text-sm font-semibold text-gray-900">Important Details</h4>
  {/* Fields */}
</div>

{/* NBOCA/Audit requirement - Blue background */}
<div className="bg-blue-50 p-4 rounded-lg space-y-4">
  <h4 className="text-sm font-semibold text-gray-900">NBOCA Required Fields</h4>
  {/* Fields */}
</div>
```

### Input Components
- **Text input:** Native `<input type="text">` with Tailwind classes
- **Date input:** `<DateInput>` component from `/components/DateInput.tsx`
- **Select/Dropdown:** `<SearchableSelect>` component from `/components/SearchableSelect.tsx`
- **Surgeon search:** `<SurgeonSearch>` component from `/components/SurgeonSearch.tsx`
- **NHS Provider:** `<NHSProviderSelect>` component from `/components/NHSProviderSelect.tsx`
- **Textarea:** Native `<textarea>` with `rows={3}` minimum

### Conditional Fields
```tsx
{/* Checkbox trigger */}
<label className="flex items-center">
  <input
    type="checkbox"
    checked={formData.fieldEnabled}
    onChange={(e) => setFormData({ ...formData, fieldEnabled: e.target.checked })}
    className="mr-2 h-4 w-4"
  />
  <span className="text-sm font-medium text-gray-700">Enable Additional Fields</span>
</label>

{/* Conditional content - indented with ml-6 */}
{formData.fieldEnabled && (
  <div className="ml-6 space-y-4">
    {/* Nested fields */}
  </div>
)}
```

### Helper Text
```tsx
<p className="text-xs text-gray-500 mt-1">
  Helper text explaining the field or providing examples
</p>
```

### Required Fields
- Mark with `*` in label
- Add `required` attribute to input
- Use red border for validation errors (if implementing validation feedback)

---

## Tables

### Table Component
**Always use the `<Table>` component** from `/components/Table.tsx` for all data tables. Never use raw `<table>` HTML elements.

### Basic Structure
```tsx
import { Table, TableHeader, TableBody, TableRow, TableHeadCell, TableCell } from '../components/Table'

<Table>
  <TableHeader>
    <TableRow>
      <TableHeadCell>Column 1</TableHeadCell>
      <TableHeadCell>Column 2</TableHeadCell>
      <TableHeadCell>Column 3</TableHeadCell>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow onClick={() => handleRowClick(item)}>
      <TableCell className="font-medium text-gray-900">{item.id}</TableCell>
      <TableCell className="text-gray-900">{item.name}</TableCell>
      <TableCell className="text-gray-500">{item.status}</TableCell>
    </TableRow>
  </TableBody>
</Table>
```

### Component Styling
The Table components provide consistent styling:

**Table Wrapper:**
- `overflow-x-auto` - Horizontal scrolling on small screens
- `min-w-full` - Full width table
- `divide-y divide-gray-200` - Row dividers

**TableHeader:**
- `bg-gray-50` - Light gray background
- Header rows have uppercase text

**TableHeadCell:**
- `px-6 py-3` - Consistent padding
- `text-left text-xs font-medium text-gray-500 uppercase tracking-wider`
- Use for all column headers

**TableBody:**
- `bg-white` - White background
- `divide-y divide-gray-200` - Row dividers

**TableRow:**
- Automatically adds `hover:bg-blue-50 cursor-pointer transition-colors` when `onClick` is provided
- Clickable rows highlight on hover

**TableCell:**
- `px-6 py-4` - Consistent padding (matches header)
- `whitespace-nowrap text-sm` - Prevents text wrapping by default
- Override with `className` if wrapping needed

### Usage Patterns

#### Clickable Rows
```tsx
<TableRow onClick={() => viewDetails(item)}>
  <TableCell className="font-medium text-gray-900">{item.id}</TableCell>
  <TableCell className="text-gray-900">{item.name}</TableCell>
</TableRow>
```

#### Action Buttons in Cells
```tsx
<TableCell>
  <div className="flex space-x-2">
    <button
      onClick={(e) => {
        e.stopPropagation() // Prevent row click
        handleEdit(item)
      }}
      className="text-blue-600 hover:text-blue-900"
    >
      Edit
    </button>
    <button
      onClick={(e) => {
        e.stopPropagation()
        handleDelete(item)
      }}
      className="text-red-600 hover:text-red-900"
    >
      Delete
    </button>
  </div>
</TableCell>
```

#### Status Badges
```tsx
<TableCell>
  <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
    {item.status}
  </span>
</TableCell>
```

#### Empty State
```tsx
{items.length === 0 ? (
  <div className="p-8 text-center text-gray-500">
    <p className="mb-2">No items found</p>
    <p className="text-sm">Add items to see them here</p>
  </div>
) : (
  <Table>
    {/* Table content */}
  </Table>
)}
```

### Text Color Conventions
- **Primary data (IDs, names):** `text-gray-900` (darker, more prominent)
- **Secondary data (dates, details):** `text-gray-900` or `text-gray-500` (lighter)
- **Actions/Links:** `text-blue-600 hover:text-blue-900`
- **Destructive actions:** `text-red-600 hover:text-red-900`

### Column Width
- Let columns auto-size by default
- Add `className="w-32"` or similar to specific cells if fixed width needed
- Use `whitespace-nowrap` (default) to prevent wrapping
- Remove `whitespace-nowrap` with `className="whitespace-normal"` if text should wrap

### Responsive Behavior
- Table wrapper has `overflow-x-auto` for horizontal scrolling on small screens
- Consider hiding less important columns on mobile with responsive classes:
  ```tsx
  <TableHeadCell className="hidden md:table-cell">Optional Column</TableHeadCell>
  <TableCell className="hidden md:table-cell">{item.optional}</TableCell>
  ```

### Key Rules
- ✅ **DO** use Table component for all data tables
- ✅ **DO** make rows clickable when they lead to detail views
- ✅ **DO** use `e.stopPropagation()` on action buttons inside clickable rows
- ✅ **DO** use consistent padding (`px-6 py-4` for cells, `px-6 py-3` for headers)
- ✅ **DO** use status badges for categorical data (status, type, etc.)
- ❌ **DON'T** use raw `<table>` HTML elements
- ❌ **DON'T** mix different padding values
- ❌ **DON'T** forget to handle empty states

### Examples
See these files for reference implementations:
- **List table:** `frontend/src/pages/PatientsPage.tsx`
- **Episode table:** `frontend/src/pages/EpisodesPage.tsx`
- **Nested tables:** `frontend/src/components/CancerEpisodeDetailModal.tsx`

---

## Colors & Themes

### Primary Colors
- **Blue (Primary):** `bg-blue-600`, `hover:bg-blue-700`, `focus:ring-blue-500`
- **Gray (Secondary):** `bg-gray-600`, `hover:bg-gray-700`, `focus:ring-gray-500`
- **Green (Success):** `bg-green-600`, `hover:bg-green-700`, `focus:ring-green-500`
- **Red (Danger):** `bg-red-600`, `hover:bg-red-700`, `focus:ring-red-500`

### Background Colors
- **Page background:** `bg-gray-100`
- **Card background:** `bg-white`
- **Section highlight:** `bg-gray-50`
- **Important highlight:** `bg-amber-50`
- **Info highlight:** `bg-blue-50`
- **Success highlight:** `bg-green-50`

### Text Colors
- **Primary text:** `text-gray-900`
- **Secondary text:** `text-gray-600`
- **Muted text:** `text-gray-500`
- **Label text:** `text-gray-700`
- **White text:** `text-white` (on colored backgrounds)

### Borders
- **Default:** `border-gray-300`
- **Divider:** `border-gray-200`
- **Focus:** `focus:ring-2 focus:ring-blue-500`

### Header Gradients
- **Blue:** `bg-gradient-to-r from-blue-600 to-blue-700`
- **Purple:** `bg-gradient-to-r from-purple-600 to-purple-700`
- **Green:** `bg-gradient-to-r from-green-600 to-green-700`

---

## Typography

### Headings
```tsx
<h1 className="text-2xl font-bold text-gray-900">Page Title</h1>
<h2 className="text-xl font-semibold text-gray-900">Section Title</h2>
<h3 className="text-lg font-semibold text-gray-900">Subsection</h3>
<h4 className="text-sm font-semibold text-gray-900">Label Heading</h4>
```

### Body Text
```tsx
<p className="text-base text-gray-900">Regular paragraph</p>
<p className="text-sm text-gray-600">Secondary text</p>
<p className="text-xs text-gray-500">Helper text</p>
```

### Labels
```tsx
<label className="block text-sm font-medium text-gray-700 mb-1">
  Field Label
</label>
```

### Font Weights
- **Regular:** `font-normal` (default)
- **Medium:** `font-medium` (labels)
- **Semibold:** `font-semibold` (headings)
- **Bold:** `font-bold` (emphasis)

---

## Layout & Spacing

### Container Padding
- **Page containers:** `p-6` or `p-8`
- **Card/Modal padding:** `p-6`
- **Header/Footer padding:** `px-6 py-4`
- **Section padding:** `p-4`

### Vertical Spacing
- **Between major sections:** `space-y-6` or `space-y-8`
- **Between form fields:** `space-y-4`
- **Between subsections:** `space-y-3`
- **Between related items:** `space-y-2`

### Horizontal Spacing
- **Button groups:** `space-x-3`
- **Form columns:** `gap-4`
- **Icon + text:** `space-x-2`

### Margins
- **Section separation:** `mb-6` or `mb-8`
- **Field label margin:** `mb-1` or `mb-2`
- **Helper text margin:** `mt-1`

### Border Radius
- **Cards/Modals:** `rounded-lg` (0.5rem)
- **Buttons:** `rounded-lg`
- **Inputs:** `rounded-lg`
- **Badges:** `rounded` or `rounded-full`

---

## Best Practices

### Accessibility
- Use semantic HTML (`<form>`, `<label>`, `<button>`)
- Include `aria-label` for icon-only buttons
- Ensure sufficient color contrast
- Make interactive elements keyboard accessible

### Responsiveness
- Use responsive grid: `grid-cols-1 md:grid-cols-2`
- Stack columns on mobile when appropriate
- Ensure modals work on small screens (`p-4` on container)
- Use `max-w-*` classes to prevent excessive width

### Performance
- Minimize re-renders with proper state management
- Use `React.memo` for expensive components
- Avoid inline function definitions in render loops

### Code Organization
- Group related fields in sections
- Use comments to separate major sections
- Extract complex validation logic
- Reuse common components (Button, DateInput, SearchableSelect)

---

## Examples

See these files for reference implementations:
- **Standard form modal:** `frontend/src/components/TumourModal.tsx`
- **Multi-step form:** `frontend/src/components/AddTreatmentModal.tsx`
- **Summary modal:** `frontend/src/components/TreatmentSummaryModal.tsx`
- **Investigation form:** `frontend/src/components/InvestigationModal.tsx`
- **Patient form:** `frontend/src/components/PatientModal.tsx`

---

## Migration Checklist

When updating existing components or creating new ones:

- [ ] Header: Title, close button positioned correctly
- [ ] Footer: Buttons follow left (Cancel) / right (Primary) pattern
- [ ] Button variants: secondary for Cancel/Close, primary for main action
- [ ] Spacing: `justify-between` for button layout, proper padding
- [ ] Border: `border-t` on footer, `border-b` on header
- [ ] Form: `space-y-6` for sections, `space-y-4` for fields
- [ ] Grid: Appropriate `grid-cols-*` for field layout
- [ ] Colors: Consistent use of gray-50/blue-50/amber-50 for sections
- [ ] Typography: Proper heading levels and text sizes
- [ ] Multi-step: Progress indicator, step validation, conditional rendering

---

*Last updated: 2025-12-27*
