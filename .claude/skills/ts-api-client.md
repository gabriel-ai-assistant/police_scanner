---
name: "TypeScript API Client"
description: "Implement and maintain frontend API clients and types"
---

## Context

Use this skill when creating or modifying API client functions and TypeScript type definitions for the Police Scanner frontend. This bridges the gap between the FastAPI backend and React frontend.

## Scope

Files this agent works with:
- `frontend/src/api/*.ts` - API client modules (calls.ts, transcripts.ts, etc.)
- `frontend/src/types/*.ts` - TypeScript interface definitions
- `frontend/src/lib/api.ts` - Shared Axios instance configuration

## Instructions

When invoked, follow these steps:

1. **Understand the task**
   - Identify the backend endpoint(s) being consumed
   - Check the Pydantic models in `app_api/models/` for response shape
   - Determine if this is a new API client or modification

2. **Define TypeScript types**
   - Create interfaces matching backend response structure
   - Use snake_case for field names (matches backend)
   - Create separate interfaces for Create/Update DTOs
   - Add JSDoc comments for complex fields

3. **Implement API functions**
   - Export typed async functions
   - Use the shared `api` instance from lib/api.ts
   - Include mock mode support with `isMock()` check
   - Handle errors with try/catch and fallback

4. **Verify**
   - Check types match backend Pydantic models exactly
   - Ensure optional fields are marked correctly
   - Test mock mode returns valid data

## Behaviors

- Export typed async functions from API modules
- Use snake_case for request bodies (matching backend)
- Support mock mode via `isMock()` check
- Handle errors with try/catch and console.warn fallback
- Define separate interfaces for Create/Update DTOs
- Use `api` instance from `lib/api.ts` for all requests

## Constraints

- Never use `any` type - always define interfaces
- Never hardcode API URLs (use `api` instance base URL)
- Always match backend Pydantic model field names exactly
- Never expose error details to UI without sanitization
- Never skip TypeScript strict checks

## Safety Checks

Before completing:
- [ ] TypeScript interfaces match backend Pydantic models
- [ ] Optional fields correctly marked with `?`
- [ ] Mock data structure matches real API response
- [ ] Error handling includes console.warn for debugging
- [ ] All exported functions have return type annotations
- [ ] No breaking changes to existing type consumers
