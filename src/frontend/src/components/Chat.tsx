"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  async function handleSend() {
    const question = input.trim();
    if (!question || loading) return;

    const userMessage: Message = { role: "user", content: question };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Something went wrong");
      }

      const data = await response.json();
      const assistantMessage: Message = {
        role: "assistant",
        content: data.answer,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: "assistant",
        content:
          error instanceof Error
            ? error.message
            : "Something went wrong. Please try again.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto w-full">
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            <p>Ask a Torah question to get started</p>
          </div>
        )}
        <div className="space-y-4">
          {messages.map((message, i) => (
            <Card
              key={i}
              className={`p-4 ${
                message.role === "user"
                  ? "ml-12 bg-primary text-primary-foreground"
                  : "mr-12"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
            </Card>
          ))}
          {loading && (
            <Card className="mr-12 p-4">
              <p className="text-sm text-muted-foreground animate-pulse">
                Thinking...
              </p>
            </Card>
          )}
        </div>
      </ScrollArea>

      <div className="border-t p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a Torah question..."
            disabled={loading}
          />
          <Button type="submit" disabled={!input.trim() || loading}>
            Send
          </Button>
        </form>
      </div>
    </div>
  );
}
