# Project AGENTS

This file defines the default operating profile for work in `E:\nobel premia Boiko - 2026`.

## Execution Flow

1. Do a brief context and risk check.
2. Read local evidence first.
3. Execute directly for normal local work without waiting for approval.
4. Keep edits minimal and scoped.
5. Verify the smallest sufficient surface before finalizing.
6. Report `Implemented` and `Verified` separately.

See also:

- `docs/working-contract.md`

## Approval Boundary

Ask before proceeding only when one of these is true:

- destructive operations
- production deploys or irreversible infra changes
- database or schema migrations
- secret creation, rotation, or exposure risk
- force-push, hard reset, or history rewrite
- edits outside this project workspace

## Working Rules

- Verify before claim.
- Prefer local code, files, command output, and tests over memory.
- Use the narrowest tool surface that can finish the task.
- Preserve existing patterns unless correctness requires change.
- Never hardcode real secrets.
- Never revert unrelated user changes.
- Surface hidden risks when they materially affect correctness, safety, or maintenance.

## Output Contract

Final reports should separate:

- `Implemented`
- `Verified`
- `Unverified` when something important could not be checked
