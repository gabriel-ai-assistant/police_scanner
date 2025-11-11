import type { Call } from '../types/call';
import api from './client';
import { mockCalls } from './mockData';

export async function getCalls(params?: { feedId?: string }): Promise<Call[]> {
  try {
    const response = await api.get<Call[]>('/calls', { params });
    return response.data;
  } catch (error) {
    console.warn('Using mock calls due to API error', error);
    if (params?.feedId) {
      return mockCalls.filter((call) => call.feedId === params.feedId);
    }
    return mockCalls;
  }
}

export async function getCall(id: string): Promise<Call | undefined> {
  try {
    const response = await api.get<Call>(`/calls/${id}`);
    return response.data;
  } catch (error) {
    console.warn('Using mock call due to API error', error);
    return mockCalls.find((call) => call.id === id);
  }
}
