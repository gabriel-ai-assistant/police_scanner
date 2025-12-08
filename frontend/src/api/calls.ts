import { api } from '@/lib/api';

export interface Call {
  id: string;
  call_uid?: string;
  feed_id?: number;
  tg_id?: number;
  started_at?: string;
  duration_ms?: number;
  processed?: boolean;
}

export async function getRecentCalls(limit: number = 50): Promise<Call[]> {
  try {
    const res = await api.get('/calls', { params: { limit } });
    return res.data ?? [];
  } catch (e) {
    console.error('getRecentCalls failed', e);
    return [];
  }
}

export async function getCallsByFeed(feedId: number, limit: number = 50): Promise<Call[]> {
  try {
    const res = await api.get('/calls', { params: { feed_id: feedId, limit } });
    return res.data ?? [];
  } catch (e) {
    console.error('getCallsByFeed failed', e);
    return [];
  }
}

// Export alias for Dashboard compatibility
export const getCalls = getRecentCalls;
