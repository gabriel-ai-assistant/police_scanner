import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getProcessingState, getSystemStatus } from '../../api/admin';
import { Card, CardContent } from '../ui/card';

function ProcessingPipeline() {
  const processingQuery = useQuery({
    queryKey: ['admin', 'processing-state'],
    queryFn: () => getProcessingState(),
    refetchInterval: 10000,
  });

  const statusQuery = useQuery({
    queryKey: ['admin', 'system-status'],
    queryFn: () => getSystemStatus(),
    refetchInterval: 30000,
  });

  const state = processingQuery.data;
  const status = statusQuery.data;

  if (!state) {
    return <div className="text-center text-muted-foreground">Loading...</div>;
  }

  const chartData = [
    { name: 'Queued', value: state.queued },
    { name: 'Downloaded', value: state.downloaded },
    { name: 'Transcribed', value: state.transcribed },
    { name: 'Indexed', value: state.indexed },
    { name: 'Error', value: state.error },
  ];

  const completionRate = state.total > 0 ? Math.round(((state.transcribed + state.indexed) / state.total) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Status Overview */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">{state.queued}</div>
            <p className="text-xs text-muted-foreground">Queued</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">{state.downloaded}</div>
            <p className="text-xs text-muted-foreground">Downloaded</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">{state.transcribed}</div>
            <p className="text-xs text-muted-foreground">Transcribed</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">{state.indexed}</div>
            <p className="text-xs text-muted-foreground">Indexed</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-red-500">{state.error}</div>
            <p className="text-xs text-muted-foreground">Errors</p>
          </CardContent>
        </Card>
      </div>

      {/* Completion Rate */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm font-medium">Completion Rate</span>
              <span className="text-sm font-bold">{completionRate}%</span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div
                className="bg-primary h-2 rounded-full transition-all duration-500"
                style={{ width: `${completionRate}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              {state.transcribed + state.indexed} of {state.total} calls processed
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Pipeline Chart */}
      <Card>
        <CardContent className="pt-6">
          <h3 className="font-medium mb-4">Pipeline Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip
                cursor={{ fill: 'hsl(var(--accent) / 0.2)' }}
                contentStyle={{ backgroundColor: 'hsl(var(--background))', borderRadius: 8, border: '1px solid hsl(var(--border))' }}
              />
              <Bar dataKey="value" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* System Stats */}
      {status && (
        <Card>
          <CardContent className="pt-6">
            <h3 className="font-medium mb-4">System Statistics</h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Total Calls</p>
                <p className="text-2xl font-bold">{status.calls_total || 0}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Transcribed</p>
                <p className="text-2xl font-bold">{status.transcripts_total || 0}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Active Playlists</p>
                <p className="text-2xl font-bold">{status.active_playlists || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default ProcessingPipeline;
