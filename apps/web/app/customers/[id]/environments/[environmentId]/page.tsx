"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { TopNav } from "@/components/TopNav";
import {
  ApiError,
  createDeployment,
  createRepository,
  createService,
  type DeploymentStatus,
  type EnvironmentOverview,
  getEnvironmentOverview,
  type RepositoryProvider,
} from "@/lib/api";

export default function EnvironmentOverviewPage() {
  const params = useParams<{ id: string; environmentId: string }>();
  const { id: customerId, environmentId } = params;

  const [overview, setOverview] = useState<EnvironmentOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showServiceForm, setShowServiceForm] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setOverview(await getEnvironmentOverview(customerId, environmentId));
    } catch (err) {
      setError(
        err instanceof ApiError ? (err.detail ?? err.message) : "Failed to load environment.",
      );
    }
  }, [customerId, environmentId]);

  useEffect(() => {
    // See app/tickets/page.tsx: `refresh` is shared with every
    // create-service/repository/deployment handler below, not single-use.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, [refresh]);

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

  if (!overview) {
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
      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-6 py-10">
        <div>
          <Link
            href={`/customers/${customerId}`}
            className="text-sm text-neutral-500 hover:underline"
          >
            ← Back to customer
          </Link>
          <h1 className="text-2xl font-semibold">{overview.environment.name}</h1>
          <p className="text-sm text-neutral-500">Environment overview</p>
        </div>

        <div className="flex items-center justify-between">
          <h2 className="font-medium">Services</h2>
          <button
            onClick={() => setShowServiceForm((v) => !v)}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm font-medium hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
          >
            {showServiceForm ? "Cancel" : "New service"}
          </button>
        </div>

        {showServiceForm && (
          <NewServiceForm
            customerId={customerId}
            environmentId={environmentId}
            onCreated={refresh}
            onDone={() => setShowServiceForm(false)}
          />
        )}

        {overview.services.length === 0 ? (
          <p className="text-sm text-neutral-500">No services in this environment yet.</p>
        ) : (
          <div className="flex flex-col gap-4">
            {overview.services.map(({ service, repositories, deployments }) => (
              <div
                key={service.id}
                className="flex flex-col gap-3 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800"
              >
                <div className="flex items-baseline justify-between">
                  <span className="font-medium">{service.name}</span>
                  <span className="text-xs text-neutral-500">
                    {service.language ?? "—"} {service.owner_team ? `· ${service.owner_team}` : ""}
                  </span>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="flex flex-col gap-2">
                    <span className="text-xs font-medium tracking-wide text-neutral-500 uppercase">
                      Repositories
                    </span>
                    {repositories.length === 0 ? (
                      <span className="text-sm text-neutral-400">None yet.</span>
                    ) : (
                      <ul className="flex flex-col gap-1 text-sm">
                        {repositories.map((r) => (
                          <li key={r.id} className="font-mono text-xs">
                            {r.provider}: {r.full_name} @ {r.default_branch}
                          </li>
                        ))}
                      </ul>
                    )}
                    <AddRepositoryForm serviceId={service.id} onCreated={refresh} />
                  </div>

                  <div className="flex flex-col gap-2">
                    <span className="text-xs font-medium tracking-wide text-neutral-500 uppercase">
                      Deployments
                    </span>
                    {deployments.length === 0 ? (
                      <span className="text-sm text-neutral-400">None yet.</span>
                    ) : (
                      <ul className="flex flex-col gap-1 text-sm">
                        {deployments.map((d) => (
                          <li key={d.id} className="font-mono text-xs">
                            {d.version} ({d.status}) —{" "}
                            {new Date(d.deployed_at).toLocaleDateString()}
                          </li>
                        ))}
                      </ul>
                    )}
                    <AddDeploymentForm serviceId={service.id} onCreated={refresh} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function NewServiceForm({
  customerId,
  environmentId,
  onCreated,
  onDone,
}: {
  customerId: string;
  environmentId: string;
  onCreated: () => void;
  onDone: () => void;
}) {
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("");
  const [ownerTeam, setOwnerTeam] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createService(customerId, environmentId, {
        name,
        language: language || undefined,
        owner_team: ownerTeam || undefined,
      });
      onCreated();
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? (err.detail ?? err.message) : "Failed to create service.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-wrap items-end gap-2 rounded-lg border border-neutral-200 p-3 dark:border-neutral-800"
    >
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Service name"
        required
        className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
      />
      <input
        value={language}
        onChange={(e) => setLanguage(e.target.value)}
        placeholder="Language (optional)"
        className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
      />
      <input
        value={ownerTeam}
        onChange={(e) => setOwnerTeam(e.target.value)}
        placeholder="Owner team (optional)"
        className="rounded-md border border-neutral-300 bg-background px-3 py-1.5 text-sm dark:border-neutral-700"
      />
      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-brand px-3 py-1.5 text-sm font-semibold text-brand-ink disabled:opacity-50"
      >
        {submitting ? "Creating…" : "Create"}
      </button>
      {error && <p className="w-full text-sm text-red-600 dark:text-red-400">{error}</p>}
    </form>
  );
}

function AddRepositoryForm({ serviceId, onCreated }: { serviceId: string; onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [fullName, setFullName] = useState("");
  const [provider, setProvider] = useState<RepositoryProvider>("LOCAL");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await createRepository(serviceId, { full_name: fullName, provider });
      setFullName("");
      setOpen(false);
      onCreated();
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-fit text-xs text-brand-ink underline dark:text-brand"
      >
        + Add repository
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        value={fullName}
        onChange={(e) => setFullName(e.target.value)}
        placeholder="org/repo"
        required
        className="min-w-0 flex-1 rounded-md border border-neutral-300 bg-background px-2 py-1 text-xs dark:border-neutral-700"
      />
      <select
        value={provider}
        onChange={(e) => setProvider(e.target.value as RepositoryProvider)}
        className="rounded-md border border-neutral-300 bg-background px-2 py-1 text-xs dark:border-neutral-700"
      >
        {(["LOCAL", "GITHUB", "GITLAB"] as const).map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </select>
      <button
        type="submit"
        disabled={submitting}
        className="rounded-md border border-neutral-300 px-2 py-1 text-xs font-medium disabled:opacity-50 dark:border-neutral-700"
      >
        Add
      </button>
    </form>
  );
}

function AddDeploymentForm({ serviceId, onCreated }: { serviceId: string; onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [version, setVersion] = useState("");
  const [status, setStatus] = useState<DeploymentStatus>("SUCCESS");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await createDeployment(serviceId, { version, status });
      setVersion("");
      setOpen(false);
      onCreated();
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-fit text-xs text-brand-ink underline dark:text-brand"
      >
        + Add deployment
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        value={version}
        onChange={(e) => setVersion(e.target.value)}
        placeholder="v1.2.3"
        required
        className="min-w-0 flex-1 rounded-md border border-neutral-300 bg-background px-2 py-1 text-xs dark:border-neutral-700"
      />
      <select
        value={status}
        onChange={(e) => setStatus(e.target.value as DeploymentStatus)}
        className="rounded-md border border-neutral-300 bg-background px-2 py-1 text-xs dark:border-neutral-700"
      >
        {(["IN_PROGRESS", "SUCCESS", "FAILED", "ROLLED_BACK"] as const).map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      <button
        type="submit"
        disabled={submitting}
        className="rounded-md border border-neutral-300 px-2 py-1 text-xs font-medium disabled:opacity-50 dark:border-neutral-700"
      >
        Add
      </button>
    </form>
  );
}
