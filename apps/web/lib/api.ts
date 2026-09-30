/**
 * Minimal typed API client. The browser always calls same-origin `/api/*`
 * (proxied to FastAPI by the Next.js rewrite in next.config.ts) — see
 * ADR-001 D10. There is no base-URL configuration here on purpose: adding
 * one would be an easy way to accidentally reintroduce cross-origin calls.
 */

export interface HealthStatus {
  status: "ok" | "degraded";
  database: "ok" | "unreachable";
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "support2fix",
      ...init?.headers,
    },
  });

  if (!res.ok && res.status !== 503) {
    throw new ApiError(res.status, `Request to ${path} failed: ${res.status}`);
  }

  return (await res.json()) as T;
}

export function getHealth(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>("/v1/health");
}
