/**
 * Global progress bar store for tracking long operations
 */

import { writable, derived } from "svelte/store";

export type ProgressType =
  | "upload"
  | "download"
  | "bulk"
  | "report"
  | "loading"
  | "generic";

export interface ProgressItem {
  id: string;
  type: ProgressType;
  label?: string;
  percent: number | null; // null = indeterminate
  isError: boolean;
}

interface ProgressState {
  items: ProgressItem[];
}

function createProgressStore() {
  const { subscribe, update } = writable<ProgressState>({
    items: [],
  });

  let idCounter = 0;

  function generateId(): string {
    return `progress-${Date.now()}-${idCounter++}`;
  }

  return {
    subscribe,

    /**
     * Start a new progress operation
     * Returns the progress ID for tracking
     */
    start(
      type: ProgressType = "generic",
      label?: string,
      initialPercent: number | null = null,
    ): string {
      const id = generateId();
      const item: ProgressItem = {
        id,
        type,
        label,
        percent: initialPercent,
        isError: false,
      };

      update((state) => ({
        items: [...state.items, item],
      }));

      return id;
    },

    /**
     * Update progress percentage for an operation
     */
    update(id: string, percent: number, label?: string): void {
      update((state) => ({
        items: state.items.map((item) =>
          item.id === id
            ? {
                ...item,
                percent: Math.min(100, Math.max(0, percent)),
                label: label ?? item.label,
              }
            : item,
        ),
      }));
    },

    /**
     * Mark operation as complete and remove after delay
     */
    done(id: string, delay: number = 500): void {
      update((state) => ({
        items: state.items.map((item) =>
          item.id === id ? { ...item, percent: 100 } : item,
        ),
      }));

      setTimeout(() => {
        update((state) => ({
          items: state.items.filter((item) => item.id !== id),
        }));
      }, delay);
    },

    /**
     * Mark operation as failed
     */
    error(id: string, delay: number = 2000): void {
      update((state) => ({
        items: state.items.map((item) =>
          item.id === id ? { ...item, isError: true } : item,
        ),
      }));

      setTimeout(() => {
        update((state) => ({
          items: state.items.filter((item) => item.id !== id),
        }));
      }, delay);
    },

    /**
     * Remove a specific progress item
     */
    remove(id: string): void {
      update((state) => ({
        items: state.items.filter((item) => item.id !== id),
      }));
    },

    /**
     * Clear all progress items
     */
    clear(): void {
      update(() => ({ items: [] }));
    },

    /**
     * Track a bulk operation with progress
     * Returns a tracker with methods to update progress
     */
    trackBulk(
      totalItems: number,
      label?: string,
    ): {
      id: string;
      increment: () => void;
      finish: () => void;
      fail: () => void;
    } {
      let completed = 0;
      const id = this.start("bulk", label, 0);

      return {
        id,
        increment: () => {
          completed++;
          const percent = Math.round((completed / totalItems) * 100);
          this.update(id, percent);
        },
        finish: () => {
          this.done(id);
        },
        fail: () => {
          this.error(id);
        },
      };
    },

    /**
     * Wrap an async operation with indeterminate progress
     */
    async track<T>(
      type: ProgressType,
      label: string,
      operation: () => Promise<T>,
    ): Promise<T> {
      const id = this.start(type, label, null);
      try {
        const result = await operation();
        this.done(id);
        return result;
      } catch (err) {
        this.error(id);
        throw err;
      }
    },
  };
}

export const progress = createProgressStore();

export const progressItems = derived(progress, ($p) => $p.items);

export const isAnyProgress = derived(progress, ($p) => $p.items.length > 0);

export const globalPercent = derived(progress, ($p) => {
  if ($p.items.length === 0) return null;

  const determinate = $p.items.filter((item) => item.percent !== null);
  if (determinate.length === 0) return null;

  const total = determinate.reduce((sum, item) => sum + (item.percent ?? 0), 0);
  return Math.round(total / determinate.length);
});
