const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiOptions {
  method?: string;
  body?: unknown;
  token?: string;
}

async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (options.token) {
    headers["Authorization"] = `Bearer ${options.token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || "Request failed");
  }

  return response.json();
}

export function register(email: string, password: string) {
  return api<{ token: string }>("/auth/register", {
    method: "POST",
    body: { email, password },
  });
}

export function login(email: string, password: string) {
  return api<{ token: string }>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export interface Session {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface SessionDetail {
  id: number;
  title: string;
  messages: { role: string; content: string; created_at: string }[];
}

export function listSessions(token: string) {
  return api<Session[]>("/sessions", { token });
}

export function createSession(token: string) {
  return api<{ id: number }>("/sessions", { method: "POST", token });
}

export function getSession(token: string, sessionId: number) {
  return api<SessionDetail>(`/sessions/${sessionId}`, { token });
}

export function addMessage(
  token: string,
  sessionId: number,
  role: string,
  content: string
) {
  return api<{ status: string }>(`/sessions/${sessionId}/messages`, {
    method: "POST",
    token,
    body: { role, content },
  });
}

export { API_URL };
