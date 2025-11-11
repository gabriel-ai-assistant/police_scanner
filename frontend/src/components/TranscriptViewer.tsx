import { useMemo } from 'react';
import { Badge } from './ui/badge';

type Segment = {
  start?: number;
  end?: number;
  text?: string;
  keywords?: string[];
};

type Transcript = {
  id: number | string;
  segments?: Segment[];
};

function formatTime(s?: number) {
  if (typeof s !== 'number' || Number.isNaN(s)) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60).toString().padStart(2, '0');
  return `${m}:${sec}`;
}

export default function TranscriptViewer({
  transcript,
  highlight
}: {
  transcript: Transcript;
  highlight?: string;
}) {
  const segments = useMemo<Segment[]>(
    () => (Array.isArray(transcript.segments) ? transcript.segments : []),
    [transcript.segments]
  );

  return (
    <div className="space-y-3">
      {segments.map((segment, idx) => (
        <div
          key={idx}
          className="rounded-md border border-border p-3 text-sm bg-card"
        >
          <div className="mb-2 flex items-center gap-3 text-muted-foreground">
            <span>{formatTime(segment.start)}</span>
            <span>→</span>
            <span>{formatTime(segment.end)}</span>
            {(segment.keywords ?? []).map((keyword) => (
              <Badge key={keyword} variant="outline" className="capitalize">
                {keyword}
              </Badge>
            ))}
          </div>
          <div className="leading-relaxed">
            {segment.text ?? ''}
          </div>
        </div>
      ))}
      {segments.length === 0 && (
        <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
          No segments available.
        </div>
      )}
    </div>
  );
}
