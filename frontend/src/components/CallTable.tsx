import { Play } from 'lucide-react';

import type { Call } from '../types/call';
import { Badge } from './ui/badge';
import { Button } from './ui/button';

interface CallTableProps {
  calls: Call[];
  onSelect?: (callId: string) => void;
}

const priorityVariant: Record<Call['priority'], 'default' | 'secondary' | 'destructive'> = {
  low: 'secondary',
  medium: 'default',
  high: 'destructive'
};

function CallTable({ calls, onSelect }: CallTableProps) {
  if (!calls.length) {
    return <div className="text-sm text-muted-foreground">No calls to display.</div>;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <table className="min-w-full divide-y divide-border text-sm">
        <thead className="bg-muted/60 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-4 py-3 text-left font-semibold">Time</th>
            <th className="px-4 py-3 text-left font-semibold">Talkgroup</th>
            <th className="px-4 py-3 text-left font-semibold">Description</th>
            <th className="px-4 py-3 text-left font-semibold">Priority</th>
            <th className="px-4 py-3 text-left font-semibold">Duration</th>
            <th className="px-4 py-3 text-left font-semibold">Playback</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border bg-card">
          {calls.map((call) => (
            <tr key={call.id} className="hover:bg-muted/40">
              <td className="px-4 py-3 font-medium">{new Date(call.timestamp).toLocaleTimeString()}</td>
              <td className="px-4 py-3">{call.talkgroup}</td>
              <td className="px-4 py-3">{call.description}</td>
              <td className="px-4 py-3">
                <Badge variant={priorityVariant[call.priority]} className="capitalize">
                  {call.priority}
                </Badge>
              </td>
              <td className="px-4 py-3">{call.duration}s</td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <audio controls className="h-8">
                    <source src={call.audioUrl} type="audio/mpeg" />
                    Your browser does not support audio playback.
                  </audio>
                  {onSelect ? (
                    <Button variant="ghost" size="icon" onClick={() => onSelect(call.id)}>
                      <Play className="h-4 w-4" />
                    </Button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default CallTable;
