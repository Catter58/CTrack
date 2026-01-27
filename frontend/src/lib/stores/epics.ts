/**
 * Store for epics management
 */

import { writable, derived } from "svelte/store";
import api from "$lib/api/client";

export interface Epic {
  id: string;
  key: string;
  title: string;
  description: string;
  priority: "lowest" | "low" | "medium" | "high" | "highest";
  status: {
    id: string;
    name: string;
    category: string;
    color: string;
  };
  total_issues: number;
  completed_issues: number;
  total_story_points: number;
  completed_story_points: number;
}

interface EpicsState {
  epics: Epic[];
  isLoading: boolean;
  error: string | null;
}

function createEpicsStore() {
  const { subscribe, set, update } = writable<EpicsState>({
    epics: [],
    isLoading: false,
    error: null,
  });

  return {
    subscribe,

    async loadEpics(projectKey: string) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const epics = await api.get<Epic[]>(
          `/api/projects/${projectKey}/epics`,
        );
        update((s) => ({
          ...s,
          epics,
          isLoading: false,
        }));
        return epics;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось загрузить эпики";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return [];
      }
    },

    clearError() {
      update((s) => ({ ...s, error: null }));
    },

    reset() {
      set({
        epics: [],
        isLoading: false,
        error: null,
      });
    },
  };
}

export const epicsStore = createEpicsStore();

export const epicsList = derived(epicsStore, ($e) => $e.epics);
export const epicsLoading = derived(epicsStore, ($e) => $e.isLoading);
export const epicsError = derived(epicsStore, ($e) => $e.error);

// Computed statistics
export const epicsStats = derived(epicsStore, ($e) => {
  const total = $e.epics.length;
  const completed = $e.epics.filter(
    (epic) => epic.status.category === "done",
  ).length;
  const totalIssues = $e.epics.reduce((sum, e) => sum + e.total_issues, 0);
  const completedIssues = $e.epics.reduce(
    (sum, e) => sum + e.completed_issues,
    0,
  );
  const totalSP = $e.epics.reduce((sum, e) => sum + e.total_story_points, 0);
  const completedSP = $e.epics.reduce(
    (sum, e) => sum + e.completed_story_points,
    0,
  );

  return {
    total,
    completed,
    totalIssues,
    completedIssues,
    totalSP,
    completedSP,
  };
});
