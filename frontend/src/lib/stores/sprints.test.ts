/**
 * Tests for the sprints store
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { get } from "svelte/store";

// Mock the API client
vi.mock("$lib/api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { sprints, type Sprint, type SprintWithStats } from "./sprints";
import api from "$lib/api/client";

const mockSprint: Sprint = {
  id: "sprint-1",
  project_id: "test-project",
  name: "Sprint 1",
  goal: "Complete MVP",
  start_date: "2024-01-01",
  end_date: "2024-01-14",
  status: "planned",
  initial_story_points: null,
  completed_story_points: null,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

const mockSprintWithStats: SprintWithStats = {
  ...mockSprint,
  total_story_points: 20,
  remaining_story_points: 20,
  total_issues: 5,
  completed_issues: 0,
  remaining_issues: 5,
};

describe("sprints store", () => {
  beforeEach(() => {
    sprints.reset();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("loadSprints", () => {
    it("should load sprints for a project", async () => {
      vi.mocked(api.get).mockResolvedValueOnce([mockSprint]);

      await sprints.loadSprints("TEST");

      expect(api.get).toHaveBeenCalledWith(
        "/api/projects/TEST/sprints",
        undefined,
      );
      const state = get(sprints);
      expect(state.sprints).toHaveLength(1);
      expect(state.sprints[0].name).toBe("Sprint 1");
    });

    it("should handle load error", async () => {
      vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

      await sprints.loadSprints("TEST");

      const state = get(sprints);
      expect(state.error).toBe("Network error");
    });
  });

  describe("loadSprint", () => {
    it("should load a single sprint with stats", async () => {
      vi.mocked(api.get).mockResolvedValueOnce(mockSprintWithStats);

      const result = await sprints.loadSprint("sprint-1");

      expect(api.get).toHaveBeenCalledWith("/api/sprints/sprint-1");
      expect(result).toEqual(mockSprintWithStats);
    });

    it("should return null on error", async () => {
      vi.mocked(api.get).mockRejectedValueOnce(new Error("Not found"));

      const result = await sprints.loadSprint("invalid-id");

      expect(result).toBeNull();
    });
  });

  describe("createSprint", () => {
    it("should create a new sprint", async () => {
      const newSprintData = {
        name: "Sprint 2",
        goal: "New features",
        start_date: "2024-01-15",
        end_date: "2024-01-28",
      };

      vi.mocked(api.post).mockResolvedValueOnce({
        ...mockSprint,
        id: "sprint-2",
        ...newSprintData,
      });

      const result = await sprints.createSprint("TEST", newSprintData);

      expect(api.post).toHaveBeenCalledWith(
        "/api/projects/TEST/sprints",
        newSprintData,
      );
      expect(result?.name).toBe("Sprint 2");
    });

    it("should add new sprint to the list", async () => {
      const existingSprints = [mockSprint];
      vi.mocked(api.get).mockResolvedValueOnce(existingSprints);
      await sprints.loadSprints("TEST");

      const newSprint = { ...mockSprint, id: "sprint-2", name: "Sprint 2" };
      vi.mocked(api.post).mockResolvedValueOnce(newSprint);

      await sprints.createSprint("TEST", {
        name: "Sprint 2",
        start_date: "2024-01-15",
        end_date: "2024-01-28",
      });

      const state = get(sprints);
      expect(state.sprints).toHaveLength(2);
    });
  });

  describe("startSprint", () => {
    it("should start a planned sprint", async () => {
      vi.mocked(api.get).mockResolvedValueOnce([mockSprint]);
      await sprints.loadSprints("TEST");

      const activeSprint = { ...mockSprint, status: "active" };
      vi.mocked(api.post).mockResolvedValueOnce(activeSprint);

      const result = await sprints.startSprint("sprint-1");

      expect(api.post).toHaveBeenCalledWith("/api/sprints/sprint-1/start");
      expect(result?.status).toBe("active");
    });

    it("should update sprint status in store", async () => {
      vi.mocked(api.get).mockResolvedValueOnce([mockSprint]);
      await sprints.loadSprints("TEST");

      vi.mocked(api.post).mockResolvedValueOnce({
        ...mockSprint,
        status: "active",
      });
      await sprints.startSprint("sprint-1");

      const state = get(sprints);
      expect(state.sprints[0].status).toBe("active");
    });
  });

  describe("completeSprint", () => {
    it("should complete an active sprint", async () => {
      const activeSprint = { ...mockSprint, status: "active" };
      vi.mocked(api.get).mockResolvedValueOnce([activeSprint]);
      await sprints.loadSprints("TEST");

      const completedSprint = { ...activeSprint, status: "completed" };
      vi.mocked(api.post).mockResolvedValueOnce(completedSprint);

      const result = await sprints.completeSprint("sprint-1", "backlog");

      expect(api.post).toHaveBeenCalledWith("/api/sprints/sprint-1/complete", {
        move_incomplete_to: "backlog",
      });
      expect(result?.status).toBe("completed");
    });

    it("should move incomplete issues to next sprint", async () => {
      const activeSprint = { ...mockSprint, status: "active" };
      vi.mocked(api.get).mockResolvedValueOnce([activeSprint]);
      await sprints.loadSprints("TEST");

      vi.mocked(api.post).mockResolvedValueOnce({
        ...activeSprint,
        status: "completed",
      });
      await sprints.completeSprint("sprint-1", "sprint-2");

      expect(api.post).toHaveBeenCalledWith("/api/sprints/sprint-1/complete", {
        move_incomplete_to: "sprint-2",
      });
    });
  });

  describe("deleteSprint", () => {
    it("should delete a sprint", async () => {
      vi.mocked(api.get).mockResolvedValueOnce([mockSprint]);
      await sprints.loadSprints("TEST");

      vi.mocked(api.delete).mockResolvedValueOnce({ success: true });

      const result = await sprints.deleteSprint("sprint-1");

      expect(api.delete).toHaveBeenCalledWith("/api/sprints/sprint-1");
      expect(result).toBe(true);
    });

    it("should remove sprint from store", async () => {
      vi.mocked(api.get).mockResolvedValueOnce([mockSprint]);
      await sprints.loadSprints("TEST");

      vi.mocked(api.delete).mockResolvedValueOnce({ success: true });
      await sprints.deleteSprint("sprint-1");

      const state = get(sprints);
      expect(state.sprints).toHaveLength(0);
    });
  });

  describe("reset", () => {
    it("should reset the store to initial state", async () => {
      vi.mocked(api.get).mockResolvedValueOnce([mockSprint]);
      await sprints.loadSprints("TEST");

      sprints.reset();

      const state = get(sprints);
      expect(state.sprints).toHaveLength(0);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });
  });
});
