"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { LogoMark, Wordmark } from "@/components/Logo";
import { ApiError, login, register } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "login") {
        await login({ email, password });
      } else {
        await register({ email, password, organization_name: organizationName });
      }
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? (err.detail ?? err.message) : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-background px-6 text-foreground">
      <div className="flex items-center gap-2">
        <LogoMark size={40} />
        <Wordmark className="text-2xl" />
      </div>

      <form
        onSubmit={handleSubmit}
        className="flex w-full max-w-sm flex-col gap-4 rounded-lg border border-neutral-200 p-6 dark:border-neutral-800"
      >
        <div className="flex gap-1 rounded-md bg-neutral-100 p-1 text-sm dark:bg-neutral-900">
          {(["login", "register"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => {
                setMode(m);
                setError(null);
              }}
              className={`flex-1 rounded px-3 py-1.5 font-medium transition-colors ${
                mode === m
                  ? "bg-background text-foreground shadow-sm"
                  : "text-neutral-500 hover:text-foreground"
              }`}
            >
              {m === "login" ? "Sign in" : "Create account"}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={mode === "register" ? 8 : undefined}
            className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
          />
        </div>

        {mode === "register" && (
          <div className="flex flex-col gap-1">
            <label className="text-xs text-neutral-500">Organization name</label>
            <input
              value={organizationName}
              onChange={(e) => setOrganizationName(e.target.value)}
              required
              className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
            />
          </div>
        )}

        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="mt-1 rounded-md bg-brand px-4 py-2 text-sm font-semibold text-brand-ink hover:brightness-95 disabled:opacity-50"
        >
          {submitting
            ? mode === "login"
              ? "Signing in…"
              : "Creating account…"
            : mode === "login"
              ? "Sign in"
              : "Create account"}
        </button>
      </form>
    </div>
  );
}
