/**
 * Authentication types
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

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isAdmin: boolean;
  error: string | null;
}

export interface AuthContextValue extends AuthState {
  /**
   * Sign in with Google OAuth
   */
  loginWithGoogle: () => Promise<void>;

  /**
   * Sign in with email and password
   */
  loginWithEmail: (email: string, password: string) => Promise<void>;

  /**
   * Register a new account with email and password
   */
  registerWithEmail: (email: string, password: string) => Promise<void>;

  /**
   * Sign out
   */
  logout: () => Promise<void>;

  /**
   * Clear any auth errors
   */
  clearError: () => void;

  /**
   * Refresh the current user's profile from the server
   */
  refreshUser: () => Promise<void>;
}

export interface SessionResponse {
  user: User;
  message: string;
}
