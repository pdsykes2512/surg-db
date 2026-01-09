# AI Development Note

## Parallel Development Environment

AI assistant functionality is being developed in a separate directory to allow parallel work:

- **This directory** (`/root/impact`): Production bug fixes and maintenance
- **AI directory** (`/root/impact-ai`): AI assistant feature development

## Why Separate?

This allows:
1. Continue fixing bugs in production without affecting AI development
2. Develop AI features without risk of breaking production
3. Test both environments simultaneously on different ports
4. Easier rollback if AI feature needs more work

## Quick Access

```bash
cd /root/impact-ai
```

See `/root/impact-ai/DEVELOPMENT_SETUP.md` for complete setup instructions.

## When Will They Merge?

The AI assistant branch will be merged back into main once:
- All 3 phases are complete (backend, reports, frontend)
- Security testing passes (PII filtering, RBAC, audit logging)
- User acceptance testing complete
- Performance testing shows <10s response times

## Current Status

Check `/root/impact-ai/README_AI_DEV.md` for implementation progress.
