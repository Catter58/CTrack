<script lang="ts">
	import { Download, Close } from 'carbon-icons-svelte';
	import { pwa, canShowInstallPrompt } from '$lib/stores/pwa';
	import { fade, fly } from 'svelte/transition';

	async function handleInstall() {
		await pwa.install();
	}

	function handleDismiss() {
		pwa.dismiss();
	}
</script>

{#if $canShowInstallPrompt}
	<div
		class="install-banner"
		in:fly={{ y: 100, duration: 300 }}
		out:fade={{ duration: 200 }}
		role="alert"
		aria-live="polite"
	>
		<div class="install-content">
			<Download size={20} />
			<span class="install-text">Установите CTrack для быстрого доступа</span>
		</div>
		<div class="install-actions">
			<button class="install-button primary" onclick={handleInstall}>Установить</button>
			<button
				class="install-button dismiss"
				onclick={handleDismiss}
				aria-label="Закрыть"
				title="Не сейчас"
			>
				<Close size={16} />
			</button>
		</div>
	</div>
{/if}

<style>
	.install-banner {
		position: fixed;
		bottom: 1rem;
		left: 50%;
		transform: translateX(-50%);
		background: var(--cds-layer-01, #262626);
		border: 1px solid var(--cds-border-subtle-01, #393939);
		border-radius: 4px;
		padding: 0.75rem 1rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1.5rem;
		z-index: 9999;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
		max-width: calc(100vw - 2rem);
		width: auto;
	}

	.install-content {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		color: var(--cds-text-primary, #f4f4f4);
	}

	.install-text {
		font-size: 0.875rem;
		white-space: nowrap;
	}

	.install-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.install-button {
		border: none;
		border-radius: 4px;
		cursor: pointer;
		font-size: 0.875rem;
		transition:
			background-color 0.15s,
			opacity 0.15s;
	}

	.install-button.primary {
		padding: 0.5rem 1rem;
		background: var(--cds-button-primary, #0f62fe);
		color: white;
	}

	.install-button.primary:hover {
		background: var(--cds-button-primary-hover, #0353e9);
	}

	.install-button.dismiss {
		padding: 0.375rem;
		background: transparent;
		color: var(--cds-text-secondary, #c6c6c6);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.install-button.dismiss:hover {
		background: var(--cds-layer-hover-01, #353535);
	}

	@media (max-width: 480px) {
		.install-banner {
			left: 1rem;
			right: 1rem;
			transform: none;
			width: auto;
		}

		.install-text {
			white-space: normal;
			font-size: 0.8125rem;
		}
	}
</style>
