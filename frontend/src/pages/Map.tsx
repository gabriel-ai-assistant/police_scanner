// src/pages/Map.tsx
import { useState, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getLocations, getHeatmap, getLocationStats } from '@/api/locations';
import type { Location, HeatmapPoint } from '@/api/locations';
import { LocationMap, MapControls, LocationPopup } from '@/components/map';
import type { MapViewMode } from '@/components/map';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MapPin, Activity, Radio, Building2 } from 'lucide-react';

export default function Map() {
  const [viewMode, setViewMode] = useState<MapViewMode>('cluster');
  const [timeWindow, setTimeWindow] = useState(24);
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null);
  const [bounds, setBounds] = useState<{
    sw_lat: number;
    sw_lon: number;
    ne_lat: number;
    ne_lon: number;
  } | null>(null);

  // Fetch locations for pins/cluster view
  const { data: locationsData, isLoading: locationsLoading } = useQuery({
    queryKey: ['locations', timeWindow, bounds],
    queryFn: () => getLocations({
      hours: timeWindow,
      limit: 1000,
      bbox: bounds ? `${bounds.sw_lat},${bounds.sw_lon},${bounds.ne_lat},${bounds.ne_lon}` : undefined
    }),
    enabled: viewMode !== 'heatmap',
    staleTime: 30000, // 30 seconds
  });

  // Fetch heatmap data
  const { data: heatmapData, isLoading: heatmapLoading } = useQuery({
    queryKey: ['heatmap', timeWindow],
    queryFn: () => getHeatmap({ hours: timeWindow }),
    enabled: viewMode === 'heatmap',
    staleTime: 30000,
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['locationStats', timeWindow],
    queryFn: () => getLocationStats({ hours: timeWindow }),
    staleTime: 60000, // 1 minute
  });

  const handleBoundsChange = useCallback((newBounds: typeof bounds) => {
    setBounds(newBounds);
  }, []);

  const handleLocationClick = useCallback((location: Location) => {
    setSelectedLocation(location);
  }, []);

  // Determine center point
  const centerLat = heatmapData?.center_lat ?? locationsData?.items?.[0]?.latitude ?? 33.2366;
  const centerLon = heatmapData?.center_lon ?? locationsData?.items?.[0]?.longitude ?? -96.8009;

  const isLoading = viewMode === 'heatmap' ? heatmapLoading : locationsLoading;
  const totalLocations = viewMode === 'heatmap'
    ? (heatmapData?.total_locations ?? 0)
    : (locationsData?.total ?? 0);

  return (
    <div className="h-full flex flex-col -m-6">
      {/* Stats Cards */}
      <div className="p-4 pb-0 grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <MapPin className="h-8 w-8 text-red-500" />
            <div>
              <p className="text-2xl font-bold">{stats?.total_locations ?? 0}</p>
              <p className="text-xs text-muted-foreground">Total Locations</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <Activity className="h-8 w-8 text-green-500" />
            <div>
              <p className="text-2xl font-bold">{stats?.geocoded ?? 0}</p>
              <p className="text-xs text-muted-foreground">Geocoded</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <Radio className="h-8 w-8 text-blue-500" />
            <div>
              <p className="text-2xl font-bold">{stats?.unique_feeds ?? 0}</p>
              <p className="text-xs text-muted-foreground">Active Feeds</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <Building2 className="h-8 w-8 text-purple-500" />
            <div>
              <p className="text-2xl font-bold">{stats?.unique_cities ?? 0}</p>
              <p className="text-xs text-muted-foreground">Cities</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Map Container */}
      <div className="flex-1 relative p-4">
        <div className="w-full h-full rounded-lg overflow-hidden border shadow-sm">
          <LocationMap
            locations={locationsData?.items ?? []}
            heatmapPoints={heatmapData?.points ?? []}
            centerLat={centerLat}
            centerLon={centerLon}
            viewMode={viewMode}
            onLocationClick={handleLocationClick}
            onBoundsChange={handleBoundsChange}
          />

          {/* Controls Overlay */}
          <MapControls
            viewMode={viewMode}
            onViewModeChange={setViewMode}
            timeWindow={timeWindow}
            onTimeWindowChange={setTimeWindow}
            totalLocations={totalLocations}
            isLoading={isLoading}
          />

          {/* Selected Location Popup */}
          <LocationPopup
            location={selectedLocation}
            onClose={() => setSelectedLocation(null)}
          />
        </div>
      </div>
    </div>
  );
}
