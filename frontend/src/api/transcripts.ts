import type { Transcript } from '../types/transcript';
import api from './client';
import { mockTranscripts } from './mockData';

export async function getTranscript(id: string): Promise<Transcript | undefined> {
  try {
    const response = await api.get<Transcript>(`/transcripts/${id}`);
    return response.data;
  } catch (error) {
    console.warn('Using mock transcript due to API error', error);
    return mockTranscripts.find((transcript) => transcript.id === id);
  }
}

export async function searchTranscripts(query: string): Promise<Transcript[]> {
  try {
    const response = await api.get<Transcript[]>('/search', { params: { q: query } });
    return response.data;
  } catch (error) {
    console.warn('Using mock transcripts due to API error', error);
    const term = query.toLowerCase();
    if (!term) return mockTranscripts;
    return mockTranscripts.filter((transcript) =>
      transcript.segments.some((segment) => segment.text.toLowerCase().includes(term))
    );
  }
}
