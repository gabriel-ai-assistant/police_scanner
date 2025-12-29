/**
 * User authentication types
 *
 * These types match the backend Pydantic models in app_api/models/auth.py
 */

export interface User {
  id: string;
  firebaseUid: string;
  email: string;
  emailVerified: boolean;
  displayName: string | null;
  avatarUrl: string | null;
  role: 'user' | 'admin';
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  lastLoginAt: string | null;
}

export interface UserUpdate {
  displayName?: string;
}

export interface UserRoleUpdate {
  role: 'user' | 'admin';
}

export interface SessionRequest {
  id_token: string;
}

export interface SessionResponse {
  user: User;
  message: string;
}

export interface UserListResponse {
  users: User[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuthAuditLog {
  id: number;
  userId: string | null;
  eventType: string;
  ipAddress: string | null;
  userAgent: string | null;
  metadata: Record<string, unknown> | null;
  createdAt: string;
}

export interface AuthAuditLogResponse {
  logs: AuthAuditLog[];
  total: number;
  limit: number;
  offset: number;
}
