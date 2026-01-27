/**
 * Tests for the backlog store
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { get } from "svelte/store";

// Mock the API client
vi.mock("$lib/api/client", () => ({
  default: {
    get: vi.fn(),
    patch: vi.fn(),
  },
}));

import {
  backlog,
  backlogIssues,
  backlogCount,
  backlogHasMore,
  backlogStoryPoints,
  type BacklogIssue,
} from "./backlog";
import api from "$lib/api/client";

const mockIssue: BacklogIssue = {
  id: "issue-1",
  key: "TEST-1",
  title: "Test Issue",
  description: null,
  priority: "medium",
  story_points: 5,
  due_date: null,
  epic_id: null,
  issue_type: {
    id: "type-1",
    name: "Task",
    icon: "task",
    color: "#0066cc",
    is_subtask: false,
  },
  status: {
    id: "status-1",
    name: "To Do",
    category: "todo",
    color: "#808080",
  },
  assignee: null,
  reporter: {
    id: 1,
    username: "testuser",
    email: "test@example.com",
    full_name: "Test User",
  },
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

describe("backlog store", () => {
  beforeEach(() => {
    backlog.reset();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("loadBacklog", () => {
    it("should load backlog issues", async () => {
      vi.mocked(api.get).mockResolvedValueOnce([mockIssue]);

      await backlog.loadBacklog("TEST");

      expect(api.get).toHaveBeenCalledWith("/api/projects/TEST/backlog", {
        limit: "20",
      });
      expect(get(backlogIssues)).toHaveLength(1);
      expect(get(backlogIssues)[0].key).toBe("TEST-1");
    });

    it("should set hasMore based on result count", async () => {
      // Less than page size means no more
      vi.mocked(api.get).mockResolvedValueOnce([mockIssue]);

      await backlog.loadBacklog("TEST");

      expect(get(backlogHasMore)).toBe(false);
    });

    it("should handle load error", async () => {
      vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

      const result = await backlog.loadBacklog("TEST");

      expect(result).toEqual([]);
      const state = get(backlog);
      expect(state.error).toBe("Network error");
    });
  });

  describe("loadMore", () => {
    it("should append more issues", async () => {
      // First load
      vi.mocked(api.get).mockResolvedValueOnce(
        Array(20)
          .fill(null)
          .map((_, i) => ({
            ...mockIssue,
            id: `issue-${i}`,
            key: `TEST-${i}`,
          })),
      );
      await backlog.loadBacklog("TEST");

      // Load more
      const moreIssues = Array(5)
        .fill(null)
        .map((_, i) => ({
          ...mockIssue,
          id: `issue-${20 + i}`,
          key: `TEST-${20 + i}`,
        }));
      vi.mocked(api.get).mockResolvedValueOnce(moreIssues);

      await backlog.loadMore();

      expect(get(backlogIssues)).toHaveLength(25);
    });

    it("should not load more if already loading", async () => {
      vi.mocked(api.get).mockResolvedValueOnce([mockIssue]);
      await backlog.loadBacklog("TEST");

      // hasMore is false because we got less than page size
      await backlog.loadMore();

      // Should not have called api.get again
      expect(vi.mocked(api.get).mock.calls.length).toBe(1);
    });
  });

  describe("updateIssueSprint", () => {
    it("should add issue to sprint", async () => {
      vi.mocked(api.get).mockResolvedValueOnce([mockIssue]);
      await backlog.loadBacklog("TEST");

      vi.mocked(api.patch).mockResolvedValueOnce({ ...mockIssue });

      await backlog.updateIssueSprint("TEST-1", "sprint-1");

      expect(api.patch).toHaveBeenCalledWith(
        "/api/issues/TEST-1/sprint?sprint_id=sprint-1",
      );
      // Issue should be removed from backlog
      expect(get(backlogIssues)).toHaveLength(0);
    });

    it("should remove issue from sprint", async () => {
      vi.mocked(api.patch).mockResolvedValueOnce({ ...mockIssue });

      await backlog.updateIssueSprint("TEST-1", null);

      expect(api.patch).toHaveBeenCalledWith("/api/issues/TEST-1/sprint");
    });
  });

  describe("updateIssueStoryPoints", () => {
    it("should optimistically update story points", async () => {
      vi.mocked(api.get).mockResolvedValueOnce([mockIssue]);
      await backlog.loadBacklog("TEST");

      vi.mocked(api.patch).mockResolvedValueOnce({});

      await backlog.updateIssueStoryPoints("TEST-1", 8);

      const issues = get(backlogIssues);
      expect(issues[0].story_points).toBe(8);
    });
  });

  describe("addIssue", () => {
    it("should add issue to the beginning of the list", async () => {
      vi.mocked(api.get).mockResolvedValueOnce([mockIssue]);
      await backlog.loadBacklog("TEST");

      const newIssue = { ...mockIssue, id: "issue-2", key: "TEST-2" };
      backlog.addIssue(newIssue);

      const issues = get(backlogIssues);
      expect(issues).toHaveLength(2);
      expect(issues[0].key).toBe("TEST-2");
    });
  });

  describe("removeIssue", () => {
    it("should remove issue from the list", async () => {
      vi.mocked(api.get).mockResolvedValueOnce([mockIssue]);
      await backlog.loadBacklog("TEST");

      backlog.removeIssue("TEST-1");

      expect(get(backlogIssues)).toHaveLength(0);
    });
  });

  describe("derived stores", () => {
    it("backlogStoryPoints should calculate total", async () => {
      const issues = [
        { ...mockIssue, id: "1", story_points: 5 },
        { ...mockIssue, id: "2", story_points: 3 },
        { ...mockIssue, id: "3", story_points: null },
      ];
      vi.mocked(api.get).mockResolvedValueOnce(issues);
      await backlog.loadBacklog("TEST");

      expect(get(backlogStoryPoints)).toBe(8);
    });

    it("backlogCount should return total count", async () => {
      const issues = [
        { ...mockIssue, id: "1" },
        { ...mockIssue, id: "2" },
      ];
      vi.mocked(api.get).mockResolvedValueOnce(issues);
      await backlog.loadBacklog("TEST");

      expect(get(backlogCount)).toBe(2);
    });
  });

  describe("reset", () => {
    it("should reset store to initial state", async () => {
      vi.mocked(api.get).mockResolvedValueOnce([mockIssue]);
      await backlog.loadBacklog("TEST");

      backlog.reset();

      const state = get(backlog);
      expect(state.issues).toHaveLength(0);
      expect(state.totalCount).toBe(0);
      expect(state.hasMore).toBe(true);
      expect(state.isLoading).toBe(false);
      expect(state.isLoadingMore).toBe(false);
      expect(state.error).toBeNull();
    });
  });
});
