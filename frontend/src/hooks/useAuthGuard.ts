"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth, getAccessToken } from "@/lib/auth";

/**
 * useAuthGuard - Prevents redirect-on-refresh issues.
 * Synchronously checks localStorage for a token before trusting Zustand's
 * reactive state, which may not be hydrated yet on first render.
 *
 * Returns { ready: boolean } â€” render your page only when ready === true.
 */
export function useAuthGuard() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = getAccessToken();
    if (token) {
      setReady(true);
      return;
    }

    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
      return;
    }

    if (!isLoading && isAuthenticated) {
      setReady(true);
    }
  }, [isAuthenticated, isLoading, router]);

  return { ready };
}
