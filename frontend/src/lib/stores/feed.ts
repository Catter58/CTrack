/**
 * Store for activity feed with cursor-based pagination
 */

import { writable, derived } from "svelte/store";
import api from "$lib/api/client";
import type { Project } from "$lib/stores/projects";

export interface FeedUser {
  id: number;
  username: string;
  full_name: string | null;
}

export interface FeedIssue {
  id: string;
  key: string;
  title: string;
  project: {
    id: string;
    key: string;
    name: string;
  };
}

export type FeedAction =
  | "created"
  | "status_changed"
  | "assigned"
  | "unassigned"
  | "priority_changed"
  | "due_date_changed"
  | "story_points_changed"
  | "attachment_added"
  | "attachment_removed"
  | "commented";

export interface FeedItem {
  id: string;
  action: FeedAction;
  created_at: string;
  user: FeedUser;
  issue: FeedIssue;
  old_value: unknown | null;
  new_value: unknown | null;
  comment_preview: string | null;
}

export interface FeedFilters {
  user_id?: number;
  project_id?: string;
  action?: FeedAction;
  date_from?: string;
  date_to?: string;
}

interface FeedResponse {
  items: FeedItem[];
  next_cursor: string | null;
  has_more: boolean;
}

interface FeedState {
  items: FeedItem[];
  projects: Project[];
  users: FeedUser[];
  filters: FeedFilters;
  cursor: string | null;
  hasMore: boolean;
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
}

function createFeedStore() {
  const { subscribe, set, update } = writable<FeedState>({
    items: [],
    projects: [],
    users: [],
    filters: {},
    cursor: null,
    hasMore: true,
    isLoading: false,
    isLoadingMore: false,
    error: null,
  });

  return {
    subscribe,

    async loadFeed(filters?: FeedFilters) {
      update((s) => ({
        ...s,
        isLoading: true,
        error: null,
        items: [],
        cursor: null,
        hasMore: true,
      }));

      try {
        let state: FeedState | undefined;
        const unsubscribe = subscribe((s) => {
          state = s;
        });
        unsubscribe();

        if (!state) return;

        const params: Record<string, string> = {
          limit: "50",
        };

        const activeFilters = filters ?? state.filters;

        if (activeFilters.user_id !== undefined) {
          params.user_id = String(activeFilters.user_id);
        }
        if (activeFilters.project_id) {
          params.project_id = activeFilters.project_id;
        }
        if (activeFilters.action) {
          params.action = activeFilters.action;
        }
        if (activeFilters.date_from) {
          params.date_from = activeFilters.date_from;
        }
        if (activeFilters.date_to) {
          params.date_to = activeFilters.date_to;
        }

        const response = await api.get<FeedResponse>("/api/feed", params);

        update((s) => ({
          ...s,
          items: response.items,
          cursor: response.next_cursor,
          hasMore: response.has_more,
          filters: activeFilters,
          isLoading: false,
        }));

        return response;
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Не удалось загрузить ленту активности";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return null;
      }
    },

    async loadMore() {
      let state: FeedState | undefined;
      const unsubscribe = subscribe((s) => {
        state = s;
      });
      unsubscribe();

      if (!state || !state.hasMore || !state.cursor || state.isLoadingMore) {
        return;
      }

      update((s) => ({ ...s, isLoadingMore: true, error: null }));

      try {
        const params: Record<string, string> = {
          limit: "50",
          cursor: state.cursor,
        };

        if (state.filters.user_id !== undefined) {
          params.user_id = String(state.filters.user_id);
        }
        if (state.filters.project_id) {
          params.project_id = state.filters.project_id;
        }
        if (state.filters.action) {
          params.action = state.filters.action;
        }
        if (state.filters.date_from) {
          params.date_from = state.filters.date_from;
        }
        if (state.filters.date_to) {
          params.date_to = state.filters.date_to;
        }

        const response = await api.get<FeedResponse>("/api/feed", params);

        update((s) => ({
          ...s,
          items: [...s.items, ...response.items],
          cursor: response.next_cursor,
          hasMore: response.has_more,
          isLoadingMore: false,
        }));

        return response;
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Не удалось загрузить больше записей";
        update((s) => ({
          ...s,
          isLoadingMore: false,
          error: message,
        }));
        return null;
      }
    },

    async loadProjects() {
      try {
        const projects = await api.get<Project[]>("/api/projects");
        update((s) => ({ ...s, projects }));
        return projects;
      } catch (err) {
        console.error("Failed to load projects:", err);
        return [];
      }
    },

    async loadUsers() {
      try {
        // Load all users that have activity
        const users = await api.get<FeedUser[]>("/api/users");
        update((s) => ({ ...s, users }));
        return users;
      } catch (err) {
        console.error("Failed to load users:", err);
        return [];
      }
    },

    setFilters(filters: FeedFilters) {
      update((s) => ({
        ...s,
        filters,
        cursor: null,
        hasMore: true,
      }));
    },

    clearFilters() {
      update((s) => ({
        ...s,
        filters: {},
        cursor: null,
        hasMore: true,
      }));
    },

    clearError() {
      update((s) => ({ ...s, error: null }));
    },

    reset() {
      set({
        items: [],
        projects: [],
        users: [],
        filters: {},
        cursor: null,
        hasMore: true,
        isLoading: false,
        isLoadingMore: false,
        error: null,
      });
    },
  };
}

export const feed = createFeedStore();

// Derived stores
export const feedItems = derived(feed, ($s) => $s.items);
export const feedProjects = derived(feed, ($s) => $s.projects);
export const feedUsers = derived(feed, ($s) => $s.users);
export const feedFilters = derived(feed, ($s) => $s.filters);
export const feedHasMore = derived(feed, ($s) => $s.hasMore);
export const feedLoading = derived(feed, ($s) => $s.isLoading);
export const feedLoadingMore = derived(feed, ($s) => $s.isLoadingMore);
export const feedError = derived(feed, ($s) => $s.error);

// Action options for filters
export const actionOptions: { value: FeedAction | ""; text: string }[] = [
  { value: "", text: "Все действия" },
  { value: "created", text: "Создание" },
  { value: "status_changed", text: "Изменение статуса" },
  { value: "assigned", text: "Назначение" },
  { value: "unassigned", text: "Снятие назначения" },
  { value: "priority_changed", text: "Изменение приоритета" },
  { value: "due_date_changed", text: "Изменение срока" },
  { value: "story_points_changed", text: "Изменение SP" },
  { value: "attachment_added", text: "Добавление вложения" },
  { value: "attachment_removed", text: "Удаление вложения" },
  { value: "commented", text: "Комментарий" },
];

// Action labels for display
export const actionLabels: Record<FeedAction, string> = {
  created: "создал(а) задачу",
  status_changed: "изменил(а) статус",
  assigned: "назначил(а) исполнителя",
  unassigned: "снял(а) назначение",
  priority_changed: "изменил(а) приоритет",
  due_date_changed: "изменил(а) срок",
  story_points_changed: "изменил(а) story points",
  attachment_added: "добавил(а) вложение",
  attachment_removed: "удалил(а) вложение",
  commented: "прокомментировал(а)",
};
