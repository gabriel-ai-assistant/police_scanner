---
name: "React Query Patterns"
description: "Implement and optimize TanStack Query usage"
---

## Context

Use this skill when working with TanStack Query (React Query) for data fetching and state management in the frontend. This includes query configuration, mutations, and caching strategies.

## Scope

Files this agent works with:
- `frontend/src/pages/*.tsx` - Query usage in pages
- `frontend/src/hooks/*.ts` - Custom query hooks
- `frontend/src/main.tsx` - QueryClient configuration

## Instructions

When invoked, follow these steps:

1. **Understand the requirement**
   - Identify if it's a read (query) or write (mutation)
   - Check existing query patterns in similar components
   - Determine caching/refetch requirements

2. **Design the query**
   - Define unique query key structure
   - Configure staleTime/cacheTime appropriately
   - Plan query invalidation strategy

3. **Implement**
   - Use useQuery for reads, useMutation for writes
   - Add proper error handling
   - Implement loading states

4. **Verify**
   - Check query devtools for cache behavior
   - Test refetch and invalidation
   - Verify optimistic updates work correctly

## Behaviors

- Use composite query keys: `['entity', 'action', params]`
- Invalidate queries after mutations
- Configure staleTime/cacheTime appropriately
- Use optimistic updates for better UX
- Handle error states with retry logic

## Constraints

- Never use `useEffect` for data fetching
- Never store server state in `useState`
- Always provide error handling in queries
- Never use string-only query keys (use arrays)
- Never skip loading state handling

## Safety Checks

Before completing:
- [ ] Query keys are unique and descriptive
- [ ] Loading states handled (isLoading, isFetching)
- [ ] Error states handled (isError, error)
- [ ] Mutations invalidate related queries
- [ ] Optimistic updates have rollback on error

## Query Client Configuration

```typescript
// main.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,           // 1 minute
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});
```

## Query Patterns

```typescript
// Basic query
const { data, isLoading, isError, refetch } = useQuery({
  queryKey: ['dashboard', 'stats'],
  queryFn: getDashboardStats,
});

// Query with params
const { data } = useQuery({
  queryKey: ['subscription', subscriptionId],
  queryFn: () => getSubscription(subscriptionId),
  enabled: !!subscriptionId,  // Only fetch when ID exists
});

// Query with refetch interval
const { data } = useQuery({
  queryKey: ['dashboard', 'stats'],
  queryFn: getDashboardStats,
  refetchInterval: 30000,  // Refetch every 30 seconds
});
```

## Mutation Patterns

```typescript
// Basic mutation with invalidation
const updateMutation = useMutation({
  mutationFn: (data) => updateSubscription(id, data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['subscription', id] });
    queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
  },
  onError: (error) => {
    alert(`Update failed: ${error.message}`);
  },
});

// Optimistic update
const rateMutation = useMutation({
  mutationFn: (rating) => submitRating(transcriptId, rating),
  onMutate: async (newRating) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries({ queryKey: ['transcript', transcriptId] });

    // Snapshot previous value
    const previous = queryClient.getQueryData(['transcript', transcriptId]);

    // Optimistically update
    queryClient.setQueryData(['transcript', transcriptId], (old) => ({
      ...old,
      rating: newRating,
    }));

    return { previous };
  },
  onError: (err, newRating, context) => {
    // Rollback on error
    queryClient.setQueryData(['transcript', transcriptId], context.previous);
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ['transcript', transcriptId] });
  },
});
```

## Query Key Factory Pattern

```typescript
// queryKeys.ts
export const queryKeys = {
  dashboard: {
    all: ['dashboard'] as const,
    stats: () => [...queryKeys.dashboard.all, 'stats'] as const,
    myFeeds: () => [...queryKeys.dashboard.all, 'my-feeds'] as const,
  },
  subscriptions: {
    all: ['subscriptions'] as const,
    list: () => [...queryKeys.subscriptions.all, 'list'] as const,
    detail: (id: string) => [...queryKeys.subscriptions.all, 'detail', id] as const,
  },
};

// Usage
useQuery({
  queryKey: queryKeys.subscriptions.detail(id),
  queryFn: () => getSubscription(id),
});
```

## Error Handling

```typescript
// Component-level error handling
const { data, isError, error } = useQuery({
  queryKey: ['data'],
  queryFn: fetchData,
});

if (isError) {
  return <ErrorState title="Failed to load" description={error.message} onRetry={refetch} />;
}

// Global error handler
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      onError: (error) => console.error('Query error:', error),
    },
    mutations: {
      onError: (error) => console.error('Mutation error:', error),
    },
  },
});
```
