"use client";

import { Session } from "@/lib/api";

interface SidebarProps {
  sessions: Session[];
  activeSessionId: number | null;
  onSelectSession: (id: number) => void;
  onNewChat: () => void;
  onLogout: () => void;
}

export default function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onLogout,
}: SidebarProps) {
  return (
    <div className="w-64 border-r border-[var(--border)] bg-[var(--card)] flex flex-col h-full">
      <div className="p-4 border-b border-[var(--border)]">
        <button
          onClick={onNewChat}
          className="w-full bg-[var(--primary)] text-[var(--primary-foreground)] rounded-xl px-4 py-2.5 text-sm font-semibold hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
        >
          <span className="text-lg">+</span> New chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {sessions.map((session) => (
          <button
            key={session.id}
            onClick={() => onSelectSession(session.id)}
            className={`w-full text-left rounded-lg px-3 py-2.5 mb-1 text-sm transition-colors truncate ${
              activeSessionId === session.id
                ? "bg-[var(--secondary)] font-medium"
                : "hover:bg-[var(--secondary)]"
            }`}
          >
            {session.title}
          </button>
        ))}
        {sessions.length === 0 && (
          <p className="text-xs text-[var(--muted-foreground)] text-center mt-4">
            No conversations yet
          </p>
        )}
      </div>

      <div className="p-4 border-t border-[var(--border)]">
        <button
          onClick={onLogout}
          className="w-full text-sm text-[var(--muted-foreground)] hover:text-red-500 transition-colors"
        >
          Sign out
        </button>
      </div>
    </div>
  );
}
