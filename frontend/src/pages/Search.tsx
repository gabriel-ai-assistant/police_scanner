import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';

import { searchTranscripts } from '../api/transcripts';
import ErrorState from '../components/ErrorState';
import LoadingScreen from '../components/LoadingScreen';
import SearchBar from '../components/SearchBar';
import TranscriptViewer from '../components/TranscriptViewer';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';

function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get('q') ?? '';

  const transcriptsQuery = useQuery({
    queryKey: ['transcripts', { query }],
    queryFn: () => searchTranscripts(query),
    enabled: query.length > 0,
    staleTime: 60 * 1000
  });

  useEffect(() => {
    if (!query) {
      // no-op in React Query v4; if you previously used .remove(), just skip
    }
  }, [query]);

  const handleSearch = (value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) params.set('q', value);
    else params.delete('q');
    setSearchParams(params);
  };

  const showEmptyState = !query;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Search</CardTitle>
          <CardDescription>Search transcripts instantly via Meilisearch.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <SearchBar defaultValue={query} onSearch={handleSearch} />

          {showEmptyState ? (
            <div className="rounded-lg border border-border bg-muted/30 p-6 text-sm text-muted-foreground">
              Enter a keyword to search transcripts.
            </div>
          ) : transcriptsQuery.isLoading ? (
            <LoadingScreen />
          ) : transcriptsQuery.isError ? (
            <ErrorState onRetry={() => transcriptsQuery.refetch()} />
          ) : (
            <div className="space-y-4">
              {transcriptsQuery.data?.length ? (
                transcriptsQuery.data.map((transcript) => (
                  <Card key={transcript.id}>
                    <CardHeader>
                      <CardTitle className="text-base">Transcript {transcript.id}</CardTitle>
                      <CardDescription>
                        Processed {new Date(transcript.createdAt).toLocaleString()} — Call {transcript.callId}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <TranscriptViewer transcript={transcript} highlight={query} />
                    </CardContent>
                  </Card>
                ))
              ) : (
                <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
                  No transcripts matched “{query}”.
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default Search;
