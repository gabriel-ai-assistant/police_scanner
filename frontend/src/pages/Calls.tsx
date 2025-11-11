import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';

import { getCalls } from '../api/calls';
import { useRefreshInterval } from '../lib/useRefreshInterval';
import { getFeeds } from '../api/feeds';
import CallTable from '../components/CallTable';
import ErrorState from '../components/ErrorState';
import LoadingScreen from '../components/LoadingScreen';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';

function Calls() {
  const refreshInterval = useRefreshInterval();
  const [searchParams, setSearchParams] = useSearchParams();
  const feedId = searchParams.get('feedId') ?? '';
  const searchTerm = searchParams.get('q') ?? '';

  const feedsQuery = useQuery({ queryKey: ['feeds'], queryFn: getFeeds, staleTime: 5 * 60 * 1000, refetchInterval: refreshInterval });
  const callsQuery = useQuery({ queryKey: ['calls', feedId], queryFn: () => getCalls(feedId ? { feedId } : undefined), refetchInterval: refreshInterval });

  const filteredCalls = useMemo(() => {
    const calls = callsQuery.data ?? [];
    if (!searchTerm) return calls;
    const term = searchTerm.toLowerCase();
    return calls.filter((call) => call.description.toLowerCase().includes(term) || call.talkgroup.toLowerCase().includes(term));
  }, [callsQuery.data, searchTerm]);

  const handleSearch = (value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set('q', value);
    } else {
      params.delete('q');
    }
    setSearchParams(params);
  };

  const handleFeedChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set('feedId', value);
    } else {
      params.delete('feedId');
    }
    setSearchParams(params);
  };

  if (callsQuery.isLoading) {
    return <LoadingScreen />;
  }

  if (callsQuery.isError) {
    return <ErrorState onRetry={() => callsQuery.refetch()} />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Calls</CardTitle>
          <CardDescription>Monitor and play back recent calls synced from Broadcastify.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <div className="flex flex-1 flex-col gap-2">
              <label className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Filter by feed</label>
              <select
                value={feedId}
                onChange={handleFeedChange}
                className="h-10 rounded-md border border-border bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="">All feeds</option>
                {(feedsQuery.data ?? []).map((feed) => (
                  <option key={feed.id} value={feed.id}>
                    {feed.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-1 flex-col gap-2">
              <label className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Search calls</label>
              <Input
                value={searchTerm}
                onChange={(event) => handleSearch(event.target.value)}
                placeholder="Search by talkgroup or description"
              />
            </div>
          </div>
          <CallTable calls={filteredCalls} />
        </CardContent>
      </Card>
    </div>
  );
}

export default Calls;
