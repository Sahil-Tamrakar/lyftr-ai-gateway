import type { ChatResponse, HealthStatus } from "./types";

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

export interface ChatPayload {
  session_id: string;
  message: string;
  system_prompt: string;
}

export class ChatApiError extends Error {
  readonly status: number;
  readonly title: string;

  constructor(status: number, detail: string, title: string) {
    super(detail);
    this.name = "ChatApiError";
    this.status = status;
    this.title = title;
  }
}

function titleForStatus(status: number): string {
  if (status === 422) return "Validation error";
  if (status === 503) return "Service unavailable";
  if (status === 502) return "Provider error";
  if (status === 404) return "Not found";
  if (status >= 500) return "Server error";
  return "Request failed";
}

function describeDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return JSON.stringify(item);
      })
      .filter(Boolean)
      .join(" · ");
  }
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return "";
}

export async function sendChat(payload: ChatPayload): Promise<ChatResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new ChatApiError(
      0,
      `Unable to reach the API at ${API_BASE_URL}. Make sure the backend is running and ALLOWED_ORIGINS includes this page.`,
      "Network error",
    );
  }

  const raw = await response.text();
  let body: unknown = null;
  if (raw) {
    try {
      body = JSON.parse(raw);
    } catch {
      body = null;
    }
  }

  if (!response.ok) {
    const detail =
      describeDetail((body as { detail?: unknown } | null)?.detail) ||
      `Request failed with status ${response.status}.`;
    throw new ChatApiError(response.status, detail, titleForStatus(response.status));
  }

  const parsed = body as ChatResponse | null;
  if (!parsed || typeof parsed.reply !== "string" || !parsed.metadata) {
    throw new ChatApiError(
      502,
      "The API returned an unexpected response shape.",
      "Bad response",
    );
  }
  return parsed;
}

export async function fetchHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }
  return (await response.json()) as HealthStatus;
}
