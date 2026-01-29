/**
 * Store for global search functionality
 */

import { writable, derived } from "svelte/store";
import api from "$lib/api/client";

export interface SearchIssue {
  id: string;
  key: string;
  title: string;
  project: {
    key: string;
    name: string;
  };
  status: {
    name: string;
    color: string;
  };
}

export interface SearchProject {
  id: string;
  key: string;
  name: string;
}

export interface GlobalSearchResults {
  query: string;
  issues: SearchIssue[];
  projects: SearchProject[];
}

export interface ProjectSearchItem {
  id: string;
  key: string;
  title: string;
  headline_title: string | null;
  headline_description: string | null;
  status: {
    name: string;
    color: string;
  };
  priority: string;
  assignee: {
    id: number;
    username: string;
    full_name: string | null;
  } | null;
}

export interface ProjectSearchResults {
  query: string;
  items: ProjectSearchItem[];
  total: number;
  page: number;
  page_size: number;
}

interface SearchState {
  query: string;
  results: GlobalSearchResults | null;
  isLoading: boolean;
  isOpen: boolean;
  error: string | null;
}

interface ProjectSearchState {
  query: string;
  results: ProjectSearchResults | null;
  isLoading: boolean;
  error: string | null;
}

// Debounce helper
function debounce<T extends (...args: string[]) => void | Promise<void>>(
  fn: T,
  delay: number,
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

function createSearchStore() {
  const { subscribe, set, update } = writable<SearchState>({
    query: "",
    results: null,
    isLoading: false,
    isOpen: false,
    error: null,
  });

  const performSearch = async (query: string) => {
    if (!query.trim()) {
      update((s) => ({ ...s, results: null, isLoading: false }));
      return;
    }

    update((s) => ({ ...s, isLoading: true, error: null }));

    try {
      const results = await api.get<GlobalSearchResults>("/api/search", {
        q: query,
        limit: "10",
      });
      update((s) => ({ ...s, results, isLoading: false }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Ошибка поиска";
      update((s) => ({ ...s, isLoading: false, error: message }));
    }
  };

  const debouncedSearch = debounce(performSearch, 300);

  return {
    subscribe,

    setQuery(query: string) {
      update((s) => ({ ...s, query }));
      debouncedSearch(query);
    },

    async search(query: string) {
      update((s) => ({ ...s, query }));
      await performSearch(query);
    },

    open() {
      update((s) => ({ ...s, isOpen: true }));
    },

    close() {
      update((s) => ({ ...s, isOpen: false }));
    },

    toggle() {
      update((s) => ({ ...s, isOpen: !s.isOpen }));
    },

    clear() {
      set({
        query: "",
        results: null,
        isLoading: false,
        isOpen: false,
        error: null,
      });
    },

    reset() {
      update((s) => ({
        ...s,
        query: "",
        results: null,
        error: null,
      }));
    },
  };
}

function createProjectSearchStore() {
  const { subscribe, set, update } = writable<ProjectSearchState>({
    query: "",
    results: null,
    isLoading: false,
    error: null,
  });

  return {
    subscribe,

    async search(
      projectKey: string,
      query: string,
      options?: {
        status_id?: string;
        page?: number;
        page_size?: number;
      },
    ) {
      update((s) => ({ ...s, query, isLoading: true, error: null }));

      try {
        const params: Record<string, string> = { q: query };
        if (options?.status_id) params.status_id = options.status_id;
        if (options?.page) params.page = String(options.page);
        if (options?.page_size) params.page_size = String(options.page_size);

        const results = await api.get<ProjectSearchResults>(
          `/api/projects/${projectKey}/search`,
          params,
        );
        update((s) => ({ ...s, results, isLoading: false }));
        return results;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Ошибка поиска";
        update((s) => ({ ...s, isLoading: false, error: message }));
        return null;
      }
    },

    reset() {
      set({
        query: "",
        results: null,
        isLoading: false,
        error: null,
      });
    },
  };
}

export const search = createSearchStore();
export const projectSearch = createProjectSearchStore();

// Derived stores for convenience
export const searchQuery = derived(search, ($s) => $s.query);
export const searchResults = derived(search, ($s) => $s.results);
export const searchIsLoading = derived(search, ($s) => $s.isLoading);
export const searchIsOpen = derived(search, ($s) => $s.isOpen);
export const searchError = derived(search, ($s) => $s.error);

export const projectSearchResults = derived(projectSearch, ($s) => $s.results);
export const projectSearchIsLoading = derived(
  projectSearch,
  ($s) => $s.isLoading,
);
export const projectSearchError = derived(projectSearch, ($s) => $s.error);
