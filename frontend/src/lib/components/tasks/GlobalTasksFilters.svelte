<script lang="ts">
	import { Search, Select, SelectItem, DatePicker, DatePickerInput, Button } from 'carbon-components-svelte';
	import { Filter, Close } from 'carbon-icons-svelte';
	import type { Project } from '$lib/stores/projects';
	import type { GlobalStatus, GlobalUser, GlobalTasksFilters } from '$lib/stores/globalTasks';
	import { priorityOptions } from '$lib/stores/globalTasks';
	import { clearTasksFilters } from '$lib/utils/filterStorage';

	interface Props {
		projects: Project[];
		statuses: GlobalStatus[];
		assignees: GlobalUser[];
		filters: GlobalTasksFilters;
		onFilterChange: (filters: GlobalTasksFilters) => void;
		onProjectChange?: (projectKey: string | undefined) => void;
	}

	let { projects, statuses, assignees, filters, onFilterChange, onProjectChange }: Props = $props();

	let searchValue = $state('');
	let selectedProjectId = $state('');
	let selectedStatusId = $state('');
	let selectedPriority = $state('');
	let selectedAssigneeId = $state('');
	let dueDateFrom = $state('');
	let dueDateTo = $state('');

	let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

	let projectItems = $derived([
		{ value: '', text: 'Все проекты' },
		...projects.map((p) => ({ value: p.id, text: `${p.key} - ${p.name}` }))
	]);

	let statusItems = $derived([
		{ value: '', text: 'Все статусы' },
		...statuses.map((s) => ({ value: s.id, text: s.name }))
	]);

	let assigneeItems = $derived([
		{ value: '', text: 'Все исполнители' },
		{ value: '0', text: 'Не назначен' },
		...assignees.map((a) => ({
			value: String(a.id),
			text: a.full_name || a.username
		}))
	]);

	let hasActiveFilters = $derived(
		searchValue.trim() !== '' ||
			selectedProjectId !== '' ||
			selectedStatusId !== '' ||
			selectedPriority !== '' ||
			selectedAssigneeId !== '' ||
			dueDateFrom !== '' ||
			dueDateTo !== ''
	);

	function formatDateForDisplay(isoDate: string): string {
		const parts = isoDate.split('-');
		if (parts.length === 3) {
			const [year, month, day] = parts;
			return `${month}/${day}/${year}`;
		}
		return '';
	}

	function buildFilters(): GlobalTasksFilters {
		const f: GlobalTasksFilters = {};
		if (selectedProjectId !== '') {
			f.project_id = selectedProjectId;
		}
		if (selectedStatusId !== '') {
			f.status_id = selectedStatusId;
		}
		if (selectedPriority !== '') {
			f.priority = selectedPriority;
		}
		if (selectedAssigneeId !== '') {
			f.assignee_id = parseInt(selectedAssigneeId);
		}
		if (dueDateFrom !== '') {
			f.due_date_from = dueDateFrom;
		}
		if (dueDateTo !== '') {
			f.due_date_to = dueDateTo;
		}
		if (searchValue.trim() !== '') {
			f.search = searchValue.trim();
		}
		return f;
	}

	function handleSearchInput(event: Event) {
		const target = event.target as HTMLInputElement;
		searchValue = target.value;

		if (searchDebounceTimer) {
			clearTimeout(searchDebounceTimer);
		}
		searchDebounceTimer = setTimeout(() => {
			onFilterChange(buildFilters());
		}, 300);
	}

	function handleProjectChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		selectedProjectId = target.value;

		// Notify parent to load project-specific data
		if (onProjectChange) {
			const project = projects.find((p) => p.id === selectedProjectId);
			onProjectChange(project?.key);
		}

		onFilterChange(buildFilters());
	}

	function handleStatusChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		selectedStatusId = target.value;
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

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	function handleDateFromChange(event: CustomEvent<any>) {
		const detail = event.detail;
		if (detail && detail.dateStr) {
			const dateStr = typeof detail.dateStr === 'string' ? detail.dateStr : detail.dateStr.from || '';
			dueDateFrom = parseLocalDate(dateStr) || '';
		} else {
			dueDateFrom = '';
		}
		onFilterChange(buildFilters());
	}

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	function handleDateToChange(event: CustomEvent<any>) {
		const detail = event.detail;
		if (detail && detail.dateStr) {
			const dateStr = typeof detail.dateStr === 'string' ? detail.dateStr : detail.dateStr.from || '';
			dueDateTo = parseLocalDate(dateStr) || '';
		} else {
			dueDateTo = '';
		}
		onFilterChange(buildFilters());
	}

	function parseLocalDate(dateStr: string): string | null {
		if (!dateStr) return null;
		// DatePicker returns MM/DD/YYYY format by default
		const parts = dateStr.split('/');
		if (parts.length === 3) {
			const [month, day, year] = parts;
			return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
		}
		return null;
	}

	function clearFilters() {
		searchValue = '';
		selectedProjectId = '';
		selectedStatusId = '';
		selectedPriority = '';
		selectedAssigneeId = '';
		dueDateFrom = '';
		dueDateTo = '';
		clearTasksFilters();
		onProjectChange?.(undefined);
		onFilterChange({});
	}

	// Sync with external filter changes (e.g., from URL)
	$effect(() => {
		searchValue = filters.search || '';
		selectedProjectId = filters.project_id || '';
		selectedStatusId = filters.status_id || '';
		selectedPriority = filters.priority || '';
		selectedAssigneeId = filters.assignee_id !== undefined ? String(filters.assignee_id) : '';
		dueDateFrom = filters.due_date_from || '';
		dueDateTo = filters.due_date_to || '';
	});
</script>

<div class="global-tasks-filters">
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
		{#key projectItems.length}
			<Select
				size="sm"
				labelText=""
				hideLabel
				selected={selectedProjectId}
				on:change={handleProjectChange}
			>
				{#each projectItems as item (item.value)}
					<SelectItem value={item.value} text={item.text} />
				{/each}
			</Select>
		{/key}
	</div>

	<div class="filter-group">
		{#key statusItems.length}
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
			{#each priorityOptions as item (item.value)}
				<SelectItem value={item.value} text={item.text} />
			{/each}
		</Select>
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
				{#each assigneeItems as item (item.value)}
					<SelectItem value={item.value} text={item.text} />
				{/each}
			</Select>
		{/key}
	</div>

	<div class="filter-group date-group">
		<DatePicker
			datePickerType="single"
			dateFormat="m/d/Y"
			on:change={handleDateFromChange}
		>
			<DatePickerInput
				size="sm"
				labelText=""
				placeholder="С даты"
				value={dueDateFrom ? formatDateForDisplay(dueDateFrom) : ''}
			/>
		</DatePicker>
	</div>

	<div class="filter-group date-group">
		<DatePicker
			datePickerType="single"
			dateFormat="m/d/Y"
			on:change={handleDateToChange}
		>
			<DatePickerInput
				size="sm"
				labelText=""
				placeholder="По дату"
				value={dueDateTo ? formatDateForDisplay(dueDateTo) : ''}
			/>
		</DatePicker>
	</div>

	{#if hasActiveFilters}
		<Button kind="ghost" size="small" icon={Close} iconDescription="Очистить фильтры" on:click={clearFilters}>
			Очистить
		</Button>
	{/if}
</div>

<style>
	.global-tasks-filters {
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
		max-width: 280px;
	}

	.date-group {
		min-width: 120px;
	}

	:global(.global-tasks-filters .bx--search) {
		background: var(--cds-layer);
	}

	:global(.global-tasks-filters .bx--select-input) {
		background: var(--cds-layer);
	}

	:global(.global-tasks-filters .bx--date-picker-input__wrapper) {
		width: 100%;
	}

	:global(.global-tasks-filters .bx--date-picker__input) {
		background: var(--cds-layer);
		width: 100%;
	}

	:global(.global-tasks-filters .bx--date-picker--single .bx--date-picker__input) {
		width: 120px;
	}
</style>
