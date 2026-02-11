// src/api/analytics.ts
import { api } from '@/lib/api';

export type KeywordHit = { keyword: string; count: number };
export type HourlyPoint = { hour: string; count: number };
export type TalkgroupHit = { groupId: string; display?: string; count: number };

const isMock = import.meta.env.VITE_MOCK === '1';

const mockKeywordHits: KeywordHit[] = [
  { keyword: 'pursuit', count: 12 },
  { keyword: 'accident', count: 9 },
  { keyword: 'alarm', count: 7 },
];

const mockHourly: HourlyPoint[] = [
  { hour: '00', count: 4 }, { hour: '01', count: 3 }, { hour: '02', count: 2 },
  { hour: '03', count: 2 }, { hour: '04', count: 1 }, { hour: '05', count: 1 },
  { hour: '06', count: 2 }, { hour: '07', count: 5 }, { hour: '08', count: 7 },
  { hour: '09', count: 6 }, { hour: '10', count: 8 }, { hour: '11', count: 9 },
  { hour: '12', count: 11 }, { hour: '13', count: 12 }, { hour: '14', count: 10 },
  { hour: '15', count: 9 }, { hour: '16', count: 8 }, { hour: '17', count: 7 },
  { hour: '18', count: 10 }, { hour: '19', count: 12 }, { hour: '20', count: 14 },
  { hour: '21', count: 13 }, { hour: '22', count: 9 }, { hour: '23', count: 6 },
];

const mockTopTalkgroups: TalkgroupHit[] = [
  { groupId: '7017-38529', display: 'SAFD Alert', count: 42 },
  { groupId: '7017-38273', display: 'SAPD NORTH A PTL', count: 38 },
  { groupId: '7017-39043', display: 'Fire Tac 3', count: 22 },
];

export type DashboardMetrics = {
  total_calls_24h: number;
  active_playlists: number;
  transcripts_today: number;
  avg_transcription_confidence: number;
  processing_queue_size: number;
  api_calls_today: number;
  recent_calls: any[];
  top_talkgroups: TalkgroupHit[];
};

const mockDashboardMetrics: DashboardMetrics = {
  total_calls_24h: 145,
  active_playlists: 8,
  transcripts_today: 127,
  avg_transcription_confidence: 0.82,
  processing_queue_size: 3,
  api_calls_today: 247,
  recent_calls: [],
  top_talkgroups: mockTopTalkgroups
};

export async function fetchKeywordHits(): Promise<KeywordHit[]> {
  if (isMock) return mockKeywordHits;
  try {
    const res = await api.get<KeywordHit[]>('/analytics/keywords');
    return res.data ?? [];
  } catch (error) {
    console.error('Failed to fetch keyword hits', error);
    throw error;
  }
}

export async function getDashboardMetrics(): Promise<DashboardMetrics> {
  if (isMock) return mockDashboardMetrics;
  try {
    const res = await api.get<DashboardMetrics>('/analytics/dashboard');
    return res.data;
  } catch (error) {
    console.error('Failed to fetch dashboard metrics', error);
    throw error;
  }
}

export async function fetchHourlyActivity(): Promise<HourlyPoint[]> {
  if (isMock) return mockHourly;
  try {
    const res = await api.get<HourlyPoint[]>('/analytics/hourly');
    return res.data ?? [];
  } catch (error) {
    console.error('Failed to fetch hourly activity', error);
    throw error;
  }
}

export async function fetchTopTalkgroups(limit = 10): Promise<TalkgroupHit[]> {
  if (isMock) return mockTopTalkgroups.slice(0, limit);
  try {
    const res = await api.get<TalkgroupHit[]>(`/analytics/talkgroups/top?limit=${limit}`);
    const data = res.data ?? [];
    return data.slice(0, limit);
  } catch (error) {
    console.error('Failed to fetch top talkgroups', error);
    throw error;
  }
}

// Export aliases for Dashboard compatibility
export const getKeywordHits = fetchKeywordHits;
