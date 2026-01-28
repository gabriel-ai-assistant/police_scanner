// src/api/locations.ts
import { api } from '@/lib/api';

export type Location = {
  id: string;
  source_type: string;
  source_id: string;
  raw_location_text: string;
  location_type?: string;
  latitude?: number;
  longitude?: number;
  geocode_confidence?: number;
  geocode_source?: string;
  street_name?: string;
  street_number?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  formatted_address?: string;
  playlist_uuid?: string;
  county_id?: number;
  geocoded_at?: string;
  created_at: string;
  updated_at?: string;
  // Context fields
  playlist_name?: string;
  county_name?: string;
  county_state?: string;
  transcript_text?: string;
  transcript_created_at?: string;
};

export type HeatmapPoint = {
  lat: number;
  lon: number;
  count: number;
  most_recent?: string;
};

export type LocationListResponse = {
  items: Location[];
  total: number;
  limit: number;
  offset: number;
};

export type HeatmapResponse = {
  points: HeatmapPoint[];
  total_locations: number;
  time_window_hours: number;
  center_lat?: number;
  center_lon?: number;
};

export type LocationStats = {
  total_locations: number;
  geocoded: number;
  unique_transcripts: number;
  unique_feeds: number;
  unique_cities: number;
  time_range: {
    oldest?: string;
    newest?: string;
  };
  time_window_hours: number;
};

export type LocationsQueryParams = {
  feed_id?: string;
  bbox?: string;
  since?: string;
  hours?: number;
  limit?: number;
  offset?: number;
};

export type HeatmapQueryParams = {
  feed_id?: string;
  hours?: number;
  grid_precision?: number;
};

const isMock = import.meta.env.VITE_MOCK === '1';

// Mock data for development
const mockLocations: Location[] = [
  {
    id: '1',
    source_type: 'transcript',
    source_id: 'call-1',
    raw_location_text: '123 Main Street',
    location_type: 'address',
    latitude: 33.2366,
    longitude: -96.8009,
    geocode_confidence: 0.9,
    city: 'Prosper',
    state: 'TX',
    formatted_address: '123 Main Street, Prosper, TX 75078',
    created_at: new Date().toISOString(),
    playlist_name: 'Prosper PD',
    transcript_text: 'Unit 12 responding to 123 Main Street.'
  },
  {
    id: '2',
    source_type: 'transcript',
    source_id: 'call-2',
    raw_location_text: '5th and Broadway',
    location_type: 'intersection',
    latitude: 33.2400,
    longitude: -96.7950,
    geocode_confidence: 0.85,
    city: 'Prosper',
    state: 'TX',
    formatted_address: '5th St & Broadway, Prosper, TX',
    created_at: new Date().toISOString(),
    playlist_name: 'Prosper PD',
    transcript_text: 'Accident reported at 5th and Broadway.'
  },
];

const mockHeatmapPoints: HeatmapPoint[] = [
  { lat: 33.2366, lon: -96.8009, count: 5, most_recent: new Date().toISOString() },
  { lat: 33.2400, lon: -96.7950, count: 3, most_recent: new Date().toISOString() },
  { lat: 33.2350, lon: -96.8050, count: 8, most_recent: new Date().toISOString() },
];

export async function getLocations(params?: LocationsQueryParams): Promise<LocationListResponse> {
  if (isMock) {
    return {
      items: mockLocations,
      total: mockLocations.length,
      limit: params?.limit ?? 500,
      offset: params?.offset ?? 0
    };
  }
  try {
    const response = await api.get<LocationListResponse>('/locations', { params });
    return response.data;
  } catch (error) {
    console.warn('Using mock locations due to API error', error);
    return {
      items: mockLocations,
      total: mockLocations.length,
      limit: params?.limit ?? 500,
      offset: params?.offset ?? 0
    };
  }
}

export async function getHeatmap(params?: HeatmapQueryParams): Promise<HeatmapResponse> {
  if (isMock) {
    return {
      points: mockHeatmapPoints,
      total_locations: mockHeatmapPoints.reduce((sum, p) => sum + p.count, 0),
      time_window_hours: params?.hours ?? 24,
      center_lat: 33.2370,
      center_lon: -96.8000
    };
  }
  try {
    const response = await api.get<HeatmapResponse>('/locations/heatmap', { params });
    return response.data;
  } catch (error) {
    console.warn('Using mock heatmap due to API error', error);
    return {
      points: mockHeatmapPoints,
      total_locations: mockHeatmapPoints.reduce((sum, p) => sum + p.count, 0),
      time_window_hours: params?.hours ?? 24,
      center_lat: 33.2370,
      center_lon: -96.8000
    };
  }
}

export async function getLocation(id: string): Promise<Location | undefined> {
  if (isMock) {
    return mockLocations.find(l => l.id === id);
  }
  try {
    const response = await api.get<Location>(`/locations/${id}`);
    return response.data;
  } catch (error) {
    console.warn('Using mock location due to API error', error);
    return mockLocations.find(l => l.id === id);
  }
}

export async function getLocationStats(params?: { feed_id?: string; hours?: number }): Promise<LocationStats> {
  if (isMock) {
    return {
      total_locations: 15,
      geocoded: 12,
      unique_transcripts: 10,
      unique_feeds: 2,
      unique_cities: 3,
      time_range: {
        oldest: new Date(Date.now() - 86400000).toISOString(),
        newest: new Date().toISOString()
      },
      time_window_hours: params?.hours ?? 24
    };
  }
  try {
    const response = await api.get<LocationStats>('/locations/stats/summary', { params });
    return response.data;
  } catch (error) {
    console.warn('Using mock stats due to API error', error);
    return {
      total_locations: 15,
      geocoded: 12,
      unique_transcripts: 10,
      unique_feeds: 2,
      unique_cities: 3,
      time_range: {},
      time_window_hours: params?.hours ?? 24
    };
  }
}
