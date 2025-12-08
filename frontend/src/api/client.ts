// src/api/client.ts
import type { AxiosInstance } from 'axios';
import { api, isMock } from '@/lib/api';

/** Axios instance used by API modules */
export const apiClient: AxiosInstance = api;

/** Helper so other API modules can branch on mock vs live */
export const isMockMode = isMock;

const API_BASE_URL_KEY = 'police-scanner-api-base-url';

/**
 * Get the current API base URL from localStorage or environment
 */
export function getCurrentApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const stored = window.localStorage.getItem(API_BASE_URL_KEY);
    if (stored) {
      return stored;
    }
  }
  return import.meta.env.VITE_API_URL || '/api';
}

/**
 * Set the API base URL and update the axios instance
 */
export function setApiBaseUrl(url: string): void {
  if (typeof window !== 'undefined') {
    if (url.trim()) {
      window.localStorage.setItem(API_BASE_URL_KEY, url.trim());
    } else {
      window.localStorage.removeItem(API_BASE_URL_KEY);
    }
  }
  // Update axios baseURL
  api.defaults.baseURL = url.trim() || import.meta.env.VITE_API_URL || '/api';
}

export default apiClient;
