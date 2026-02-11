// src/api/transcripts.ts
import { api } from '@/lib/api';

export type Transcript = {
  id: number;
  call_uid?: string;
  text: string;
  confidence?: number;
  language?: string;
  created_at?: string;
};

const isMock = import.meta.env.VITE_MOCK === '1';

const mockTranscripts: Transcript[] = [
  { id: 1, call_uid: 'call-1', text: 'Unit 12 responding to scene.', confidence: 0.89, language: 'en' },
  { id: 2, call_uid: 'call-2', text: 'Fire alarm active at 5th & Main.', confidence: 0.92, language: 'en' },
];

export async function getTranscript(id: number): Promise<Transcript | undefined> {
  if (isMock) return mockTranscripts.find(t => t.id === id);
  try {
    const response = await api.get<Transcript>(`/transcripts/${id}`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch transcript', error);
    throw error;
  }
}

export async function listTranscripts(opts?: { callUid?: string; limit?: number }): Promise<Transcript[]> {
  const { callUid, limit = 20 } = opts || {};
  if (isMock) {
    const base = callUid ? mockTranscripts.filter(t => t.call_uid === callUid) : mockTranscripts;
    return base.slice(0, limit);
  }
  try {
    const params: Record<string, any> = { limit };
    if (callUid) params.call_uid = callUid;
    const response = await api.get<Transcript[]>('/transcripts', { params });
    return response.data ?? [];
  } catch (error) {
    console.error('Failed to fetch transcripts', error);
    throw error;
  }
}

export async function searchTranscripts(query: string = '', limit: number = 50): Promise<Transcript[]> {
  if (isMock) return mockTranscripts.slice(0, limit);
  try {
    const response = await api.get<Transcript[]>('/transcripts/search', { params: { q: query, limit } });
    return response.data ?? [];
  } catch (error) {
    console.error('Failed to search transcripts', error);
    throw error;
  }
}
