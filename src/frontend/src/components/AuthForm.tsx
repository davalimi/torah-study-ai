"use client";

import { useState } from "react";
import { register, login } from "@/lib/api";

interface AuthFormProps {
  onAuth: (token: string) => void;
}

export default function AuthForm({ onAuth }: AuthFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const fn = isRegister ? register : login;
      const { token } = await fn(email, password);
      localStorage.setItem("token", token);
      onAuth(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-[var(--background)]">
      <div className="w-full max-w-sm px-6">
        <h1
          className="text-3xl font-bold text-center mb-2"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Torah Study AI
        </h1>
        <p className="text-center text-[var(--muted-foreground)] mb-8">
          Your chavruta. Real sources. Every answer.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
            className="w-full rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3 text-[15px] placeholder:text-[var(--muted-foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            required
            minLength={6}
            className="w-full rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3 text-[15px] placeholder:text-[var(--muted-foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent"
          />

          {error && (
            <p className="text-sm text-red-500 text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[var(--primary)] text-[var(--primary-foreground)] rounded-xl px-4 py-3 text-[15px] font-semibold hover:opacity-90 disabled:opacity-30 transition-opacity"
          >
            {loading ? "..." : isRegister ? "Create account" : "Sign in"}
          </button>
        </form>

        <button
          onClick={() => {
            setIsRegister(!isRegister);
            setError("");
          }}
          className="w-full text-center text-sm text-[var(--muted-foreground)] mt-4 hover:text-[var(--accent)] transition-colors"
        >
          {isRegister
            ? "Already have an account? Sign in"
            : "No account? Create one"}
        </button>
      </div>
    </div>
  );
}
