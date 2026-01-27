/**
 * Store for single issue detail
 */

import { writable, derived } from "svelte/store";
import api from "$lib/api/client";

export interface IssueType {
  id: string;
  name: string;
  icon: string;
  color: string;
  is_subtask: boolean;
}

export interface Status {
  id: string;
  name: string;
  category: string;
  color: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  first_name: string | null;
  last_name: string | null;
}

export interface Comment {
  id: string;
  author: User;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowTransition {
  id: string;
  from_status: Status;
  to_status: Status;
  name: string;
}

export interface IssueDetail {
  id: string;
  key: string;
  issue_number: number;
  title: string;
  description: string;
  priority: string;
  story_points: number | null;
  due_date: string | null;
  custom_fields: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  issue_type: IssueType;
  status: Status;
  assignee: User | null;
  reporter: User;
  parent_id: string | null;
}

interface IssueState {
  issue: IssueDetail | null;
  comments: Comment[];
  transitions: WorkflowTransition[];
  isLoading: boolean;
  error: string | null;
}

function createIssueStore() {
  const { subscribe, set, update } = writable<IssueState>({
    issue: null,
    comments: [],
    transitions: [],
    isLoading: false,
    error: null,
  });

  return {
    subscribe,

    async load(issueKey: string) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const issue = await api.get<IssueDetail>(`/api/issues/${issueKey}`);
        update((s) => ({ ...s, issue, isLoading: false }));
        return issue;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load issue";
        update((s) => ({ ...s, isLoading: false, error: message }));
        return null;
      }
    },

    async loadComments(issueKey: string) {
      try {
        const comments = await api.get<Comment[]>(
          `/api/issues/${issueKey}/comments`,
        );
        update((s) => ({ ...s, comments }));
        return comments;
      } catch (err) {
        console.error("Failed to load comments:", err);
        return [];
      }
    },

    async loadTransitions(issueKey: string) {
      try {
        const transitions = await api.get<WorkflowTransition[]>(
          `/api/issues/${issueKey}/transitions`,
        );
        update((s) => ({ ...s, transitions }));
        return transitions;
      } catch (err) {
        console.error("Failed to load transitions:", err);
        return [];
      }
    },

    async update(
      issueKey: string,
      data: {
        title?: string;
        description?: string;
        status_id?: string;
        priority?: string;
        assignee_id?: number | null;
        story_points?: number | null;
        due_date?: string | null;
      },
    ): Promise<IssueDetail | null> {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const issue = await api.patch<IssueDetail>(
          `/api/issues/${issueKey}`,
          data,
        );
        update((s) => ({ ...s, issue, isLoading: false }));
        return issue;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to update issue";
        update((s) => ({ ...s, isLoading: false, error: message }));
        return null;
      }
    },

    async addComment(
      issueKey: string,
      content: string,
    ): Promise<Comment | null> {
      try {
        const comment = await api.post<Comment>(
          `/api/issues/${issueKey}/comments`,
          {
            content,
          },
        );
        update((s) => ({ ...s, comments: [...s.comments, comment] }));
        return comment;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to add comment";
        update((s) => ({ ...s, error: message }));
        return null;
      }
    },

    async transitionStatus(
      issueKey: string,
      statusId: string,
    ): Promise<IssueDetail | null> {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const issue = await api.patch<IssueDetail>(`/api/issues/${issueKey}`, {
          status_id: statusId,
        });
        update((s) => ({ ...s, issue, isLoading: false }));

        // Reload transitions after status change
        this.loadTransitions(issueKey);

        return issue;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to transition issue";
        update((s) => ({ ...s, isLoading: false, error: message }));
        return null;
      }
    },

    reset() {
      set({
        issue: null,
        comments: [],
        transitions: [],
        isLoading: false,
        error: null,
      });
    },

    clearError() {
      update((s) => ({ ...s, error: null }));
    },
  };
}

export const issue = createIssueStore();

export const currentIssue = derived(issue, ($s) => $s.issue);
export const issueComments = derived(issue, ($s) => $s.comments);
export const issueTransitions = derived(issue, ($s) => $s.transitions);
export const issueLoading = derived(issue, ($s) => $s.isLoading);
export const issueError = derived(issue, ($s) => $s.error);

// Priority helpers
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
