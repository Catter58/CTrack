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
  avatar?: string | null;
}

export interface Comment {
  id: string;
  author: User;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface Activity {
  id: string;
  user: User | null;
  action: string;
  field_name: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  created_at: string;
}

export interface Attachment {
  id: string;
  filename: string;
  file_size: number;
  content_type: string;
  uploaded_by: User;
  created_at: string;
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
  epic_id: string | null;
  children_count: number;
  completed_children_count: number;
}

export interface ChildIssue {
  id: string;
  key: string;
  title: string;
  priority: string;
  story_points: number | null;
  due_date: string | null;
  created_at: string;
  issue_type: IssueType;
  status: Status;
  assignee: User | null;
  epic_id: string | null;
}

interface IssueState {
  issue: IssueDetail | null;
  comments: Comment[];
  transitions: WorkflowTransition[];
  children: ChildIssue[];
  activities: Activity[];
  attachments: Attachment[];
  isLoading: boolean;
  error: string | null;
}

function createIssueStore() {
  const { subscribe, set, update } = writable<IssueState>({
    issue: null,
    comments: [],
    transitions: [],
    children: [],
    activities: [],
    attachments: [],
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

    async loadChildren(issueKey: string) {
      try {
        const children = await api.get<ChildIssue[]>(
          `/api/issues/${issueKey}/children`,
        );
        update((s) => ({ ...s, children }));
        return children;
      } catch (err) {
        console.error("Failed to load children:", err);
        return [];
      }
    },

    async loadActivities(issueKey: string) {
      try {
        const activities = await api.get<Activity[]>(
          `/api/issues/${issueKey}/activity`,
        );
        update((s) => ({ ...s, activities }));
        return activities;
      } catch (err) {
        console.error("Failed to load activities:", err);
        return [];
      }
    },

    async loadAttachments(issueKey: string) {
      try {
        const attachments = await api.get<Attachment[]>(
          `/api/issues/${issueKey}/attachments`,
        );
        update((s) => ({ ...s, attachments }));
        return attachments;
      } catch (err) {
        console.error("Failed to load attachments:", err);
        return [];
      }
    },

    async uploadAttachment(
      issueKey: string,
      file: File,
    ): Promise<Attachment | null> {
      try {
        const attachment = await api.uploadFile<Attachment>(
          `/api/issues/${issueKey}/attachments`,
          file,
        );
        update((s) => ({ ...s, attachments: [...s.attachments, attachment] }));
        return attachment;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to upload attachment";
        update((s) => ({ ...s, error: message }));
        return null;
      }
    },

    async deleteAttachment(attachmentId: string): Promise<boolean> {
      try {
        await api.delete(`/api/attachments/${attachmentId}`);
        update((s) => ({
          ...s,
          attachments: s.attachments.filter((a) => a.id !== attachmentId),
        }));
        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to delete attachment";
        update((s) => ({ ...s, error: message }));
        return false;
      }
    },

    async quickCompleteChild(childKey: string, doneStatusId: string) {
      try {
        await api.patch(`/api/issues/${childKey}`, {
          status_id: doneStatusId,
        });
        // Update the child's status in local state
        update((s) => ({
          ...s,
          children: s.children.map((c) =>
            c.key === childKey
              ? { ...c, status: { ...c.status, category: "done" } }
              : c,
          ),
          // Update parent's stats
          issue: s.issue
            ? {
                ...s.issue,
                completed_children_count: s.issue.completed_children_count + 1,
              }
            : s.issue,
        }));
        return true;
      } catch (err) {
        console.error("Failed to complete child:", err);
        return false;
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
        custom_fields?: Record<string, unknown>;
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

    async updateComment(
      commentId: string,
      content: string,
    ): Promise<Comment | null> {
      try {
        const comment = await api.patch<Comment>(`/api/comments/${commentId}`, {
          content,
        });
        update((s) => ({
          ...s,
          comments: s.comments.map((c) => (c.id === commentId ? comment : c)),
        }));
        return comment;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to update comment";
        update((s) => ({ ...s, error: message }));
        return null;
      }
    },

    async deleteComment(commentId: string): Promise<boolean> {
      try {
        await api.delete(`/api/comments/${commentId}`);
        update((s) => ({
          ...s,
          comments: s.comments.filter((c) => c.id !== commentId),
        }));
        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to delete comment";
        update((s) => ({ ...s, error: message }));
        return false;
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
        children: [],
        activities: [],
        attachments: [],
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
export const issueChildren = derived(issue, ($s) => $s.children);
export const issueActivities = derived(issue, ($s) => $s.activities);
export const issueAttachments = derived(issue, ($s) => $s.attachments);
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
