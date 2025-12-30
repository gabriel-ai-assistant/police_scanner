import { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { getFeeds } from '../api/feeds';
import { listSubscriptions, createSubscription, deleteSubscription } from '../api/subscriptions';
import { useRefreshInterval } from '../lib/useRefreshInterval';
import ErrorState from '../components/ErrorState';
import FeedList from '../components/FeedList';
import LoadingScreen from '../components/LoadingScreen';
import SearchBar from '../components/SearchBar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { useNavigate } from 'react-router-dom';

function Feeds() {
  const refreshInterval = useRefreshInterval();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState('');

  const feedsQuery = useQuery({
    queryKey: ['feeds'],
    queryFn: getFeeds,
    staleTime: 5 * 60 * 1000,
    refetchInterval: refreshInterval
  });

  const subscriptionsQuery = useQuery({
    queryKey: ['subscriptions'],
    queryFn: listSubscriptions,
    staleTime: 30 * 1000,
  });

  const subscribeMutation = useMutation({
    mutationFn: (playlistUuid: string) => createSubscription({ playlist_uuid: playlistUuid }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
    },
  });

  const unsubscribeMutation = useMutation({
    mutationFn: (subscriptionId: string) => deleteSubscription(subscriptionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
    },
  });

  // Build subscription status map (feed.id -> isSubscribed)
  const subscriptionStatus = useMemo(() => {
    const map = new Map<string, boolean>();
    const subs = subscriptionsQuery.data?.subscriptions ?? [];
    subs.forEach((sub) => {
      map.set(sub.playlistUuid, true);
    });
    return map;
  }, [subscriptionsQuery.data]);

  // Build subscriptionId lookup for unsubscribe
  const subscriptionIdMap = useMemo(() => {
    const map = new Map<string, string>();
    const subs = subscriptionsQuery.data?.subscriptions ?? [];
    subs.forEach((sub) => {
      map.set(sub.playlistUuid, sub.id);
    });
    return map;
  }, [subscriptionsQuery.data]);

  const handleSubscribe = (feedId: string) => {
    subscribeMutation.mutate(feedId);
  };

  const handleUnsubscribe = (feedId: string) => {
    const subscriptionId = subscriptionIdMap.get(feedId);
    if (subscriptionId) {
      unsubscribeMutation.mutate(subscriptionId);
    }
  };

  const filteredFeeds = useMemo(() => {
    const feeds = feedsQuery.data ?? [];
    if (!query) return feeds;
    const term = query.toLowerCase();
    return feeds.filter((feed) => feed.name.toLowerCase().includes(term) || feed.state.toLowerCase().includes(term));
  }, [feedsQuery.data, query]);

  if (feedsQuery.isLoading) {
    return <LoadingScreen />;
  }

  if (feedsQuery.isError) {
    return <ErrorState onRetry={() => feedsQuery.refetch()} />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Feeds</CardTitle>
          <CardDescription>Browse active Broadcastify feeds. Subscribe to receive keyword notifications.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <SearchBar defaultValue={query} onSearch={setQuery} />
          <FeedList
            feeds={filteredFeeds}
            onViewCalls={(feedId) => navigate(`/calls?feedId=${feedId}`)}
            subscriptionStatus={subscriptionStatus}
            onSubscribe={handleSubscribe}
            onUnsubscribe={handleUnsubscribe}
            isSubscribing={subscribeMutation.isPending || unsubscribeMutation.isPending}
          />
        </CardContent>
      </Card>
    </div>
  );
}

export default Feeds;
