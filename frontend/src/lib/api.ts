// src/lib/api.ts
import axios from 'axios';

const MOCK = import.meta.env.VITE_MOCK === '1';
const PASTED_JWT = (import.meta.env.VITE_BCFY_JWT as string | undefined) || '';

/** Shared Axios client for real API calls (only used when MOCK === '0'). */
export const api = axios.create({
  baseURL: 'https://api.bcfy.io',
  timeout: 15000,
});

// Attach Authorization only if we're not mocking and a JWT is present.
api.interceptors.request.use((config) => {
  if (!MOCK && PASTED_JWT) {
    config.headers = { ...(config.headers || {}), Authorization: `Bearer ${PASTED_JWT}` };
  }
  return config;
});

/** Utility for other modules to check mock mode. */
export function isMock(): boolean {
  return MOCK;
}
