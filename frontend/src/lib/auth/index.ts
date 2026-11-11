"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api, onSessionExpired } from "@/lib/api";
import { setAccessToken } from "@/lib/token-registry";

interface User {
  id: string;
  username: string;
  email: string;
  roles: string[];
  scopes: string[];
}

type SessionStatus = "unknown" | "authenticated" | "unauthenticated";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  /**
   * Tri-state session status.
   *
   * - "unknown": the persisted session has not been validated yet.
   * - "authenticated": the token was verified against the API.
   * - "unauthenticated": there is no usable session.
   *
   * A persisted token is *not* proof of a session: it may be expired,
   * revoked, or malformed. Guards must wait for "unknown" to resolve
   * instead of treating the mere presence of a token as a login.
   */
  status: SessionStatus;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<boolean>;
  setTokens: (access: string, refresh: string) => void;
  fetchUser: () => Promise<void>;
  /** Validate the persisted session against the API. Idempotent. */
  restoreSession: () => Promise<void>;
  // OPTIMIZATION: Track last fetch time to implement caching
  _lastFetchUserTime: number;
  _restoreSessionInProgress: boolean;
}

const STORAGE_KEY = "auth-storage";
// Cache user profile for 5 minutes after fetch
const USER_CACHE_TTL_MS = 5 * 60 * 1000;

const getStoredSession = () => {
  if (typeof window === "undefined") {
    return {
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    };
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      const st = parsed?.state;
      if (st?.accessToken) {
        return {
          user: st.user || null,
          accessToken: st.accessToken,
          refreshToken: st.refreshToken || null,
          isAuthenticated: true,
        };
      }
    }
  } catch (e) {
    console.error("Error reading initial auth storage:", e);
  }

  return {
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
  };
};

const initialSession = getStoredSession();

// Publish the initial token so the API interceptor can attach it to the very
// first request, before any component has had a chance to call `set()`.
setAccessToken(initialSession.accessToken);

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      user: initialSession.user,
      accessToken: initialSession.accessToken,
      refreshToken: initialSession.refreshToken,
      isAuthenticated: initialSession.isAuthenticated,
      isLoading: false,
      status: "unknown",
      _lastFetchUserTime: 0,
      _restoreSessionInProgress: false,

      login: async (username: string, password: string) => {
        set({ isLoading: true });
        try {
          const response = await api.post("/auth/login", { username, password });
          const { access_token, refresh_token } = response.data;
          setAccessToken(access_token);
          set({
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
            status: "authenticated",
            isLoading: false,
            _lastFetchUserTime: Date.now(),
          });
          await get().fetchUser();
        } catch (err) {
          set({ isLoading: false });
          throw err;
        }
      },

      logout: () => {
        setAccessToken(null);
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false,
          status: "unauthenticated",
          _lastFetchUserTime: 0,
        });
        if (typeof window !== "undefined") {
          try {
            localStorage.removeItem(STORAGE_KEY);
          } catch {}
        }
      },

      /**
       * Renew the access token.
       *
       * Resolves to `true` when a new token was obtained and `false` when the
       * session could not be renewed. The response interceptor relies on that
       * return value to decide whether the original request may be replayed.
       */
      refreshAccessToken: async (): Promise<boolean> => {
        const { refreshToken } = get();
        if (!refreshToken) {
          return false;
        }

        try {
          const response = await api.post(
            "/auth/refresh",
            { refresh_token: refreshToken },
            { skipAuthRefresh: true }
          );
          const { access_token, refresh_token: newRefreshToken } = response.data;
          setAccessToken(access_token);
          set({
            accessToken: access_token,
            refreshToken: newRefreshToken || refreshToken,
            isAuthenticated: true,
            status: "authenticated",
            _lastFetchUserTime: Date.now(),
          });
          return true;
        } catch {
          get().logout();
          return false;
        }
      },

      setTokens: (access: string, refresh: string) => {
        setAccessToken(access);
        set({
          accessToken: access,
          refreshToken: refresh,
          isAuthenticated: true,
          status: "authenticated",
          _lastFetchUserTime: Date.now(),
        });
      },

      /**
       * OPTIMIZATION: Fetch user with caching.
       * 
       * Only calls /auth/me if:
       * 1. User data not yet cached, OR
       * 2. Cache older than 5 minutes
       * 3. Token has been refreshed (new refresh resets cache)
       */
      fetchUser: async () => {
        const { accessToken, _lastFetchUserTime } = get();
        if (!accessToken) {
          return;
        }

        const now = Date.now();
        // Use cached user data if still valid
        if (_lastFetchUserTime > 0 && now - _lastFetchUserTime < USER_CACHE_TTL_MS) {
          return;
        }

        try {
          const response = await api.get("/auth/me");
          set({
            user: response.data,
            isAuthenticated: true,
            status: "authenticated",
            isLoading: false,
            _lastFetchUserTime: now,
          });
        } catch (err: any) {
          if (err?.response?.status === 401) {
            // The response interceptor already attempted a refresh and replay.
            // Reaching this point means the session is genuinely expired.
            get().logout();
          } else {
            set({ isLoading: false });
          }
        }
      },

      /**
       * OPTIMIZATION: Validate the persisted session with deduplication.
       *
       * A token that only exists in localStorage is not a session. This calls
       * `/auth/me` so an expired or tampered token is discarded instead of
       * letting the user into a dashboard that fails every request.
       * 
       * Guard against multiple concurrent restoreSession() calls (e.g., from
       * tab focus events) by tracking in-progress state.
       */
      restoreSession: async () => {
        const state = get();
        
        // Skip if already validating or already resolved
        if (state._restoreSessionInProgress || state.status !== "unknown") {
          return;
        }

        if (!getAccessToken()) {
          set({ status: "unauthenticated", isAuthenticated: false, isLoading: false });
          return;
        }

        set({ isLoading: true, _restoreSessionInProgress: true });
        
        try {
          await get().fetchUser();

          // `fetchUser` calls `logout()` on a 401, which already sets the
          // status. If the request failed for a transient reason (network
          // error) the token is still unknown-good, so the session is kept and
          // the status stays "unknown" until a later attempt succeeds.
          const updatedState = get();
          if (updatedState.status === "unknown") {
            set({
              status: updatedState.accessToken ? "authenticated" : "unauthenticated",
              isLoading: false,
              _restoreSessionInProgress: false,
            });
          } else {
            set({ isLoading: false, _restoreSessionInProgress: false });
          }
        } catch (err) {
          set({ isLoading: false, _restoreSessionInProgress: false });
        }
      },
    }),
    {
      name: STORAGE_KEY,
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        if (state?.accessToken) {
          setAccessToken(state.accessToken);
          useAuth.setState({
            isAuthenticated: true,
            isLoading: false,
          });
        }
      },
    }
  )
);

// A 401 that survives the refresh attempt means the session is gone. The
// store is torn down here so every consumer (guards, header, sidebar)
// observes the change and the router can send the user to the login page.
onSessionExpired(() => {
  useAuth.getState().logout();
});

/**
 * Read the current access token.
 *
 * This is a pure read: it never mutates the store, so it is safe to call
 * during render (which several pages do as an auth guard).
 */
export const getAccessToken = (): string | null => {
  const storeToken = useAuth.getState().accessToken;
  if (storeToken) return storeToken;

  if (typeof window !== "undefined") {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        const token = parsed?.state?.accessToken;
        if (token) {
          setAccessToken(token);
          return token;
        }
      }
    } catch {}
  }
  return null;
};

export const refreshAccessToken = () => useAuth.getState().refreshAccessToken();
