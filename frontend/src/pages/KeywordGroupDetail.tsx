import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, FileUp, Link2, Plus, Trash2, ToggleLeft, ToggleRight } from 'lucide-react';

import {
  getKeywordGroup,
  updateKeywordGroup,
  deleteKeywordGroup,
  createKeyword,
  updateKeyword,
  deleteKeyword,
  bulkImportKeywords,
} from '../api/keywordGroups';
import { MATCH_TYPES, type MatchType } from '../types/keywordGroup';
import ErrorState from '../components/ErrorState';
import LoadingScreen from '../components/LoadingScreen';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

function KeywordGroupDetail() {
  const { id: groupId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [showAddKeyword, setShowAddKeyword] = useState(false);
  const [showBulkImport, setShowBulkImport] = useState(false);
  const [newKeyword, setNewKeyword] = useState('');
  const [newMatchType, setNewMatchType] = useState<MatchType>('substring');
  const [bulkKeywords, setBulkKeywords] = useState('');
  const [bulkMatchType, setBulkMatchType] = useState<MatchType>('substring');

  const groupQuery = useQuery({
    queryKey: ['keyword-group', groupId],
    queryFn: () => getKeywordGroup(groupId!),
    enabled: !!groupId,
  });

  const updateGroupMutation = useMutation({
    mutationFn: (data: { name?: string; description?: string; is_active?: boolean }) =>
      updateKeywordGroup(groupId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keyword-group', groupId] });
      queryClient.invalidateQueries({ queryKey: ['keyword-groups'] });
    },
    onError: (error: Error) => {
      alert(`Failed to update group: ${error.message}`);
    },
  });

  const deleteGroupMutation = useMutation({
    mutationFn: () => deleteKeywordGroup(groupId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keyword-groups'] });
      navigate('/keyword-groups');
    },
    onError: (error: Error) => {
      alert(`Failed to delete group: ${error.message}`);
    },
  });

  const createKeywordMutation = useMutation({
    mutationFn: (data: { keyword: string; match_type?: MatchType }) =>
      createKeyword(groupId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keyword-group', groupId] });
      queryClient.invalidateQueries({ queryKey: ['keyword-groups'] });
      setNewKeyword('');
      setShowAddKeyword(false);
    },
    onError: (error: Error) => {
      alert(`Failed to add keyword: ${error.message}`);
    },
  });

  const updateKeywordMutation = useMutation({
    mutationFn: ({ keywordId, data }: { keywordId: string; data: { is_active?: boolean } }) =>
      updateKeyword(groupId!, keywordId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keyword-group', groupId] });
    },
    onError: (error: Error) => {
      alert(`Failed to update keyword: ${error.message}`);
    },
  });

  const deleteKeywordMutation = useMutation({
    mutationFn: (keywordId: string) => deleteKeyword(groupId!, keywordId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keyword-group', groupId] });
      queryClient.invalidateQueries({ queryKey: ['keyword-groups'] });
    },
    onError: (error: Error) => {
      alert(`Failed to delete keyword: ${error.message}`);
    },
  });

  const bulkImportMutation = useMutation({
    mutationFn: (data: { keywords: string; match_type?: MatchType }) =>
      bulkImportKeywords(groupId!, data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['keyword-group', groupId] });
      queryClient.invalidateQueries({ queryKey: ['keyword-groups'] });
      setBulkKeywords('');
      setShowBulkImport(false);
      alert(`Imported ${result.imported} keywords. Skipped ${result.skipped} duplicates.${result.errors.length ? '\nErrors: ' + result.errors.join(', ') : ''}`);
    },
    onError: (error: Error) => {
      alert(`Failed to import keywords: ${error.message}`);
    },
  });

  const handleAddKeyword = () => {
    if (newKeyword.trim()) {
      createKeywordMutation.mutate({
        keyword: newKeyword.trim(),
        match_type: newMatchType,
      });
    }
  };

  const handleBulkImport = () => {
    if (bulkKeywords.trim()) {
      bulkImportMutation.mutate({
        keywords: bulkKeywords,
        match_type: bulkMatchType,
      });
    }
  };

  const handleToggleKeyword = (keywordId: string, currentActive: boolean) => {
    updateKeywordMutation.mutate({
      keywordId,
      data: { is_active: !currentActive },
    });
  };

  const handleDeleteKeyword = (keywordId: string, keyword: string) => {
    if (confirm(`Delete "${keyword}"?`)) {
      deleteKeywordMutation.mutate(keywordId);
    }
  };

  const handleDeleteGroup = () => {
    if (confirm('Delete this keyword group? This will also remove it from any subscriptions.')) {
      deleteGroupMutation.mutate();
    }
  };

  const handleToggleGroupActive = () => {
    if (groupQuery.data) {
      updateGroupMutation.mutate({ is_active: !groupQuery.data.isActive });
    }
  };

  if (groupQuery.isLoading) {
    return <LoadingScreen />;
  }

  if (groupQuery.isError) {
    return <ErrorState onRetry={() => groupQuery.refetch()} />;
  }

  const group = groupQuery.data;
  const isTemplate = group?.isTemplate;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/keyword-groups')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">{group?.name}</h1>
            {isTemplate && <Badge variant="secondary">Template</Badge>}
            {!group?.isActive && <Badge variant="destructive">Inactive</Badge>}
          </div>
          {group?.description && (
            <p className="text-muted-foreground">{group.description}</p>
          )}
        </div>
      </div>

      {/* Group Settings (only for non-templates) */}
      {!isTemplate && (
        <Card>
          <CardHeader>
            <CardTitle>Group Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-lg border border-border">
              <div className="flex items-center gap-3">
                {group?.isActive ? (
                  <ToggleRight className="h-5 w-5 text-green-600" />
                ) : (
                  <ToggleLeft className="h-5 w-5 text-muted-foreground" />
                )}
                <div>
                  <p className="font-medium">Active</p>
                  <p className="text-sm text-muted-foreground">
                    {group?.isActive
                      ? 'Keywords in this group will be matched'
                      : 'This group is disabled and will not match'}
                  </p>
                </div>
              </div>
              <Switch
                checked={group?.isActive}
                onCheckedChange={handleToggleGroupActive}
                disabled={updateGroupMutation.isPending}
              />
            </div>

            <div className="pt-4 border-t border-border">
              <Button
                variant="destructive"
                onClick={handleDeleteGroup}
                disabled={deleteGroupMutation.isPending}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Group
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Linked Subscriptions */}
      {!isTemplate && group?.linkedSubscriptions && group.linkedSubscriptions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Link2 className="h-5 w-5" />
              Linked Subscriptions
            </CardTitle>
            <CardDescription>
              This keyword group is used by these subscriptions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {group.linkedSubscriptions.map((sub) => (
                <div
                  key={sub.subscriptionId}
                  className="flex items-center justify-between p-3 rounded-lg border border-border bg-muted/30 cursor-pointer hover:bg-muted/50"
                  onClick={() => navigate(`/subscriptions/${sub.subscriptionId}`)}
                >
                  <span className="font-medium">{sub.playlistName || 'Unknown Playlist'}</span>
                  <Badge variant="outline">View</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Keywords */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Keywords ({group?.keywords?.length || 0})</CardTitle>
            <CardDescription>
              {isTemplate
                ? 'Keywords in this template'
                : 'Add and manage keywords for this group'}
            </CardDescription>
          </div>
          {!isTemplate && (
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setShowBulkImport(true)}>
                <FileUp className="h-4 w-4 mr-2" />
                Bulk Import
              </Button>
              <Button onClick={() => setShowAddKeyword(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Keyword
              </Button>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {group?.keywords?.length === 0 ? (
            <div className="py-8 text-center border border-dashed border-border rounded-lg">
              <p className="text-muted-foreground">
                No keywords yet. Add some to get started.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {group?.keywords?.map((kw) => (
                <div
                  key={kw.id}
                  className={`flex items-center justify-between p-3 rounded-lg border ${
                    kw.isActive
                      ? 'border-border bg-card'
                      : 'border-muted bg-muted/30 opacity-60'
                  }`}
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <span className={`font-mono ${!kw.isActive ? 'line-through' : ''}`}>
                      {kw.keyword}
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {MATCH_TYPES.find((m) => m.value === kw.matchType)?.label || kw.matchType}
                    </Badge>
                  </div>

                  {!isTemplate && (
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={kw.isActive}
                        onCheckedChange={() => handleToggleKeyword(kw.id, kw.isActive)}
                        disabled={updateKeywordMutation.isPending}
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={() => handleDeleteKeyword(kw.id, kw.keyword)}
                        disabled={deleteKeywordMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add Keyword Dialog */}
      <Dialog open={showAddKeyword} onOpenChange={setShowAddKeyword}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Keyword</DialogTitle>
            <DialogDescription>
              Add a new keyword to this group
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="keyword">Keyword</Label>
              <Input
                id="keyword"
                placeholder="e.g., Main Street, 10-33"
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="match-type">Match Type</Label>
              <Select value={newMatchType} onValueChange={(v) => setNewMatchType(v as MatchType)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MATCH_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label} - {type.description}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddKeyword(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAddKeyword}
              disabled={!newKeyword.trim() || createKeywordMutation.isPending}
            >
              {createKeywordMutation.isPending ? 'Adding...' : 'Add Keyword'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Import Dialog */}
      <Dialog open={showBulkImport} onOpenChange={setShowBulkImport}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bulk Import Keywords</DialogTitle>
            <DialogDescription>
              Paste keywords separated by new lines (max 500)
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="bulk-keywords">Keywords (one per line)</Label>
              <textarea
                id="bulk-keywords"
                className="w-full h-40 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder={`Main Street
Oak Avenue
10-33
Structure fire`}
                value={bulkKeywords}
                onChange={(e) => setBulkKeywords(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="bulk-match-type">Match Type (for all)</Label>
              <Select value={bulkMatchType} onValueChange={(v) => setBulkMatchType(v as MatchType)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MATCH_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <p className="text-sm text-muted-foreground">
              {bulkKeywords.split('\n').filter((l) => l.trim()).length} keywords to import
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBulkImport(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleBulkImport}
              disabled={!bulkKeywords.trim() || bulkImportMutation.isPending}
            >
              {bulkImportMutation.isPending ? 'Importing...' : 'Import'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default KeywordGroupDetail;
