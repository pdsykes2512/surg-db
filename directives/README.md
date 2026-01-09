# Directives

This directory contains Standard Operating Procedures (SOPs) written in Markdown that guide AI agents and developers in performing specific tasks within the IMPACT system.

## Purpose

Directives serve as natural language instructions for complex operations, defining:
- **Goals** - What needs to be accomplished
- **Inputs** - Required data and parameters
- **Tools/Scripts** - Execution scripts to use
- **Outputs** - Expected results
- **Edge Cases** - Error conditions and handling

## Structure

Each directive is a Markdown file describing a specific operational workflow:

### Example Directive Structure
```markdown
# Operation Name

## Goal
Clear description of what this operation accomplishes.

## Prerequisites
- Required tools
- Access permissions
- Environment setup

## Inputs
- Parameter 1: Description and format
- Parameter 2: Description and format

## Process
1. Step 1 description
2. Step 2 description
3. Step 3 description

## Execution
```bash
python execution/script_name.py --param value
```

## Outputs
- Output 1: Description and location
- Output 2: Description and location

## Edge Cases
- Error condition 1: How to handle
- Error condition 2: How to handle

## Validation
How to verify the operation completed successfully

## Rollback
How to undo changes if something goes wrong
```

## Using Directives

Directives are read by:
1. **AI Agents** - Follow step-by-step instructions to complete tasks
2. **Developers** - Understand workflows and procedures
3. **System Operators** - Execute maintenance and deployment tasks

### AI Agent Usage
When an AI agent receives a task:
1. Read relevant directive for guidance
2. Identify required execution scripts
3. Determine inputs and parameters
4. Execute scripts in specified order
5. Validate outputs
6. Handle edge cases as documented

### Developer Usage
When implementing new features:
1. Read related directives to understand workflows
2. Identify scripts that need modification
3. Update directive if process changes
4. Test changes against directive steps

## Directive Categories

### Data Management
- Patient data import/export
- Database migrations
- Backup and restore procedures
- Data quality checks

### System Operations
- Encryption setup
- Index creation
- Service management
- Health monitoring

### Reporting & Analytics
- NBOCA COSD XML export
- Performance reports
- Data completeness checks
- Audit trail queries

### Security & Compliance
- Encryption key management
- User access control
- Audit logging
- GDPR compliance tasks

## Creating New Directives

When creating a new directive:

1. **Use clear structure** - Follow the template above
2. **Be specific** - Provide exact commands and parameters
3. **Document edge cases** - Anticipate failure modes
4. **Include examples** - Show sample inputs/outputs
5. **Provide validation** - How to verify success
6. **Plan rollback** - How to undo if needed

### Directive Template
```markdown
# [Operation Name]

## Goal
[What this operation accomplishes]

## Prerequisites
- [Required tool/access 1]
- [Required tool/access 2]

## Inputs
- **param1**: [Description] (type: string, required)
- **param2**: [Description] (type: int, optional, default: 100)

## Process
1. [First step]
2. [Second step]
3. [Third step]

## Execution
```bash
# Example command
python execution/script.py --param1 value1 --param2 100

# With verbose output
python execution/script.py --param1 value1 --verbose
```

## Outputs
- **output1**: [Description and location]
- **output2**: [Description and location]

## Edge Cases

### Case 1: [Error condition]
**Cause**: [Why this happens]
**Solution**: [How to fix]
**Command**: 
```bash
python execution/fix_script.py
```

### Case 2: [Another error condition]
**Cause**: [Why this happens]
**Solution**: [How to fix]

## Validation
```bash
# Check if operation succeeded
python execution/verify_script.py

# Expected output:
# ✓ Operation completed successfully
# ✓ Data integrity verified
```

## Rollback
If operation fails or needs to be undone:

```bash
# Step 1: Stop affected services
sudo systemctl stop impact-backend

# Step 2: Restore from backup
python execution/restore_backup.py --backup latest

# Step 3: Restart services
sudo systemctl start impact-backend
```

## Notes
- [Important consideration 1]
- [Important consideration 2]
- [Known limitation]

## See Also
- `execution/related_script.py` - Related execution script
- `docs/related_doc.md` - Related documentation
```

## Best Practices

### Clarity
- Write for someone unfamiliar with the system
- Use simple, direct language
- Avoid jargon unless defined
- Include concrete examples

### Completeness
- Cover all required parameters
- Document optional parameters and defaults
- Explain all edge cases
- Provide validation steps

### Maintainability
- Update directives when processes change
- Version control all changes
- Add timestamps for major updates
- Reference related directives

### Safety
- Include rollback procedures
- Warn about destructive operations
- Require confirmations for risky tasks
- Document backup requirements

## Relationship to Execution Scripts

Directives and execution scripts work together:

```
Directive (What to do)           Execution Script (How to do it)
├─ Natural language              ├─ Python/Bash code
├─ Step-by-step process          ├─ Deterministic logic
├─ Parameters and inputs         ├─ Argument parsing
├─ Expected outputs              ├─ Result generation
├─ Edge case handling            ├─ Error handling
└─ Validation steps              └─ Output validation
```

**Example:**
- `directives/encrypt_database.md` - Explains encryption setup process
- `execution/setup_database_encryption.sh` - Implements encryption
- `execution/migrate_to_encrypted_fields.py` - Migrates data
- `execution/verify_encryption.py` - Validates encryption

## Directive Lifecycle

1. **Creation** - New workflow needs documentation
2. **Review** - Team reviews for accuracy and completeness
3. **Testing** - Follow directive to verify it works
4. **Deployment** - Directive goes live for use
5. **Maintenance** - Update as system evolves
6. **Deprecation** - Mark obsolete if workflow changes

## Questions?

For questions about directives:
1. Check existing directives for examples
2. Review execution scripts for implementation details
3. Consult system documentation
4. Ask in team discussions

## Contributing

When updating directives:
1. Maintain consistent structure
2. Test all commands before committing
3. Update "Last Updated" date
4. Document what changed and why
5. Review with team if major changes

## Related Documentation

- `execution/README.md` - Execution scripts documentation
- `CODE_STYLE_GUIDE.md` - Coding standards
- `docs/operations/` - Operational procedures
- `AGENTS.md` - AI agent instructions
