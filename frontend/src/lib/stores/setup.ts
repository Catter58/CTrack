/**
 * Store for setup wizard
 */

import { writable, derived } from "svelte/store";
import api from "$lib/api/client";

export interface SetupStatus {
  setup_required: boolean;
  has_users: boolean;
  has_issue_types: boolean;
  has_statuses: boolean;
}

interface SetupState {
  status: SetupStatus | null;
  isLoading: boolean;
  error: string | null;
}

function createSetupStore() {
  const { subscribe, update } = writable<SetupState>({
    status: null,
    isLoading: true,
    error: null,
  });

  return {
    subscribe,

    async checkStatus() {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const status = await api.get<SetupStatus>("/api/setup/status");
        update((s) => ({
          ...s,
          status,
          isLoading: false,
        }));
        return status;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to check setup status";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return null;
      }
    },

    async completeSetup(data: {
      admin_user: {
        email: string;
        username: string;
        password: string;
        full_name?: string;
      };
      org_settings: {
        name: string;
        timezone?: string;
      };
      issue_type_template: string;
    }) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const result = await api.post<{
          access_token: string;
          refresh_token: string;
          message: string;
        }>("/api/setup/complete", data);

        update((s) => ({
          ...s,
          status: {
            setup_required: false,
            has_users: true,
            has_issue_types: true,
            has_statuses: true,
          },
          isLoading: false,
        }));

        return result;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Setup failed";
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
  };
}

export const setup = createSetupStore();

export const setupStatus = derived(setup, ($s) => $s.status);
export const setupRequired = derived(
  setup,
  ($s) => $s.status?.setup_required ?? false,
);
export const setupLoading = derived(setup, ($s) => $s.isLoading);
export const setupError = derived(setup, ($s) => $s.error);
