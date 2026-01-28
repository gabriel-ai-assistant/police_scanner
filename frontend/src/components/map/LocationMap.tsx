// src/components/map/LocationMap.tsx
import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import 'leaflet.markercluster';
import type { Location, HeatmapPoint } from '@/api/locations';

// Fix for default marker icons in Leaflet with bundlers
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';
import iconRetina from 'leaflet/dist/images/marker-icon-2x.png';

const DefaultIcon = L.icon({
  iconUrl: icon,
  iconRetinaUrl: iconRetina,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

L.Marker.prototype.options.icon = DefaultIcon;

export type MapViewMode = 'pins' | 'heatmap' | 'cluster';

interface LocationMapProps {
  locations?: Location[];
  heatmapPoints?: HeatmapPoint[];
  centerLat?: number;
  centerLon?: number;
  zoom?: number;
  viewMode?: MapViewMode;
  onLocationClick?: (location: Location) => void;
  onBoundsChange?: (bounds: { sw_lat: number; sw_lon: number; ne_lat: number; ne_lon: number }) => void;
  className?: string;
}

export function LocationMap({
  locations = [],
  heatmapPoints = [],
  centerLat = 33.2366,
  centerLon = -96.8009,
  zoom = 12,
  viewMode = 'cluster',
  onLocationClick,
  onBoundsChange,
  className = ''
}: LocationMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.MarkerClusterGroup | L.LayerGroup | null>(null);
  const heatLayerRef = useRef<any>(null);

  // Initialize map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = L.map(mapContainerRef.current).setView([centerLat, centerLon], zoom);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    // Track bounds changes
    map.on('moveend', () => {
      if (onBoundsChange) {
        const bounds = map.getBounds();
        onBoundsChange({
          sw_lat: bounds.getSouthWest().lat,
          sw_lon: bounds.getSouthWest().lng,
          ne_lat: bounds.getNorthEast().lat,
          ne_lon: bounds.getNorthEast().lng
        });
      }
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update center when props change
  useEffect(() => {
    if (mapRef.current && centerLat && centerLon) {
      mapRef.current.setView([centerLat, centerLon], zoom);
    }
  }, [centerLat, centerLon, zoom]);

  // Update markers/heatmap when data or view mode changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Clear existing layers
    if (markersLayerRef.current) {
      map.removeLayer(markersLayerRef.current);
      markersLayerRef.current = null;
    }
    if (heatLayerRef.current) {
      map.removeLayer(heatLayerRef.current);
      heatLayerRef.current = null;
    }

    if (viewMode === 'heatmap' && heatmapPoints.length > 0) {
      // Create heatmap layer
      const heatData = heatmapPoints.map(p => [p.lat, p.lon, p.count] as [number, number, number]);

      // Dynamic import for leaflet.heat (it modifies L globally)
      import('leaflet.heat').then(() => {
        // @ts-ignore - leaflet.heat adds this to L
        const heat = L.heatLayer(heatData, {
          radius: 25,
          blur: 15,
          maxZoom: 17,
          max: Math.max(...heatmapPoints.map(p => p.count), 1),
          gradient: {
            0.0: 'blue',
            0.25: 'cyan',
            0.5: 'lime',
            0.75: 'yellow',
            1.0: 'red'
          }
        }).addTo(map);
        heatLayerRef.current = heat;
      });
    } else if (viewMode === 'cluster' && locations.length > 0) {
      // Create clustered markers
      // @ts-ignore - markercluster types
      const markers = L.markerClusterGroup({
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        maxClusterRadius: 50
      });

      locations.forEach(loc => {
        if (loc.latitude && loc.longitude) {
          const marker = L.marker([loc.latitude, loc.longitude]);
          marker.bindPopup(createPopupContent(loc));
          marker.on('click', () => {
            if (onLocationClick) onLocationClick(loc);
          });
          markers.addLayer(marker);
        }
      });

      map.addLayer(markers);
      markersLayerRef.current = markers;
    } else if (viewMode === 'pins' && locations.length > 0) {
      // Create individual markers
      const layerGroup = L.layerGroup();

      locations.forEach(loc => {
        if (loc.latitude && loc.longitude) {
          const marker = L.marker([loc.latitude, loc.longitude]);
          marker.bindPopup(createPopupContent(loc));
          marker.on('click', () => {
            if (onLocationClick) onLocationClick(loc);
          });
          layerGroup.addLayer(marker);
        }
      });

      layerGroup.addTo(map);
      markersLayerRef.current = layerGroup;
    }
  }, [locations, heatmapPoints, viewMode, onLocationClick]);

  return (
    <div
      ref={mapContainerRef}
      className={`w-full h-full min-h-[400px] ${className}`}
      style={{ zIndex: 0 }}
    />
  );
}

function createPopupContent(location: Location): string {
  const lines = [
    `<div class="location-popup">`,
    `<strong>${escapeHtml(location.raw_location_text)}</strong>`,
  ];

  if (location.formatted_address) {
    lines.push(`<br/><small>${escapeHtml(location.formatted_address)}</small>`);
  }

  if (location.location_type) {
    lines.push(`<br/><span class="text-xs text-gray-500">Type: ${escapeHtml(location.location_type)}</span>`);
  }

  if (location.playlist_name) {
    lines.push(`<br/><span class="text-xs text-blue-600">Feed: ${escapeHtml(location.playlist_name)}</span>`);
  }

  if (location.transcript_text) {
    const excerpt = location.transcript_text.slice(0, 100) + (location.transcript_text.length > 100 ? '...' : '');
    lines.push(`<hr class="my-1"/><small class="text-gray-600">"${escapeHtml(excerpt)}"</small>`);
  }

  if (location.created_at) {
    const date = new Date(location.created_at);
    lines.push(`<br/><span class="text-xs text-gray-400">${date.toLocaleString()}</span>`);
  }

  lines.push(`</div>`);
  return lines.join('');
}

function escapeHtml(str: string): string {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

export default LocationMap;
