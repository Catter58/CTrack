<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		DataTable,
		Pagination,
		Tag,
		Link,
		Loading,
		InlineNotification
	} from 'carbon-components-svelte';
	import { ArrowUp, ArrowDown, User } from 'carbon-icons-svelte';
	import {
		globalTasks,
		globalTasksList,
		globalTasksProjects,
		globalTasksStatuses,
		globalTasksAssignees,
		globalTasksFilters,
		globalTasksPagination,
		globalTasksSort,
		globalTasksLoading,
		globalTasksError,
		priorityLabels,
		priorityColors,
		type GlobalTasksFilters
	} from '$lib/stores/globalTasks';
	import GlobalTasksFiltersComponent from '$lib/components/tasks/GlobalTasksFilters.svelte';

	// Read filters from URL
	let urlFilters = $derived.by<GlobalTasksFilters>(() => {
		const params = $page.url.searchParams;
		const f: GlobalTasksFilters = {};

		const projectId = params.get('project');
		if (projectId) f.project_id = projectId;

		const statusId = params.get('status');
		if (statusId) f.status_id = statusId;

		const priority = params.get('priority');
		if (priority) f.priority = priority;

		const assignee = params.get('assignee');
		if (assignee !== null) f.assignee_id = parseInt(assignee);

		const dueDateFrom = params.get('due_from');
		if (dueDateFrom) f.due_date_from = dueDateFrom;

		const dueDateTo = params.get('due_to');
		if (dueDateTo) f.due_date_to = dueDateTo;

		const search = params.get('search');
		if (search) f.search = search;

		return f;
	});

	let isInitialized = $state(false);
	let previousUrlSearch = $state<string | null>(null);

	// Store sortable info separately since DataTable headers don't support custom properties
	const sortableColumns = new Set(['key', 'title', 'priority', 'due_date', 'created_at']);

	// DataTable headers - use any to avoid Carbon's strict typing
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const headers: any[] = [
		{ key: 'key', value: 'Ключ' },
		{ key: 'title', value: 'Название' },
		{ key: 'project', value: 'Проект' },
		{ key: 'status', value: 'Статус' },
		{ key: 'priority', value: 'Приоритет' },
		{ key: 'assignee', value: 'Исполнитель' },
		{ key: 'due_date', value: 'Срок' },
		{ key: 'created_at', value: 'Создано' }
	];

	// Transform tasks for DataTable
	let rows = $derived(
		$globalTasksList.map((task) => ({
			id: task.id,
			key: task.key,
			title: task.title,
			project: task.project,
			status: task.status,
			priority: task.priority,
			assignee: task.assignee,
			due_date: task.due_date,
			created_at: task.created_at,
			issue_type: task.issue_type
		}))
	);

	onMount(async () => {
		// Load projects first
		await globalTasks.loadProjects();

		// Parse URL filters and load initial data
		globalTasks.setFilters(urlFilters);
		previousUrlSearch = window.location.search;

		// Load statuses and assignees based on initial filter
		if (urlFilters.project_id) {
			const project = $globalTasksProjects.find((p) => p.id === urlFilters.project_id);
			if (project) {
				await Promise.all([
					globalTasks.loadStatuses(project.key),
					globalTasks.loadAssignees(project.key)
				]);
			}
		} else {
			await globalTasks.loadStatuses();
		}

		await globalTasks.loadTasks();
		isInitialized = true;
	});

	// Reload when URL changes (after initialization)
	$effect(() => {
		const currentSearch = $page.url.search;
		if (isInitialized && previousUrlSearch !== null && currentSearch !== previousUrlSearch) {
			previousUrlSearch = currentSearch;
			globalTasks.setFilters(urlFilters);
			globalTasks.loadTasks();
		}
	});

	function updateUrl(filters: GlobalTasksFilters) {
		const url = new URL($page.url);

		// Clear existing params
		url.searchParams.delete('project');
		url.searchParams.delete('status');
		url.searchParams.delete('priority');
		url.searchParams.delete('assignee');
		url.searchParams.delete('due_from');
		url.searchParams.delete('due_to');
		url.searchParams.delete('search');

		// Set new params
		if (filters.project_id) url.searchParams.set('project', filters.project_id);
		if (filters.status_id) url.searchParams.set('status', filters.status_id);
		if (filters.priority) url.searchParams.set('priority', filters.priority);
		if (filters.assignee_id !== undefined) url.searchParams.set('assignee', String(filters.assignee_id));
		if (filters.due_date_from) url.searchParams.set('due_from', filters.due_date_from);
		if (filters.due_date_to) url.searchParams.set('due_to', filters.due_date_to);
		if (filters.search) url.searchParams.set('search', filters.search);

		goto(url.toString(), { replaceState: true, noScroll: true });
	}

	async function handleFilterChange(filters: GlobalTasksFilters) {
		globalTasks.setFilters(filters);
		globalTasks.setPage(1);
		updateUrl(filters);
		await globalTasks.loadTasks(filters);
	}

	async function handleProjectChange(projectKey: string | undefined) {
		// Load project-specific statuses and assignees
		if (projectKey) {
			await Promise.all([
				globalTasks.loadStatuses(projectKey),
				globalTasks.loadAssignees(projectKey)
			]);
		} else {
			await globalTasks.loadStatuses();
			globalTasks.loadAssignees(undefined);
		}
	}

	async function handlePageChange(event: CustomEvent<{ page?: number; pageSize?: number }>) {
		if (event.detail.page !== undefined) {
			globalTasks.setPage(event.detail.page);
		}
		if (event.detail.pageSize !== undefined) {
			globalTasks.setPageSize(event.detail.pageSize);
		}
		await globalTasks.loadTasks();
	}

	async function handleSort(columnKey: string) {
		if (!sortableColumns.has(columnKey)) return;

		globalTasks.toggleSort(columnKey);
		await globalTasks.loadTasks();
	}

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('ru-RU', {
			day: 'numeric',
			month: 'short'
		});
	}

	function formatRelativeTime(dateStr: string): string {
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

		if (diffDays === 0) {
			const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
			if (diffHours === 0) {
				const diffMins = Math.floor(diffMs / (1000 * 60));
				if (diffMins < 1) return 'только что';
				return `${diffMins} мин. назад`;
			}
			return `${diffHours} ч. назад`;
		}
		if (diffDays === 1) return 'вчера';
		if (diffDays < 7) return `${diffDays} дн. назад`;
		if (diffDays < 30) {
			const weeks = Math.floor(diffDays / 7);
			return `${weeks} нед. назад`;
		}
		return formatDate(dateStr);
	}

	function isOverdue(dateStr: string | null): boolean {
		if (!dateStr) return false;
		const dueDate = new Date(dateStr);
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		return dueDate < today;
	}

	function isDueSoon(dateStr: string | null): boolean {
		if (!dateStr) return false;
		const dueDate = new Date(dateStr);
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		const twoDaysFromNow = new Date(today);
		twoDaysFromNow.setDate(today.getDate() + 2);
		return dueDate >= today && dueDate <= twoDaysFromNow;
	}

	function getAssigneeName(assignee: { username: string; full_name: string | null } | null): string {
		if (!assignee) return '-';
		return assignee.full_name || assignee.username;
	}

	function handleRowClick(issueKey: string) {
		goto(`/issues/${issueKey}`);
	}
</script>

<svelte:head>
	<title>Все задачи - CTrack</title>
</svelte:head>

<div class="tasks-page">
	<header class="page-header">
		<h1>Все задачи</h1>
	</header>

	<GlobalTasksFiltersComponent
		projects={$globalTasksProjects}
		statuses={$globalTasksStatuses}
		assignees={$globalTasksAssignees}
		filters={$globalTasksFilters}
		onFilterChange={handleFilterChange}
		onProjectChange={handleProjectChange}
	/>

	{#if $globalTasksError}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={$globalTasksError}
			on:close={() => globalTasks.clearError()}
		/>
	{/if}

	<div class="table-container">
		{#if $globalTasksLoading && !isInitialized}
			<div class="loading-state">
				<Loading withOverlay={false} />
			</div>
		{:else if rows.length === 0 && !$globalTasksLoading}
			<div class="empty-state">
				<p>Задачи не найдены</p>
				<p class="empty-hint">Попробуйте изменить параметры фильтра</p>
			</div>
		{:else}
			{#if $globalTasksLoading}
				<div class="loading-overlay">
					<Loading small withOverlay={false} />
				</div>
			{/if}
			<DataTable {headers} {rows} size="short">
				<svelte:fragment slot="cell-header" let:header>
					{#if sortableColumns.has(header.key)}
						<button
							class="sortable-header"
							class:active={$globalTasksSort.column === header.key}
							onclick={() => handleSort(header.key)}
						>
							{header.value}
							{#if $globalTasksSort.column === header.key}
								{#if $globalTasksSort.direction === 'asc'}
									<ArrowUp size={16} />
								{:else}
									<ArrowDown size={16} />
								{/if}
							{/if}
						</button>
					{:else}
						{header.value}
					{/if}
				</svelte:fragment>
				<svelte:fragment slot="cell" let:row let:cell>
					{#if cell.key === 'key'}
						<Link href="/issues/{row.key}">{cell.value}</Link>
					{:else if cell.key === 'title'}
						<div class="title-cell">
							<span
								class="type-icon"
								style="background-color: {row.issue_type.color}"
								title={row.issue_type.name}
							></span>
							<button
								class="title-link"
								onclick={() => handleRowClick(row.key)}
							>
								{cell.value}
							</button>
						</div>
					{:else if cell.key === 'project'}
						<Tag size="sm" type="outline">{row.project.key}</Tag>
					{:else if cell.key === 'status'}
						<Tag size="sm" style="--tag-background-color: {row.status.color}">
							{row.status.name}
						</Tag>
					{:else if cell.key === 'priority'}
						<div class="priority-cell">
							<span
								class="priority-dot"
								style="background-color: {priorityColors[cell.value] || '#6f6f6f'}"
							></span>
							<span>{priorityLabels[cell.value] || cell.value}</span>
						</div>
					{:else if cell.key === 'assignee'}
						<div class="assignee-cell">
							{#if row.assignee}
								<User size={16} />
								<span>{getAssigneeName(row.assignee)}</span>
							{:else}
								<span class="no-value">-</span>
							{/if}
						</div>
					{:else if cell.key === 'due_date'}
						{#if cell.value}
							<span
								class="due-date"
								class:overdue={isOverdue(cell.value)}
								class:due-soon={isDueSoon(cell.value)}
							>
								{formatDate(cell.value)}
							</span>
						{:else}
							<span class="no-value">-</span>
						{/if}
					{:else if cell.key === 'created_at'}
						<span class="created-at" title={formatDate(cell.value)}>
							{formatRelativeTime(cell.value)}
						</span>
					{:else}
						{cell.value}
					{/if}
				</svelte:fragment>
			</DataTable>

			<Pagination
				pageSize={$globalTasksPagination.pageSize}
				page={$globalTasksPagination.page}
				totalItems={$globalTasksPagination.total}
				pageSizeInputDisabled
				on:change={handlePageChange}
			/>
		{/if}
	</div>
</div>

<style>
	.tasks-page {
		padding: 1rem 2rem;
		max-width: 1600px;
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

	.table-container {
		background: var(--cds-layer);
		border-radius: 6px;
		margin-top: 1rem;
		position: relative;
	}

	.loading-overlay {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.3);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 10;
		border-radius: 6px;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		min-height: 300px;
		color: var(--cds-text-secondary);
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

	.loading-state {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 300px;
	}

	.sortable-header {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		background: none;
		border: none;
		color: var(--cds-text-secondary);
		font-weight: 600;
		font-size: inherit;
		cursor: pointer;
		padding: 0;
	}

	.sortable-header:hover {
		color: var(--cds-text-primary);
	}

	.sortable-header.active {
		color: var(--cds-interactive);
	}

	.title-cell {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.type-icon {
		width: 14px;
		height: 14px;
		border-radius: 3px;
		flex-shrink: 0;
	}

	.title-link {
		background: none;
		border: none;
		color: var(--cds-link-primary);
		text-align: left;
		cursor: pointer;
		padding: 0;
		font-size: inherit;
	}

	.title-link:hover {
		color: var(--cds-link-primary-hover);
		text-decoration: underline;
	}

	.priority-cell {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.priority-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.assignee-cell {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		color: var(--cds-text-secondary);
	}

	.no-value {
		color: var(--cds-text-disabled);
	}

	.due-date {
		color: var(--cds-text-secondary);
	}

	.due-date.overdue {
		color: var(--cds-support-error);
		font-weight: 500;
	}

	.due-date.due-soon {
		color: var(--cds-support-warning);
		font-weight: 500;
	}

	.created-at {
		color: var(--cds-text-secondary);
		font-size: 0.875rem;
	}

	:global(.tasks-page .bx--data-table) {
		width: 100%;
	}

	:global(.tasks-page .bx--data-table tbody tr) {
		cursor: pointer;
	}

	:global(.tasks-page .bx--data-table tbody tr:hover) {
		background: var(--cds-layer-hover);
	}

	:global(.tasks-page .bx--pagination) {
		border-top: 1px solid var(--cds-border-subtle);
	}

	:global(.tasks-page .bx--link) {
		color: var(--cds-link-primary);
	}

	:global(.tasks-page .bx--link:hover) {
		color: var(--cds-link-primary-hover);
	}
</style>
