import type { TicketPriority, TicketStatus } from "@/lib/api";

const STATUS_STYLES: Record<TicketStatus, string> = {
  OPEN: "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300",
  INVESTIGATING: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  ROOT_CAUSE_FOUND: "bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300",
  FIX_PROPOSED: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  VALIDATING: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  RESOLVED: "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300",
  ESCALATED: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
};

const PRIORITY_STYLES: Record<TicketPriority, string> = {
  LOW: "text-neutral-500 dark:text-neutral-400",
  MEDIUM: "text-blue-600 dark:text-blue-400",
  HIGH: "text-amber-600 dark:text-amber-400",
  CRITICAL: "text-red-600 dark:text-red-400 font-semibold",
};

export function StatusBadge({ status }: { status: TicketStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${STATUS_STYLES[status]}`}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  return (
    <span className={`text-xs tracking-wide uppercase ${PRIORITY_STYLES[priority]}`}>
      {priority}
    </span>
  );
}
