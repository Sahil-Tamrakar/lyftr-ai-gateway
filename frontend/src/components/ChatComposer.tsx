import React, { useState, useRef, useEffect } from 'react';

interface Props {
  onSend: (text: string) => void;
  isLoading: boolean;
}

export const ChatComposer: React.FC<Props> = ({ onSend, isLoading }) => {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [text]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (!text.trim() || isLoading) return;
    const msg = text;
    setText('');
    onSend(msg);
  };

  return (
    <div className="relative flex items-center bg-[#2f2f2f] rounded-3xl border border-[#3e3e3e] shadow-lg focus-within:border-[#52525b] transition-all px-4 py-2">
      <textarea
        ref={textareaRef}
        data-testid="chat-input"
        rows={1}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask anything — the gateway routes, caches, and fails over..."
        className="w-full bg-transparent text-[#ececec] placeholder-[#71717a] text-sm outline-none resize-none max-h-40 py-1.5 leading-relaxed"
      />

      <button
        data-testid="send-button"
        onClick={handleSend}
        disabled={isLoading || !text.trim()}
        className={`ml-2 w-9 h-9 rounded-full flex items-center justify-center transition-all shrink-0 ${
          text.trim() && !isLoading
            ? 'bg-[#10a37f] text-white hover:bg-[#0e8e6e] shadow-md'
            : 'bg-[#404040] text-[#71717a] cursor-not-allowed'
        }`}
      >
        {isLoading ? (
          <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
        ) : (
          <svg className="w-4 h-4 transform rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 19V5m0 0l-7 7m7-7l7 7" />
          </svg>
        )}
      </button>
    </div>
  );
};
