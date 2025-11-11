import type { Transcript } from '../types/transcript';
import api, { normalizeListResponse } from './client';
import { mockTranscripts } from './mockData';

export async function getTranscript(id: string): Promise<Transcript | undefined> {
  try {
    const response = await api.get<Transcript | Transcript[]>(`/transcripts/${id}`);
    const maybeArray = normalizeListResponse<Transcript>(response.data);
    if (maybeArray !== null) {
      return maybeArray.find((transcript) => transcript.id === id);
    }
    if (response.data && typeof response.data === 'object') {
      const transcript = normalizeTranscript(response.data);
      if (transcript) {
        return transcript;
      }
    }
  } catch (error) {
    console.warn('Using mock transcript due to API error', error);
  }
  return mockTranscripts.find((transcript) => transcript.id === id);
}

export async function searchTranscripts(query: string): Promise<Transcript[]> {
  try {
    const response = await api.get<Transcript[] | Record<string, unknown>>('/search', { params: { q: query } });
    const transcripts = normalizeListResponse<Transcript>(response.data);
    if (transcripts !== null) {
      return transcripts.map(normalizeTranscript).filter((value): value is Transcript => Boolean(value));
    }
    if (response.data && typeof response.data === 'object') {
      const hits = normalizeListResponse<Record<string, unknown>>((response.data as Record<string, unknown>).hits);
      if (hits !== null) {
        return hits
          .map((hit) => normalizeTranscript(hit.document ?? hit.payload ?? hit))
          .filter((value): value is Transcript => Boolean(value));
      }
    }
    console.warn('Unexpected transcript search payload, using mock data', response.data);
  } catch (error) {
    console.warn('Using mock transcripts due to API error', error);
    const term = query.toLowerCase();
    if (!term) return mockTranscripts;
    return mockTranscripts.filter((transcript) =>
      transcript.segments.some((segment) => segment.text.toLowerCase().includes(term))
    );
  }
  if (!query) {
    return mockTranscripts;
  }
  const term = query.toLowerCase();
  return mockTranscripts.filter((transcript) =>
    transcript.segments.some((segment) => segment.text.toLowerCase().includes(term))
  );
}

function normalizeTranscript(value: unknown): Transcript | null {
  if (!value || typeof value !== 'object') {
    return null;
  }

  const record = value as Record<string, unknown>;
  const id = typeof record.id === 'string' ? record.id : typeof record.transcript_id === 'string' ? record.transcript_id : null;
  const callId = typeof record.callId === 'string' ? record.callId : typeof record.call_id === 'string' ? record.call_id : '';
  const feedId = typeof record.feedId === 'string' ? record.feedId : typeof record.feed_id === 'string' ? record.feed_id : '';
  const createdAtValue = record.createdAt ?? record.created_at ?? record.timestamp;
  const createdAt = typeof createdAtValue === 'string' ? createdAtValue : new Date().toISOString();
  const summary = typeof record.summary === 'string' ? record.summary : undefined;
  const segmentsRaw = record.segments ?? record.chunks ?? record.parts ?? [];
  const segmentsList = normalizeListResponse<Transcript['segments'][number]>(segmentsRaw);
  const segments = (segmentsList ?? []).map((segment, index) => normalizeSegment(segment, index, id ?? `segment-${index}`));

  if (!id) {
    return null;
  }

  return {
    id,
    callId,
    feedId,
    createdAt,
    summary,
    segments
  };
}

function normalizeSegment(
  value: unknown,
  index: number,
  parentId: string
): Transcript['segments'][number] {
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const id = typeof record.id === 'string' ? record.id : `${parentId}-${index}`;
    const startValue = record.start ?? record.start_time ?? record.begin ?? 0;
    const endValue = record.end ?? record.end_time ?? record.finish ?? startValue;
    const textValue = record.text ?? record.caption ?? record.content ?? '';
    const keywordsValue = record.keywords ?? record.tags ?? record.alerts;

    return {
      id,
      start: typeof startValue === 'number' ? startValue : Number(startValue) || 0,
      end: typeof endValue === 'number' ? endValue : Number(endValue) || 0,
      text: typeof textValue === 'string' ? textValue : String(textValue ?? ''),
      keywords: Array.isArray(keywordsValue) ? keywordsValue.map((keyword) => String(keyword)) : undefined
    };
  }

  return {
    id: `${parentId}-${index}`,
    start: 0,
    end: 0,
    text: String(value ?? ''),
    keywords: undefined
  };
}
