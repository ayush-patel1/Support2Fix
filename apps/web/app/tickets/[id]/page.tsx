"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { PriorityBadge, StatusBadge } from "@/components/TicketBadges";
import { TopNav } from "@/components/TopNav";
import {
  addTicketComment,
  ApiError,
  changeTicketStatus,
  getTicket,
  listTicketEvents,
  type Ticket,
  type TicketEvent,
  type TicketPriority,
  type TicketStatus,
  updateTicket,
} from "@/lib/api";

const ALL_STATUSES: TicketStatus[] = [
  "OPEN",
  "INVESTIGATING",
  "ROOT_CAUSE_FOUND",
  "FIX_PROPOSED",
  "VALIDATING",
  "RESOLVED",
  "ESCALATED",
];

export default function TicketDetailPage() {
  const params = useParams<{ id: string }>();
  const ticketId = params.id;

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [events, setEvents] = useState<TicketEvent[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("MEDIUM");

  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [t, e] = await Promise.all([getTicket(ticketId), listTicketEvents(ticketId)]);
      setTicket(t);
      setEvents(e);
      setTitle(t.title);
      setDescription(t.description);
      setPriority(t.priority);
    } catch (err) {
      setLoadError(
        err instanceof ApiError ? (err.detail ?? err.message) : "Failed to load ticket.",
      );
    }
  }, [ticketId]);

  useEffect(() => {
    // `refresh` is shared with the status-change/edit/comment handlers
    // below (they re-fetch to pick up new timeline entries), not single-use
    // like HealthBadge's inline .then() — see app/tickets/page.tsx for the
    // same reasoning. Effect deps are a stable route param, so there's no
    // cascading-render risk.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, [refresh]);

  async function handleSaveEdit() {
    if (!ticket) return;
    setBusy(true);
    setActionError(null);
    try {
      const updated = await updateTicket(ticket.id, { title, description, priority });
      setTicket(updated);
      setEditing(false);
      await refresh(); // pick up the FIELD_CHANGED timeline entries
    } catch (err) {
      setActionError(err instanceof ApiError ? (err.detail ?? err.message) : "Save failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleStatusChange(newStatus: TicketStatus) {
    if (!ticket) return;
    setBusy(true);
    setActionError(null);
    try {
      const updated = await changeTicketStatus(ticket.id, newStatus);
      setTicket(updated);
      await refresh();
    } catch (err) {
      setActionError(
        err instanceof ApiError ? (err.detail ?? err.message) : "That status change was rejected.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleAddComment(e: React.FormEvent) {
    e.preventDefault();
    if (!comment.trim()) return;
    setBusy(true);
    setActionError(null);
    try {
      await addTicketComment(ticketId, comment);
      setComment("");
      await refresh();
    } catch (err) {
      setActionError(
        err instanceof ApiError ? (err.detail ?? err.message) : "Failed to add comment.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    return (
      <div className="flex min-h-screen flex-col bg-background text-foreground">
        <TopNav active="/tickets" />
        <main className="mx-auto w-full max-w-3xl px-6 py-10">
          <p className="text-sm text-red-600 dark:text-red-400">{loadError}</p>
        </main>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="flex min-h-screen flex-col bg-background text-foreground">
        <TopNav active="/tickets" />
        <main className="mx-auto w-full max-w-3xl px-6 py-10 text-sm text-neutral-500">
          Loading…
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <TopNav active="/tickets" />
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-10">
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-4">
            {editing ? (
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-xl font-semibold dark:border-neutral-700"
              />
            ) : (
              <h1 className="text-xl font-semibold">{ticket.title}</h1>
            )}
            <div className="flex items-center gap-2">
              <PriorityBadge priority={ticket.priority} />
              <StatusBadge status={ticket.status} />
            </div>
          </div>

          {editing ? (
            <>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
              />
              <div className="flex items-center gap-2">
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value as TicketPriority)}
                  className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
                >
                  {(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const).map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleSaveEdit}
                  disabled={busy}
                  className="rounded-md bg-brand px-3 py-1.5 text-sm font-semibold text-brand-ink disabled:opacity-50"
                >
                  Save
                </button>
                <button
                  onClick={() => setEditing(false)}
                  className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700"
                >
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="text-sm whitespace-pre-wrap text-neutral-700 dark:text-neutral-300">
                {ticket.description || <span className="text-neutral-400">No description.</span>}
              </p>
              <button
                onClick={() => setEditing(true)}
                className="w-fit text-sm font-medium text-brand-ink underline dark:text-brand"
              >
                Edit
              </button>
            </>
          )}
        </div>

        <div className="flex items-center gap-2 border-t border-neutral-200 pt-4 dark:border-neutral-800">
          <span className="text-sm font-medium">Change status:</span>
          <select
            value={ticket.status}
            onChange={(e) => handleStatusChange(e.target.value as TicketStatus)}
            disabled={busy}
            className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
          >
            {ALL_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replaceAll("_", " ")}
              </option>
            ))}
          </select>
          <span className="text-xs text-neutral-500">
            Only transitions allowed by the state machine will succeed.
          </span>
        </div>

        {actionError && <p className="text-sm text-red-600 dark:text-red-400">{actionError}</p>}

        <div className="flex flex-col gap-3 border-t border-neutral-200 pt-4 dark:border-neutral-800">
          <h2 className="font-medium">Timeline</h2>
          <ol className="flex flex-col gap-3">
            {events.map((event) => (
              <li key={event.id} className="flex gap-3 text-sm">
                <span className="w-16 shrink-0 text-xs text-neutral-500">
                  {new Date(event.created_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
                <span>{describeEvent(event)}</span>
              </li>
            ))}
          </ol>
          <form onSubmit={handleAddComment} className="flex gap-2 pt-2">
            <input
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add a comment…"
              className="flex-1 rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
            />
            <button
              type="submit"
              disabled={busy || !comment.trim()}
              className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm font-medium disabled:opacity-50 dark:border-neutral-700"
            >
              Comment
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}

function describeEvent(event: TicketEvent): string {
  switch (event.type) {
    case "CREATED":
      return "Ticket created.";
    case "STATUS_CHANGED":
      return `Status changed: ${String(event.payload.from)} → ${String(event.payload.to)}`;
    case "FIELD_CHANGED":
      return `${String(event.payload.field)} changed: "${String(event.payload.from)}" → "${String(event.payload.to)}"`;
    case "COMMENT":
      return String(event.payload.comment);
    default:
      return event.type;
  }
}
