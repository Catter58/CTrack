<script lang="ts">
	import { onMount } from 'svelte';
	import { Loading } from 'carbon-components-svelte';
	import { ArrowDown, Renew } from 'carbon-icons-svelte';

	interface Props {
		onRefresh: () => Promise<void>;
		threshold?: number;
		disabled?: boolean;
		children?: import('svelte').Snippet;
	}

	let {
		onRefresh,
		threshold = 80,
		disabled = false,
		children
	}: Props = $props();

	let containerRef: HTMLDivElement | null = $state(null);
	let isTouchDevice = $state(false);

	let startY = $state(0);
	let currentPull = $state(0);
	let isPulling = $state(false);
	let isRefreshing = $state(false);
	let canRefresh = $state(false);

	const maxPull = 120;

	onMount(() => {
		isTouchDevice = 'ontouchstart' in window;
	});

	function triggerHaptic(): void {
		if (navigator.vibrate) {
			navigator.vibrate(10);
		}
	}

	function isAtTop(): boolean {
		if (!containerRef) return false;
		// Check if the container or its scrollable parent is at the top
		let element: HTMLElement | null = containerRef;
		while (element) {
			if (element.scrollTop > 0) {
				return false;
			}
			element = element.parentElement;
		}
		return window.scrollY === 0;
	}

	function handleTouchStart(event: TouchEvent): void {
		if (disabled || isRefreshing || !isTouchDevice) return;

		// Only start if at top of scroll
		if (!isAtTop()) return;

		const touch = event.touches[0];
		startY = touch.clientY;
		isPulling = true;
	}

	function handleTouchMove(event: TouchEvent): void {
		if (!isPulling || disabled || isRefreshing) return;

		const touch = event.touches[0];
		const deltaY = touch.clientY - startY;

		// Only pull down, not up
		if (deltaY <= 0) {
			currentPull = 0;
			canRefresh = false;
			return;
		}

		// Check if we're still at top (prevent pull if user scrolled)
		if (!isAtTop()) {
			isPulling = false;
			currentPull = 0;
			canRefresh = false;
			return;
		}

		// Prevent default scroll when pulling
		event.preventDefault();

		// Apply resistance as pull increases
		const resistance = 1 - Math.min(deltaY / 300, 0.7);
		let pull = deltaY * resistance;

		// Cap at max pull
		if (pull > maxPull) {
			pull = maxPull + (pull - maxPull) * 0.2;
		}

		currentPull = pull;

		// Check if threshold reached
		const wasCanRefresh = canRefresh;
		canRefresh = pull >= threshold;

		// Haptic feedback when crossing threshold
		if (canRefresh && !wasCanRefresh) {
			triggerHaptic();
		}
	}

	async function handleTouchEnd(): Promise<void> {
		if (!isPulling || disabled) return;

		isPulling = false;

		if (canRefresh && !isRefreshing) {
			isRefreshing = true;
			currentPull = threshold; // Hold at threshold during refresh
			triggerHaptic();

			try {
				await onRefresh();
			} finally {
				isRefreshing = false;
				currentPull = 0;
				canRefresh = false;
			}
		} else {
			currentPull = 0;
			canRefresh = false;
		}
	}

	function handleTouchCancel(): void {
		isPulling = false;
		if (!isRefreshing) {
			currentPull = 0;
			canRefresh = false;
		}
	}

	let indicatorStyle = $derived(`transform: translateY(${currentPull - 60}px)`);
	let indicatorTransition = $derived(
		isPulling ? 'transition: none' : 'transition: transform 0.2s ease-out'
	);
	let rotationStyle = $derived(
		`transform: rotate(${Math.min(currentPull / threshold, 1) * 180}deg)`
	);
</script>

<div
	class="pull-to-refresh-container"
	bind:this={containerRef}
	ontouchstart={handleTouchStart}
	ontouchmove={handleTouchMove}
	ontouchend={handleTouchEnd}
	ontouchcancel={handleTouchCancel}
>
	{#if isTouchDevice}
		<div
			class="pull-indicator"
			class:visible={currentPull > 0 || isRefreshing}
			class:can-refresh={canRefresh}
			class:refreshing={isRefreshing}
			style="{indicatorStyle}; {indicatorTransition}"
		>
			{#if isRefreshing}
				<Loading small withOverlay={false} />
				<span class="pull-text">Обновление...</span>
			{:else if canRefresh}
				<Renew size={24} />
				<span class="pull-text">Отпустите для обновления</span>
			{:else}
				<div class="arrow-icon" style={rotationStyle}>
					<ArrowDown size={24} />
				</div>
				<span class="pull-text">Потяните для обновления</span>
			{/if}
		</div>
	{/if}

	<div
		class="pull-content"
		style="transform: translateY({currentPull}px); {isPulling ? '' : 'transition: transform 0.2s ease-out'}"
	>
		{@render children?.()}
	</div>
</div>

<style>
	.pull-to-refresh-container {
		position: relative;
		overflow: visible;
		touch-action: pan-x pan-down;
	}

	.pull-indicator {
		position: absolute;
		top: 0;
		left: 50%;
		transform: translateX(-50%) translateY(-60px);
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		background: var(--cds-layer-02, #393939);
		border-radius: 8px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
		opacity: 0;
		pointer-events: none;
		z-index: 100;
	}

	.pull-indicator.visible {
		opacity: 1;
	}

	.pull-indicator.can-refresh {
		background: var(--cds-support-success, #24a148);
		color: white;
	}

	.pull-indicator.refreshing {
		background: var(--cds-layer-02, #393939);
		color: var(--cds-text-primary, #f4f4f4);
	}

	.pull-text {
		font-size: 0.75rem;
		font-weight: 500;
		white-space: nowrap;
	}

	.arrow-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		transition: transform 0.1s ease-out;
	}

	.pull-content {
		position: relative;
	}

	/* Loading indicator styling */
	.pull-indicator :global(.bx--loading) {
		width: 24px;
		height: 24px;
	}

	.pull-indicator :global(.bx--loading__svg) {
		stroke: currentColor;
	}
</style>
