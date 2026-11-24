import React from 'react';
import { MessageMetadata } from '../types/chat';

interface Props {
  metadata: MessageMetadata;
}

export const TelemetryBadge: React.FC<Props> = ({ metadata }) => {
  const isCache = metadata.resolution_source === 'LLM_CACHE';

  return (
    <div className="flex flex-wrap items-center gap-2 pt-2 text-xs font-mono text-[#a1a1aa]">
      <span
        data-testid="meta-source"
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold tracking-wide uppercase border ${
          isCache
            ? 'bg-[#0284c7]/10 text-[#38bdf8] border-[#0284c7]/30'
            : 'bg-[#10a37f]/10 text-[#10a37f] border-[#10a37f]/30'
        }`}
      >
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            isCache ? 'bg-[#38bdf8]' : 'bg-[#10a37f]'
          }`}
        />
        {metadata.resolution_source}
      </span>

      <span className="text-[#52525b]">/</span>

      <span data-testid="meta-model" className="text-[#d4d4d8]">
        {metadata.model}
      </span>

      <span className="text-[#52525b]">•</span>

      <span data-testid="meta-latency" className="text-[#a1a1aa]">
        {metadata.latency_ms} ms
      </span>

      <span className="text-[#52525b]">•</span>

      <div className="flex items-center gap-1 text-[#71717a]">
        <span>IN</span>
        <span data-testid="meta-input-tokens" className="text-[#e4e4e7] font-medium">
          {metadata.input_tokens}
        </span>
        <span className="ml-1">OUT</span>
        <span data-testid="meta-output-tokens" className="text-[#e4e4e7] font-medium">
          {metadata.output_tokens}
        </span>
      </div>

      {metadata.key_id && (
        <>
          <span className="text-[#52525b]">•</span>
          <span className="text-[#71717a]">{metadata.key_id}</span>
        </>
      )}

      {metadata.fallback_attempts > 0 && (
        <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px]">
          {metadata.fallback_attempts} fallback{metadata.fallback_attempts > 1 ? 's' : ''}
        </span>
      )}
    </div>
  );
};
