/**
 * Store for global tasks (all user's tasks across projects)
 */

import { writable, derived } from "svelte/store";
import api from "$lib/api/client";
import type { Project } from "$lib/stores/projects";

export interface GlobalIssueType {
  id: string;
  name: string;
  icon: string;
  color: string;
  is_subtask: boolean;
}

export interface GlobalStatus {
  id: string;
  name: string;
  category: "todo" | "in_progress" | "done";
  color: string;
}

export interface GlobalUser {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
}

export interface GlobalIssue {
  id: string;
  key: string;
  title: string;
  priority: "lowest" | "low" | "medium" | "high" | "highest";
  due_date: string | null;
  created_at: string;
  issue_type: GlobalIssueType;
  status: GlobalStatus;
  assignee: GlobalUser | null;
  project: {
    id: string;
    key: string;
    name: string;
  };
}

export interface GlobalTasksFilters {
  project_id?: string;
  status_id?: string;
  priority?: string;
  assignee_id?: number;
  due_date_from?: string;
  due_date_to?: string;
  search?: string;
}

export interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
}

export interface SortState {
  column: string;
  direction: "asc" | "desc";
}

interface GlobalTasksResponse {
  items: GlobalIssue[];
  total: number;
  page: number;
  page_size: number;
}

interface GlobalTasksState {
  tasks: GlobalIssue[];
  projects: Project[];
  statuses: GlobalStatus[];
  assignees: GlobalUser[];
  filters: GlobalTasksFilters;
  pagination: PaginationState;
  sort: SortState;
  isLoading: boolean;
  error: string | null;
}

function createGlobalTasksStore() {
  const { subscribe, set, update } = writable<GlobalTasksState>({
    tasks: [],
    projects: [],
    statuses: [],
    assignees: [],
    filters: {},
    pagination: {
      page: 1,
      pageSize: 20,
      total: 0,
    },
    sort: {
      column: "created_at",
      direction: "desc",
    },
    isLoading: false,
    error: null,
  });

  return {
    subscribe,

    async loadTasks(filters?: GlobalTasksFilters) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        let state: GlobalTasksState | undefined;
        const unsubscribe = subscribe((s) => {
          state = s;
        });
        unsubscribe();

        if (!state) return;

        const params: Record<string, string> = {
          page: String(state.pagination.page),
          page_size: String(state.pagination.pageSize),
        };

        // Add sort parameters
        if (state.sort.column) {
          params.sort_by = state.sort.column;
          params.sort_dir = state.sort.direction;
        }

        // Add filters
        const activeFilters = filters ?? state.filters;
        if (activeFilters.project_id) {
          params.project_id = activeFilters.project_id;
        }
        if (activeFilters.status_id) {
          params.status_id = activeFilters.status_id;
        }
        if (activeFilters.priority) {
          params.priority = activeFilters.priority;
        }
        if (activeFilters.assignee_id !== undefined) {
          params.assignee_id = String(activeFilters.assignee_id);
        }
        if (activeFilters.due_date_from) {
          params.due_date_from = activeFilters.due_date_from;
        }
        if (activeFilters.due_date_to) {
          params.due_date_to = activeFilters.due_date_to;
        }
        if (activeFilters.search) {
          params.search = activeFilters.search;
        }

        const response = await api.get<GlobalTasksResponse>(
          "/api/issues",
          params,
        );

        update((s) => ({
          ...s,
          tasks: response.items,
          pagination: {
            ...s.pagination,
            total: response.total,
          },
          filters: activeFilters,
          isLoading: false,
        }));

        return response;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось загрузить задачи";
        update((s) => ({
          ...s,
          isLoading: false,
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

    async loadStatuses(projectId?: string) {
      try {
        const endpoint = projectId
          ? `/api/projects/${projectId}/statuses`
          : "/api/statuses";
        const statuses = await api.get<GlobalStatus[]>(endpoint);
        update((s) => ({ ...s, statuses }));
        return statuses;
      } catch (err) {
        console.error("Failed to load statuses:", err);
        return [];
      }
    },

    async loadAssignees(projectKey?: string) {
      try {
        if (projectKey) {
          interface MemberResponse {
            user: {
              id: number;
              username: string;
              email: string;
              first_name: string;
              last_name: string;
            };
          }
          const members = await api.get<MemberResponse[]>(
            `/api/projects/${projectKey}/members`,
          );
          const assignees: GlobalUser[] = members.map((m) => ({
            id: m.user.id,
            username: m.user.username,
            email: m.user.email,
            full_name:
              `${m.user.first_name} ${m.user.last_name}`.trim() || null,
          }));
          update((s) => ({ ...s, assignees }));
          return assignees;
        }
        // If no project, clear assignees
        update((s) => ({ ...s, assignees: [] }));
        return [];
      } catch (err) {
        console.error("Failed to load assignees:", err);
        return [];
      }
    },

    setFilters(filters: GlobalTasksFilters) {
      update((s) => ({
        ...s,
        filters,
        pagination: { ...s.pagination, page: 1 },
      }));
    },

    setPage(page: number) {
      update((s) => ({
        ...s,
        pagination: { ...s.pagination, page },
      }));
    },

    setPageSize(pageSize: number) {
      update((s) => ({
        ...s,
        pagination: { ...s.pagination, page: 1, pageSize },
      }));
    },

    setSort(column: string, direction: "asc" | "desc") {
      update((s) => ({
        ...s,
        sort: { column, direction },
      }));
    },

    toggleSort(column: string) {
      update((s) => {
        if (s.sort.column === column) {
          return {
            ...s,
            sort: {
              column,
              direction: s.sort.direction === "asc" ? "desc" : "asc",
            },
          };
        }
        return {
          ...s,
          sort: { column, direction: "desc" },
        };
      });
    },

    clearFilters() {
      update((s) => ({
        ...s,
        filters: {},
        pagination: { ...s.pagination, page: 1 },
      }));
    },

    clearError() {
      update((s) => ({ ...s, error: null }));
    },

    reset() {
      set({
        tasks: [],
        projects: [],
        statuses: [],
        assignees: [],
        filters: {},
        pagination: {
          page: 1,
          pageSize: 20,
          total: 0,
        },
        sort: {
          column: "created_at",
          direction: "desc",
        },
        isLoading: false,
        error: null,
      });
    },
  };
}

export const globalTasks = createGlobalTasksStore();

// Derived stores
export const globalTasksList = derived(globalTasks, ($s) => $s.tasks);
export const globalTasksProjects = derived(globalTasks, ($s) => $s.projects);
export const globalTasksStatuses = derived(globalTasks, ($s) => $s.statuses);
export const globalTasksAssignees = derived(globalTasks, ($s) => $s.assignees);
export const globalTasksFilters = derived(globalTasks, ($s) => $s.filters);
export const globalTasksPagination = derived(
  globalTasks,
  ($s) => $s.pagination,
);
export const globalTasksSort = derived(globalTasks, ($s) => $s.sort);
export const globalTasksLoading = derived(globalTasks, ($s) => $s.isLoading);
export const globalTasksError = derived(globalTasks, ($s) => $s.error);

// Priority helpers
export const priorityOptions = [
  { value: "", text: "Все приоритеты" },
  { value: "highest", text: "Критический" },
  { value: "high", text: "Высокий" },
  { value: "medium", text: "Средний" },
  { value: "low", text: "Низкий" },
  { value: "lowest", text: "Минимальный" },
];

export const priorityLabels: Record<string, string> = {
  highest: "Критический",
  high: "Высокий",
  medium: "Средний",
  low: "Низкий",
  lowest: "Минимальный",
};

export const priorityColors: Record<string, string> = {
  highest: "#da1e28",
  high: "#ff832b",
  medium: "#f1c21b",
  low: "#0f62fe",
  lowest: "#6f6f6f",
};
