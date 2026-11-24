import { ChatRequestPayload, ChatResponsePayload, HealthStatus } from '../types/chat';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function checkHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

export async function sendChatMessage(
  payload: ChatRequestPayload,
  simulateFailureHeader?: string
): Promise<ChatResponsePayload> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (simulateFailureHeader) {
    headers['X-Simulate-Failure'] = simulateFailureHeader;
  }

  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      // fallback to status text
    }
    const error: any = new Error(errorDetail);
    error.status = res.status;
    throw error;
  }

  return res.json();
}
