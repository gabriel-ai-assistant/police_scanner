---
name: "Test Runner"
description: "Execute and analyze test results for Python and TypeScript"
---

## Context

Use this skill when running tests for the Police Scanner platform. This includes executing pytest for Python code and Jest/Vitest for TypeScript code, analyzing failures, and checking coverage.

## Scope

Files this agent works with:
- `app_scheduler/tests/*.py` - Scheduler tests
- `app_api/tests/*.py` - API tests (if present)
- `frontend/src/**/*.test.ts` - Frontend unit tests
- `frontend/src/**/*.spec.ts` - Frontend integration tests
- `pytest.ini`, `jest.config.js`, `vitest.config.ts` - Test configuration

## Instructions

When invoked, follow these steps:

1. **Understand the scope**
   - Identify which tests to run (all, specific file, specific test)
   - Check if tests require special setup (database, containers)
   - Review test configuration files

2. **Run tests**
   - Use appropriate runner (pytest, npm test)
   - Include coverage if requested
   - Capture output for analysis

3. **Analyze results**
   - Parse failure messages
   - Identify failing test file:line
   - Determine if failure is test bug or code bug

4. **Report findings**
   - Summarize pass/fail counts
   - Provide specific failure details
   - Suggest fixes for common patterns

## Behaviors

- Run pytest with coverage: `pytest --cov=app_api --cov-report=term-missing`
- Run frontend tests: `npm test` in frontend directory
- Report failure summaries with file:line references
- Suggest fixes for common test failures
- Check coverage thresholds when configured

## Constraints

- Never modify test files to make tests pass (fix source code instead)
- Never skip tests without explicit user approval
- Run tests in isolation (no shared state between tests)
- Never run tests with production credentials
- Never delete test fixtures without understanding impact

## Safety Checks

Before completing:
- [ ] Test database connection verified (for DB tests)
- [ ] Mock data matches expected schemas
- [ ] Test cleanup runs even on failure
- [ ] No tests modify production data
- [ ] Coverage report generated if requested

## Python Test Commands

```bash
# Run all tests
cd app_scheduler && python -m pytest

# Run with coverage
python -m pytest --cov=. --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_database_writes.py

# Run specific test
python -m pytest tests/test_database_writes.py::test_insert_new_call

# Verbose output
python -m pytest -v

# Stop on first failure
python -m pytest -x
```

## Frontend Test Commands

```bash
# Run all tests
cd frontend && npm test

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test -- src/components/Button.test.tsx

# Watch mode
npm test -- --watch

# Update snapshots
npm test -- -u
```

## Common Failure Patterns

| Failure | Cause | Fix |
|---------|-------|-----|
| Connection refused | Test DB not running | Start test database |
| Import error | Missing dependency | Check requirements.txt |
| Assertion mismatch | Code changed | Update test or fix code |
| Timeout | Slow operation | Increase timeout or mock |
| Fixture error | Setup failed | Check test fixtures |

## Test Structure Reference

```python
# Python test pattern
async def test_feature_name():
    # Arrange
    conn = await get_connection()
    try:
        await cleanup_test_data(conn)

        # Act
        result = await function_under_test(conn, params)

        # Assert
        assert result is not None
        assert result['field'] == expected
    finally:
        await release_connection(conn)
```

```typescript
// TypeScript test pattern
describe('ComponentName', () => {
  it('should handle expected behavior', () => {
    // Arrange
    const props = { ... };

    // Act
    render(<Component {...props} />);

    // Assert
    expect(screen.getByText('Expected')).toBeInTheDocument();
  });
});
```
