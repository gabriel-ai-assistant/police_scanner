# Contributing to Police Scanner Analytics Platform

Thank you for your interest in contributing to this project. This guide will help you get started with development and maintain code quality standards.

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Code Style Guidelines](#code-style-guidelines)
- [Git Workflow](#git-workflow)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Code Review Checklist](#code-review-checklist)

## Development Environment Setup

### Prerequisites

- **Docker & Docker Compose** - Container runtime
- **Python 3.11+** - Backend development
- **Node.js 20+** - Frontend development
- **Git** - Version control
- **PostgreSQL client** (optional) - Database inspection
- **Make** (optional) - Build automation

### First-Time Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd policescanner
   ```

2. **Copy environment template**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Start services**:
   ```bash
   docker compose up -d
   ```

4. **Verify all services are running**:
   ```bash
   docker compose ps
   ```

For detailed setup instructions, see [docs/guides/local-development.md](docs/guides/local-development.md).

## Code Style Guidelines

### Python (FastAPI, Celery, APScheduler)

**General Principles**:
- Use type hints for all function signatures
- Prefer `async`/`await` for I/O-bound operations
- Use logging instead of print statements
- No hardcoded secrets (always use environment variables)

**Example**:
```python
from typing import List
import logging

logger = logging.getLogger(__name__)

async def get_recent_calls(limit: int = 50) -> List[dict]:
    """Fetch recent calls from database.

    Args:
        limit: Maximum number of calls to return

    Returns:
        List of call dictionaries
    """
    logger.info(f"Fetching {limit} recent calls")
    # Implementation...
    return results
```

**Code Quality Tools**:
- **Ruff** - Linting and formatting (configured in `pyproject.toml`)
- **Pytest** - Testing framework
- **MyPy** - Static type checking (optional)

**Run quality checks**:
```bash
make lint      # Run linters
make format    # Auto-format code
make test      # Run tests
```

### TypeScript/React (Frontend)

**General Principles**:
- Use functional components with hooks
- Type all props and return values
- Use React Router v6 for navigation
- TanStack Query for server state management
- Tailwind CSS for styling

**Example**:
```typescript
interface CallListProps {
  limit?: number;
  onCallClick?: (callId: string) => void;
}

export const CallList: React.FC<CallListProps> = ({
  limit = 50,
  onCallClick
}) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['calls', limit],
    queryFn: () => fetchCalls(limit)
  });

  // Component implementation...
};
```

**Code Quality Tools**:
- **ESLint** - Linting (configured in `frontend/.eslintrc.json`)
- **Prettier** - Code formatting (configured in `frontend/.prettierrc.json`)
- **TypeScript** - Type checking

**Run quality checks**:
```bash
cd frontend
npm run lint        # ESLint
npm run format      # Prettier
npm run type-check  # TypeScript
```

### Database Migrations

- Use sequential migration files: `001_description.sql`, `002_description.sql`
- Include both `-- UP` and `-- DOWN` migrations
- Test migrations on a copy of production data before deploying
- Document breaking changes in migration comments

## Git Workflow

### Branch Naming

Use descriptive branch names with prefixes:
- `feature/add-audio-filters` - New features
- `fix/transcript-encoding-bug` - Bug fixes
- `refactor/api-error-handling` - Code refactoring
- `docs/update-deployment-guide` - Documentation updates
- `chore/update-dependencies` - Maintenance tasks

### Commit Message Format

Follow conventional commits format:

```
<type>(<scope>): <short summary>

<optional body>

<optional footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring (no functional changes)
- `test`: Adding or updating tests
- `chore`: Build process, tooling, dependencies
- `perf`: Performance improvements

**Examples**:
```
feat(api): add pagination to calls endpoint

Add limit and offset query parameters to GET /api/calls
to support pagination for large result sets.

Closes #42
```

```
fix(transcription): handle empty audio files gracefully

Previously, empty MP3 files would cause Whisper to crash.
Now we check file size and skip transcription if < 1KB.
```

### Commit Guidelines

- Keep commits atomic (one logical change per commit)
- Write clear, descriptive commit messages
- Reference issue numbers when applicable
- Don't commit secrets or sensitive data
- Run tests before committing

## Testing Requirements

### Backend Tests (Python/Pytest)

**Location**: `app_*/tests/`

**Coverage Requirements**:
- All new API endpoints must have tests
- Critical business logic must have >80% coverage
- Database operations should have integration tests

**Running tests**:
```bash
# All tests
pytest

# Specific module
pytest app_api/tests/

# With coverage
pytest --cov=app_api --cov-report=html
```

**Example test**:
```python
import pytest
from app_api.main import app

@pytest.mark.asyncio
async def test_get_calls_returns_200(test_client):
    response = await test_client.get("/api/calls?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "calls" in data
    assert len(data["calls"]) <= 10
```

### Frontend Tests (TypeScript/Jest/React Testing Library)

**Location**: `frontend/src/**/__tests__/`

**Coverage Requirements**:
- All new components should have basic render tests
- User interactions should be tested
- API integration should use mocked responses

**Running tests**:
```bash
cd frontend
npm test           # Run tests
npm run test:watch # Watch mode
npm run coverage   # With coverage
```

### Integration Tests

For features that span multiple services:
- Test end-to-end workflows (API → Database → Search)
- Use Docker Compose for isolated test environments
- Document test scenarios in test docstrings

## Pull Request Process

### Before Creating a PR

1. **Pull latest changes** from main branch:
   ```bash
   git checkout main
   git pull origin main
   git checkout your-feature-branch
   git rebase main
   ```

2. **Run all quality checks**:
   ```bash
   make lint test
   cd frontend && npm run lint && npm test
   ```

3. **Build containers** to verify no build errors:
   ```bash
   docker compose build
   ```

### Creating the PR

1. **Push your branch**:
   ```bash
   git push origin your-feature-branch
   ```

2. **Open Pull Request** on GitHub

3. **Fill out PR template** with:
   - Description of changes
   - Type of change (feature/fix/refactor/docs)
   - Testing checklist
   - Deployment notes (if applicable)

### PR Review Process

- At least one approval required before merging
- All CI checks must pass
- Address all review comments
- Keep PR scope focused (prefer smaller PRs)

## Code Review Checklist

### For Reviewers

**Functionality**:
- [ ] Code solves the stated problem
- [ ] Edge cases are handled
- [ ] Error handling is appropriate
- [ ] No obvious bugs or logic errors

**Code Quality**:
- [ ] Code is readable and well-organized
- [ ] Variable/function names are descriptive
- [ ] Complex logic has explanatory comments
- [ ] No unnecessary code duplication

**Testing**:
- [ ] Tests are included for new functionality
- [ ] Tests cover edge cases
- [ ] Tests pass locally and in CI

**Security**:
- [ ] No hardcoded secrets or credentials
- [ ] Input validation is present
- [ ] No SQL injection vulnerabilities
- [ ] Authentication/authorization properly enforced

**Performance**:
- [ ] No obvious performance regressions
- [ ] Database queries are optimized (indexes, N+1 queries)
- [ ] Caching is used where appropriate

**Documentation**:
- [ ] README updated if needed
- [ ] API endpoints documented
- [ ] Complex functions have docstrings

### For Authors

Before requesting review:
- [ ] Self-review your own code
- [ ] Remove debug statements and commented code
- [ ] Update tests to reflect changes
- [ ] Update documentation
- [ ] Verify CI passes
- [ ] Test locally in Docker environment

## Additional Resources

- **Architecture Documentation**: See [CLAUDE.md](CLAUDE.md)
- **API Documentation**: http://localhost:8000/docs
- **Local Development Guide**: [docs/guides/local-development.md](docs/guides/local-development.md)
- **Deployment Guide**: [docs/deployment/deployment-checklist.md](docs/deployment/deployment-checklist.md)

## Questions or Issues?

- Review existing documentation in `docs/`
- Check [CLAUDE.md](CLAUDE.md) for architecture details
- Consult service logs for debugging: `docker compose logs <service-name>`

---

Thank you for contributing to make this project better!
