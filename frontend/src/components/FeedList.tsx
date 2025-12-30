import { Bell, BellOff, Radio } from 'lucide-react';

import type { Feed } from '../types/feed';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { formatDate } from '../lib/dates';

interface FeedListProps {
  feeds: Feed[];
  onViewCalls?: (feedId: string) => void;
  subscriptionStatus?: Map<string, boolean>;
  onSubscribe?: (feedId: string) => void;
  onUnsubscribe?: (feedId: string) => void;
  isSubscribing?: boolean;
}

function FeedList({ feeds, onViewCalls, subscriptionStatus, onSubscribe, onUnsubscribe, isSubscribing }: FeedListProps) {
  if (!feeds.length) {
    return <div className="text-sm text-muted-foreground">No feeds available.</div>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {feeds.map((feed) => {
        const isSubscribed = subscriptionStatus?.get(feed.id) ?? false;

        return (
          <div key={feed.id} className="flex flex-col rounded-lg border border-border bg-card p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Radio className="h-4 w-4 text-primary" />
                <h3 className="text-base font-semibold">{feed.name}</h3>
              </div>
              <div className="flex items-center gap-2">
                {isSubscribed && (
                  <Badge variant="outline" className="text-green-600">
                    <Bell className="h-3 w-3 mr-1" />
                    Subscribed
                  </Badge>
                )}
                <Badge variant={feed.isActive ? 'default' : 'secondary'}>{feed.isActive ? 'Active' : 'Idle'}</Badge>
              </div>
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
            <div className="mt-4 flex gap-2">
              {onViewCalls && (
                <Button variant="outline" className="flex-1" onClick={() => onViewCalls(feed.id)}>
                  View calls
                </Button>
              )}
              {onSubscribe && onUnsubscribe && (
                isSubscribed ? (
                  <Button
                    variant="ghost"
                    className="flex-1"
                    onClick={() => onUnsubscribe(feed.id)}
                    disabled={isSubscribing}
                  >
                    <BellOff className="h-4 w-4 mr-2" />
                    Unsubscribe
                  </Button>
                ) : (
                  <Button
                    variant="default"
                    className="flex-1"
                    onClick={() => onSubscribe(feed.id)}
                    disabled={isSubscribing}
                  >
                    <Bell className="h-4 w-4 mr-2" />
                    Subscribe
                  </Button>
                )
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default FeedList;
