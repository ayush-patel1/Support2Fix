"use client";

import { useEffect, useState } from "react";
import { getHealth, type HealthStatus } from "@/lib/api";

type State = { kind: "loading" } | { kind: "loaded"; health: HealthStatus } | { kind: "error" };

/**
 * Small status pill showing whether the API (and its database) is reachable.
 * Used on the dashboard so "the app runs" is visible, not just assumed.
 */
export function HealthBadge() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((health) => {
        if (!cancelled) setState({ kind: "loaded", health });
      })
      .catch(() => {
        if (!cancelled) setState({ kind: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const { label, className } = describe(state);

  return (
    <span
      data-testid="health-badge"
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium ${className}`}
    >
      <span className="h-2 w-2 rounded-full bg-current" />
      {label}
    </span>
  );
}

function describe(state: State): { label: string; className: string } {
  switch (state.kind) {
    case "loading":
      return { label: "Checking API…", className: "bg-slate-100 text-slate-600" };
    case "error":
      return { label: "API unreachable", className: "bg-red-100 text-red-700" };
    case "loaded":
      return state.health.status === "ok"
        ? { label: "API + database OK", className: "bg-green-100 text-green-700" }
        : { label: "API up, database unreachable", className: "bg-amber-100 text-amber-700" };
  }
}
