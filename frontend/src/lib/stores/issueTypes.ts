/**
 * Store for issue types management
 */

import { writable, derived } from "svelte/store";
import api from "$lib/api/client";

export interface IssueType {
  id: string;
  name: string;
  icon: string;
  color: string;
  is_subtask: boolean;
  parent_types: string[];
  order: number;
}

interface IssueTypesState {
  items: IssueType[];
  isLoading: boolean;
  error: string | null;
}

function createIssueTypesStore() {
  const { subscribe, update } = writable<IssueTypesState>({
    items: [],
    isLoading: false,
    error: null,
  });

  return {
    subscribe,

    async load(projectKey: string) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const items = await api.get<IssueType[]>(
          `/api/projects/${projectKey}/issue-types`,
        );
        update((s) => ({ ...s, items, isLoading: false }));
        return items;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load issue types";
        update((s) => ({ ...s, isLoading: false, error: message }));
        return null;
      }
    },

    async create(
      projectKey: string,
      data: Omit<IssueType, "id">,
    ): Promise<IssueType | null> {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const item = await api.post<IssueType>(
          `/api/projects/${projectKey}/issue-types`,
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
          err instanceof Error ? err.message : "Failed to create issue type";
        update((s) => ({ ...s, isLoading: false, error: message }));
        return null;
      }
    },

    async update(
      issueTypeId: string,
      data: Partial<Omit<IssueType, "id">>,
    ): Promise<IssueType | null> {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const item = await api.patch<IssueType>(
          `/api/issue-types/${issueTypeId}`,
          data,
        );
        update((s) => ({
          ...s,
          items: s.items.map((i) => (i.id === issueTypeId ? item : i)),
          isLoading: false,
        }));
        return item;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to update issue type";
        update((s) => ({ ...s, isLoading: false, error: message }));
        return null;
      }
    },

    async delete(issueTypeId: string): Promise<boolean> {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        await api.delete(`/api/issue-types/${issueTypeId}`);
        update((s) => ({
          ...s,
          items: s.items.filter((i) => i.id !== issueTypeId),
          isLoading: false,
        }));
        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to delete issue type";
        update((s) => ({ ...s, isLoading: false, error: message }));
        return false;
      }
    },

    clearError() {
      update((s) => ({ ...s, error: null }));
    },
  };
}

export const issueTypes = createIssueTypesStore();

export const issueTypesLoading = derived(issueTypes, ($s) => $s.isLoading);
export const issueTypesError = derived(issueTypes, ($s) => $s.error);
export const issueTypesList = derived(issueTypes, ($s) => $s.items);
