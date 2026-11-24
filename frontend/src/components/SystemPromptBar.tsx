import React, { useState } from 'react';

interface Props {
  systemPrompt: string;
  setSystemPrompt: (val: string) => void;
}

export const SystemPromptBar: React.FC<Props> = ({ systemPrompt, setSystemPrompt }) => {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div className="mb-6 rounded-xl border border-[#2d2d2d] bg-[#1a1a1a]/80 backdrop-blur-sm overflow-hidden transition-all">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-xs text-[#a1a1aa] hover:text-[#ececec] hover:bg-[#242424] transition-colors"
      >
        <div className="flex items-center gap-2 font-mono">
          <svg className="w-3.5 h-3.5 text-[#10a37f]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
          </svg>
          <span className="font-semibold tracking-wide uppercase text-[11px]">System Prompt</span>
          <span className="px-1.5 py-0.2 rounded bg-[#10a37f]/20 text-[#10a37f] text-[10px] font-bold">
            ACTIVE
          </span>
        </div>
        <svg
          className={`w-3.5 h-3.5 transform transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="p-3 border-t border-[#262626]">
          <textarea
            data-testid="system-prompt-input"
            rows={2}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="Set session system instructions..."
            className="w-full bg-[#121212] border border-[#2e2e2e] focus:border-[#10a37f] rounded-lg p-2.5 text-xs font-mono text-[#d4d4d8] placeholder-[#52525b] outline-none transition-colors resize-none"
          />
        </div>
      )}
    </div>
  );
};
