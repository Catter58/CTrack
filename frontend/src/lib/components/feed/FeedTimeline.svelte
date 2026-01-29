<script lang="ts">
	import { SkeletonText } from 'carbon-components-svelte';
	import type { FeedItem as FeedItemType } from '$lib/stores/feed';
	import FeedItem from './FeedItem.svelte';

	interface Props {
		items: FeedItemType[];
		isLoading: boolean;
	}

	let { items, isLoading }: Props = $props();

	// Group items by date
	interface DateGroup {
		label: string;
		date: string;
		items: FeedItemType[];
	}

	function formatDateLabel(dateStr: string): string {
		const date = new Date(dateStr);
		const today = new Date();
		const yesterday = new Date(today);
		yesterday.setDate(yesterday.getDate() - 1);

		// Reset times to compare only dates
		const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());
		const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate());
		const yesterdayOnly = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate());

		if (dateOnly.getTime() === todayOnly.getTime()) {
			return 'Сегодня';
		}
		if (dateOnly.getTime() === yesterdayOnly.getTime()) {
			return 'Вчера';
		}

		return date.toLocaleDateString('ru-RU', {
			day: 'numeric',
			month: 'long',
			year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined
		});
	}

	function getDateKey(dateStr: string): string {
		const date = new Date(dateStr);
		return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
	}

	let groupedItems = $derived.by<DateGroup[]>(() => {
		const groups: Map<string, FeedItemType[]> = new Map();

		for (const item of items) {
			const key = getDateKey(item.created_at);
			const existing = groups.get(key);
			if (existing) {
				existing.push(item);
			} else {
				groups.set(key, [item]);
			}
		}

		const result: DateGroup[] = [];
		for (const [dateKey, groupItems] of groups) {
			result.push({
				label: formatDateLabel(groupItems[0].created_at),
				date: dateKey,
				items: groupItems
			});
		}

		return result;
	});
</script>

<div class="feed-timeline">
	{#if isLoading}
		{@const skeletonItems = [0, 1, 2, 3, 4]}
		<div class="skeleton-container">
			{#each skeletonItems as i}
				<div class="skeleton-item" style="--delay: {i * 0.1}s">
					<div class="skeleton-icon">
						<SkeletonText width="32px" />
					</div>
					<div class="skeleton-content">
						<SkeletonText width="60%" />
						<SkeletonText width="80%" />
						<SkeletonText width="40%" />
					</div>
				</div>
			{/each}
		</div>
	{:else if items.length === 0}
		<div class="empty-state">
			<p>Нет активности</p>
			<p class="empty-hint">Попробуйте изменить параметры фильтра</p>
		</div>
	{:else}
		<div class="timeline-line"></div>
		{#each groupedItems as group (group.date)}
			<div class="date-group">
				<div class="date-header">
					<span class="date-label">{group.label}</span>
				</div>
				<div class="group-items">
					{#each group.items as item (item.id)}
						<FeedItem {item} />
					{/each}
				</div>
			</div>
		{/each}
	{/if}
</div>

<style>
	.feed-timeline {
		position: relative;
		padding-left: 1.5rem;
	}

	.timeline-line {
		position: absolute;
		left: 0;
		top: 0;
		bottom: 0;
		width: 2px;
		background: var(--cds-border-subtle);
	}

	.date-group {
		margin-bottom: 1.5rem;
	}

	.date-header {
		position: relative;
		margin-bottom: 1rem;
		padding-left: 1rem;
	}

	.date-header::before {
		content: '';
		position: absolute;
		left: -1.5rem;
		top: 50%;
		transform: translateY(-50%);
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: var(--cds-interactive);
		border: 2px solid var(--cds-background);
	}

	.date-label {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--cds-text-secondary);
		text-transform: capitalize;
	}

	.group-items {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		padding-left: 1rem;
	}

	.skeleton-container {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		padding-left: 1rem;
	}

	.skeleton-item {
		display: flex;
		gap: 0.75rem;
		padding: 1rem;
		background: var(--cds-field);
		border-radius: 6px;
		animation: pulse 1.5s ease-in-out infinite;
		animation-delay: var(--delay);
	}

	@keyframes pulse {
		0%, 100% {
			opacity: 1;
		}
		50% {
			opacity: 0.6;
		}
	}

	.skeleton-icon {
		width: 2rem;
		height: 2rem;
		border-radius: 50%;
		background: var(--cds-layer);
		flex-shrink: 0;
	}

	.skeleton-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		min-height: 200px;
		color: var(--cds-text-secondary);
		padding-left: 1rem;
	}

	.empty-state p {
		margin: 0;
		font-size: 1rem;
	}

	.empty-hint {
		font-size: 0.875rem !important;
		margin-top: 0.5rem !important;
		color: var(--cds-text-helper);
	}
</style>
