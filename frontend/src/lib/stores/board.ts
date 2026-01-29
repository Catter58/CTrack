/**
 * Store for board/kanban management
 */

import { writable, derived, get } from "svelte/store";
import api from "$lib/api/client";

export interface IssueType {
  id: string;
  name: string;
  icon: string;
  color: string;
  is_subtask: boolean;
  is_epic: boolean;
}

export interface Status {
  id: string;
  name: string;
  category: "todo" | "in_progress" | "done";
  color: string;
  order: number;
}

export interface Issue {
  id: string;
  key: string;
  title: string;
  description: string | null;
  priority: "lowest" | "low" | "medium" | "high" | "highest";
  story_points: number | null;
  due_date: string | null;
  epic_id: string | null;
  issue_type: IssueType;
  status: Status;
  assignee: {
    id: number;
    username: string;
    email: string;
    full_name: string;
  } | null;
  reporter: { id: number; username: string; email: string; full_name: string };
  created_at: string;
  updated_at: string;
}

export interface Board {
  id: string;
  name: string;
  board_type: "kanban" | "scrum";
  columns: string[];
  filters: Record<string, unknown>;
  settings: Record<string, unknown>;
  sprint_id: string | null;
}

export interface BoardColumn {
  status: Status;
  issues: Issue[];
  count: number;
}

export interface BoardData {
  board: Board;
  columns: BoardColumn[];
}

export interface WorkflowTransition {
  id: string;
  from_status: Status;
  to_status: Status;
  name: string;
}

interface BoardState {
  boards: Board[];
  currentBoard: Board | null;
  columns: BoardColumn[];
  issueTypes: IssueType[];
  statuses: Status[];
  workflowTransitions: WorkflowTransition[];
  isLoading: boolean;
  error: string | null;
}

function createBoardStore() {
  const store = writable<BoardState>({
    boards: [],
    currentBoard: null,
    columns: [],
    issueTypes: [],
    statuses: [],
    workflowTransitions: [],
    isLoading: false,
    error: null,
  });

  const { subscribe, set, update } = store;

  return {
    subscribe,

    async loadBoards(projectKey: string) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const boards = await api.get<Board[]>(
          `/api/projects/${projectKey}/boards`,
        );
        update((s) => ({
          ...s,
          boards,
          isLoading: false,
        }));
        return boards;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load boards";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return [];
      }
    },

    async loadBoardData(
      boardId: string,
      filters?: {
        assignee_id?: number;
        type_id?: string;
        priority?: string;
        search?: string;
        sprint_id?: string;
      },
    ) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        // Build query params from filters
        const params: Record<string, string> = {};
        if (filters?.assignee_id !== undefined) {
          params.assignee_id = String(filters.assignee_id);
        }
        if (filters?.type_id) {
          params.type_id = filters.type_id;
        }
        if (filters?.priority) {
          params.priority = filters.priority;
        }
        if (filters?.search) {
          params.search = filters.search;
        }
        if (filters?.sprint_id) {
          params.sprint_id = filters.sprint_id;
        }

        const data = await api.get<BoardData>(
          `/api/boards/${boardId}/issues`,
          Object.keys(params).length > 0 ? params : undefined,
        );
        update((s) => ({
          ...s,
          currentBoard: data.board,
          columns: data.columns,
          isLoading: false,
        }));
        return data;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load board data";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return null;
      }
    },

    async loadIssueTypes(projectKey: string) {
      try {
        const types = await api.get<IssueType[]>(
          `/api/projects/${projectKey}/issue-types`,
        );
        update((s) => ({ ...s, issueTypes: types }));
        return types;
      } catch (err) {
        console.error("Failed to load issue types:", err);
        return [];
      }
    },

    async loadStatuses(projectKey: string) {
      try {
        const statuses = await api.get<Status[]>(
          `/api/projects/${projectKey}/statuses`,
        );
        update((s) => ({ ...s, statuses }));
        return statuses;
      } catch (err) {
        console.error("Failed to load statuses:", err);
        return [];
      }
    },

    async loadWorkflow(projectKey: string) {
      try {
        const transitions = await api.get<WorkflowTransition[]>(
          `/api/projects/${projectKey}/workflow`,
        );
        update((s) => ({ ...s, workflowTransitions: transitions }));
        return transitions;
      } catch (err) {
        console.error("Failed to load workflow:", err);
        return [];
      }
    },

    /**
     * Check if transition from one status to another is allowed
     */
    canTransition(fromStatusId: string, toStatusId: string): boolean {
      let transitions: WorkflowTransition[] = [];
      const unsubscribe = subscribe((s) => {
        transitions = s.workflowTransitions;
      });
      unsubscribe();

      // If no transitions defined, allow all
      if (transitions.length === 0) {
        return true;
      }

      return transitions.some(
        (t) =>
          t.from_status.id === fromStatusId && t.to_status.id === toStatusId,
      );
    },

    /**
     * Get all allowed target status IDs from a given status
     */
    getAllowedTargetStatuses(fromStatusId: string): string[] {
      let transitions: WorkflowTransition[] = [];
      const unsubscribe = subscribe((s) => {
        transitions = s.workflowTransitions;
      });
      unsubscribe();

      // If no transitions defined, return empty (allow all in UI)
      if (transitions.length === 0) {
        return [];
      }

      return transitions
        .filter((t) => t.from_status.id === fromStatusId)
        .map((t) => t.to_status.id);
    },

    async updateIssueStatus(issueKey: string, statusId: string) {
      // Optimistic update
      update((s) => {
        const newColumns = s.columns.map((col) => {
          // Find and remove issue from current column
          const issueIndex = col.issues.findIndex((i) => i.key === issueKey);
          if (issueIndex !== -1) {
            const [issue] = col.issues.splice(issueIndex, 1);
            col.count--;

            // Find target column and add issue
            const targetCol = s.columns.find((c) => c.status.id === statusId);
            if (targetCol) {
              issue.status = targetCol.status;
              targetCol.issues.unshift(issue);
              targetCol.count++;
            }
          }
          return col;
        });
        return { ...s, columns: newColumns };
      });

      try {
        await api.patch(`/api/issues/${issueKey}`, { status_id: statusId });
      } catch (err) {
        // Revert on error - reload board
        const state = get(store);
        if (state.currentBoard) {
          await this.loadBoardData(state.currentBoard.id);
        }
        throw err;
      }
    },

    async createIssue(
      projectKey: string,
      data: {
        title: string;
        issue_type_id: string;
        priority?: string;
        description?: string;
        assignee_id?: number;
        due_date?: string;
        status_id?: string;
        epic_id?: string;
        custom_fields?: Record<string, unknown>;
      },
    ) {
      try {
        const issue = await api.post<Issue>(
          `/api/projects/${projectKey}/issues`,
          data,
        );

        // Add to board if current board exists
        update((s) => {
          if (s.currentBoard) {
            const targetCol = s.columns.find(
              (c) => c.status.id === issue.status.id,
            );
            if (targetCol) {
              targetCol.issues.unshift(issue);
              targetCol.count++;
            }
          }
          return s;
        });

        return issue;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to create issue";
        throw new Error(message);
      }
    },

    async updateIssue(
      issueKey: string,
      data: {
        priority?: string;
        assignee_id?: number | null;
        story_points?: number | null;
        title?: string;
        description?: string;
      },
    ) {
      // Optimistic update - create new objects for proper reactivity
      update((s) => {
        const newColumns = s.columns.map((col) => {
          const issueIndex = col.issues.findIndex((i) => i.key === issueKey);
          if (issueIndex === -1) return col;

          // Create new issue object with updates
          const updatedIssue = { ...col.issues[issueIndex] };
          if (data.priority !== undefined) {
            updatedIssue.priority = data.priority as Issue["priority"];
          }
          if (data.story_points !== undefined) {
            updatedIssue.story_points = data.story_points;
          }
          if (data.assignee_id !== undefined) {
            if (data.assignee_id === null) {
              updatedIssue.assignee = null;
            }
            // Note: For assignee, we'd need the full user object
            // The API will return updated issue, so we'll reload if needed
          }

          // Create new issues array with updated issue
          const newIssues = [...col.issues];
          newIssues[issueIndex] = updatedIssue;

          // Return new column object
          return { ...col, issues: newIssues };
        });
        return { ...s, columns: newColumns };
      });

      try {
        const updated = await api.patch(`/api/issues/${issueKey}`, data);
        // Update with server response to get full assignee data
        if (data.assignee_id !== undefined) {
          const state = get(store);
          if (state.currentBoard) {
            await this.loadBoardData(state.currentBoard.id);
          }
        }
        return updated;
      } catch (err) {
        // Revert on error - reload board
        const state = get(store);
        if (state.currentBoard) {
          await this.loadBoardData(state.currentBoard.id);
        }
        throw err;
      }
    },

    async updateIssueStoryPoints(issueKey: string, storyPoints: number | null) {
      // Optimistic update - create new objects for proper reactivity
      update((s) => {
        const newColumns = s.columns.map((col) => {
          const issueIndex = col.issues.findIndex((i) => i.key === issueKey);
          if (issueIndex === -1) return col;

          // Create new issue with updated story points
          const updatedIssue = {
            ...col.issues[issueIndex],
            story_points: storyPoints,
          };
          const newIssues = [...col.issues];
          newIssues[issueIndex] = updatedIssue;

          return { ...col, issues: newIssues };
        });
        return { ...s, columns: newColumns };
      });

      try {
        await api.patch(`/api/issues/${issueKey}`, {
          story_points: storyPoints,
        });
      } catch (err) {
        // Revert on error - reload board
        const state = get(store);
        if (state.currentBoard) {
          await this.loadBoardData(state.currentBoard.id);
        }
        throw err;
      }
    },

    clearError() {
      update((s) => ({ ...s, error: null }));
    },

    reset() {
      set({
        boards: [],
        currentBoard: null,
        columns: [],
        issueTypes: [],
        statuses: [],
        workflowTransitions: [],
        isLoading: false,
        error: null,
      });
    },
  };
}

export const board = createBoardStore();

// Derived stores
export const boardsList = derived(board, ($b) => $b.boards);
export const currentBoard = derived(board, ($b) => $b.currentBoard);
export const boardColumns = derived(board, ($b) => $b.columns);
export const issueTypes = derived(board, ($b) => $b.issueTypes);
export const statuses = derived(board, ($b) => $b.statuses);
export const workflowTransitions = derived(
  board,
  ($b) => $b.workflowTransitions,
);
export const boardLoading = derived(board, ($b) => $b.isLoading);
export const boardError = derived(board, ($b) => $b.error);

// Flat list of all issues from all columns (for list view)
export const flatIssuesList = derived(board, ($b) =>
  $b.columns.flatMap((col) => col.issues),
);
