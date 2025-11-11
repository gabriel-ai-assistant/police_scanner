import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { getFeeds } from '../api/feeds';
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
  const [query, setQuery] = useState('');
  const feedsQuery = useQuery({ queryKey: ['feeds'], queryFn: getFeeds, staleTime: 5 * 60 * 1000, refetchInterval: refreshInterval });

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
          <CardDescription>Browse active Broadcastify feeds synced via the backend.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <SearchBar defaultValue={query} onSearch={setQuery} />
          <FeedList feeds={filteredFeeds} onViewCalls={(feedId) => navigate(`/calls?feedId=${feedId}`)} />
        </CardContent>
      </Card>
    </div>
  );
}

export default Feeds;
