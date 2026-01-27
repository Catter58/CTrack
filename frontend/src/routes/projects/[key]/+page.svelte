<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { page } from '$app/stores';
	import {
		Button,
		Tile,
		Loading,
		InlineNotification,
		Tag,
		Modal,
		TextInput,
		Select,
		SelectItem,
		Dropdown,
		DatePicker,
		DatePickerInput
	} from 'carbon-components-svelte';
	import { Add, Settings, ChartColumn } from 'carbon-icons-svelte';
	import { dndzone, type DndEvent } from 'svelte-dnd-action';
	import { flip } from 'svelte/animate';
	import { projects, currentProject, projectsLoading, projectsError, projectMembers } from '$lib/stores/projects';
	import {
		board,
		boardColumns,
		currentBoard,
		issueTypes,
		boardLoading,
		boardError,
		workflowTransitions,
		type Issue,
		type BoardColumn
	} from '$lib/stores/board';
	import { sprints, type SprintWithStats } from '$lib/stores/sprints';
	import { epicsStore, epicsList } from '$lib/stores/epics';
	import RichEditor from '$lib/components/RichEditor.svelte';
	import { SprintHeader, IssueCard, BoardFilters, BoardSkeleton } from '$lib/components/board';
	import { goto } from '$app/navigation';
	import { toasts } from '$lib/stores/toast';

	const projectKey = $derived($page.params.key);

	// Board filters from URL
	interface BoardFilterValues {
		assignee_id?: number;
		type_id?: string;
		priority?: string;
		search?: string;
		sprint_id?: string;
	}

	let boardFilters = $derived.by<BoardFilterValues>(() => {
		const params = $page.url.searchParams;
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

	function handleFilterChange(filters: BoardFilterValues) {
		const url = new URL($page.url);

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

	// Local state for columns - required for svelte-dnd-action to work properly
	// We sync from the store and manage locally during drag operations
	let localColumns = $state<BoardColumn[]>([]);

	// Sync local columns when store changes (but not during drag)
	let draggedIssueId = $state<string | null>(null);
	const flipDurationMs = 200;

	$effect(() => {
		// Only sync when not dragging to avoid conflicts
		if (!draggedIssueId && $boardColumns.length > 0) {
			localColumns = $boardColumns.map(col => ({
				...col,
				issues: [...col.issues]
			}));
		}
	});

	// Sprint state for scrum boards
	let currentSprint = $state<SprintWithStats | null>(null);

	// Get the dragged issue from its ID
	let draggedIssue = $derived.by(() => {
		if (!draggedIssueId) return null;
		for (const col of localColumns) {
			const found = col.issues.find(i => i.id === draggedIssueId);
			if (found) return found;
		}
		return null;
	});

	// Get allowed target status IDs for the currently dragged issue
	let allowedTargetStatusIds = $derived.by(() => {
		if (!draggedIssue) return [];
		// If no workflow transitions defined, allow all
		if ($workflowTransitions.length === 0) return [];
		const currentStatusId = draggedIssue.status.id;
		return $workflowTransitions
			.filter((t) => t.from_status.id === currentStatusId)
			.map((t) => t.to_status.id);
	});

	// Check if a column is a valid drop target for the dragged issue
	function isValidDropTarget(columnStatusId: string): boolean {
		if (!draggedIssue) return false;
		// Same column - not a valid target
		if (draggedIssue.status.id === columnStatusId) return false;
		// If no workflow defined, allow all transitions
		if ($workflowTransitions.length === 0) return true;
		// Check if transition is allowed
		return allowedTargetStatusIds.includes(columnStatusId);
	}

	onMount(async () => {
		const key = get(page).params.key!;
		// Load project, members, and sprints in parallel
		await Promise.all([
			projects.loadProject(key),
			projects.loadMembers(key),
			sprints.loadSprints(key)
		]);
		// Load board data with initial filters from URL
		const boards = await board.loadBoards(key);
		if (boards.length > 0) {
			const initialFilters = boardFilters;
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

	// Set default issue type when loaded
	$effect(() => {
		if ($issueTypes.length > 0 && !newIssueTypeId) {
			// Default to "Task" type (index 2) or first available
			const taskType = $issueTypes.find((t) => t.name === 'Задача');
			newIssueTypeId = taskType?.id || $issueTypes[0]?.id || '';
		}
	});

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
				status_id: newIssueStatusId || undefined
			});

			showCreateIssueModal = false;
			newIssueTitle = '';
			newIssueDescription = '';
			newIssueAssigneeId = 'none';
			newIssueEpicId = 'none';
			newIssueDueDate = '';
			newIssueStatusId = '';
		} catch (err) {
			createError = err instanceof Error ? err.message : 'Не удалось создать задачу';
		} finally {
			isCreating = false;
		}
	}

	// svelte-dnd-action handlers
	function handleDndConsider(columnStatusId: string, e: CustomEvent<DndEvent<Issue>>) {
		const columnIndex = localColumns.findIndex(c => c.status.id === columnStatusId);
		if (columnIndex !== -1) {
			// Update the column's issues during drag
			localColumns[columnIndex] = {
				...localColumns[columnIndex],
				issues: e.detail.items
			};
		}
		// Track which issue is being dragged
		if (e.detail.info.trigger === 'dragStarted') {
			draggedIssueId = e.detail.info.id as string;
		}
	}

	async function handleDndFinalize(columnStatusId: string, e: CustomEvent<DndEvent<Issue>>) {
		const columnIndex = localColumns.findIndex(c => c.status.id === columnStatusId);
		if (columnIndex === -1) return;

		const column = localColumns[columnIndex];

		// Update column issues
		localColumns[columnIndex] = {
			...column,
			issues: e.detail.items
		};

		// Find the moved issue
		const movedIssueId = e.detail.info.id as string;
		const movedIssue = e.detail.items.find(i => i.id === movedIssueId);

		// Reset drag state
		draggedIssueId = null;

		// If the issue was moved to a different column, update status on server
		if (movedIssue && movedIssue.status.id !== columnStatusId) {
			// Check workflow transition
			const transition = $workflowTransitions.find(
				t => t.from_status.id === movedIssue.status.id && t.to_status.id === columnStatusId
			);

			if ($workflowTransitions.length > 0 && !transition) {
				// Invalid transition - reload board to revert
				toasts.warning('Переход недоступен', `Нельзя переместить из "${movedIssue.status.name}" в "${column.status.name}"`);
				const boardId = $currentBoard?.id;
				if (boardId) {
					await board.loadBoardData(boardId, boardFilters);
				}
				return;
			}

			try {
				await board.updateIssueStatus(movedIssue.key, columnStatusId);
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
	}

	function getColumnStoryPoints(column: BoardColumn): number {
		return column.issues.reduce((sum, issue) => sum + (issue.story_points || 0), 0);
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

	// Keyboard shortcuts
	function handleKeyDown(event: KeyboardEvent) {
		// Don't trigger shortcuts when typing in inputs
		if (
			event.target instanceof HTMLInputElement ||
			event.target instanceof HTMLTextAreaElement ||
			event.target instanceof HTMLSelectElement
		) {
			return;
		}

		switch (event.key.toLowerCase()) {
			case 'c':
				// Create new issue
				showCreateIssueModal = true;
				event.preventDefault();
				break;
			case 'b':
				// Go to backlog
				window.location.href = `/projects/${projectKey}/backlog`;
				event.preventDefault();
				break;
			case '/':
				// Focus search (if implemented)
				event.preventDefault();
				break;
			case 'escape':
				// Close modal
				if (showCreateIssueModal) {
					showCreateIssueModal = false;
					event.preventDefault();
				}
				break;
		}
	}

	async function handleUpdateStoryPoints(issueKey: string, storyPoints: number | null) {
		try {
			await board.updateIssueStoryPoints(issueKey, storyPoints);
		} catch {
			toasts.error('Ошибка', 'Не удалось обновить Story Points');
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
			<BoardFilters
				issueTypes={$issueTypes}
				members={($projectMembers || []).map((m) => ({
					id: m.user_id,
					username: m.username,
					full_name: m.full_name
				}))}
				sprints={$sprints.sprints}
				filters={boardFilters}
				onFilterChange={handleFilterChange}
			/>
		</div>

		<div class="board-container">
			<div class="board">
				{#each localColumns as column (column.status.id)}
						<div
						class="column"
						class:drag-over={draggedIssueId && isValidDropTarget(column.status.id)}
						class:drag-invalid={draggedIssueId && !isValidDropTarget(column.status.id) && draggedIssue?.status.id !== column.status.id}
						role="region"
						aria-label={column.status.name}
					>
						<div class="column-header">
							<span class="column-title">
								<span class="status-dot" style="background-color: {column.status.color}"></span>
								{column.status.name}
							</span>
							<div class="column-actions">
								<button
									class="quick-add-btn"
									title="Добавить задачу в {column.status.name}"
									onclick={() => handleQuickCreate(column.status.id)}
								>
									<Add size={16} />
								</button>
								<div class="column-stats">
									<Tag size="sm">{column.count}</Tag>
									{#if getColumnStoryPoints(column) > 0}
										<Tag size="sm" type="outline">{getColumnStoryPoints(column)} SP</Tag>
									{/if}
								</div>
							</div>
						</div>
						<div
							class="column-content"
							use:dndzone={{
								items: column.issues,
								flipDurationMs,
								type: 'board-issues'
							}}
							onconsider={(e) => handleDndConsider(column.status.id, e)}
							onfinalize={(e) => handleDndFinalize(column.status.id, e)}
						>
							{#each column.issues as issue (issue.id)}
								<article class="dnd-item" animate:flip={{ duration: flipDurationMs }}>
									<IssueCard
										{issue}
										isDragging={draggedIssueId === issue.id}
										onUpdateStoryPoints={handleUpdateStoryPoints}
										onUpdatePriority={handleUpdatePriority}
										onUpdateAssignee={handleUpdateAssignee}
										availableAssignees={($projectMembers || []).map(m => ({
											id: m.user_id,
											username: m.username,
											full_name: m.full_name
										}))}
									/>
								</article>
							{/each}
						</div>
					</div>
				{/each}
			</div>
		</div>
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
					titleText="Исполнитель"
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
						if (detail && typeof detail === 'object' && 'dateStr' in detail) {
							// Convert from dd.mm.yyyy to yyyy-mm-dd for API
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
					titleText="Эпик"
					selectedId={newIssueEpicId}
					items={epicItems}
					on:select={(e) => (newIssueEpicId = e.detail.selectedId)}
				/>
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
		padding: 0 1rem;
		flex-shrink: 0;
	}

	.board-container {
		flex: 1;
		overflow-x: auto;
		padding: 1rem;
	}

	.board {
		display: flex;
		gap: 1rem;
		height: 100%;
		min-width: max-content;
	}

	.column {
		width: 320px;
		min-width: 320px;
		background: var(--cds-layer);
		border-radius: 8px;
		display: flex;
		flex-direction: column;
		max-height: 100%;
		transition:
			box-shadow 0.2s ease,
			background-color 0.2s ease,
			opacity 0.2s ease,
			transform 0.2s ease;
	}

	.column.drag-over {
		box-shadow: inset 0 0 0 2px var(--cds-support-success);
		background: rgba(36, 161, 72, 0.15);
		transform: scale(1.01);
	}

	.column.drag-invalid {
		opacity: 0.4;
		box-shadow: inset 0 0 0 1px var(--cds-support-error);
		background: rgba(218, 30, 40, 0.05);
	}

	.column-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		border-bottom: 1px solid var(--cds-border-subtle);
	}

	.column-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-weight: 600;
	}

	.column-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.quick-add-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		border: none;
		border-radius: 4px;
		background: transparent;
		color: var(--cds-text-secondary);
		cursor: pointer;
		transition: all 0.1s ease;
	}

	.quick-add-btn:hover {
		background: var(--cds-layer-hover);
		color: var(--cds-interactive);
	}

	.column-stats {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.status-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
	}

	.column-content {
		flex: 1;
		overflow-y: auto;
		padding: 0.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		min-height: 100px;
		transition: background-color 0.2s ease;
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
</style>
