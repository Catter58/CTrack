/**
 * API клиент для CTrack с автоматическим обновлением токена
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
  skipAuth?: boolean; // Пропустить авторизацию (для refresh endpoint)
}

type RefreshCallback = () => Promise<string | null>;
type LogoutCallback = () => void;

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;
  private refreshCallback: RefreshCallback | null = null;
  private logoutCallback: LogoutCallback | null = null;
  private isRefreshing = false;
  private refreshPromise: Promise<string | null> | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.token = token;
  }

  /**
   * Установить callback для обновления токена
   */
  setRefreshCallback(callback: RefreshCallback) {
    this.refreshCallback = callback;
  }

  /**
   * Установить callback для logout при неудачном refresh
   */
  setLogoutCallback(callback: LogoutCallback) {
    this.logoutCallback = callback;
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {},
  ): Promise<T> {
    const { params, skipAuth, ...fetchOptions } = options;

    let url = `${this.baseUrl}${endpoint}`;
    if (params) {
      const searchParams = new URLSearchParams(params);
      url += `?${searchParams.toString()}`;
    }

    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...fetchOptions.headers,
    };

    if (this.token && !skipAuth) {
      (headers as Record<string, string>)["Authorization"] =
        `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...fetchOptions,
      headers,
    });

    // Если 401 и есть callback для refresh - пробуем обновить токен
    if (response.status === 401 && !skipAuth && this.refreshCallback) {
      const newToken = await this.tryRefresh();
      if (newToken) {
        // Повторяем запрос с новым токеном
        (headers as Record<string, string>)["Authorization"] =
          `Bearer ${newToken}`;
        const retryResponse = await fetch(url, {
          ...fetchOptions,
          headers,
        });

        if (!retryResponse.ok) {
          const error = await retryResponse
            .json()
            .catch(() => ({ detail: "Ошибка сервера" }));
          throw new Error(error.detail || `HTTP ${retryResponse.status}`);
        }

        return retryResponse.json();
      } else {
        // Refresh не удался - logout
        this.logoutCallback?.();
        throw new Error("Сессия истекла. Пожалуйста, войдите снова.");
      }
    }

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Ошибка сервера" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Попытка обновить токен (с защитой от дублирования)
   */
  private async tryRefresh(): Promise<string | null> {
    // Если уже идёт refresh - ждём его результат
    if (this.isRefreshing && this.refreshPromise) {
      return this.refreshPromise;
    }

    this.isRefreshing = true;
    this.refreshPromise = this.refreshCallback!();

    try {
      const newToken = await this.refreshPromise;
      return newToken;
    } finally {
      this.isRefreshing = false;
      this.refreshPromise = null;
    }
  }

  async get<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, { method: "GET", params });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async patch<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(
    endpoint: string,
    params?: Record<string, string | boolean>,
  ): Promise<T> {
    // Convert boolean values to strings for URL params
    const stringParams = params
      ? Object.fromEntries(
          Object.entries(params).map(([k, v]) => [k, String(v)]),
        )
      : undefined;
    return this.request<T>(endpoint, {
      method: "DELETE",
      params: stringParams,
    });
  }
}

export const api = new ApiClient(API_BASE_URL);
export default api;
