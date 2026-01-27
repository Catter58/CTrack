/**
 * Store for projects management
 */

import { writable, derived } from "svelte/store";
import api from "$lib/api/client";

export interface Project {
  id: string;
  key: string;
  name: string;
  description: string;
  owner_id: number;
  is_archived: boolean;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// API response format
interface ProjectMemberApi {
  user: {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
  };
  role: "admin" | "manager" | "developer" | "viewer";
  joined_at: string;
}

// Frontend format (flattened)
export interface ProjectMember {
  user_id: number;
  username: string;
  email: string;
  full_name: string;
  role: "admin" | "manager" | "developer" | "viewer";
  joined_at: string;
}

interface ProjectsState {
  projects: Project[];
  currentProject: Project | null;
  members: ProjectMember[];
  isLoading: boolean;
  error: string | null;
}

function createProjectsStore() {
  const { subscribe, set, update } = writable<ProjectsState>({
    projects: [],
    currentProject: null,
    members: [],
    isLoading: false,
    error: null,
  });

  return {
    subscribe,

    async loadProjects(includeArchived: boolean = false) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const params = includeArchived
          ? { include_archived: "true" }
          : undefined;
        const projects = await api.get<Project[]>("/api/projects", params);
        update((s) => ({
          ...s,
          projects,
          isLoading: false,
        }));
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load projects";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
      }
    },

    async loadProject(key: string) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const project = await api.get<Project>(`/api/projects/${key}`);
        update((s) => ({
          ...s,
          currentProject: project,
          isLoading: false,
        }));
        return project;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load project";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return null;
      }
    },

    async createProject(data: {
      key: string;
      name: string;
      description?: string;
    }) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const project = await api.post<Project>("/api/projects", data);
        update((s) => ({
          ...s,
          projects: [...s.projects, project],
          isLoading: false,
        }));
        return project;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to create project";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return null;
      }
    },

    async updateProject(
      key: string,
      data: { name?: string; description?: string },
    ) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const project = await api.patch<Project>(`/api/projects/${key}`, data);
        update((s) => ({
          ...s,
          projects: s.projects.map((p) => (p.key === key ? project : p)),
          currentProject:
            s.currentProject?.key === key ? project : s.currentProject,
          isLoading: false,
        }));
        return project;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to update project";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return null;
      }
    },

    async archiveProject(key: string) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        await api.delete(`/api/projects/${key}`);
        update((s) => ({
          ...s,
          projects: s.projects.filter((p) => p.key !== key),
          isLoading: false,
        }));
        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to archive project";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return false;
      }
    },

    async restoreProject(key: string) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const project = await api.patch<Project>(`/api/projects/${key}`, {
          is_archived: false,
        });
        update((s) => ({
          ...s,
          currentProject: project,
          projects: s.projects.map((p) => (p.key === key ? project : p)),
          isLoading: false,
        }));
        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to restore project";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return false;
      }
    },

    async deleteProjectPermanently(key: string) {
      update((s) => ({ ...s, isLoading: true, error: null }));

      try {
        await api.delete(`/api/projects/${key}`, { permanent: true });
        update((s) => ({
          ...s,
          projects: s.projects.filter((p) => p.key !== key),
          currentProject: null,
          isLoading: false,
        }));
        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to delete project";
        update((s) => ({
          ...s,
          isLoading: false,
          error: message,
        }));
        return false;
      }
    },

    async loadMembers(key: string) {
      try {
        const apiMembers = await api.get<ProjectMemberApi[]>(
          `/api/projects/${key}/members`,
        );
        // Transform API response to frontend format
        const members: ProjectMember[] = apiMembers.map((m) => ({
          user_id: m.user.id,
          username: m.user.username,
          email: m.user.email,
          full_name:
            `${m.user.first_name} ${m.user.last_name}`.trim() ||
            m.user.username,
          role: m.role,
          joined_at: m.joined_at,
        }));
        update((s) => ({
          ...s,
          members,
        }));
        return members;
      } catch (err) {
        console.error("Failed to load members:", err);
        return [];
      }
    },

    async addMember(key: string, userId: number, role: string) {
      try {
        const member = await api.post<ProjectMember>(
          `/api/projects/${key}/members`,
          {
            user_id: userId,
            role,
          },
        );
        update((s) => ({
          ...s,
          members: [...s.members, member],
        }));
        return member;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось добавить участника";
        update((s) => ({ ...s, error: message }));
        return null;
      }
    },

    async updateMemberRole(key: string, userId: number, role: string) {
      try {
        const member = await api.patch<ProjectMember>(
          `/api/projects/${key}/members/${userId}`,
          {
            role,
          },
        );
        update((s) => ({
          ...s,
          members: s.members.map((m) => (m.user_id === userId ? member : m)),
        }));
        return member;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось изменить роль";
        update((s) => ({ ...s, error: message }));
        return null;
      }
    },

    async removeMember(key: string, userId: number) {
      try {
        await api.delete(`/api/projects/${key}/members/${userId}`);
        update((s) => ({
          ...s,
          members: s.members.filter((m) => m.user_id !== userId),
        }));
        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Не удалось удалить участника";
        update((s) => ({ ...s, error: message }));
        return false;
      }
    },

    clearError() {
      update((s) => ({ ...s, error: null }));
    },

    reset() {
      set({
        projects: [],
        currentProject: null,
        members: [],
        isLoading: false,
        error: null,
      });
    },
  };
}

export const projects = createProjectsStore();

// Derived stores
export const projectsList = derived(projects, ($p) => $p.projects);
export const currentProject = derived(projects, ($p) => $p.currentProject);
export const projectMembers = derived(projects, ($p) => $p.members);
export const projectsLoading = derived(projects, ($p) => $p.isLoading);
export const projectsError = derived(projects, ($p) => $p.error);
