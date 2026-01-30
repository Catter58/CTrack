<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import {
		Button,
		Tile,
		Loading,
		InlineNotification,
		Modal,
		TextInput,
		TextArea,
		NumberInput,
		Select,
		SelectItem,
		Dropdown,
		MultiSelect,
		Checkbox,
		DatePicker,
		DatePickerInput,
		OverflowMenu,
		OverflowMenuItem
	} from 'carbon-components-svelte';
	import { Add, Settings, ChartColumn, Report, Save } from 'carbon-icons-svelte';
	import { projects, currentProject, projectsLoading, projectsError, projectMembers } from '$lib/stores/projects';
	import {
		board,
		boardColumns,
		currentBoard,
		issueTypes,
		boardLoading,
		boardError,
		workflowTransitions,
		flatIssuesList
	} from '$lib/stores/board';
	import { sprints, type SprintWithStats } from '$lib/stores/sprints';
	import {
		filtersStore,
		savedFilters,
		type FilterValues,
		type CreateFilterData,
		type SavedFilter
	} from '$lib/stores/filters';
	import { SaveFilterModal } from '$lib/components/filters';
	import { epicsStore, epicsList } from '$lib/stores/epics';
	import RichEditor from '$lib/components/RichEditor.svelte';
	import { SprintHeader, BoardFilters, BoardSkeleton, BoardView, ListView, ViewSwitcher } from '$lib/components/board';
	import PullToRefresh from '$lib/components/PullToRefresh.svelte';
	import { goto } from '$app/navigation';
	import { toasts } from '$lib/stores/toast';
	import api from '$lib/api/client';
	import {
		saveBoardFilters,
		loadBoardFilters,
		clearBoardFilters,
		hasUrlParams
	} from '$lib/utils/filterStorage';

	const projectKey = $derived(page.params.key);

	// Custom field definition type
	interface CustomFieldDefinition {
		id: string;
		name: string;
		field_key: string;
		field_type: 'text' | 'textarea' | 'number' | 'date' | 'select' | 'multiselect' | 'checkbox' | 'url';
		options: string[];
		is_required: boolean;
		default_value: unknown;
		description: string;
	}

	// Board filters from URL
	interface BoardFilterValues {
		assignee_id?: number;
		type_id?: string;
		priority?: string;
		search?: string;
		sprint_id?: string;
	}

	// Current view from URL (default: board)
	let currentView = $derived.by<'board' | 'list'>(() => {
		const view = page.url.searchParams.get('view');
		return view === 'list' ? 'list' : 'board';
	});

	let boardFilters = $derived.by<BoardFilterValues>(() => {
		const params = page.url.searchParams;
		const f: BoardFilterValues = {};
		const assignee = params.get('assignee');
		if (assignee !== null) {
			f.assignee_id = parseInt(assignee);
		}
		const type = params.get('type');
		if (type) {
			f.type_id = type;
		}
		const priority = params.get('priority');
		if (priority) {
			f.priority = priority;
		}
		const search = params.get('search');
		if (search) {
			f.search = search;
		}
		const sprintId = params.get('sprint');
		if (sprintId) {
			f.sprint_id = sprintId;
		}
		return f;
	});

	function handleViewChange(view: 'board' | 'list') {
		const url = new URL(page.url);
		if (view === 'board') {
			url.searchParams.delete('view');
		} else {
			url.searchParams.set('view', view);
		}
		goto(url.toString(), { replaceState: true, noScroll: true });
	}

	function handleFilterChange(filters: BoardFilterValues) {
		if (!projectKey) return;

		const url = new URL(page.url);

		// Clear existing filter params
		url.searchParams.delete('assignee');
		url.searchParams.delete('type');
		url.searchParams.delete('priority');
		url.searchParams.delete('search');
		url.searchParams.delete('sprint');

		// Set new params
		if (filters.assignee_id !== undefined) {
			url.searchParams.set('assignee', String(filters.assignee_id));
		}
		if (filters.type_id) {
			url.searchParams.set('type', filters.type_id);
		}
		if (filters.priority) {
			url.searchParams.set('priority', filters.priority);
		}
		if (filters.search) {
			url.searchParams.set('search', filters.search);
		}
		if (filters.sprint_id) {
			url.searchParams.set('sprint', filters.sprint_id);
		}

		// Navigate with new URL (without page reload)
		goto(url.toString(), { replaceState: true, noScroll: true });

		// Save filters to localStorage
		saveBoardFilters(projectKey, filters);

		// Reload board with filters
		const boardId = $currentBoard?.id;
		if (boardId) {
			board.loadBoardData(boardId, filters);
		}
	}

	let showCreateIssueModal = $state(false);
	let newIssueTitle = $state('');
	let newIssueTypeId = $state('');
	let newIssuePriority = $state('medium');
	let newIssueDescription = $state('');
	let newIssueAssigneeId = $state<string>('none');
	let newIssueEpicId = $state<string>('none');
	let newIssueDueDate = $state<string>('');
	let newIssueStatusId = $state<string>('');
	let isCreating = $state(false);
	let createError = $state<string | null>(null);

	// Saved filters state
	let showSaveFilterModal = $state(false);
	let selectedFilterId = $state<string>('');

	// Custom fields for create modal
	let customFieldDefinitions = $state<CustomFieldDefinition[]>([]);
	let customFieldsForm = $state<Record<string, unknown>>({});

	// Member dropdown items
	let memberItems = $derived([
		{ id: 'none', text: 'Не назначен' },
		...($projectMembers || []).filter((m) => m && m.user_id).map((m) => ({
			id: m.user_id.toString(),
			text: m.full_name || m.username
		}))
	]);

	// Epic dropdown items
	let epicItems = $derived([
		{ id: 'none', text: 'Без эпика' },
		...$epicsList.map((e) => ({
			id: e.id,
			text: `${e.key}: ${e.title}`
		}))
	]);

	// Members for board/list components
	let members = $derived(
		($projectMembers || []).filter((m) => m && m.user_id).map((m) => ({
			id: m.user_id,
			username: m.username,
			full_name: m.full_name
		}))
	);

	// Check if any filters are active
	let hasActiveFilters = $derived(
		boardFilters.assignee_id !== undefined ||
		boardFilters.type_id !== undefined ||
		boardFilters.priority !== undefined ||
		boardFilters.search !== undefined ||
		boardFilters.sprint_id !== undefined
	);

	// Clear saved filter selection when filters are cleared
	$effect(() => {
		if (!hasActiveFilters && selectedFilterId) {
			selectedFilterId = '';
			filtersStore.setCurrentFilter(null);
		}
	});

	// Sprint state for scrum boards
	let currentSprint = $state<SprintWithStats | null>(null);

	onMount(async () => {
		const key = page.params.key;
		if (!key) return;
		// Load project, members, sprints, and saved filters in parallel
		await Promise.all([
			projects.loadProject(key),
			projects.loadMembers(key),
			sprints.loadSprints(key),
			filtersStore.load(key)
		]);

		// Determine initial filters: URL params take precedence, then localStorage
		let initialFilters: BoardFilterValues;
		if (hasUrlParams(page.url)) {
			initialFilters = boardFilters;
		} else {
			const savedFiltersFromStorage = loadBoardFilters(key);
			if (savedFiltersFromStorage) {
				initialFilters = savedFiltersFromStorage;
				// Update URL to reflect restored filters
				const url = new URL(page.url);
				if (initialFilters.assignee_id !== undefined) {
					url.searchParams.set('assignee', String(initialFilters.assignee_id));
				}
				if (initialFilters.type_id) {
					url.searchParams.set('type', initialFilters.type_id);
				}
				if (initialFilters.priority) {
					url.searchParams.set('priority', initialFilters.priority);
				}
				if (initialFilters.search) {
					url.searchParams.set('search', initialFilters.search);
				}
				if (initialFilters.sprint_id) {
					url.searchParams.set('sprint', initialFilters.sprint_id);
				}
				goto(url.toString(), { replaceState: true, noScroll: true });
			} else {
				initialFilters = boardFilters;
			}
		}

		// Load board data with initial filters
		const boards = await board.loadBoards(key);
		if (boards.length > 0) {
			const boardData = await board.loadBoardData(boards[0].id, initialFilters);

			// If scrum board, load sprint data
			if (boardData && boardData.board.board_type === 'scrum' && boardData.board.sprint_id) {
				const sprint = await sprints.loadSprint(boardData.board.sprint_id);
				if (sprint) {
					currentSprint = sprint;
				}
			}
		}
		// Load issue types, statuses, workflow and epics in parallel
		await Promise.all([
			board.loadIssueTypes(key),
			board.loadStatuses(key),
			board.loadWorkflow(key),
			epicsStore.loadEpics(key)
		]);
	});

	// Check for create param in URL (e.g., ?create=epic)
	let createParam = $derived(page.url.searchParams.get('create'));

	// Set default issue type when loaded
	$effect(() => {
		if ($issueTypes.length > 0 && !newIssueTypeId) {
			const taskType = $issueTypes.find((t) => t.name === 'Задача');
			newIssueTypeId = taskType?.id || $issueTypes[0]?.id || '';
		}
	});

	// Handle create param from URL (e.g., ?create=epic)
	$effect(() => {
		if (createParam && $issueTypes.length > 0 && !showCreateIssueModal) {
			// Find the requested issue type
			const typeName = createParam === 'epic' ? 'Эпик' : createParam;
			const requestedType = $issueTypes.find(
				(t) => t.name.toLowerCase() === typeName.toLowerCase()
			);

			if (requestedType) {
				newIssueTypeId = requestedType.id;
				showCreateIssueModal = true;

				// Clear the create param from URL
				const url = new URL(page.url);
				url.searchParams.delete('create');
				goto(url.toString(), { replaceState: true, noScroll: true });
			}
		}
	});

	// Load custom fields when issue type changes
	$effect(() => {
		if (projectKey && newIssueTypeId) {
			loadCustomFieldsForType(newIssueTypeId);
		}
	});

	async function loadCustomFieldsForType(typeId: string) {
		try {
			const fields = await api.get<CustomFieldDefinition[]>(
				`/api/projects/${projectKey}/custom-fields/for-type/${typeId}`
			);
			customFieldDefinitions = fields;
			const newForm: Record<string, unknown> = {};
			for (const field of fields) {
				if (field.default_value !== null && field.default_value !== undefined) {
					newForm[field.field_key] = field.default_value;
				}
			}
			customFieldsForm = newForm;
		} catch (err) {
			console.error('Failed to load custom fields:', err);
			customFieldDefinitions = [];
			customFieldsForm = {};
		}
	}

	function handleQuickCreate(statusId: string) {
		newIssueStatusId = statusId;
		showCreateIssueModal = true;
	}

	async function handleCreateIssue() {
		if (!projectKey || !newIssueTitle.trim() || !newIssueTypeId) {
			createError = 'Название и тип обязательны';
			return;
		}

		isCreating = true;
		createError = null;

		try {
			await board.createIssue(projectKey, {
				title: newIssueTitle.trim(),
				issue_type_id: newIssueTypeId,
				priority: newIssuePriority,
				description: newIssueDescription.trim() || undefined,
				assignee_id: newIssueAssigneeId !== 'none' ? parseInt(newIssueAssigneeId) : undefined,
				epic_id: newIssueEpicId !== 'none' ? newIssueEpicId : undefined,
				due_date: newIssueDueDate || undefined,
				status_id: newIssueStatusId || undefined,
				custom_fields: Object.keys(customFieldsForm).length > 0 ? customFieldsForm : undefined
			});

			showCreateIssueModal = false;
			newIssueTitle = '';
			newIssueDescription = '';
			newIssueAssigneeId = 'none';
			newIssueEpicId = 'none';
			newIssueDueDate = '';
			newIssueStatusId = '';
			customFieldsForm = {};
		} catch (err) {
			createError = err instanceof Error ? err.message : 'Не удалось создать задачу';
		} finally {
			isCreating = false;
		}
	}

	async function handleStatusUpdate(issueKey: string, statusId: string) {
		try {
			await board.updateIssueStatus(issueKey, statusId);
		} catch (err) {
			const message = err instanceof Error ? err.message : 'Ошибка обновления статуса';
			toasts.error('Ошибка', message);
			// Reload board to revert
			const boardId = $currentBoard?.id;
			if (boardId) {
				await board.loadBoardData(boardId, boardFilters);
			}
		}
	}

	function handleTransitionError(message: string, fromStatus: string, toStatus: string) {
		toasts.warning('Переход недоступен', `Нельзя переместить из "${fromStatus}" в "${toStatus}"`);
		// Reload board to revert
		const boardId = $currentBoard?.id;
		if (boardId) {
			board.loadBoardData(boardId, boardFilters);
		}
	}

	async function handleUpdatePriority(issueKey: string, priority: string) {
		try {
			await board.updateIssue(issueKey, { priority });
			toasts.success('Приоритет обновлён');
		} catch (err) {
			console.error('Failed to update priority:', err);
		}
	}

	async function handleUpdateAssignee(issueKey: string, assigneeId: number | null) {
		try {
			await board.updateIssue(issueKey, { assignee_id: assigneeId });
			toasts.success('Исполнитель обновлён');
		} catch (err) {
			console.error('Failed to update assignee:', err);
		}
	}

	async function handleUpdateStoryPoints(issueKey: string, storyPoints: number | null) {
		try {
			await board.updateIssueStoryPoints(issueKey, storyPoints);
		} catch {
			toasts.error('Ошибка', 'Не удалось обновить Story Points');
		}
	}

	// Saved filters handlers
	function buildFiltersForSave(): FilterValues {
		const f: FilterValues = {};
		if (boardFilters.assignee_id !== undefined) {
			f.assignee_id = boardFilters.assignee_id;
		}
		if (boardFilters.type_id) {
			f.type_id = boardFilters.type_id;
		}
		if (boardFilters.priority) {
			f.priority = boardFilters.priority;
		}
		if (boardFilters.search) {
			f.search = boardFilters.search;
		}
		// Note: sprint_id is not part of FilterValues, it's board-specific
		return f;
	}

	function handleSavedFilterApply(filter: SavedFilter) {
		selectedFilterId = filter.id;
		filtersStore.setCurrentFilter(filter);
		// Apply the saved filter values, preserving current sprint filter
		const newFilters: BoardFilterValues = {
			...filter.filters,
			sprint_id: boardFilters.sprint_id
		};
		handleFilterChange(newFilters);
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
				filtersStore.setCurrentFilter(null);
				handleFilterChange({});
			}
		}
	}

	// Pull-to-refresh handler
	async function handleRefresh(): Promise<void> {
		const boardId = $currentBoard?.id;
		if (boardId) {
			await board.loadBoardData(boardId, boardFilters);
			toasts.success('Обновлено');
		}
	}

	// Keyboard shortcuts
	function handleKeyDown(event: KeyboardEvent) {
		if (
			event.target instanceof HTMLInputElement ||
			event.target instanceof HTMLTextAreaElement ||
			event.target instanceof HTMLSelectElement
		) {
			return;
		}

		switch (event.key.toLowerCase()) {
			case 'c':
				showCreateIssueModal = true;
				event.preventDefault();
				break;
			case 'b':
				window.location.href = `/projects/${projectKey}/backlog`;
				event.preventDefault();
				break;
			case 'v':
				// Toggle view
				handleViewChange(currentView === 'board' ? 'list' : 'board');
				event.preventDefault();
				break;
			case 'escape':
				if (showCreateIssueModal) {
					showCreateIssueModal = false;
					event.preventDefault();
				}
				break;
		}
	}
</script>

<svelte:head>
	<title>{$currentProject?.name || projectKey} - CTrack</title>
</svelte:head>

<svelte:window onkeydown={handleKeyDown} />

{#if $projectsLoading}
	<div class="loading-container">
		<Loading withOverlay={false} />
	</div>
{:else if $boardLoading && !$currentBoard}
	<BoardSkeleton columns={4} cardsPerColumn={3} />
{:else if $projectsError}
	<InlineNotification
		kind="error"
		title="Ошибка"
		subtitle={$projectsError}
		on:close={() => projects.clearError()}
	/>
{:else if $currentProject}
	<div class="project-page">
		<header class="project-header">
			<div class="header-content">
				<h1 class="project-title">{$currentProject.name}</h1>
				{#if $currentProject.description}
					<p class="description">{$currentProject.description}</p>
				{/if}
			</div>
			<div class="header-actions">
				<Button kind="ghost" href="/projects/{projectKey}/issues">
					Задачи
				</Button>
				<Button kind="ghost" href="/projects/{projectKey}/backlog">
					Бэклог
				</Button>
				<Button kind="ghost" href="/projects/{projectKey}/epics">
					Эпики
				</Button>
				<Button kind="ghost" href="/projects/{projectKey}/sprints">
					Спринты
				</Button>
				<Button kind="ghost" icon={ChartColumn} href="/projects/{projectKey}/metrics">
					Метрики
				</Button>
				<Button kind="ghost" icon={Report} href="/projects/{projectKey}/reports">
					Отчёты
				</Button>
				<Button kind="ghost" icon={Settings} href="/projects/{projectKey}/settings">
					Настройки
				</Button>
				<Button icon={Add} on:click={() => (showCreateIssueModal = true)}>Создать задачу</Button>
			</div>
		</header>

		{#if $boardError}
			<InlineNotification
				kind="error"
				title="Ошибка доски"
				subtitle={$boardError}
				on:close={() => board.clearError()}
			/>
		{/if}

		{#if $currentBoard?.board_type === 'scrum' && currentSprint}
			<SprintHeader sprint={currentSprint} />
		{/if}

		<div class="filters-container">
			<div class="filters-left">
				<BoardFilters
					issueTypes={$issueTypes}
					members={members}
					sprints={$sprints.sprints}
					filters={boardFilters}
					savedFilters={$savedFilters}
					{selectedFilterId}
					onFilterChange={handleFilterChange}
					onSavedFilterSelect={handleSavedFilterApply}
					onClear={() => projectKey && clearBoardFilters(projectKey)}
				/>
			</div>
			<div class="filters-right">
				{#if hasActiveFilters}
					<Button
						kind="tertiary"
						size="small"
						icon={Save}
						on:click={() => (showSaveFilterModal = true)}
					>
						Сохранить
					</Button>
				{/if}
				{#if $savedFilters.length > 0}
					<OverflowMenu flipped iconDescription="Управление фильтрами">
						{#each $savedFilters as filter (filter.id)}
							<OverflowMenuItem
								text="Удалить «{filter.name}»"
								danger
								on:click={() => handleDeleteFilter(filter)}
							/>
						{/each}
					</OverflowMenu>
				{/if}
				<ViewSwitcher {currentView} onViewChange={handleViewChange} />
			</div>
		</div>

		<PullToRefresh onRefresh={handleRefresh}>
			{#if currentView === 'board'}
				<BoardView
					columns={$boardColumns}
					workflowTransitions={$workflowTransitions}
					{members}
					onStatusUpdate={handleStatusUpdate}
					onPriorityUpdate={handleUpdatePriority}
					onAssigneeUpdate={handleUpdateAssignee}
					onStoryPointsUpdate={handleUpdateStoryPoints}
					onQuickCreate={handleQuickCreate}
					onTransitionError={handleTransitionError}
				/>
			{:else}
				<ListView
					issues={$flatIssuesList}
					{members}
					onPriorityUpdate={handleUpdatePriority}
					onAssigneeUpdate={handleUpdateAssignee}
				/>
			{/if}
		</PullToRefresh>
	</div>
{:else}
	<div class="not-found">
		<Tile>
			<h2>Проект не найден</h2>
			<p>Проект с ключом "{projectKey}" не существует или у вас нет доступа.</p>
			<Button href="/projects">Вернуться к проектам</Button>
		</Tile>
	</div>
{/if}

<Modal
	bind:open={showCreateIssueModal}
	modalHeading="Новая задача"
	primaryButtonText="Создать"
	secondaryButtonText="Отмена"
	primaryButtonDisabled={isCreating || !newIssueTitle.trim() || !newIssueTypeId}
	on:click:button--primary={handleCreateIssue}
	on:click:button--secondary={() => (showCreateIssueModal = false)}
	on:close={() => (showCreateIssueModal = false)}
>
	<div class="modal-form">
		{#if createError}
			<InlineNotification kind="error" title="Ошибка" subtitle={createError} hideCloseButton lowContrast />
		{/if}

		<div class="form-group">
			<TextInput bind:value={newIssueTitle} labelText="Название" placeholder="Что нужно сделать?" required />
		</div>

		<div class="form-row">
			<div class="form-field">
				<Select bind:selected={newIssueTypeId} labelText="Тип задачи">
					{#each $issueTypes as type (type.id)}
						<SelectItem value={type.id} text={type.name} />
					{/each}
				</Select>
			</div>
			<div class="form-field">
				<Select bind:selected={newIssuePriority} labelText="Приоритет">
					<SelectItem value="lowest" text="Минимальный" />
					<SelectItem value="low" text="Низкий" />
					<SelectItem value="medium" text="Средний" />
					<SelectItem value="high" text="Высокий" />
					<SelectItem value="highest" text="Критический" />
				</Select>
			</div>
		</div>

		<div class="form-row">
			<div class="form-field">
				<Dropdown
					label="Исполнитель"
					selectedId={newIssueAssigneeId}
					items={memberItems}
					on:select={(e) => (newIssueAssigneeId = e.detail.selectedId)}
				/>
			</div>
			<div class="form-field date-picker-field">
				<DatePicker
					datePickerType="single"
					dateFormat="d.m.Y"
					on:change={(e) => {
						const detail = e.detail;
						if (detail && typeof detail === 'object' && 'dateStr' in detail && typeof detail.dateStr === 'string') {
							const parts = detail.dateStr.split('.');
							if (parts.length === 3) {
								newIssueDueDate = `${parts[2]}-${parts[1]}-${parts[0]}`;
							}
						}
					}}
				>
					<DatePickerInput labelText="Срок" placeholder="дд.мм.гггг" />
				</DatePicker>
			</div>
		</div>

		{#if epicItems.length > 1}
			<div class="form-group">
				<Dropdown
					label="Эпик"
					selectedId={newIssueEpicId}
					items={epicItems}
					on:select={(e) => (newIssueEpicId = e.detail.selectedId)}
				/>
			</div>
		{/if}

		{#if customFieldDefinitions.length > 0}
			<div class="custom-fields-section">
				<h4>Дополнительные поля</h4>
				{#each customFieldDefinitions as field (field.id)}
					<div class="form-group">
						{#if field.field_type === 'text'}
							<TextInput
								labelText={field.name}
								value={customFieldsForm[field.field_key]?.toString() || ''}
								required={field.is_required}
								on:input={(e) => {
									const target = e.target as HTMLInputElement;
									customFieldsForm[field.field_key] = target.value;
								}}
							/>
						{:else if field.field_type === 'textarea'}
							<TextArea
								labelText={field.name}
								value={customFieldsForm[field.field_key]?.toString() || ''}
								required={field.is_required}
								on:input={(e) => {
									const target = e.target as HTMLTextAreaElement;
									customFieldsForm[field.field_key] = target.value;
								}}
							/>
						{:else if field.field_type === 'number'}
							<NumberInput
								labelText={field.name}
								value={typeof customFieldsForm[field.field_key] === 'number' ? (customFieldsForm[field.field_key] as number) : null}
								on:change={(e) => {
									customFieldsForm[field.field_key] = e.detail ?? null;
								}}
							/>
						{:else if field.field_type === 'date'}
							<DatePicker
								datePickerType="single"
								dateFormat="d.m.Y"
								value={customFieldsForm[field.field_key]?.toString() || ''}
								on:change={(e) => {
									const detail = e.detail;
									if (detail && typeof detail === 'object' && 'dateStr' in detail) {
										const dateStr = detail.dateStr;
										if (typeof dateStr === 'string' && dateStr) {
											const parts = dateStr.split('.');
											if (parts.length === 3) {
												customFieldsForm[field.field_key] = `${parts[2]}-${parts[1]}-${parts[0]}`;
											}
										} else {
											customFieldsForm[field.field_key] = null;
										}
									}
								}}
							>
								<DatePickerInput labelText={field.name} placeholder="дд.мм.гггг" />
							</DatePicker>
						{:else if field.field_type === 'select'}
							<Dropdown
								label={field.name}
								selectedId={customFieldsForm[field.field_key]?.toString() || ''}
								items={[
									{ id: '', text: 'Не выбрано' },
									...field.options.map((opt) => ({ id: opt, text: opt }))
								]}
								on:select={(e) => {
									customFieldsForm[field.field_key] = e.detail.selectedId || null;
								}}
							/>
						{:else if field.field_type === 'multiselect'}
							<MultiSelect
								label={field.name}
								selectedIds={Array.isArray(customFieldsForm[field.field_key]) ? (customFieldsForm[field.field_key] as string[]) : []}
								items={field.options.map((opt) => ({ id: opt, text: opt }))}
								on:select={(e) => {
									customFieldsForm[field.field_key] = e.detail.selectedIds;
								}}
							/>
						{:else if field.field_type === 'checkbox'}
							<Checkbox
								labelText={field.name}
								checked={customFieldsForm[field.field_key] === true}
								on:check={(e) => {
									customFieldsForm[field.field_key] = e.detail;
								}}
							/>
						{:else if field.field_type === 'url'}
							<TextInput
								labelText={field.name}
								value={customFieldsForm[field.field_key]?.toString() || ''}
								required={field.is_required}
								type="url"
								on:input={(e) => {
									const target = e.target as HTMLInputElement;
									customFieldsForm[field.field_key] = target.value;
								}}
							/>
						{/if}
					</div>
				{/each}
			</div>
		{/if}

		<div class="form-group">
			<label class="bx--label">Описание</label>
			<RichEditor
				value={newIssueDescription}
				placeholder="Опишите задачу..."
				onchange={(json) => (newIssueDescription = json)}
			/>
		</div>
	</div>
</Modal>

<SaveFilterModal
	open={showSaveFilterModal}
	filters={buildFiltersForSave()}
	onClose={() => (showSaveFilterModal = false)}
	onSave={handleSaveFilter}
/>

<style>
	.loading-container {
		min-height: 50vh;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.project-page {
		height: calc(100vh - 48px);
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.project-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		padding: 1.5rem 2rem;
		border-bottom: 1px solid var(--cds-border-subtle);
		flex-shrink: 0;
	}

	.project-title {
		font-size: 1.5rem;
		font-weight: 600;
		margin: 0;
	}

	.header-content .description {
		color: var(--cds-text-secondary);
		margin: 0.5rem 0 0;
		font-size: 0.875rem;
	}

	.header-actions {
		display: flex;
		gap: 0.5rem;
	}

	.filters-container {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem 1rem;
		flex-shrink: 0;
		gap: 1rem;
	}

	.filters-left {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.filters-right {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-shrink: 0;
	}

	/* Prevent layout shift when buttons appear/disappear */
	.filters-left :global(.bx--btn),
	.filters-right :global(.bx--btn) {
		flex-shrink: 0;
	}

	.not-found {
		display: flex;
		justify-content: center;
		padding: 3rem;
	}

	.not-found :global(.bx--tile) {
		text-align: center;
		padding: 2rem;
	}

	.not-found h2 {
		margin: 0 0 0.5rem;
	}

	.not-found p {
		color: var(--cds-text-secondary);
		margin: 0 0 1rem;
	}

	/* Modal form styles */
	.modal-form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.form-group {
		width: 100%;
	}

	.form-group :global(.bx--label) {
		display: block;
		margin-bottom: 0.5rem;
		font-size: 0.75rem;
		font-weight: 400;
		color: var(--cds-text-secondary);
	}

	.form-row {
		display: flex;
		flex-direction: row;
		align-items: flex-end;
		gap: 1rem;
		width: 100%;
	}

	.form-field {
		flex: 1 1 0;
		min-width: 0;
	}

	.form-field :global(.bx--dropdown__wrapper),
	.form-field :global(.bx--date-picker),
	.form-field :global(.bx--form-item) {
		width: 100%;
	}

	.form-field :global(.bx--dropdown) {
		max-width: 100%;
	}

	.form-field :global(.bx--select) {
		width: 100%;
	}

	/* RichEditor in modal - compact height */
	.modal-form .form-group :global(.editor-container),
	.modal-form .form-group :global(.editor-wrapper) {
		min-height: 80px !important;
	}

	/* Custom fields section */
	.custom-fields-section {
		margin-top: 0.5rem;
		padding-top: 1rem;
		border-top: 1px solid var(--cds-border-subtle);
	}

	.custom-fields-section h4 {
		font-size: 0.875rem;
		font-weight: 600;
		margin-bottom: 1rem;
		color: var(--cds-text-primary);
	}

	/* Fix DatePicker calendar in modal */
	:global(.bx--modal) {
		overflow: visible;
	}

	:global(.bx--modal-content) {
		overflow: visible !important;
	}

	:global(.bx--modal-container) {
		overflow: visible !important;
	}

	:global(.bx--modal-container .bx--modal-content--overflow-indicator) {
		display: none;
	}

	.date-picker-field {
		position: relative;
	}

	.date-picker-field :global(.bx--date-picker) {
		position: static;
	}

	.date-picker-field :global(.bx--date-picker-container) {
		position: relative;
	}

	.date-picker-field :global(.bx--date-picker__calendar),
	.date-picker-field :global(.flatpickr-calendar) {
		position: absolute !important;
		z-index: 10001 !important;
		top: 100% !important;
		left: 0 !important;
	}

	/* Mobile responsive styles */
	@media (max-width: 768px) {
		.project-page {
			height: auto;
			min-height: calc(100vh - 48px - 64px);
			overflow: visible;
		}

		.project-header {
			flex-direction: column;
			gap: 1rem;
			padding: 1rem;
		}

		.header-content {
			width: 100%;
		}

		.project-title {
			font-size: 1.25rem;
		}

		.header-actions {
			width: 100%;
			flex-wrap: wrap;
			overflow-x: auto;
			padding-bottom: 0.5rem;
			scrollbar-width: none;
			-ms-overflow-style: none;
		}

		.header-actions::-webkit-scrollbar {
			display: none;
		}

		.header-actions :global(.bx--btn) {
			flex-shrink: 0;
			padding: 0 0.75rem;
		}

		.filters-container {
			flex-direction: column;
			align-items: stretch;
			padding: 0.75rem;
			gap: 0.75rem;
		}

		.filters-left {
			overflow-x: auto;
			padding-bottom: 0.5rem;
			scrollbar-width: none;
			-ms-overflow-style: none;
		}

		.filters-left::-webkit-scrollbar {
			display: none;
		}

		.filters-right {
			justify-content: flex-end;
		}

		.form-row {
			flex-direction: column;
		}

		.form-field {
			width: 100%;
		}

		.not-found {
			padding: 1.5rem;
		}
	}
</style>
