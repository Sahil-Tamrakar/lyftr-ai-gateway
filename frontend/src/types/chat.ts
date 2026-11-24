export interface MessageMetadata {
  resolution_source: 'LIVE_INFERENCE' | 'LLM_CACHE';
  model: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  key_id: string | null;
  fallback_attempts: number;
}

export interface ChatMessage {
  id?: number;
  role: 'user' | 'assistant' | 'error';
  content: string;
  metadata?: MessageMetadata;
  status_code?: number;
}

export interface ChatRequestPayload {
  session_id: string;
  message: string;
  system_prompt?: string;
}

export interface ChatResponsePayload {
  session_id: string;
  reply: string;
  metadata: MessageMetadata;
}

export interface HealthStatus {
  status: string;
  keys_configured: number;
  cache_enabled: boolean;
}

export interface SessionSummary {
  session_id: string;
  title: string;
  updated_at: string;
  message_count: number;
  system_prompt: string | null;
}

export interface SessionMessage {
  role: 'user' | 'assistant';
  content: string;
  metadata?: MessageMetadata;
}

export interface SessionMessagesResponse {
  session_id: string;
  messages: SessionMessage[];
}
