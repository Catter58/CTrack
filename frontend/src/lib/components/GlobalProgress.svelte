<script lang="ts">
	import { progressItems, globalPercent } from '$lib/stores/progress';
	import { fade } from 'svelte/transition';

	const hasProgress = $derived($progressItems.length > 0);
	const hasError = $derived($progressItems.some((item) => item.isError));
	const isIndeterminate = $derived($globalPercent === null);
	const currentPercent = $derived($globalPercent ?? 0);
</script>

{#if hasProgress}
	<div
		class="global-progress"
		class:error={hasError}
		class:indeterminate={isIndeterminate}
		role="progressbar"
		aria-valuemin={0}
		aria-valuemax={100}
		aria-valuenow={isIndeterminate ? undefined : currentPercent}
		aria-label="Операция выполняется"
		transition:fade={{ duration: 200 }}
	>
		{#if isIndeterminate}
			<div class="progress-bar indeterminate"></div>
		{:else}
			<div class="progress-bar determinate" style="width: {currentPercent}%"></div>
		{/if}
	</div>
{/if}

<style>
	.global-progress {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		height: 3px;
		z-index: 10000;
		background: var(--cds-layer-01, #262626);
		overflow: hidden;
	}

	.progress-bar {
		height: 100%;
		background: var(--cds-interactive, #0f62fe);
		transition: width 0.2s ease-out;
	}

	.progress-bar.indeterminate {
		width: 30%;
		animation: indeterminate 1.5s ease-in-out infinite;
	}

	.global-progress.error .progress-bar {
		background: var(--cds-support-error, #da1e28);
	}

	@keyframes indeterminate {
		0% {
			transform: translateX(-100%);
		}
		100% {
			transform: translateX(400%);
		}
	}
</style>
