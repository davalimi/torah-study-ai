import Chat from "@/components/Chat";

export default function Home() {
  return (
    <main className="flex flex-col h-screen bg-[var(--background)]">
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
      <Chat />
    </main>
  );
}
