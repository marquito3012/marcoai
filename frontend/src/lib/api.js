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
const MAX_RETRIES = 3
const RETRY_BASE_DELAY = 1000

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name    = 'ApiError'
    this.status  = status
  }
}

function isRetryable(status) {
  return !status || status >= 500
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Thin wrapper around `fetch` that:
 *  - Prepends the API base URL
 *  - Includes cookies (credentials: 'include')
 *  - Sets Content-Type: application/json by default
 *  - Retries on network errors and 5xx with exponential backoff
 *  - Throws `ApiError` on non-2xx responses
 *
 * @param {string} path    - e.g. '/auth/me'
 * @param {RequestInit} [options]
 * @returns {Promise<any>} - parsed JSON response
 */
export async function apiFetch(path, options = {}) {
  const { headers: extraHeaders, signal, ...rest } = options
  let lastError

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const res = await fetch(`${BASE}${path}`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...extraHeaders,
        },
        signal,
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
        if (isRetryable(res.status) && attempt < MAX_RETRIES) {
          await sleep(RETRY_BASE_DELAY * Math.pow(2, attempt))
          continue
        }
        throw new ApiError(detail, res.status)
      }

      if (res.status === 204) return null
      return res.json()
    } catch (err) {
      if (err.name === 'AbortError') throw err
      lastError = err
      if (attempt < MAX_RETRIES && (!err.status || err.name === 'TypeError')) {
        await sleep(RETRY_BASE_DELAY * Math.pow(2, attempt))
        continue
      }
      throw err
    }
  }

  throw lastError
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
