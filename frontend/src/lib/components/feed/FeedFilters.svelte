<script lang="ts">
	import { Select, SelectItem, DatePicker, DatePickerInput, Button } from 'carbon-components-svelte';
	import { Filter, Close } from 'carbon-icons-svelte';
	import type { Project } from '$lib/stores/projects';
	import type { FeedUser, FeedFilters, FeedAction } from '$lib/stores/feed';
	import { actionOptions } from '$lib/stores/feed';
	import { clearFeedFilters } from '$lib/utils/filterStorage';

	interface Props {
		projects: Project[];
		users: FeedUser[];
		filters: FeedFilters;
		onFilterChange: (filters: FeedFilters) => void;
	}

	let { projects, users, filters, onFilterChange }: Props = $props();

	let selectedUserId = $state('');
	let selectedProjectId = $state('');
	let selectedAction = $state('');
	let dateFrom = $state('');
	let dateTo = $state('');

	let projectItems = $derived([
		{ value: '', text: 'Все проекты' },
		...(projects || []).map((p) => ({ value: p.id, text: `${p.key} - ${p.name}` }))
	]);

	let userItems = $derived([
		{ value: '', text: 'Все пользователи' },
		...(users || []).map((u) => ({
			value: String(u.id),
			text: u.full_name || u.username
		}))
	]);

	let hasActiveFilters = $derived(
		selectedUserId !== '' ||
			selectedProjectId !== '' ||
			selectedAction !== '' ||
			dateFrom !== '' ||
			dateTo !== ''
	);

	function formatDateForDisplay(isoDate: string): string {
		const parts = isoDate.split('-');
		if (parts.length === 3) {
			const [year, month, day] = parts;
			return `${month}/${day}/${year}`;
		}
		return '';
	}

	function buildFilters(): FeedFilters {
		const f: FeedFilters = {};
		if (selectedUserId !== '') {
			f.user_id = parseInt(selectedUserId);
		}
		if (selectedProjectId !== '') {
			f.project_id = selectedProjectId;
		}
		if (selectedAction !== '') {
			f.action = selectedAction as FeedAction;
		}
		if (dateFrom !== '') {
			f.date_from = dateFrom;
		}
		if (dateTo !== '') {
			f.date_to = dateTo;
		}
		return f;
	}

	function handleUserChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		selectedUserId = target.value;
		onFilterChange(buildFilters());
	}

	function handleProjectChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		selectedProjectId = target.value;
		onFilterChange(buildFilters());
	}

	function handleActionChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		selectedAction = target.value;
		onFilterChange(buildFilters());
	}

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	function handleDateFromChange(event: CustomEvent<any>) {
		const detail = event.detail;
		if (detail && detail.dateStr) {
			const dateStr = typeof detail.dateStr === 'string' ? detail.dateStr : detail.dateStr.from || '';
			dateFrom = parseLocalDate(dateStr) || '';
		} else {
			dateFrom = '';
		}
		onFilterChange(buildFilters());
	}

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	function handleDateToChange(event: CustomEvent<any>) {
		const detail = event.detail;
		if (detail && detail.dateStr) {
			const dateStr = typeof detail.dateStr === 'string' ? detail.dateStr : detail.dateStr.from || '';
			dateTo = parseLocalDate(dateStr) || '';
		} else {
			dateTo = '';
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
		selectedUserId = '';
		selectedProjectId = '';
		selectedAction = '';
		dateFrom = '';
		dateTo = '';
		clearFeedFilters();
		onFilterChange({});
	}

	// Sync with external filter changes (e.g., from URL)
	$effect(() => {
		selectedUserId = filters.user_id !== undefined ? String(filters.user_id) : '';
		selectedProjectId = filters.project_id || '';
		selectedAction = filters.action || '';
		dateFrom = filters.date_from || '';
		dateTo = filters.date_to || '';
	});
</script>

<div class="feed-filters">
	<div class="filter-icon">
		<Filter size={20} />
	</div>

	<div class="filter-group">
		{#key userItems.length}
			<Select
				size="sm"
				labelText=""
				hideLabel
				selected={selectedUserId}
				on:change={handleUserChange}
			>
				{#each userItems as item (item.value)}
					<SelectItem value={item.value} text={item.text} />
				{/each}
			</Select>
		{/key}
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
		<Select
			size="sm"
			labelText=""
			hideLabel
			selected={selectedAction}
			on:change={handleActionChange}
		>
			{#each actionOptions as item (item.value)}
				<SelectItem value={item.value} text={item.text} />
			{/each}
		</Select>
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
				value={dateFrom ? formatDateForDisplay(dateFrom) : ''}
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
				value={dateTo ? formatDateForDisplay(dateTo) : ''}
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
	.feed-filters {
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
		min-width: 160px;
	}

	.date-group {
		min-width: 120px;
	}

	:global(.feed-filters .bx--select-input) {
		background: var(--cds-layer);
	}

	:global(.feed-filters .bx--date-picker-input__wrapper) {
		width: 100%;
	}

	:global(.feed-filters .bx--date-picker__input) {
		background: var(--cds-layer);
		width: 100%;
	}

	:global(.feed-filters .bx--date-picker--single .bx--date-picker__input) {
		width: 120px;
	}
</style>
