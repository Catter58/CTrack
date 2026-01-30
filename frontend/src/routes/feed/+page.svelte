<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { Loading, InlineNotification, Button } from 'carbon-components-svelte';
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
		type FeedAction,
		type FeedItem
	} from '$lib/stores/feed';
	import { events, type SSEEvent, type ActivityFeedEventData } from '$lib/stores/events';
	import { FeedFilters as FeedFiltersComponent, FeedTimeline } from '$lib/components/feed';
	import {
		saveFeedFilters,
		loadFeedFilters,
		hasUrlParams
	} from '$lib/utils/filterStorage';
	import PullToRefresh from '$lib/components/PullToRefresh.svelte';

	// Read filters from URL
	let urlFilters = $derived.by<FeedFilters>(() => {
		const params = page.url.searchParams;
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
	let timelineContainer: HTMLDivElement | null = $state(null);

	// Real-time updates state
	let newEventsCount = $state(0);
	let newItemIds = $state<Set<string>>(new Set());
	let isUserScrolledDown = $state(false);

	const SCROLL_THRESHOLD = 100;

	function checkScrollPosition(): void {
		if (!timelineContainer) return;
		isUserScrolledDown = window.scrollY > SCROLL_THRESHOLD;
	}

	function scrollToTop(): void {
		window.scrollTo({ top: 0, behavior: 'smooth' });
		newEventsCount = 0;
	}

	function handleActivityEvent(event: SSEEvent): void {
		if (!isInitialized) return;

		const activityData = event.data as unknown as ActivityFeedEventData;
		if (!activityData) return;

		// Convert SSE event data to FeedItem format
		const feedItem: FeedItem = {
			id: activityData.id,
			action: activityData.action as FeedAction,
			created_at: activityData.created_at,
			user: {
				id: activityData.user.id,
				username: activityData.user.username,
				full_name: activityData.user.full_name
			},
			issue: {
				id: activityData.id,
				key: activityData.issue.key,
				title: activityData.issue.title,
				project: {
					id: '',
					key: activityData.issue.project.key,
					name: activityData.issue.project.name
				}
			},
			old_value: activityData.old_value,
			new_value: activityData.new_value,
			comment_preview: null
		};

		// Try to prepend the item (will return null if filtered out or duplicate)
		const addedId = feed.prependItem(feedItem);

		if (addedId) {
			// Mark as new for animation
			newItemIds = new Set([...newItemIds, addedId]);

			// Clear "new" status after animation completes
			setTimeout(() => {
				newItemIds = new Set([...newItemIds].filter((id) => id !== addedId));
			}, 2000);

			// If user is scrolled down, increment counter
			if (isUserScrolledDown) {
				newEventsCount += 1;
			}
		}
	}

	onMount(() => {
		// Set up scroll listener
		window.addEventListener('scroll', checkScrollPosition);

		// Load reference data and feed
		async function init(): Promise<void> {
			await Promise.all([feed.loadProjects(), feed.loadUsers()]);

			// Determine initial filters: URL params take precedence, then localStorage
			let initialFilters: FeedFilters;
			if (hasUrlParams(page.url)) {
				initialFilters = urlFilters;
			} else {
				const savedFilters = loadFeedFilters();
				if (savedFilters) {
					initialFilters = savedFilters;
					updateUrl(savedFilters);
				} else {
					initialFilters = urlFilters;
				}
			}

			feed.setFilters(initialFilters);
			previousUrlSearch = window.location.search;

			await feed.loadFeed();
			isInitialized = true;

			// Connect to SSE and subscribe to activity events
			events.connect();
		}

		init();

		// Subscribe to activity.created events
		const unsubscribeActivity = events.on('activity.created', handleActivityEvent);

		// Cleanup on unmount
		return () => {
			window.removeEventListener('scroll', checkScrollPosition);
			unsubscribeActivity();
			events.disconnect();
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
		const currentSearch = page.url.search;
		if (isInitialized && previousUrlSearch !== null && currentSearch !== previousUrlSearch) {
			previousUrlSearch = currentSearch;
			feed.setFilters(urlFilters);
			feed.loadFeed();
			// Reset new events counter when filters change
			newEventsCount = 0;
		}
	});

	function updateUrl(filters: FeedFilters): void {
		const url = new URL(page.url);

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

	async function handleFilterChange(filters: FeedFilters): Promise<void> {
		feed.setFilters(filters);
		updateUrl(filters);
		saveFeedFilters(filters);
		newEventsCount = 0;
		await feed.loadFeed(filters);
	}

	async function handleRefresh(): Promise<void> {
		newEventsCount = 0;
		await feed.loadFeed();
	}
</script>

<svelte:head>
	<title>Лента активности - CTrack</title>
</svelte:head>

<PullToRefresh onRefresh={handleRefresh}>
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

	{#if newEventsCount > 0}
		<div class="new-events-banner">
			<Button kind="ghost" size="small" on:click={scrollToTop}>
				{newEventsCount} {newEventsCount === 1 ? 'новое событие' : newEventsCount < 5 ? 'новых события' : 'новых событий'}
			</Button>
		</div>
	{/if}

	<div class="timeline-container" bind:this={timelineContainer}>
		<FeedTimeline items={$feedItems} isLoading={$feedLoading && !isInitialized} {newItemIds} />

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
</PullToRefresh>

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

	.new-events-banner {
		position: sticky;
		top: 0;
		z-index: 100;
		display: flex;
		justify-content: center;
		padding: 0.5rem;
		background: var(--cds-layer);
		border-bottom: 1px solid var(--cds-border-subtle);
		animation: slideDown 0.3s ease-out;
	}

	@keyframes slideDown {
		from {
			transform: translateY(-100%);
			opacity: 0;
		}
		to {
			transform: translateY(0);
			opacity: 1;
		}
	}
</style>
