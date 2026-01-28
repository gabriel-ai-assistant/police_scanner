// src/components/map/MapControls.tsx
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MapPin, Flame, Layers, Clock } from 'lucide-react';
import type { MapViewMode } from './LocationMap';

interface MapControlsProps {
  viewMode: MapViewMode;
  onViewModeChange: (mode: MapViewMode) => void;
  timeWindow: number;
  onTimeWindowChange: (hours: number) => void;
  totalLocations?: number;
  isLoading?: boolean;
}

const TIME_OPTIONS = [
  { label: '1h', value: 1 },
  { label: '6h', value: 6 },
  { label: '24h', value: 24 },
  { label: '7d', value: 168 },
  { label: '30d', value: 720 },
];

const VIEW_MODES: { mode: MapViewMode; icon: typeof MapPin; label: string }[] = [
  { mode: 'cluster', icon: Layers, label: 'Cluster' },
  { mode: 'pins', icon: MapPin, label: 'Pins' },
  { mode: 'heatmap', icon: Flame, label: 'Heat' },
];

export function MapControls({
  viewMode,
  onViewModeChange,
  timeWindow,
  onTimeWindowChange,
  totalLocations = 0,
  isLoading = false
}: MapControlsProps) {
  return (
    <Card className="absolute top-4 right-4 z-[1000] shadow-lg">
      <CardContent className="p-3 space-y-3">
        {/* View Mode Toggle */}
        <div>
          <div className="text-xs text-muted-foreground mb-1.5 flex items-center gap-1">
            <Layers className="h-3 w-3" />
            View
          </div>
          <div className="flex gap-1">
            {VIEW_MODES.map(({ mode, icon: Icon, label }) => (
              <Button
                key={mode}
                variant={viewMode === mode ? 'default' : 'outline'}
                size="sm"
                onClick={() => onViewModeChange(mode)}
                className="h-7 px-2 text-xs"
                title={label}
              >
                <Icon className="h-3.5 w-3.5 mr-1" />
                {label}
              </Button>
            ))}
          </div>
        </div>

        {/* Time Window */}
        <div>
          <div className="text-xs text-muted-foreground mb-1.5 flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Time Range
          </div>
          <div className="flex gap-1 flex-wrap">
            {TIME_OPTIONS.map(({ label, value }) => (
              <Button
                key={value}
                variant={timeWindow === value ? 'default' : 'outline'}
                size="sm"
                onClick={() => onTimeWindowChange(value)}
                className="h-6 px-2 text-xs"
              >
                {label}
              </Button>
            ))}
          </div>
        </div>

        {/* Stats */}
        <div className="text-xs text-muted-foreground border-t pt-2">
          {isLoading ? (
            <span className="animate-pulse">Loading...</span>
          ) : (
            <span>{totalLocations.toLocaleString()} locations</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default MapControls;
