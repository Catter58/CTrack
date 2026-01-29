<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Loading, InlineNotification } from 'carbon-components-svelte';
	import {
		feed,
		feedItems,
		feedProjects,
		feedUsers,
		feedFilters,
		feedHasMore,
		feedLoading,
		feedLoadingMore,
		feedError,
		type FeedFilters,
		type FeedAction
	} from '$lib/stores/feed';
	import { FeedFilters as FeedFiltersComponent, FeedTimeline } from '$lib/components/feed';

	// Read filters from URL
	let urlFilters = $derived.by<FeedFilters>(() => {
		const params = $page.url.searchParams;
		const f: FeedFilters = {};

		const userId = params.get('user');
		if (userId !== null) f.user_id = parseInt(userId);

		const projectId = params.get('project');
		if (projectId) f.project_id = projectId;

		const action = params.get('action');
		if (action) f.action = action as FeedAction;

		const dateFrom = params.get('date_from');
		if (dateFrom) f.date_from = dateFrom;

		const dateTo = params.get('date_to');
		if (dateTo) f.date_to = dateTo;

		return f;
	});

	let isInitialized = $state(false);
	let previousUrlSearch = $state<string | null>(null);
	let sentinelElement: HTMLDivElement | null = $state(null);

	onMount(() => {
		// Load reference data and feed
		async function init() {
			await Promise.all([feed.loadProjects(), feed.loadUsers()]);

			// Apply URL filters and load feed
			feed.setFilters(urlFilters);
			previousUrlSearch = window.location.search;

			await feed.loadFeed();
			isInitialized = true;
		}

		init();

		// Cleanup on unmount
		return () => {
			feed.reset();
		};
	});

	// Set up intersection observer when sentinel is available
	$effect(() => {
		if (!sentinelElement || !isInitialized) return;

		const observer = new IntersectionObserver(
			(entries) => {
				const entry = entries[0];
				if (entry.isIntersecting && $feedHasMore && !$feedLoadingMore && !$feedLoading) {
					feed.loadMore();
				}
			},
			{
				rootMargin: '100px'
			}
		);

		observer.observe(sentinelElement);

		return () => {
			observer.disconnect();
		};
	});

	// Reload when URL changes (after initialization)
	$effect(() => {
		const currentSearch = $page.url.search;
		if (isInitialized && previousUrlSearch !== null && currentSearch !== previousUrlSearch) {
			previousUrlSearch = currentSearch;
			feed.setFilters(urlFilters);
			feed.loadFeed();
		}
	});

	function updateUrl(filters: FeedFilters) {
		const url = new URL($page.url);

		// Clear existing params
		url.searchParams.delete('user');
		url.searchParams.delete('project');
		url.searchParams.delete('action');
		url.searchParams.delete('date_from');
		url.searchParams.delete('date_to');

		// Set new params
		if (filters.user_id !== undefined) url.searchParams.set('user', String(filters.user_id));
		if (filters.project_id) url.searchParams.set('project', filters.project_id);
		if (filters.action) url.searchParams.set('action', filters.action);
		if (filters.date_from) url.searchParams.set('date_from', filters.date_from);
		if (filters.date_to) url.searchParams.set('date_to', filters.date_to);

		goto(url.toString(), { replaceState: true, noScroll: true });
	}

	async function handleFilterChange(filters: FeedFilters) {
		feed.setFilters(filters);
		updateUrl(filters);
		await feed.loadFeed(filters);
	}
</script>

<svelte:head>
	<title>Лента активности - CTrack</title>
</svelte:head>

<div class="feed-page">
	<header class="page-header">
		<h1>Лента активности</h1>
	</header>

	<FeedFiltersComponent
		projects={$feedProjects}
		users={$feedUsers}
		filters={$feedFilters}
		onFilterChange={handleFilterChange}
	/>

	{#if $feedError}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={$feedError}
			on:close={() => feed.clearError()}
		/>
	{/if}

	<div class="timeline-container">
		<FeedTimeline items={$feedItems} isLoading={$feedLoading && !isInitialized} />

		{#if $feedHasMore && isInitialized && $feedItems.length > 0}
			<div class="sentinel" bind:this={sentinelElement}>
				{#if $feedLoadingMore}
					<div class="loading-more">
						<Loading small withOverlay={false} />
						<span>Загрузка...</span>
					</div>
				{/if}
			</div>
		{/if}

		{#if !$feedHasMore && $feedItems.length > 0}
			<div class="end-message">
				Это все записи
			</div>
		{/if}
	</div>
</div>

<style>
	.feed-page {
		padding: 1rem 2rem;
		max-width: 900px;
		margin: 0 auto;
	}

	.page-header {
		margin-bottom: 1.5rem;
	}

	.page-header h1 {
		margin: 0;
		font-size: 1.75rem;
		font-weight: 600;
	}

	.timeline-container {
		margin-top: 1.5rem;
	}

	.sentinel {
		min-height: 50px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.loading-more {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--cds-text-secondary);
		padding: 1rem;
	}

	.end-message {
		text-align: center;
		padding: 1rem;
		color: var(--cds-text-secondary);
		font-size: 0.875rem;
	}
</style>
