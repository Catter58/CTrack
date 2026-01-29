/**
 * Store for saved filters management
 */

import { writable, derived } from "svelte/store";
import api from "$lib/api/client";

export interface SavedFilter {
  id: string;
  name: string;
  project_id: string;
  owner_id: number;
  is_shared: boolean;
  filters: FilterValues;
  created_at: string;
  updated_at: string;
}

export interface FilterValues {
  status_id?: string;
  priority?: string;
  assignee_id?: number;
  type_id?: string;
  search?: string;
}

export interface CreateFilterData {
  name: string;
  is_shared: boolean;
  filters: FilterValues;
}

interface FiltersState {
  savedFilters: SavedFilter[];
  currentFilter: SavedFilter | null;
  isLoading: boolean;
  error: string | null;
}

function createFiltersStore() {
  const { subscribe, set, update } = writable<FiltersState>({
    savedFilters: [],
    currentFilter: null,
    isLoading: false,
    error: null,
  });

  return {
    subscribe,

    async load(projectKey: string): Promise<SavedFilter[]> {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const filters = await api.get<SavedFilter[]>(
          `/api/projects/${projectKey}/filters`,
        );
        update((s) => ({
          ...s,
          savedFilters: filters,
          isLoading: false,
        }));
        return filters;
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Не удалось загрузить сохранённые фильтры";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return [];
      }
    },

    async create(
      projectKey: string,
      data: CreateFilterData,
    ): Promise<SavedFilter | null> {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const filter = await api.post<SavedFilter>(
          `/api/projects/${projectKey}/filters`,
          data,
        );
        update((s) => ({
          ...s,
          savedFilters: [...s.savedFilters, filter],
          isLoading: false,
        }));
        return filter;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось сохранить фильтр";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return null;
      }
    },

    async delete(_projectKey: string, filterId: string): Promise<boolean> {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        // Note: delete endpoint doesn't require projectKey in path
        await api.delete(`/api/projects/filters/${filterId}`);
        update((s) => ({
          ...s,
          savedFilters: s.savedFilters.filter((f) => f.id !== filterId),
          currentFilter:
            s.currentFilter?.id === filterId ? null : s.currentFilter,
          isLoading: false,
        }));
        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось удалить фильтр";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return false;
      }
    },

    setCurrentFilter(filter: SavedFilter | null) {
      update((s) => ({ ...s, currentFilter: filter }));
    },

    clearError() {
      update((s) => ({ ...s, error: null }));
    },

    reset() {
      set({
        savedFilters: [],
        currentFilter: null,
        isLoading: false,
        error: null,
      });
    },
  };
}

export const filtersStore = createFiltersStore();

export const savedFilters = derived(filtersStore, ($f) => $f.savedFilters);
export const currentFilter = derived(filtersStore, ($f) => $f.currentFilter);
export const filtersLoading = derived(filtersStore, ($f) => $f.isLoading);
export const filtersError = derived(filtersStore, ($f) => $f.error);
