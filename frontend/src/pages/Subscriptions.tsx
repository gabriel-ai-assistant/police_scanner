import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Bell, BellOff, ChevronRight, Trash2 } from 'lucide-react';

import { listSubscriptions, updateSubscription, deleteSubscription } from '../api/subscriptions';
import ErrorState from '../components/ErrorState';
import LoadingScreen from '../components/LoadingScreen';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';

function Subscriptions() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const subscriptionsQuery = useQuery({
    queryKey: ['subscriptions'],
    queryFn: listSubscriptions,
    staleTime: 30 * 1000,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { notifications_enabled?: boolean } }) =>
      updateSubscription(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSubscription,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
    },
  });

  const handleToggleNotifications = (subscriptionId: string, currentValue: boolean) => {
    updateMutation.mutate({
      id: subscriptionId,
      data: { notifications_enabled: !currentValue },
    });
  };

  const handleUnsubscribe = (subscriptionId: string, playlistName?: string) => {
    if (confirm(`Unsubscribe from ${playlistName || 'this playlist'}?`)) {
      deleteMutation.mutate(subscriptionId);
    }
  };

  if (subscriptionsQuery.isLoading) {
    return <LoadingScreen />;
  }

  if (subscriptionsQuery.isError) {
    return <ErrorState onRetry={() => subscriptionsQuery.refetch()} />;
  }

  const subscriptions = subscriptionsQuery.data?.subscriptions ?? [];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>My Subscriptions</CardTitle>
            <CardDescription>
              Playlists you're subscribed to. Link keyword groups for notifications.
            </CardDescription>
          </div>
          <Button variant="outline" onClick={() => navigate('/feeds')}>
            Browse Feeds
          </Button>
        </CardHeader>
        <CardContent>
          {subscriptions.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-muted-foreground mb-4">
                You haven't subscribed to any playlists yet.
              </p>
              <Button onClick={() => navigate('/feeds')}>Browse Feeds</Button>
            </div>
          ) : (
            <div className="space-y-3">
              {subscriptions.map((sub) => (
                <div
                  key={sub.id}
                  className="flex items-center justify-between rounded-lg border border-border bg-card p-4 hover:bg-muted/40 transition-colors"
                >
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div
                      className="flex-1 min-w-0 cursor-pointer"
                      onClick={() => navigate(`/subscriptions/${sub.id}`)}
                    >
                      <h3 className="font-medium truncate">
                        {sub.playlistName || 'Unknown Playlist'}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="secondary" className="text-xs">
                          {sub.keywordGroupCount} keyword group{sub.keywordGroupCount !== 1 ? 's' : ''}
                        </Badge>
                        {sub.notificationsEnabled ? (
                          <Badge variant="outline" className="text-xs text-green-600">
                            <Bell className="h-3 w-3 mr-1" />
                            Notifications on
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-xs text-muted-foreground">
                            <BellOff className="h-3 w-3 mr-1" />
                            Muted
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">Notifications</span>
                      <Switch
                        checked={sub.notificationsEnabled}
                        onCheckedChange={() => handleToggleNotifications(sub.id, sub.notificationsEnabled)}
                        disabled={updateMutation.isPending}
                      />
                    </div>

                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={() => handleUnsubscribe(sub.id, sub.playlistName)}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>

                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => navigate(`/subscriptions/${sub.id}`)}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default Subscriptions;
