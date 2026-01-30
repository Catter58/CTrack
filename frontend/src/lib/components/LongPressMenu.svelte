<script lang="ts">
	import { onMount } from 'svelte';

	interface MenuItem {
		id: string;
		label: string;
		icon?: typeof import('carbon-icons-svelte').Add;
		danger?: boolean;
		disabled?: boolean;
	}

	interface Props {
		items: MenuItem[];
		onSelect?: (itemId: string) => void;
		pressDelay?: number;
		disabled?: boolean;
		children?: import('svelte').Snippet;
	}

	let {
		items = [],
		onSelect,
		pressDelay = 500,
		disabled = false,
		children
	}: Props = $props();

	let isTouchDevice = $state(false);
	let showMenu = $state(false);
	let menuPosition = $state({ x: 0, y: 0 });
	let pressTimer: ReturnType<typeof setTimeout> | null = null;
	let isPressing = $state(false);
	let startX = $state(0);
	let startY = $state(0);

	const movementThreshold = 10;

	onMount(() => {
		isTouchDevice = 'ontouchstart' in window;

		// Close menu on outside click
		function handleOutsideClick(event: MouseEvent | TouchEvent): void {
			if (showMenu) {
				const target = event.target as HTMLElement;
				if (!target.closest('.context-menu')) {
					showMenu = false;
				}
			}
		}

		document.addEventListener('click', handleOutsideClick);
		document.addEventListener('touchstart', handleOutsideClick);

		return () => {
			document.removeEventListener('click', handleOutsideClick);
			document.removeEventListener('touchstart', handleOutsideClick);
			if (pressTimer) {
				clearTimeout(pressTimer);
			}
		};
	});

	function triggerHaptic(): void {
		if (navigator.vibrate) {
			navigator.vibrate(20);
		}
	}

	function handleTouchStart(event: TouchEvent): void {
		if (disabled || !isTouchDevice || items.length === 0) return;

		const touch = event.touches[0];
		startX = touch.clientX;
		startY = touch.clientY;
		isPressing = true;

		pressTimer = setTimeout(() => {
			if (isPressing) {
				triggerHaptic();
				showMenu = true;

				// Position menu near touch point but within viewport
				const viewportWidth = window.innerWidth;
				const viewportHeight = window.innerHeight;
				const menuWidth = 200;
				const menuHeight = items.length * 44 + 16;

				let x = startX;
				let y = startY + 10;

				// Adjust if menu would go off right edge
				if (x + menuWidth > viewportWidth - 16) {
					x = viewportWidth - menuWidth - 16;
				}

				// Adjust if menu would go off bottom edge
				if (y + menuHeight > viewportHeight - 16) {
					y = startY - menuHeight - 10;
				}

				// Ensure menu doesn't go off left or top edges
				x = Math.max(16, x);
				y = Math.max(16, y);

				menuPosition = { x, y };

				// Prevent default to avoid text selection
				event.preventDefault();
			}
		}, pressDelay);
	}

	function handleTouchMove(event: TouchEvent): void {
		if (!isPressing) return;

		const touch = event.touches[0];
		const deltaX = Math.abs(touch.clientX - startX);
		const deltaY = Math.abs(touch.clientY - startY);

		// Cancel long press if finger moved too much
		if (deltaX > movementThreshold || deltaY > movementThreshold) {
			cancelPress();
		}
	}

	function handleTouchEnd(): void {
		cancelPress();
	}

	function cancelPress(): void {
		isPressing = false;
		if (pressTimer) {
			clearTimeout(pressTimer);
			pressTimer = null;
		}
	}

	function handleMenuItemClick(itemId: string, event: MouseEvent | TouchEvent): void {
		event.preventDefault();
		event.stopPropagation();

		const item = items.find((i) => i.id === itemId);
		if (item?.disabled) return;

		triggerHaptic();
		showMenu = false;
		onSelect?.(itemId);
	}

	// Also support right-click on non-touch devices
	function handleContextMenu(event: MouseEvent): void {
		if (disabled || items.length === 0 || isTouchDevice) return;

		event.preventDefault();

		const viewportWidth = window.innerWidth;
		const viewportHeight = window.innerHeight;
		const menuWidth = 200;
		const menuHeight = items.length * 44 + 16;

		let x = event.clientX;
		let y = event.clientY;

		if (x + menuWidth > viewportWidth - 16) {
			x = viewportWidth - menuWidth - 16;
		}
		if (y + menuHeight > viewportHeight - 16) {
			y = event.clientY - menuHeight;
		}

		x = Math.max(16, x);
		y = Math.max(16, y);

		menuPosition = { x, y };
		showMenu = true;
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="long-press-container"
	ontouchstart={handleTouchStart}
	ontouchmove={handleTouchMove}
	ontouchend={handleTouchEnd}
	ontouchcancel={handleTouchEnd}
	oncontextmenu={handleContextMenu}
>
	{@render children?.()}
</div>

{#if showMenu}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div
		class="context-menu"
		style="left: {menuPosition.x}px; top: {menuPosition.y}px"
		onclick={(e) => e.stopPropagation()}
		ontouchstart={(e) => e.stopPropagation()}
	>
		{#each items as item (item.id)}
			<button
				class="menu-item"
				class:danger={item.danger}
				class:disabled={item.disabled}
				onclick={(e) => handleMenuItemClick(item.id, e)}
				ontouchend={(e) => handleMenuItemClick(item.id, e)}
				disabled={item.disabled}
			>
				{#if item.icon}
					{@const Icon = item.icon}
					<Icon size={16} />
				{/if}
				<span>{item.label}</span>
			</button>
		{/each}
	</div>
{/if}

<style>
	.long-press-container {
		user-select: none;
		-webkit-user-select: none;
		-webkit-touch-callout: none;
	}

	.context-menu {
		position: fixed;
		z-index: 10001;
		min-width: 180px;
		background: var(--cds-layer-02, #393939);
		border: 1px solid var(--cds-border-strong-01, #525252);
		border-radius: 6px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
		padding: 0.5rem 0;
		animation: menu-fade-in 0.15s ease-out;
	}

	@keyframes menu-fade-in {
		from {
			opacity: 0;
			transform: scale(0.95);
		}
		to {
			opacity: 1;
			transform: scale(1);
		}
	}

	.menu-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
		padding: 0.75rem 1rem;
		border: none;
		background: none;
		color: var(--cds-text-primary, #f4f4f4);
		font-size: 0.875rem;
		text-align: left;
		cursor: pointer;
		transition: background-color 0.1s ease;
	}

	.menu-item:hover,
	.menu-item:active {
		background: var(--cds-layer-hover, #4c4c4c);
	}

	.menu-item.danger {
		color: var(--cds-support-error, #da1e28);
	}

	.menu-item.danger:hover {
		background: rgba(218, 30, 40, 0.2);
	}

	.menu-item.disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.menu-item.disabled:hover {
		background: none;
	}

	.menu-item :global(svg) {
		flex-shrink: 0;
	}
</style>
