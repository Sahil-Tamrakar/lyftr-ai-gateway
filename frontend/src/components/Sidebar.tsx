import React from 'react';
import { HealthStatus } from '../types/chat';

interface Props {
  sessionId: string;
  onNewSession: () => void;
  health: HealthStatus | null;
}

export const Sidebar: React.FC<Props> = ({ sessionId, onNewSession, health }) => {
  return (
    <aside className="w-64 bg-[#171717] border-r border-[#262626] flex flex-col justify-between p-3 select-none">
      <div className="space-y-4">
        <div className="flex items-center gap-2.5 px-3 py-2 text-white font-semibold text-sm">
          <div className="w-6 h-6 rounded-md bg-[#10a37f]/20 border border-[#10a37f]/40 flex items-center justify-center text-[#10a37f]">
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <span>LLM Gateway</span>
        </div>

        <button
          onClick={onNewSession}
          className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-[#212121] hover:bg-[#2a2a2a] text-[#d4d4d8] text-xs font-medium border border-[#2f2f2f] transition-colors"
        >
          <div className="flex items-center gap-2">
            <svg className="w-3.5 h-3.5 text-[#10a37f]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
            </svg>
            <span>New Session</span>
          </div>
          <kbd className="text-[10px] text-[#71717a] font-mono">⌘K</kbd>
        </button>

        <nav className="space-y-1">
          <div className="px-3 py-2 rounded-lg bg-[#212121] text-white text-xs font-medium flex items-center gap-2.5">
            <svg className="w-4 h-4 text-[#10a37f]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            <span>Chat Console</span>
          </div>
          <div className="px-3 py-2 rounded-lg hover:bg-[#212121] text-[#a1a1aa] text-xs font-medium flex items-center gap-2.5 cursor-pointer transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span>Gateway Health</span>
          </div>
          <div className="px-3 py-2 rounded-lg hover:bg-[#212121] text-[#a1a1aa] text-xs font-medium flex items-center gap-2.5 cursor-pointer transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>Session Logs</span>
          </div>
        </nav>
      </div>

      <div className="space-y-3 pt-3 border-t border-[#262626] font-mono text-[11px]">
        <div className="bg-[#1f1f1f] rounded-lg p-2.5 space-y-2 border border-[#2a2a2a]">
          <div className="flex items-center justify-between">
            <span className="text-[#71717a]">GATEWAY HEALTH</span>
            <span className="flex items-center gap-1.5 text-[#10a37f] font-semibold text-[10px]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#10a37f] animate-pulse" />
              {health?.status ? health.status.toUpperCase() : 'ONLINE'}
            </span>
          </div>
          <div className="flex items-center gap-2 text-[#a1a1aa]">
            <span className="bg-[#2a2a2a] px-1.5 py-0.5 rounded text-[10px]">
              {health ? `${health.keys_configured} KEYS` : '2 KEYS'}
            </span>
            <span className="bg-[#2a2a2a] px-1.5 py-0.5 rounded text-[10px] text-[#38bdf8]">
              {health?.cache_enabled ? 'CACHE ON' : 'CACHE ON'}
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between px-1 text-[11px]">
          <span className="text-[#52525b]">SESSION</span>
          <span className="text-[#a1a1aa] font-medium">{sessionId}</span>
        </div>
      </div>
    </aside>
  );
};
