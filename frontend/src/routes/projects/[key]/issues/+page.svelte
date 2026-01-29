<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		Button,
		Loading,
		InlineNotification,
		Search,
		Select,
		SelectItem,
		Dropdown,
		DataTable,
		Pagination,
		Tag,
		Link,
		OverflowMenu,
		OverflowMenuItem,
		Breadcrumb,
		BreadcrumbItem
	} from 'carbon-components-svelte';
	import { ArrowLeft, Save, Filter, Close } from 'carbon-icons-svelte';
	import { projects, projectsLoading, projectMembers } from '$lib/stores/projects';
	import { board, issueTypes, statuses } from '$lib/stores/board';
	import {
		filtersStore,
		savedFilters,
		type FilterValues,
		type CreateFilterData,
		type SavedFilter
	} from '$lib/stores/filters';
	import { SaveFilterModal } from '$lib/components/filters';
	import { toasts } from '$lib/stores/toast';
	import api from '$lib/api/client';

	interface TableIssue {
		id: string;
		key: string;
		title: string;
		status: {
			id: string;
			name: string;
			color: string;
			category: string;
		};
		priority: string;
		assignee: {
			id: number;
			username: string;
			full_name: string;
		} | null;
		issue_type: {
			id: string;
			name: string;
			icon: string;
			color: string;
		};
		created_at: string;
		due_date: string | null;
	}

	interface IssuesResponse {
		items: TableIssue[];
		total: number;
		page: number;
		page_size: number;
	}

	const projectKey = $derived($page.params.key);

	let issues = $state<TableIssue[]>([]);
	let totalCount = $state(0);
	let currentPage = $state(1);
	let pageSize = $state(20);
	let isLoadingIssues = $state(false);
	let issuesError = $state<string | null>(null);

	let showSaveFilterModal = $state(false);
	let selectedFilterId = $state<string>('');

	// Filter values from URL
	let filterValues = $derived.by<FilterValues>(() => {
		const params = $page.url.searchParams;
		const f: FilterValues = {};

		const statusId = params.get('status');
		if (statusId) {
			f.status_id = statusId;
		}

		const priority = params.get('priority');
		if (priority) {
			f.priority = priority;
		}

		const assignee = params.get('assignee');
		if (assignee !== null) {
			f.assignee_id = parseInt(assignee);
		}

		const typeId = params.get('type');
		if (typeId) {
			f.type_id = typeId;
		}

		const search = params.get('search');
		if (search) {
			f.search = search;
		}

		return f;
	});

	// Local filter state for UI controls
	let searchValue = $state('');
	let selectedStatusId = $state('');
	let selectedPriority = $state('');
	let selectedAssigneeId = $state('');
	let selectedTypeId = $state('');

	let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

	const priorities = [
		{ value: '', text: 'Все приоритеты' },
		{ value: 'highest', text: 'Критический' },
		{ value: 'high', text: 'Высокий' },
		{ value: 'medium', text: 'Средний' },
		{ value: 'low', text: 'Низкий' },
		{ value: 'lowest', text: 'Минимальный' }
	];

	let statusItems = $derived([
		{ value: '', text: 'Все статусы' },
		...$statuses.map((s) => ({ value: s.id, text: s.name }))
	]);

	let typeItems = $derived([
		{ value: '', text: 'Все типы' },
		...$issueTypes.map((t) => ({ value: t.id, text: t.name }))
	]);

	let assigneeItems = $derived([
		{ id: '', text: 'Все исполнители' },
		{ id: '0', text: 'Не назначен' },
		...($projectMembers || [])
			.filter((m) => m && m.user_id)
			.map((m) => ({
				id: String(m.user_id),
				text: m.full_name || m.username
			}))
	]);

	let savedFilterItems = $derived([
		{ id: '', text: 'Сохранённые фильтры' },
		...$savedFilters.map((f) => ({ id: f.id, text: f.name }))
	]);

	let hasActiveFilters = $derived(
		searchValue.trim() !== '' ||
			selectedStatusId !== '' ||
			selectedPriority !== '' ||
			selectedAssigneeId !== '' ||
			selectedTypeId !== ''
	);

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const headers: any[] = [
		{ key: 'key', value: 'Ключ' },
		{ key: 'title', value: 'Название' },
		{ key: 'status', value: 'Статус' },
		{ key: 'priority', value: 'Приоритет' },
		{ key: 'assignee', value: 'Исполнитель' },
		{ key: 'created_at', value: 'Создано' },
		{ key: 'due_date', value: 'Срок' }
	];

	// Sync local filter state with URL params
	$effect(() => {
		searchValue = filterValues.search || '';
		selectedStatusId = filterValues.status_id || '';
		selectedPriority = filterValues.priority || '';
		selectedAssigneeId =
			filterValues.assignee_id !== undefined ? String(filterValues.assignee_id) : '';
		selectedTypeId = filterValues.type_id || '';
	});

	let isInitialized = $state(false);
	let previousUrlSearch = $state<string | null>(null);

	onMount(async () => {
		const key = get(page).params.key!;
		await Promise.all([
			projects.loadProject(key),
			projects.loadMembers(key),
			board.loadIssueTypes(key),
			board.loadStatuses(key),
			filtersStore.load(key)
		]);
		// Set initial URL state before loading
		previousUrlSearch = window.location.search;
		await loadIssues();
		isInitialized = true;
	});

	// Reload issues when URL params change (after initial load)
	$effect(() => {
		const currentSearch = $page.url.search;
		// Only reload if URL actually changed after initialization
		if (isInitialized && previousUrlSearch !== null && currentSearch !== previousUrlSearch) {
			previousUrlSearch = currentSearch;
			loadIssues();
		}
	});

	async function loadIssues(): Promise<void> {
		isLoadingIssues = true;
		issuesError = null;

		try {
			const params: Record<string, string> = {
				page: String(currentPage),
				page_size: String(pageSize)
			};

			if (filterValues.status_id) {
				params.status_id = filterValues.status_id;
			}
			if (filterValues.priority) {
				params.priority = filterValues.priority;
			}
			if (filterValues.assignee_id !== undefined) {
				params.assignee_id = String(filterValues.assignee_id);
			}
			if (filterValues.type_id) {
				params.type_id = filterValues.type_id;
			}
			if (filterValues.search) {
				params.search = filterValues.search;
			}

			const response = await api.get<IssuesResponse>(
				`/api/projects/${projectKey}/issues`,
				params
			);

			issues = response.items;
			totalCount = response.total;
		} catch (err) {
			const message = err instanceof Error ? err.message : 'Не удалось загрузить задачи';
			issuesError = message;
		} finally {
			isLoadingIssues = false;
		}
	}

	function buildFilters(): FilterValues {
		const f: FilterValues = {};
		if (selectedStatusId !== '') {
			f.status_id = selectedStatusId;
		}
		if (selectedPriority !== '') {
			f.priority = selectedPriority;
		}
		if (selectedAssigneeId !== '') {
			f.assignee_id = parseInt(selectedAssigneeId);
		}
		if (selectedTypeId !== '') {
			f.type_id = selectedTypeId;
		}
		if (searchValue.trim() !== '') {
			f.search = searchValue.trim();
		}
		return f;
	}

	function applyFilters(filters: FilterValues): void {
		const url = new URL($page.url);

		url.searchParams.delete('status');
		url.searchParams.delete('priority');
		url.searchParams.delete('assignee');
		url.searchParams.delete('type');
		url.searchParams.delete('search');

		if (filters.status_id) {
			url.searchParams.set('status', filters.status_id);
		}
		if (filters.priority) {
			url.searchParams.set('priority', filters.priority);
		}
		if (filters.assignee_id !== undefined) {
			url.searchParams.set('assignee', String(filters.assignee_id));
		}
		if (filters.type_id) {
			url.searchParams.set('type', filters.type_id);
		}
		if (filters.search) {
			url.searchParams.set('search', filters.search);
		}

		currentPage = 1;
		goto(url.toString(), { replaceState: true, noScroll: true });
		// loadIssues will be called by $effect when URL updates
	}

	function handleSearchInput(event: Event): void {
		const target = event.target as HTMLInputElement;
		searchValue = target.value;

		if (searchDebounceTimer) {
			clearTimeout(searchDebounceTimer);
		}
		searchDebounceTimer = setTimeout(() => {
			applyFilters(buildFilters());
		}, 300);
	}

	function handleStatusChange(event: Event): void {
		const target = event.target as HTMLSelectElement;
		selectedStatusId = target.value;
		applyFilters(buildFilters());
	}

	function handlePriorityChange(event: Event): void {
		const target = event.target as HTMLSelectElement;
		selectedPriority = target.value;
		applyFilters(buildFilters());
	}

	function handleAssigneeSelect(
		event: CustomEvent<{ selectedId: string; selectedItem: { id: string; text: string } }>
	): void {
		selectedAssigneeId = event.detail.selectedId;
		applyFilters(buildFilters());
	}

	function handleTypeChange(event: Event): void {
		const target = event.target as HTMLSelectElement;
		selectedTypeId = target.value;
		applyFilters(buildFilters());
	}

	function handleSavedFilterSelect(
		event: CustomEvent<{ selectedId: string; selectedItem: { id: string; text: string } }>
	): void {
		const filterId = event.detail.selectedId;
		selectedFilterId = filterId;

		if (!filterId) {
			return;
		}

		const filter = $savedFilters.find((f) => f.id === filterId);
		if (filter) {
			filtersStore.setCurrentFilter(filter);
			applyFilters(filter.filters);
		}
	}

	function clearFilters(): void {
		searchValue = '';
		selectedStatusId = '';
		selectedPriority = '';
		selectedAssigneeId = '';
		selectedTypeId = '';
		selectedFilterId = '';
		filtersStore.setCurrentFilter(null);
		applyFilters({});
	}

	async function handleSaveFilter(data: CreateFilterData): Promise<void> {
		if (!projectKey) return;
		const filter = await filtersStore.create(projectKey, data);
		if (filter) {
			toasts.success('Фильтр сохранён', `Фильтр "${filter.name}" успешно создан`);
		} else {
			throw new Error('Не удалось сохранить фильтр');
		}
	}

	async function handleDeleteFilter(filter: SavedFilter): Promise<void> {
		if (!projectKey) return;
		const success = await filtersStore.delete(projectKey, filter.id);
		if (success) {
			toasts.success('Фильтр удалён');
			if (selectedFilterId === filter.id) {
				selectedFilterId = '';
				clearFilters();
			}
		}
	}

	function handlePageChange(
		event: CustomEvent<{ page?: number; pageSize?: number }>
	): void {
		if (event.detail.page !== undefined) {
			currentPage = event.detail.page;
		}
		if (event.detail.pageSize !== undefined) {
			pageSize = event.detail.pageSize;
		}
		loadIssues();
	}

	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString('ru-RU', {
			day: '2-digit',
			month: '2-digit',
			year: 'numeric'
		});
	}

	function getPriorityLabel(priority: string): string {
		const labels: Record<string, string> = {
			highest: 'Критический',
			high: 'Высокий',
			medium: 'Средний',
			low: 'Низкий',
			lowest: 'Минимальный'
		};
		return labels[priority] || priority;
	}

	function getPriorityType(
		priority: string
	): 'red' | 'magenta' | 'gray' | 'blue' | 'teal' | undefined {
		const types: Record<string, 'red' | 'magenta' | 'gray' | 'blue' | 'teal'> = {
			highest: 'red',
			high: 'magenta',
			medium: 'gray',
			low: 'blue',
			lowest: 'teal'
		};
		return types[priority];
	}
</script>

<svelte:head>
	<title>Задачи проекта {projectKey} - CTrack</title>
</svelte:head>

<div class="issues-page">
	<Breadcrumb noTrailingSlash>
		<BreadcrumbItem href="/projects">Проекты</BreadcrumbItem>
		<BreadcrumbItem href="/projects/{projectKey}">{projectKey}</BreadcrumbItem>
		<BreadcrumbItem href="/projects/{projectKey}/issues" isCurrentPage>Задачи</BreadcrumbItem>
	</Breadcrumb>

	<header class="page-header">
		<div class="header-left">
			<Button kind="ghost" size="small" icon={ArrowLeft} href="/projects/{projectKey}">
				Назад к доске
			</Button>
			<h1>Задачи проекта {projectKey}</h1>
		</div>
	</header>

	{#if $projectsLoading}
		<Loading />
	{:else if issuesError}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={issuesError}
			on:close={() => (issuesError = null)}
		/>
	{:else}
		<div class="filters-section">
			<div class="filters-row">
				<div class="filter-icon">
					<Filter size={20} />
				</div>

				<div class="filter-group search-group">
					<Search
						size="sm"
						placeholder="Поиск по названию..."
						value={searchValue}
						on:input={handleSearchInput}
						on:clear={() => {
							searchValue = '';
							applyFilters(buildFilters());
						}}
					/>
				</div>

				<div class="filter-group">
					<Select
						size="sm"
						labelText=""
						hideLabel
						selected={selectedStatusId}
						on:change={handleStatusChange}
					>
						{#each statusItems as item (item.value)}
							<SelectItem value={item.value} text={item.text} />
						{/each}
					</Select>
				</div>

				<div class="filter-group">
					<Select
						size="sm"
						labelText=""
						hideLabel
						selected={selectedPriority}
						on:change={handlePriorityChange}
					>
						{#each priorities as item (item.value)}
							<SelectItem value={item.value} text={item.text} />
						{/each}
					</Select>
				</div>

				<div class="filter-group">
					<Dropdown
						size="sm"
						label=""
						hideLabel
						selectedId={selectedAssigneeId}
						items={assigneeItems}
						on:select={handleAssigneeSelect}
					/>
				</div>

				<div class="filter-group">
					<Select
						size="sm"
						labelText=""
						hideLabel
						selected={selectedTypeId}
						on:change={handleTypeChange}
					>
						{#each typeItems as item (item.value)}
							<SelectItem value={item.value} text={item.text} />
						{/each}
					</Select>
				</div>

				{#if hasActiveFilters}
					<Button kind="ghost" size="small" icon={Close} on:click={clearFilters}>Сбросить</Button>
				{/if}
			</div>

			<div class="saved-filters-row">
				<div class="filter-group saved-filters-group">
					<Dropdown
						size="sm"
						label="Сохранённые фильтры"
						hideLabel
						selectedId={selectedFilterId}
						items={savedFilterItems}
						on:select={handleSavedFilterSelect}
					/>
				</div>

				{#if hasActiveFilters}
					<Button
						kind="tertiary"
						size="small"
						icon={Save}
						on:click={() => (showSaveFilterModal = true)}
					>
						Сохранить фильтр
					</Button>
				{/if}

				{#if $savedFilters.length > 0}
					<OverflowMenu flipped iconDescription="Управление фильтрами">
						{#each $savedFilters as filter (filter.id)}
							<OverflowMenuItem
								text="Удалить «{filter.name}»"
								danger
								on:click={() => {
									handleDeleteFilter(filter);
								}}
							/>
						{/each}
					</OverflowMenu>
				{/if}
			</div>
		</div>

		<div class="table-container">
			{#if isLoadingIssues}
				<Loading small withOverlay={false} />
			{:else}
				<DataTable sortable {headers} rows={issues}>
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
								<Link href="/issues/{row.key}">{cell.value}</Link>
							</div>
						{:else if cell.key === 'status'}
							<Tag size="sm" style="--tag-background-color: {row.status.color}">
								{row.status.name}
							</Tag>
						{:else if cell.key === 'priority'}
							<Tag size="sm" type={getPriorityType(cell.value)}>
								{getPriorityLabel(cell.value)}
							</Tag>
						{:else if cell.key === 'assignee'}
							{#if row.assignee}
								{row.assignee.full_name || row.assignee.username}
							{:else}
								<span class="unassigned">Не назначен</span>
							{/if}
						{:else if cell.key === 'created_at'}
							{formatDate(cell.value)}
						{:else if cell.key === 'due_date'}
							{#if cell.value}
								{formatDate(cell.value)}
							{:else}
								<span class="no-date">-</span>
							{/if}
						{:else}
							{cell.value}
						{/if}
					</svelte:fragment>
				</DataTable>

				<Pagination
					bind:pageSize
					bind:page={currentPage}
					totalItems={totalCount}
					pageSizeInputDisabled
					on:change={handlePageChange}
				/>
			{/if}
		</div>
	{/if}
</div>

<SaveFilterModal
	open={showSaveFilterModal}
	filters={buildFilters()}
	onClose={() => (showSaveFilterModal = false)}
	onSave={handleSaveFilter}
/>

<style>
	.issues-page {
		padding: 1rem 2rem;
		max-width: 1600px;
		margin: 0 auto;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin: 1rem 0 1.5rem;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.header-left h1 {
		margin: 0;
		font-size: 1.5rem;
	}

	.filters-section {
		background: var(--cds-field);
		border-radius: 6px;
		padding: 1rem;
		margin-bottom: 1rem;
	}

	.filters-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
	}

	.saved-filters-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-top: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid var(--cds-border-subtle);
	}

	.filter-icon {
		color: var(--cds-text-secondary);
		display: flex;
		align-items: center;
	}

	.filter-group {
		min-width: 140px;
	}

	.search-group {
		min-width: 200px;
		flex: 1;
		max-width: 300px;
	}

	.saved-filters-group {
		min-width: 200px;
	}

	.table-container {
		background: var(--cds-layer);
		border-radius: 6px;
	}

	.title-cell {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.type-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 20px;
		height: 20px;
		border-radius: 4px;
		font-size: 0.75rem;
		flex-shrink: 0;
	}

	.unassigned,
	.no-date {
		color: var(--cds-text-secondary);
	}

	:global(.issues-page .bx--search) {
		background: var(--cds-layer);
	}

	:global(.issues-page .bx--select-input) {
		background: var(--cds-layer);
	}

	:global(.issues-page .bx--dropdown) {
		background: var(--cds-layer);
	}

	:global(.issues-page .bx--data-table) {
		width: 100%;
	}

	:global(.issues-page .bx--pagination) {
		border-top: 1px solid var(--cds-border-subtle);
	}
</style>
