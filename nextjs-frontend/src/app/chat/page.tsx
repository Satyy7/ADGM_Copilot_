"use client";
import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, RotateCcw, BookOpen, Cpu, Clock } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import TopBar from "@/components/layout/TopBar";
import { sendChatMessage } from "@/lib/api";
import type { ChatMessage, CitationSource } from "@/types";
import { cn, formatLatency, collectionBadgeColor, truncate } from "@/lib/utils";

const SUGGESTIONS = [
  "What are the UBO beneficial ownership disclosure requirements in ADGM?",
  "What documents are needed to incorporate an ADGM private company?",
  "What are the annual filing obligations for an ADGM company?",
  "Explain the employment contract probation period rules under ADGM Employment Regulations.",
];

function TypingIndicator() {
  return (
    <div className="flex items-end gap-3 animate-fade-in">
      <div className="w-8 h-8 rounded-xl bg-jade-400/15 border border-jade-400/25 flex items-center justify-center flex-shrink-0">
        <Cpu size={14} className="text-jade-400" />
      </div>
      <div className="glass rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-1.5">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  );
}

function CitationChip({ source }: { source: CitationSource }) {
  return (
    <div
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs border cursor-default hover:opacity-80 transition-opacity"
      style={{
        background: collectionBadgeColor(source.collection),
        borderColor: "rgba(255,255,255,0.08)",
        color: "#c8d8f0",
      }}
      title={source.rule_reference ?? source.source_title}
    >
      <BookOpen size={10} className="flex-shrink-0 opacity-60" />
      <span className="font-medium truncate max-w-[160px]">{source.source_title}</span>
      {source.rule_reference && (
        <span className="text-gold-400 opacity-70 text-[10px]">{source.rule_reference}</span>
      )}
    </div>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={cn("flex items-end gap-3", isUser ? "flex-row-reverse" : "flex-row")}
    >
      {/* Avatar */}
      <div className={cn(
        "w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-xs font-bold",
        isUser
          ? "bg-gold-500/20 border border-gold-500/30 text-gold-400"
          : "bg-jade-400/15 border border-jade-400/25 text-jade-400"
      )}>
        {isUser ? "U" : <Cpu size={14} />}
      </div>

      {/* Bubble */}
      <div className={cn("max-w-[78%] flex flex-col gap-2", isUser ? "items-end" : "items-start")}>
        <div className={cn(
          "px-4 py-3 rounded-2xl text-sm leading-relaxed",
          isUser
            ? "bg-gold-500/15 border border-gold-500/20 text-white rounded-br-sm"
            : "glass rounded-bl-sm"
        )}>
          {isUser ? (
            <p className="text-white">{msg.content}</p>
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
        <div className={cn("flex items-center gap-2 text-[10px] text-slate-600", isUser ? "flex-row-reverse" : "flex-row")}>
          {msg.model && <span className="text-jade-400/60">{msg.model}</span>}
          {msg.latency_ms && (
            <span className="flex items-center gap-1">
              <Clock size={9} /> {formatLatency(msg.latency_ms)}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

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
      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.answer,
        sources: res.sources,
        model: res.model,
        latency_ms: res.latency_ms,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err: unknown) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `**Error:** ${err instanceof Error ? err.message : "Request failed. Is the backend running on port 8001?"}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar
        title="Compliance Chat"
        subtitle="RAG · HyDE · CRAG · Self-RAG — 16-phase intelligence stack"
      />

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
        {messages.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center h-full text-center space-y-6"
          >
            <div className="w-16 h-16 rounded-2xl bg-jade-400/10 border border-jade-400/20 flex items-center justify-center animate-float">
              <Cpu size={28} className="text-jade-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white mb-1">ADGM Compliance Assistant</h3>
              <p className="text-sm text-slate-500 max-w-md">
                Ask any question about ADGM regulations. Answers are grounded in official sources with full citations.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-2xl w-full">
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  onClick={() => handleSend(s)}
                  className="glass glass-hover rounded-xl px-4 py-3 text-xs text-left text-slate-400 hover:text-slate-200 transition-all duration-200 group"
                >
                  <span className="block text-gold-400/60 mb-1 text-[10px] font-medium uppercase tracking-wide">Try this →</span>
                  {truncate(s, 80)}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="px-6 pb-6 pt-3 border-t border-white/5">
        {messages.length > 0 && (
          <button
            onClick={() => setMessages([])}
            className="flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-400 mb-3 transition-colors"
          >
            <RotateCcw size={11} /> New conversation
          </button>
        )}
        <div className="glass rounded-2xl border border-white/8 flex items-end gap-3 p-3 focus-within:border-gold-500/30 transition-all">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about ADGM regulations…"
            rows={1}
            className="flex-1 bg-transparent text-sm text-white placeholder:text-slate-600 resize-none focus:outline-none leading-relaxed min-h-[24px] max-h-[120px]"
            style={{ height: "auto" }}
            onInput={e => {
              const t = e.target as HTMLTextAreaElement;
              t.style.height = "auto";
              t.style.height = Math.min(t.scrollHeight, 120) + "px";
            }}
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className={cn(
              "w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 transition-all",
              input.trim() && !loading
                ? "bg-gold-500 text-navy-950 shadow-gold-sm hover:bg-gold-400"
                : "bg-navy-700 text-slate-600 cursor-not-allowed"
            )}
          >
            <Send size={15} />
          </motion.button>
        </div>
        <p className="text-center text-[10px] text-slate-700 mt-2">
          Answers grounded in ADGM official regulatory sources · Citations verified by Self-RAG
        </p>
      </div>
    </div>
  );
}
