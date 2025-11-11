import axios from 'axios';

const defaultBaseUrl = import.meta.env.VITE_API_URL ?? '/api';
const storageKey = 'police-scanner-api-url';

function resolveBaseUrl() {
  if (typeof window !== 'undefined') {
    const stored = window.localStorage.getItem(storageKey);
    if (stored) {
      return stored;
    }
  }
  return defaultBaseUrl;
}

export const api = axios.create({
  baseURL: resolveBaseUrl(),
  withCredentials: false
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      console.warn('Unauthorized: ensure you are authenticated.');
    }
    if (status >= 500) {
      console.error('Server error from API', error);
    }
    return Promise.reject(error);
  }
);

export function setApiBaseUrl(url: string) {
  if (typeof window !== 'undefined') {
    if (url) {
      window.localStorage.setItem(storageKey, url);
    } else {
      window.localStorage.removeItem(storageKey);
    }
  }
  api.defaults.baseURL = url || defaultBaseUrl;
}

export function getCurrentApiBaseUrl() {
  return api.defaults.baseURL ?? defaultBaseUrl;
}

export default api;
