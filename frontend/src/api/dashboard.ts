/**
 * Dashboard API module for personalized user experience.
 */

import { api, isMock } from '@/lib/api';
import type {
  DashboardStats,
  MyFeedsResponse,
  RecentCallsResponse,
  RecentTranscriptsResponse,
  KeywordSummaryResponse,
  RecentActivityResponse,
  TranscriptRating,
  TranscriptRatingDeleteResponse,
} from '@/types/dashboard';

// Mock data for development
const mockStats: DashboardStats = {
  myFeeds: 2,
  myCalls1h: 42,
  myTranscripts24h: 128,
};

const mockFeeds: MyFeedsResponse = {
  feeds: [
    {
      id: 'feed-1',
      name: 'Prosper PD',
      description: 'Prosper Police Department',
      listeners: 1234,
      isActive: true,
      updatedAt: new Date().toISOString(),
      subscribedAt: new Date().toISOString(),
    },
    {
      id: 'feed-2',
      name: 'Frisco PD',
      description: 'Frisco Police Department',
      listeners: 567,
      isActive: true,
      updatedAt: new Date().toISOString(),
      subscribedAt: new Date().toISOString(),
    },
  ],
  total: 2,
  hasMore: false,
};

const mockCalls: RecentCallsResponse = {
  calls: [
    {
      id: 'call-1',
      timestamp: new Date().toISOString(),
      talkgroup: '12345',
      duration: 15,
      feedName: 'Prosper PD',
      feedId: 'feed-1',
      audioUrl: undefined,
    },
  ],
};

const mockTranscripts: RecentTranscriptsResponse = {
  transcripts: [
    {
      id: 1,
      text: 'Unit 5 responding to Main Street...',
      confidence: 0.92,
      createdAt: new Date().toISOString(),
      feedName: 'Prosper PD',
      feedId: 'feed-1',
      callId: 'call-1',
    },
  ],
};

const mockKeywordSummary: KeywordSummaryResponse = {
  groups: [
    { name: 'Home Streets', keywordCount: 15, isActive: true },
    { name: 'Emergency Codes', keywordCount: 9, isActive: true },
  ],
  totalKeywords: 24,
  message: 'Keyword matching coming soon',
};

const mockActivities: RecentActivityResponse = {
  activities: [
    {
      id: 'call-1',
      timestamp: new Date().toISOString(),
      talkgroup: '12345',
      duration: 15,
      feedName: 'Prosper PD',
      feedId: 'feed-1',
      audioUrl: undefined,
      transcriptId: 1,
      transcriptText: 'Unit 5 responding to Main Street...',
      transcriptConfidence: 0.92,
      userRating: null,
    },
    {
      id: 'call-2',
      timestamp: new Date(Date.now() - 60000).toISOString(),
      talkgroup: '12346',
      duration: 22,
      feedName: 'Frisco PD',
      feedId: 'feed-2',
      audioUrl: undefined,
      transcriptId: 2,
      transcriptText: 'Copy that, en route to Oak Street location.',
      transcriptConfidence: 0.88,
      userRating: true,
    },
  ],
};

/**
 * Get dashboard statistics for the current user
 */
export async function getDashboardStats(): Promise<DashboardStats> {
  if (isMock()) {
    return mockStats;
  }

  try {
    const response = await api.get<DashboardStats>('/dashboard/stats');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch dashboard stats', error);
    throw error;
  }
}

/**
 * Get user's subscribed feeds for dashboard display
 */
export async function getMyFeeds(limit: number = 6): Promise<MyFeedsResponse> {
  if (isMock()) {
    return mockFeeds;
  }

  try {
    const response = await api.get<MyFeedsResponse>('/dashboard/my-feeds', {
      params: { limit },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch my feeds', error);
    throw error;
  }
}

/**
 * Get recent calls from user's subscribed feeds
 */
export async function getRecentCalls(limit: number = 10): Promise<RecentCallsResponse> {
  if (isMock()) {
    return mockCalls;
  }

  try {
    const response = await api.get<RecentCallsResponse>('/dashboard/recent-calls', {
      params: { limit },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch recent calls', error);
    throw error;
  }
}

/**
 * Get recent transcripts from user's subscribed feeds
 */
export async function getRecentTranscripts(limit: number = 10): Promise<RecentTranscriptsResponse> {
  if (isMock()) {
    return mockTranscripts;
  }

  try {
    const response = await api.get<RecentTranscriptsResponse>('/dashboard/recent-transcripts', {
      params: { limit },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch recent transcripts', error);
    throw error;
  }
}

/**
 * Get summary of user's keyword groups (placeholder until matching engine is built)
 */
export async function getKeywordSummary(): Promise<KeywordSummaryResponse> {
  if (isMock()) {
    return mockKeywordSummary;
  }

  try {
    const response = await api.get<KeywordSummaryResponse>('/dashboard/keyword-summary');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch keyword summary', error);
    throw error;
  }
}

/**
 * Get recent activity (calls + transcripts) from user's subscribed feeds
 */
export async function getRecentActivity(limit: number = 10): Promise<RecentActivityResponse> {
  if (isMock()) {
    return mockActivities;
  }

  try {
    const response = await api.get<RecentActivityResponse>('/dashboard/recent-activity', {
      params: { limit },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch recent activity', error);
    throw error;
  }
}

/**
 * Rate a transcript (thumbs up/down)
 * Toggle behavior: clicking same rating again removes it
 */
export async function rateTranscript(
  transcriptId: number,
  rating: boolean
): Promise<TranscriptRating | TranscriptRatingDeleteResponse> {
  if (isMock()) {
    return {
      id: `rating-${Date.now()}`,
      transcriptId,
      rating,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  }

  const response = await api.put<TranscriptRating | TranscriptRatingDeleteResponse>(
    `/ratings/${transcriptId}`,
    { rating }
  );
  return response.data;
}

/**
 * Remove a transcript rating
 */
export async function deleteTranscriptRating(transcriptId: number): Promise<void> {
  if (isMock()) {
    return;
  }

  await api.delete(`/ratings/${transcriptId}`);
}
