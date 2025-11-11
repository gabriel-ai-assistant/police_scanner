import type { Feed } from '../types/feed';
import api from './client';
import { mockFeeds } from './mockData';

export async function getFeeds(): Promise<Feed[]> {
  try {
    const response = await api.get<Feed[]>('/feeds');
    return response.data;
  } catch (error) {
    console.warn('Using mock feeds due to API error', error);
    return mockFeeds;
  }
}

export async function getFeed(id: string): Promise<Feed | undefined> {
  try {
    const response = await api.get<Feed>(`/feeds/${id}`);
    return response.data;
  } catch (error) {
    console.warn('Using mock feed due to API error', error);
    return mockFeeds.find((feed) => feed.id === id);
  }
}
