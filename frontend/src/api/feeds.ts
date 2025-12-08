// src/api/feeds.ts
import { api } from '@/lib/api';

export type Feed = {
  uuid: string;
  name: string;
  descr?: string;
  listeners?: number;
  num_groups?: number;
  sync: boolean;
};

const MOCK_FEEDS: Feed[] = [
  {
    uuid: "feed-1",
    name: "Indianapolis Metropolitan Police",
    listeners: 396,
    num_groups: 5,
    sync: true,
  },
  { uuid: "feed-2", name: "Dallas / Collin County Public Safety", listeners: 182, sync: true },
  { uuid: "feed-3", name: "Prosper Police / Fire", listeners: 74, sync: false },
];

const isMock = import.meta.env.VITE_MOCK === '1';

export async function fetchTopFeeds(top = 25): Promise<Feed[]> {
  if (isMock) return MOCK_FEEDS.slice(0, top);
  try {
    const res = await api.get('/playlists', { params: { limit: top } });
    return res.data ?? MOCK_FEEDS.slice(0, top);
  } catch (e) {
    console.warn('fetchTopFeeds failed, using mock data', e);
    return MOCK_FEEDS.slice(0, top);
  }
}

// Export alias for Dashboard compatibility
export const getFeeds = fetchTopFeeds;
