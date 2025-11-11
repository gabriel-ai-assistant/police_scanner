import api from './client';
import { mockCalls, mockFeeds, mockKeywordHits, mockTranscripts } from './mockData';
import type { KeywordSummary } from './mockData';

export interface DashboardMetrics {
  feedCount: number;
  activeFeeds: number;
  recentCalls: number;
  transcriptsToday: number;
}

export async function getDashboardMetrics(): Promise<DashboardMetrics> {
  try {
    const response = await api.get<DashboardMetrics>('/analytics/overview');
    return response.data;
  } catch (error) {
    console.warn('Using mock dashboard metrics due to API error', error);
    const recentCalls = mockCalls.filter((call) => Date.now() - new Date(call.timestamp).getTime() < 1000 * 60 * 60);
    const transcriptsToday = mockTranscripts.filter((transcript) => {
      const created = new Date(transcript.createdAt);
      const now = new Date();
      return (
        created.getFullYear() === now.getFullYear() &&
        created.getMonth() === now.getMonth() &&
        created.getDate() === now.getDate()
      );
    });
    return {
      feedCount: mockFeeds.length,
      activeFeeds: mockFeeds.filter((feed) => feed.isActive).length,
      recentCalls: recentCalls.length,
      transcriptsToday: transcriptsToday.length
    };
  }
}

export async function getKeywordHits(): Promise<KeywordSummary[]> {
  try {
    const response = await api.get<KeywordSummary[]>('/analytics/keyword-hits');
    return response.data;
  } catch (error) {
    console.warn('Using mock keyword hits due to API error', error);
    return mockKeywordHits;
  }
}
