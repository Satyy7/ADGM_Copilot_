"use client";
import { useState, useRef, useEffect } from "react";
import { Send, RotateCcw, BookOpen, Sparkles, Clock } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import TopBar from "@/components/layout/TopBar";
import { sendChatMessage } from "@/lib/api";
import type { ChatMessage, CitationSource } from "@/types";
import { collectionBadgeColor, truncate, formatLatency } from "@/lib/utils";

const SUGGESTIONS = [
  "What are the UBO beneficial ownership disclosure requirements in ADGM?",
  "What documents are needed to incorporate an ADGM private company?",
  "What are the annual filing obligations for an ADGM company?",
  "Explain the employment contract probation period rules under ADGM.",
];

function TypingIndicator() {
  return (
    <div className="flex items-end gap-3">
      <div className="w-8 h-8 rounded-xl bg-amber-100 border border-amber-200 flex items-center justify-center flex-shrink-0">
        <Sparkles size={13} className="text-amber-600" />
      </div>
      <div className="card px-4 py-3 flex items-center gap-1.5 rounded-bl-sm">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  );
}

function CitationChip({ source }: { source: CitationSource }) {
  const bg = collectionBadgeColor(source.collection);
  return (
    <div
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] border cursor-default hover:opacity-80 transition-opacity"
      style={{ background: bg, borderColor: "var(--border)", color: "var(--text-2)" }}
      title={source.rule_reference ?? source.source_title}
    >
      <BookOpen size={9} className="flex-shrink-0 opacity-60" />
      <span className="font-medium truncate max-w-[150px]">{source.source_title}</span>
      {source.rule_reference && (
        <span className="text-amber-600 text-[10px] font-semibold">{source.rule_reference}</span>
      )}
    </div>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex items-end gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-xs font-bold ${
          isUser
            ? "text-white"
            : "bg-amber-100 border border-amber-200 text-amber-700"
        }`}
        style={isUser ? { background: "linear-gradient(135deg,#D97706,#92400E)" } : {}}
      >
        {isUser ? "U" : <Sparkles size={13} />}
      </div>

      {/* Content */}
      <div className={`max-w-[78%] flex flex-col gap-1.5 ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
            isUser
              ? "text-white rounded-br-sm"
              : "card rounded-bl-sm"
          }`}
          style={isUser ? { background: "linear-gradient(135deg,#D97706,#92400E)" } : {}}
        >
          {isUser ? (
            <p>{msg.content}</p>
          ) : (
            <div className="prose-adgm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Citations */}
        {!isUser && msg.sources && msg.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 max-w-full">
            {msg.sources.map((s, i) => <CitationChip key={i} source={s} />)}
          </div>
        )}

        {/* Meta */}
        <div className={`flex items-center gap-2 text-[10px] text-[var(--text-3)] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
          {msg.model && <span className="text-amber-600">{msg.model}</span>}
          {msg.latency_ms && (
            <span className="flex items-center gap-1">
              <Clock size={9} /> {formatLatency(msg.latency_ms)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(question?: string) {
    const q = (question ?? input).trim();
    if (!q || loading) return;
    setInput("");

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: q,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await sendChatMessage(q);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.answer,
        sources: res.sources,
        model: res.model,
        latency_ms: res.latency_ms,
        timestamp: new Date(),
      }]);
    } catch (err: unknown) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `**Error:** ${err instanceof Error ? err.message : "Request failed. Is the backend running on port 8000?"}`,
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar
        title="AI Compliance Copilot"
        subtitle="Ask any question about ADGM regulations and get cited, accurate answers"
      />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6 page-enter">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center"
              style={{ background: "linear-gradient(135deg,#FFFBEB,#FEF3C7)", border: "1.5px solid #FDE68A" }}
            >
              <Sparkles size={28} className="text-amber-600" />
            </div>
            <div>
              <h3 className="font-display text-xl font-semibold text-[var(--text)] mb-1.5">
                ADGM Compliance Assistant
              </h3>
              <p className="text-sm text-[var(--text-2)] max-w-md leading-relaxed">
                Ask any question about ADGM regulations. Answers are grounded in official sources with full citations.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-2xl w-full">
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  onClick={() => handleSend(s)}
                  className="card card-hover rounded-xl px-4 py-3 text-left text-[12.5px] text-[var(--text-2)] hover:text-[var(--text)] transition-all duration-150 group"
                >
                  <span className="block text-amber-500 mb-1 text-[10px] font-semibold uppercase tracking-wide">Try this →</span>
                  {truncate(s, 80)}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-6 pb-6 pt-3 border-t border-[var(--border)] bg-white/80 backdrop-blur-sm">
        {messages.length > 0 && (
          <button
            onClick={() => setMessages([])}
            className="flex items-center gap-1.5 text-[11px] text-[var(--text-3)] hover:text-amber-600 mb-3 transition-colors"
          >
            <RotateCcw size={10} /> New conversation
          </button>
        )}
        <div className="card flex items-end gap-3 p-3 focus-within:border-amber-300 focus-within:shadow-amber transition-all">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about ADGM regulations…"
            rows={1}
            className="flex-1 bg-transparent text-sm text-[var(--text)] placeholder:text-[var(--text-3)] resize-none focus:outline-none leading-relaxed min-h-[24px] max-h-[120px] font-sans"
            onInput={e => {
              const t = e.target as HTMLTextAreaElement;
              t.style.height = "auto";
              t.style.height = Math.min(t.scrollHeight, 120) + "px";
            }}
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="btn-amber w-9 h-9 p-0 flex items-center justify-center flex-shrink-0 rounded-xl"
          >
            <Send size={14} />
          </button>
        </div>
        <p className="text-center text-[10px] text-[var(--text-3)] mt-2">
          Answers grounded in official ADGM regulatory sources with full citations
        </p>
      </div>
    </div>
  );
}
