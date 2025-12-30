import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Radio, FileText, Headphones, Bell, ChevronRight, FolderOpen } from 'lucide-react';

import {
  getDashboardStats,
  getMyFeeds,
  getRecentActivity,
  getKeywordSummary,
} from '../api/dashboard';
import ActivityItem from '../components/ActivityItem';
import { useRefreshInterval } from '../lib/useRefreshInterval';
import ErrorState from '../components/ErrorState';
import LoadingScreen from '../components/LoadingScreen';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { formatDate } from '../lib/dates';

function Dashboard() {
  const navigate = useNavigate();
  const refreshInterval = useRefreshInterval();

  // User-scoped queries
  const statsQuery = useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: getDashboardStats,
    refetchInterval: refreshInterval,
  });

  const feedsQuery = useQuery({
    queryKey: ['dashboard', 'my-feeds'],
    queryFn: () => getMyFeeds(6),
    refetchInterval: refreshInterval,
  });

  const activityQuery = useQuery({
    queryKey: ['dashboard', 'recent-activity'],
    queryFn: () => getRecentActivity(10),
    refetchInterval: refreshInterval,
  });

  const keywordQuery = useQuery({
    queryKey: ['dashboard', 'keyword-summary'],
    queryFn: getKeywordSummary,
    staleTime: 10 * 60 * 1000,
  });

  const isLoading =
    statsQuery.isLoading ||
    feedsQuery.isLoading ||
    activityQuery.isLoading ||
    keywordQuery.isLoading;

  const isError =
    statsQuery.isError ||
    feedsQuery.isError ||
    activityQuery.isError ||
    keywordQuery.isError;

  const metricCards = useMemo(() => {
    const stats = statsQuery.data;
    return [
      {
        label: 'My Feeds',
        value: stats?.myFeeds ?? 0,
        helper: 'subscribed',
        icon: Radio,
      },
      {
        label: 'My Calls (1h)',
        value: stats?.myCalls1h ?? 0,
        helper: 'from subscribed feeds',
        icon: Headphones,
      },
      {
        label: 'My Transcripts (24h)',
        value: stats?.myTranscripts24h ?? 0,
        helper: 'from subscribed feeds',
        icon: FileText,
      },
    ];
  }, [statsQuery.data]);

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (isError) {
    return (
      <ErrorState
        onRetry={() => {
          statsQuery.refetch();
          feedsQuery.refetch();
          activityQuery.refetch();
          keywordQuery.refetch();
        }}
      />
    );
  }

  const feeds = feedsQuery.data?.feeds ?? [];
  const activities = activityQuery.data?.activities ?? [];
  const keywordSummary = keywordQuery.data;
  const hasSubscriptions = (statsQuery.data?.myFeeds ?? 0) > 0;

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {metricCards.map((card) => (
          <Card key={card.label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardDescription>{card.label}</CardDescription>
              <card.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{card.value}</div>
              <p className="text-xs text-muted-foreground">{card.helper}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* My Feeds */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>My Feeds</CardTitle>
              <CardDescription>Your subscribed Broadcastify feeds.</CardDescription>
            </div>
            {feeds.length > 0 && (
              <Button variant="outline" size="sm" onClick={() => navigate('/subscriptions')}>
                Manage
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {feeds.length === 0 ? (
              <div className="py-8 text-center">
                <Radio className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-4">No subscribed feeds yet.</p>
                <Button onClick={() => navigate('/feeds')}>Browse Feeds</Button>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {feeds.map((feed) => (
                  <div
                    key={feed.id}
                    className="flex flex-col rounded-lg border border-border bg-card p-4 shadow-sm cursor-pointer hover:bg-muted/40 transition-colors"
                    onClick={() => navigate('/subscriptions')}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Radio className="h-4 w-4 text-primary" />
                        <h3 className="text-base font-semibold truncate">{feed.name}</h3>
                      </div>
                      <Badge variant={feed.isActive ? 'default' : 'secondary'}>
                        {feed.isActive ? 'Active' : 'Idle'}
                      </Badge>
                    </div>
                    <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <dt className="text-muted-foreground">Listeners</dt>
                        <dd className="font-medium">{feed.listeners.toLocaleString()}</dd>
                      </div>
                      <div>
                        <dt className="text-muted-foreground">Updated</dt>
                        <dd className="font-medium">{feed.updatedAt ? formatDate(feed.updatedAt) : '—'}</dd>
                      </div>
                    </dl>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Keyword Groups Summary */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Keyword Groups</CardTitle>
              <CardDescription>Your configured keyword alerts.</CardDescription>
            </div>
            <Button variant="ghost" size="icon" onClick={() => navigate('/keyword-groups')}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent>
            {!keywordSummary || keywordSummary.groups.length === 0 ? (
              <div className="py-6 text-center">
                <FolderOpen className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
                <p className="text-sm text-muted-foreground mb-3">No keyword groups yet.</p>
                <Button variant="outline" size="sm" onClick={() => navigate('/keyword-groups')}>
                  Create Group
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {keywordSummary.groups.map((group) => (
                  <div
                    key={group.name}
                    className="flex items-center justify-between p-3 rounded-lg border border-border bg-muted/30"
                  >
                    <div className="flex items-center gap-2">
                      <Bell className={`h-4 w-4 ${group.isActive ? 'text-green-600' : 'text-muted-foreground'}`} />
                      <span className="font-medium">{group.name}</span>
                    </div>
                    <Badge variant="secondary">{group.keywordCount} keywords</Badge>
                  </div>
                ))}
                <div className="pt-2 text-center">
                  <p className="text-xs text-muted-foreground">
                    {keywordSummary.totalKeywords} total keywords configured
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">{keywordSummary.message}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest calls and transcripts from your subscribed feeds.</CardDescription>
          </div>
          {activities.length > 0 && (
            <Button variant="ghost" size="icon" onClick={() => navigate('/calls')}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {!hasSubscriptions ? (
            <div className="py-8 text-center">
              <Headphones className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">Subscribe to feeds to see activity here.</p>
              <Button onClick={() => navigate('/feeds')}>Browse Feeds</Button>
            </div>
          ) : activities.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-muted-foreground">No recent activity from your feeds.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {activities.map((activity) => (
                <ActivityItem key={activity.id} activity={activity} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default Dashboard;
