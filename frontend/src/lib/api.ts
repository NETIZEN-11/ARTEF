import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

declare module "axios" {
  // Marker used to opt a request out of the automatic 401 refresh-and-retry.
  export interface AxiosRequestConfig {
    skipAuthRefresh?: boolean;
  }
}
import { getRegisteredAccessToken } from "./token-registry";

export const getApiBaseUrl = () => {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) {
    return configured.endsWith("/api/v1")
      ? configured
      : `${configured.replace(/\/+$/, "")}/api/v1`;
  }

  if (typeof window !== "undefined") {
    return `${window.location.origin}/api/v1`;
  }

  return "/api/v1";
};

const API_URL = getApiBaseUrl();

/** Default request timeout. Extended to 45s to accommodate free cloud tier cold starts. */
export const API_TIMEOUT_MS = 45_000;

/**
 * Notified when the session can no longer be renewed.
 *
 * The auth store subscribes to this so an expired session tears down the
 * store and the router sends the user back to the login page. Without it a
 * dead session left the user on a dashboard whose every request returned 401.
 */
type SessionExpiredListener = () => void;
const sessionExpiredListeners = new Set<SessionExpiredListener>();

export const onSessionExpired = (listener: SessionExpiredListener): (() => void) => {
  sessionExpiredListeners.add(listener);
  return () => {
    sessionExpiredListeners.delete(listener);
  };
};

const notifySessionExpired = () => {
  sessionExpiredListeners.forEach((listener) => {
    try {
      listener();
    } catch {
      /* a failing listener must never break the request pipeline */
    }
  });
};

export const api = axios.create({
  baseURL: API_URL,
  timeout: API_TIMEOUT_MS,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // The token is read from the registry to avoid a circular module import
    // between api.ts and lib/auth.
    const token = getRegisteredAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean; skipAuthRefresh?: boolean })
      | undefined;

    const isAuthEndpoint = originalRequest?.url?.includes("/auth/refresh");

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.skipAuthRefresh &&
      !isAuthEndpoint
    ) {
      originalRequest._retry = true;

      const { refreshAccessToken } = await import("./auth");
      const refreshed = await refreshAccessToken();

      // refreshAccessToken() resolves to false when the session could not be
      // renewed. Replaying the request with the stale token would only
      // produce a second 401 and hide the real cause, so the original error
      // is propagated instead.
      if (!refreshed) {
        notifySessionExpired();
        return Promise.reject(error);
      }

      const token = getRegisteredAccessToken();
      if (token && originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${token}`;
      }
      return api(originalRequest);
    }

    return Promise.reject(error);
  }
);

export const handleApiError = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") {
      return "The request timed out. Please try again.";
    }
    if (error.code === "ERR_CANCELED") {
      return "The request was cancelled.";
    }
    const data = error.response?.data;
    if (typeof data?.detail === "string") {
      return data.detail;
    }
    if (typeof data?.detail?.message === "string") {
      return data.detail.message;
    }
    if (typeof data?.message === "string") {
      return data.message;
    }
    if (!error.response) {
      return "Unable to reach the ARTEF API. Check that the backend is running.";
    }
    return error.message;
  }
  return "An unexpected error occurred";
};
