<script lang="ts">
	import { Search, Select, SelectItem, Button } from 'carbon-components-svelte';
	import { Filter, Close } from 'carbon-icons-svelte';
	import type { IssueType } from '$lib/stores/board';
	import type { SavedFilter } from '$lib/stores/filters';

	interface Assignee {
		id: number;
		username: string;
		full_name?: string | null;
	}

	interface Sprint {
		id: string;
		name: string;
		status: 'planned' | 'active' | 'completed';
	}

	interface FilterValues {
		assignee_id?: number;
		type_id?: string;
		priority?: string;
		search?: string;
		sprint_id?: string;
	}

	interface Props {
		issueTypes: IssueType[];
		members: Assignee[];
		sprints?: Sprint[];
		filters: FilterValues;
		savedFilters?: SavedFilter[];
		selectedFilterId?: string;
		onFilterChange: (filters: FilterValues) => void;
		onSavedFilterSelect?: (filter: SavedFilter) => void;
		onClear?: () => void;
	}

	let {
		issueTypes,
		members,
		sprints = [],
		filters,
		savedFilters = [],
		selectedFilterId = '',
		onFilterChange,
		onSavedFilterSelect,
		onClear
	}: Props = $props();

	let showSavedFiltersMenu = $state(false);
	let filterIconRef = $state<HTMLButtonElement | null>(null);

	// Initialize with empty values - $effect below syncs with filters prop
	let searchValue = $state('');
	let selectedTypeId = $state('');
	let selectedPriority = $state('');
	let selectedAssigneeId = $state('');
	let selectedSprintId = $state('');

	let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

	const priorities = [
		{ value: '', text: 'Все приоритеты' },
		{ value: 'highest', text: 'Критический' },
		{ value: 'high', text: 'Высокий' },
		{ value: 'medium', text: 'Средний' },
		{ value: 'low', text: 'Низкий' },
		{ value: 'lowest', text: 'Минимальный' }
	];

	let assigneeItems = $derived([
		{ id: '', text: 'Все исполнители' },
		{ id: '0', text: 'Не назначен' },
		...members.map((m) => ({
			id: String(m.id),
			text: m.full_name || m.username
		}))
	]);

	let typeItems = $derived([
		{ value: '', text: 'Все типы' },
		...issueTypes.map((t) => ({
			value: t.id,
			text: t.name
		}))
	]);

	const sprintStatusLabels: Record<string, string> = {
		active: '(активный)',
		planned: '(план)',
		completed: '(завершён)'
	};

	let sprintItems = $derived([
		{ value: '', text: 'Все спринты' },
		{ value: 'backlog', text: 'Бэклог (без спринта)' },
		...sprints.map((s) => ({
			value: s.id,
			text: `${s.name} ${sprintStatusLabels[s.status] || ''}`
		}))
	]);

	let hasActiveFilters = $derived(
		searchValue.trim() !== '' ||
			selectedTypeId !== '' ||
			selectedPriority !== '' ||
			selectedAssigneeId !== '' ||
			selectedSprintId !== ''
	);

	function buildFilters(): FilterValues {
		const f: FilterValues = {};
		if (selectedAssigneeId !== '') {
			f.assignee_id = parseInt(selectedAssigneeId);
		}
		if (selectedTypeId !== '') {
			f.type_id = selectedTypeId;
		}
		if (selectedPriority !== '') {
			f.priority = selectedPriority;
		}
		if (searchValue.trim() !== '') {
			f.search = searchValue.trim();
		}
		if (selectedSprintId !== '') {
			f.sprint_id = selectedSprintId;
		}
		return f;
	}

	function handleSearchInput(event: Event) {
		const target = event.target as HTMLInputElement;
		searchValue = target.value;

		// Debounce search
		if (searchDebounceTimer) {
			clearTimeout(searchDebounceTimer);
		}
		searchDebounceTimer = setTimeout(() => {
			onFilterChange(buildFilters());
		}, 300);
	}

	function handleTypeChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		selectedTypeId = target.value;
		onFilterChange(buildFilters());
	}

	function handlePriorityChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		selectedPriority = target.value;
		onFilterChange(buildFilters());
	}

	function handleAssigneeChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		selectedAssigneeId = target.value;
		onFilterChange(buildFilters());
	}

	function handleSprintChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		selectedSprintId = target.value;
		onFilterChange(buildFilters());
	}

	function clearFilters() {
		searchValue = '';
		selectedTypeId = '';
		selectedPriority = '';
		selectedAssigneeId = '';
		selectedSprintId = '';
		onClear?.();
		onFilterChange({});
	}

	// Sync with external filter changes (e.g., from URL)
	$effect(() => {
		searchValue = filters.search || '';
		selectedTypeId = filters.type_id || '';
		selectedPriority = filters.priority || '';
		selectedAssigneeId = filters.assignee_id !== undefined ? String(filters.assignee_id) : '';
		selectedSprintId = filters.sprint_id || '';
	});

	function toggleSavedFiltersMenu() {
		showSavedFiltersMenu = !showSavedFiltersMenu;
	}

	function handleSavedFilterClick(filter: SavedFilter) {
		showSavedFiltersMenu = false;
		onSavedFilterSelect?.(filter);
	}

	function handleClickOutside(event: MouseEvent) {
		if (showSavedFiltersMenu && filterIconRef && !filterIconRef.contains(event.target as Node)) {
			const menu = document.querySelector('.saved-filters-menu');
			if (menu && !menu.contains(event.target as Node)) {
				showSavedFiltersMenu = false;
			}
		}
	}
</script>

<svelte:window on:click={handleClickOutside} />

<div class="board-filters">
	<div class="filter-icon-wrapper">
		<button
			class="filter-icon-btn"
			class:has-saved-filters={savedFilters.length > 0}
			class:has-selected={selectedFilterId !== ''}
			bind:this={filterIconRef}
			onclick={toggleSavedFiltersMenu}
			title={savedFilters.length > 0 ? 'Сохранённые фильтры' : 'Фильтры'}
		>
			<Filter size={20} />
			{#if savedFilters.length > 0}
				<span class="filter-badge">{savedFilters.length}</span>
			{/if}
		</button>

		{#if showSavedFiltersMenu && savedFilters.length > 0}
			<div class="saved-filters-menu">
				<div class="menu-header">Сохранённые фильтры</div>
				{#each savedFilters as filter (filter.id)}
					<button
						class="menu-item"
						class:selected={selectedFilterId === filter.id}
						onclick={() => handleSavedFilterClick(filter)}
					>
						{filter.name}
						{#if filter.is_shared}
							<span class="shared-badge">общий</span>
						{/if}
					</button>
				{/each}
			</div>
		{/if}
	</div>

	<div class="filter-group search-group">
		<Search
			size="sm"
			placeholder="Поиск задач..."
			value={searchValue}
			on:input={handleSearchInput}
			on:clear={() => {
				searchValue = '';
				onFilterChange(buildFilters());
			}}
		/>
	</div>

	<div class="filter-group">
		{#key assigneeItems.length}
			<Select
				size="sm"
				labelText=""
				hideLabel
				selected={selectedAssigneeId}
				on:change={handleAssigneeChange}
			>
				{#each assigneeItems as item (item.id)}
					<SelectItem value={item.id} text={item.text} />
				{/each}
			</Select>
		{/key}
	</div>

	<div class="filter-group">
		{#key typeItems.length}
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
		{/key}
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

	{#if sprints.length > 0}
		<div class="filter-group sprint-filter">
			{#key sprintItems.length}
				<Select
					size="sm"
					labelText=""
					hideLabel
					selected={selectedSprintId}
					on:change={handleSprintChange}
				>
					{#each sprintItems as item (item.value)}
						<SelectItem value={item.value} text={item.text} />
					{/each}
				</Select>
			{/key}
		</div>
	{/if}

	{#if hasActiveFilters}
		<Button
			kind="ghost"
			size="small"
			icon={Close}
			iconDescription="Очистить фильтры"
			on:click={clearFilters}
		>
			Очистить
		</Button>
	{/if}
</div>

<style>
	.board-filters {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		background: var(--cds-field);
		border-radius: 6px;
		flex-wrap: wrap;
	}

	.filter-icon-wrapper {
		position: relative;
	}

	.filter-icon-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border: none;
		border-radius: 4px;
		background: transparent;
		color: var(--cds-text-secondary);
		cursor: pointer;
		transition: all 0.15s ease;
		position: relative;
	}

	.filter-icon-btn:hover {
		background: var(--cds-layer-hover);
		color: var(--cds-text-primary);
	}

	.filter-icon-btn.has-saved-filters {
		color: var(--cds-text-primary);
	}

	.filter-icon-btn.has-selected {
		color: var(--cds-interactive);
		background: var(--cds-layer);
	}

	.filter-badge {
		position: absolute;
		top: 2px;
		right: 2px;
		min-width: 14px;
		height: 14px;
		padding: 0 4px;
		font-size: 10px;
		font-weight: 600;
		line-height: 14px;
		text-align: center;
		color: var(--cds-text-on-color);
		background: var(--cds-interactive);
		border-radius: 7px;
	}

	.saved-filters-menu {
		position: absolute;
		top: 100%;
		left: 0;
		margin-top: 4px;
		min-width: 200px;
		max-width: 280px;
		background-color: var(--cds-layer-01, var(--cds-layer, #262626));
		border: 1px solid var(--cds-border-subtle);
		border-radius: 4px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
		z-index: 1000;
		overflow: hidden;
	}

	.menu-header {
		padding: 0.5rem 0.75rem;
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--cds-text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		border-bottom: 1px solid var(--cds-border-subtle);
		background-color: var(--cds-layer-accent-01, var(--cds-layer-accent, #333333));
	}

	.menu-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: 0.5rem 0.75rem;
		border: none;
		background-color: var(--cds-layer-01, var(--cds-layer, #262626));
		color: var(--cds-text-primary);
		font-size: 0.875rem;
		text-align: left;
		cursor: pointer;
		transition: background-color 0.1s ease;
	}

	.menu-item:hover {
		background-color: var(--cds-layer-hover-01, var(--cds-layer-hover, #353535));
	}

	.menu-item.selected {
		background-color: var(--cds-layer-selected-01, var(--cds-layer-selected, #393939));
		color: var(--cds-interactive);
	}

	.shared-badge {
		font-size: 0.625rem;
		padding: 2px 6px;
		background-color: var(--cds-tag-background-gray, #525252);
		color: var(--cds-text-secondary);
		border-radius: 10px;
		text-transform: uppercase;
		letter-spacing: 0.3px;
	}

	.filter-group {
		min-width: 140px;
	}

	.search-group {
		min-width: 200px;
		flex: 1;
		max-width: 300px;
	}

	:global(.board-filters .bx--search) {
		background: var(--cds-layer);
	}

	:global(.board-filters .bx--select-input) {
		background: var(--cds-layer);
	}
</style>
