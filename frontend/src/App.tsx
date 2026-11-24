import React from 'react';
import { Sidebar } from './components/Sidebar';
import { SystemPromptBar } from './components/SystemPromptBar';
import { MessageItem } from './components/MessageItem';
import { ChatComposer } from './components/ChatComposer';
import { useChat } from './hooks/useChat';

export function App() {
  const {
    sessionId,
    initNewSession,
    messages,
    systemPrompt,
    setSystemPrompt,
    isLoading,
    health,
    sendMessage,
  } = useChat();

  return (
    <div className="flex h-screen bg-[#212121] text-[#ececec] overflow-hidden antialiased">
      <Sidebar sessionId={sessionId} onNewSession={initNewSession} health={health} />

      <div className="flex-1 flex flex-col min-w-0 h-full relative">
        <header className="h-14 border-b border-[#2d2d2d] flex items-center justify-between px-6 bg-[#212121]/90 backdrop-blur-sm z-10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-[#ececec]">LLM Gateway</span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#10a37f]/10 text-[#10a37f] border border-[#10a37f]/30 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#10a37f]" />
              LIVE
            </span>
          </div>
          <div className="w-8 h-8 rounded-full bg-[#10a37f]/20 border border-[#10a37f]/40 flex items-center justify-center text-[#10a37f] text-xs font-semibold">
            AG
          </div>
        </header>

        <main className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto">
            <SystemPromptBar
              systemPrompt={systemPrompt}
              setSystemPrompt={setSystemPrompt}
            />

            {messages.length === 0 ? (
              <div className="h-96 flex flex-col items-center justify-center text-center text-[#71717a] space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-[#2a2a2a] border border-[#333] flex items-center justify-center text-[#10a37f]">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-[#d4d4d8]">Ready for Inference</h3>
                  <p className="text-xs text-[#71717a] mt-1">
                    Deterministic caching enabled • Auto key pool failover on 429/5xx
                  </p>
                </div>
              </div>
            ) : (
              messages.map((msg, index) => <MessageItem key={index} message={msg} />)
            )}
          </div>
        </main>

        <footer className="shrink-0 p-4 pb-6 bg-gradient-to-t from-[#212121] via-[#212121] to-transparent">
          <div className="max-w-3xl mx-auto">
            <ChatComposer onSend={sendMessage} isLoading={isLoading} />
            <div className="mt-2 text-center text-[11px] text-[#71717a] font-mono">
              Live inference failover • Deterministic response cache • SQLite session history
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default App;
