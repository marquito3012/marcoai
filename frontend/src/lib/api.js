/**
 * MarcoAI – Centralised API client
 *
 * All requests automatically include the session cookie (credentials: 'include')
 * so the HttpOnly JWT is sent on every call without the frontend ever touching it.
 *
 * Usage:
 *   import { apiFetch } from '@/lib/api'
 *   const user = await apiFetch('/auth/me')
 *   await apiFetch('/chat', { method: 'POST', body: JSON.stringify({ message }) })
 */

const BASE = '/api/v1'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name    = 'ApiError'
    this.status  = status
  }
}

/**
 * Thin wrapper around `fetch` that:
 *  - Prepends the API base URL
 *  - Includes cookies (credentials: 'include')
 *  - Sets Content-Type: application/json by default
 *  - Throws `ApiError` on non-2xx responses
 *
 * @param {string} path    - e.g. '/auth/me'
 * @param {RequestInit} [options]
 * @returns {Promise<any>} - parsed JSON response
 */
export async function apiFetch(path, options = {}) {
  const { headers: extraHeaders, ...rest } = options

  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...extraHeaders,
    },
    ...rest,
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail ?? detail
    } catch {
      // ignore parse error
    }
    throw new ApiError(detail, res.status)
  }

  // 204 No Content
  if (res.status === 204) return null
  return res.json()
}

/** Convenience shortcuts */
export const apiGet    = (path, opts)   => apiFetch(path, { method: 'GET',    ...opts })
export const apiPost   = (path, body)   => apiFetch(path, { method: 'POST',   body: JSON.stringify(body) })
export const apiPut    = (path, body)   => apiFetch(path, { method: 'PUT',    body: JSON.stringify(body) })
export const apiDelete = (path)         => apiFetch(path, { method: 'DELETE' })

/** Redirect to the backend's Google OAuth initiation endpoint */
export function loginWithGoogle() {
  window.location.href = `${BASE}/auth/google`
}

/** Clear the server-side JWT cookie */
export async function logoutApi() {
  return apiPost('/auth/logout', {})
}
