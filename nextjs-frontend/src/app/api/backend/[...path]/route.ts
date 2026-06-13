/**
 * Catch-all proxy route: /api/backend/** → http://localhost:8000/api/v1/**
 *
 * Replaces the next.config.mjs rewrite so we can set an explicit 120-second
 * timeout. The old rewrite had no timeout control; long-running Groq calls
 * caused the browser to receive a 500 before the backend finished.
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_BASE = "http://localhost:8000/api/v1";

/** Headers that must not be forwarded to an upstream HTTP request. */
const HOP_BY_HOP = new Set([
  "host",
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
]);

async function proxy(
  req: NextRequest,
  pathSegments: string[]
): Promise<NextResponse> {
  const pathname = pathSegments.join("/");
  const search = req.nextUrl.search ?? "";
  const url = `${BACKEND_BASE}/${pathname}${search}`;

  // 120-second hard timeout — well above Groq's worst-case rate-limit wait.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120_000);

  try {
    // Forward all application headers; strip hop-by-hop ones.
    const forwardHeaders = new Headers();
    req.headers.forEach((value, key) => {
      if (!HOP_BY_HOP.has(key.toLowerCase())) {
        forwardHeaders.set(key, value);
      }
    });

    // Read the body as a Blob so both JSON and multipart/form-data work.
    const hasBody = req.method !== "GET" && req.method !== "HEAD";
    const body = hasBody ? await req.blob() : undefined;

    const upstream = await fetch(url, {
      method: req.method,
      headers: forwardHeaders,
      body,
      signal: controller.signal,
      // Disable Next.js extended fetch caching for proxy requests.
      cache: "no-store",
    });

    // Forward the full response body and headers back to the browser.
    const responseBlob = await upstream.blob();
    const responseHeaders = new Headers();
    upstream.headers.forEach((value, key) => {
      if (!HOP_BY_HOP.has(key.toLowerCase())) {
        responseHeaders.set(key, value);
      }
    });

    return new NextResponse(responseBlob, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (err: unknown) {
    const aborted =
      controller.signal.aborted ||
      (err instanceof Error && err.name === "AbortError");

    if (aborted) {
      return NextResponse.json(
        { detail: "Backend request timed out after 120 seconds." },
        { status: 504 }
      );
    }

    const message = err instanceof Error ? err.message : "Unknown proxy error";
    console.error("[backend-proxy] error:", message);
    return NextResponse.json(
      { detail: `Proxy error: ${message}` },
      { status: 502 }
    );
  } finally {
    clearTimeout(timer);
  }
}

export async function GET(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxy(req, params.path);
}

export async function POST(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxy(req, params.path);
}

export async function PUT(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxy(req, params.path);
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxy(req, params.path);
}
