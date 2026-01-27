<script lang="ts">
	import { Search, Select, SelectItem, Button } from 'carbon-components-svelte';
	import { Filter, Close } from 'carbon-icons-svelte';
	import type { IssueType } from '$lib/stores/board';

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
		onFilterChange: (filters: FilterValues) => void;
	}

	let { issueTypes, members, sprints = [], filters, onFilterChange }: Props = $props();

	let searchValue = $state(filters.search || '');
	let selectedTypeId = $state(filters.type_id || '');
	let selectedPriority = $state(filters.priority || '');
	let selectedAssigneeId = $state(filters.assignee_id !== undefined ? String(filters.assignee_id) : '');
	let selectedSprintId = $state(filters.sprint_id || '');

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
</script>

<div class="board-filters">
	<div class="filter-icon">
		<Filter size={20} />
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

	:global(.board-filters .bx--search) {
		background: var(--cds-layer);
	}

	:global(.board-filters .bx--select-input) {
		background: var(--cds-layer);
	}
</style>
