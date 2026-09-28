"use client";

import { ThemeProvider } from "next-themes";
import { ReactNode, useEffect } from "react";
import { useAuth } from "@/lib/auth";

export function Providers({ children }: { children: ReactNode }) {
  const { fetchUser, isAuthenticated, isLoading, accessToken } = useAuth();

  useEffect(() => {
    const handler = (e: ErrorEvent) => {
      if (e.message?.includes("startTime")) e.preventDefault();
    };
    const rejHandler = (e: PromiseRejectionEvent) => {
      const msg = (e.reason as any)?.message || String(e.reason);
      if (msg.includes("startTime")) e.preventDefault();
    };
    window.addEventListener("error", handler);
    window.addEventListener("unhandledrejection", rejHandler);
    return () => {
      window.removeEventListener("error", handler);
      window.removeEventListener("unhandledrejection", rejHandler);
    };
  }, []);

  useEffect(() => {
    if (accessToken && !isAuthenticated && !isLoading) {
      fetchUser();
    }
  }, [fetchUser, isAuthenticated, isLoading, accessToken]);

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      {children}
    </ThemeProvider>
  );
}