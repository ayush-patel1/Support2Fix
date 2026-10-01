"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, getMe, type MeResponse } from "@/lib/api";

/** Redirects to /login on a 401 instead of letting a protected page render

 * its data-fetch error inline. `loading` stays true until the redirect
 * fires or `me` is known, so callers can gate their own rendering on it.
 */
export function useAuthGuard(): { me: MeResponse | null; loading: boolean } {
  const router = useRouter();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          router.replace("/login");
        }
      })
      .finally(() => setLoading(false));
  }, [router]);

  return { me, loading };
}
