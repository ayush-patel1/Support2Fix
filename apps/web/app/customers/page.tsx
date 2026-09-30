"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { TopNav } from "@/components/TopNav";
import {
  ApiError,
  type Customer,
  type CustomerTier,
  createCustomer,
  listCustomers,
} from "@/lib/api";

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [name, setName] = useState("");
  const [tier, setTier] = useState<CustomerTier>("STANDARD");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    listCustomers()
      .then(setCustomers)
      .catch((err) =>
        setError(
          err instanceof ApiError ? (err.detail ?? err.message) : "Failed to load customers.",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      const customer = await createCustomer({ name, tier });
      setCustomers((prev) => [...prev, customer]);
      setName("");
      setShowForm(false);
    } catch (err) {
      setFormError(
        err instanceof ApiError ? (err.detail ?? err.message) : "Failed to create customer.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <TopNav active="/customers" />
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-6 py-10">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold">Customers</h1>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-brand-ink hover:brightness-95"
          >
            {showForm ? "Cancel" : "New customer"}
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleSubmit}
            className="flex flex-wrap items-end gap-3 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800"
          >
            <div className="flex flex-col gap-1">
              <label className="text-xs text-neutral-500">Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-neutral-500">Tier</label>
              <select
                value={tier}
                onChange={(e) => setTier(e.target.value as CustomerTier)}
                className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
              >
                {(["FREE", "STANDARD", "ENTERPRISE"] as const).map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-brand-ink disabled:opacity-50"
            >
              {submitting ? "Creating…" : "Create"}
            </button>
            {formError && (
              <p className="w-full text-sm text-red-600 dark:text-red-400">{formError}</p>
            )}
          </form>
        )}

        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        {!loading && customers.length === 0 && !error && (
          <p className="text-sm text-neutral-500">No customers yet.</p>
        )}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {customers.map((customer) => (
            <Link
              key={customer.id}
              href={`/customers/${customer.id}`}
              className="flex flex-col gap-1 rounded-lg border border-neutral-200 p-4 transition-colors hover:border-brand hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
            >
              <span className="font-medium">{customer.name}</span>
              <span className="text-xs tracking-wide text-neutral-500 uppercase">
                {customer.tier}
              </span>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
