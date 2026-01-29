<script lang="ts">
  let deferredPrompt: BeforeInstallPromptEvent | null = $state(null);
  let showPrompt = $state(false);

  interface BeforeInstallPromptEvent extends Event {
    prompt(): Promise<void>;
    userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
  }

  $effect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      deferredPrompt = e as BeforeInstallPromptEvent;
      showPrompt = true;
    };

    window.addEventListener('beforeinstallprompt', handler);

    return () => window.removeEventListener('beforeinstallprompt', handler);
  });

  async function install() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      showPrompt = false;
    }
    deferredPrompt = null;
  }
</script>

{#if showPrompt}
  <div class="install-prompt">
    <span>Установить CTrack?</span>
    <button onclick={install}>Установить</button>
    <button onclick={() => (showPrompt = false)}>Не сейчас</button>
  </div>
{/if}

<style>
  .install-prompt {
    position: fixed;
    bottom: 1rem;
    left: 50%;
    transform: translateX(-50%);
    background: var(--cds-layer-01, #262626);
    border: 1px solid var(--cds-border-subtle-01, #393939);
    border-radius: 4px;
    padding: 1rem 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    z-index: 9999;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
  }

  .install-prompt span {
    color: var(--cds-text-primary, #f4f4f4);
    font-size: 0.875rem;
  }

  .install-prompt button {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    transition: background-color 0.15s;
  }

  .install-prompt button:first-of-type {
    background: var(--cds-button-primary, #0f62fe);
    color: white;
  }

  .install-prompt button:first-of-type:hover {
    background: var(--cds-button-primary-hover, #0353e9);
  }

  .install-prompt button:last-of-type {
    background: transparent;
    color: var(--cds-text-secondary, #c6c6c6);
  }

  .install-prompt button:last-of-type:hover {
    background: var(--cds-layer-hover-01, #353535);
  }
</style>
