import { HealthBadge } from "@/components/HealthBadge";

export default function DashboardPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <HealthBadge />
      </div>
      <p className="text-slate-600 dark:text-slate-400">
        Tickets, investigations and their status will appear here starting Phase 3.
      </p>
    </main>
  );
}
