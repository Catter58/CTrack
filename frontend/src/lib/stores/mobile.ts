/**
 * Mobile viewport detection store
 * Uses Carbon Design System breakpoints
 */

import { writable, derived } from "svelte/store";
import { browser } from "$app/environment";

// Carbon breakpoints (in px)
export const BREAKPOINTS = {
  sm: 320,
  md: 672,
  lg: 1056,
  xlg: 1312,
  max: 1584,
} as const;

// Mobile threshold - matches common tablet/mobile breakpoint
const MOBILE_BREAKPOINT = 768;

interface ViewportState {
  width: number;
  height: number;
}

function createViewportStore() {
  const initial: ViewportState = {
    width: browser ? window.innerWidth : 1024,
    height: browser ? window.innerHeight : 768,
  };

  const { subscribe, set } = writable<ViewportState>(initial);

  if (browser) {
    const handleResize = () => {
      set({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    window.addEventListener("resize", handleResize);
  }

  return { subscribe };
}

export const viewport = createViewportStore();

// Derived stores for common breakpoint checks
export const isMobile = derived(
  viewport,
  ($viewport) => $viewport.width < MOBILE_BREAKPOINT,
);
export const isTablet = derived(
  viewport,
  ($viewport) =>
    $viewport.width >= MOBILE_BREAKPOINT && $viewport.width < BREAKPOINTS.lg,
);
export const isDesktop = derived(
  viewport,
  ($viewport) => $viewport.width >= BREAKPOINTS.lg,
);

// Sidebar state management
interface SidebarState {
  isOpen: boolean;
}

function createSidebarStore() {
  const { subscribe, update } = writable<SidebarState>({
    isOpen: false,
  });

  return {
    subscribe,
    open: () => update((s) => ({ ...s, isOpen: true })),
    close: () => update((s) => ({ ...s, isOpen: false })),
    toggle: () => update((s) => ({ ...s, isOpen: !s.isOpen })),
  };
}

export const sidebar = createSidebarStore();
export const sidebarIsOpen = derived(sidebar, ($sidebar) => $sidebar.isOpen);
