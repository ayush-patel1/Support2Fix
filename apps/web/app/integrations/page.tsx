"use client";

import { useCallback, useEffect, useState } from "react";
import { TopNav } from "@/components/TopNav";
import {
  ApiError,
  createIntegration,
  deleteIntegration,
  isActiveOrganizationAdmin,
  type Integration,
  listIntegrations,
  testIntegration,
} from "@/lib/api";
import { useAuthGuard } from "@/lib/useAuthGuard";

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? (error.detail ?? error.message) : fallback;
}

export default function IntegrationsPage() {
  const { me, loading: authLoading } = useAuthGuard();
  const isAdmin = me !== null && isActiveOrganizationAdmin(me);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [name, setName] = useState("");
  const [repoPath, setRepoPath] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setIntegrations(await listIntegrations("CODE_HOST"));
    } catch (err) {
      setError(errorMessage(err, "Failed to load repository integrations."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading || !isAdmin) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [authLoading, isAdmin, load]);

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const created = await createIntegration({
        kind: "CODE_HOST",
        name: name.trim(),
        config: { repo_path: repoPath.trim() },
      });
      setIntegrations((current) => [created, ...current]);
      setName("");
      setRepoPath("");
      setNotice("Repository connected.");
    } catch (err) {
      setError(errorMessage(err, "Failed to connect repository."));
    } finally {
      setSaving(false);
    }
  }

  async function handleTest(integration: Integration) {
    setTestingId(integration.id);
    setError(null);
    setNotice(null);
    try {
      const result = await testIntegration(integration.id);
      if (result.ok) {
        setNotice(`${integration.name}: ${result.detail}`);
      } else {
        setError(`${integration.name}: ${result.detail}`);
      }
    } catch (err) {
      setError(errorMessage(err, `Failed to test ${integration.name}.`));
    } finally {
      setTestingId(null);
    }
  }

  async function handleDelete(integration: Integration) {
    setDeletingId(integration.id);
    setError(null);
    setNotice(null);
    try {
      await deleteIntegration(integration.id);
      setIntegrations((current) => current.filter((item) => item.id !== integration.id));
      setNotice(`${integration.name} disconnected.`);
    } catch (err) {
      setError(errorMessage(err, `Failed to disconnect ${integration.name}.`));
    } finally {
      setDeletingId(null);
    }
  }

  if (authLoading || !me) return null;

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <TopNav active="/integrations" userEmail={me.user.email} />
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-6 py-10">
        {!isAdmin ? (
          <section className="rounded-lg border border-neutral-200 p-6 dark:border-neutral-800">
            <h1 className="text-2xl font-semibold">Administrator access required</h1>
            <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
              Repository integrations can only be managed by an administrator of the active
              organization.
            </p>
          </section>
        ) : (
          <>
            <div>
              <h1 className="text-2xl font-semibold">Repository integrations</h1>
              <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
                Connect local Git working trees for evidence collection during investigations.
              </p>
            </div>

            {error && (
              <p
                role="alert"
                className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200"
              >
                {error}
              </p>
            )}
            {notice && (
              <p
                role="status"
                className="rounded-md border border-green-300 bg-green-50 px-4 py-3 text-sm text-green-800 dark:border-green-900 dark:bg-green-950 dark:text-green-200"
              >
                {notice}
              </p>
            )}

            <section className="rounded-lg border border-neutral-200 p-5 dark:border-neutral-800">
              <h2 className="font-semibold">Connect a Git repository</h2>
              <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
                Enter a path to an existing Git working tree visible to the API, tools, and worker.
                Repository contents are read from the current checkout; no Git credentials are
                stored.
              </p>
              <form onSubmit={handleCreate} className="mt-5 grid gap-4 sm:grid-cols-2">
                <label className="grid gap-1.5 text-sm font-medium">
                  Display name
                  <input
                    required
                    maxLength={150}
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="Payments service"
                    className="rounded-md border border-neutral-300 bg-background px-3 py-2 font-normal dark:border-neutral-700"
                  />
                </label>
                <label className="grid gap-1.5 text-sm font-medium">
                  Repository path
                  <input
                    required
                    value={repoPath}
                    onChange={(event) => setRepoPath(event.target.value)}
                    placeholder="/workspace/examples/shopmock"
                    className="rounded-md border border-neutral-300 bg-background px-3 py-2 font-mono text-sm font-normal dark:border-neutral-700"
                  />
                </label>
                <div className="sm:col-span-2">
                  <button
                    type="submit"
                    disabled={saving}
                    className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-brand-ink hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {saving ? "Connecting…" : "Connect repository"}
                  </button>
                </div>
              </form>
              <p className="mt-4 text-xs text-neutral-500 dark:text-neutral-400">
                Docker Compose: mount your repositories parent folder with{" "}
                <code className="font-mono">REPOSITORIES_PATH</code> in{" "}
                <code className="font-mono">.env</code>, then use the corresponding{" "}
                <code className="font-mono">/workspace/…</code> path here. Only organization admins
                can manage integrations.
              </p>
            </section>

            <section className="grid gap-3">
              <h2 className="font-semibold">Connected repositories</h2>
              {loading ? (
                <p className="text-sm text-neutral-500">Loading repositories…</p>
              ) : integrations.length === 0 ? (
                <p className="rounded-lg border border-dashed border-neutral-300 px-4 py-8 text-center text-sm text-neutral-500 dark:border-neutral-700">
                  No repositories connected yet.
                </p>
              ) : (
                integrations.map((integration) => (
                  <article
                    key={integration.id}
                    className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800"
                  >
                    <div className="min-w-0">
                      <h3 className="font-medium">{integration.name}</h3>
                      <p className="mt-1 break-all font-mono text-xs text-neutral-500">
                        {String(integration.config.repo_path ?? "Repository path unavailable")}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={testingId !== null || deletingId !== null}
                        onClick={() => handleTest(integration)}
                        className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-50 disabled:opacity-60 dark:border-neutral-700 dark:hover:bg-neutral-900"
                      >
                        {testingId === integration.id ? "Testing…" : "Test connection"}
                      </button>
                      <button
                        type="button"
                        disabled={testingId !== null || deletingId !== null}
                        onClick={() => handleDelete(integration)}
                        className="rounded-md border border-red-300 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50 disabled:opacity-60 dark:border-red-900 dark:text-red-300 dark:hover:bg-red-950"
                      >
                        {deletingId === integration.id ? "Removing…" : "Disconnect"}
                      </button>
                    </div>
                  </article>
                ))
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}
