// src/api/client.ts
import type { AxiosInstance } from 'axios';
import { api, isMock } from '@/lib/api';

/** Axios instance used by API modules */
export const apiClient: AxiosInstance = api;

/** Helper so other API modules can branch on mock vs live */
export const isMockMode = isMock;

export default apiClient;
