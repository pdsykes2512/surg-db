# GitHub Copilot Instructions for IMPACT

This document provides context and guidelines for GitHub Copilot when working with the IMPACT (Integrated Monitoring Platform for Audit Care & Treatment) repository.

## Repository Overview

IMPACT is a production-ready NBOCA-compliant surgical outcomes tracking system for colorectal cancer care. It enables healthcare providers to track patient episodes, record surgical procedures with OPCS-4 coding, maintain TNM staging, and generate NBOCA COSD v9/v10 XML exports for national audit submissions.

**Key Characteristics:**
- Healthcare application with strict data compliance (UK GDPR, Caldicott Principles)
- Full-stack TypeScript/Python application
- 3-layer architecture (Directive → Orchestration → Execution)
- Production system with 7,900+ patients, 8,000+ episodes, 7,900+ treatments

## Technology Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for build tooling
- **Tailwind CSS** for styling
- **React Router** for navigation
- **React Query (@tanstack/react-query)** for API caching
- Development server runs on port 3000

### Backend
- **FastAPI** (Python async web framework)
- **Pydantic** for data validation
- **Motor** (async MongoDB driver)
- **Python-JOSE** for JWT authentication
- **Passlib** with bcrypt for password hashing
- API server runs on port 8000

### Database
- **MongoDB** document-oriented database
- 9 collections: patients, episodes, treatments, tumours, investigations, clinicians, surgeons, users, nhs_providers
- Field-level encryption (AES-256) for sensitive data
- Comprehensive indexes for performance

## Critical Files to Review Before Making Changes

### Must-Read Documentation
1. **AGENTS.md** - AI agent operating instructions, 3-layer architecture, self-annealing principles
2. **RECENT_CHANGES.md** - Recent changes log (READ THIS FIRST to avoid duplicate work)
3. **DATABASE_SCHEMA.md** - Complete database schema (NEVER modify schema without approval)
4. **STYLE_GUIDE.md** - UI/UX design patterns and component standards
5. **CODE_STYLE_GUIDE.md** - Code formatting and naming conventions

### Architecture Documentation
- **GIT_WORKFLOW.md** - Branching strategy (develop/main workflow)
- **SEARCH_FUNCTIONALITY_PROTECTION.md** - Search architecture principles
- **PERFORMANCE_OPTIMIZATION_REPORT.md** - Performance patterns and optimizations

## Directory Structure

```
/home/runner/work/impact/impact/
├── .github/
│   ├── workflows/          # CI/CD workflows (auto-versioning)
│   └── copilot-instructions.md  # This file
├── backend/
│   ├── app/
│   │   ├── routes/        # FastAPI route handlers
│   │   ├── models/        # Pydantic models
│   │   ├── utils/         # Utility functions (encryption, serializers, etc.)
│   │   ├── database.py    # MongoDB connection
│   │   ├── auth.py        # JWT authentication
│   │   └── main.py        # FastAPI application entry point
│   ├── migrations/        # Database migration scripts
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/    # Reusable UI components
│   │   │   ├── forms/     # Multi-step forms
│   │   │   ├── layout/    # Layout components
│   │   │   ├── modals/    # Modal dialogs
│   │   │   └── search/    # Search components
│   │   ├── pages/         # Page components (routing)
│   │   ├── hooks/         # Custom React hooks
│   │   ├── contexts/      # React contexts (auth, etc.)
│   │   ├── services/      # API service layer
│   │   ├── utils/         # Utility functions
│   │   ├── data/          # Static data (procedures, diagnoses)
│   │   └── types/         # TypeScript type definitions
│   ├── package.json       # Node dependencies
│   └── vite.config.ts     # Vite configuration
├── execution/             # Layer 3: Deterministic Python scripts
│   ├── active/           # Currently used scripts
│   └── migrations/       # Data migration scripts
├── directives/           # Layer 1: SOPs in Markdown
├── docs/                 # Documentation
│   ├── api/             # API documentation
│   ├── guides/          # User guides
│   ├── setup/           # Setup and deployment
│   └── development/     # Developer documentation
└── services/            # Systemd service files
```

## Key Patterns and Conventions

### 3-Layer Architecture

This system follows a strict 3-layer architecture:

1. **Layer 1: Directive (What to do)** - SOPs in `directives/` directory
   - Natural language instructions
   - Define goals, inputs, tools, outputs, edge cases

2. **Layer 2: Orchestration (Decision making)** - AI agents coordinate work
   - Read directives, call execution scripts
   - Handle errors, update directives with learnings

3. **Layer 3: Execution (Doing the work)** - Python scripts in `execution/`
   - Deterministic, testable operations
   - API calls, data processing, file operations
   - Environment variables in `.env`

**Why:** Separates probabilistic AI decision-making from deterministic operations, maximizing reliability.

### Service Management

**CRITICAL:** Backend and frontend run as systemd services. NEVER use manual commands.

```bash
# ✅ CORRECT: Use systemd
sudo systemctl restart impact-backend
sudo systemctl restart impact-frontend
sudo systemctl status impact-backend

# ❌ WRONG: Don't use these
pkill -f "uvicorn"
bash execution/start_backend.sh
cd frontend && npm run dev
```

**Service files:** `/etc/systemd/system/impact-backend.service` and `impact-frontend.service`
**Log files:** `~/.tmp/backend.log` and `~/.tmp/frontend.log`

### Code Style

#### TypeScript/React
- Use functional components with hooks (no class components)
- Custom hooks: `is*` prefix for state flags (`isLoading`), `show*` for visibility, `has*` for possession
- Boolean props: Always use `is*` or `has*` prefix
- Import organization: Standard library → Third-party → Local application
- Path aliases: Use `@/` for cleaner imports (configured in tsconfig.json)
- React Query for API caching (5-minute stale time, 10-minute cache time)
- Memoization: Use `useMemo` for expensive calculations, `useCallback` for functions

#### Python/FastAPI
- Async/await pattern for all route handlers
- Pydantic models for request/response validation
- Logger instead of print statements: `logger.error()`, `logger.debug()`
- Comprehensive error handling with try/except and HTTPException
- Type hints for all function parameters and return values
- Import organization: Standard library → Third-party → Local application

### Database Schema Protection

**CRITICAL:** Database schema is SACRED. You MUST NOT modify without explicit approval:
- Field names, types, structures
- Collections or relationships
- Data normalization/cleaning logic
- NBOCA/COSD compliance field mappings

**If schema changes needed:**
1. Read `DATABASE_SCHEMA.md` first
2. Propose changes and get explicit approval
3. Update `DATABASE_SCHEMA.md` BEFORE implementing
4. Update Pydantic models in `backend/app/models/`
5. Test in `impact_test` database before production
6. Document in `RECENT_CHANGES.md`

### Sensitive Data Handling

- NHS numbers, MRN, DOB, postcodes: ALWAYS encrypted (AES-256)
- Hash-based search for encrypted fields (indexed for performance)
- Never log sensitive data
- Field-level encryption utility: `backend/app/utils/encryption.py`
- Search uses `*_hash` fields, never decrypted fields

### API Patterns

#### Backend (FastAPI)
```python
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..auth import require_admin
from ..database import get_database
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/items/")
async def list_items(
    skip: int = 0,
    limit: int = 100,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        # Use aggregation for complex queries
        items = await db.items.find().skip(skip).limit(limit).to_list(length=limit)
        return items
    except Exception as e:
        logger.error(f"Error listing items: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list items")
```

#### Frontend (React Query)
```typescript
import { useQuery } from '@tanstack/react-query';
import api from '@/services/api';

function ItemsList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['items', { skip, limit }],
    queryFn: () => api.get('/items/', { params: { skip, limit } }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <div>Error loading items</div>;
  
  return <div>{/* render items */}</div>;
}
```

### Search Functionality

**CRITICAL PRINCIPLE:** Always filter entire database FIRST, then apply pagination.

```python
# ✅ CORRECT: Search → Count → Paginate
query = {"cancer_type": {"$regex": search_term, "$options": "i"}}
total = await collection.count_documents(query)
results = await collection.find(query).skip(skip).limit(limit).to_list(length=limit)

# ❌ WRONG: Paginate → Filter (misses results on other pages!)
results = await collection.find().skip(skip).limit(limit).to_list(length=limit)
filtered = [r for r in results if search_term in r["cancer_type"]]
```

### Performance Optimizations

1. **React Query:** Automatic caching, request deduplication, background refetching
2. **MongoDB Aggregation:** Use pipelines for complex calculations (not client-side)
3. **Memoization:** `useMemo` for data transformations, `useCallback` for functions
4. **Indexes:** All query fields should have indexes
5. **Bulk Operations:** Use `$in` operator instead of N+1 queries
6. **Pagination:** Always implement for lists >100 items

### Responsive Design

Mobile-first approach with Tailwind breakpoints:
- `sm:` (640px) - Large phones, small tablets
- `md:` (768px) - Tablets
- `lg:` (1024px) - Laptops
- `xl:` (1280px) - Large desktops

**Patterns:**
- Padding: `px-2 sm:px-4 md:px-6`
- Grids: `grid-cols-1 sm:grid-cols-2 md:grid-cols-3`
- Touch targets: Minimum 44×44px
- Modal widths: Progressive scaling (`max-w-full sm:max-w-lg md:max-w-xl lg:max-w-2xl`)

## Testing and Validation

### Before Making Changes
1. Read `RECENT_CHANGES.md` to avoid duplicate work
2. Check if feature already exists or was recently fixed
3. Review relevant documentation (STYLE_GUIDE.md, DATABASE_SCHEMA.md)

### After Making Changes
1. Test locally with systemd services
2. Check logs: `tail -50 ~/.tmp/backend.log` and `~/.tmp/frontend.log`
3. Verify no TypeScript errors: `cd frontend && npm run build`
4. Test in browser at relevant breakpoints (375px, 640px, 768px, 1024px)
5. Update `RECENT_CHANGES.md` with comprehensive change log

### Manual Testing Checklist
- [ ] Login/authentication works
- [ ] Create, read, update, delete operations
- [ ] Search and filtering (test with various terms)
- [ ] Pagination (test multiple pages)
- [ ] Mobile responsive (test at 375px width)
- [ ] Form validation (test invalid inputs)
- [ ] Modal interactions (open, close, submit)

## Common Tasks

### Adding a New API Endpoint
1. Create route handler in `backend/app/routes/`
2. Add Pydantic models in `backend/app/models/` if needed
3. Register router in `backend/app/main.py`
4. Add API method to `frontend/src/services/api.ts`
5. Create React Query hook if complex
6. Test with curl or Postman first
7. Restart backend service: `sudo systemctl restart impact-backend`

### Adding a New Page
1. Create page component in `frontend/src/pages/`
2. Add route in `frontend/src/App.tsx`
3. Update navigation in `frontend/src/components/layout/Layout.tsx`
4. Follow responsive design patterns from STYLE_GUIDE.md
5. Use existing components from `frontend/src/components/common/`
6. Test mobile layout (<640px) and desktop (>768px)

### Database Migration
1. Create script in `execution/migrations/`
2. Test with dry-run flag first
3. Backup database: `python execution/active/backup_database.py --manual`
4. Run migration with verification
5. Update `DATABASE_SCHEMA.md` if schema changes
6. Document in `RECENT_CHANGES.md`

## Security Guidelines

### Authentication
- All protected routes use JWT tokens
- Token validation in `backend/app/auth.py`
- Role-based access: admin, surgeon, data_entry, viewer
- Frontend context: `frontend/src/contexts/AuthContext.tsx`

### Data Protection
- Never commit secrets (`.env`, `credentials.json`, `token.json`)
- Field-level encryption for NHS numbers, MRN, DOB, postcodes
- Use `backend/app/utils/encryption.py` for encryption operations
- Hash-based search for encrypted fields (never decrypt for search)
- Audit logging for all CRUD operations

### Input Validation
- Backend: Pydantic models validate all inputs
- Frontend: Form validation before submission
- Sanitize search inputs to prevent NoSQL injection
- Use `backend/app/utils/search_helpers.py` for search sanitization

## Git Workflow

- **develop branch:** Active development (work here)
- **main branch:** Production releases only
- **Semantic commits:** `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- **Auto-versioning:** Merges to main trigger version bumps
  - `feat:` = minor version bump (1.0.0 → 1.1.0)
  - `fix:` = patch version bump (1.0.0 → 1.0.1)
- **Archive branches:** Auto-created on minor/major version bumps

## Common Pitfalls to Avoid

1. **Don't modify encrypted fields without using encryption utilities**
2. **Don't fetch all records and filter client-side** (use server-side filtering)
3. **Don't use synchronous operations in async route handlers**
4. **Don't skip pagination for large datasets**
5. **Don't change database schema without approval and documentation**
6. **Don't use `print()` statements** (use `logger.debug()` or `logger.error()`)
7. **Don't hardcode localhost URLs** (use environment variables)
8. **Don't create duplicate ID generation logic** (use `frontend/src/utils/idGenerators.ts`)
9. **Don't skip mobile responsive testing** (test at <640px width)
10. **Don't restart services manually** (use systemd commands)

## File Organization

### Temporary Files
- All intermediate files go in `.tmp/` directory
- Never commit `.tmp/` contents
- Log files stored in `~/.tmp/` (not `/tmp/`)

### Environment Variables
- Backend: `backend/.env`
- Frontend: `frontend/.env`
- Never commit `.env` files

### Documentation Updates
Always update these files when making changes:
1. `RECENT_CHANGES.md` - Detailed change log
2. Relevant documentation in `docs/`
3. `DATABASE_SCHEMA.md` if schema changes
4. `STYLE_GUIDE.md` if UI patterns change

## Key Utilities and Helpers

### Backend Utilities (`backend/app/utils/`)
- `encryption.py` - Field-level encryption, hash generation, search
- `serializers.py` - MongoDB ObjectId serialization
- `search_helpers.py` - Search input sanitization
- `date_formatters.py` - Date formatting for exports
- `clinician_helpers.py` - Clinician resolution logic

### Frontend Utilities (`frontend/src/utils/`)
- `idGenerators.ts` - Generate patient/episode/treatment/tumour/investigation IDs
- `styleHelpers.ts` - Consistent styling (urgency, status, complexity, approach)

### Custom Hooks (`frontend/src/hooks/`)
- `usePatients.ts` - Fetch patients with loading/error states
- `useClinicians.ts` - Fetch clinicians with loading/error states

## NBOCA Compliance

This system is NBOCA COSD v9/v10 compliant with 59/59 mandatory fields implemented.

**Critical Fields:**
- Patient demographics (NHS number, DOB, gender, postcode)
- Episode data (referral date, diagnosis date, treatment dates)
- Tumour staging (TNM v7/v8, grade, morphology)
- Treatment details (surgery, chemotherapy, radiotherapy)
- Outcomes (mortality, complications, readmissions)

**Export Formats:**
- XML (COSD v9/v10) for national audit submissions
- Excel for local analysis and reporting

**Validation:**
- ICD-10 codes: 63 colorectal cancer codes
- OPCS-4 codes: 126 procedure codes
- Pre-submission validation with error reporting
- Data quality dashboard with completeness metrics

## Getting Help

- **Documentation:** See `docs/` directory
- **Recent Changes:** Check `RECENT_CHANGES.md` first
- **Architecture:** Read `AGENTS.md` for 3-layer architecture
- **Style Guide:** Reference `STYLE_GUIDE.md` for UI patterns
- **Database:** Consult `DATABASE_SCHEMA.md` for schema
- **Issues:** https://github.com/pdsykes2512/impact/issues

## Version Information

- **Current Version:** 1.1.0
- **Status:** Production Ready
- **Lines of Code:** ~15,000
- **API Endpoints:** 50+
- **Database Collections:** 9
- **Test Data:** 7,900+ patients, 8,000+ episodes, 7,900+ treatments

---

**Remember:** This is a production healthcare system with real patient data. Always prioritize data integrity, security, and compliance over convenience.
