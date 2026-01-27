/**
 * Store for sprints management
 */

import { writable } from "svelte/store";
import api from "$lib/api/client";

export type SprintStatus = "planned" | "active" | "completed";

export interface Sprint {
  id: string;
  project_id: string;
  name: string;
  goal: string;
  start_date: string;
  end_date: string;
  status: SprintStatus;
  initial_story_points: number | null;
  completed_story_points: number | null;
  created_at: string;
  updated_at: string;
}

export interface SprintWithStats extends Sprint {
  total_story_points: number;
  remaining_story_points: number;
  total_issues: number;
  completed_issues: number;
  remaining_issues: number;
}

export interface SprintIssue {
  id: string;
  key: string;
  title: string;
  status: {
    id: string;
    name: string;
    category: string;
    color: string;
  };
  issue_type: {
    id: string;
    name: string;
    icon: string;
    color: string;
  };
  assignee: {
    id: number;
    username: string;
    full_name: string;
  } | null;
  story_points: number | null;
  priority: string;
}

export interface CreateSprintData {
  name: string;
  goal?: string;
  start_date: string;
  end_date: string;
}

export interface UpdateSprintData {
  name?: string;
  goal?: string;
  start_date?: string;
  end_date?: string;
}

interface SprintsState {
  sprints: Sprint[];
  currentSprint: SprintWithStats | null;
  sprintIssues: SprintIssue[];
  activeSprint: Sprint | null;
  isLoading: boolean;
  error: string | null;
}

function createSprintsStore() {
  const { subscribe, set, update } = writable<SprintsState>({
    sprints: [],
    currentSprint: null,
    sprintIssues: [],
    activeSprint: null,
    isLoading: false,
    error: null,
  });

  return {
    subscribe,

    async loadSprints(projectKey: string, status?: SprintStatus) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const params = status ? { status } : undefined;
        const sprints = await api.get<Sprint[]>(
          `/api/projects/${projectKey}/sprints`,
          params,
        );
        const activeSprint = sprints.find((s) => s.status === "active") || null;
        update((s) => ({
          ...s,
          sprints,
          activeSprint,
          isLoading: false,
        }));
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось загрузить спринты";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
      }
    },

    async loadSprint(sprintId: string) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const sprint = await api.get<SprintWithStats>(
          `/api/sprints/${sprintId}`,
        );
        update((s) => ({
          ...s,
          currentSprint: sprint,
          isLoading: false,
        }));
        return sprint;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось загрузить спринт";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return null;
      }
    },

    async loadSprintIssues(sprintId: string) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const issues = await api.get<SprintIssue[]>(
          `/api/sprints/${sprintId}/issues`,
        );
        update((s) => ({
          ...s,
          sprintIssues: issues,
          isLoading: false,
        }));
        return issues;
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Не удалось загрузить задачи спринта";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return [];
      }
    },

    async createSprint(projectKey: string, data: CreateSprintData) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const sprint = await api.post<Sprint>(
          `/api/projects/${projectKey}/sprints`,
          data,
        );
        update((s) => ({
          ...s,
          sprints: [sprint, ...s.sprints],
          isLoading: false,
        }));
        return sprint;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось создать спринт";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return null;
      }
    },

    async updateSprint(sprintId: string, data: UpdateSprintData) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const sprint = await api.patch<Sprint>(
          `/api/sprints/${sprintId}`,
          data,
        );
        update((s) => ({
          ...s,
          sprints: s.sprints.map((sp) => (sp.id === sprintId ? sprint : sp)),
          currentSprint:
            s.currentSprint?.id === sprintId
              ? { ...s.currentSprint, ...sprint }
              : s.currentSprint,
          isLoading: false,
        }));
        return sprint;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось обновить спринт";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return null;
      }
    },

    async deleteSprint(sprintId: string) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        await api.delete(`/api/sprints/${sprintId}`);
        update((s) => ({
          ...s,
          sprints: s.sprints.filter((sp) => sp.id !== sprintId),
          currentSprint:
            s.currentSprint?.id === sprintId ? null : s.currentSprint,
          isLoading: false,
        }));
        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось удалить спринт";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return false;
      }
    },

    async startSprint(sprintId: string) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const sprint = await api.post<Sprint>(`/api/sprints/${sprintId}/start`);
        update((s) => ({
          ...s,
          sprints: s.sprints.map((sp) => (sp.id === sprintId ? sprint : sp)),
          activeSprint: sprint,
          isLoading: false,
        }));
        return sprint;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось запустить спринт";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return null;
      }
    },

    async completeSprint(
      sprintId: string,
      moveIncompleteTo: string | null = null,
    ) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const sprint = await api.post<Sprint>(
          `/api/sprints/${sprintId}/complete`,
          { move_incomplete_to: moveIncompleteTo },
        );
        update((s) => ({
          ...s,
          sprints: s.sprints.map((sp) => (sp.id === sprintId ? sprint : sp)),
          activeSprint: s.activeSprint?.id === sprintId ? null : s.activeSprint,
          isLoading: false,
        }));
        return sprint;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось завершить спринт";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return null;
      }
    },

    clearError() {
      update((s) => ({ ...s, error: null }));
    },

    reset() {
      set({
        sprints: [],
        currentSprint: null,
        sprintIssues: [],
        activeSprint: null,
        isLoading: false,
        error: null,
      });
    },
  };
}

export const sprints = createSprintsStore();
