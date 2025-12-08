// src/lib/api.ts
import axios from 'axios';

const MOCK = import.meta.env.VITE_MOCK === '1';

// Use local backend API by default, or environment variable override
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

/** Shared Axios client for API calls to backend. */
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

/** Utility for other modules to check mock mode. */
export function isMock(): boolean {
  return MOCK;
}

/** Get current API base URL */
export function getCurrentApiBaseUrl(): string {
  return API_BASE_URL;
}

/** Set API base URL (for runtime configuration) */
export function setApiBaseUrl(url: string): void {
  api.defaults.baseURL = url.trim() || '/api';
}
