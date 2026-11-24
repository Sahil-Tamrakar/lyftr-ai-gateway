import React from 'react';
import { HealthStatus, SessionSummary } from '../types/chat';

interface Props {
  sessionId: string;
  sessions: SessionSummary[];
  onNewSession: () => void;
  onSelectSession: (id: string) => void;
  health: HealthStatus | null;
}

function formatSessionDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export const Sidebar: React.FC<Props> = ({ sessionId, sessions, onNewSession, onSelectSession, health }) => {
  return (
    <aside className="w-64 bg-[#171717] border-r border-[#262626] flex flex-col p-3 select-none">
      <div className="flex flex-col flex-1 min-h-0">
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
          </nav>
        </div>

        <div className="mt-4 flex flex-1 min-h-0 flex-col">
          <div className="px-3 pb-2 text-[10px] font-semibold tracking-wider uppercase text-[#52525b]">
            Recent Chats
          </div>
          <div className="flex-1 overflow-y-auto space-y-1 pr-1">
            {sessions.length === 0 ? (
              <p className="px-3 py-2 text-[11px] text-[#52525b]">No conversations yet.</p>
            ) : (
              sessions.map((session) => {
                const active = session.session_id === sessionId;
                return (
                  <button
                    key={session.session_id}
                    onClick={() => onSelectSession(session.session_id)}
                    title={session.title || 'Untitled session'}
                    className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                      active
                        ? 'bg-[#2a2a2a] text-white'
                        : 'text-[#a1a1aa] hover:bg-[#212121]'
                    }`}
                  >
                    <div className="truncate text-xs font-medium">
                      {session.title || 'Untitled session'}
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-[10px] text-[#52525b] font-mono">
                      <span>{formatSessionDate(session.updated_at)}</span>
                      <span>•</span>
                      <span>{session.message_count} {session.message_count === 1 ? 'msg' : 'msgs'}</span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
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
      </div>
    </aside>
  );
};
