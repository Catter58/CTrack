/**
 * Стор аутентификации CTrack
 */

import { writable, derived, get } from "svelte/store";
import { browser } from "$app/environment";
import api from "$lib/api/client";

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  avatar: string | null;
  bio: string;
  timezone: string;
  is_active: boolean;
  is_staff: boolean;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  error: string | null;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

const STORAGE_KEY = "ctrack_auth";

// Тип для auth store (явно определён чтобы избежать циклических ссылок)
interface AuthStore {
  subscribe: (
    run: (value: AuthState) => void,
    invalidate?: () => void,
  ) => () => void;
  init(): Promise<void>;
  login(email: string, password: string): Promise<boolean>;
  register(data: {
    email: string;
    username: string;
    password: string;
    first_name?: string;
    last_name?: string;
  }): Promise<boolean>;
  refresh(): Promise<boolean>;
  logout(): void;
  clearError(): void;
  updateUser(partialUser: Partial<User>): void;
}

function getStoredAuth(): Partial<AuthState> {
  if (!browser) return {};
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const data = JSON.parse(stored);
      return {
        accessToken: data.accessToken || null,
        refreshToken: data.refreshToken || null,
      };
    }
  } catch {
    // Ignore parse errors
  }
  return {};
}

function saveAuth(accessToken: string | null, refreshToken: string | null) {
  if (!browser) return;
  if (accessToken && refreshToken) {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ accessToken, refreshToken }),
    );
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
}

function createAuthStore(): AuthStore {
  const stored = getStoredAuth();

  const { subscribe, set, update } = writable<AuthState>({
    user: null,
    accessToken: stored.accessToken || null,
    refreshToken: stored.refreshToken || null,
    isLoading: true,
    error: null,
  });

  // Set token in API client
  if (stored.accessToken) {
    api.setToken(stored.accessToken);
  }

  // Callback для автоматического refresh токена (вызывается из API клиента при 401)
  const handleAutoRefresh = async (): Promise<string | null> => {
    const state = get({ subscribe });
    if (!state.refreshToken) {
      return null;
    }

    try {
      // Используем skipAuth чтобы избежать бесконечного цикла
      const tokens = await api.post<TokenResponse>("/api/auth/refresh", {
        refresh_token: state.refreshToken,
      });

      api.setToken(tokens.access_token);
      saveAuth(tokens.access_token, tokens.refresh_token);

      update((s) => ({
        ...s,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
      }));

      return tokens.access_token;
    } catch {
      return null;
    }
  };

  // Callback для logout (вызывается из API клиента при неудачном refresh)
  const handleAutoLogout = () => {
    api.setToken(null);
    saveAuth(null, null);
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isLoading: false,
      error: null,
    });
  };

  // Устанавливаем callbacks в API клиент
  api.setRefreshCallback(handleAutoRefresh);
  api.setLogoutCallback(handleAutoLogout);

  const store: AuthStore = {
    subscribe,

    /**
     * Initialize auth state - check if stored token is valid
     */
    async init() {
      const state = get({ subscribe });
      if (!state.accessToken) {
        update((s) => ({ ...s, isLoading: false }));
        return;
      }

      try {
        api.setToken(state.accessToken);
        const user = await api.get<User>("/api/auth/me");
        update((s) => ({
          ...s,
          user,
          isLoading: false,
          error: null,
        }));
      } catch {
        // Token invalid - auto-refresh уже попробует обновить
        // Если не удалось - handleAutoLogout уже вызван
        update((s) => ({ ...s, isLoading: false }));
      }
    },

    /**
     * Login with email and password
     */
    async login(email: string, password: string): Promise<boolean> {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const tokens = await api.post<TokenResponse>("/api/auth/login", {
          email,
          password,
        });

        api.setToken(tokens.access_token);
        saveAuth(tokens.access_token, tokens.refresh_token);

        const user = await api.get<User>("/api/auth/me");

        update((s) => ({
          ...s,
          user,
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          isLoading: false,
          error: null,
        }));

        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Ошибка входа";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return false;
      }
    },

    /**
     * Register new user
     */
    async register(data: {
      email: string;
      username: string;
      password: string;
      first_name?: string;
      last_name?: string;
    }): Promise<boolean> {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const tokens = await api.post<TokenResponse>(
          "/api/auth/register",
          data,
        );

        api.setToken(tokens.access_token);
        saveAuth(tokens.access_token, tokens.refresh_token);

        const user = await api.get<User>("/api/auth/me");

        update((s) => ({
          ...s,
          user,
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          isLoading: false,
          error: null,
        }));

        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Ошибка регистрации";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return false;
      }
    },

    /**
     * Refresh access token
     */
    async refresh(): Promise<boolean> {
      const state = get({ subscribe });
      if (!state.refreshToken) {
        this.logout();
        return false;
      }

      try {
        const tokens = await api.post<TokenResponse>("/api/auth/refresh", {
          refresh_token: state.refreshToken,
        });

        api.setToken(tokens.access_token);
        saveAuth(tokens.access_token, tokens.refresh_token);

        const user = await api.get<User>("/api/auth/me");

        update((s) => ({
          ...s,
          user,
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          isLoading: false,
          error: null,
        }));

        return true;
      } catch {
        this.logout();
        return false;
      }
    },

    /**
     * Logout user
     */
    logout() {
      const state = get({ subscribe });

      // Try to invalidate refresh token on server
      if (state.accessToken && state.refreshToken) {
        api
          .post("/api/auth/logout", { refresh_token: state.refreshToken })
          .catch(() => {
            // Ignore errors
          });
      }

      api.setToken(null);
      saveAuth(null, null);

      set({
        user: null,
        accessToken: null,
        refreshToken: null,
        isLoading: false,
        error: null,
      });
    },

    /**
     * Clear error
     */
    clearError() {
      update((s) => ({ ...s, error: null }));
    },

    /**
     * Update user data (partial update)
     */
    updateUser(partialUser: Partial<User>) {
      update((s) => ({
        ...s,
        user: s.user ? { ...s.user, ...partialUser } : null,
      }));
    },
  };

  return store;
}

export const auth = createAuthStore();

// Derived stores for convenience
export const user = derived(auth, ($auth: AuthState) => $auth.user);
export const isAuthenticated = derived(
  auth,
  ($auth: AuthState) => !!$auth.user,
);
export const isLoading = derived(auth, ($auth: AuthState) => $auth.isLoading);
export const authError = derived(auth, ($auth: AuthState) => $auth.error);
