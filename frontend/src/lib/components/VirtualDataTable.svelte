<script lang="ts" generics="T extends { id: string | number }">
	import type { Snippet } from 'svelte';

	interface Header {
		key: string;
		value: string;
	}

	interface Props {
		headers: Header[];
		rows: T[];
		size?: 'compact' | 'short' | 'medium' | 'tall';
		rowHeight?: number;
		containerHeight?: string;
		threshold?: number;
		cellHeader?: Snippet<[{ header: Header }]>;
		cell?: Snippet<[{ row: T; cell: { key: string; value: unknown } }]>;
		onRowClick?: (row: T) => void;
	}

	let {
		headers,
		rows,
		size = 'short',
		rowHeight,
		containerHeight = '600px',
		threshold = 50,
		cellHeader,
		cell,
		onRowClick
	}: Props = $props();

	// Calculate row height based on size if not explicitly provided
	let effectiveRowHeight = $derived.by(() => {
		if (rowHeight) return rowHeight;
		switch (size) {
			case 'compact':
				return 32;
			case 'short':
				return 40;
			case 'medium':
				return 48;
			case 'tall':
				return 64;
			default:
				return 40;
		}
	});

	let containerRef: HTMLDivElement | null = $state(null);
	let scrollTop = $state(0);
	let viewportHeight = $state(0);

	let useVirtualization = $derived(rows.length >= threshold);
	const overscan = 5;

	let visibleRange = $derived.by(() => {
		if (!useVirtualization) {
			return { start: 0, end: rows.length };
		}

		const startIndex = Math.max(0, Math.floor(scrollTop / effectiveRowHeight) - overscan);
		const visibleCount = Math.ceil(viewportHeight / effectiveRowHeight) + 2 * overscan;
		const endIndex = Math.min(rows.length, startIndex + visibleCount);

		return { start: startIndex, end: endIndex };
	});

	let visibleRows = $derived(rows.slice(visibleRange.start, visibleRange.end));

	let totalHeight = $derived(rows.length * effectiveRowHeight);
	let offsetY = $derived(visibleRange.start * effectiveRowHeight);

	function handleScroll(event: Event) {
		const target = event.target as HTMLDivElement;
		scrollTop = target.scrollTop;
	}

	function handleRowClick(row: T) {
		if (onRowClick) {
			onRowClick(row);
		}
	}

	function getCellValue(row: T, key: string): unknown {
		return (row as Record<string, unknown>)[key];
	}

	$effect(() => {
		if (containerRef) {
			viewportHeight = containerRef.clientHeight;

			const resizeObserver = new ResizeObserver((entries) => {
				for (const entry of entries) {
					viewportHeight = entry.contentRect.height;
				}
			});

			resizeObserver.observe(containerRef);

			return () => {
				resizeObserver.disconnect();
			};
		}
	});
</script>

<div class="bx--data-table-container virtual-data-table">
	<table class="bx--data-table bx--data-table--{size}">
		<thead>
			<tr>
				{#each headers as header (header.key)}
					<th scope="col">
						<span class="bx--table-header-label">
							{#if cellHeader}
								{@render cellHeader({ header })}
							{:else}
								{header.value}
							{/if}
						</span>
					</th>
				{/each}
			</tr>
		</thead>
	</table>

	{#if useVirtualization}
		<div
			bind:this={containerRef}
			class="virtual-tbody-container"
			style:height={containerHeight}
			onscroll={handleScroll}
		>
			<div class="virtual-tbody-spacer" style:height="{totalHeight}px">
				<table class="bx--data-table bx--data-table--{size} virtual-table-body">
					<tbody style:transform="translateY({offsetY}px)">
						{#each visibleRows as row (row.id)}
							<tr
								class:clickable={!!onRowClick}
								onclick={() => handleRowClick(row)}
								style:height="{effectiveRowHeight}px"
							>
								{#each headers as header (header.key)}
									<td>
										{#if cell}
											{@render cell({ row, cell: { key: header.key, value: getCellValue(row, header.key) } })}
										{:else}
											{getCellValue(row, header.key)}
										{/if}
									</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{:else}
		<table class="bx--data-table bx--data-table--{size}">
			<tbody>
				{#each rows as row (row.id)}
					<tr
						class:clickable={!!onRowClick}
						onclick={() => handleRowClick(row)}
					>
						{#each headers as header (header.key)}
							<td>
								{#if cell}
									{@render cell({ row, cell: { key: header.key, value: getCellValue(row, header.key) } })}
								{:else}
									{getCellValue(row, header.key)}
								{/if}
							</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</div>

<style>
	.virtual-data-table {
		width: 100%;
	}

	.virtual-data-table > table {
		width: 100%;
		table-layout: fixed;
	}

	.virtual-tbody-container {
		overflow-y: auto;
		overflow-x: hidden;
	}

	.virtual-tbody-spacer {
		position: relative;
	}

	.virtual-table-body {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		width: 100%;
		table-layout: fixed;
	}

	tr.clickable {
		cursor: pointer;
	}

	tr.clickable:hover {
		background: var(--cds-layer-hover) !important;
	}
</style>
