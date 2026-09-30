import Link from "next/link";
import { HealthBadge } from "@/components/HealthBadge";
import { TopNav } from "@/components/TopNav";

function PhaseBadge({ children }: { children: string }) {
  return (
    <span className="rounded-full bg-neutral-100 px-2 py-0.5 font-mono text-[10px] font-medium tracking-wider text-neutral-500 uppercase dark:bg-neutral-800 dark:text-neutral-400">
      {children}
    </span>
  );
}

function DashboardCard({
  title,
  description,
  phase,
  href,
  cta,
}: {
  title: string;
  description: string;
  phase: string;
  href?: string;
  cta?: string;
}) {
  const content = (
    <>
      <div className="flex items-start justify-between gap-2">
        <h2 className="font-semibold text-neutral-900 dark:text-neutral-100">{title}</h2>
        <PhaseBadge>{phase}</PhaseBadge>
      </div>
      <p className="text-sm text-neutral-600 dark:text-neutral-400">{description}</p>
      {href && cta && (
        <span className="mt-auto pt-2 text-sm font-medium text-brand-ink group-hover:underline dark:text-brand">
          {cta} →
        </span>
      )}
    </>
  );

  const baseClasses = "group flex h-full flex-col gap-2 rounded-lg border p-4 transition-colors";

  if (href) {
    return (
      <Link
        href={href}
        className={`${baseClasses} border-neutral-200 hover:border-brand hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900`}
      >
        {content}
      </Link>
    );
  }

  return (
    <div
      className={`${baseClasses} cursor-not-allowed border-dashed border-neutral-200 opacity-70 dark:border-neutral-800`}
      title={`Not built yet — arrives in ${phase}`}
    >
      {content}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <TopNav active="/dashboard" />

      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-6 py-10">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">Dashboard</h1>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Organization overview</p>
          </div>
          <HealthBadge />
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <DashboardCard
            title="Tickets"
            description="Create, triage, search and track support tickets."
            phase="Phase 3"
          />
          <DashboardCard
            title="Customers"
            description="Environments, services, repositories and deployments."
            phase="Phase 4"
          />
          <DashboardCard
            title="Investigation console"
            description="Root cause, evidence, reproduction, fix and approval — end to end."
            phase="Design preview"
            href="/investigations/2841"
            cta="View preview"
          />
        </div>
      </main>
    </div>
  );
}
