import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ThumbsUp, ThumbsDown } from 'lucide-react';

import { rateTranscript } from '../api/dashboard';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { formatTime } from '../lib/dates';
import type { RecentActivity } from '../types/dashboard';

interface ActivityItemProps {
  activity: RecentActivity;
}

export function ActivityItem({ activity }: ActivityItemProps) {
  const queryClient = useQueryClient();
  const [localRating, setLocalRating] = useState<boolean | null>(activity.userRating ?? null);

  // Sync local state when activity data changes (e.g., after query refetch)
  useEffect(() => {
    setLocalRating(activity.userRating ?? null);
  }, [activity.userRating]);

  const ratingMutation = useMutation({
    mutationFn: ({ transcriptId, rating }: { transcriptId: number; rating: boolean }) =>
      rateTranscript(transcriptId, rating),
    onMutate: async ({ rating }) => {
      // Optimistic update
      if (localRating === rating) {
        setLocalRating(null); // Toggle off
      } else {
        setLocalRating(rating);
      }
    },
    onSuccess: (data) => {
      // Handle toggle-off case
      if ('deleted' in data && data.deleted) {
        setLocalRating(null);
      }
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'recent-activity'] });
    },
    onError: () => {
      // Revert on error
      setLocalRating(activity.userRating ?? null);
    },
  });

  const handleRate = (rating: boolean) => {
    if (!activity.transcriptId) return;
    ratingMutation.mutate({ transcriptId: activity.transcriptId, rating });
  };

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      {/* Header: Feed badge + timestamp */}
      <div className="flex items-center justify-between mb-3">
        <Badge variant="outline">{activity.feedName ?? 'Unknown'}</Badge>
        <span className="text-xs text-muted-foreground">
          {activity.timestamp ? formatTime(activity.timestamp) : '---'}
        </span>
      </div>

      {/* Transcript text (if available) */}
      {activity.transcriptText ? (
        <p className="text-sm line-clamp-2 mb-3">{activity.transcriptText}</p>
      ) : (
        <p className="text-sm text-muted-foreground italic mb-3">Transcript not available</p>
      )}

      {/* Footer: Duration, Audio, Rating buttons */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1">
          {/* Duration */}
          {activity.duration && (
            <span className="text-xs text-muted-foreground whitespace-nowrap">{activity.duration}s</span>
          )}

          {/* Audio player */}
          {activity.audioUrl ? (
            <audio controls className="h-8 flex-1 min-w-0">
              <source src={activity.audioUrl} type="audio/wav" />
              <source src={activity.audioUrl} type="audio/mpeg" />
            </audio>
          ) : (
            <span className="text-xs text-muted-foreground">Audio unavailable</span>
          )}
        </div>

        {/* Rating buttons (only if transcript exists) */}
        {activity.transcriptId && (
          <div className="flex items-center gap-1 flex-shrink-0">
            <Button
              variant="ghost"
              size="icon"
              className={`h-8 w-8 ${localRating === true ? 'text-green-600 bg-green-100 hover:bg-green-200' : ''}`}
              onClick={() => handleRate(true)}
              disabled={ratingMutation.isPending}
              title="Good transcript"
            >
              <ThumbsUp className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className={`h-8 w-8 ${localRating === false ? 'text-red-600 bg-red-100 hover:bg-red-200' : ''}`}
              onClick={() => handleRate(false)}
              disabled={ratingMutation.isPending}
              title="Poor transcript"
            >
              <ThumbsDown className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>

      {/* Confidence indicator (if transcript exists) */}
      {activity.transcriptConfidence != null && (
        <p className="text-xs text-muted-foreground mt-2">
          Confidence: {(activity.transcriptConfidence * 100).toFixed(0)}%
        </p>
      )}
    </div>
  );
}

export default ActivityItem;
