"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { addMessage, API_URL } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatProps {
  token: string;
  sessionId: number | null;
  initialMessages?: Message[];
  onSessionCreated?: (id: number) => void;
}

// Extract text content from React children (for section detection)
function getTextContent(children: React.ReactNode): string {
  if (typeof children === "string") return children;
  if (Array.isArray(children)) return children.map(getTextContent).join("");
  if (children && typeof children === "object" && "props" in children) {
    return getTextContent((children as React.ReactElement<{ children?: React.ReactNode }>).props.children);
  }
  return "";
}

// Transform Sefaria references in text to clickable links.
// Matches patterns like: Berakhot 17b:13, Genesis 1:1, Rashi on Exodus 20:8
function linkifyReferences(text: string): string {
  const refPattern = /\(([A-Z][A-Za-z\s]+(?:\s\d+[ab]?:?\d*(?::\d+)?))\)/g;
  return text.replace(refPattern, (match, ref) => {
    const slug = ref.trim().replace(/\s+/g, "_").replace(/:/g, ".");
    const url = `https://www.sefaria.org/${slug}`;
    return `([${ref}](${url}))`;
  });
}

export default function Chat({
  token,
  sessionId,
  initialMessages = [],
  onSessionCreated,
}: ChatProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(sessionId);
  const isChattingRef = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isChattingRef.current) {
      setMessages(initialMessages);
      setCurrentSessionId(sessionId);
    }
  }, [sessionId, initialMessages]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [sessionId]);

  async function ensureSession(): Promise<number> {
    if (currentSessionId) return currentSessionId;

    const response = await fetch(`${API_URL}/sessions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });
    const data = await response.json();
    setCurrentSessionId(data.id);
    onSessionCreated?.(data.id);
    return data.id;
  }

  async function handleSend() {
    const question = input.trim();
    if (!question || loading) return;

    const userMessage: Message = { role: "user", content: question };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
    isChattingRef.current = true;

    try {
      const sid = await ensureSession();

      await addMessage(token, sid, "user", question);

      const response = await fetch(`${API_URL}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Something went wrong");
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No response body");

      let fullAnswer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ") && line !== "data: [DONE]") {
            const payload = line.slice(6);
            try {
              const parsed = JSON.parse(payload);
              const chunk = parsed.text || "";
              fullAnswer += chunk;
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  updated[updated.length - 1] = {
                    ...last,
                    content: last.content + chunk,
                  };
                }
                return updated;
              });
            } catch {
              // Ignore malformed SSE lines
            }
          }
        }
      }

      if (fullAnswer) {
        await addMessage(token, sid, "assistant", fullAnswer);
      }
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.role === "assistant") {
          updated[updated.length - 1] = {
            ...last,
            content:
              error instanceof Error
                ? error.message
                : "Something went wrong. Please try again.",
          };
        }
        return updated;
      });
    } finally {
      setLoading(false);
      isChattingRef.current = false;
      inputRef.current?.focus();
    }
  }

  const markdownComponents = {
    h1: ({ children }: { children?: React.ReactNode }) => (
      <h1 className="text-2xl font-bold mt-8 mb-4 text-[var(--foreground)]">{children}</h1>
    ),
    h2: ({ children }: { children?: React.ReactNode }) => (
      <h2 className="text-xl font-bold mt-6 mb-3 text-[var(--foreground)]">{children}</h2>
    ),
    h3: ({ children }: { children?: React.ReactNode }) => {
      const text = getTextContent(children);

      if (text.includes("TL;DR")) {
        return (
          <div className="tldr-heading mt-2 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-[var(--accent)]">
              Key Takeaway
            </span>
          </div>
        );
      }

      if (text.includes("Sources") || text.includes("Explanation")) {
        return (
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)] mt-8 mb-3">
            {children}
          </h3>
        );
      }

      return (
        <h3 className="text-lg font-semibold mt-6 mb-3 text-[var(--foreground)]">
          {children}
        </h3>
      );
    },
    p: ({ children }: { children?: React.ReactNode }) => {
      const text = getTextContent(children);
      const isDisclaimer =
        text.includes("consult your Rabbi") ||
        text.includes("learning purposes only");

      if (isDisclaimer) {
        return (
          <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <span className="font-semibold">Note: </span>
            <span className="italic">{children}</span>
          </div>
        );
      }

      return (
        <p className="mb-4 leading-7 text-[var(--foreground)]">{children}</p>
      );
    },
    ul: ({ children }: { children?: React.ReactNode }) => (
      <ul className="list-disc pl-6 mb-4 space-y-2 marker:text-[var(--accent)]">{children}</ul>
    ),
    ol: ({ children }: { children?: React.ReactNode }) => (
      <ol className="list-decimal pl-6 mb-4 space-y-2">{children}</ol>
    ),
    li: ({ children }: { children?: React.ReactNode }) => (
      <li className="leading-7 text-[var(--foreground)]">{children}</li>
    ),
    strong: ({ children }: { children?: React.ReactNode }) => (
      <strong className="font-bold text-[var(--foreground)]">{children}</strong>
    ),
    em: ({ children }: { children?: React.ReactNode }) => (
      <em className="italic text-[var(--foreground)]">{children}</em>
    ),
    a: ({ href, children }: { href?: string; children?: React.ReactNode }) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[var(--accent)] text-[13px] no-underline hover:underline opacity-70 hover:opacity-100 transition-opacity"
      >
        {children}
      </a>
    ),
    blockquote: ({ children }: { children?: React.ReactNode }) => (
      <blockquote className="border-l-4 border-[var(--accent)] pl-4 my-4 italic text-[var(--foreground)]">
        {children}
      </blockquote>
    ),
    code: ({ children }: { children?: React.ReactNode }) => (
      <code className="bg-[var(--muted)] px-1.5 py-0.5 rounded text-sm font-mono">
        {children}
      </code>
    ),
    hr: () => <hr className="my-6 border-[var(--border)]" />,
  };

  return (
    <div className="flex flex-col h-full">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-8">
        <div className="max-w-4xl mx-auto space-y-8">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full min-h-[60vh] text-center">
              <h2
                className="text-3xl font-bold mb-2"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                Shalom!
              </h2>
              <p className="text-[var(--muted-foreground)] text-base">
                Ask any Torah question to get started.
              </p>
            </div>
          )}

          {messages.filter((m) => m.content !== "").map((message, i) => {
            if (message.role === "user") {
              return (
                <div key={i} className="flex justify-end">
                  <div className="max-w-[75%] rounded-2xl px-5 py-3 bg-[var(--primary)] text-[var(--primary-foreground)]">
                    <p className="text-[15px] leading-relaxed whitespace-pre-wrap">
                      {message.content}
                    </p>
                  </div>
                </div>
              );
            }

            // Assistant messages: full width, no bubble
            const linkedContent = linkifyReferences(message.content);
            return (
              <div key={i} className="w-full">
                <div className="text-[15px]">
                  <ReactMarkdown components={markdownComponents}>
                    {linkedContent}
                  </ReactMarkdown>
                </div>
              </div>
            );
          })}

          {loading && messages[messages.length - 1]?.content === "" && (
            <div className="flex justify-start">
              <div className="py-2">
                <div className="flex gap-1.5">
                  <span className="w-2 h-2 bg-[var(--accent)] rounded-full animate-bounce [animation-delay:-0.3s]" />
                  <span className="w-2 h-2 bg-[var(--accent)] rounded-full animate-bounce [animation-delay:-0.15s]" />
                  <span className="w-2 h-2 bg-[var(--accent)] rounded-full animate-bounce" />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-[var(--border)] bg-[var(--background)] px-6 py-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="max-w-4xl mx-auto flex gap-3"
        >
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a Torah question..."
            disabled={loading}
            className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3 text-[15px] placeholder:text-[var(--muted-foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent disabled:opacity-50 transition-shadow"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="bg-[var(--primary)] text-[var(--primary-foreground)] rounded-xl px-6 py-3 text-[15px] font-semibold hover:opacity-90 disabled:opacity-30 transition-opacity"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
