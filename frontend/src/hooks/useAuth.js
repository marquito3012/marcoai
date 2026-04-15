/**
 * MarcoAI – useAuth hook
 *
 * Provides:
 *   - `user`, `isAuthenticated`, `isLoading` from the global auth store
 *   - `logout()` – calls the backend and clears the store
 *   - `initAuth()` – called once on app mount to verify the cookie
 */
import { useCallback } from 'react'
import { apiFetch, logoutApi } from '../lib/api'
import useAuthStore from '../store/authStore'

export function useAuth() {
  const { user, isAuthenticated, isLoading, setUser, clearUser } = useAuthStore()

  /**
   * Ping /auth/me to check if a valid JWT cookie exists.
   * Should be called exactly once, from App.jsx on mount.
   */
  const initAuth = useCallback(async () => {
    try {
      const userData = await apiFetch('/auth/me')
      setUser(userData)
    } catch {
      clearUser()
    }
  }, [setUser, clearUser])

  /**
   * Log the user out:
   *   1. Calls POST /auth/logout (backend clears the HttpOnly cookie)
   *   2. Clears the Zustand store
   */
  const logout = useCallback(async () => {
    try {
      await logoutApi()
    } finally {
      clearUser()
    }
  }, [clearUser])

  return {
    user,
    isAuthenticated,
    isLoading,
    logout,
    initAuth,
  }
}
