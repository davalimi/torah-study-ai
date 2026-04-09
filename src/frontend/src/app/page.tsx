"use client";

import { useState, useEffect, useCallback } from "react";
import AuthForm from "@/components/AuthForm";
import Sidebar from "@/components/Sidebar";
import Chat from "@/components/Chat";
import { listSessions, getSession, Session } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [activeMessages, setActiveMessages] = useState<Message[]>([]);

  useEffect(() => {
    const saved = localStorage.getItem("token");
    if (saved) setToken(saved);
  }, []);

  const refreshSessions = useCallback(async () => {
    if (!token) return;
    try {
      const data = await listSessions(token);
      setSessions(data);
    } catch {
      // Token expired or invalid
      setToken(null);
      localStorage.removeItem("token");
    }
  }, [token]);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  async function handleSelectSession(id: number) {
    if (!token) return;
    const data = await getSession(token, id);
    setActiveSessionId(id);
    setActiveMessages(
      data.messages.map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
      }))
    );
  }

  function handleNewChat() {
    setActiveSessionId(null);
    setActiveMessages([]);
  }

  function handleLogout() {
    localStorage.removeItem("token");
    setToken(null);
    setSessions([]);
    setActiveSessionId(null);
    setActiveMessages([]);
  }

  function handleAuth(newToken: string) {
    setToken(newToken);
  }

  function handleSessionCreated(id: number) {
    setActiveSessionId(id);
    refreshSessions();
  }

  if (!token) {
    return <AuthForm onAuth={handleAuth} />;
  }

  return (
    <div className="flex h-screen bg-[var(--background)]">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onLogout={handleLogout}
      />

      <div className="flex-1 flex flex-col">
        <header className="border-b border-[var(--border)] bg-[var(--card)] px-6 py-4">
          <h1
            className="text-xl font-bold tracking-tight"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Torah Study AI
          </h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Your chavruta. Real sources. Every answer.
          </p>
        </header>

        <Chat
          token={token}
          sessionId={activeSessionId}
          initialMessages={activeMessages}
          onSessionCreated={handleSessionCreated}
        />
      </div>
    </div>
  );
}
