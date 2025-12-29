/**
 * Firebase client configuration
 *
 * This module initializes the Firebase client SDK for authentication.
 * Firebase handles the OAuth flow with Google and email/password auth.
 */

import { initializeApp, getApps, FirebaseApp } from 'firebase/app';
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  User as FirebaseUser,
  Auth,
} from 'firebase/auth';

// Firebase configuration from environment variables
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
};

// Validate configuration
const isConfigValid = Boolean(
  firebaseConfig.apiKey &&
  firebaseConfig.authDomain &&
  firebaseConfig.projectId
);

// Initialize Firebase (singleton pattern)
let app: FirebaseApp | null = null;
let auth: Auth | null = null;

if (isConfigValid) {
  // Only initialize if not already initialized
  if (getApps().length === 0) {
    app = initializeApp(firebaseConfig);
  } else {
    app = getApps()[0];
  }
  auth = getAuth(app);
} else {
  console.warn(
    'Firebase configuration is incomplete. Authentication will not work. ' +
    'Please set VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, and VITE_FIREBASE_PROJECT_ID.'
  );
}

// Google OAuth provider
const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({
  prompt: 'select_account', // Always show account picker
});

/**
 * Check if Firebase is properly configured
 */
export function isFirebaseConfigured(): boolean {
  return isConfigValid && auth !== null;
}

/**
 * Get the Firebase Auth instance
 */
export function getFirebaseAuth(): Auth | null {
  return auth;
}

/**
 * Sign in with Google OAuth
 * Returns the Firebase ID token on success
 */
export async function signInWithGoogle(): Promise<string> {
  if (!auth) {
    throw new Error('Firebase not configured');
  }

  try {
    const result = await signInWithPopup(auth, googleProvider);
    const idToken = await result.user.getIdToken();
    return idToken;
  } catch (error: any) {
    console.error('Google sign-in error:', error);

    // Provide user-friendly error messages
    switch (error.code) {
      case 'auth/popup-blocked':
        throw new Error('Please allow popups for this site to sign in with Google');
      case 'auth/popup-closed-by-user':
        throw new Error('Sign-in was cancelled');
      case 'auth/cancelled-popup-request':
        throw new Error('Sign-in was cancelled');
      default:
        throw new Error(error.message || 'Failed to sign in with Google');
    }
  }
}

/**
 * Sign in with email and password
 * Returns the Firebase ID token on success
 */
export async function signInWithEmail(email: string, password: string): Promise<string> {
  if (!auth) {
    throw new Error('Firebase not configured');
  }

  try {
    const result = await signInWithEmailAndPassword(auth, email, password);
    const idToken = await result.user.getIdToken();
    return idToken;
  } catch (error: any) {
    console.error('Email sign-in error:', error);

    // Provide user-friendly error messages
    switch (error.code) {
      case 'auth/invalid-email':
        throw new Error('Invalid email address');
      case 'auth/user-disabled':
        throw new Error('This account has been disabled');
      case 'auth/user-not-found':
        throw new Error('No account found with this email');
      case 'auth/wrong-password':
        throw new Error('Incorrect password');
      case 'auth/invalid-credential':
        throw new Error('Invalid email or password');
      case 'auth/too-many-requests':
        throw new Error('Too many failed attempts. Please try again later');
      default:
        throw new Error(error.message || 'Failed to sign in');
    }
  }
}

/**
 * Register a new account with email and password
 * Returns the Firebase ID token on success
 */
export async function registerWithEmail(email: string, password: string): Promise<string> {
  if (!auth) {
    throw new Error('Firebase not configured');
  }

  try {
    const result = await createUserWithEmailAndPassword(auth, email, password);
    const idToken = await result.user.getIdToken();
    return idToken;
  } catch (error: any) {
    console.error('Email registration error:', error);

    // Provide user-friendly error messages
    switch (error.code) {
      case 'auth/email-already-in-use':
        throw new Error('An account with this email already exists');
      case 'auth/invalid-email':
        throw new Error('Invalid email address');
      case 'auth/weak-password':
        throw new Error('Password is too weak. Please use at least 6 characters');
      default:
        throw new Error(error.message || 'Failed to create account');
    }
  }
}

/**
 * Sign out from Firebase
 */
export async function firebaseSignOut(): Promise<void> {
  if (!auth) {
    return;
  }

  try {
    await signOut(auth);
  } catch (error) {
    console.error('Sign out error:', error);
    throw new Error('Failed to sign out');
  }
}

/**
 * Get the current Firebase user
 */
export function getCurrentFirebaseUser(): FirebaseUser | null {
  return auth?.currentUser ?? null;
}

/**
 * Subscribe to auth state changes
 * Returns an unsubscribe function
 */
export function onFirebaseAuthStateChanged(
  callback: (user: FirebaseUser | null) => void
): () => void {
  if (!auth) {
    // Call with null immediately if not configured
    callback(null);
    return () => {};
  }

  return onAuthStateChanged(auth, callback);
}

/**
 * Get a fresh ID token for the current user
 * Useful for refreshing tokens before API calls
 */
export async function getIdToken(forceRefresh = false): Promise<string | null> {
  const user = getCurrentFirebaseUser();
  if (!user) {
    return null;
  }

  try {
    return await user.getIdToken(forceRefresh);
  } catch (error) {
    console.error('Error getting ID token:', error);
    return null;
  }
}

// Export types
export type { FirebaseUser };
