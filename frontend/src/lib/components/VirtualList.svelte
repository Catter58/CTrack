<script lang="ts" generics="T">
	import { onMount } from 'svelte';
	import type { Snippet } from 'svelte';

	interface Props {
		items: T[];
		itemHeight: number;
		height?: string;
		overscan?: number;
		threshold?: number;
		children: Snippet<[{ item: T; index: number }]>;
	}

	let {
		items,
		itemHeight,
		height = '100%',
		overscan = 5,
		threshold = 50,
		children
	}: Props = $props();

	let containerRef: HTMLDivElement | null = $state(null);
	let scrollTop = $state(0);
	let containerHeight = $state(0);

	// If items below threshold, render all items without virtualization
	let useVirtualization = $derived(items.length >= threshold);

	// Calculate visible range
	let visibleRange = $derived.by(() => {
		if (!useVirtualization) {
			return { start: 0, end: items.length };
		}

		const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
		const visibleCount = Math.ceil(containerHeight / itemHeight) + 2 * overscan;
		const endIndex = Math.min(items.length, startIndex + visibleCount);

		return { start: startIndex, end: endIndex };
	});

	// Items to render
	let visibleItems = $derived(
		items.slice(visibleRange.start, visibleRange.end).map((item, i) => ({
			item,
			index: visibleRange.start + i
		}))
	);

	// Total height for scrollbar
	let totalHeight = $derived(items.length * itemHeight);

	// Offset for positioning visible items
	let offsetY = $derived(visibleRange.start * itemHeight);

	function handleScroll(event: Event) {
		const target = event.target as HTMLDivElement;
		scrollTop = target.scrollTop;
	}

	onMount(() => {
		if (containerRef) {
			containerHeight = containerRef.clientHeight;

			const resizeObserver = new ResizeObserver((entries) => {
				for (const entry of entries) {
					containerHeight = entry.contentRect.height;
				}
			});

			resizeObserver.observe(containerRef);

			return () => {
				resizeObserver.disconnect();
			};
		}
	});

	// Scroll to specific index
	export function scrollToIndex(index: number, behavior: 'auto' | 'smooth' = 'smooth') {
		if (containerRef && useVirtualization) {
			const targetScrollTop = index * itemHeight;
			containerRef.scrollTo({ top: targetScrollTop, behavior });
		}
	}
</script>

{#if useVirtualization}
	<div
		bind:this={containerRef}
		class="virtual-list-container"
		style:height
		onscroll={handleScroll}
	>
		<div class="virtual-list-inner" style:height="{totalHeight}px">
			<div class="virtual-list-content" style:transform="translateY({offsetY}px)">
				{#each visibleItems as { item, index } (index)}
					<div class="virtual-list-item" style:height="{itemHeight}px">
						{@render children({ item, index })}
					</div>
				{/each}
			</div>
		</div>
	</div>
{:else}
	<div class="virtual-list-container static" style:height>
		{#each items as item, index (index)}
			<div class="virtual-list-item" style:min-height="{itemHeight}px">
				{@render children({ item, index })}
			</div>
		{/each}
	</div>
{/if}

<style>
	.virtual-list-container {
		overflow-y: auto;
		position: relative;
	}

	.virtual-list-container.static {
		overflow-y: visible;
		height: auto !important;
	}

	.virtual-list-inner {
		position: relative;
	}

	.virtual-list-content {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
	}

	.virtual-list-item {
		box-sizing: border-box;
	}
</style>
