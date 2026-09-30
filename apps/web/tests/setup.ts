import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import "@testing-library/jest-dom/vitest";

// RTL's automatic cleanup only self-registers when it detects a *global*
// afterEach (i.e. `test.globals: true`). We import hooks explicitly instead
// (see vitest.config.ts), so we register cleanup ourselves.
afterEach(() => {
  cleanup();
});
