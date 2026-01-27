/**
 * Store for project metrics (velocity, burndown)
 */

import { writable, derived } from "svelte/store";
import api from "$lib/api/client";

export interface VelocitySprint {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  committed_story_points: number;
  completed_story_points: number;
}

export interface VelocityData {
  sprints: VelocitySprint[];
  average_velocity: number;
  total_sprints: number;
}

export interface BurndownPoint {
  date: string;
  value: number;
}

export interface BurndownData {
  sprint_id: string;
  sprint_name: string;
  start_date: string;
  end_date: string;
  initial_story_points: number;
  ideal: BurndownPoint[];
  actual: BurndownPoint[];
}

interface MetricsState {
  velocity: VelocityData | null;
  burndown: BurndownData | null;
  isLoadingVelocity: boolean;
  isLoadingBurndown: boolean;
  error: string | null;
}

function createMetricsStore() {
  const { subscribe, set, update } = writable<MetricsState>({
    velocity: null,
    burndown: null,
    isLoadingVelocity: false,
    isLoadingBurndown: false,
    error: null,
  });

  return {
    subscribe,

    async loadVelocity(projectKey: string, limit: number = 6) {
      update((s) => ({ ...s, isLoadingVelocity: true, error: null }));

      try {
        const data = await api.get<VelocityData>(
          `/api/projects/${projectKey}/metrics/velocity`,
          { limit: String(limit) },
        );
        update((s) => ({
          ...s,
          velocity: data,
          isLoadingVelocity: false,
        }));
        return data;
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Не удалось загрузить данные velocity";
        update((s) => ({
          ...s,
          isLoadingVelocity: false,
          error: message,
        }));
        return null;
      }
    },

    async loadBurndown(sprintId: string) {
      update((s) => ({ ...s, isLoadingBurndown: true, error: null }));

      try {
        const data = await api.get<BurndownData>(
          `/api/sprints/${sprintId}/burndown`,
        );
        update((s) => ({
          ...s,
          burndown: data,
          isLoadingBurndown: false,
        }));
        return data;
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Не удалось загрузить данные burndown";
        update((s) => ({
          ...s,
          isLoadingBurndown: false,
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
        velocity: null,
        burndown: null,
        isLoadingVelocity: false,
        isLoadingBurndown: false,
        error: null,
      });
    },
  };
}

export const metrics = createMetricsStore();

export const velocityData = derived(metrics, ($m) => $m.velocity);
export const burndownData = derived(metrics, ($m) => $m.burndown);
export const isLoadingVelocity = derived(metrics, ($m) => $m.isLoadingVelocity);
export const isLoadingBurndown = derived(metrics, ($m) => $m.isLoadingBurndown);
export const metricsError = derived(metrics, ($m) => $m.error);
