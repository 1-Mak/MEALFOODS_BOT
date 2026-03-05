const API_BASE = import.meta.env.VITE_API_URL || "";

let authToken: string | null = null;

export function setToken(token: string) {
  authToken = token;
}

export function getToken(): string | null {
  return authToken;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  const resp = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    const msg = body.detail || `HTTP ${resp.status}`;
    const err = new Error(msg) as Error & { status: number; url: string; body: unknown };
    err.status = resp.status;
    err.url = `${options.method || "GET"} ${path}`;
    err.body = body;
    throw err;
  }

  return resp.json();
}
