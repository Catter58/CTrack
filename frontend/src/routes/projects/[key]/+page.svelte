<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { page } from '$app/stores';
	import {
		Button,
		Tile,
		Loading,
		InlineNotification,
		ToastNotification,
		Tag,
		Modal,
		TextInput,
		Select,
		SelectItem,
		Dropdown,
		DatePicker,
		DatePickerInput
	} from 'carbon-components-svelte';
	import { Add, Settings, User, Calendar } from 'carbon-icons-svelte';
	import { projects, currentProject, projectsLoading, projectsError, projectMembers } from '$lib/stores/projects';
	import {
		board,
		boardColumns,
		issueTypes,
		boardLoading,
		boardError,
		workflowTransitions,
		type Issue,
		type BoardColumn
	} from '$lib/stores/board';
	import RichEditor from '$lib/components/RichEditor.svelte';

	const projectKey = $derived($page.params.key);

	let showCreateIssueModal = $state(false);
	let newIssueTitle = $state('');
	let newIssueTypeId = $state('');
	let newIssuePriority = $state('medium');
	let newIssueDescription = $state('');
	let newIssueAssigneeId = $state<string>('none');
	let newIssueDueDate = $state<string>('');
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

	// Drag state
	let draggedIssue = $state<Issue | null>(null);
	let dragOverColumnId = $state<string | null>(null);

	// Toast notification state
	let toastMessage = $state<string | null>(null);
	let toastTimeout: ReturnType<typeof setTimeout> | null = null;

	function showToast(message: string) {
		toastMessage = message;
		if (toastTimeout) {
			clearTimeout(toastTimeout);
		}
		toastTimeout = setTimeout(() => {
			toastMessage = null;
		}, 4000);
	}

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

	// Check if a column is a valid drop target
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
		// Load project and members in parallel
		await Promise.all([
			projects.loadProject(key),
			projects.loadMembers(key)
		]);
		// Load board data
		const boards = await board.loadBoards(key);
		if (boards.length > 0) {
			await board.loadBoardData(boards[0].id);
		}
		// Load issue types, statuses and workflow in parallel
		await Promise.all([
			board.loadIssueTypes(key),
			board.loadStatuses(key),
			board.loadWorkflow(key)
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

	async function handleCreateIssue() {
		if (!newIssueTitle.trim() || !newIssueTypeId) {
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
				due_date: newIssueDueDate || undefined
			});

			showCreateIssueModal = false;
			newIssueTitle = '';
			newIssueDescription = '';
			newIssueAssigneeId = 'none';
			newIssueDueDate = '';
		} catch (err) {
			createError = err instanceof Error ? err.message : 'Не удалось создать задачу';
		} finally {
			isCreating = false;
		}
	}

	function handleDragStart(event: DragEvent, issue: Issue) {
		draggedIssue = issue;
		if (event.dataTransfer) {
			event.dataTransfer.effectAllowed = 'move';
			event.dataTransfer.setData('text/plain', issue.key);
		}
	}

	function handleDragOver(event: DragEvent, columnId: string) {
		event.preventDefault();
		dragOverColumnId = columnId;
		if (event.dataTransfer) {
			event.dataTransfer.dropEffect = 'move';
		}
	}

	function handleDragLeave() {
		dragOverColumnId = null;
	}

	async function handleDrop(event: DragEvent, column: BoardColumn) {
		event.preventDefault();
		dragOverColumnId = null;

		if (!draggedIssue || draggedIssue.status.id === column.status.id) {
			draggedIssue = null;
			return;
		}

		// Check workflow transition
		if (!isValidDropTarget(column.status.id)) {
			showToast(`Нельзя переместить из "${draggedIssue.status.name}" в "${column.status.name}"`);
			draggedIssue = null;
			return;
		}

		try {
			await board.updateIssueStatus(draggedIssue.key, column.status.id);
		} catch (err) {
			const message = err instanceof Error ? err.message : 'Ошибка обновления статуса';
			showToast(message);
		}

		draggedIssue = null;
	}

	function handleDragEnd() {
		draggedIssue = null;
		dragOverColumnId = null;
	}

	function getPriorityColor(priority: string): string {
		switch (priority) {
			case 'highest':
				return '#da1e28';
			case 'high':
				return '#ff832b';
			case 'medium':
				return '#f1c21b';
			case 'low':
				return '#0f62fe';
			case 'lowest':
				return '#6f6f6f';
			default:
				return '#6f6f6f';
		}
	}

	function getPriorityLabel(priority: string): string {
		switch (priority) {
			case 'highest':
				return 'Критический';
			case 'high':
				return 'Высокий';
			case 'medium':
				return 'Средний';
			case 'low':
				return 'Низкий';
			case 'lowest':
				return 'Минимальный';
			default:
				return priority;
		}
	}

	function formatDueDate(dateStr: string | null): string {
		if (!dateStr) return '';
		const date = new Date(dateStr);
		return date.toLocaleDateString('ru-RU', {
			day: 'numeric',
			month: 'short'
		});
	}

	function isDueOverdue(dateStr: string | null): boolean {
		if (!dateStr) return false;
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		const due = new Date(dateStr);
		return due < today;
	}

	function isDueSoon(dateStr: string | null): boolean {
		if (!dateStr) return false;
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		const due = new Date(dateStr);
		const diffDays = Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
		return diffDays >= 0 && diffDays <= 2;
	}
</script>

<svelte:head>
	<title>{$currentProject?.name || projectKey} - CTrack</title>
</svelte:head>

{#if $projectsLoading || $boardLoading}
	<div class="loading-container">
		<Loading withOverlay={false} />
	</div>
{:else if $projectsError}
	<InlineNotification
		kind="error"
		title="Ошибка"
		subtitle={$projectsError}
		on:close={() => projects.clearError()}
	/>
{:else if $currentProject}
	<div class="project-page">
		{#if toastMessage}
			<div class="toast-container">
				<ToastNotification
					kind="warning"
					title="Переход недоступен"
					subtitle={toastMessage}
					timeout={4000}
					on:close={() => (toastMessage = null)}
				/>
			</div>
		{/if}
		<header class="project-header">
			<div class="header-content">
				<div class="project-title">
					<Tag type="blue">{$currentProject.key}</Tag>
					<h1>{$currentProject.name}</h1>
				</div>
				{#if $currentProject.description}
					<p class="description">{$currentProject.description}</p>
				{/if}
			</div>
			<div class="header-actions">
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

		<div class="board-container">
			<div class="board">
				{#each $boardColumns as column (column.status.id)}
					<div
						class="column"
						class:drag-over={dragOverColumnId === column.status.id && isValidDropTarget(column.status.id)}
						class:drag-invalid={draggedIssue && !isValidDropTarget(column.status.id) && draggedIssue.status.id !== column.status.id}
						class:drag-allowed={draggedIssue && isValidDropTarget(column.status.id)}
						ondragover={(e) => handleDragOver(e, column.status.id)}
						ondragleave={handleDragLeave}
						ondrop={(e) => handleDrop(e, column)}
						role="region"
						aria-label={column.status.name}
					>
						<div class="column-header">
							<span class="column-title">
								<span class="status-dot" style="background-color: {column.status.color}"></span>
								{column.status.name}
							</span>
							<Tag size="sm">{column.count}</Tag>
						</div>
						<div class="column-content">
							{#each column.issues as issue (issue.key)}
								<a
									href="/issues/{issue.key}"
									class="issue-card"
									draggable="true"
									ondragstart={(e) => handleDragStart(e, issue)}
									ondragend={handleDragEnd}
									role="button"
									tabindex="0"
								>
									<div class="issue-header">
										<span class="issue-type" style="color: {issue.issue_type.color}">
											{issue.issue_type.name}
										</span>
										<span class="issue-key">{issue.key}</span>
									</div>
									<h4 class="issue-title">{issue.title}</h4>
									<div class="issue-footer">
										<span
											class="priority"
											style="color: {getPriorityColor(issue.priority)}"
											title={getPriorityLabel(issue.priority)}
										>
											{getPriorityLabel(issue.priority)}
										</span>
										{#if issue.story_points}
											<Tag size="sm" type="outline">{issue.story_points} SP</Tag>
										{/if}
									</div>
									<div class="issue-meta">
										{#if issue.due_date}
											<span
												class="due-date"
												class:overdue={isDueOverdue(issue.due_date)}
												class:due-soon={isDueSoon(issue.due_date)}
												title="Срок: {formatDueDate(issue.due_date)}"
											>
												<Calendar size={14} />
												{formatDueDate(issue.due_date)}
											</span>
										{/if}
										{#if issue.assignee}
											<span class="assignee" title={issue.assignee.full_name || issue.assignee.username}>
												<User size={14} />
												{issue.assignee.full_name?.split(' ')[0] || issue.assignee.username}
											</span>
										{/if}
									</div>
								</a>
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
	.toast-container {
		position: fixed;
		top: 64px;
		right: 1rem;
		z-index: 9000;
	}

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
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.project-title h1 {
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
		transition: box-shadow 0.15s ease;
	}

	.column.drag-over {
		box-shadow: inset 0 0 0 2px var(--cds-support-success);
		background: rgba(36, 161, 72, 0.1);
	}

	.column.drag-allowed {
		box-shadow: inset 0 0 0 1px var(--cds-support-success);
	}

	.column.drag-invalid {
		opacity: 0.5;
		box-shadow: inset 0 0 0 1px var(--cds-support-error);
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
	}

	.issue-card {
		display: block;
		background: var(--cds-field);
		border: 1px solid var(--cds-border-strong-01, #525252);
		border-radius: 6px;
		padding: 0.75rem;
		cursor: grab;
		text-decoration: none;
		color: inherit;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
		transition:
			transform 0.1s ease,
			box-shadow 0.1s ease,
			border-color 0.1s ease;
	}

	.issue-card:hover {
		border-color: var(--cds-interactive);
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
	}

	.issue-card:active {
		cursor: grabbing;
		transform: scale(1.02);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
	}

	.issue-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 0.75rem;
		margin-bottom: 0.5rem;
	}

	.issue-type {
		font-weight: 500;
	}

	.issue-key {
		color: var(--cds-text-secondary);
	}

	.issue-title {
		font-size: 0.875rem;
		font-weight: 500;
		margin: 0 0 0.5rem;
		line-height: 1.3;
	}

	.issue-footer {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.75rem;
	}

	.priority {
		font-weight: 500;
	}

	.issue-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.75rem;
		margin-top: 0.5rem;
		color: var(--cds-text-secondary);
	}

	.due-date {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.due-date.overdue {
		color: var(--cds-support-error, #da1e28);
	}

	.due-date.due-soon {
		color: var(--cds-support-warning, #f1c21b);
	}

	.assignee {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		margin-left: auto;
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
