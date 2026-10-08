"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "@/lib/api";

interface User {
  id: string;
  username: string;
  email: string;
  roles: string[];
  scopes: string[];
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isReady: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<void>;
  setTokens: (access: string, refresh: string) => void;
  fetchUser: () => Promise<void>;
  initializeAuth: () => void;
}

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
    const raw = localStorage.getItem("auth-storage");
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

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      user: initialSession.user,
      accessToken: initialSession.accessToken,
      refreshToken: initialSession.refreshToken,
      isAuthenticated: initialSession.isAuthenticated,
      isLoading: false,
      isReady: true,

      initializeAuth: () => {
        if (typeof window === "undefined") return;
        try {
          const raw = localStorage.getItem("auth-storage");
          if (raw) {
            const parsed = JSON.parse(raw);
            const st = parsed?.state;
            if (st?.accessToken) {
              set({
                user: st.user || null,
                accessToken: st.accessToken,
                refreshToken: st.refreshToken || null,
                isAuthenticated: true,
                isLoading: false,
                isReady: true,
              });
              return;
            }
          }
        } catch {}
      },

      login: async (username: string, password: string) => {
        set({ isLoading: true });
        try {
          const response = await api.post("/auth/login", { username, password });
          const { access_token, refresh_token } = response.data;
          set({
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
            isLoading: false,
            isReady: true,
          });
          await get().fetchUser();
        } catch (err) {
          set({ isLoading: false });
          throw err;
        }
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false,
          isReady: true,
        });
        if (typeof window !== "undefined") {
          try {
            localStorage.removeItem("auth-storage");
          } catch {}
        }
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get();
        if (!refreshToken) return;

        try {
          const response = await api.post("/auth/refresh", { refresh_token: refreshToken });
          const { access_token, refresh_token: newRefreshToken } = response.data;
          set({ accessToken: access_token, refreshToken: newRefreshToken, isAuthenticated: true });
        } catch {
          get().logout();
        }
      },

      setTokens: (access: string, refresh: string) => {
        set({ accessToken: access, refreshToken: refresh, isAuthenticated: true, isReady: true });
      },

      fetchUser: async () => {
        const { accessToken } = get();
        if (!accessToken) {
          return;
        }

        try {
          const response = await api.get("/auth/me");
          set({ user: response.data, isAuthenticated: true, isLoading: false, isReady: true });
        } catch (err: any) {
          if (err?.response?.status === 401) {
            try {
              await get().refreshAccessToken();
              const response = await api.get("/auth/me");
              set({ user: response.data, isAuthenticated: true, isLoading: false, isReady: true });
            } catch {
              get().logout();
            }
          } else {
            set({ isLoading: false, isReady: true });
          }
        }
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        if (state?.accessToken) {
          useAuth.setState({
            isAuthenticated: true,
            isLoading: false,
            isReady: true,
          });
        }
      },
    }
  )
);

export const getAccessToken = (): string | null => {
  const storeToken = useAuth.getState().accessToken;
  if (storeToken) return storeToken;

  if (typeof window !== "undefined") {
    try {
      const raw = localStorage.getItem("auth-storage");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed?.state?.accessToken) {
          useAuth.setState({
            user: parsed.state.user || null,
            accessToken: parsed.state.accessToken,
            refreshToken: parsed.state.refreshToken || null,
            isAuthenticated: true,
            isLoading: false,
            isReady: true,
          });
          return parsed.state.accessToken;
        }
      }
    } catch {}
  }
  return null;
};

export const refreshAccessToken = () => useAuth.getState().refreshAccessToken();