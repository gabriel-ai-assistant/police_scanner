import { apiClient } from './client';

export interface Call {
  id: string;
  feedId?: number;
  tgId?: number;
  startedAt?: string;
  durationSeconds?: number;
}

export async function getRecentCalls(): Promise<Call[]> {
  try {
    const res = await apiClient.get('/api/calls/recent');
    return res.data ?? [];
  } catch (e) {
    console.error('getRecentCalls failed', e);
    return [];
  }
}

export async function getCallsByFeed(feedId: number): Promise<Call[]> {
  try {
    const res = await apiClient.get(`/api/calls?feedId=${feedId}`);
    return res.data ?? [];
  } catch (e) {
    console.error('getCallsByFeed failed', e);
    return [];
  }
}
