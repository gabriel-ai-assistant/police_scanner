import type { Feed } from '../types/feed';
import api, { normalizeListResponse } from './client';
import api from './client';
import { mockFeeds } from './mockData';

export async function getFeeds(): Promise<Feed[]> {
  try {
    const response = await api.get<Feed[]>('/feeds');
    const feeds = normalizeListResponse<Feed>(response.data);
    if (feeds !== null) {
      return feeds;
    }
    console.warn('Unexpected feeds payload, using mock data', response.data);
  } catch (error) {
    console.warn('Using mock feeds due to API error', error);
  }
  return mockFeeds;
    return response.data;
  } catch (error) {
    console.warn('Using mock feeds due to API error', error);
    return mockFeeds;
  }
}

export async function getFeed(id: string): Promise<Feed | undefined> {
  try {
    const response = await api.get<Feed | Feed[]>(`/feeds/${id}`);
    const maybeArray = normalizeListResponse<Feed>(response.data);
    if (maybeArray !== null) {
      return maybeArray.find((feed) => feed.id === id);
    }
    if (response.data !== undefined) {
      console.warn('Unexpected feed payload, attempting to normalize', response.data);
    }
    if (response.data && typeof response.data === 'object' && 'id' in response.data) {
      return response.data as Feed;
    }
  } catch (error) {
    console.warn('Using mock feed due to API error', error);
  }
  return mockFeeds.find((feed) => feed.id === id);
    const response = await api.get<Feed>(`/feeds/${id}`);
    return response.data;
  } catch (error) {
    console.warn('Using mock feed due to API error', error);
    return mockFeeds.find((feed) => feed.id === id);
  }
}
