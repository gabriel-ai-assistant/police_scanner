import { Radio } from 'lucide-react';

import type { Feed } from '../types/feed';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { formatDate } from '../lib/dates';

interface FeedListProps {
  feeds: Feed[];
  onViewCalls?: (feedId: string) => void;
}

function FeedList({ feeds, onViewCalls }: FeedListProps) {
  if (!feeds.length) {
    return <div className="text-sm text-muted-foreground">No feeds available.</div>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {feeds.map((feed) => (
        <div key={feed.id} className="flex flex-col rounded-lg border border-border bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Radio className="h-4 w-4 text-primary" />
              <h3 className="text-base font-semibold">{feed.name}</h3>
            </div>
            <Badge variant={feed.isActive ? 'default' : 'secondary'}>{feed.isActive ? 'Active' : 'Idle'}</Badge>
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-muted-foreground">State</dt>
              <dd className="font-medium">{feed.state}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Listeners</dt>
              <dd className="font-medium">{feed.listeners.toLocaleString()}</dd>
            </div>
            <div className="col-span-2">
              <dt className="text-muted-foreground">Updated</dt>
              <dd className="font-medium">{formatDate(feed.updatedAt)}</dd>
            </div>
          </dl>
          {onViewCalls ? (
            <Button className="mt-4" onClick={() => onViewCalls(feed.id)}>
              View calls
            </Button>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export default FeedList;
