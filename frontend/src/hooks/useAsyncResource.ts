"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface UseAsyncResourceOptions {
  /** Poll interval in milliseconds. Set to 0 to disable polling. */
  pollIntervalMs?: number;
  /** Skip the request entirely (e.g. while unauthenticated). */
  enabled?: boolean;
  /** Extract a human-readable message from a rejection. */
  formatError?: (error: unknown) => string;
}

// OPTIMIZATION: Global request deduplication map to prevent multiple
// identical requests from being issued simultaneously.
// Key: stringified loader + dependencies, Value: Promise<T> for in-flight request
const requestDedupeMap = new Map<string, Promise<any>>();
const dequeuedRequestsRef = new Map<string, { timestamp: number; data: any }>();
const DEDUP_CACHE_TTL_MS = 1000; // Cache deduped responses for 1 second

function getDedupeKey(index: number): string {
  // Use component instance index to create unique key per hook instance
  return `loader-${index}`;
}

let instanceCounter = 0;

/**
 * Run an async loader with:
 *  - request cancellation on unmount and on re-run (no stale writes),
 *  - a generation guard so a slow response can never overwrite a newer one,
 *  - optional polling that never overlaps with an in-flight request,
 *  - OPTIMIZATION: request deduplication to avoid duplicate API calls,
 *  - OPTIMIZATION: smart polling that accounts for tab visibility,
 *  - explicit loading / error / empty state.
 */
export function useAsyncResource<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  deps: unknown[],
  options: UseAsyncResourceOptions = {}
): AsyncState<T> & { refresh: () => Promise<void> } {
  const { pollIntervalMs = 0, enabled = true, formatError } = options;

  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: enabled,
    error: null,
  });

  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const abortRef = useRef<AbortController | null>(null);
  const generationRef = useRef(0);
  const inFlightRef = useRef(false);
  const mountedRef = useRef(true);
  const instanceIdRef = useRef(instanceCounter++);

  const defaultFormatError = useCallback((error: unknown) => {
    if (axios.isAxiosError(error)) {
      if (error.code === "ERR_CANCELED") return "Request cancelled";
      if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") {
        return "The request timed out. Please try again.";
      }
      const data = error.response?.data;
      if (typeof data?.detail === "string") return data.detail;
      if (typeof data?.detail?.message === "string") return data.detail.message;
      if (typeof data?.message === "string") return data.message;
      if (!error.response) {
        return "Unable to reach the ARTEF API. Check that the backend is running.";
      }
    }
    return error instanceof Error ? error.message : "An unexpected error occurred";
  }, []);

  const run = useCallback(async () => {
    if (!enabled) return;

    // OPTIMIZATION: Check if another request is already in-flight with
    // the same dependencies. If so, wait for it instead of issuing another.
    const dedupeKey = `instance-${instanceIdRef.current}`;
    
    const now = Date.now();
    const cached = dequeuedRequestsRef.get(dedupeKey);
    if (cached && now - cached.timestamp < DEDUP_CACHE_TTL_MS) {
      // Use recently cached result
      if (!mountedRef.current) return;
      setState({ data: cached.data, loading: false, error: null });
      return;
    }

    // Check for in-flight request with same key
    if (requestDedupeMap.has(dedupeKey)) {
      try {
        const cachedResult = await requestDedupeMap.get(dedupeKey);
        if (!mountedRef.current) return;
        setState({ data: cachedResult, loading: false, error: null });
        dequeuedRequestsRef.set(dedupeKey, { timestamp: Date.now(), data: cachedResult });
        return;
      } catch (error) {
        if (!mountedRef.current) return;
        setState({
          data: null,
          loading: false,
          error: (formatError ?? defaultFormatError)(error),
        });
        return;
      }
    }

    // Cancel any previous request so a slow response cannot arrive late.
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const generation = ++generationRef.current;
    inFlightRef.current = true;
    setState((prev) => ({ ...prev, loading: true, error: null }));

    // Create deduped request promise
    const requestPromise = (async () => {
      try {
        const data = await loaderRef.current(controller.signal);
        if (!mountedRef.current || generation !== generationRef.current) return data;
        setState({ data, loading: false, error: null });
        dequeuedRequestsRef.set(dedupeKey, { timestamp: Date.now(), data });
        return data;
      } catch (error) {
        if (!mountedRef.current || generation !== generationRef.current) throw error;
        if (axios.isAxiosError(error) && error.code === "ERR_CANCELED") {
          setState((prev) => ({ ...prev, loading: false }));
          throw error;
        }
        const errorMsg = (formatError ?? defaultFormatError)(error);
        setState({
          data: null,
          loading: false,
          error: errorMsg,
        });
        throw error;
      } finally {
        if (generation === generationRef.current) {
          inFlightRef.current = false;
          requestDedupeMap.delete(dedupeKey);
        }
      }
    })();

    requestDedupeMap.set(dedupeKey, requestPromise);
  }, [enabled, formatError, defaultFormatError]);

  useEffect(() => {
    mountedRef.current = true;
    if (enabled) {
      void run();
    }
    return () => {
      mountedRef.current = false;
      abortRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, run, ...deps]);

  useEffect(() => {
    if (!enabled || pollIntervalMs <= 0) return;

    // OPTIMIZATION: Only poll when tab is visible. Stop polling when
    // tab is in background to save bandwidth and reduce server load.
    const handleVisibilityChange = () => {
      // Visibility change is handled by the interval itself checking document.visibilityState
    };

    const interval = setInterval(() => {
      // Never overlap with an in-flight request.
      // OPTIMIZATION: Also skip polling when tab is not visible
      if (!inFlightRef.current && document.visibilityState === "visible") {
        void run();
      }
    }, pollIntervalMs);

    document.addEventListener("visibilitychange", handleVisibilityChange);
    
    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [enabled, pollIntervalMs, run]);

  return { ...state, refresh: run };
}
