"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { PriorityBadge, StatusBadge } from "@/components/TicketBadges";
import { TopNav } from "@/components/TopNav";
import {
  ApiError,
  type Customer,
  createTicket,
  listCustomers,
  listTickets,
  type Ticket,
  type TicketPriority,
  type TicketStatus,
} from "@/lib/api";

const STATUSES: TicketStatus[] = [
  "OPEN",
  "INVESTIGATING",
  "ROOT_CAUSE_FOUND",
  "FIX_PROPOSED",
  "VALIDATING",
  "RESOLVED",
  "ESCALATED",
];
const PRIORITIES: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [status, setStatus] = useState<TicketStatus | "">("");
  const [priority, setPriority] = useState<TicketPriority | "">("");
  const [search, setSearch] = useState("");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(
    async (cursor?: string) => {
      setLoading(true);
      setError(null);
      try {
        const page = await listTickets({
          status: status || undefined,
          priority: priority || undefined,
          search: search || undefined,
          cursor,
        });
        setTickets((prev) => (cursor ? [...prev, ...page.items] : page.items));
        setNextCursor(page.next_cursor);
      } catch (err) {
        setError(err instanceof ApiError ? (err.detail ?? err.message) : "Failed to load tickets.");
      } finally {
        setLoading(false);
      }
    },
    [status, priority, search],
  );

  useEffect(() => {
    // `load` is intentionally shared with the "Load more" button and filter
    // changes below, not single-use like HealthBadge's inline .then() — so
    // it can't be restructured to dodge this rule without duplicating the
    // fetch. Effect deps are stable (filter state only), so there's no
    // actual cascading-render risk here.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  useEffect(() => {
    listCustomers()
      .then(setCustomers)
      .catch(() => setCustomers([]));
  }, []);

  const customerName = (id: string) => customers.find((c) => c.id === id)?.name ?? id.slice(0, 8);

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <TopNav active="/tickets" />
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-6 py-10">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold">Tickets</h1>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-brand-ink hover:brightness-95"
          >
            {showForm ? "Cancel" : "New ticket"}
          </button>
        </div>

        {showForm && (
          <NewTicketForm
            customers={customers}
            onCreated={(ticket) => {
              setTickets((prev) => [ticket, ...prev]);
              setShowForm(false);
            }}
          />
        )}

        <div className="flex flex-wrap gap-3">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as TicketStatus | "")}
            className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
          >
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replaceAll("_", " ")}
              </option>
            ))}
          </select>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value as TicketPriority | "")}
            className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
          >
            <option value="">All priorities</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search title or description…"
            className="min-w-[220px] flex-1 rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
          />
        </div>

        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

        <div className="divide-y divide-neutral-200 rounded-lg border border-neutral-200 dark:divide-neutral-800 dark:border-neutral-800">
          {tickets.length === 0 && !loading && (
            <p className="p-6 text-center text-sm text-neutral-500">
              No tickets match these filters.
            </p>
          )}
          {tickets.map((ticket) => (
            <Link
              key={ticket.id}
              href={`/tickets/${ticket.id}`}
              className="flex items-center justify-between gap-4 p-4 transition-colors hover:bg-neutral-50 dark:hover:bg-neutral-900"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{ticket.title}</p>
                <p className="text-xs text-neutral-500">{customerName(ticket.customer_id)}</p>
              </div>
              <PriorityBadge priority={ticket.priority} />
              <StatusBadge status={ticket.status} />
            </Link>
          ))}
        </div>

        {nextCursor && (
          <button
            onClick={() => load(nextCursor)}
            disabled={loading}
            className="mx-auto rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium hover:bg-neutral-100 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-900"
          >
            {loading ? "Loading…" : "Load more"}
          </button>
        )}
      </main>
    </div>
  );
}

function NewTicketForm({
  customers,
  onCreated,
}: {
  customers: Customer[];
  onCreated: (ticket: Ticket) => void;
}) {
  const [customerId, setCustomerId] = useState(customers[0]?.id ?? "");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("MEDIUM");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!customerId) {
      setError("Create a customer first — a ticket must belong to one.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const ticket = await createTicket({ customer_id: customerId, title, description, priority });
      onCreated(ticket);
    } catch (err) {
      setError(err instanceof ApiError ? (err.detail ?? err.message) : "Failed to create ticket.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-3 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800"
    >
      {customers.length === 0 ? (
        <p className="text-sm text-neutral-500">
          No customers yet —{" "}
          <Link href="/customers" className="underline">
            create one
          </Link>{" "}
          before opening a ticket.
        </p>
      ) : (
        <select
          value={customerId}
          onChange={(e) => setCustomerId(e.target.value)}
          className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
        >
          {customers.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      )}
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Title"
        required
        className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
      />
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Description"
        rows={3}
        className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
      />
      <select
        value={priority}
        onChange={(e) => setPriority(e.target.value as TicketPriority)}
        className="w-fit rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
      >
        {(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const).map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </select>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <button
        type="submit"
        disabled={submitting || customers.length === 0}
        className="w-fit rounded-md bg-brand px-4 py-2 text-sm font-semibold text-brand-ink hover:brightness-95 disabled:opacity-50"
      >
        {submitting ? "Creating…" : "Create ticket"}
      </button>
    </form>
  );
}
