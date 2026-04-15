/**
 * MarcoAI – Auth Zustand Store
 *
 * Tracks the authenticated user globally.
 * `isLoading` starts true until the /auth/me check resolves,
 * preventing a flash of the login page for already-authenticated users.
 */
import { create } from 'zustand'

const useAuthStore = create((set) => ({
  /** @type {{ id: string, email: string, name: string, picture_url: string | null } | null} */
  user:            null,
  isAuthenticated: false,
  isLoading:       true,   // true while we're checking the JWT cookie

  /** Called after a successful /auth/me response */
  setUser: (user) =>
    set({ user, isAuthenticated: !!user, isLoading: false }),

  /** Called when /auth/me returns 401 or after logout */
  clearUser: () =>
    set({ user: null, isAuthenticated: false, isLoading: false }),
}))

export default useAuthStore
