/**
 * BUG-024: Verify types/dashboard.ts exports all required types
 * and they match what dashboard API module expects.
 *
 * This is a compile-time test - if types are missing or mismatched,
 * TypeScript will fail to compile this file.
 */

import { describe, it, expect } from 'vitest';
import type {
  DashboardStats,
  MyFeed,
  MyFeedsResponse,
  RecentCall,
  RecentCallsResponse,
  RecentTranscript,
  RecentTranscriptsResponse,
  KeywordGroupSummary,
  KeywordSummaryResponse,
  RecentActivity,
  RecentActivityResponse,
  TranscriptRating,
  TranscriptRatingRequest,
  TranscriptRatingDeleteResponse,
} from '@/types/dashboard';

describe('BUG-024: Dashboard types exist and are structurally correct', () => {
  it('DashboardStats has expected fields', () => {
    const stats: DashboardStats = {
      myFeeds: 1,
      myCalls1h: 2,
      myTranscripts24h: 3,
    };
    expect(stats.myFeeds).toBe(1);
  });

  it('MyFeed has expected fields', () => {
    const feed: MyFeed = {
      id: 'feed-1',
      name: 'Test Feed',
      listeners: 100,
      isActive: true,
    };
    expect(feed.id).toBe('feed-1');
  });

  it('MyFeedsResponse has expected fields', () => {
    const resp: MyFeedsResponse = {
      feeds: [],
      total: 0,
      hasMore: false,
    };
    expect(resp.total).toBe(0);
  });

  it('RecentCall has expected fields', () => {
    const call: RecentCall = { id: 'call-1' };
    expect(call.id).toBe('call-1');
  });

  it('RecentActivity has expected fields', () => {
    const activity: RecentActivity = {
      id: 'act-1',
      userRating: null,
    };
    expect(activity.userRating).toBeNull();
  });

  it('TranscriptRating has expected fields', () => {
    const rating: TranscriptRating = {
      id: 'r-1',
      transcriptId: 42,
      rating: true,
    };
    expect(rating.rating).toBe(true);
  });

  it('TranscriptRatingDeleteResponse has expected fields', () => {
    const resp: TranscriptRatingDeleteResponse = {
      deleted: true,
      message: 'Rating removed',
    };
    expect(resp.deleted).toBe(true);
  });
});
