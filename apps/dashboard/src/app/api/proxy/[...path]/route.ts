/**
 * Proxy route — forwards /api/proxy/* to the FastAPI host, server-to-server.
 *
 * Keeps API_URL server-side (never exposed to the browser) and avoids CORS:
 * the browser only ever talks to Next.js. Read-only dashboard → GET only.
 *
 *   GET /api/proxy/api/v1/positions/open  →  GET ${API_URL}/api/v1/positions/open
 */

import { type NextRequest, NextResponse } from "next/server"

const API_URL = process.env.API_URL ?? "http://localhost:8000"

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params
  const upstream = `${API_URL}/${path.join("/")}${req.nextUrl.search}`
  const headers: Record<string, string> = { "Content-Type": "application/json" }
  // Forward the dashboard token (server-side env) when the API requires it.
  if (process.env.DASHBOARD_API_TOKEN) {
    headers["X-Dashboard-Token"] = process.env.DASHBOARD_API_TOKEN
  }
  try {
    const res = await fetch(upstream, { headers, cache: "no-store" })
    const body = await res.text()
    return new NextResponse(body, {
      status: res.status,
      headers: { "Content-Type": res.headers.get("Content-Type") ?? "application/json" },
    })
  } catch {
    return NextResponse.json(
      { detail: `dashboard API unreachable at ${API_URL}` },
      { status: 502 },
    )
  }
}
