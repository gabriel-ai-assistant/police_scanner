import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Bell, BellOff, Link2, Plus, Trash2, Unlink } from 'lucide-react';

import {
  getSubscription,
  updateSubscription,
  deleteSubscription,
  listLinkedKeywordGroups,
  linkKeywordGroup,
  unlinkKeywordGroup,
} from '../api/subscriptions';
import { listKeywordGroups } from '../api/keywordGroups';
import ErrorState from '../components/ErrorState';
import LoadingScreen from '../components/LoadingScreen';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { useState } from 'react';

function SubscriptionDetail() {
  const { id: subscriptionId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedGroupId, setSelectedGroupId] = useState<string>('');

  const subscriptionQuery = useQuery({
    queryKey: ['subscription', subscriptionId],
    queryFn: () => getSubscription(subscriptionId!),
    enabled: !!subscriptionId,
  });

  const linkedGroupsQuery = useQuery({
    queryKey: ['subscription-groups', subscriptionId],
    queryFn: () => listLinkedKeywordGroups(subscriptionId!),
    enabled: !!subscriptionId,
  });

  const userGroupsQuery = useQuery({
    queryKey: ['keyword-groups'],
    queryFn: () => listKeywordGroups(false),
  });

  const updateMutation = useMutation({
    mutationFn: (data: { notifications_enabled?: boolean }) =>
      updateSubscription(subscriptionId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscription', subscriptionId] });
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteSubscription(subscriptionId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
      navigate('/subscriptions');
    },
  });

  const linkMutation = useMutation({
    mutationFn: (groupId: string) =>
      linkKeywordGroup(subscriptionId!, { keyword_group_id: groupId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscription-groups', subscriptionId] });
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
      setSelectedGroupId('');
    },
  });

  const unlinkMutation = useMutation({
    mutationFn: (groupId: string) => unlinkKeywordGroup(subscriptionId!, groupId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscription-groups', subscriptionId] });
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
    },
  });

  const handleToggleNotifications = () => {
    if (subscriptionQuery.data) {
      updateMutation.mutate({
        notifications_enabled: !subscriptionQuery.data.notificationsEnabled,
      });
    }
  };

  const handleUnsubscribe = () => {
    if (confirm('Are you sure you want to unsubscribe? This will remove all keyword group links.')) {
      deleteMutation.mutate();
    }
  };

  const handleLinkGroup = () => {
    if (selectedGroupId) {
      linkMutation.mutate(selectedGroupId);
    }
  };

  const handleUnlinkGroup = (groupId: string, groupName: string) => {
    if (confirm(`Remove "${groupName}" from this subscription?`)) {
      unlinkMutation.mutate(groupId);
    }
  };

  if (subscriptionQuery.isLoading) {
    return <LoadingScreen />;
  }

  if (subscriptionQuery.isError) {
    return <ErrorState onRetry={() => subscriptionQuery.refetch()} />;
  }

  const subscription = subscriptionQuery.data;
  const linkedGroups = linkedGroupsQuery.data ?? [];
  const userGroups = userGroupsQuery.data?.groups ?? [];

  // Filter out already linked groups
  const linkedGroupIds = new Set(linkedGroups.map((g) => g.keywordGroupId));
  const availableGroups = userGroups.filter((g) => !linkedGroupIds.has(g.id) && !g.isTemplate);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/subscriptions')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">{subscription?.playlistName || 'Subscription'}</h1>
          <p className="text-muted-foreground">Manage notification settings and keyword groups</p>
        </div>
      </div>

      {/* Settings Card */}
      <Card>
        <CardHeader>
          <CardTitle>Subscription Settings</CardTitle>
          <CardDescription>
            {subscription?.playlistDescr || 'Configure notifications for this playlist'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg border border-border">
            <div className="flex items-center gap-3">
              {subscription?.notificationsEnabled ? (
                <Bell className="h-5 w-5 text-green-600" />
              ) : (
                <BellOff className="h-5 w-5 text-muted-foreground" />
              )}
              <div>
                <p className="font-medium">Notifications</p>
                <p className="text-sm text-muted-foreground">
                  {subscription?.notificationsEnabled
                    ? 'You will receive alerts for matching keywords'
                    : 'Notifications are muted for this subscription'}
                </p>
              </div>
            </div>
            <Switch
              checked={subscription?.notificationsEnabled}
              onCheckedChange={handleToggleNotifications}
              disabled={updateMutation.isPending}
            />
          </div>

          <div className="pt-4 border-t border-border">
            <Button
              variant="destructive"
              onClick={handleUnsubscribe}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Unsubscribe
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Keyword Groups Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5" />
            Linked Keyword Groups
          </CardTitle>
          <CardDescription>
            Keywords from these groups will trigger notifications for this playlist
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Link new group */}
          {availableGroups.length > 0 && (
            <div className="flex gap-2">
              <Select value={selectedGroupId} onValueChange={setSelectedGroupId}>
                <SelectTrigger className="flex-1">
                  <SelectValue placeholder="Select a keyword group to link..." />
                </SelectTrigger>
                <SelectContent>
                  {availableGroups.map((group) => (
                    <SelectItem key={group.id} value={group.id}>
                      {group.name} ({group.keywordCount} keywords)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                onClick={handleLinkGroup}
                disabled={!selectedGroupId || linkMutation.isPending}
              >
                <Plus className="h-4 w-4 mr-2" />
                Link
              </Button>
            </div>
          )}

          {userGroups.length === 0 && (
            <div className="text-center py-4">
              <p className="text-muted-foreground mb-2">
                You haven't created any keyword groups yet.
              </p>
              <Button variant="outline" onClick={() => navigate('/keyword-groups')}>
                Create Keyword Group
              </Button>
            </div>
          )}

          {/* Linked groups list */}
          {linkedGroupsQuery.isLoading ? (
            <div className="text-center py-4 text-muted-foreground">Loading...</div>
          ) : linkedGroups.length === 0 ? (
            <div className="text-center py-8 border border-dashed border-border rounded-lg">
              <p className="text-muted-foreground">
                No keyword groups linked. Link groups above to enable notifications.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {linkedGroups.map((link) => (
                <div
                  key={link.id}
                  className="flex items-center justify-between p-3 rounded-lg border border-border bg-muted/30"
                >
                  <div
                    className="flex-1 cursor-pointer"
                    onClick={() => navigate(`/keyword-groups/${link.keywordGroupId}`)}
                  >
                    <p className="font-medium">{link.keywordGroupName}</p>
                    <p className="text-sm text-muted-foreground">
                      {link.keywordCount} active keyword{link.keywordCount !== 1 ? 's' : ''}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive hover:bg-destructive/10"
                    onClick={() => handleUnlinkGroup(link.keywordGroupId, link.keywordGroupName)}
                    disabled={unlinkMutation.isPending}
                  >
                    <Unlink className="h-4 w-4 mr-2" />
                    Unlink
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default SubscriptionDetail;
