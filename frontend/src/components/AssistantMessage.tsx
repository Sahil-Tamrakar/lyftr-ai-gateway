import { useState, type ReactNode } from "react";
import type { MessageMetadata } from "../types";
import { Markdown } from "./Markdown";
import {
  ArrowDownIcon,
  ArrowUpIcon,
  BoltIcon,
  CheckIcon,
  ClockIcon,
  CopyIcon,
  CpuIcon,
  KeyIcon,
} from "./icons";

function MetaItem({
  icon,
  label,
  title,
  children,
}: {
  icon: ReactNode;
  label: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <span className="inline-flex items-center gap-1.5" title={title}>
      {icon}
      <span className="text-slate-600">{label}</span>
      {children}
    </span>
  );
}

export function AssistantMessage({
  content,
  metadata,
}: {
  content: string;
  metadata: MessageMetadata;
}) {
  const [copied, setCopied] = useState(false);
  const isCache = metadata.resolution_source === "LLM_CACHE";

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard permissions are not available; fail silently.
    }
  }

  return (
    <article
      data-testid="assistant-message"
      className="animate-fade-up overflow-hidden rounded-xl border border-white/[0.07] bg-white/[0.02] shadow-lg shadow-black/20"
    >
      <div className="flex items-center justify-between gap-3 border-b border-white/[0.05] px-3.5 py-2 sm:px-4">
        <div className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.18em] text-slate-500">
          <span className="flex h-5 w-5 items-center justify-center rounded-md border border-emerald-400/20 bg-emerald-400/[0.08] text-emerald-300">
            <BoltIcon className="h-3 w-3" />
          </span>
          Assistant
        </div>
        <span
          data-testid="meta-source"
          className={[
            "rounded-full border px-2 py-0.5 font-mono text-[9.5px] font-medium tracking-[0.08em]",
            isCache
              ? "border-sky-400/25 bg-sky-400/[0.07] text-sky-300"
              : "border-emerald-400/25 bg-emerald-400/[0.07] text-emerald-300",
          ].join(" ")}
        >
          {metadata.resolution_source}
        </span>
      </div>

      <div className="px-3.5 py-3 sm:px-4">
        <Markdown content={content} />
      </div>

      <div className="flex flex-wrap items-center gap-x-3.5 gap-y-2 border-t border-white/[0.05] bg-black/20 px-3.5 py-2.5 text-[10.5px] text-slate-400 sm:px-4">
        <MetaItem
          icon={<CpuIcon className="h-3 w-3 text-slate-600" />}
          label="model"
          title="Model used for this response"
        >
          <span
            data-testid="meta-model"
            className="font-mono text-[10px] text-slate-300"
          >
            {metadata.model}
          </span>
        </MetaItem>

        <MetaItem
          icon={<ClockIcon className="h-3 w-3 text-slate-600" />}
          label="latency"
          title="Time spent producing this response"
        >
          <span data-testid="meta-latency" className="font-mono text-slate-300">
            {metadata.latency_ms} ms
          </span>
        </MetaItem>

        <MetaItem
          icon={<ArrowDownIcon className="h-3 w-3 text-slate-600" />}
          label="in"
          title="Input tokens for this request only"
        >
          <span
            data-testid="meta-input-tokens"
            className="font-mono text-slate-300"
          >
            {metadata.input_tokens}
          </span>
        </MetaItem>

        <MetaItem
          icon={<ArrowUpIcon className="h-3 w-3 text-slate-600" />}
          label="out"
          title="Output tokens for this request only"
        >
          <span
            data-testid="meta-output-tokens"
            className="font-mono text-slate-300"
          >
            {metadata.output_tokens}
          </span>
        </MetaItem>

        <MetaItem
          icon={<KeyIcon className="h-3 w-3 text-slate-600" />}
          label="key"
          title="Provider identity that served the request"
        >
          <span
            data-testid="meta-key-id"
            className="font-mono text-slate-300"
          >
            {metadata.key_id ?? "shared cache"}
          </span>
        </MetaItem>

        {metadata.fallback_attempts > 0 ? (
          <span
            data-testid="meta-fallback"
            className="rounded-full border border-amber-400/25 bg-amber-400/[0.07] px-2 py-0.5 font-mono text-[9.5px] text-amber-300"
          >
            fallback ×{metadata.fallback_attempts}
          </span>
        ) : null}

        <button
          type="button"
          onClick={handleCopy}
          title="Copy response"
          aria-label="Copy response"
          className="ml-auto inline-flex items-center gap-1 rounded-md border border-white/[0.06] px-1.5 py-1 text-slate-500 transition hover:border-white/15 hover:text-slate-300"
        >
          {copied ? (
            <CheckIcon className="h-3 w-3 text-emerald-400" />
          ) : (
            <CopyIcon className="h-3 w-3" />
          )}
          <span className="text-[9.5px] uppercase tracking-wider">
            {copied ? "copied" : "copy"}
          </span>
        </button>
      </div>
    </article>
  );
}
