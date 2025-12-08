import { api } from '@/lib/api';

// Types
export interface Country {
  coid: number;
  country_name: string;
  country_code: string;
  sync: boolean;
  is_active: boolean;
}

export interface State {
  stid: number;
  coid: number;
  state_name: string;
  state_code: string;
  sync: boolean;
  is_active: boolean;
}

export interface County {
  cntid: number;
  stid: number;
  coid: number;
  county_name: string;
  state_name?: string;
  state_code?: string;
  sync: boolean;
  is_active: boolean;
  lat?: number;
  lon?: number;
}

export interface Playlist {
  uuid: string;
  name: string;
  descr?: string;
  listeners?: number;
  sync: boolean;
}

export interface SystemLog {
  id: number;
  timestamp: string;
  component: string;
  event_type: string;
  severity: string;
  message?: string;
}

export interface ProcessingState {
  queued: number;
  downloaded: number;
  transcribed: number;
  indexed: number;
  error: number;
  total: number;
}

const isMock = import.meta.env.VITE_MOCK === '1';

// Mock data
const mockCountries: Country[] = [
  { coid: 1, country_name: 'United States', country_code: 'US', sync: true, is_active: true },
  { coid: 2, country_name: 'Canada', country_code: 'CA', sync: false, is_active: true },
];

const mockStates: State[] = [
  { stid: 1, coid: 1, state_name: 'Texas', state_code: 'TX', sync: true, is_active: true },
  { stid: 2, coid: 1, state_name: 'California', state_code: 'CA', sync: false, is_active: true },
];

const mockCounties: County[] = [
  { cntid: 1, stid: 1, coid: 1, county_name: 'Bexar County', state_name: 'Texas', state_code: 'TX', sync: true, is_active: true },
  { cntid: 2, stid: 1, coid: 1, county_name: 'Harris County', state_name: 'Texas', state_code: 'TX', sync: false, is_active: true },
];

const mockPlaylists: Playlist[] = [
  { uuid: 'playlist-1', name: 'San Antonio Police', listeners: 150, sync: true },
  { uuid: 'playlist-2', name: 'San Antonio Fire', listeners: 75, sync: true },
  { uuid: 'playlist-3', name: 'Austin Police', listeners: 200, sync: false },
];

// Countries
export async function getCountries(syncOnly = false): Promise<Country[]> {
  if (isMock) return syncOnly ? mockCountries.filter(c => c.sync) : mockCountries;
  try {
    const params = syncOnly ? { sync_only: true } : {};
    const res = await api.get('/geography/countries', { params });
    return res.data ?? [];
  } catch (e) {
    console.warn('getCountries failed', e);
    return syncOnly ? mockCountries.filter(c => c.sync) : mockCountries;
  }
}

export async function updateCountrySync(coid: number, sync: boolean): Promise<Country> {
  if (isMock) {
    const country = mockCountries.find(c => c.coid === coid);
    if (country) country.sync = sync;
    return country || mockCountries[0];
  }
  try {
    const res = await api.patch(`/geography/countries/${coid}`, { sync });
    return res.data;
  } catch (e) {
    console.error('updateCountrySync failed', e);
    throw e;
  }
}

// States
export async function getStates(coid?: number, syncOnly = false): Promise<State[]> {
  if (isMock) {
    let states = mockStates;
    if (coid) states = states.filter(s => s.coid === coid);
    if (syncOnly) states = states.filter(s => s.sync);
    return states;
  }
  try {
    const params: Record<string, any> = {};
    if (coid) params.coid = coid;
    if (syncOnly) params.sync_only = true;
    const res = await api.get('/geography/states', { params });
    return res.data ?? [];
  } catch (e) {
    console.warn('getStates failed', e);
    let states = mockStates;
    if (coid) states = states.filter(s => s.coid === coid);
    if (syncOnly) states = states.filter(s => s.sync);
    return states;
  }
}

export async function updateStateSync(stid: number, sync: boolean): Promise<State> {
  if (isMock) {
    const state = mockStates.find(s => s.stid === stid);
    if (state) state.sync = sync;
    return state || mockStates[0];
  }
  try {
    const res = await api.patch(`/geography/states/${stid}`, { sync });
    return res.data;
  } catch (e) {
    console.error('updateStateSync failed', e);
    throw e;
  }
}

// Counties
export async function getCounties(stid?: number, syncOnly = false): Promise<County[]> {
  if (isMock) {
    let counties = mockCounties;
    if (stid) counties = counties.filter(c => c.stid === stid);
    if (syncOnly) counties = counties.filter(c => c.sync);
    return counties;
  }
  try {
    const params: Record<string, any> = {};
    if (stid) params.stid = stid;
    if (syncOnly) params.sync_only = true;
    const res = await api.get('/geography/counties', { params });
    return res.data ?? [];
  } catch (e) {
    console.warn('getCounties failed', e);
    let counties = mockCounties;
    if (stid) counties = counties.filter(c => c.stid === stid);
    if (syncOnly) counties = counties.filter(c => c.sync);
    return counties;
  }
}

export async function updateCountySync(cntid: number, sync: boolean): Promise<County> {
  if (isMock) {
    const county = mockCounties.find(c => c.cntid === cntid);
    if (county) county.sync = sync;
    return county || mockCounties[0];
  }
  try {
    const res = await api.patch(`/geography/counties/${cntid}`, { sync });
    return res.data;
  } catch (e) {
    console.error('updateCountySync failed', e);
    throw e;
  }
}

// Playlists
export async function getAllPlaylists(): Promise<Playlist[]> {
  if (isMock) return mockPlaylists;
  try {
    const res = await api.get('/playlists', { params: { limit: 1000 } });
    return res.data ?? [];
  } catch (e) {
    console.warn('getAllPlaylists failed', e);
    return mockPlaylists;
  }
}

export async function updatePlaylistSync(uuid: string, sync: boolean): Promise<Playlist> {
  if (isMock) {
    const playlist = mockPlaylists.find(p => p.uuid === uuid);
    if (playlist) playlist.sync = sync;
    return playlist || mockPlaylists[0];
  }
  try {
    const res = await api.patch(`/playlists/${uuid}`, { sync });
    return res.data;
  } catch (e) {
    console.error('updatePlaylistSync failed', e);
    throw e;
  }
}

// System monitoring
export async function getSystemLogs(component?: string, severity?: string, limit = 50): Promise<SystemLog[]> {
  if (isMock) return [];
  try {
    const params: Record<string, any> = { limit };
    if (component) params.component = component;
    if (severity) params.severity = severity;
    const res = await api.get('/system/logs', { params });
    return res.data ?? [];
  } catch (e) {
    console.warn('getSystemLogs failed', e);
    return [];
  }
}

export async function getProcessingState(): Promise<ProcessingState> {
  if (isMock) {
    return { queued: 3, downloaded: 5, transcribed: 142, indexed: 135, error: 0, total: 285 };
  }
  try {
    const res = await api.get('/system/processing-state');
    return res.data;
  } catch (e) {
    console.warn('getProcessingState failed', e);
    return { queued: 0, downloaded: 0, transcribed: 0, indexed: 0, error: 0, total: 0 };
  }
}

export async function getSystemStatus(): Promise<any> {
  if (isMock) {
    return {
      status: 'operational',
      calls_total: 145,
      transcripts_total: 127,
      active_playlists: 8,
      recent_error: null,
    };
  }
  try {
    const res = await api.get('/system/status');
    return res.data;
  } catch (e) {
    console.warn('getSystemStatus failed', e);
    return { status: 'unknown' };
  }
}
