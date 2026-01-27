<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount, onDestroy } from 'svelte';
	import {
		Breadcrumb,
		BreadcrumbItem,
		Tile,
		Button,
		Tag,
		TextInput,
		TextArea,
		Select,
		SelectItem,
		Dropdown,
		DatePicker,
		DatePickerInput,
		Modal,
		InlineNotification,
		Loading
	} from 'carbon-components-svelte';
	import { Edit, TrashCan, Send, ArrowRight, Calendar, User } from 'carbon-icons-svelte';
	import {
		issue,
		currentIssue,
		issueComments,
		issueTransitions,
		issueChildren,
		issueLoading,
		issueError,
		priorityLabels,
		priorityColors
	} from '$lib/stores/issue';
	import { projects, projectMembers } from '$lib/stores/projects';
	import { board, statuses } from '$lib/stores/board';
	import api from '$lib/api/client';
	import RichEditor from '$lib/components/RichEditor.svelte';
	import RichContent from '$lib/components/RichContent.svelte';
	import { SubtasksList } from '$lib/components/issues';

	const issueKey = $page.params.key!;

	// Edit mode
	let isEditing = $state(false);
	let editForm = $state({
		title: '',
		description: '',
		priority: '',
		story_points: null as number | null,
		assignee_id: null as number | null,
		due_date: null as string | null
	});

	// Comment
	let newComment = $state('');
	let isAddingComment = $state(false);

	// Delete modal
	let showDeleteModal = $state(false);
	let isDeleting = $state(false);

	// Get done status for quick-complete
	let doneStatusId = $derived(
		$statuses.find((s) => s.category === 'done')?.id ?? null
	);

	onMount(async () => {
		const projectKey = issueKey?.split('-')[0];
		await Promise.all([
			issue.load(issueKey),
			issue.loadComments(issueKey),
			issue.loadTransitions(issueKey),
			issue.loadChildren(issueKey),
			projectKey ? projects.loadMembers(projectKey) : Promise.resolve(),
			projectKey ? board.loadStatuses(projectKey) : Promise.resolve()
		]);
	});

	onDestroy(() => {
		issue.reset();
	});

	function startEdit() {
		if ($currentIssue) {
			editForm = {
				title: $currentIssue.title,
				description: $currentIssue.description ?? '',
				priority: $currentIssue.priority,
				story_points: $currentIssue.story_points,
				assignee_id: $currentIssue.assignee?.id ?? null,
				due_date: $currentIssue.due_date
			};
			isEditing = true;
		}
	}

	async function saveEdit() {
		if (!$currentIssue) return;

		const result = await issue.update(issueKey, {
			title: editForm.title,
			description: editForm.description,
			priority: editForm.priority,
			story_points: editForm.story_points,
			assignee_id: editForm.assignee_id,
			due_date: editForm.due_date
		});

		if (result) {
			isEditing = false;
		}
	}

	function cancelEdit() {
		isEditing = false;
	}

	async function handleTransition(statusId: string) {
		await issue.transitionStatus(issueKey, statusId);
	}

	async function handleAddComment() {
		if (!newComment.trim()) return;

		isAddingComment = true;
		const result = await issue.addComment(issueKey, newComment.trim());
		if (result) {
			newComment = '';
		}
		isAddingComment = false;
	}

	async function handleDelete() {
		if (!$currentIssue) return;

		isDeleting = true;
		try {
			await api.delete(`/api/issues/${issueKey}`);
			// Navigate back to project board
			const projectKey = issueKey.split('-')[0];
			goto(`/projects/${projectKey}`);
		} catch (err) {
			console.error('Failed to delete issue:', err);
		}
		isDeleting = false;
		showDeleteModal = false;
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleString('ru-RU', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatDateShort(dateStr: string | null): string {
		if (!dateStr) return '—';
		return new Date(dateStr).toLocaleDateString('ru-RU', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	}

	function formatUserName(user: { first_name?: string | null; last_name?: string | null; full_name?: string | null; username: string }): string {
		// Try full_name first
		if (user.full_name?.trim()) return user.full_name;
		// Try first_name + last_name
		const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ').trim();
		if (fullName) return fullName;
		// Fallback to username
		return user.username;
	}

	// Prepare members dropdown items
	let memberItems = $derived([
		{ id: 'none', text: 'Не назначен' },
		...$projectMembers.map((m) => ({
			id: m.user_id.toString(),
			text: m.full_name || m.username
		}))
	]);
</script>

<svelte:head>
	<title>{$currentIssue?.key || issueKey} - CTrack</title>
</svelte:head>

{#if $issueLoading && !$currentIssue}
	<div class="loading-container">
		<Loading withOverlay={false} />
	</div>
{:else if $issueError}
	<div class="error-container">
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={$issueError}
			on:close={() => issue.clearError()}
		/>
	</div>
{:else if $currentIssue}
	{@const projectKey = issueKey.split('-')[0]}
	<div class="issue-page">
		<Breadcrumb noTrailingSlash>
			<BreadcrumbItem href="/projects">Проекты</BreadcrumbItem>
			<BreadcrumbItem href="/projects/{projectKey}">{projectKey}</BreadcrumbItem>
			<BreadcrumbItem href="/issues/{issueKey}" isCurrentPage>{issueKey}</BreadcrumbItem>
		</Breadcrumb>

		<div class="issue-layout">
			<!-- Main Content -->
			<main class="issue-main">
				<header class="issue-header">
					<div class="header-top">
						<div class="issue-meta">
							<Tag type="blue" style="background-color: {$currentIssue.issue_type.color}">
								{$currentIssue.issue_type.name}
							</Tag>
							<span class="issue-key">{$currentIssue.key}</span>
						</div>
						<div class="header-actions">
							{#if !isEditing}
								<Button kind="ghost" icon={Edit} on:click={startEdit}>
									Редактировать
								</Button>
							{/if}
							<Button kind="danger-ghost" icon={TrashCan} on:click={() => (showDeleteModal = true)}>
								Удалить
							</Button>
						</div>
					</div>

					{#if isEditing}
						<div class="edit-form">
							<TextInput bind:value={editForm.title} labelText="Название" size="xl" />
						</div>
					{:else}
						<h1>{$currentIssue.title}</h1>
					{/if}
				</header>

				<section class="issue-description">
					<h3>Описание</h3>
					{#if isEditing}
						<RichEditor
							value={editForm.description}
							placeholder="Опишите задачу..."
							onchange={(json) => (editForm.description = json)}
						/>
					{:else}
						<div class="description-content">
							<RichContent content={$currentIssue.description} />
						</div>
					{/if}
				</section>

				{#if isEditing}
					<div class="edit-actions">
						<Button kind="secondary" on:click={cancelEdit}>Отмена</Button>
						<Button on:click={saveEdit}>Сохранить</Button>
					</div>
				{/if}

				<!-- Subtasks Section -->
				{#if $currentIssue && ($currentIssue.children_count > 0 || !$currentIssue.issue_type.is_subtask)}
					<SubtasksList
						children={$issueChildren}
						childrenCount={$currentIssue.children_count}
						completedChildrenCount={$currentIssue.completed_children_count}
						{doneStatusId}
						onComplete={(childKey, statusId) => issue.quickCompleteChild(childKey, statusId)}
					/>
				{/if}

				<!-- Comments Section -->
				<section class="comments-section">
					<h3>Комментарии ({$issueComments.length})</h3>

					<div class="add-comment">
						<TextArea
							bind:value={newComment}
							placeholder="Добавить комментарий..."
							rows={2}
						/>
						<Button
							size="small"
							icon={Send}
							disabled={!newComment.trim() || isAddingComment}
							on:click={handleAddComment}
						>
							Отправить
						</Button>
					</div>

					<div class="comments-list">
						{#each $issueComments as comment (comment.id)}
							<div class="comment">
								<div class="comment-header">
									<span class="comment-author">
										{formatUserName(comment.author)}
									</span>
									<span class="comment-date">{formatDate(comment.created_at)}</span>
								</div>
								<p class="comment-content">{comment.content}</p>
							</div>
						{:else}
							<p class="no-comments">Комментариев пока нет</p>
						{/each}
					</div>
				</section>
			</main>

			<!-- Sidebar -->
			<aside class="issue-sidebar">
				<Tile>
					<h3>Статус</h3>
					<div class="status-block">
						<Tag
							type={$currentIssue.status.category === 'done' ? 'green' : $currentIssue.status.category === 'in_progress' ? 'blue' : 'gray'}
						>
							{$currentIssue.status.name}
						</Tag>

						{#if $issueTransitions.length > 0}
							<div class="transitions">
								{#each $issueTransitions as transition (transition.id)}
									<Button
										kind="tertiary"
										size="small"
										icon={ArrowRight}
										on:click={() => handleTransition(transition.to_status.id)}
									>
										{transition.name}
									</Button>
								{/each}
							</div>
						{/if}
					</div>
				</Tile>

				<Tile>
					<h3>Детали</h3>
					<div class="details-list">
						<div class="details-row">
							<span class="details-label">Приоритет</span>
							<div class="details-value">
								{#if isEditing}
									<Select bind:selected={editForm.priority} size="sm" hideLabel>
										{#each Object.entries(priorityLabels) as [value, label]}
											<SelectItem {value} text={label} />
										{/each}
									</Select>
								{:else}
									<span style="color: {priorityColors[$currentIssue.priority]}">
										{priorityLabels[$currentIssue.priority] || $currentIssue.priority}
									</span>
								{/if}
							</div>
						</div>

						<div class="details-row">
							<span class="details-label">Story Points</span>
							<div class="details-value">
								{#if isEditing}
									<TextInput
										bind:value={editForm.story_points}
										type="number"
										size="sm"
										hideLabel
									/>
								{:else}
									{$currentIssue.story_points ?? '—'}
								{/if}
							</div>
						</div>

						<div class="details-row">
							<span class="details-label">Исполнитель</span>
							<div class="details-value">
								{#if isEditing}
									<Dropdown
										size="sm"
										selectedId={editForm.assignee_id?.toString() ?? 'none'}
										items={memberItems}
										on:select={(e) => {
											editForm.assignee_id =
												e.detail.selectedId === 'none'
													? null
													: parseInt(e.detail.selectedId);
										}}
									/>
								{:else if $currentIssue.assignee}
									<span class="user-info">
										<User size={16} />
										{formatUserName($currentIssue.assignee)}
									</span>
								{:else}
									<span class="unassigned">Не назначен</span>
								{/if}
							</div>
						</div>

						<div class="details-row">
							<span class="details-label">Автор</span>
							<div class="details-value">
								<span class="user-info">
									<User size={16} />
									{formatUserName($currentIssue.reporter)}
								</span>
							</div>
						</div>

						<div class="details-row">
							<span class="details-label">Срок</span>
							<div class="details-value">
								{#if isEditing}
									<DatePicker
										datePickerType="single"
										dateFormat="d.m.Y"
										value={editForm.due_date ? new Date(editForm.due_date).toLocaleDateString('ru-RU') : ''}
										on:change={(e) => {
											const detail = e.detail;
											if (typeof detail === 'object' && detail !== null && 'dateStr' in detail) {
												const dateStr = detail.dateStr;
												if (typeof dateStr === 'string' && dateStr) {
													// Convert dd.mm.yyyy to yyyy-mm-dd
													const parts = dateStr.split('.');
													if (parts.length === 3) {
														editForm.due_date = `${parts[2]}-${parts[1]}-${parts[0]}`;
													}
												} else {
													editForm.due_date = null;
												}
											}
										}}
									>
										<DatePickerInput
											placeholder="дд.мм.гггг"
											size="sm"
										/>
									</DatePicker>
								{:else}
									<span class="date-info">
										<Calendar size={16} />
										{formatDateShort($currentIssue.due_date)}
									</span>
								{/if}
							</div>
						</div>

						<div class="details-row">
							<span class="details-label">Создана</span>
							<div class="details-value">{formatDate($currentIssue.created_at)}</div>
						</div>

						<div class="details-row">
							<span class="details-label">Обновлена</span>
							<div class="details-value">{formatDate($currentIssue.updated_at)}</div>
						</div>
					</div>
				</Tile>
			</aside>
		</div>
	</div>
{:else}
	<div class="not-found">
		<Tile>
			<h2>Задача не найдена</h2>
			<p>Задача с ключом "{issueKey}" не существует или у вас нет доступа.</p>
			<Button href="/projects">Вернуться к проектам</Button>
		</Tile>
	</div>
{/if}

<!-- Delete Confirmation Modal -->
<Modal
	danger
	bind:open={showDeleteModal}
	modalHeading="Удалить задачу"
	primaryButtonText="Удалить"
	secondaryButtonText="Отмена"
	primaryButtonDisabled={isDeleting}
	on:click:button--primary={handleDelete}
	on:click:button--secondary={() => (showDeleteModal = false)}
>
	<p>
		Вы уверены, что хотите удалить задачу <strong>{$currentIssue?.key}</strong>?
		Это действие нельзя отменить.
	</p>
</Modal>

<style>
	.loading-container,
	.error-container {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 50vh;
		padding: 2rem;
	}

	.issue-page {
		padding: 1rem 2rem;
		max-width: 1400px;
		margin: 0 auto;
	}

	.issue-layout {
		display: grid;
		grid-template-columns: 1fr 320px;
		gap: 2rem;
		margin-top: 1.5rem;
	}

	.issue-main {
		min-width: 0;
		max-width: 100%;
		overflow: hidden;
	}

	.issue-header {
		margin-bottom: 2rem;
	}

	.header-top {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.issue-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.issue-key {
		color: var(--cds-text-secondary);
		font-size: 0.875rem;
	}

	.header-actions {
		display: flex;
		gap: 0.5rem;
	}

	h1 {
		font-size: 1.75rem;
		font-weight: 600;
		margin: 0;
		line-height: 1.3;
	}

	h3 {
		font-size: 1rem;
		font-weight: 600;
		margin: 0 0 1rem;
	}

	.issue-description {
		margin-bottom: 2rem;
	}

	.description-content {
		background: var(--cds-field);
		border-radius: 4px;
		padding: 1rem;
		min-height: 100px;
	}

	/* RichEditor container constraints */
	.issue-description :global(.codex-editor) {
		max-width: 100%;
	}

	.issue-description :global(.ce-block__content) {
		max-width: 100%;
	}

	.issue-description :global(.ce-toolbar__content) {
		max-width: 100%;
	}

	.edit-form {
		margin-bottom: 1rem;
	}

	.edit-actions {
		display: flex;
		gap: 0.5rem;
		justify-content: flex-end;
		margin-bottom: 2rem;
	}

	.comments-section {
		border-top: 1px solid var(--cds-border-subtle);
		padding-top: 2rem;
	}

	.add-comment {
		display: flex;
		gap: 0.5rem;
		align-items: flex-end;
		margin-bottom: 1.5rem;
	}

	.add-comment :global(.bx--text-area-wrapper) {
		flex: 1;
	}

	.comments-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.comment {
		background: var(--cds-field);
		border-radius: 4px;
		padding: 1rem;
	}

	.comment-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.comment-author {
		font-weight: 500;
	}

	.comment-date {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}

	.comment-content {
		margin: 0;
		white-space: pre-wrap;
	}

	.no-comments {
		color: var(--cds-text-secondary);
		font-style: italic;
	}

	.issue-sidebar {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.issue-sidebar :global(.bx--tile) {
		padding: 1rem;
	}

	.status-block {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.transitions {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.user-info,
	.date-info {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.unassigned {
		color: var(--cds-text-secondary);
		font-style: italic;
	}

	/* Details list styling */
	.details-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.details-row {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.details-label {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
		font-weight: 500;
	}

	.details-value {
		font-size: 0.875rem;
		color: var(--cds-text-primary);
	}

	/* Form controls in sidebar */
	.issue-sidebar :global(.bx--dropdown),
	.issue-sidebar :global(.bx--select),
	.issue-sidebar :global(.bx--text-input-wrapper),
	.issue-sidebar :global(.bx--date-picker) {
		width: 100%;
	}

	.issue-sidebar :global(.bx--list-box__menu) {
		z-index: 9100;
	}

	/* Ensure Tile allows overflow for dropdowns */
	.issue-sidebar :global(.bx--tile) {
		overflow: visible;
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

	@media (max-width: 900px) {
		.issue-layout {
			grid-template-columns: 1fr;
		}

		.issue-sidebar {
			order: -1;
		}
	}
</style>
