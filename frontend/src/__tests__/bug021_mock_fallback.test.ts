/**
 * BUG-021: Verify API modules throw errors in production instead of
 * silently falling back to mock data.
 *
 * Test strategy:
 * - Mock axios to reject with a network error
 * - Verify that API functions throw (not return mock data)
 * - Verify that with VITE_MOCK=1, mock data IS returned
 *
 * Requires: vitest (add to devDependencies)
 *   npm i -D vitest @testing-library/react @testing-library/jest-dom jsdom
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the @/lib/api module
vi.mock('@/lib/api', () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    defaults: { baseURL: '/api' },
  };
  return {
    api: mockAxiosInstance,
    isMock: vi.fn(() => false),  // default: NOT mock mode
  };
});

import { api, isMock } from '@/lib/api';
import type { Mock } from 'vitest';

describe('BUG-021: Dashboard API error handling', () => {
  beforeEach(() => {
    vi.resetModules();
    (api.get as Mock).mockRejectedValue(new Error('Network Error'));
    (isMock as Mock).mockReturnValue(false);
  });

  it('getDashboardStats throws on API error in production', async () => {
    const { getDashboardStats } = await import('@/api/dashboard');
    await expect(getDashboardStats()).rejects.toThrow();
  });

  it('getMyFeeds throws on API error in production', async () => {
    const { getMyFeeds } = await import('@/api/dashboard');
    await expect(getMyFeeds()).rejects.toThrow();
  });

  it('getRecentCalls throws on API error in production', async () => {
    const { getRecentCalls } = await import('@/api/dashboard');
    await expect(getRecentCalls()).rejects.toThrow();
  });

  it('getRecentTranscripts throws on API error in production', async () => {
    const { getRecentTranscripts } = await import('@/api/dashboard');
    await expect(getRecentTranscripts()).rejects.toThrow();
  });

  it('getKeywordSummary throws on API error in production', async () => {
    const { getKeywordSummary } = await import('@/api/dashboard');
    await expect(getKeywordSummary()).rejects.toThrow();
  });

  it('getRecentActivity throws on API error in production', async () => {
    const { getRecentActivity } = await import('@/api/dashboard');
    await expect(getRecentActivity()).rejects.toThrow();
  });

  it('getDashboardStats returns mock data when isMock() is true', async () => {
    (isMock as Mock).mockReturnValue(true);
    const { getDashboardStats } = await import('@/api/dashboard');
    const result = await getDashboardStats();
    expect(result).toBeDefined();
    expect(result.myFeeds).toBeDefined();
  });
});

describe('BUG-021: Analytics API error handling', () => {
  beforeEach(() => {
    vi.resetModules();
    (api.get as Mock).mockRejectedValue(new Error('Network Error'));
  });

  it('getDashboardMetrics throws on API error in production', async () => {
    const { getDashboardMetrics } = await import('@/api/analytics');
    await expect(getDashboardMetrics()).rejects.toThrow();
  });

  it('fetchHourlyActivity throws on API error in production', async () => {
    const { fetchHourlyActivity } = await import('@/api/analytics');
    await expect(fetchHourlyActivity()).rejects.toThrow();
  });

  it('fetchTopTalkgroups throws on API error in production', async () => {
    const { fetchTopTalkgroups } = await import('@/api/analytics');
    await expect(fetchTopTalkgroups()).rejects.toThrow();
  });

  it('fetchKeywordHits throws on API error in production', async () => {
    const { fetchKeywordHits } = await import('@/api/analytics');
    await expect(fetchKeywordHits()).rejects.toThrow();
  });
});

describe('BUG-021: Feeds API error handling', () => {
  beforeEach(() => {
    vi.resetModules();
    (api.get as Mock).mockRejectedValue(new Error('Network Error'));
  });

  it('fetchTopFeeds throws on API error in production', async () => {
    const { fetchTopFeeds } = await import('@/api/feeds');
    await expect(fetchTopFeeds()).rejects.toThrow();
  });
});

describe('BUG-021: Transcripts API error handling', () => {
  beforeEach(() => {
    vi.resetModules();
    (api.get as Mock).mockRejectedValue(new Error('Network Error'));
  });

  it('getTranscript throws on API error in production', async () => {
    const { getTranscript } = await import('@/api/transcripts');
    await expect(getTranscript(1)).rejects.toThrow();
  });

  it('listTranscripts throws on API error in production', async () => {
    const { listTranscripts } = await import('@/api/transcripts');
    await expect(listTranscripts()).rejects.toThrow();
  });

  it('searchTranscripts throws on API error in production', async () => {
    const { searchTranscripts } = await import('@/api/transcripts');
    await expect(searchTranscripts('test')).rejects.toThrow();
  });
});
