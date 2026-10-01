"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { Logo } from "@/components/Logo";
import { logout } from "@/lib/api";

const LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/tickets", label: "Tickets" },
  { href: "/customers", label: "Customers" },
] as const;

export function TopNav({ active, userEmail }: { active?: string; userEmail?: string }) {
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-10 border-b border-neutral-200 bg-background/80 backdrop-blur-sm dark:border-neutral-800">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <Link href="/" className="transition-opacity hover:opacity-80">
          <Logo size={48} wordmarkClassName="text-2xl" />
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`rounded-md px-3 py-1.5 font-medium transition-colors ${
                active?.startsWith(link.href)
                  ? "bg-brand text-brand-ink"
                  : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-900"
              }`}
            >
              {link.label}
            </Link>
          ))}
          {userEmail ? (
            <>
              <span className="ml-2 hidden text-xs text-neutral-500 sm:inline">{userEmail}</span>
              <button
                onClick={handleLogout}
                className="rounded-md px-3 py-1.5 font-medium text-neutral-600 transition-colors hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-900"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="rounded-md px-3 py-1.5 font-medium text-neutral-600 transition-colors hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-900"
            >
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
