"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { TopNav } from "@/components/TopNav";
import {
  ApiError,
  getInvestigation,
  getTicket,
  type InvestigationDetail,
  type Ticket,
} from "@/lib/api";
import { useAuthGuard } from "@/lib/useAuthGuard";

const ACTIVE = new Set(["QUEUED", "RUNNING"]);

function pretty(value: unknown): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2) ?? String(value);
}

function formatTime(value: string): string {
  return new Date(value).toLocaleString();
}

function StateBadge({ status }: { status: string }) {
  const styles =
    status === "COMPLETED"
      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
      : status === "FAILED"
        ? "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200"
        : "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-100";
  return (
    <span className={`rounded-full px-3 py-1 font-mono text-xs font-semibold ${styles}`}>
      {status}
    </span>
  );
}

export default function InvestigationPage() {
  const params = useParams<{ id: string }>();
  const investigationId = params.id;
  const { me, loading: authLoading } = useAuthGuard();
  const [investigation, setInvestigation] = useState<InvestigationDetail | null>(null);
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState<string | null>(null);
  const investigationStatus = investigation?.status;

  const refresh = useCallback(async () => {
    try {
      const result = await getInvestigation(investigationId);
      const ticketResult = await getTicket(result.ticket_id);
      setInvestigation(result);
      setTicket(ticketResult);
      setError(null);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? (err.detail ?? err.message)
          : "The investigation could not be loaded.",
      );
    }
  }, [investigationId]);

  useEffect(() => {
    if (authLoading || !me) return;
    let stopped = false;
    const update = async () => {
      if (stopped) return;
      await refresh();
    };
    void update();
    const timer = window.setInterval(() => {
      if (investigationStatus && !ACTIVE.has(investigationStatus)) return;
      void update();
    }, 2000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [authLoading, me, refresh, investigationStatus]);

  if (authLoading || !me) return null;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <TopNav active="/tickets" userEmail={me.user.email} />
      <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-6 py-10">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link
              href={ticket ? `/tickets/${ticket.id}` : "/tickets"}
              className="text-sm text-neutral-500 hover:underline"
            >
              ← {ticket ? "Back to ticket" : "Tickets"}
            </Link>
            <h1 className="mt-2 text-2xl font-semibold">Evidence investigation</h1>
            <p className="mt-1 text-sm text-neutral-500">
              {ticket?.title ?? `Investigation ${investigationId}`}
            </p>
          </div>
          {investigation && <StateBadge status={investigation.status} />}
        </div>

        {error && (
          <div
            role="alert"
            className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200"
          >
            {error}
          </div>
        )}

        {!investigation && !error && (
          <p className="rounded-lg border border-neutral-200 p-6 text-sm text-neutral-500 dark:border-neutral-800">
            Loading investigation…
          </p>
        )}

        {investigation && (
          <>
            <section className="rounded-lg border border-neutral-200 p-5 dark:border-neutral-800">
              <h2 className="font-semibold">Investigation status</h2>
              <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-300">
                {investigation.summary ??
                  "The worker is collecting tenant-scoped evidence. This page refreshes automatically."}
              </p>
              <p className="mt-3 text-xs text-neutral-500">
                Started {formatTime(investigation.created_at)}
                {investigation.completed_at &&
                  ` · Finished ${formatTime(investigation.completed_at)}`}
              </p>
            </section>

            {investigation.candidate && (
              <section className="rounded-lg border border-amber-300 bg-amber-50 p-5 dark:border-amber-900 dark:bg-amber-950/40">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-semibold">Root-cause candidate</h2>
                  <span className="rounded bg-amber-200 px-2 py-0.5 font-mono text-xs dark:bg-amber-900">
                    {investigation.candidate.classification}
                  </span>
                </div>
                <p className="mt-3 text-sm">{investigation.candidate.summary}</p>
                {investigation.candidate.path && (
                  <p className="mt-2 font-mono text-xs">
                    {investigation.candidate.path}
                    {investigation.candidate.line_number
                      ? `:${investigation.candidate.line_number}`
                      : ""}
                  </p>
                )}
                <div className="mt-3 flex flex-wrap gap-3 text-xs">
                  {investigation.candidate.evidence_ids.map((evidenceId) => (
                    <a
                      key={evidenceId}
                      href={`#evidence-${evidenceId}`}
                      className="font-medium underline"
                    >
                      Evidence {evidenceId.slice(0, 8)}
                    </a>
                  ))}
                </div>
              </section>
            )}

            {investigation.evidence_gaps.length > 0 && (
              <section className="rounded-lg border border-neutral-200 p-5 dark:border-neutral-800">
                <h2 className="font-semibold">Evidence gaps</h2>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-neutral-600 dark:text-neutral-300">
                  {investigation.evidence_gaps.map((gap, index) => (
                    <li key={`${index}-${gap}`}>{gap}</li>
                  ))}
                </ul>
              </section>
            )}

            <section className="rounded-lg border border-neutral-200 p-5 dark:border-neutral-800">
              <h2 className="font-semibold">Activity</h2>
              <ol className="mt-4 space-y-4">
                {investigation.timeline.map((item) => (
                  <li key={`${item.kind}-${item.id}`} className="border-l-2 border-brand/50 pl-4">
                    {item.evidence_id ? (
                      <a
                        href={`#evidence-${item.evidence_id}`}
                        className="text-sm font-medium underline"
                      >
                        {item.title}
                      </a>
                    ) : (
                      <p className="text-sm">{item.title}</p>
                    )}
                    <time className="mt-1 block text-xs text-neutral-500">
                      {formatTime(item.occurred_at)}
                    </time>
                  </li>
                ))}
                {investigation.timeline.length === 0 && (
                  <li className="text-sm text-neutral-500">No activity recorded yet.</li>
                )}
              </ol>
            </section>

            <section id="evidence" className="flex flex-col gap-3">
              <div>
                <h2 className="text-lg font-semibold">Collected evidence</h2>
                <p className="text-sm text-neutral-500">
                  Tool output is redacted, tenant-scoped, hashed, and treated as untrusted data.
                </p>
              </div>
              {investigation.evidence.map((item) => (
                <article
                  id={`evidence-${item.id}`}
                  key={item.id}
                  className="scroll-mt-6 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-mono text-sm font-semibold">{item.tool_name}</h3>
                    <time className="text-xs text-neutral-500">{formatTime(item.observed_at)}</time>
                  </div>
                  <p className="mt-1 text-xs text-neutral-500">
                    SHA-256: <span className="break-all font-mono">{item.content_sha256}</span>
                  </p>
                  <details className="mt-3">
                    <summary className="cursor-pointer text-sm font-medium">
                      View redacted data
                    </summary>
                    <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded bg-neutral-100 p-3 text-xs dark:bg-neutral-900">
                      {pretty(item.content)}
                    </pre>
                  </details>
                </article>
              ))}
              {investigation.evidence.length === 0 && investigation.status === "COMPLETED" && (
                <p className="rounded-lg border border-dashed border-neutral-300 p-5 text-sm text-neutral-500 dark:border-neutral-700">
                  No evidence was returned. Review the recorded evidence gaps and integration
                  configuration.
                </p>
              )}
            </section>

            <p className="text-xs text-neutral-500">
              This workflow collects evidence and proposes an unconfirmed hypothesis. It does not
              run customer code, generate patches, or open pull requests.
            </p>
          </>
        )}
      </main>
    </div>
  );
}
