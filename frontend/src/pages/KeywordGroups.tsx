import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, Copy, FolderPlus, Link2, Plus, Trash2 } from 'lucide-react';

import {
  listKeywordGroups,
  listTemplates,
  createKeywordGroup,
  cloneTemplate,
  deleteKeywordGroup,
} from '../api/keywordGroups';
import ErrorState from '../components/ErrorState';
import LoadingScreen from '../components/LoadingScreen';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';

function KeywordGroups() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showCloneDialog, setShowCloneDialog] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDescription, setNewGroupDescription] = useState('');

  const groupsQuery = useQuery({
    queryKey: ['keyword-groups'],
    queryFn: () => listKeywordGroups(false),
    staleTime: 30 * 1000,
  });

  const templatesQuery = useQuery({
    queryKey: ['keyword-group-templates'],
    queryFn: listTemplates,
    staleTime: 5 * 60 * 1000,
  });

  const createMutation = useMutation({
    mutationFn: createKeywordGroup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keyword-groups'] });
      setShowCreateDialog(false);
      setNewGroupName('');
      setNewGroupDescription('');
    },
  });

  const cloneMutation = useMutation({
    mutationFn: cloneTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keyword-groups'] });
      setShowCloneDialog(false);
      setSelectedTemplateId('');
      setNewGroupName('');
      setNewGroupDescription('');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteKeywordGroup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keyword-groups'] });
    },
  });

  const handleCreate = () => {
    if (newGroupName.trim()) {
      createMutation.mutate({
        name: newGroupName.trim(),
        description: newGroupDescription.trim() || undefined,
      });
    }
  };

  const handleClone = () => {
    if (selectedTemplateId && newGroupName.trim()) {
      cloneMutation.mutate({
        template_id: selectedTemplateId,
        name: newGroupName.trim(),
        description: newGroupDescription.trim() || undefined,
      });
    }
  };

  const handleDelete = (groupId: string, groupName: string) => {
    if (confirm(`Delete "${groupName}"? This will also remove it from any subscriptions.`)) {
      deleteMutation.mutate(groupId);
    }
  };

  const openCloneDialog = (templateId: string, templateName: string) => {
    setSelectedTemplateId(templateId);
    setNewGroupName(`${templateName} (Copy)`);
    setNewGroupDescription('');
    setShowCloneDialog(true);
  };

  if (groupsQuery.isLoading) {
    return <LoadingScreen />;
  }

  if (groupsQuery.isError) {
    return <ErrorState onRetry={() => groupsQuery.refetch()} />;
  }

  const groups = groupsQuery.data?.groups ?? [];
  const templates = templatesQuery.data?.templates ?? [];

  return (
    <div className="space-y-6">
      {/* User's Keyword Groups */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Keyword Groups</CardTitle>
            <CardDescription>
              Create and manage keyword groups for notification filtering
            </CardDescription>
          </div>
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                New Group
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Keyword Group</DialogTitle>
                <DialogDescription>
                  Create a new group to organize keywords for notifications
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    placeholder="e.g., Home Streets, Work Area"
                    value={newGroupName}
                    onChange={(e) => setNewGroupName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description (optional)</Label>
                  <Input
                    id="description"
                    placeholder="e.g., Streets near my home address"
                    value={newGroupDescription}
                    onChange={(e) => setNewGroupDescription(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
                  Cancel
                </Button>
                <Button
                  onClick={handleCreate}
                  disabled={!newGroupName.trim() || createMutation.isPending}
                >
                  {createMutation.isPending ? 'Creating...' : 'Create'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          {groups.length === 0 ? (
            <div className="py-12 text-center">
              <FolderPlus className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">
                You haven't created any keyword groups yet.
              </p>
              <p className="text-sm text-muted-foreground mb-4">
                Start from scratch or clone a template below.
              </p>
              <Button onClick={() => setShowCreateDialog(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Your First Group
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {groups.map((group) => (
                <div
                  key={group.id}
                  className="flex items-center justify-between p-4 rounded-lg border border-border bg-card hover:bg-muted/40 transition-colors"
                >
                  <div
                    className="flex-1 cursor-pointer"
                    onClick={() => navigate(`/keyword-groups/${group.id}`)}
                  >
                    <h3 className="font-medium">{group.name}</h3>
                    {group.description && (
                      <p className="text-sm text-muted-foreground">{group.description}</p>
                    )}
                    <div className="flex items-center gap-2 mt-2">
                      <Badge variant="secondary">
                        {group.keywordCount} keyword{group.keywordCount !== 1 ? 's' : ''}
                      </Badge>
                      {group.subscriptionCount > 0 && (
                        <Badge variant="outline">
                          <Link2 className="h-3 w-3 mr-1" />
                          {group.subscriptionCount} subscription{group.subscriptionCount !== 1 ? 's' : ''}
                        </Badge>
                      )}
                      {!group.isActive && (
                        <Badge variant="destructive">Inactive</Badge>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={() => handleDelete(group.id, group.name)}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => navigate(`/keyword-groups/${group.id}`)}
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

      {/* Templates */}
      <Card>
        <CardHeader>
          <CardTitle>Templates</CardTitle>
          <CardDescription>
            Pre-made keyword groups you can clone and customize
          </CardDescription>
        </CardHeader>
        <CardContent>
          {templatesQuery.isLoading ? (
            <div className="text-center py-4 text-muted-foreground">Loading templates...</div>
          ) : templates.length === 0 ? (
            <div className="text-center py-4 text-muted-foreground">
              No templates available
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {templates.map((template) => (
                <div
                  key={template.id}
                  className="p-4 rounded-lg border border-border bg-muted/30"
                >
                  <h3 className="font-medium">{template.name}</h3>
                  {template.description && (
                    <p className="text-sm text-muted-foreground mt-1">{template.description}</p>
                  )}
                  <div className="flex items-center justify-between mt-3">
                    <Badge variant="secondary">
                      {template.keywordCount} keywords
                    </Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openCloneDialog(template.id, template.name)}
                    >
                      <Copy className="h-4 w-4 mr-2" />
                      Clone
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Clone Dialog */}
      <Dialog open={showCloneDialog} onOpenChange={setShowCloneDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clone Template</DialogTitle>
            <DialogDescription>
              Create a copy of the template that you can customize
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="clone-name">Name for your copy</Label>
              <Input
                id="clone-name"
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="clone-description">Description (optional)</Label>
              <Input
                id="clone-description"
                placeholder="Add a custom description"
                value={newGroupDescription}
                onChange={(e) => setNewGroupDescription(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCloneDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleClone}
              disabled={!newGroupName.trim() || cloneMutation.isPending}
            >
              {cloneMutation.isPending ? 'Cloning...' : 'Clone'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default KeywordGroups;
