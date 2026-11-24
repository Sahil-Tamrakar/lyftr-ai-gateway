import { useState, useEffect, useCallback } from 'react';
import { ChatMessage, HealthStatus } from '../types/chat';
import { sendChatMessage, checkHealth } from '../api/client';

export function useChat() {
  const [sessionId, setSessionId] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [systemPrompt, setSystemPrompt] = useState<string>(
    'You are a senior engineer. Answer concisely with production-ready guidance.'
  );
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  const initNewSession = useCallback(() => {
    const id = 'sess_' + Math.random().toString(36).substring(2, 10);
    setSessionId(id);
    setMessages([]);
  }, []);

  useEffect(() => {
    initNewSession();
    checkHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, [initNewSession]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;

    // Add user message to state
    const userMsg: ChatMessage = { role: 'user', content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const resp = await sendChatMessage({
        session_id: sessionId,
        message: trimmed,
        system_prompt: systemPrompt.trim(),
      });

      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: resp.reply,
        metadata: resp.metadata,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        role: 'error',
        content: err.message || 'An unexpected error occurred.',
        status_code: err.status || 500,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    sessionId,
    initNewSession,
    messages,
    systemPrompt,
    setSystemPrompt,
    isLoading,
    health,
    sendMessage,
  };
}
