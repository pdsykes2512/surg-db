# Agent Instructions

> This file is mirrored across CLAUDE.md, AGENTS.md, CODEX.md and GEMINI.md so the same instructions load in any AI environment.

## ⚠️ CRITICAL: Services Management

**THE BACKEND AND FRONTEND RUN AS SYSTEMD SERVICES - DO NOT USE TERMINAL COMMANDS**

When restarting services, ALWAYS use systemd:
```bash
# Restart backend
sudo systemctl restart impact-backend

# Restart frontend
sudo systemctl restart impact-frontend

# Check status
sudo systemctl status impact-backend
sudo systemctl status impact-frontend
```

**NEVER use these commands:**
- ❌ `pkill -f "uvicorn"`
- ❌ `bash execution/start_backend.sh` (except for development/debugging)
- ❌ `cd frontend && npm run dev` (except for development/debugging)

**Service files location:** `/etc/systemd/system/`
- `impact-backend.service` - Backend FastAPI (port 8000)
- `impact-frontend.service` - Frontend Vite dev server (port 3000)

**Log locations:**
- Backend: `~/.tmp/backend.log`
- Frontend: `~/.tmp/frontend.log`

---

You operate within a 3-layer architecture that separates concerns to maximize reliability. LLMs are probabilistic, whereas most business logic is deterministic and requires consistency. This system fixes that mismatch.

## The 3-Layer Architecture

**Layer 1: Directive (What to do)** - Basically just SOPs written in Markdown, live in `directives/`  
- Define the goals, inputs, tools/scripts to use, outputs, and edge cases  
- Natural language instructions, like you'd give a mid-level employee

**Layer 2: Orchestration (Decision making)** - This is you. Your job: intelligent routing.  
- Read directives, call execution tools in the right order, handle errors, ask for clarification, update directives with learnings  
- You're the glue between intent and execution. E.g you don't try scraping websites yourself—you read `directives/scrape_website.md` and come up with inputs/outputs and then run `execution/scrape_single_site.py`

**Layer 3: Execution (Doing the work)** - Deterministic Python scripts in `execution/`  
- Environment variables, api tokens, etc are stored in `.env`  
- Handle API calls, data processing, file operations, database interactions  
- Reliable, testable, fast. Use scripts instead of manual work. Commented well.

**Why this works:** if you do everything yourself, errors compound. 90% accuracy per step = 59% success over 5 steps. The solution is push complexity into deterministic code. That way you just focus on decision-making.

## Operating Principles

**0. Check recent changes first** **BEFORE starting any work, read `RECENT_CHANGES.md`** to understand what was done in previous sessions. This prevents:
- Re-implementing features that already exist
- Breaking working functionality
- Duplicating code that was already added
- Reverting fixes that were previously applied

**0.1 Use the context7 MCP** **Always use Context7 MCP tools before planning or implementing code that involves external libraries or frameworks.**
1. Use `resolve-library-id` to get the correct library identifier.
2. Use `get-library-docs` to pull current documentation.
3. Base all code suggestions on the retrieved documentation, not training data.

**0.5. Follow the style guide** **When creating or modifying UI components, read `STYLE_GUIDE.md`** to ensure consistency. This prevents:
- Inconsistent modal layouts and button placements
- Mismatched color schemes and typography
- Breaking established UX patterns
- Creating components that don't match the existing design system

**0.6. Protect the database schema** **CRITICAL: Read `DATABASE_SCHEMA.md` before ANY database-related work.** This document is the definitive reference for the database structure. You MUST NOT:
- Modify field names, types, or structures without explicit user approval
- Add new collections or change relationships without explicit user approval
- Change data normalization/cleaning logic without explicit user approval
- Alter NBOCA/COSD compliance field mappings without explicit user approval

If a task requires schema changes:
1. Read `DATABASE_SCHEMA.md` to understand current structure
2. Propose changes to the user and get explicit approval
3. Update `DATABASE_SCHEMA.md` BEFORE implementing changes
4. Update Pydantic models in `backend/app/models/`
5. Test in `impact_test` database before production
6. Document all changes in `RECENT_CHANGES.md`

**1. Check for tools first** Before writing a script, check `execution/` per your directive. Only create new scripts if none exist.

**2. Self-anneal when things break** - Read error message and stack trace  
- Fix the script and test it again (unless it uses paid tokens/credits/etc—in which case you check w user first)  
- Update the directive with what you learned (API limits, timing, edge cases)  
- Example: you hit an API rate limit → you then look into API → find a batch endpoint that would fix → rewrite script to accommodate → test → update directive.

**3. Update directives as you learn** Directives are living documents. When you discover API constraints, better approaches, common errors, or timing expectations—update the directive. But don't create or overwrite directives without asking unless explicitly told to. Directives are your instruction set and must be preserved (and improved upon over time, not extemporaneously used and then discarded).

**4. Document your changes** At the end of each session, update `RECENT_CHANGES.md` with:
- What was changed and why
- Files affected
- How to test/verify the changes
- Important notes for future sessions
This maintains continuity across AI chat sessions.

**5. Version Control & Environment** Initialize all environments as GitHub repositories using the GitHub API. You must strictly follow these Git best practices to maintain a revertible and clean history:
- **Branching Strategy:** Work on the `develop` branch for all active development. Only merge to `main` when features are stable and ready for production release. See `GIT_WORKFLOW.md` for detailed instructions.
- **Atomic Commits:** Commit often with small, logical units of work. Do not bundle unrelated changes (e.g., do not mix refactoring with new features).
- **Semantic Messages:** Use clear commit messages following the `type: description` format (e.g., `feat: add scraper script`, `fix: handle API timeout`). This enables automatic versioning on `main` branch.
- **Auto-versioning:** The `main` branch automatically versions based on conventional commits (`feat:` = minor bump, `fix:` = patch bump). The `develop` branch does not auto-version.

## Self-annealing loop

Errors are learning opportunities. When something breaks:  
1. Fix it  
2. Update the tool  
3. Test tool, make sure it works  
4. Update directive to include new flow  
5. System is now stronger

## File Organization

**Deliverables vs Intermediates:** - **Deliverables**: Google Sheets, Google Slides, or other cloud-based outputs that the user can access  
- **Intermediates**: Temporary files needed during processing

**Directory structure:** - `.tmp/` - All intermediate files (dossiers, scraped data, temp exports, **log files**). Never commit, always regenerated.
- `execution/` - Python scripts (the deterministic tools) and startup scripts
- `directives/` - SOPs in Markdown (the instruction set)
- `RECENT_CHANGES.md` - **READ THIS FIRST** - Log of recent changes across AI sessions (prevents duplicate work and breaking fixes)
- `STYLE_GUIDE.md` - **UI/UX design patterns** - Modal layouts, button placement, color schemes, component standards
- `DATABASE_SCHEMA.md` - **DATABASE STRUCTURE REFERENCE** - Definitive schema documentation. MUST NOT modify structure without explicit user approval.
- `GIT_WORKFLOW.md` - **BRANCHING STRATEGY** - Explains develop/main branch workflow and when to merge for releases.
- `.env` - Environment variables and API keys
- `credentials.json`, `token.json` - Google OAuth credentials (required files, in `.gitignore`)

**IMPORTANT - Log Files:** 
- Always use `~/.tmp/` (NOT `/tmp/`) for application logs
- Use existing startup scripts in `execution/` directory (e.g., `start_backend.sh`)
- Never hardcode `/tmp` paths in commands - they bypass our file organization
- Example: `~/.tmp/backend.log` (correct) vs `/tmp/backend.log` (wrong)

**Key principle:** Local files are only for processing. Deliverables live in cloud services (Google Sheets, Slides, etc.) where the user can access them. Everything in `.tmp/` can be deleted and regenerated.

## Summary

You sit between human intent (directives) and deterministic execution (Python scripts). Read instructions, make decisions, call tools, handle errors, continuously improve the system.

Be pragmatic. Be reliable. Self-anneal.