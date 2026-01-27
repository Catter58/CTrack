/**
 * Tests for the toast notification store
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { get } from "svelte/store";
import { toasts, toastsList } from "./toast";

describe("toast store", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    toasts.dismissAll();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe("success", () => {
    it("should add a success toast", () => {
      toasts.success("Success!", "Operation completed");

      const list = get(toastsList);
      expect(list).toHaveLength(1);
      expect(list[0].kind).toBe("success");
      expect(list[0].title).toBe("Success!");
      expect(list[0].subtitle).toBe("Operation completed");
    });

    it("should auto-remove after timeout", () => {
      toasts.success("Success!");

      vi.advanceTimersByTime(4000);

      expect(get(toastsList)).toHaveLength(0);
    });
  });

  describe("error", () => {
    it("should add an error toast", () => {
      toasts.error("Error!", "Something went wrong");

      const list = get(toastsList);
      expect(list).toHaveLength(1);
      expect(list[0].kind).toBe("error");
      expect(list[0].title).toBe("Error!");
    });

    it("should have longer default timeout (6000ms)", () => {
      toasts.error("Error!");

      vi.advanceTimersByTime(5000);
      expect(get(toastsList)).toHaveLength(1);

      vi.advanceTimersByTime(1000);
      expect(get(toastsList)).toHaveLength(0);
    });
  });

  describe("warning", () => {
    it("should add a warning toast", () => {
      toasts.warning("Warning!", "Be careful");

      const list = get(toastsList);
      expect(list).toHaveLength(1);
      expect(list[0].kind).toBe("warning");
    });
  });

  describe("info", () => {
    it("should add an info toast", () => {
      toasts.info("Info", "Just FYI");

      const list = get(toastsList);
      expect(list).toHaveLength(1);
      expect(list[0].kind).toBe("info");
    });
  });

  describe("dismiss", () => {
    it("should remove a specific toast", () => {
      const id1 = toasts.success("Toast 1");
      toasts.success("Toast 2");

      expect(get(toastsList)).toHaveLength(2);

      toasts.dismiss(id1);

      const list = get(toastsList);
      expect(list).toHaveLength(1);
      expect(list[0].title).toBe("Toast 2");
    });
  });

  describe("dismissAll", () => {
    it("should remove all toasts", () => {
      toasts.success("Toast 1");
      toasts.error("Toast 2");
      toasts.warning("Toast 3");

      expect(get(toastsList)).toHaveLength(3);

      toasts.dismissAll();

      expect(get(toastsList)).toHaveLength(0);
    });
  });

  describe("multiple toasts", () => {
    it("should stack multiple toasts", () => {
      toasts.success("Success");
      toasts.error("Error");
      toasts.warning("Warning");

      const list = get(toastsList);
      expect(list).toHaveLength(3);
      expect(list[0].kind).toBe("success");
      expect(list[1].kind).toBe("error");
      expect(list[2].kind).toBe("warning");
    });

    it("should remove toasts independently by timeout", () => {
      toasts.success("Success", undefined, 1000);
      toasts.error("Error", undefined, 2000);

      vi.advanceTimersByTime(1000);
      expect(get(toastsList)).toHaveLength(1);
      expect(get(toastsList)[0].kind).toBe("error");

      vi.advanceTimersByTime(1000);
      expect(get(toastsList)).toHaveLength(0);
    });
  });

  describe("custom timeout", () => {
    it("should respect custom timeout", () => {
      toasts.success("Quick toast", undefined, 1000);

      vi.advanceTimersByTime(999);
      expect(get(toastsList)).toHaveLength(1);

      vi.advanceTimersByTime(1);
      expect(get(toastsList)).toHaveLength(0);
    });

    it("should not auto-remove with timeout 0", () => {
      toasts.success("Persistent toast", undefined, 0);

      vi.advanceTimersByTime(10000);
      expect(get(toastsList)).toHaveLength(1);
    });
  });

  describe("unique IDs", () => {
    it("should generate unique IDs for each toast", () => {
      const id1 = toasts.success("Toast 1");
      const id2 = toasts.success("Toast 2");

      expect(id1).not.toBe(id2);
    });
  });
});
