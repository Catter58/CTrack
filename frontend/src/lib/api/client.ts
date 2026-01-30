/**
 * API клиент для CTrack с автоматическим обновлением токена
 */

import { progress } from "$lib/stores/progress";

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

  /**
   * Extract error message from API response
   */
  private extractErrorMessage(error: unknown, status: number): string {
    if (!error || typeof error !== "object") {
      return `HTTP ${status}`;
    }

    const err = error as Record<string, unknown>;

    // Handle Pydantic validation errors (array of objects)
    if (Array.isArray(err.detail)) {
      const messages = err.detail.map((e: unknown) => {
        if (typeof e === "object" && e !== null && "msg" in e) {
          return (e as { msg: string }).msg;
        }
        return String(e);
      });
      return messages.join("; ");
    }

    // Handle string detail
    if (typeof err.detail === "string") {
      return err.detail;
    }

    // Handle object detail with message
    if (typeof err.detail === "object" && err.detail !== null) {
      const detail = err.detail as Record<string, unknown>;
      if ("message" in detail && typeof detail.message === "string") {
        return detail.message;
      }
      if ("msg" in detail && typeof detail.msg === "string") {
        return detail.msg;
      }
    }

    // Handle top-level message
    if (typeof err.message === "string") {
      return err.message;
    }

    return `HTTP ${status}`;
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
          throw new Error(
            this.extractErrorMessage(error, retryResponse.status),
          );
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
      throw new Error(this.extractErrorMessage(error, response.status));
    }

    // Handle 204 No Content responses
    if (response.status === 204) {
      return undefined as T;
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

  /**
   * Upload FormData using fetch (no progress tracking)
   * Does not set Content-Type header (browser sets it automatically with boundary)
   */
  async upload<T>(endpoint: string, formData: FormData): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const headers: HeadersInit = {};
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: formData,
    });

    if (response.status === 401 && this.refreshCallback) {
      const newToken = await this.tryRefresh();
      if (newToken) {
        headers["Authorization"] = `Bearer ${newToken}`;
        const retryResponse = await fetch(url, {
          method: "POST",
          headers,
          body: formData,
        });

        if (!retryResponse.ok) {
          const error = await retryResponse
            .json()
            .catch(() => ({ detail: "Ошибка сервера" }));
          throw new Error(
            this.extractErrorMessage(error, retryResponse.status),
          );
        }
        return retryResponse.json();
      }
      this.logoutCallback?.();
      throw new Error("Сессия истекла. Пожалуйста, войдите снова.");
    }

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Ошибка сервера" }));
      throw new Error(this.extractErrorMessage(error, response.status));
    }

    return response.json();
  }

  /**
   * Upload a file using XMLHttpRequest for progress tracking
   * Does not set Content-Type header (browser sets it automatically with boundary)
   */
  async uploadFile<T>(
    endpoint: string,
    file: File,
    fieldName: string = "file",
    showProgress: boolean = true,
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const formData = new FormData();
    formData.append(fieldName, file);

    const progressId = showProgress
      ? progress.start("upload", file.name, 0)
      : null;

    const doUpload = (token: string | null): Promise<T> => {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.upload.onprogress = (event) => {
          if (progressId && event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            progress.update(progressId, percent);
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            if (progressId) progress.done(progressId);
            try {
              resolve(JSON.parse(xhr.responseText));
            } catch {
              resolve(undefined as T);
            }
          } else if (xhr.status === 401) {
            reject({ status: 401, response: xhr.responseText });
          } else {
            if (progressId) progress.error(progressId);
            try {
              const error = JSON.parse(xhr.responseText);
              reject(new Error(this.extractErrorMessage(error, xhr.status)));
            } catch {
              reject(new Error(`HTTP ${xhr.status}`));
            }
          }
        };

        xhr.onerror = () => {
          if (progressId) progress.error(progressId);
          reject(new Error("Ошибка сети"));
        };

        xhr.open("POST", url);
        if (token) {
          xhr.setRequestHeader("Authorization", `Bearer ${token}`);
        }
        xhr.send(formData);
      });
    };

    try {
      return await doUpload(this.token);
    } catch (err) {
      if (
        typeof err === "object" &&
        err !== null &&
        "status" in err &&
        (err as { status: number }).status === 401 &&
        this.refreshCallback
      ) {
        const newToken = await this.tryRefresh();
        if (newToken) {
          return doUpload(newToken);
        }
        this.logoutCallback?.();
        if (progressId) progress.error(progressId);
        throw new Error("Сессия истекла. Пожалуйста, войдите снова.");
      }
      throw err;
    }
  }

  /**
   * Download a file with authentication and progress tracking
   * Uses XMLHttpRequest for progress events
   */
  async downloadFile(
    endpoint: string,
    filename: string,
    showProgress: boolean = true,
  ): Promise<void> {
    const url = `${this.baseUrl}${endpoint}`;
    const progressId = showProgress
      ? progress.start("download", filename, null)
      : null;

    const doDownload = (token: string | null): Promise<Blob> => {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.onprogress = (event) => {
          if (progressId && event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            progress.update(progressId, percent);
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(xhr.response);
          } else if (xhr.status === 401) {
            reject({ status: 401 });
          } else {
            reject(new Error(`HTTP ${xhr.status}`));
          }
        };

        xhr.onerror = () => {
          reject(new Error("Ошибка сети"));
        };

        xhr.open("GET", url);
        xhr.responseType = "blob";
        if (token) {
          xhr.setRequestHeader("Authorization", `Bearer ${token}`);
        }
        xhr.send();
      });
    };

    const handleDownloadSuccess = (blob: Blob): void => {
      if (progressId) progress.done(progressId);

      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(blobUrl);
    };

    try {
      const blob = await doDownload(this.token);
      handleDownloadSuccess(blob);
    } catch (err) {
      if (
        typeof err === "object" &&
        err !== null &&
        "status" in err &&
        (err as { status: number }).status === 401 &&
        this.refreshCallback
      ) {
        const newToken = await this.tryRefresh();
        if (newToken) {
          const blob = await doDownload(newToken);
          handleDownloadSuccess(blob);
          return;
        }
        this.logoutCallback?.();
        if (progressId) progress.error(progressId);
        throw new Error("Сессия истекла. Пожалуйста, войдите снова.");
      }
      if (progressId) progress.error(progressId);
      throw err;
    }
  }
}

export const api = new ApiClient(API_BASE_URL);
export default api;

/**
 * Convert a relative media URL to an absolute URL.
 * E.g., "/media/avatars/xxx.jpg" -> "http://localhost:8000/media/avatars/xxx.jpg"
 */
export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  // Already an absolute URL
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }
  // Relative URL - prepend API base URL
  return `${API_BASE_URL}${url.startsWith("/") ? "" : "/"}${url}`;
}
