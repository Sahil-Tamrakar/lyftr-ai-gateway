import React, { useState } from 'react';
import { ChatMessage } from '../types/chat';
import { TelemetryBadge } from './TelemetryBadge';

export const MessageItem: React.FC<{ message: ChatMessage }> = ({ message }) => {
  const [copied, setCopied] = useState(false);

  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-6">
        <div className="max-w-[85%] bg-[#2f2f2f] text-[#ececec] px-4 py-2.5 rounded-2xl rounded-tr-sm text-sm leading-relaxed shadow-sm">
          {message.content}
        </div>
      </div>
    );
  }

  if (message.role === 'error') {
    return (
      <div className="flex items-start gap-4 mb-6">
        <div className="w-8 h-8 rounded-full bg-rose-950/60 border border-rose-800 flex items-center justify-center shrink-0 text-rose-400 text-sm font-bold">
          !
        </div>
        <div className="flex-1 bg-rose-950/30 border border-rose-900/50 rounded-xl p-3 text-rose-300 text-sm">
          <div className="font-semibold text-rose-400 text-xs mb-1 uppercase tracking-wider">
            HTTP {message.status_code || 500} Error
          </div>
          <p>{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="assistant-message" className="flex items-start gap-4 mb-8">
      <div className="w-8 h-8 rounded-full bg-[#10a37f]/15 border border-[#10a37f]/30 flex items-center justify-center shrink-0 text-[#10a37f]">
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="3" />
          <path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10l2 2M5 19l2-2m10-10l2-2" />
        </svg>
      </div>

      <div className="flex-1 min-w-0 space-y-3">
        <div className="text-[#ececec] text-sm leading-relaxed whitespace-pre-wrap font-sans">
          {message.content}
        </div>

        {message.metadata && <TelemetryBadge metadata={message.metadata} />}
      </div>
    </div>
  );
};
