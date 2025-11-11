export interface TranscriptSegment {
  id: string;
  start: number;
  end: number;
  text: string;
  keywords?: string[];
}

export interface Transcript {
  id: string;
  callId: string;
  feedId: string;
  createdAt: string;
  summary?: string;
  segments: TranscriptSegment[];
}
