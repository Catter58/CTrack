/**
 * Filter storage utility for persisting filters to localStorage
 */

import type { GlobalTasksFilters } from "$lib/stores/globalTasks";
import type { FeedFilters } from "$lib/stores/feed";

export interface BoardFilters {
  assignee_id?: number;
  type_id?: string;
  priority?: string;
  search?: string;
  sprint_id?: string;
}

const STORAGE_PREFIX = "ctrack:filters";

const STORAGE_KEYS = {
  tasks: `${STORAGE_PREFIX}:tasks`,
  feed: `${STORAGE_PREFIX}:feed`,
  board: (projectKey: string) => `${STORAGE_PREFIX}:board:${projectKey}`,
} as const;

function isEmptyFilters(filters: object): boolean {
  return Object.keys(filters).length === 0;
}

function safeGetItem<T>(key: string): T | null {
  if (typeof window === "undefined") return null;

  try {
    const stored = localStorage.getItem(key);
    if (!stored) return null;
    return JSON.parse(stored) as T;
  } catch {
    return null;
  }
}

function safeSetItem(key: string, value: unknown): void {
  if (typeof window === "undefined") return;

  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // localStorage might be full or disabled
  }
}

function safeRemoveItem(key: string): void {
  if (typeof window === "undefined") return;

  try {
    localStorage.removeItem(key);
  } catch {
    // Ignore errors
  }
}

export function saveTasksFilters(filters: GlobalTasksFilters): void {
  if (isEmptyFilters(filters)) {
    safeRemoveItem(STORAGE_KEYS.tasks);
  } else {
    safeSetItem(STORAGE_KEYS.tasks, filters);
  }
}

export function loadTasksFilters(): GlobalTasksFilters | null {
  return safeGetItem<GlobalTasksFilters>(STORAGE_KEYS.tasks);
}

export function clearTasksFilters(): void {
  safeRemoveItem(STORAGE_KEYS.tasks);
}

export function saveFeedFilters(filters: FeedFilters): void {
  if (isEmptyFilters(filters)) {
    safeRemoveItem(STORAGE_KEYS.feed);
  } else {
    safeSetItem(STORAGE_KEYS.feed, filters);
  }
}

export function loadFeedFilters(): FeedFilters | null {
  return safeGetItem<FeedFilters>(STORAGE_KEYS.feed);
}

export function clearFeedFilters(): void {
  safeRemoveItem(STORAGE_KEYS.feed);
}

export function saveBoardFilters(
  projectKey: string,
  filters: BoardFilters,
): void {
  const key = STORAGE_KEYS.board(projectKey);
  if (isEmptyFilters(filters)) {
    safeRemoveItem(key);
  } else {
    safeSetItem(key, filters);
  }
}

export function loadBoardFilters(projectKey: string): BoardFilters | null {
  return safeGetItem<BoardFilters>(STORAGE_KEYS.board(projectKey));
}

export function clearBoardFilters(projectKey: string): void {
  safeRemoveItem(STORAGE_KEYS.board(projectKey));
}

export function hasUrlParams(url: URL): boolean {
  return url.searchParams.toString().length > 0;
}
