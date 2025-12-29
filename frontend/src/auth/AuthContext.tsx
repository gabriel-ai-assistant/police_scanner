/**
 * Authentication Context and Provider
 *
 * Manages authentication state using Firebase Auth and backend sessions.
 * Flow:
 * 1. User authenticates with Firebase (Google OAuth or email/password)
 * 2. Firebase returns an ID token
 * 3. Frontend sends token to backend /api/auth/session
 * 4. Backend verifies token and sets httpOnly session cookie
 * 5. Subsequent requests include cookie automatically
 */

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  useCallback,
  ReactNode,
} from 'react';
import { api } from '@/lib/api';
import {
  signInWithGoogle,
  signInWithEmail,
  registerWithEmail,
  firebaseSignOut,
  isFirebaseConfigured,
} from '@/lib/firebase';
import type { AuthContextValue, AuthState, User, SessionResponse } from './types';

// Initial state
const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  isAdmin: false,
  error: null,
};

// Create context
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Hook to access auth context
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Auth Provider Component
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>(initialState);

  /**
   * Create session with backend after Firebase auth
   */
  const createBackendSession = useCallback(async (idToken: string): Promise<User> => {
    const response = await api.post<SessionResponse>('/auth/session', {
      id_token: idToken,
    });
    return response.data.user;
  }, []);

  /**
   * Fetch current user from backend (uses session cookie)
   */
  const fetchCurrentUser = useCallback(async (): Promise<User | null> => {
    try {
      const response = await api.get<User>('/auth/me');
      return response.data;
    } catch (error: any) {
      // 401 means not authenticated - not an error
      if (error.response?.status === 401) {
        return null;
      }
      console.error('Error fetching current user:', error);
      return null;
    }
  }, []);

  /**
   * Initialize auth state on mount
   */
  useEffect(() => {
    const initAuth = async () => {
      try {
        // Try to restore session from cookie
        const user = await fetchCurrentUser();

        if (user) {
          setState({
            user,
            isAuthenticated: true,
            isLoading: false,
            isAdmin: user.role === 'admin',
            error: null,
          });
        } else {
          setState({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            isAdmin: false,
            error: null,
          });
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
        setState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          isAdmin: false,
          error: null,
        });
      }
    };

    initAuth();
  }, [fetchCurrentUser]);

  /**
   * Login with Google OAuth
   */
  const loginWithGoogle = useCallback(async () => {
    if (!isFirebaseConfigured()) {
      setState(prev => ({
        ...prev,
        error: 'Authentication service is not configured',
      }));
      return;
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // 1. Get Firebase ID token via Google OAuth
      const idToken = await signInWithGoogle();

      // 2. Create session with backend
      const user = await createBackendSession(idToken);

      setState({
        user,
        isAuthenticated: true,
        isLoading: false,
        isAdmin: user.role === 'admin',
        error: null,
      });
    } catch (error: any) {
      console.error('Google login error:', error);
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error.message || 'Failed to sign in with Google',
      }));
    }
  }, [createBackendSession]);

  /**
   * Login with email and password
   */
  const loginWithEmailFn = useCallback(async (email: string, password: string) => {
    if (!isFirebaseConfigured()) {
      setState(prev => ({
        ...prev,
        error: 'Authentication service is not configured',
      }));
      return;
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // 1. Get Firebase ID token via email/password
      const idToken = await signInWithEmail(email, password);

      // 2. Create session with backend
      const user = await createBackendSession(idToken);

      setState({
        user,
        isAuthenticated: true,
        isLoading: false,
        isAdmin: user.role === 'admin',
        error: null,
      });
    } catch (error: any) {
      console.error('Email login error:', error);
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error.message || 'Failed to sign in',
      }));
    }
  }, [createBackendSession]);

  /**
   * Register with email and password
   */
  const registerWithEmailFn = useCallback(async (email: string, password: string) => {
    if (!isFirebaseConfigured()) {
      setState(prev => ({
        ...prev,
        error: 'Authentication service is not configured',
      }));
      return;
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // 1. Create Firebase account and get ID token
      const idToken = await registerWithEmail(email, password);

      // 2. Create session with backend (also creates user record)
      const user = await createBackendSession(idToken);

      setState({
        user,
        isAuthenticated: true,
        isLoading: false,
        isAdmin: user.role === 'admin',
        error: null,
      });
    } catch (error: any) {
      console.error('Registration error:', error);
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error.message || 'Failed to create account',
      }));
    }
  }, [createBackendSession]);

  /**
   * Logout
   */
  const logout = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true }));

    try {
      // 1. Sign out from Firebase
      await firebaseSignOut();

      // 2. Clear backend session (clears cookie)
      try {
        await api.post('/auth/logout');
      } catch (error) {
        // Ignore errors - we're logging out anyway
        console.debug('Logout API error (ignored):', error);
      }

      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        isAdmin: false,
        error: null,
      });
    } catch (error: any) {
      console.error('Logout error:', error);
      // Still clear state even if there's an error
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        isAdmin: false,
        error: null,
      });
    }
  }, []);

  /**
   * Clear error
   */
  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  /**
   * Refresh user from backend
   */
  const refreshUser = useCallback(async () => {
    const user = await fetchCurrentUser();
    if (user) {
      setState(prev => ({
        ...prev,
        user,
        isAuthenticated: true,
        isAdmin: user.role === 'admin',
      }));
    }
  }, [fetchCurrentUser]);

  // Memoize context value
  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      loginWithGoogle,
      loginWithEmail: loginWithEmailFn,
      registerWithEmail: registerWithEmailFn,
      logout,
      clearError,
      refreshUser,
    }),
    [state, loginWithGoogle, loginWithEmailFn, registerWithEmailFn, logout, clearError, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
