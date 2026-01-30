/**
 * Store for project reports
 */

import { writable, derived } from "svelte/store";
import api from "$lib/api/client";
import { progress } from "$lib/stores/progress";

export interface StatusCount {
  status_id: string;
  status_name: string;
  category: string;
  status_color: string;
  count: number;
}

export interface PriorityCount {
  priority: string;
  count: number;
}

export interface AssigneeCount {
  assignee_id: number | null;
  assignee_name: string | null;
  count: number;
}

export interface TypeCount {
  type_id: string;
  type_name: string;
  count: number;
}

export interface ProjectSummary {
  total_issues: number;
  by_status: StatusCount[];
  by_type: TypeCount[];
  by_priority: PriorityCount[];
  by_assignee: AssigneeCount[];
}

export interface CreatedVsResolvedItem {
  date: string;
  created: number;
  resolved: number;
}

export interface CreatedVsResolved {
  period: string;
  date_from: string;
  date_to: string;
  data: CreatedVsResolvedItem[];
}

export interface CycleTimeGroup {
  group_name: string;
  group_id: string | null;
  avg_hours: number | null;
  median_hours: number | null;
  count: number;
}

export interface CycleTimeData {
  overall_avg_hours: number | null;
  overall_median_hours: number | null;
  total_completed: number;
  by_type: CycleTimeGroup[];
  by_priority: CycleTimeGroup[];
}

interface ReportsState {
  summary: ProjectSummary | null;
  createdVsResolved: CreatedVsResolved | null;
  cycleTime: CycleTimeData | null;
  isLoadingSummary: boolean;
  isLoadingCreatedVsResolved: boolean;
  isLoadingCycleTime: boolean;
  error: string | null;
}

function createReportsStore() {
  const { subscribe, set, update } = writable<ReportsState>({
    summary: null,
    createdVsResolved: null,
    cycleTime: null,
    isLoadingSummary: false,
    isLoadingCreatedVsResolved: false,
    isLoadingCycleTime: false,
    error: null,
  });

  return {
    subscribe,

    async loadSummary(
      projectKey: string,
      showProgress: boolean = true,
    ): Promise<ProjectSummary | null> {
      update((s) => ({ ...s, isLoadingSummary: true, error: null }));
      const progressId = showProgress
        ? progress.start("report", "Сводка по проекту")
        : null;

      try {
        const data = await api.get<ProjectSummary>(
          `/api/projects/${projectKey}/reports/summary`,
        );
        update((s) => ({
          ...s,
          summary: data,
          isLoadingSummary: false,
        }));
        if (progressId) progress.done(progressId);
        return data;
      } catch (err) {
        if (progressId) progress.error(progressId);
        const message =
          err instanceof Error
            ? err.message
            : "Не удалось загрузить сводку по проекту";
        update((s) => ({
          ...s,
          isLoadingSummary: false,
          error: message,
        }));
        return null;
      }
    },

    async loadCreatedVsResolved(
      projectKey: string,
      days: number = 30,
      showProgress: boolean = true,
    ): Promise<CreatedVsResolved | null> {
      update((s) => ({ ...s, isLoadingCreatedVsResolved: true, error: null }));
      const progressId = showProgress
        ? progress.start("report", "Создано/решено")
        : null;

      try {
        const data = await api.get<CreatedVsResolved>(
          `/api/projects/${projectKey}/reports/created-vs-resolved`,
          { days: String(days) },
        );
        update((s) => ({
          ...s,
          createdVsResolved: data,
          isLoadingCreatedVsResolved: false,
        }));
        if (progressId) progress.done(progressId);
        return data;
      } catch (err) {
        if (progressId) progress.error(progressId);
        const message =
          err instanceof Error
            ? err.message
            : "Не удалось загрузить данные создано/решено";
        update((s) => ({
          ...s,
          isLoadingCreatedVsResolved: false,
          error: message,
        }));
        return null;
      }
    },

    async loadCycleTime(
      projectKey: string,
      days: number = 30,
      showProgress: boolean = true,
    ): Promise<CycleTimeData | null> {
      update((s) => ({ ...s, isLoadingCycleTime: true, error: null }));
      const progressId = showProgress
        ? progress.start("report", "Время цикла")
        : null;

      try {
        const data = await api.get<CycleTimeData>(
          `/api/projects/${projectKey}/reports/cycle-time`,
          { days: String(days) },
        );
        update((s) => ({
          ...s,
          cycleTime: data,
          isLoadingCycleTime: false,
        }));
        if (progressId) progress.done(progressId);
        return data;
      } catch (err) {
        if (progressId) progress.error(progressId);
        const message =
          err instanceof Error
            ? err.message
            : "Не удалось загрузить время цикла";
        update((s) => ({
          ...s,
          isLoadingCycleTime: false,
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
        summary: null,
        createdVsResolved: null,
        cycleTime: null,
        isLoadingSummary: false,
        isLoadingCreatedVsResolved: false,
        isLoadingCycleTime: false,
        error: null,
      });
    },
  };
}

export const reports = createReportsStore();

export const summaryData = derived(reports, ($r) => $r.summary);
export const createdVsResolvedData = derived(
  reports,
  ($r) => $r.createdVsResolved,
);
export const cycleTimeData = derived(reports, ($r) => $r.cycleTime);
export const isLoadingSummary = derived(reports, ($r) => $r.isLoadingSummary);
export const isLoadingCreatedVsResolved = derived(
  reports,
  ($r) => $r.isLoadingCreatedVsResolved,
);
export const isLoadingCycleTime = derived(
  reports,
  ($r) => $r.isLoadingCycleTime,
);
export const reportsError = derived(reports, ($r) => $r.error);
