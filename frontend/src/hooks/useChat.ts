import { useState, useEffect, useCallback } from 'react';
import { ChatMessage, HealthStatus, SessionSummary } from '../types/chat';
import {
  checkHealth,
  fetchSessionMessages,
  fetchSessions,
  sendChatMessage,
} from '../api/client';

const DEFAULT_SYSTEM_PROMPT =
  'You are a senior engineer. Answer concisely with production-ready guidance.';

export function useChat() {
  const [sessionId, setSessionId] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [systemPrompt, setSystemPrompt] = useState<string>(DEFAULT_SYSTEM_PROMPT);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadingSession, setIsLoadingSession] = useState<boolean>(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await fetchSessions());
    } catch {
      // History is optional; keep the last known list on failure.
    }
  }, []);

  const initNewSession = useCallback(() => {
    const id = 'sess_' + Math.random().toString(36).substring(2, 10);
    setSessionId(id);
    setMessages([]);
    setSystemPrompt(DEFAULT_SYSTEM_PROMPT);
  }, []);

  useEffect(() => {
    initNewSession();
    checkHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
    refreshSessions();
  }, [initNewSession, refreshSessions]);

  const selectSession = useCallback(
    async (id: string) => {
      if (!id || id === sessionId || isLoading || isLoadingSession) return;

      setIsLoadingSession(true);
      try {
        const response = await fetchSessionMessages(id);
        setSessionId(id);
        setMessages(
          response.messages.map((message) => ({
            role: message.role,
            content: message.content,
            metadata: message.metadata,
          }))
        );

        const summary = sessions.find((session) => session.session_id === id);
        setSystemPrompt(summary?.system_prompt ?? '');
      } catch (err: any) {
        setSessionId(id);
        setMessages([
          {
            role: 'error',
            content: err.message || 'Could not load this session.',
            status_code: err.status || 500,
          },
        ]);
        setSystemPrompt('');
      } finally {
        setIsLoadingSession(false);
      }
    },
    [sessionId, isLoading, isLoadingSession, sessions]
  );

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isLoading || isLoadingSession) return;

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
      void refreshSessions();
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
    sessions,
    initNewSession,
    selectSession,
    messages,
    systemPrompt,
    setSystemPrompt,
    isLoading: isLoading || isLoadingSession,
    health,
    sendMessage,
  };
}
