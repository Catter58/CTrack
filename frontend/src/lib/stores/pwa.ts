/**
 * PWA install state management store
 */

import { writable, derived, get } from "svelte/store";
import { browser } from "$app/environment";

const STORAGE_KEY = "ctrack_pwa_dismissed";
const DISMISS_DURATION_DAYS = 30;

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

interface PWAState {
  deferredPrompt: BeforeInstallPromptEvent | null;
  isInstallable: boolean;
  isDismissed: boolean;
  isInstalled: boolean;
}

function isDismissedRecently(): boolean {
  if (!browser) return false;
  try {
    const dismissedAt = localStorage.getItem(STORAGE_KEY);
    if (!dismissedAt) return false;

    const dismissDate = new Date(dismissedAt);
    const now = new Date();
    const daysSinceDismiss =
      (now.getTime() - dismissDate.getTime()) / (1000 * 60 * 60 * 24);

    return daysSinceDismiss < DISMISS_DURATION_DAYS;
  } catch {
    return false;
  }
}

function saveDismissed(): void {
  if (!browser) return;
  localStorage.setItem(STORAGE_KEY, new Date().toISOString());
}

function clearDismissed(): void {
  if (!browser) return;
  localStorage.removeItem(STORAGE_KEY);
}

function createPWAStore() {
  const { subscribe, update } = writable<PWAState>({
    deferredPrompt: null,
    isInstallable: false,
    isDismissed: isDismissedRecently(),
    isInstalled: false,
  });

  return {
    subscribe,

    /**
     * Initialize PWA event listeners (call in layout onMount)
     */
    init(): () => void {
      if (!browser) return () => {};

      // Check if already installed as PWA
      const isStandalone =
        window.matchMedia("(display-mode: standalone)").matches ||
        (window.navigator as Navigator & { standalone?: boolean })
          .standalone === true;

      if (isStandalone) {
        update((s) => ({ ...s, isInstalled: true }));
        return () => {};
      }

      const handleBeforeInstall = (e: Event) => {
        e.preventDefault();
        const prompt = e as BeforeInstallPromptEvent;
        update((s) => ({
          ...s,
          deferredPrompt: prompt,
          isInstallable: true,
        }));
      };

      const handleAppInstalled = () => {
        update((s) => ({
          ...s,
          deferredPrompt: null,
          isInstallable: false,
          isInstalled: true,
        }));
        clearDismissed();
      };

      window.addEventListener("beforeinstallprompt", handleBeforeInstall);
      window.addEventListener("appinstalled", handleAppInstalled);

      return () => {
        window.removeEventListener("beforeinstallprompt", handleBeforeInstall);
        window.removeEventListener("appinstalled", handleAppInstalled);
      };
    },

    /**
     * Trigger the install prompt
     */
    async install(): Promise<boolean> {
      const state = get({ subscribe });
      const prompt = state.deferredPrompt;

      if (!prompt) return false;

      await prompt.prompt();
      const { outcome } = await prompt.userChoice;

      if (outcome === "accepted") {
        update((s) => ({
          ...s,
          deferredPrompt: null,
          isInstallable: false,
        }));
        return true;
      }

      return false;
    },

    /**
     * Dismiss the install prompt (remembers for DISMISS_DURATION_DAYS days)
     */
    dismiss(): void {
      saveDismissed();
      update((s) => ({ ...s, isDismissed: true }));
    },

    /**
     * Reset dismissed state (for testing or settings)
     */
    resetDismissed(): void {
      clearDismissed();
      update((s) => ({ ...s, isDismissed: false }));
    },
  };
}

export const pwa = createPWAStore();

// Derived stores for convenience
export const canShowInstallPrompt = derived(
  pwa,
  ($pwa) => $pwa.isInstallable && !$pwa.isDismissed && !$pwa.isInstalled,
);
export const isInstalled = derived(pwa, ($pwa) => $pwa.isInstalled);
