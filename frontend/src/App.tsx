import { useEffect, useRef, useState } from "react";
import { ChatApiError, fetchHealth, sendChat } from "./api";
import { AssistantMessage } from "./components/AssistantMessage";
import { Composer } from "./components/Composer";
import { SystemPromptBar } from "./components/SystemPromptBar";
import {
  ActivityIcon,
  AlertIcon,
  BoltIcon,
  CheckIcon,
  CopyIcon,
  DatabaseIcon,
  KeyIcon,
} from "./components/icons";
import type { ChatMessage, HealthStatus } from "./types";

function newId(): string {
  const random = globalThis.crypto?.randomUUID?.();
  return random ?? `id-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function createSessionId(): string {
  const random =
    globalThis.crypto?.randomUUID?.().replace(/-/g, "") ??
    `${Date.now()}${Math.random().toString(36).slice(2)}`;
  return `s-${random.slice(0, 8)}`;
}

const EXAMPLE_PROMPTS = [
  "Explain key failover in one paragraph.",
  "Write a Python retry decorator with exponential backoff.",
  "Summarize how SQLite WAL mode improves concurrency.",
];

function EmptyState({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="flex h-full min-h-[300px] flex-col items-center justify-center px-4 text-center">
      <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl border border-emerald-400/20 bg-emerald-400/[0.07] text-emerald-300 shadow-lg shadow-emerald-500/5">
        <ActivityIcon className="h-5 w-5" />
      </div>
      <h2 className="text-[13.5px] font-medium tracking-tight text-slate-200">
        Start a session
      </h2>
      <p className="mt-1.5 max-w-sm text-[11.5px] leading-relaxed text-slate-500">
        Requests walk an ordered key pool with automatic failover. Identical prompts
        return instantly from cache with preserved token counts.
      </p>
      <div className="mt-5 flex flex-wrap justify-center gap-2">
        {EXAMPLE_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onPick(prompt)}
            className="rounded-full border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 text-[10.5px] text-slate-400 transition hover:border-white/20 hover:bg-white/[0.05] hover:text-slate-200"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

function LoadingRow() {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3">
      <div className="flex items-end gap-1">
        {[0, 1, 2].map((index) => (
          <span
            key={index}
            className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-emerald-400"
            style={{ animationDelay: `${index * 160}ms` }}
          />
        ))}
      </div>
      <span className="text-[11.5px] text-slate-400">
        Routing request through the key pool…
      </span>
    </div>
  );
}

export default function App() {
  const [sessionId] = useState(createSessionId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthChecked, setHealthChecked] = useState(false);
  const [sessionCopied, setSessionCopied] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((status) => {
        if (!cancelled) {
          setHealth(status);
          setHealthChecked(true);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHealth(null);
          setHealthChecked(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (messages.length === 0 && !loading) return;
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  async function handleSend() {
    const text = draft.trim();
    if (!text || loading) return;

    // Clear the composer immediately, before the network round-trip.
    setDraft("");
    setMessages((previous) => [
      ...previous,
      { id: newId(), role: "user", content: text },
    ]);
    setLoading(true);

    try {
      const response = await sendChat({
        session_id: sessionId,
        message: text,
        system_prompt: systemPrompt,
      });
      setMessages((previous) => [
        ...previous,
        {
          id: newId(),
          role: "assistant",
          content: response.reply,
          metadata: response.metadata,
        },
      ]);
    } catch (error) {
      const apiError =
        error instanceof ChatApiError
          ? error
          : new ChatApiError(
              0,
              "Something went wrong while contacting the API.",
              "Unexpected error",
            );
      setMessages((previous) => [
        ...previous,
        {
          id: newId(),
          role: "error",
          content: apiError.message,
          errorTitle: apiError.title,
          status: apiError.status || undefined,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleCopySession() {
    try {
      await navigator.clipboard.writeText(sessionId);
      setSessionCopied(true);
      window.setTimeout(() => setSessionCopied(false), 1500);
    } catch {
      // Clipboard access is optional.
    }
  }

  const statusLabel = health
    ? "online"
    : healthChecked
      ? "offline"
      : "checking";
  const statusTone =
    statusLabel === "online"
      ? "border-emerald-400/20 bg-emerald-400/[0.06] text-emerald-300"
      : statusLabel === "offline"
        ? "border-rose-400/20 bg-rose-400/[0.06] text-rose-300"
        : "border-amber-400/20 bg-amber-400/[0.06] text-amber-300";
  const dotTone =
    statusLabel === "online"
      ? "bg-emerald-400"
      : statusLabel === "offline"
        ? "bg-rose-400"
        : "bg-amber-400 animate-pulse";

  const turns = messages.filter((message) => message.role === "assistant").length;

  return (
    <div className="relative flex h-screen min-h-0 flex-col overflow-hidden">
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute -top-48 left-1/2 h-[460px] w-[760px] -translate-x-1/2 rounded-full bg-emerald-500/[0.05] blur-3xl" />
        <div className="absolute -bottom-32 right-0 h-[340px] w-[520px] rounded-full bg-sky-500/[0.04] blur-3xl" />
      </div>

      <header className="relative z-10 shrink-0 border-b border-white/[0.06] bg-ink-950/70 backdrop-blur-xl">
        <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between gap-3 px-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-emerald-400/25 bg-gradient-to-br from-emerald-400/20 to-sky-500/10 text-emerald-300 shadow-lg shadow-emerald-500/10">
              <BoltIcon className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <h1 className="truncate text-[14.5px] font-semibold tracking-tight text-slate-100">
                LLM Gateway
              </h1>
              <p className="truncate text-[9.5px] uppercase tracking-[0.2em] text-slate-500">
                Observability console
              </p>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <div className="hidden items-center gap-1.5 lg:flex">
              <span
                data-testid="health-status"
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[9.5px] font-medium uppercase tracking-[0.12em] ${statusTone}`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${dotTone}`} />
                {statusLabel}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.07] bg-white/[0.02] px-2.5 py-1 text-[9.5px] uppercase tracking-[0.12em] text-slate-400">
                <KeyIcon className="h-3 w-3 text-slate-500" />
                {health ? health.keys_configured : "–"} keys
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.07] bg-white/[0.02] px-2.5 py-1 text-[9.5px] uppercase tracking-[0.12em] text-slate-400">
                <DatabaseIcon className="h-3 w-3 text-slate-500" />
                cache {health?.cache_enabled ? "on" : "off"}
              </span>
            </div>

            <div className="flex items-center gap-1.5 rounded-lg border border-white/[0.07] bg-white/[0.03] py-1 pl-2.5 pr-1">
              <span className="hidden text-[9px] uppercase tracking-[0.16em] text-slate-500 sm:inline">
                Session
              </span>
              <span className="font-mono text-[10.5px] text-slate-300">
                {sessionId}
              </span>
              <button
                type="button"
                onClick={handleCopySession}
                aria-label="Copy session id"
                title="Copy session id"
                className="rounded p-1 text-slate-500 transition hover:bg-white/[0.06] hover:text-slate-200"
              >
                {sessionCopied ? (
                  <CheckIcon className="h-3 w-3 text-emerald-400" />
                ) : (
                  <CopyIcon className="h-3 w-3" />
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto flex min-h-0 w-full max-w-5xl flex-1 flex-col gap-3 px-3 py-3 sm:px-6 sm:py-4">
        <SystemPromptBar value={systemPrompt} onChange={setSystemPrompt} />

        <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-white/[0.07] bg-ink-900/50 shadow-2xl shadow-black/40 backdrop-blur-sm">
          <div className="flex shrink-0 items-center justify-between border-b border-white/[0.06] px-3.5 py-2 sm:px-4">
            <span className="text-[9.5px] uppercase tracking-[0.2em] text-slate-500">
              Conversation
            </span>
            <span className="text-[9.5px] uppercase tracking-[0.14em] text-slate-600">
              {turns} {turns === 1 ? "reply" : "replies"}
            </span>
          </div>

          <div
            data-testid="chat-stream"
            className="chat-scroll flex-1 space-y-4 overflow-y-auto px-3 py-4 sm:px-5"
          >
            {messages.length === 0 && !loading ? (
              <EmptyState onPick={setDraft} />
            ) : null}

            {messages.map((message) => {
              if (message.role === "user") {
                return (
                  <div
                    key={message.id}
                    className="flex animate-fade-up flex-col items-end gap-1"
                  >
                    <span className="pr-1 text-[9px] uppercase tracking-[0.18em] text-slate-600">
                      You
                    </span>
                    <div className="max-w-[86%] whitespace-pre-wrap rounded-2xl rounded-tr-sm border border-indigo-400/20 bg-indigo-500/[0.11] px-3.5 py-2.5 text-[13px] leading-relaxed text-slate-100">
                      {message.content}
                    </div>
                  </div>
                );
              }

              if (message.role === "error") {
                return (
                  <div
                    key={message.id}
                    data-testid="error-message"
                    role="alert"
                    className="animate-fade-up rounded-xl border border-rose-500/25 bg-rose-500/[0.07] px-3.5 py-3"
                  >
                    <div className="flex items-start gap-2.5">
                      <AlertIcon className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-[11px] font-semibold uppercase tracking-wider text-rose-200">
                            {message.errorTitle ?? "Request failed"}
                          </p>
                          {message.status ? (
                            <span className="rounded border border-rose-400/30 px-1.5 py-px font-mono text-[9.5px] text-rose-300">
                              HTTP {message.status}
                            </span>
                          ) : null}
                        </div>
                        <p className="mt-1 break-words text-[12px] leading-relaxed text-rose-100/80">
                          {message.content}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              }

              return message.metadata ? (
                <AssistantMessage
                  key={message.id}
                  content={message.content}
                  metadata={message.metadata}
                />
              ) : null;
            })}

            {loading ? <LoadingRow /> : null}
            <div ref={bottomRef} />
          </div>

          <div className="shrink-0 border-t border-white/[0.06] bg-black/10 p-2.5 sm:p-3.5">
            <Composer
              value={draft}
              loading={loading}
              onChange={setDraft}
              onSend={handleSend}
            />
          </div>
        </section>

        <p className="shrink-0 text-center text-[9.5px] tracking-wide text-slate-600">
          Live inference failover · deterministic response cache · SQLite session
          history
        </p>
      </main>
    </div>
  );
}
