---
name: "Git Operations"
description: "Manage git workflow, commits, branches, and PRs"
---

## Context

Use this skill when managing git version control operations. This includes creating commits, managing branches, and creating pull requests using the GitHub CLI.

## Scope

Files this agent works with:
- `.git/` - Git repository
- `.github/workflows/*.yml` - CI/CD pipelines
- All tracked files in the repository

## Instructions

When invoked, follow these steps:

1. **Understand the task**
   - Determine operation type: commit, branch, PR, etc.
   - Check current git status
   - Review recent commit history for conventions

2. **Execute safely**
   - Verify working directory state
   - Use appropriate git commands
   - Follow conventional commit format

3. **Verify**
   - Confirm operation succeeded
   - Check no unintended changes
   - Verify remote sync status

## Behaviors

- Create atomic commits with conventional commit messages (feat:, fix:, docs:, refactor:)
- Check git status before operations
- Create feature branches from main
- Use `gh pr create` for pull requests with proper descriptions
- Push with upstream tracking: `git push -u origin branch-name`

## Constraints

- Never force push to main/master
- Never commit .env or other secret files
- Never use git rebase on shared branches without confirmation
- Never use `git add .` without reviewing changes first
- Never amend pushed commits without confirmation

## Safety Checks

Before completing:
- [ ] Working directory state verified
- [ ] No secret files staged (.env, credentials)
- [ ] Commit message follows conventions
- [ ] PR target branch is correct
- [ ] CI checks pass (for PRs)

## Conventional Commit Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting (no code change)
- `refactor`: Code change (no feature/fix)
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
```
feat(api): add alerts endpoint
fix(scheduler): prevent job overlap
docs: update API documentation
refactor(auth): simplify token validation
```

## Common Operations

### Check Status
```bash
git status
git log --oneline -10
git diff
git diff --staged
```

### Create Commit
```bash
# Stage specific files
git add path/to/file.py

# Stage all changes (review first!)
git status
git add -A

# Commit with message
git commit -m "feat(api): add new endpoint

- Added GET /api/alerts endpoint
- Implemented pagination support

🤖 Generated with Claude Code"
```

### Branch Operations
```bash
# Create and switch to new branch
git checkout -b feature/add-alerts

# Switch branches
git checkout main

# Delete local branch
git branch -d feature/add-alerts

# Push with tracking
git push -u origin feature/add-alerts
```

### Pull Request Creation
```bash
# Create PR with GitHub CLI
gh pr create --title "feat: add alerts endpoint" --body "$(cat <<'EOF'
## Summary
- Added GET /api/alerts endpoint for notification management
- Implemented pagination support

## Test Plan
- [ ] Test endpoint returns correct data
- [ ] Verify pagination works

🤖 Generated with Claude Code
EOF
)"

# View PR status
gh pr status
gh pr view
```

### Sync with Remote
```bash
# Fetch and merge
git pull origin main

# Fetch only
git fetch origin

# Check remote status
git remote -v
git branch -vv
```

## PR Template

```markdown
## Summary
<Brief description of changes>

## Changes
- Change 1
- Change 2

## Test Plan
- [ ] Test case 1
- [ ] Test case 2

## Screenshots (if applicable)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Troubleshooting

```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Discard all local changes
git checkout -- .

# See what would be committed
git diff --cached

# View file history
git log --follow -p path/to/file

# Find who changed a line
git blame path/to/file
```
