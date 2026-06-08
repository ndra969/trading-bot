/**
 * API client — pure fetch through the Next proxy (`/api/proxy/*`).
 *
 * The browser only ever hits same-origin `/api/proxy/...`; the proxy route
 * forwards server-to-server to the FastAPI host (API_URL), so there's no CORS
 * and the API URL stays server-side. Mirrors reference/polyforge/lib/api.ts.
 */

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

const PROXY_PREFIX = "/api/proxy"

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${PROXY_PREFIX}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  })
  if (!res.ok) {
    let message = res.statusText
    try {
      const body = await res.json()
      message = body?.detail ?? body?.message ?? message
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, message)
  }
  return res.json() as Promise<T>
}

/** Build a query string from a params object, dropping null/undefined/"". */
export function qs(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ""
}
