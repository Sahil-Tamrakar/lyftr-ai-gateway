import { useState } from "react";
import { ChevronDownIcon, TerminalIcon } from "./icons";

interface SystemPromptBarProps {
  value: string;
  onChange: (value: string) => void;
}

export function SystemPromptBar({ value, onChange }: SystemPromptBarProps) {
  const [open, setOpen] = useState(true);
  const isActive = value.trim().length > 0;

  return (
    <div className="overflow-hidden rounded-xl border border-white/[0.07] bg-ink-900/60 backdrop-blur">
      <button
        type="button"
        onClick={() => setOpen((previous) => !previous)}
        aria-expanded={open}
        aria-controls="system-prompt-body"
        className="flex w-full items-center gap-2 px-3.5 py-2.5 text-left transition hover:bg-white/[0.02]"
      >
        <TerminalIcon className="h-3.5 w-3.5 text-slate-500" />
        <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-slate-400">
          System prompt
        </span>
        <span
          className={[
            "rounded-full border px-1.5 py-px text-[9px] uppercase tracking-wider",
            isActive
              ? "border-emerald-400/25 bg-emerald-400/[0.07] text-emerald-300"
              : "border-white/10 bg-white/[0.03] text-slate-500",
          ].join(" ")}
        >
          {isActive ? "active" : "optional"}
        </span>
        <ChevronDownIcon
          className={[
            "ml-auto h-3.5 w-3.5 text-slate-500 transition-transform duration-200",
            open ? "rotate-180" : "",
          ].join(" ")}
        />
      </button>

      {open ? (
        <div id="system-prompt-body" className="border-t border-white/[0.06] px-3.5 py-3">
          <textarea
            data-testid="system-prompt-input"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            rows={2}
            spellCheck={false}
            placeholder="You are a senior engineer. Answer concisely with production-ready guidance."
            aria-label="System prompt"
            className="block w-full resize-y rounded-lg border border-white/[0.07] bg-black/25 px-3 py-2 font-mono text-[12px] leading-relaxed text-slate-200 placeholder:text-slate-600 focus:border-sky-400/30 focus:outline-none focus:ring-1 focus:ring-sky-400/20"
          />
          <p className="mt-1.5 text-[10px] leading-relaxed text-slate-600">
            Applied to every turn in this session and persisted only after a successful
            reply. Clear the field to remove it.
          </p>
        </div>
      ) : null}
    </div>
  );
}
