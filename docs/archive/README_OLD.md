# Agent Environment

A 3-layer architecture for reliable AI agent operations that separates probabilistic LLM decisions from deterministic business logic.

## Architecture Overview

### Layer 1: Directives (`directives/`)
Standard Operating Procedures written in Markdown that define:
- Goals and objectives
- Required inputs
- Tools/scripts to use
- Expected outputs
- Edge cases and error handling

### Layer 2: Orchestration (AI Agent)
The AI agent acts as intelligent router that:
- Reads directives to understand tasks
- Calls execution tools in the correct order
- Handles errors and asks for clarification
- Updates directives with learnings

### Layer 3: Execution (`execution/`)
Deterministic Python scripts that handle:
- API calls
- Data processing
- File operations
- Database interactions

## Directory Structure

```
.
├── docs/development/AGENTS.md  # Core architecture documentation
├── directives/                 # SOPs and task instructions
├── execution/                  # Python scripts (deterministic tools)
├── .tmp/                       # Temporary files (not committed)
├── .env                        # Environment variables (not committed)
├── credentials.json            # Google OAuth (not committed)
└── token.json                 # Google OAuth token (not committed)
```

## Setup

1. **Add API credentials to `.env`**:
   - Open `.env` and add your API keys
   - Required credentials depend on your use case

2. **For Google services** (Sheets, Slides, etc.):
   - Place `credentials.json` in the root directory
   - Run any Google-related script to generate `token.json`

3. **Install Python dependencies** (as needed):
   ```bash
   pip install -r requirements.txt
   ```

## Version Control Practices

- **Atomic commits**: Small, logical units of work
- **Semantic messages**: Format `type: description` (e.g., `feat: add scraper`, `fix: handle timeout`)
- **Feature branches**: Never commit directly to `main`
- **Branch naming**: `feat/description` or `fix/description`

## Usage

1. Create or review a directive in `directives/`
2. The AI agent reads the directive
3. The agent calls execution scripts from `execution/`
4. Results are delivered to cloud services (Google Sheets, etc.)
5. Temporary files are stored in `.tmp/` and can be deleted

## Key Principle

**Deliverables live in the cloud** (Google Sheets, Slides, etc.) where users can access them. Local files in `.tmp/` are only for processing and can be regenerated.

## Self-Annealing

When errors occur:
1. Fix the issue
2. Update the execution tool
3. Test to ensure it works
4. Update the directive with learnings
5. System is now more robust

For more details, see [AGENTS.md](../development/AGENTS.md).
