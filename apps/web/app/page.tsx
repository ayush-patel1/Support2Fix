import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-start justify-center gap-4 px-6">
      <h1 className="text-3xl font-semibold">Support2Fix</h1>
      <p className="text-slate-600 dark:text-slate-400">
        Turns a customer support issue into an evidence-backed engineering investigation.
      </p>
      <Link
        href="/dashboard"
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
      >
        Go to dashboard
      </Link>
    </main>
  );
}
