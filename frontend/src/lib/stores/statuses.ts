/**
 * Store for statuses management
 */

import { writable, derived } from "svelte/store";
import api from "$lib/api/client";

export interface Status {
  id: string;
  name: string;
  category: "todo" | "in_progress" | "done";
  color: string;
  order: number;
}

interface StatusesState {
  items: Status[];
  isLoading: boolean;
  error: string | null;
}

function createStatusesStore() {
  const { subscribe, update } = writable<StatusesState>({
    items: [],
    isLoading: false,
    error: null,
  });

  return {
    subscribe,

    async load(projectKey: string) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const items = await api.get<Status[]>(
          `/api/projects/${projectKey}/statuses`,
        );
        update((s) => ({ ...s, items, isLoading: false }));
        return items;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load statuses";
        update((s) => ({ ...s, isLoading: false, error: message }));
        return null;
      }
    },

    async create(
      projectKey: string,
      data: Omit<Status, "id">,
    ): Promise<Status | null> {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const item = await api.post<Status>(
          `/api/projects/${projectKey}/statuses`,
          data,
        );
        update((s) => ({
          ...s,
          items: [...s.items, item],
          isLoading: false,
        }));
        return item;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to create status";
        update((s) => ({ ...s, isLoading: false, error: message }));
        return null;
      }
    },

    async update(
      statusId: string,
      data: Partial<Omit<Status, "id">>,
    ): Promise<Status | null> {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const item = await api.patch<Status>(`/api/statuses/${statusId}`, data);
        update((s) => ({
          ...s,
          items: s.items.map((i) => (i.id === statusId ? item : i)),
          isLoading: false,
        }));
        return item;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to update status";
        update((s) => ({ ...s, isLoading: false, error: message }));
        return null;
      }
    },

    async delete(statusId: string): Promise<boolean> {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        await api.delete(`/api/statuses/${statusId}`);
        update((s) => ({
          ...s,
          items: s.items.filter((i) => i.id !== statusId),
          isLoading: false,
        }));
        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to delete status";
        update((s) => ({ ...s, isLoading: false, error: message }));
        return false;
      }
    },

    clearError() {
      update((s) => ({ ...s, error: null }));
    },
  };
}

export const statuses = createStatusesStore();

export const statusesLoading = derived(statuses, ($s) => $s.isLoading);
export const statusesError = derived(statuses, ($s) => $s.error);
export const statusesList = derived(statuses, ($s) => $s.items);

// Helpers for category labels
export const categoryLabels: Record<Status["category"], string> = {
  todo: "К выполнению",
  in_progress: "В работе",
  done: "Готово",
};

export const categoryColors: Record<Status["category"], string> = {
  todo: "#6f6f6f",
  in_progress: "#1192e8",
  done: "#198038",
};
