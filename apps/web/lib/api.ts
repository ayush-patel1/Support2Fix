/**
 * Minimal typed API client. The browser always calls same-origin `/api/*`
 * (proxied to FastAPI by the Next.js rewrite in next.config.ts) — see
 * ADR-001 D10. There is no base-URL configuration here on purpose: adding
 * one would be an easy way to accidentally reintroduce cross-origin calls.
 */

export interface HealthStatus {
  status: "ok" | "degraded";
  database: "ok" | "unreachable";
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    /** The RFC 9457 problem+json `detail`, when the API sent one — this is
     * the human-readable message (e.g. "Cannot move a ticket from OPEN to
     * RESOLVED...") and should be preferred over `message` for display. */
    public readonly detail: string | undefined,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "support2fix",
      ...init?.headers,
    },
  });

  const body: unknown = await res.json().catch(() => undefined);

  if (!res.ok && res.status !== 503) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : undefined;
    throw new ApiError(res.status, detail, detail ?? `Request to ${path} failed: ${res.status}`);
  }

  return body as T;
}

function query(params: Record<string, string | number | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return "?" + new URLSearchParams(entries as [string, string][]).toString();
}

export function getHealth(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>("/v1/health");
}

// --- Auth & organizations (Phase 2) ------------------------------------

export type Role = "ADMIN" | "ENGINEER" | "SUPPORT" | "VIEWER";

export interface User {
  id: string;
  email: string;
  is_active: boolean;
}

export interface Membership {
  organization_id: string;
  organization_name: string;
  role: Role;
}

export interface MeResponse {
  user: User;
  memberships: Membership[];
  active_organization_id: string | null;
}

export function register(data: {
  email: string;
  password: string;
  organization_name: string;
}): Promise<User> {
  return apiFetch<User>("/v1/auth/register", { method: "POST", body: JSON.stringify(data) });
}

export function login(data: { email: string; password: string }): Promise<User> {
  return apiFetch<User>("/v1/auth/login", { method: "POST", body: JSON.stringify(data) });
}

export async function logout(): Promise<void> {
  await apiFetch<void>("/v1/auth/logout", { method: "POST" });
}

export function getMe(): Promise<MeResponse> {
  return apiFetch<MeResponse>("/v1/auth/me");
}

// --- Tickets (Phase 3) ------------------------------------------------

export type TicketPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type TicketStatus =
  | "OPEN"
  | "INVESTIGATING"
  | "ROOT_CAUSE_FOUND"
  | "FIX_PROPOSED"
  | "VALIDATING"
  | "RESOLVED"
  | "ESCALATED";
export type TicketEventType = "CREATED" | "FIELD_CHANGED" | "STATUS_CHANGED" | "COMMENT";

export interface Ticket {
  id: string;
  customer_id: string;
  created_by: string | null;
  title: string;
  description: string;
  priority: TicketPriority;
  status: TicketStatus;
  created_at: string;
  updated_at: string;
}

export interface TicketEvent {
  id: string;
  ticket_id: string;
  actor_user_id: string | null;
  type: TicketEventType;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface TicketListResponse {
  items: Ticket[];
  next_cursor: string | null;
}

export function listTickets(filters: {
  status?: TicketStatus;
  priority?: TicketPriority;
  customer_id?: string;
  search?: string;
  cursor?: string;
}): Promise<TicketListResponse> {
  return apiFetch<TicketListResponse>(`/v1/tickets${query(filters)}`);
}

export function getTicket(id: string): Promise<Ticket> {
  return apiFetch<Ticket>(`/v1/tickets/${id}`);
}

export function createTicket(data: {
  customer_id: string;
  title: string;
  description?: string;
  priority?: TicketPriority;
}): Promise<Ticket> {
  return apiFetch<Ticket>("/v1/tickets", { method: "POST", body: JSON.stringify(data) });
}

export function updateTicket(
  id: string,
  data: { title?: string; description?: string; priority?: TicketPriority },
): Promise<Ticket> {
  return apiFetch<Ticket>(`/v1/tickets/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export function changeTicketStatus(id: string, status: TicketStatus): Promise<Ticket> {
  return apiFetch<Ticket>(`/v1/tickets/${id}/status`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
}

export function listTicketEvents(id: string): Promise<TicketEvent[]> {
  return apiFetch<TicketEvent[]>(`/v1/tickets/${id}/events`);
}

export function addTicketComment(id: string, comment: string): Promise<TicketEvent> {
  return apiFetch<TicketEvent>(`/v1/tickets/${id}/events`, {
    method: "POST",
    body: JSON.stringify({ comment }),
  });
}

// --- Customer context (Phase 4) ---------------------------------------

export type CustomerTier = "FREE" | "STANDARD" | "ENTERPRISE";
export type RepositoryProvider = "LOCAL" | "GITHUB" | "GITLAB";
export type DeploymentStatus = "IN_PROGRESS" | "SUCCESS" | "FAILED" | "ROLLED_BACK";

export interface Customer {
  id: string;
  name: string;
  external_ref: string | null;
  tier: CustomerTier;
  created_at: string;
}

export interface Environment {
  id: string;
  customer_id: string;
  name: string;
  created_at: string;
}

export interface Service {
  id: string;
  environment_id: string;
  name: string;
  language: string | null;
  owner_team: string | null;
}

export interface Repository {
  id: string;
  service_id: string;
  provider: RepositoryProvider;
  full_name: string;
  default_branch: string;
}

export interface Deployment {
  id: string;
  service_id: string;
  version: string;
  commit_sha: string | null;
  status: DeploymentStatus;
  deployed_at: string;
}

export interface ServiceOverview {
  service: Service;
  repositories: Repository[];
  deployments: Deployment[];
}

export interface EnvironmentOverview {
  environment: Environment;
  services: ServiceOverview[];
}

export function listCustomers(): Promise<Customer[]> {
  return apiFetch<Customer[]>("/v1/customers");
}

export function getCustomer(id: string): Promise<Customer> {
  return apiFetch<Customer>(`/v1/customers/${id}`);
}

export function createCustomer(data: {
  name: string;
  external_ref?: string;
  tier?: CustomerTier;
}): Promise<Customer> {
  return apiFetch<Customer>("/v1/customers", { method: "POST", body: JSON.stringify(data) });
}

export function listEnvironments(customerId: string): Promise<Environment[]> {
  return apiFetch<Environment[]>(`/v1/customers/${customerId}/environments`);
}

export function createEnvironment(customerId: string, name: string): Promise<Environment> {
  return apiFetch<Environment>(`/v1/customers/${customerId}/environments`, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function getEnvironmentOverview(
  customerId: string,
  environmentId: string,
): Promise<EnvironmentOverview> {
  return apiFetch<EnvironmentOverview>(`/v1/customers/${customerId}/environments/${environmentId}`);
}

export function createService(
  customerId: string,
  environmentId: string,
  data: { name: string; language?: string; owner_team?: string },
): Promise<Service> {
  return apiFetch<Service>(`/v1/customers/${customerId}/environments/${environmentId}/services`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function createRepository(
  serviceId: string,
  data: { full_name: string; provider?: RepositoryProvider; default_branch?: string },
): Promise<Repository> {
  return apiFetch<Repository>(`/v1/services/${serviceId}/repositories`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function createDeployment(
  serviceId: string,
  data: { version: string; commit_sha?: string; status?: DeploymentStatus },
): Promise<Deployment> {
  return apiFetch<Deployment>(`/v1/services/${serviceId}/deployments`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}
