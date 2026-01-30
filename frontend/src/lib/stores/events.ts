/**
 * SSE (Server-Sent Events) store for real-time updates
 */

import { writable, get } from "svelte/store";
import { browser } from "$app/environment";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface SSEEvent {
  type: string;
  data?: Record<string, unknown>;
  timestamp?: string | number;
  message?: string;
  channels?: number;
}

export interface IssueEventData {
  issue_id: number | string;
  project_key: string;
  issue_key: string;
  changes?: Record<string, unknown>;
  user?: {
    id: number;
    username: string;
  };
}

export interface CommentEventData {
  comment_id: number | string;
  issue_key: string;
  project_key: string;
  user?: {
    id: number;
    username: string;
  };
}

export interface EditingEventData {
  issue_key: string;
  user_id: number;
  username: string;
  full_name: string;
  avatar_url: string | null;
  is_editing: boolean;
}

export interface ActivityFeedEventData {
  id: string;
  action: string;
  field_name: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  created_at: string;
  issue: {
    key: string;
    title: string;
    project: {
      key: string;
      name: string;
    };
  };
  user: {
    id: number;
    username: string;
    full_name: string;
    avatar: string | null;
  };
}

type EventCallback = (event: SSEEvent) => void;

interface EventsState {
  isConnected: boolean;
  lastEvent: SSEEvent | null;
  lastActivity: number;
  connectionError: string | null;
}

const STORAGE_KEY = "ctrack_auth";
const MAX_RETRY_DELAY = 30000;
const INITIAL_RETRY_DELAY = 1000;

function getStoredToken(): string | null {
  if (!browser) return null;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const data = JSON.parse(stored);
      return data.accessToken || null;
    }
  } catch {
    // Ignore parse errors
  }
  return null;
}

function createEventsStore() {
  const { subscribe, set, update } = writable<EventsState>({
    isConnected: false,
    lastEvent: null,
    lastActivity: 0,
    connectionError: null,
  });

  let eventSource: EventSource | null = null;
  let retryTimeout: ReturnType<typeof setTimeout> | null = null;
  let retryDelay = INITIAL_RETRY_DELAY;
  const subscribers = new Map<string, Set<EventCallback>>();
  let isManuallyDisconnected = false;

  function clearRetryTimeout(): void {
    if (retryTimeout) {
      clearTimeout(retryTimeout);
      retryTimeout = null;
    }
  }

  function handleEvent(event: SSEEvent): void {
    update((s) => ({
      ...s,
      lastEvent: event,
      lastActivity: Date.now(),
    }));

    // Notify type-specific subscribers
    const callbacks = subscribers.get(event.type);
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback(event);
        } catch (err) {
          console.error(
            `[SSE] Error in event callback for ${event.type}:`,
            err,
          );
        }
      });
    }

    // Notify wildcard subscribers
    const wildcardCallbacks = subscribers.get("*");
    if (wildcardCallbacks) {
      wildcardCallbacks.forEach((callback) => {
        try {
          callback(event);
        } catch (err) {
          console.error("[SSE] Error in wildcard callback:", err);
        }
      });
    }
  }

  function scheduleReconnect(): void {
    if (isManuallyDisconnected) return;

    clearRetryTimeout();

    retryTimeout = setTimeout(() => {
      console.log(`[SSE] Attempting to reconnect in ${retryDelay}ms...`);
      connect();
    }, retryDelay);

    // Exponential backoff with max limit
    retryDelay = Math.min(retryDelay * 2, MAX_RETRY_DELAY);
  }

  function connect(projectId?: string): void {
    if (!browser) return;

    const token = getStoredToken();
    if (!token) {
      update((s) => ({
        ...s,
        isConnected: false,
        connectionError: "No authentication token",
      }));
      return;
    }

    // Close existing connection
    disconnect(true);
    isManuallyDisconnected = false;

    // Build URL with token as query param (SSE doesn't support headers)
    let url = `${API_BASE_URL}/api/events?token=${encodeURIComponent(token)}`;
    if (projectId) {
      url += `&project_id=${encodeURIComponent(projectId)}`;
    }

    try {
      eventSource = new EventSource(url);

      eventSource.onopen = () => {
        console.log("[SSE] Connection established");
        retryDelay = INITIAL_RETRY_DELAY;
        update((s) => ({
          ...s,
          isConnected: true,
          connectionError: null,
          lastActivity: Date.now(),
        }));
      };

      eventSource.onmessage = (messageEvent) => {
        try {
          const event: SSEEvent = JSON.parse(messageEvent.data);

          // Update last activity for heartbeats but don't process further
          if (event.type === "heartbeat") {
            update((s) => ({ ...s, lastActivity: Date.now() }));
            return;
          }

          handleEvent(event);
        } catch (err) {
          console.error("[SSE] Failed to parse event:", err);
        }
      };

      eventSource.onerror = (err) => {
        console.error("[SSE] Connection error:", err);

        update((s) => ({
          ...s,
          isConnected: false,
          connectionError: "Connection lost",
        }));

        // Close and schedule reconnect
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }

        scheduleReconnect();
      };
    } catch (err) {
      console.error("[SSE] Failed to create EventSource:", err);
      update((s) => ({
        ...s,
        isConnected: false,
        connectionError:
          err instanceof Error ? err.message : "Connection failed",
      }));
      scheduleReconnect();
    }
  }

  function disconnect(keepSubscribers = false): void {
    if (!keepSubscribers) {
      isManuallyDisconnected = true;
    }

    clearRetryTimeout();

    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }

    update((s) => ({
      ...s,
      isConnected: false,
      connectionError: null,
    }));

    if (!keepSubscribers) {
      subscribers.clear();
    }
  }

  function subscribeToEvent(
    eventType: string,
    callback: EventCallback,
  ): () => void {
    if (!subscribers.has(eventType)) {
      subscribers.set(eventType, new Set());
    }
    subscribers.get(eventType)!.add(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = subscribers.get(eventType);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          subscribers.delete(eventType);
        }
      }
    };
  }

  function unsubscribeFromEvent(
    eventType: string,
    callback: EventCallback,
  ): void {
    const callbacks = subscribers.get(eventType);
    if (callbacks) {
      callbacks.delete(callback);
      if (callbacks.size === 0) {
        subscribers.delete(eventType);
      }
    }
  }

  // Handle page visibility change
  if (browser) {
    document.addEventListener("visibilitychange", () => {
      const state = get({ subscribe });
      if (document.hidden) {
        // Page hidden - connection will be maintained by browser
      } else if (!state.isConnected && !isManuallyDisconnected) {
        // Page visible again and not connected - reconnect
        retryDelay = INITIAL_RETRY_DELAY;
        connect();
      }
    });

    // Handle page unload
    window.addEventListener("beforeunload", () => {
      disconnect();
    });
  }

  return {
    subscribe,

    /**
     * Connect to SSE endpoint
     */
    connect,

    /**
     * Disconnect from SSE endpoint
     */
    disconnect() {
      disconnect(false);
    },

    /**
     * Subscribe to a specific event type
     * @param eventType - Event type to listen for (e.g., "issue.updated") or "*" for all events
     * @param callback - Function to call when event is received
     * @returns Unsubscribe function
     */
    on: subscribeToEvent,

    /**
     * Unsubscribe from a specific event type
     */
    off: unsubscribeFromEvent,

    /**
     * Get current connection state
     */
    getState(): EventsState {
      return get({ subscribe });
    },

    /**
     * Reset the store
     */
    reset(): void {
      disconnect(false);
      set({
        isConnected: false,
        lastEvent: null,
        lastActivity: 0,
        connectionError: null,
      });
    },
  };
}

export const events = createEventsStore();
