<script lang="ts">
	import { ToastNotification } from 'carbon-components-svelte';
	import { toasts, toastsList } from '$lib/stores/toast';
	import { fly } from 'svelte/transition';
</script>

{#if $toastsList.length > 0}
	<div class="toast-container" role="region" aria-label="Notifications">
		{#each $toastsList as toast (toast.id)}
			<div transition:fly={{ y: -20, duration: 200 }}>
				<ToastNotification
					kind={toast.kind}
					title={toast.title}
					subtitle={toast.subtitle}
					timeout={toast.timeout}
					lowContrast
					on:close={() => toasts.dismiss(toast.id)}
				/>
			</div>
		{/each}
	</div>
{/if}

<style>
	.toast-container {
		position: fixed;
		top: 64px;
		right: 1rem;
		z-index: 9000;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		max-width: 400px;
		pointer-events: none;
	}

	.toast-container > :global(*) {
		pointer-events: auto;
	}

	.toast-container :global(.bx--toast-notification) {
		margin-bottom: 0;
		max-width: 100%;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	}
</style>
