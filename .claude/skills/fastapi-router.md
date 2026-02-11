---
name: "FastAPI Router"
description: "Implement, debug, and refactor FastAPI API endpoints"
---

## Context

Use this skill when working with FastAPI API endpoints in the Police Scanner backend. This includes creating new endpoints, fixing bugs, adding features to existing endpoints, and refactoring router code.

## Scope

Files this agent works with:
- `app_api/routers/*.py` - API endpoint implementations
- `app_api/models/*.py` - Pydantic request/response schemas
- `app_api/config.py` - Application settings
- `app_api/database.py` - Database connection pool

## Instructions

When invoked, follow these steps:

1. **Understand the task**
   - Parse the user's request to identify: endpoint path, HTTP method, expected behavior
   - Use Grep to find related existing endpoints for pattern reference
   - Read the relevant router file(s) to understand current structure

2. **Analyze existing patterns**
   - Check how similar endpoints handle database queries
   - Note the response transformation pattern (`transform_*_response()`)
   - Identify Pydantic models needed for request/response

3. **Implement the endpoint**
   - Create async function with proper type hints
   - Use `Depends(get_pool)` for database connection
   - Write parameterized SQL queries (never f-strings)
   - Return properly typed Pydantic response model

4. **Verify**
   - Check for proper error handling (HTTPException)
   - Verify response model transformation
   - Ensure consistent naming conventions

## Behaviors

- Always use `async def` with `await pool.acquire()` for database operations
- Return Pydantic models with `transform_*_response()` for camelCase output
- Use `HTTPException` with appropriate status codes (400, 404, 422, 500)
- Include `Depends(get_pool)` for connection pool injection
- Follow existing pagination pattern: `limit: int = 50, offset: int = 0`
- Use parameterized queries with `$1, $2` placeholders

## Constraints

- Never import `psycopg2` (use `asyncpg` only in app_api)
- Never use `SELECT *` - always specify columns explicitly
- Always handle `None` results from `fetchrow()`
- Never use f-strings for SQL query construction
- Never expose internal database errors to clients

## Safety Checks

Before completing:
- [ ] Pool acquisition wrapped in try/finally or context manager
- [ ] SQL queries use parameterized placeholders ($1, $2, etc.)
- [ ] Response model matches return type annotation
- [ ] Error cases return appropriate HTTP status codes
- [ ] Sensitive data (passwords, tokens) not logged or returned
