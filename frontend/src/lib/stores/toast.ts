/**
 * Global toast notification store
 */

import { writable, derived } from "svelte/store";

export type ToastKind = "info" | "success" | "warning" | "error";

export interface Toast {
  id: string;
  kind: ToastKind;
  title: string;
  subtitle?: string;
  timeout?: number;
}

interface ToastState {
  toasts: Toast[];
}

function createToastStore() {
  const { subscribe, update } = writable<ToastState>({
    toasts: [],
  });

  let idCounter = 0;

  function generateId(): string {
    return `toast-${Date.now()}-${idCounter++}`;
  }

  function addToast(
    kind: ToastKind,
    title: string,
    subtitle?: string,
    timeout = 4000,
  ) {
    const id = generateId();
    const toast: Toast = { id, kind, title, subtitle, timeout };

    update((state) => ({
      toasts: [...state.toasts, toast],
    }));

    // Auto-remove after timeout
    if (timeout > 0) {
      setTimeout(() => {
        removeToast(id);
      }, timeout);
    }

    return id;
  }

  function removeToast(id: string) {
    update((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  }

  return {
    subscribe,

    /**
     * Show a success toast
     */
    success(title: string, subtitle?: string, timeout?: number) {
      return addToast("success", title, subtitle, timeout);
    },

    /**
     * Show an error toast
     */
    error(title: string, subtitle?: string, timeout?: number) {
      return addToast("error", title, subtitle, timeout ?? 6000);
    },

    /**
     * Show a warning toast
     */
    warning(title: string, subtitle?: string, timeout?: number) {
      return addToast("warning", title, subtitle, timeout);
    },

    /**
     * Show an info toast
     */
    info(title: string, subtitle?: string, timeout?: number) {
      return addToast("info", title, subtitle, timeout);
    },

    /**
     * Dismiss a specific toast
     */
    dismiss(id: string) {
      removeToast(id);
    },

    /**
     * Dismiss all toasts
     */
    dismissAll() {
      update(() => ({ toasts: [] }));
    },
  };
}

export const toasts = createToastStore();
export const toastsList = derived(toasts, ($t) => $t.toasts);
