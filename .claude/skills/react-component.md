---
name: "React Component"
description: "Implement and refactor React components and pages"
---

## Context

Use this skill when working with React components in the Police Scanner frontend. This includes creating new pages, building reusable components, fixing UI bugs, and refactoring existing components.

## Scope

Files this agent works with:
- `frontend/src/pages/*.tsx` - Route-level page components
- `frontend/src/components/*.tsx` - Reusable UI components
- `frontend/src/components/ui/*.tsx` - Radix UI primitive wrappers
- `frontend/src/hooks/*.ts` - Custom React hooks

## Instructions

When invoked, follow these steps:

1. **Understand the task**
   - Identify the component type: page, feature component, or UI primitive
   - Check if similar components exist to follow patterns
   - Determine data requirements (API calls, props, context)

2. **Analyze existing patterns**
   - Read a similar existing component for structure reference
   - Check how data fetching is handled (useQuery)
   - Note styling patterns (Tailwind classes)

3. **Implement the component**
   - Create functional component with TypeScript types
   - Use React Query for server state (useQuery/useMutation)
   - Follow structure: hooks → derived state → handlers → JSX
   - Apply Tailwind CSS for styling

4. **Verify**
   - Check loading/error states are handled
   - Verify TypeScript has no errors
   - Ensure accessibility (aria labels, keyboard support)

## Behaviors

- Use functional components with hooks (no class components)
- Use `useQuery`/`useMutation` from TanStack Query for data fetching
- Use `queryClient.invalidateQueries()` after mutations
- Follow existing component structure: hooks → derived state → handlers → JSX
- Use Tailwind CSS utilities for styling
- Use Radix UI components from `components/ui/`

## Constraints

- Never use `useEffect` for data fetching (use React Query instead)
- Never store server state in `useState` (use React Query cache)
- Never use inline styles (use Tailwind utility classes)
- Never skip loading/error state handling
- Never use `any` type - always define proper TypeScript interfaces

## Safety Checks

Before completing:
- [ ] Component handles loading state (shows spinner/skeleton)
- [ ] Component handles error state (shows error message with retry)
- [ ] TypeScript types match API response shapes
- [ ] Accessible markup used (aria-label, role, keyboard nav)
- [ ] Query keys are unique and descriptive
- [ ] Mutations invalidate relevant queries
