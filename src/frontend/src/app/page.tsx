import Chat from "@/components/Chat";

export default function Home() {
  return (
    <main className="flex flex-col h-screen">
      <header className="border-b px-4 py-3">
        <h1 className="text-lg font-semibold">Torah Study AI</h1>
        <p className="text-sm text-muted-foreground">
          Your AI study partner. Real sources. Every answer.
        </p>
      </header>
      <Chat />
    </main>
  );
}
