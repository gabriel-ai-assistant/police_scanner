import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, Pause2, Play } from 'lucide-react';
import { Button } from '../ui/button';
import { Switch } from '../ui/switch';
import { getAllPlaylists, updatePlaylistSync, type Playlist } from '../../api/admin';

function PlaylistManager() {
  const [loading, setLoading] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState('');

  const playlistsQuery = useQuery({
    queryKey: ['admin', 'playlists'],
    queryFn: () => getAllPlaylists(),
    refetchInterval: 30000,
  });

  const handlePlaylistSync = async (playlist: Playlist) => {
    const key = `playlist-${playlist.uuid}`;
    setLoading(prev => new Set(prev).add(key));
    try {
      await updatePlaylistSync(playlist.uuid, !playlist.sync);
      playlistsQuery.refetch();
    } catch (e) {
      console.error('Failed to update playlist sync', e);
    } finally {
      setLoading(prev => {
        const newSet = new Set(prev);
        newSet.delete(key);
        return newSet;
      });
    }
  };

  const playlists = playlistsQuery.data || [];
  const filtered = playlists.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Search playlists..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 px-3 py-2 border rounded-md bg-background"
        />
        <Button
          variant="outline"
          onClick={() => playlistsQuery.refetch()}
          disabled={playlistsQuery.isLoading}
        >
          {playlistsQuery.isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Refresh'}
        </Button>
      </div>

      <div className="border rounded-md divide-y max-h-96 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground">No playlists found</div>
        ) : (
          filtered.map(playlist => (
            <div key={playlist.uuid} className="flex items-center justify-between p-4 hover:bg-muted transition-colors">
              <div className="flex-1">
                <h3 className="font-medium">{playlist.name}</h3>
                <div className="flex gap-4 text-sm text-muted-foreground">
                  <span>👥 {playlist.listeners ?? 0} listeners</span>
                  {playlist.descr && <span>{playlist.descr}</span>}
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Switch
                  checked={playlist.sync}
                  onCheckedChange={() => handlePlaylistSync(playlist)}
                  disabled={loading.has(`playlist-${playlist.uuid}`)}
                />
                {loading.has(`playlist-${playlist.uuid}`) && (
                  <Loader2 className="w-4 h-4 animate-spin" />
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="text-xs text-muted-foreground">
        Showing {filtered.length} of {playlists.length} playlists
      </div>
    </div>
  );
}

export default PlaylistManager;
