"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

/**
 * useAuthGuard - the single source of truth for "is this request allowed to
 * render a protected page?".
 *
 * Problems this replaces:
 *
 *  1. The mere presence of a token in localStorage was treated as a session.
 *     An expired or tampered token let the user into the dashboard, where
 *     every API call then failed with 401.
 *  2. Each page implemented its own guard, and most of them checked the
 *     token only on mount. When the session expired *while* the page was
 *     open, the user was left staring at an empty dashboard.
 *  3. The redirect target was hard-coded, so a user who landed on a deep link
 *     lost their place.
 *
 * The guard now waits for the persisted session to be validated against
 * `/auth/me`, re-validates whenever the tab regains focus, and redirects to
 * the login page with a `next` parameter so the original destination can be
 * restored after a successful login.
 *
 * Returns { ready: boolean, authenticated: boolean } - render the protected
 * content only when `ready` is true.
 * 
 * OPTIMIZATION: Track last focus time to avoid excessive re-validation
 */
export function useAuthGuard(options?: { redirectTo?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, status, restoreSession } = useAuth();
  const [ready, setReady] = useState(false);
  
  // OPTIMIZATION: Track when we last re-validated to avoid hammering /auth/me
  // on rapid focus events. Minimum 5 second gap between re-validations.
  const lastRestoreTimeRef = useRef<number>(0);
  const RESTORE_MIN_INTERVAL_MS = 5000;

  const redirectTo = options?.redirectTo ?? "/login";

  useEffect(() => {
    // Validate the persisted session exactly once, on the first render.
    void restoreSession();
  }, [restoreSession]);

  useEffect(() => {
    if (status === "unknown") {
      setReady(false);
      return;
    }

    if (status === "unauthenticated" || !isAuthenticated) {
      const next = encodeURIComponent(pathname || "/dashboard");
      router.replace(`${redirectTo}?next=${next}`);
      return;
    }

    setReady(true);
  }, [status, isAuthenticated, pathname, redirectTo, router]);

  // OPTIMIZATION: Debounce focus/visibility change handlers to prevent
  // rapid multiple restoreSession() calls when user switches tabs or windows
  const handleVisibility = useCallback(() => {
    if (document.visibilityState !== "visible") {
      return;
    }

    const now = Date.now();
    // Skip re-validation if we just did it recently
    if (now - lastRestoreTimeRef.current < RESTORE_MIN_INTERVAL_MS) {
      return;
    }

    lastRestoreTimeRef.current = now;
    void restoreSession();
  }, [restoreSession]);

  useEffect(() => {
    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("focus", handleVisibility);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("focus", handleVisibility);
    };
  }, [handleVisibility]);

  return { ready, authenticated: isAuthenticated && status === "authenticated" };
}
