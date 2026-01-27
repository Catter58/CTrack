/**
 * Store for backlog management
 */

import { writable, derived } from "svelte/store";
import api from "$lib/api/client";

export interface BacklogIssue {
  id: string;
  key: string;
  title: string;
  description: string | null;
  priority: "lowest" | "low" | "medium" | "high" | "highest";
  story_points: number | null;
  due_date: string | null;
  epic_id: string | null;
  issue_type: {
    id: string;
    name: string;
    icon: string;
    color: string;
    is_subtask: boolean;
  };
  status: {
    id: string;
    name: string;
    category: string;
    color: string;
  };
  assignee: {
    id: number;
    username: string;
    email: string;
    full_name: string;
  } | null;
  reporter: {
    id: number;
    username: string;
    email: string;
    full_name: string;
  };
  created_at: string;
  updated_at: string;
}

interface BacklogState {
  issues: BacklogIssue[];
  totalCount: number;
  hasMore: boolean;
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
}

const PAGE_SIZE = 20;

function createBacklogStore() {
  const { subscribe, set, update } = writable<BacklogState>({
    issues: [],
    totalCount: 0,
    hasMore: true,
    isLoading: false,
    isLoadingMore: false,
    error: null,
  });

  let currentProjectKey = "";

  return {
    subscribe,

    async loadBacklog(projectKey: string, limit = PAGE_SIZE, offset = 0) {
      currentProjectKey = projectKey;
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const params: Record<string, string> = {
          limit: String(limit),
        };
        if (offset > 0) {
          params.offset = String(offset);
        }

        const issues = await api.get<BacklogIssue[]>(
          `/api/projects/${projectKey}/backlog`,
          params,
        );

        update((s) => ({
          ...s,
          issues,
          totalCount: issues.length,
          hasMore: issues.length >= limit,
          isLoading: false,
        }));
        return issues;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось загрузить бэклог";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return [];
      }
    },

    async loadMore() {
      let currentState: BacklogState | null = null;
      const unsubscribe = subscribe((s) => {
        currentState = s;
      });
      unsubscribe();

      if (
        !currentState ||
        currentState.isLoadingMore ||
        !currentState.hasMore
      ) {
        return [];
      }

      update((s) => ({ ...s, isLoadingMore: true }));

      try {
        const offset = currentState.issues.length;
        const params: Record<string, string> = {
          limit: String(PAGE_SIZE),
          offset: String(offset),
        };

        const newIssues = await api.get<BacklogIssue[]>(
          `/api/projects/${currentProjectKey}/backlog`,
          params,
        );

        update((s) => ({
          ...s,
          issues: [...s.issues, ...newIssues],
          totalCount: s.issues.length + newIssues.length,
          hasMore: newIssues.length >= PAGE_SIZE,
          isLoadingMore: false,
        }));
        return newIssues;
      } catch {
        update((s) => ({
          ...s,
          isLoadingMore: false,
        }));
        return [];
      }
    },

    async updateIssueSprint(issueKey: string, sprintId: string | null) {
      try {
        const url = sprintId
          ? `/api/issues/${issueKey}/sprint?sprint_id=${sprintId}`
          : `/api/issues/${issueKey}/sprint`;
        const updated = await api.patch(url);

        // Remove from backlog if added to sprint
        if (sprintId) {
          update((s) => ({
            ...s,
            issues: s.issues.filter((i) => i.key !== issueKey),
            totalCount: s.totalCount - 1,
          }));
        }

        return updated;
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Не удалось обновить спринт задачи";
        update((s) => ({ ...s, error: message }));
        throw err;
      }
    },

    addIssue(issue: BacklogIssue) {
      update((s) => ({
        ...s,
        issues: [issue, ...s.issues],
        totalCount: s.totalCount + 1,
      }));
    },

    removeIssue(issueKey: string) {
      update((s) => ({
        ...s,
        issues: s.issues.filter((i) => i.key !== issueKey),
        totalCount: s.totalCount - 1,
      }));
    },

    async updateIssueStoryPoints(issueKey: string, storyPoints: number | null) {
      // Optimistic update
      update((s) => ({
        ...s,
        issues: s.issues.map((issue) =>
          issue.key === issueKey
            ? { ...issue, story_points: storyPoints }
            : issue,
        ),
      }));

      await api.patch(`/api/issues/${issueKey}`, {
        story_points: storyPoints,
      });
    },

    clearError() {
      update((s) => ({ ...s, error: null }));
    },

    reset() {
      set({
        issues: [],
        totalCount: 0,
        hasMore: true,
        isLoading: false,
        isLoadingMore: false,
        error: null,
      });
    },
  };
}

export const backlog = createBacklogStore();

export const backlogIssues = derived(backlog, ($b) => $b.issues);
export const backlogCount = derived(backlog, ($b) => $b.totalCount);
export const backlogLoading = derived(backlog, ($b) => $b.isLoading);
export const backlogLoadingMore = derived(backlog, ($b) => $b.isLoadingMore);
export const backlogHasMore = derived(backlog, ($b) => $b.hasMore);
export const backlogError = derived(backlog, ($b) => $b.error);

export const backlogStoryPoints = derived(backlog, ($b) =>
  $b.issues.reduce((sum, i) => sum + (i.story_points || 0), 0),
);
