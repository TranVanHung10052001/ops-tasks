"use client";

import { useState, useRef, useEffect } from "react";

// ─── Types ─────────────────────────────────────────────────────────────────────

type AskResponse = {
  answer: string;
  tools_used?: string[];
  tool_results?: Record<string, unknown>;
  error?: string;
};

type Turn = {
  question: string;
  answer: string;
  tools_used: string[];
  tool_results: Record<string, unknown>;
  ts: string;
  loading?: boolean;
};

// ─── Example prompts (chips) ───────────────────────────────────────────────────

const EXAMPLES = [
  "Vì sao FR HAN tuần này giảm?",
  "Tuần này ai đang overload?",
  "OKR O1.1 đang thế nào?",
  "Task #5 nên giao ai phù hợp nhất?",
  "Tôi có đang giữ quá nhiều task G4 không?",
  "Member nào có scope phù hợp Bulky vendor?",
];

// ─── Tool icons ────────────────────────────────────────────────────────────────

const TOOL_LABELS: Record<string, { icon: string; name: string }> = {
  team_workload:        { icon: "👥", name: "Team workload" },
  okr_status:           { icon: "🎯", name: "OKR status" },
  metrics:              { icon: "📊", name: "Metrics" },
  find_member_for_task: { icon: "🔍", name: "Match member" },
  member_detail:        { icon: "👤", name: "Member detail" },
  task_detail:          { icon: "📋", name: "Task detail" },
};

// ─── Render helpers ────────────────────────────────────────────────────────────

function renderMarkdown(md: string): string {
  // Minimal markdown → HTML conversion for AI output.
  // Supports: **bold**, *italic*, `code`, ## headers, - bullets, numbered lists.
  return md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/^### (.+)$/gm, '<h3 class="text-sm font-medium text-text-primary mt-3 mb-1">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-md font-semibold text-text-primary mt-4 mb-2">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-lg font-semibold text-text-primary mt-4 mb-2">$1</h1>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong class="text-text-primary">$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code class="bg-surface-deep px-1 py-0.5 rounded text-accent-amber text-xs">$1</code>')
    .replace(/^[-•] (.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
    .replace(/^(\d+)\. (.+)$/gm, '<li class="ml-4 list-decimal">$2</li>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>');
}

// ─── Main component ────────────────────────────────────────────────────────────

export default function AskPage() {
  const [q, setQ] = useState("");
  const [history, setHistory] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTurn, setSelectedTurn] = useState<number | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, loading]);

  async function submit(question?: string) {
    const text = (question ?? q).trim();
    if (!text || loading) return;
    setLoading(true);
    setQ("");

    const ts = new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
    const placeholder: Turn = {
      question: text, answer: "", tools_used: [], tool_results: {}, ts, loading: true,
    };
    setHistory(prev => [...prev, placeholder]);

    try {
      const res  = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text }),
      });
      const data = (await res.json()) as AskResponse;
      setHistory(prev => {
        const next = [...prev];
        next[next.length - 1] = {
          question:     text,
          answer:       data.answer || data.error || "Không có câu trả lời.",
          tools_used:   data.tools_used || [],
          tool_results: data.tool_results || {},
          ts,
          loading:      false,
        };
        return next;
      });
    } catch (err) {
      setHistory(prev => {
        const next = [...prev];
        next[next.length - 1] = {
          ...placeholder,
          answer: `Lỗi: ${String(err)}`,
          loading: false,
        };
        return next;
      });
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const currentTurn = selectedTurn !== null ? history[selectedTurn] : history[history.length - 1];

  return (
    <div className="flex h-[calc(100vh-40px)]">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="px-6 py-4 border-b border-divider bg-surface-deep">
          <div className="flex items-center gap-3">
            <span className="text-accent-amber text-xl">⊙</span>
            <div>
              <h1 className="text-lg font-semibold text-text-primary">AI Ops Console</h1>
              <p className="text-2xs text-text-tertiary mono">
                Suy luận trên team workload · OKR · metrics · scope cá nhân
              </p>
            </div>
          </div>
        </div>

        {/* Conversation */}
        <div className="flex-1 overflow-y-auto scroll-ops px-6 py-4 space-y-6">
          {history.length === 0 && (
            <div className="text-center py-12">
              <div className="text-4xl mb-3">⊙</div>
              <h2 className="text-md text-text-primary mb-2">Hỏi AI về vận hành</h2>
              <p className="text-sm text-text-secondary mb-6 max-w-md mx-auto">
                AI có truy cập team workload, OKR Q2/2026, metrics Redash, scope từng người
                và 18 playbook.
              </p>
              <div className="flex flex-wrap gap-2 justify-center max-w-2xl mx-auto">
                {EXAMPLES.map(ex => (
                  <button
                    key={ex}
                    onClick={() => submit(ex)}
                    className="text-2xs px-3 py-1.5 bg-surface border border-divider text-text-secondary hover:border-accent-amber-deep hover:text-text-primary transition-colors"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          )}

          {history.map((turn, i) => (
            <div key={i} className="space-y-3">
              {/* User question */}
              <div className="flex justify-end">
                <div className="bg-surface border-r-2 border-accent-amber-deep p-3 max-w-[80%]">
                  <div className="text-sm text-text-primary">{turn.question}</div>
                  <div className="mono text-2xs text-text-tertiary mt-1">{turn.ts}</div>
                </div>
              </div>

              {/* AI answer */}
              <div className="flex justify-start">
                <div className="bg-surface border-l-2 border-accent-amber p-4 max-w-[80%] cursor-pointer hover:border-accent-amber-deep"
                     onClick={() => setSelectedTurn(i)}>
                  {turn.loading ? (
                    <div className="flex items-center gap-2 text-text-tertiary">
                      <span className="animate-pulse">⊙</span>
                      <span className="text-sm">AI đang suy luận…</span>
                    </div>
                  ) : (
                    <>
                      <div
                        className="text-sm text-text-secondary leading-relaxed prose prose-sm prose-invert"
                        dangerouslySetInnerHTML={{ __html: renderMarkdown(turn.answer) }}
                      />
                      {turn.tools_used.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-divider">
                          {turn.tools_used.map(t => {
                            const tl = TOOL_LABELS[t] ?? { icon: "🔧", name: t };
                            return (
                              <span key={t} className="text-2xs px-2 py-0.5 bg-surface-deep border border-divider text-text-tertiary mono">
                                {tl.icon} {tl.name}
                              </span>
                            );
                          })}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-divider px-6 py-3 bg-surface-deep">
          <div className="flex items-end gap-2 bg-surface border border-divider-strong px-3 py-2 focus-within:border-accent-amber-deep">
            <span className="text-accent-amber text-sm mt-1">&gt;</span>
            <textarea
              ref={inputRef}
              value={q}
              onChange={e => setQ(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Hỏi gì về team, OKR, metrics... (Enter để gửi, Shift+Enter xuống dòng)"
              rows={1}
              className="flex-1 bg-transparent outline-none text-sm text-text-primary placeholder:text-text-tertiary resize-none max-h-32"
              disabled={loading}
            />
            <button
              onClick={() => submit()}
              disabled={loading || !q.trim()}
              className="btn-ops primary text-2xs disabled:opacity-40"
            >
              {loading ? "…" : "Hỏi"}
            </button>
          </div>
          <div className="mono text-2xs text-text-tertiary mt-1.5">
            AI dùng Gemini 3.1 Pro · tool-use loop · trả lời chỉ là gợi ý, manager quyết định
          </div>
        </div>
      </div>

      {/* Side panel: tool results inspector */}
      {currentTurn && currentTurn.tools_used.length > 0 && (
        <aside className="w-[360px] border-l border-divider bg-surface-deep flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-divider">
            <div className="text-sm text-text-primary font-medium">Data đã dùng</div>
            <div className="mono text-2xs text-text-tertiary mt-0.5">
              {currentTurn.tools_used.length} tool · {currentTurn.ts}
            </div>
          </div>
          <div className="flex-1 overflow-y-auto scroll-ops px-4 py-3 space-y-3">
            {currentTurn.tools_used.map(t => {
              const tl   = TOOL_LABELS[t] ?? { icon: "🔧", name: t };
              const data = currentTurn.tool_results[t];
              const json = data ? JSON.stringify(data, null, 2) : "(no data)";
              return (
                <details key={t} className="border border-divider bg-surface">
                  <summary className="px-3 py-2 cursor-pointer text-xs text-text-secondary hover:text-text-primary">
                    {tl.icon} {tl.name}
                  </summary>
                  <pre className="px-3 py-2 text-2xs text-text-tertiary mono overflow-x-auto max-h-64 overflow-y-auto border-t border-divider">
                    {json.length > 4000 ? json.slice(0, 4000) + "\n…(truncated)" : json}
                  </pre>
                </details>
              );
            })}
          </div>
        </aside>
      )}
    </div>
  );
}
