import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HealthBadge } from "@/components/HealthBadge";

describe("HealthBadge", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows a loading state, then healthy when the API is OK", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ status: "ok", database: "ok" }),
      }),
    );

    render(<HealthBadge />);

    expect(screen.getByTestId("health-badge")).toHaveTextContent("Checking API…");
    await waitFor(() =>
      expect(screen.getByTestId("health-badge")).toHaveTextContent("API + database OK"),
    );
  });

  it("shows a degraded state when the database is unreachable (503)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({ status: "degraded", database: "unreachable" }),
      }),
    );

    render(<HealthBadge />);

    await waitFor(() =>
      expect(screen.getByTestId("health-badge")).toHaveTextContent("API up, database unreachable"),
    );
  });

  it("shows an error state when the fetch itself fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

    render(<HealthBadge />);

    await waitFor(() =>
      expect(screen.getByTestId("health-badge")).toHaveTextContent("API unreachable"),
    );
  });
});
