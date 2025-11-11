import type { Call } from '../types/call';
import api, { normalizeListResponse } from './client';
import api from './client';
import { mockCalls } from './mockData';

export async function getCalls(params?: { feedId?: string }): Promise<Call[]> {
  try {
    const response = await api.get<Call[]>('/calls', { params });
    const calls = normalizeListResponse<Call>(response.data);
    if (calls !== null) {
      return calls;
    }
    console.warn('Unexpected calls payload, using mock data', response.data);
    return response.data;
  } catch (error) {
    console.warn('Using mock calls due to API error', error);
    if (params?.feedId) {
      return mockCalls.filter((call) => call.feedId === params.feedId);
    }
  }
  return mockCalls;
    return mockCalls;
  }
}

export async function getCall(id: string): Promise<Call | undefined> {
  try {
    const response = await api.get<Call | Call[]>(`/calls/${id}`);
    const maybeArray = normalizeListResponse<Call>(response.data);
    if (maybeArray !== null) {
      return maybeArray.find((call) => call.id === id);
    }
    if (response.data !== undefined) {
      console.warn('Unexpected call payload, attempting to normalize', response.data);
    }
    if (response.data && typeof response.data === 'object' && 'id' in response.data) {
      return response.data as Call;
    }
  } catch (error) {
    console.warn('Using mock call due to API error', error);
  }
  return mockCalls.find((call) => call.id === id);
    const response = await api.get<Call>(`/calls/${id}`);
    return response.data;
  } catch (error) {
    console.warn('Using mock call due to API error', error);
    return mockCalls.find((call) => call.id === id);
  }
}
