"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { TopNav } from "@/components/TopNav";
import {
  ApiError,
  type Customer,
  type Environment,
  createEnvironment,
  getCustomer,
  listEnvironments,
} from "@/lib/api";

export default function CustomerDetailPage() {
  const params = useParams<{ id: string }>();
  const customerId = params.id;

  const [customer, setCustomer] = useState<Customer | null>(null);
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [c, envs] = await Promise.all([getCustomer(customerId), listEnvironments(customerId)]);
      setCustomer(c);
      setEnvironments(envs);
    } catch (err) {
      setError(err instanceof ApiError ? (err.detail ?? err.message) : "Failed to load customer.");
    }
  }, [customerId]);

  useEffect(() => {
    // See app/tickets/page.tsx: `refresh` is shared with the
    // create-environment handler below, not single-use.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, [refresh]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const env = await createEnvironment(customerId, name);
      setEnvironments((prev) => [...prev, env]);
      setName("");
      setShowForm(false);
    } catch (err) {
      setError(
        err instanceof ApiError ? (err.detail ?? err.message) : "Failed to create environment.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (error) {
    return (
      <div className="flex min-h-screen flex-col bg-background text-foreground">
        <TopNav active="/customers" />
        <main className="mx-auto w-full max-w-3xl px-6 py-10">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </main>
      </div>
    );
  }

  if (!customer) {
    return (
      <div className="flex min-h-screen flex-col bg-background text-foreground">
        <TopNav active="/customers" />
        <main className="mx-auto w-full max-w-3xl px-6 py-10 text-sm text-neutral-500">
          Loading…
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <TopNav active="/customers" />
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-10">
        <div>
          <h1 className="text-2xl font-semibold">{customer.name}</h1>
          <p className="text-xs tracking-wide text-neutral-500 uppercase">{customer.tier}</p>
        </div>

        <div className="flex items-center justify-between">
          <h2 className="font-medium">Environments</h2>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm font-medium hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
          >
            {showForm ? "Cancel" : "New environment"}
          </button>
        </div>

        {showForm && (
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. production"
              required
              className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
            />
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-brand px-3 py-1.5 text-sm font-semibold text-brand-ink disabled:opacity-50"
            >
              {submitting ? "Creating…" : "Create"}
            </button>
          </form>
        )}

        {environments.length === 0 ? (
          <p className="text-sm text-neutral-500">No environments yet.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {environments.map((env) => (
              <Link
                key={env.id}
                href={`/customers/${customerId}/environments/${env.id}`}
                className="flex flex-col gap-1 rounded-lg border border-neutral-200 p-4 transition-colors hover:border-brand hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
              >
                <span className="font-medium">{env.name}</span>
                <span className="text-xs text-neutral-500">View overview →</span>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
