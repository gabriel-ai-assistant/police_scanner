import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

import { getDashboardMetrics, getKeywordHits } from '../api/analytics';
import { getCalls } from '../api/calls';
import { getFeeds } from '../api/feeds';
import { searchTranscripts } from '../api/transcripts';
import CallTable from '../components/CallTable';
import { useRefreshInterval } from '../lib/useRefreshInterval';
import ErrorState from '../components/ErrorState';
import FeedList from '../components/FeedList';
import LoadingScreen from '../components/LoadingScreen';
import TranscriptViewer from '../components/TranscriptViewer';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';

function Dashboard() {
  const refreshInterval = useRefreshInterval();
  const metricsQuery = useQuery({ queryKey: ['dashboard', 'metrics'], queryFn: getDashboardMetrics, refetchInterval: refreshInterval });
  const feedsQuery = useQuery({ queryKey: ['feeds'], queryFn: getFeeds, refetchInterval: refreshInterval });
  const callsQuery = useQuery({ queryKey: ['calls', { limit: 5 }], queryFn: () => getCalls(), refetchInterval: refreshInterval });
  const transcriptsQuery = useQuery({ queryKey: ['transcripts', 'recent'], queryFn: () => searchTranscripts(''), staleTime: 5 * 60 * 1000, refetchInterval: refreshInterval * 2 });
  const keywordQuery = useQuery({ queryKey: ['keyword-hits'], queryFn: getKeywordHits, staleTime: 10 * 60 * 1000 });

  const isLoading = metricsQuery.isLoading || feedsQuery.isLoading || callsQuery.isLoading || transcriptsQuery.isLoading || keywordQuery.isLoading;
  const isError = metricsQuery.isError || feedsQuery.isError || callsQuery.isError || transcriptsQuery.isError || keywordQuery.isError;

  const metricCards = useMemo(() => {
    const metrics = metricsQuery.data;
    return [
      {
        label: 'Total Feeds',
        value: metrics?.feedCount ?? 0,
        helper: metrics ? `${metrics.activeFeeds} active` : '—'
      },
      {
        label: 'Recent Calls (1h)',
        value: metrics?.recentCalls ?? 0,
        helper: 'monitored'
      },
      {
        label: 'Transcripts Today',
        value: metrics?.transcriptsToday ?? 0,
        helper: 'processed'
      }
    ];
  }, [metricsQuery.data]);

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (isError) {
    return <ErrorState onRetry={() => {
      metricsQuery.refetch();
      feedsQuery.refetch();
      callsQuery.refetch();
      transcriptsQuery.refetch();
      keywordQuery.refetch();
    }} />;
  }

  const feeds = feedsQuery.data ?? [];
  const calls = callsQuery.data?.slice(0, 5) ?? [];
  const transcripts = transcriptsQuery.data?.slice(0, 2) ?? [];
  const keywordHits = keywordQuery.data ?? [];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {metricCards.map((card) => (
          <Card key={card.label}>
            <CardHeader>
              <CardDescription>{card.label}</CardDescription>
              <CardTitle className="text-3xl font-bold">{card.value}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{card.helper}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Active Feeds</CardTitle>
            <CardDescription>Feeds currently monitored from Broadcastify.</CardDescription>
          </CardHeader>
          <CardContent>
            <FeedList feeds={feeds.slice(0, 6)} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Keyword Hits (24h)</CardTitle>
            <CardDescription>Occurrences of configured alerts.</CardDescription>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={keywordHits}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="keyword" stroke="hsl(var(--muted-foreground))" tickLine={false} axisLine={false} />
                <YAxis stroke="hsl(var(--muted-foreground))" allowDecimals={false} tickLine={false} axisLine={false} />
                <Tooltip
                  cursor={{ fill: 'hsl(var(--accent) / 0.2)' }}
                  contentStyle={{ backgroundColor: 'hsl(var(--background))', borderRadius: 8, border: '1px solid hsl(var(--border))' }}
                />
                <Bar dataKey="hits" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Calls</CardTitle>
            <CardDescription>Latest dispatch activity across active feeds.</CardDescription>
          </CardHeader>
          <CardContent>
            <CallTable calls={calls} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Recent Transcripts</CardTitle>
            <CardDescription>Whisper transcripts with highlighted keywords.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {transcripts.map((transcript) => (
              <TranscriptViewer key={transcript.id} transcript={transcript} />
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default Dashboard;
