<script lang="ts">
	import { onMount } from 'svelte';

	interface SwipeAction {
		id: string;
		label: string;
		icon?: typeof import('carbon-icons-svelte').Add;
		color: string;
		backgroundColor: string;
	}

	interface Props {
		leftActions?: SwipeAction[];
		rightActions?: SwipeAction[];
		threshold?: number;
		onAction?: (actionId: string) => void;
		disabled?: boolean;
		children?: import('svelte').Snippet;
	}

	let {
		leftActions = [],
		rightActions = [],
		threshold = 80,
		onAction,
		disabled = false,
		children
	}: Props = $props();

	let containerRef: HTMLDivElement | null = $state(null);
	let contentRef: HTMLDivElement | null = $state(null);
	let isTouchDevice = $state(false);

	let startX = $state(0);
	let startY = $state(0);
	let currentX = $state(0);
	let isDragging = $state(false);
	let isHorizontalSwipe = $state(false);
	let activeAction = $state<string | null>(null);

	const maxSwipe = 120;

	onMount(() => {
		isTouchDevice = 'ontouchstart' in window;
	});

	function triggerHaptic(): void {
		if (navigator.vibrate) {
			navigator.vibrate(10);
		}
	}

	function handleTouchStart(event: TouchEvent): void {
		if (disabled || !isTouchDevice) return;

		const touch = event.touches[0];
		startX = touch.clientX;
		startY = touch.clientY;
		currentX = 0;
		isDragging = true;
		isHorizontalSwipe = false;
		activeAction = null;
	}

	function handleTouchMove(event: TouchEvent): void {
		if (!isDragging || disabled) return;

		const touch = event.touches[0];
		const deltaX = touch.clientX - startX;
		const deltaY = touch.clientY - startY;

		// Determine swipe direction on first significant move
		if (!isHorizontalSwipe && Math.abs(deltaX) < 10 && Math.abs(deltaY) < 10) {
			return;
		}

		if (!isHorizontalSwipe) {
			if (Math.abs(deltaX) > Math.abs(deltaY)) {
				isHorizontalSwipe = true;
			} else {
				isDragging = false;
				return;
			}
		}

		// Prevent vertical scroll during horizontal swipe
		event.preventDefault();

		// Calculate bounded swipe distance
		let newX = deltaX;

		// Only allow swipe if there are actions in that direction
		if (newX > 0 && leftActions.length === 0) {
			newX = 0;
		} else if (newX < 0 && rightActions.length === 0) {
			newX = 0;
		}

		// Apply resistance at the edges
		if (Math.abs(newX) > maxSwipe) {
			const overflow = Math.abs(newX) - maxSwipe;
			const resistance = 1 - overflow / (overflow + 100);
			newX = Math.sign(newX) * (maxSwipe + overflow * resistance * 0.3);
		}

		currentX = newX;

		// Determine active action based on swipe distance
		const absX = Math.abs(currentX);
		if (absX >= threshold) {
			const actions = currentX > 0 ? leftActions : rightActions;
			if (actions.length > 0 && activeAction !== actions[0].id) {
				activeAction = actions[0].id;
				triggerHaptic();
			}
		} else {
			activeAction = null;
		}
	}

	function handleTouchEnd(): void {
		if (!isDragging || disabled) return;

		isDragging = false;
		isHorizontalSwipe = false;

		// Trigger action if threshold reached
		if (activeAction && Math.abs(currentX) >= threshold) {
			triggerHaptic();
			onAction?.(activeAction);
		}

		// Reset position with animation
		currentX = 0;
		activeAction = null;
	}

	function handleTouchCancel(): void {
		isDragging = false;
		isHorizontalSwipe = false;
		currentX = 0;
		activeAction = null;
	}

	let transformStyle = $derived(`transform: translateX(${currentX}px)`);
	let transitionStyle = $derived(isDragging ? 'transition: none' : 'transition: transform 0.2s ease-out');
</script>

{#if isTouchDevice && (leftActions.length > 0 || rightActions.length > 0)}
	<div
		class="swipe-container"
		bind:this={containerRef}
		ontouchstart={handleTouchStart}
		ontouchmove={handleTouchMove}
		ontouchend={handleTouchEnd}
		ontouchcancel={handleTouchCancel}
	>
		<!-- Left actions (revealed on swipe right) -->
		{#if leftActions.length > 0}
			<div class="actions-container actions-left">
				{#each leftActions as action (action.id)}
					<div
						class="action-item"
						class:active={activeAction === action.id}
						style="background-color: {action.backgroundColor}; color: {action.color}"
					>
						{#if action.icon}
							{@const Icon = action.icon}
							<Icon size={20} />
						{/if}
						<span class="action-label">{action.label}</span>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Right actions (revealed on swipe left) -->
		{#if rightActions.length > 0}
			<div class="actions-container actions-right">
				{#each rightActions as action (action.id)}
					<div
						class="action-item"
						class:active={activeAction === action.id}
						style="background-color: {action.backgroundColor}; color: {action.color}"
					>
						{#if action.icon}
							{@const Icon = action.icon}
							<Icon size={20} />
						{/if}
						<span class="action-label">{action.label}</span>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Main content -->
		<div
			class="swipe-content"
			bind:this={contentRef}
			style="{transformStyle}; {transitionStyle}"
		>
			{@render children?.()}
		</div>
	</div>
{:else}
	{@render children?.()}
{/if}

<style>
	.swipe-container {
		position: relative;
		overflow: hidden;
		touch-action: pan-y;
	}

	.actions-container {
		position: absolute;
		top: 0;
		bottom: 0;
		display: flex;
		align-items: stretch;
	}

	.actions-left {
		left: 0;
		justify-content: flex-start;
	}

	.actions-right {
		right: 0;
		justify-content: flex-end;
	}

	.action-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-width: 80px;
		padding: 0.5rem;
		gap: 0.25rem;
		opacity: 0.8;
		transition: opacity 0.15s ease, transform 0.15s ease;
	}

	.action-item.active {
		opacity: 1;
		transform: scale(1.05);
	}

	.action-label {
		font-size: 0.625rem;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.02em;
		white-space: nowrap;
	}

	.swipe-content {
		position: relative;
		background: var(--cds-layer, #262626);
		z-index: 1;
	}
</style>
