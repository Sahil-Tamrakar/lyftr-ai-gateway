import { useEffect, useRef, type KeyboardEvent } from "react";
import { SendIcon } from "./icons";

interface ComposerProps {
  value: string;
  loading: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
}

export function Composer({ value, loading, onChange, onSend }: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 176)}px`;
  }, [value]);

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      onSend();
    }
  }

  return (
    <div className="rounded-xl border border-white/[0.08] bg-ink-850/80 shadow-inner shadow-black/20 transition focus-within:border-emerald-400/30 focus-within:ring-1 focus-within:ring-emerald-400/20">
      <textarea
        ref={textareaRef}
        data-testid="chat-input"
        value={value}
        rows={1}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask anything — the gateway routes, caches and fails over."
        aria-label="Chat message"
        className="block max-h-44 min-h-[46px] w-full resize-none bg-transparent px-3.5 pb-1 pt-3 text-[13.5px] leading-relaxed text-slate-100 placeholder:text-slate-600 focus:outline-none"
      />
      <div className="flex items-center justify-between gap-3 px-2.5 pb-2 pl-3.5">
        <span className="hidden text-[10px] tracking-wide text-slate-600 sm:block">
          <kbd className="rounded border border-white/10 bg-white/[0.04] px-1 py-0.5 font-mono text-[9.5px] text-slate-400">
            Enter
          </kbd>{" "}
          send ·{" "}
          <kbd className="rounded border border-white/10 bg-white/[0.04] px-1 py-0.5 font-mono text-[9.5px] text-slate-400">
            Shift + Enter
          </kbd>{" "}
          newline
        </span>
        <span className="text-[10px] text-slate-600 sm:hidden">
          {value.trim().length}/4000
        </span>
        <button
          type="button"
          data-testid="send-button"
          onClick={onSend}
          disabled={loading}
          aria-label="Send message"
          className="ml-auto inline-flex h-8 w-8 items-center justify-center rounded-lg border border-emerald-400/30 bg-emerald-400/15 text-emerald-300 transition hover:bg-emerald-400/25 hover:text-emerald-200 disabled:cursor-not-allowed disabled:border-white/10 disabled:bg-white/[0.04] disabled:text-slate-500"
        >
          {loading ? (
            <svg
              viewBox="0 0 24 24"
              className="h-3.5 w-3.5 animate-spin"
              fill="none"
              stroke="currentColor"
              strokeWidth={2.2}
            >
              <path d="M21 12a9 9 0 1 1-6.2-8.6" strokeLinecap="round" />
            </svg>
          ) : (
            <SendIcon className="h-3.5 w-3.5" />
          )}
        </button>
      </div>
    </div>
  );
}
