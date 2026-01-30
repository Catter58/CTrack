<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import {
		Search as SearchIcon,
		Document,
		Folder,
		ChevronLeft,
		ChevronRight
	} from 'carbon-icons-svelte';
	import { Loading, Tag, Tile } from 'carbon-components-svelte';
	import api from '$lib/api/client';
	import VirtualList from '$lib/components/VirtualList.svelte';
	import type { GlobalSearchResults, SearchIssue, SearchProject } from '$lib/stores/search';

	// Virtualization threshold
	const VIRTUALIZATION_THRESHOLD = 50;

	// Extended search results with pagination
	interface FullSearchResults {
		query: string;
		issues: SearchIssue[];
		projects: SearchProject[];
		total_issues: number;
		total_projects: number;
	}

	let query = $state('');
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let results = $state<FullSearchResults | null>(null);

	// Pagination state (used when not virtualizing)
	let currentPage = $state(1);
	let pageSize = $state(20);

	// Whether to use virtualization
	let useVirtualization = $derived(
		results !== null && results.total_issues >= VIRTUALIZATION_THRESHOLD
	);

	// Initialize from URL params
	onMount(() => {
		const urlQuery = page.url.searchParams.get('q');
		if (urlQuery) {
			query = urlQuery;
			performSearch();
		}
	});

	// Update URL when query changes
	$effect(() => {
		if (query) {
			const url = new URL(window.location.href);
			url.searchParams.set('q', query);
			window.history.replaceState({}, '', url.toString());
		}
	});

	async function performSearch(): Promise<void> {
		if (!query.trim()) {
			results = null;
			return;
		}

		isLoading = true;
		error = null;

		try {
			const data = await api.get<GlobalSearchResults>('/api/search', {
				q: query,
				limit: '100'
			});

			results = {
				...data,
				total_issues: data.issues.length,
				total_projects: data.projects.length
			};
		} catch (err) {
			error = err instanceof Error ? err.message : 'Ошибка поиска';
			results = null;
		} finally {
			isLoading = false;
		}
	}

	function handleSubmit(e: Event): void {
		e.preventDefault();
		currentPage = 1;
		performSearch();
	}

	function handleInputChange(e: Event): void {
		query = (e.target as HTMLInputElement).value;
	}

	function navigateToIssue(issue: SearchIssue): void {
		goto(`/issues/${issue.key}`);
	}

	function navigateToProject(project: SearchProject): void {
		goto(`/projects/${project.key}/board`);
	}

	// Paginated results (used when not virtualizing)
	let paginatedIssues = $derived.by(() => {
		if (!results || useVirtualization) return [];
		const start = (currentPage - 1) * pageSize;
		return results.issues.slice(start, start + pageSize);
	});

	let totalPages = $derived.by(() => {
		if (!results || useVirtualization) return 0;
		return Math.ceil(results.total_issues / pageSize);
	});
</script>

<svelte:head>
	<title>Поиск{query ? `: ${query}` : ''} - CTrack</title>
</svelte:head>

<div class="search-page">
	<header class="search-header">
		<h1>Поиск</h1>
		<form class="search-form" onsubmit={handleSubmit}>
			<div class="search-input-wrapper">
				<SearchIcon size={24} class="search-icon" />
				<input
					type="text"
					class="search-input"
					placeholder="Поиск задач и проектов..."
					value={query}
					oninput={handleInputChange}
				/>
				{#if isLoading}
					<div class="search-loading">
						<Loading withOverlay={false} small />
					</div>
				{/if}
			</div>
			<button type="submit" class="search-button">Найти</button>
		</form>
	</header>

	<main class="search-content">
		{#if error}
			<Tile class="error-tile">
				<p class="error-message">{error}</p>
			</Tile>
		{:else if isLoading}
			<div class="loading-state">
				<Loading withOverlay={false} />
				<p>Поиск...</p>
			</div>
		{:else if results}
			<div class="results-summary">
				<span>Найдено: {results.total_issues} задач, {results.total_projects} проектов</span>
			</div>

			{#if results.projects.length > 0}
				<section class="results-section">
					<h2 class="section-title">
						<Folder size={20} />
						Проекты ({results.projects.length})
					</h2>
					<div class="projects-grid">
						{#each results.projects as project (project.id)}
							<button
								class="project-card"
								onclick={() => navigateToProject(project)}
							>
								<div class="project-key">{project.key}</div>
								<div class="project-name">{project.name}</div>
							</button>
						{/each}
					</div>
				</section>
			{/if}

			{#if results.issues.length > 0}
				<section class="results-section">
					<h2 class="section-title">
						<Document size={20} />
						Задачи ({results.total_issues})
					</h2>

					{#if useVirtualization}
						<div class="issues-list-virtual">
							<VirtualList
								items={results.issues}
								itemHeight={56}
								height="calc(100vh - 400px)"
								threshold={1}
							>
								{#snippet children({ item: issue })}
									<button
										class="issue-card"
										onclick={() => navigateToIssue(issue)}
									>
										<div class="issue-main">
											<span class="issue-key">{issue.key}</span>
											<span class="issue-title">{issue.title}</span>
										</div>
										<div class="issue-meta">
											<span class="issue-project">{issue.project.name}</span>
											<Tag
												size="sm"
												style="background-color: {issue.status.color}20; color: {issue.status.color}; border: none;"
											>
												{issue.status.name}
											</Tag>
										</div>
									</button>
								{/snippet}
							</VirtualList>
						</div>
					{:else}
						<div class="issues-list">
							{#each paginatedIssues as issue (issue.id)}
								<button
									class="issue-card"
									onclick={() => navigateToIssue(issue)}
								>
									<div class="issue-main">
										<span class="issue-key">{issue.key}</span>
										<span class="issue-title">{issue.title}</span>
									</div>
									<div class="issue-meta">
										<span class="issue-project">{issue.project.name}</span>
										<Tag
											size="sm"
											style="background-color: {issue.status.color}20; color: {issue.status.color}; border: none;"
										>
											{issue.status.name}
										</Tag>
									</div>
								</button>
							{/each}
						</div>

						{#if totalPages > 1}
							<div class="pagination-wrapper">
								<button
									class="pagination-button"
									disabled={currentPage === 1}
									onclick={() => (currentPage = Math.max(1, currentPage - 1))}
								>
									<ChevronLeft size={20} />
									Назад
								</button>
								<span class="pagination-info">
									Страница {currentPage} из {totalPages}
								</span>
								<button
									class="pagination-button"
									disabled={currentPage === totalPages}
									onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
								>
									Вперед
									<ChevronRight size={20} />
								</button>
							</div>
						{/if}
					{/if}
				</section>
			{/if}

			{#if results.issues.length === 0 && results.projects.length === 0}
				<div class="empty-state">
					<SearchIcon size={32} />
					<h3>Ничего не найдено</h3>
					<p>Попробуйте изменить поисковый запрос</p>
				</div>
			{/if}
		{:else if query}
			<div class="empty-state">
				<SearchIcon size={32} />
				<h3>Нажмите "Найти" для поиска</h3>
			</div>
		{:else}
			<div class="empty-state">
				<SearchIcon size={32} />
				<h3>Введите поисковый запрос</h3>
				<p>Ищите по названию задач, ключам проектов и другим полям</p>
			</div>
		{/if}
	</main>
</div>

<style>
	.search-page {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem;
	}

	.search-header {
		margin-bottom: 2rem;
	}

	.search-header h1 {
		font-size: 1.75rem;
		font-weight: 400;
		margin: 0 0 1.5rem;
		color: var(--cds-text-primary);
	}

	.search-form {
		display: flex;
		gap: 1rem;
	}

	.search-input-wrapper {
		flex: 1;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		background: var(--cds-field);
		border: 1px solid var(--cds-border-strong);
		border-radius: 4px;
		padding: 0 1rem;
		transition: border-color 0.15s ease;
	}

	.search-input-wrapper:focus-within {
		border-color: var(--cds-focus);
		outline: 2px solid var(--cds-focus);
		outline-offset: -2px;
	}

	.search-input-wrapper :global(.search-icon) {
		color: var(--cds-icon-secondary);
		flex-shrink: 0;
	}

	.search-input {
		flex: 1;
		background: transparent;
		border: none;
		outline: none;
		font-size: 1rem;
		color: var(--cds-text-primary);
		padding: 0.875rem 0;
	}

	.search-input::placeholder {
		color: var(--cds-text-placeholder);
	}

	.search-loading {
		display: flex;
		align-items: center;
	}

	.search-loading :global(.bx--loading) {
		width: 20px;
		height: 20px;
	}

	.search-button {
		padding: 0 1.5rem;
		background: var(--cds-interactive);
		color: var(--cds-text-on-color);
		border: none;
		border-radius: 4px;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: background-color 0.15s ease;
	}

	.search-button:hover {
		background: var(--cds-interactive-hover, #0353e9);
	}

	.search-content {
		min-height: 400px;
	}

	.results-summary {
		margin-bottom: 1.5rem;
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
	}

	.results-section {
		margin-bottom: 2rem;
	}

	.section-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 1rem;
		font-weight: 600;
		margin: 0 0 1rem;
		color: var(--cds-text-primary);
	}

	.projects-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
		gap: 1rem;
	}

	.project-card {
		background: var(--cds-layer);
		border: 1px solid var(--cds-border-subtle);
		border-radius: 6px;
		padding: 1rem;
		cursor: pointer;
		transition: all 0.15s ease;
		text-align: left;
		width: 100%;
	}

	.project-card:hover {
		border-color: var(--cds-interactive);
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
	}

	.project-key {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--cds-link-primary);
		margin-bottom: 0.25rem;
	}

	.project-name {
		font-size: 0.875rem;
		color: var(--cds-text-primary);
	}

	.issues-list,
	.issues-list-virtual {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.issues-list-virtual :global(.virtual-list-item) {
		padding-bottom: 0.5rem;
	}

	.issue-card {
		display: flex;
		justify-content: space-between;
		align-items: center;
		background: var(--cds-layer);
		border: 1px solid var(--cds-border-subtle);
		border-radius: 4px;
		padding: 0.75rem 1rem;
		cursor: pointer;
		transition: all 0.15s ease;
		width: 100%;
		text-align: left;
	}

	.issue-card:hover {
		border-color: var(--cds-interactive);
		background: var(--cds-layer-hover);
	}

	.issue-main {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex: 1;
		min-width: 0;
	}

	.issue-key {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--cds-link-primary);
		flex-shrink: 0;
	}

	.issue-title {
		font-size: 0.875rem;
		color: var(--cds-text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.issue-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-shrink: 0;
	}

	.issue-project {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}

	.pagination-wrapper {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		margin-top: 1.5rem;
		padding-top: 1rem;
		border-top: 1px solid var(--cds-border-subtle);
	}

	.pagination-button {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.5rem 0.75rem;
		background: var(--cds-layer);
		border: 1px solid var(--cds-border-subtle);
		border-radius: 4px;
		font-size: 0.875rem;
		color: var(--cds-text-primary);
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.pagination-button:hover:not(:disabled) {
		background: var(--cds-layer-hover);
		border-color: var(--cds-interactive);
	}

	.pagination-button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.pagination-info {
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
	}

	.loading-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		padding: 4rem;
		color: var(--cds-text-secondary);
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 4rem;
		text-align: center;
		color: var(--cds-text-secondary);
	}

	.empty-state :global(svg) {
		opacity: 0.5;
		margin-bottom: 0.5rem;
	}

	.empty-state h3 {
		font-size: 1.125rem;
		font-weight: 500;
		margin: 0;
		color: var(--cds-text-primary);
	}

	.empty-state p {
		font-size: 0.875rem;
		margin: 0;
	}

	.error-message {
		color: var(--cds-support-error);
		margin: 0;
	}

	:global(.error-tile) {
		background: var(--cds-support-error-inverse, #fff1f1) !important;
		border-left: 3px solid var(--cds-support-error);
	}
</style>
