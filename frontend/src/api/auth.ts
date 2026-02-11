/**
 * Auth API client functions
 */

import { api } from '../lib/api';
import type {
  User,
  UserUpdate,
  UserListResponse,
  UserRoleUpdate,
  AuthAuditLogResponse,
} from '../types/auth';

/**
 * Get current user profile
 */
export async function getCurrentUser(): Promise<User> {
  const response = await api.get<User>('/auth/me');
  return response.data;
}

/**
 * Update current user profile
 */
export async function updateCurrentUser(data: UserUpdate): Promise<User> {
  const response = await api.patch<User>('/auth/me', data);
  return response.data;
}

/**
 * Logout (clears session cookie)
 */
export async function logout(): Promise<void> {
  await api.post('/auth/logout');
}

// ============================================================
// Admin endpoints
// ============================================================

/**
 * List all users (admin only)
 */
export async function listUsers(params?: {
  limit?: number;
  offset?: number;
  role?: 'user' | 'admin';
}): Promise<UserListResponse> {
  const response = await api.get<UserListResponse>('/admin/users', { params });
  return response.data;
}

/**
 * Get a specific user by ID (admin only)
 */
export async function getUser(userId: string): Promise<User> {
  const response = await api.get<User>(`/admin/users/${userId}`);
  return response.data;
}

/**
 * Update a user's role (admin only)
 */
export async function updateUserRole(userId: string, data: UserRoleUpdate): Promise<User> {
  const response = await api.patch<User>(`/admin/users/${userId}/role`, data);
  return response.data;
}

/**
 * Enable or disable a user (admin only)
 */
export async function updateUserStatus(userId: string, isActive: boolean): Promise<User> {
  const response = await api.patch<User>(`/admin/users/${userId}/status`, null, {
    params: { is_active: isActive },
  });
  return response.data;
}

/**
 * Get authentication audit log (admin only)
 */
export async function getAuditLog(params?: {
  limit?: number;
  offset?: number;
  userId?: string;
  eventType?: string;
}): Promise<AuthAuditLogResponse> {
  const response = await api.get<AuthAuditLogResponse>('/admin/audit-log', { params });
  return response.data;
}
