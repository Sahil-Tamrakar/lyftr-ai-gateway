export type ResolutionSource = "LIVE_INFERENCE" | "LLM_CACHE";

export interface MessageMetadata {
  resolution_source: ResolutionSource | string;
  model: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  key_id: string | null;
  fallback_attempts: number;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  metadata: MessageMetadata;
}

export interface HealthStatus {
  status: string;
  keys_configured: number;
  cache_enabled: boolean;
}

export type ChatRole = "user" | "assistant" | "error";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  metadata?: MessageMetadata;
  errorTitle?: string;
  status?: number;
}
