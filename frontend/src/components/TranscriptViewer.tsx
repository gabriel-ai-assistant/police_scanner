import { Fragment, useMemo } from 'react';

import type { Transcript } from '../types/transcript';
import { Badge } from './ui/badge';

interface TranscriptViewerProps {
  transcript: Transcript;
  highlight?: string;
}

function formatTime(seconds: number) {
  const minutes = Math.floor(seconds / 60)
    .toString()
    .padStart(2, '0');
  const secs = Math.floor(seconds % 60)
    .toString()
    .padStart(2, '0');
  return `${minutes}:${secs}`;
}

function TranscriptViewer({ transcript, highlight }: TranscriptViewerProps) {
  const normalizedHighlight = highlight?.toLowerCase();

  const segments = useMemo(() => (Array.isArray(transcript.segments) ? transcript.segments : []), [transcript.segments]);

  return (
    <div className="space-y-4">
      {transcript.summary ? <p className="text-sm text-muted-foreground">{transcript.summary}</p> : null}
      {segments.map((segment) => {
        const text = normalizedHighlight
          ? segment.text.split(new RegExp(`(${normalizedHighlight})`, 'ig')).map((part, index) => (
              <Fragment key={`${segment.id}-${index}`}>
                {part.toLowerCase() === normalizedHighlight ? (
                  <mark className="rounded bg-yellow-200 px-1 text-foreground dark:bg-yellow-600/50">{part}</mark>
                ) : (
                  part
                )}
              </Fragment>
            ))
          : segment.text;

        return (
          <div key={segment.id} className="rounded-lg border border-border bg-card/60 p-4">
            <div className="mb-1 flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
              <Badge variant="secondary">{formatTime(segment.start)}</Badge>
              <span>{formatTime(segment.end)}</span>
              {(segment.keywords ?? []).map((keyword) => (
                <Badge key={keyword} variant="outline" className="capitalize">
                  {keyword}
                </Badge>
              ))}
            </div>
            <p className="text-sm leading-relaxed">{text}</p>
          </div>
        );
      })}
    </div>
  );
}

export default TranscriptViewer;
