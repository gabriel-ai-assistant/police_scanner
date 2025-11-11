// src/api/transcripts.ts
import { api } from '@/lib/api';

export type Transcript = {
  id: string;
  groupId?: string;
  ts?: number;
  text: string;
  src?: string;
};

const isMock = import.meta.env.VITE_MOCK === '1';

const mockTranscripts: Transcript[] = [
  { id: 'mock-1', groupId: '7017-38529', ts: 1730493701, text: 'Unit 12 responding to scene.', src: 'dispatcher' },
  { id: 'mock-2', groupId: '7017-38273', ts: 1730493755, text: 'Fire alarm active at 5th & Main.', src: 'engine-3' },
];

export async function getTranscript(id: string): Promise<Transcript | undefined> {
  if (isMock) return mockTranscripts.find(t => t.id === id);
  try {
    const response = await api.get<Transcript>(`/transcripts/${id}`);
    return response.data;
  } catch (error) {
    console.warn('Using mock transcript due to API error', error);
    return mockTranscripts.find(t => t.id === id);
  }
}

export async function listTranscripts(opts?: { groupId?: string; limit?: number }): Promise<Transcript[]> {
  const { groupId, limit = 20 } = opts || {};
  if (isMock) {
    const base = groupId ? mockTranscripts.filter(t => t.groupId === groupId) : mockTranscripts;
    return base.slice(0, limit);
  }
  try {
    const path = groupId ? `/transcripts?groupId=${encodeURIComponent(groupId)}&limit=${limit}` : `/transcripts?limit=${limit}`;
    const response = await api.get<Transcript[]>(path);
    return response.data ?? [];
  } catch (error) {
    console.warn('Using mock transcripts due to API error', error);
    const base = groupId ? mockTranscripts.filter(t => t.groupId === groupId) : mockTranscripts;
    return base.slice(0, limit);
  }
}
