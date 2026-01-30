<script lang="ts">
	import { page } from '$app/state';
	import { goto, afterNavigate } from '$app/navigation';
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
		Loading,
		Checkbox,
		MultiSelect
	} from 'carbon-components-svelte';
	import { Edit, TrashCan, Send, ArrowRight, Calendar, User, Link } from 'carbon-icons-svelte';
	import {
		issue,
		currentIssue,
		issueComments,
		issueTransitions,
		issueChildren,
		issueActivities,
		issueAttachments,
		issueLoading,
		issueError,
		priorityLabels,
		priorityColors
	} from '$lib/stores/issue';
	import { auth } from '$lib/stores/auth';
	import { projects, projectMembers } from '$lib/stores/projects';
	import { board, statuses } from '$lib/stores/board';
	import { events, type SSEEvent, type EditingEventData } from '$lib/stores/events';
	import api, { resolveMediaUrl } from '$lib/api/client';
	import RichEditor from '$lib/components/RichEditor.svelte';
	import RichContent from '$lib/components/RichContent.svelte';
	import { ActivityFeed, AttachmentsList, AttachmentUploader, SubtasksList } from '$lib/components/issues';

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

	// Editor info type
	interface Editor {
		user_id: number;
		username: string;
		full_name: string;
		avatar_url: string | null;
	}

	// Reactive issue key from URL params
	const issueKey = $derived(page.params.key!);

	// Track the key we're currently loading to prevent double loads
	let loadingKey = $state<string | null>(null);
	let hasAttemptedLoad = $state(false);

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

	// Custom fields
	let customFieldDefinitions = $state<CustomFieldDefinition[]>([]);
	let customFieldsForm = $state<Record<string, unknown>>({});

	// Comment
	let newComment = $state('');
	let isAddingComment = $state(false);

	// Comment edit/delete state
	let editingCommentId = $state<string | null>(null);
	let editingCommentContent = $state('');
	let isSavingComment = $state(false);
	let deletingCommentId = $state<string | null>(null);
	let isDeletingComment = $state(false);

	// Delete modal
	let showDeleteModal = $state(false);
	let isDeleting = $state(false);

	// Create subtask modal
	let showSubtaskModal = $state(false);
	let newSubtaskTitle = $state('');
	let isCreatingSubtask = $state(false);

	// Editing indicator state
	let otherEditors = $state<Editor[]>([]);
	let editingHeartbeatInterval: ReturnType<typeof setInterval> | null = null;
	let unsubscribeEditing: (() => void) | null = null;

	// Get done status for quick-complete
	let doneStatusId = $derived(
		$statuses.find((s) => s.category === 'done')?.id ?? null
	);

	// Load custom field definitions for the issue type
	async function loadCustomFieldDefinitions(projectKey: string, issueTypeId: string) {
		try {
			const definitions = await api.get<CustomFieldDefinition[]>(
				`/api/projects/${projectKey}/custom-fields/for-type/${issueTypeId}`
			);
			customFieldDefinitions = definitions;
		} catch (err) {
			console.error('Failed to load custom field definitions:', err);
			customFieldDefinitions = [];
		}
	}

	// Load current editing status
	async function loadEditingStatus(key: string) {
		try {
			const response = await api.get<{ is_editing: boolean; editors: Editor[] }>(
				`/api/issues/${key}/editing`
			);
			// Filter out current user from other editors
			otherEditors = response.editors.filter((e) => e.user_id !== $auth.user?.id);
		} catch (err) {
			console.error('Failed to load editing status:', err);
		}
	}

	// Start editing session
	async function startEditingSession() {
		try {
			await api.post(`/api/issues/${issueKey}/editing`);
		} catch (err) {
			console.error('Failed to start editing session:', err);
		}
	}

	// Stop editing session
	async function stopEditingSession() {
		try {
			await api.delete(`/api/issues/${issueKey}/editing`);
		} catch (err) {
			console.error('Failed to stop editing session:', err);
		}
	}

	// Handle editing SSE events
	function handleEditingEvent(event: SSEEvent) {
		const data = event.data as EditingEventData | undefined;
		if (!data || data.issue_key !== issueKey) return;

		// Skip events from current user
		if (data.user_id === $auth.user?.id) return;

		if (data.is_editing) {
			// Add editor if not already in list
			const exists = otherEditors.some((e) => e.user_id === data.user_id);
			if (!exists) {
				otherEditors = [
					...otherEditors,
					{
						user_id: data.user_id,
						username: data.username,
						full_name: data.full_name,
						avatar_url: data.avatar_url
					}
				];
			}
		} else {
			// Remove editor from list
			otherEditors = otherEditors.filter((e) => e.user_id !== data.user_id);
		}
	}

	// Load issue data
	async function loadIssueData(key: string) {
		// Skip if already loading this key
		if (loadingKey === key && hasAttemptedLoad) return;

		loadingKey = key;
		hasAttemptedLoad = false;

		const projectKey = key?.split('-')[0];
		const loadedIssue = await issue.load(key);

		await Promise.all([
			issue.loadComments(key),
			issue.loadTransitions(key),
			issue.loadChildren(key),
			issue.loadActivities(key),
			issue.loadAttachments(key),
			projectKey ? projects.loadMembers(projectKey) : Promise.resolve(),
			projectKey ? board.loadStatuses(projectKey) : Promise.resolve(),
			loadedIssue && projectKey
				? loadCustomFieldDefinitions(projectKey, loadedIssue.issue_type.id)
				: Promise.resolve(),
			loadEditingStatus(key)
		]);

		hasAttemptedLoad = true;
	}

	// Use afterNavigate for reliable cross-browser navigation handling
	afterNavigate(() => {
		const key = page.params.key;
		if (key) {
			loadIssueData(key);
		}
	});

	onMount(() => {
		// Subscribe to editing events
		unsubscribeEditing = events.on('issue.editing', handleEditingEvent);

		// Initial load on mount
		const key = page.params.key;
		if (key) {
			loadIssueData(key);
		}
	});

	onDestroy(() => {
		// Stop editing session if we were editing
		if (isEditing) {
			stopEditingSession();
		}

		// Clear heartbeat interval
		if (editingHeartbeatInterval) {
			clearInterval(editingHeartbeatInterval);
			editingHeartbeatInterval = null;
		}

		// Unsubscribe from editing events
		if (unsubscribeEditing) {
			unsubscribeEditing();
			unsubscribeEditing = null;
		}

		// Reset loading state for next navigation
		loadingKey = null;
		hasAttemptedLoad = false;

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
			// Initialize custom fields form with current values
			customFieldsForm = { ...$currentIssue.custom_fields };
			isEditing = true;

			// Start editing session and heartbeat
			startEditingSession();
			editingHeartbeatInterval = setInterval(() => {
				startEditingSession(); // Refresh TTL every 30 seconds
			}, 30000);
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
			due_date: editForm.due_date,
			custom_fields: customFieldsForm
		});

		if (result) {
			isEditing = false;
			// Stop editing session
			stopEditingSession();
			if (editingHeartbeatInterval) {
				clearInterval(editingHeartbeatInterval);
				editingHeartbeatInterval = null;
			}
		}
	}

	function cancelEdit() {
		isEditing = false;
		// Stop editing session
		stopEditingSession();
		if (editingHeartbeatInterval) {
			clearInterval(editingHeartbeatInterval);
			editingHeartbeatInterval = null;
		}
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

	function startEditComment(commentId: string, content: string) {
		editingCommentId = commentId;
		editingCommentContent = content;
	}

	function cancelEditComment() {
		editingCommentId = null;
		editingCommentContent = '';
	}

	async function saveEditComment() {
		if (!editingCommentId || !editingCommentContent.trim()) return;

		isSavingComment = true;
		const result = await issue.updateComment(editingCommentId, editingCommentContent.trim());
		if (result) {
			editingCommentId = null;
			editingCommentContent = '';
		}
		isSavingComment = false;
	}

	function confirmDeleteComment(commentId: string) {
		deletingCommentId = commentId;
	}

	function cancelDeleteComment() {
		deletingCommentId = null;
	}

	async function handleDeleteComment() {
		if (!deletingCommentId) return;

		isDeletingComment = true;
		await issue.deleteComment(deletingCommentId);
		deletingCommentId = null;
		isDeletingComment = false;
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

	async function handleCreateSubtask() {
		if (!$currentIssue || !newSubtaskTitle.trim()) return;

		isCreatingSubtask = true;
		try {
			const projectKey = issueKey.split('-')[0];
			// Find subtask type for this project
			const issueTypes = await api.get<Array<{ id: string; name: string; is_subtask: boolean }>>(
				`/api/projects/${projectKey}/issue-types`
			);
			const subtaskType = issueTypes.find((t) => t.is_subtask);

			if (!subtaskType) {
				console.error('No subtask type found for project');
				return;
			}

			await api.post(`/api/projects/${projectKey}/issues`, {
				title: newSubtaskTitle.trim(),
				issue_type_id: subtaskType.id,
				parent_id: $currentIssue.id,
				priority: 'medium'
			});

			// Reload issue to get updated children
			await issue.load(issueKey);
			newSubtaskTitle = '';
			showSubtaskModal = false;
		} catch (err) {
			console.error('Failed to create subtask:', err);
		} finally {
			isCreatingSubtask = false;
		}
	}

	function openSubtaskModal() {
		showSubtaskModal = true;
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

	// Custom field display helpers
	function getCustomFieldDisplayValue(field: CustomFieldDefinition, value: unknown): string {
		if (value === null || value === undefined || value === '') {
			switch (field.field_type) {
				case 'text':
				case 'textarea':
					return 'Не указано';
				case 'select':
				case 'multiselect':
					return 'Не выбрано';
				case 'number':
				case 'date':
				case 'url':
					return '—';
				case 'checkbox':
					return '';
				default:
					return '—';
			}
		}

		switch (field.field_type) {
			case 'date':
				return formatDateShort(value as string);
			case 'multiselect':
				return Array.isArray(value) ? value.join(', ') : String(value);
			case 'checkbox':
				return '';
			default:
				return String(value);
		}
	}

	function isValidUrl(value: unknown): boolean {
		if (typeof value !== 'string' || !value) return false;
		try {
			new URL(value);
			return true;
		} catch {
			return false;
		}
	}

	function handleCustomFieldInput(fieldKey: string, event: Event) {
		const target = event.target as HTMLInputElement | HTMLTextAreaElement;
		customFieldsForm[fieldKey] = target.value;
	}

	function handleCustomFieldNumberInput(fieldKey: string, event: Event) {
		const target = event.target as HTMLInputElement;
		const val = target.value;
		customFieldsForm[fieldKey] = val ? parseFloat(val) : null;
	}
</script>

<svelte:head>
	<title>{$currentIssue?.key || issueKey} - CTrack</title>
</svelte:head>

{#if $issueLoading || !hasAttemptedLoad}
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
					{#if otherEditors.length > 0}
						<div class="editing-indicator">
							<div class="editing-avatars">
								{#each otherEditors as editor (editor.user_id)}
									<div class="editing-avatar" title={editor.full_name}>
										{#if editor.avatar_url}
											<img src={resolveMediaUrl(editor.avatar_url)} alt={editor.full_name} />
										{:else}
											<span class="avatar-placeholder">
												{editor.full_name.charAt(0).toUpperCase()}
											</span>
										{/if}
									</div>
								{/each}
							</div>
							<span class="editing-text">
								{#if otherEditors.length === 1}
									{otherEditors[0].full_name} редактирует задачу
								{:else}
									{otherEditors.length} пользователей редактируют задачу
								{/if}
							</span>
						</div>
					{/if}

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

				<!-- Attachments Section -->
				<section class="attachments-section">
					<h3>Вложения ({$issueAttachments.length})</h3>
					<AttachmentUploader
						onUpload={(file) => issue.uploadAttachment(issueKey, file)}
					/>
					<AttachmentsList
						attachments={$issueAttachments}
						onDelete={(id) => issue.deleteAttachment(id)}
						canDelete={(attachment) => $auth.user?.id === attachment.uploaded_by.id}
					/>
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
						onAddSubtask={openSubtaskModal}
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
									<div class="comment-meta">
										<span class="comment-author">
											{formatUserName(comment.author)}
										</span>
										<span class="comment-date">{formatDate(comment.created_at)}</span>
									</div>
									{#if $auth.user?.id === comment.author.id && editingCommentId !== comment.id}
										<div class="comment-actions">
											<Button
												kind="ghost"
												size="small"
												icon={Edit}
												iconDescription="Редактировать"
												on:click={() => startEditComment(comment.id, comment.content)}
											/>
											<Button
												kind="danger-ghost"
												size="small"
												icon={TrashCan}
												iconDescription="Удалить"
												on:click={() => confirmDeleteComment(comment.id)}
											/>
										</div>
									{/if}
								</div>
								{#if editingCommentId === comment.id}
									<div class="comment-edit">
										<TextArea
											bind:value={editingCommentContent}
											rows={3}
											disabled={isSavingComment}
										/>
										<div class="comment-edit-actions">
											<Button
												kind="secondary"
												size="small"
												on:click={cancelEditComment}
												disabled={isSavingComment}
											>
												Отмена
											</Button>
											<Button
												size="small"
												on:click={saveEditComment}
												disabled={!editingCommentContent.trim() || isSavingComment}
											>
												Сохранить
											</Button>
										</div>
									</div>
								{:else if deletingCommentId === comment.id}
									<div class="comment-delete-confirm">
										<span>Удалить комментарий?</span>
										<div class="comment-delete-actions">
											<Button
												kind="secondary"
												size="small"
												on:click={cancelDeleteComment}
												disabled={isDeletingComment}
											>
												Отмена
											</Button>
											<Button
												kind="danger"
												size="small"
												on:click={handleDeleteComment}
												disabled={isDeletingComment}
											>
												Удалить
											</Button>
										</div>
									</div>
								{:else}
									<p class="comment-content">{comment.content}</p>
								{/if}
							</div>
						{:else}
							<p class="no-comments">Комментариев пока нет</p>
						{/each}
					</div>
				</section>

				<!-- Activity Feed Section -->
				<ActivityFeed activities={$issueActivities} />
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

				{#if $currentIssue.parent}
					<Tile class="parent-card">
						<h3>Родительская задача</h3>
						<a href="/issues/{$currentIssue.parent.key}" class="parent-link">
							<span class="parent-key">{$currentIssue.parent.key}</span>
							<span class="parent-title">{$currentIssue.parent.title}</span>
						</a>
						<div class="parent-details">
							<div class="parent-row">
								<span class="parent-label">Статус</span>
								<Tag
									size="sm"
									type={$currentIssue.parent.status.category === 'done' ? 'green' : $currentIssue.parent.status.category === 'in_progress' ? 'blue' : 'gray'}
								>
									{$currentIssue.parent.status.name}
								</Tag>
							</div>
							{#if $currentIssue.parent.due_date}
								<div class="parent-row">
									<span class="parent-label">Срок</span>
									<span class="parent-value">{formatDateShort($currentIssue.parent.due_date)}</span>
								</div>
							{/if}
							{#if $currentIssue.parent.assignee}
								<div class="parent-row">
									<span class="parent-label">Исполнитель</span>
									<span class="parent-value">{formatUserName($currentIssue.parent.assignee)}</span>
								</div>
							{/if}
						</div>
					</Tile>
				{/if}

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

				{#if customFieldDefinitions.length > 0}
					<Tile>
						<h3>Кастомные поля</h3>
						<div class="details-list">
							{#each customFieldDefinitions as field (field.id)}
								{@const fieldValue = $currentIssue.custom_fields[field.field_key]}
								{@const editValue = customFieldsForm[field.field_key]}
								<div class="details-row">
									<span class="details-label">{field.name}</span>
									<div class="details-value">
										{#if isEditing}
											{#if field.field_type === 'text'}
												<TextInput
													value={editValue as string ?? ''}
													size="sm"
													hideLabel
													on:input={(e) => handleCustomFieldInput(field.field_key, e)}
												/>
											{:else if field.field_type === 'textarea'}
												<TextArea
													value={editValue as string ?? ''}
													rows={2}
													hideLabel
													on:input={(e) => handleCustomFieldInput(field.field_key, e)}
												/>
											{:else if field.field_type === 'number'}
												<TextInput
													value={editValue as string ?? ''}
													type="number"
													size="sm"
													hideLabel
													on:input={(e) => handleCustomFieldNumberInput(field.field_key, e)}
												/>
											{:else if field.field_type === 'date'}
												<DatePicker
													datePickerType="single"
													dateFormat="d.m.Y"
													value={editValue ? new Date(editValue as string).toLocaleDateString('ru-RU') : ''}
													on:change={(e) => {
														const detail = e.detail;
														if (typeof detail === 'object' && detail !== null && 'dateStr' in detail) {
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
													<DatePickerInput placeholder="дд.мм.гггг" size="sm" />
												</DatePicker>
											{:else if field.field_type === 'select'}
												<Dropdown
													size="sm"
													selectedId={editValue as string ?? ''}
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
													size="sm"
													selectedIds={Array.isArray(editValue) ? editValue : []}
													items={field.options.map((opt) => ({ id: opt, text: opt }))}
													on:select={(e) => {
														customFieldsForm[field.field_key] = e.detail.selectedIds;
													}}
												/>
											{:else if field.field_type === 'checkbox'}
												<Checkbox
													checked={editValue === true}
													on:check={(e) => {
														customFieldsForm[field.field_key] = e.detail;
													}}
												/>
											{:else if field.field_type === 'url'}
												<TextInput
													value={editValue as string ?? ''}
													size="sm"
													hideLabel
													placeholder="https://..."
													on:input={(e) => handleCustomFieldInput(field.field_key, e)}
												/>
											{/if}
										{:else}
											{#if field.field_type === 'checkbox'}
												<Checkbox checked={fieldValue === true} disabled />
											{:else if field.field_type === 'url' && isValidUrl(fieldValue)}
												<a href={fieldValue as string} target="_blank" rel="noopener noreferrer" class="url-link">
													<Link size={16} />
													{fieldValue}
												</a>
											{:else}
												<span class={!fieldValue ? 'empty-value' : ''}>
													{getCustomFieldDisplayValue(field, fieldValue)}
												</span>
											{/if}
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</Tile>
				{/if}
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

<!-- Create Subtask Modal -->
<Modal
	bind:open={showSubtaskModal}
	modalHeading="Новая подзадача"
	primaryButtonText={isCreatingSubtask ? 'Создание...' : 'Создать'}
	secondaryButtonText="Отмена"
	primaryButtonDisabled={isCreatingSubtask || !newSubtaskTitle.trim()}
	on:click:button--primary={handleCreateSubtask}
	on:click:button--secondary={() => (showSubtaskModal = false)}
	on:close={() => (showSubtaskModal = false)}
>
	<TextInput
		bind:value={newSubtaskTitle}
		labelText="Название"
		placeholder="Что нужно сделать?"
		disabled={isCreatingSubtask}
	/>
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

	.editing-indicator {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		background: var(--cds-support-warning-inverse);
		border-radius: 4px;
		margin-bottom: 1rem;
	}

	.editing-avatars {
		display: flex;
		align-items: center;
	}

	.editing-avatar {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		overflow: hidden;
		border: 2px solid var(--cds-layer);
		margin-left: -8px;
	}

	.editing-avatar:first-child {
		margin-left: 0;
	}

	.editing-avatar img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.avatar-placeholder {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		height: 100%;
		background: var(--cds-interactive);
		color: var(--cds-text-on-color);
		font-size: 0.75rem;
		font-weight: 600;
	}

	.editing-text {
		font-size: 0.875rem;
		color: var(--cds-text-primary);
		font-weight: 500;
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

	.attachments-section {
		margin-bottom: 2rem;
	}

	.attachments-section h3 {
		margin-bottom: 1rem;
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
		align-items: flex-start;
		margin-bottom: 0.5rem;
		gap: 0.5rem;
	}

	.comment-meta {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.comment-author {
		font-weight: 500;
	}

	.comment-date {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}

	.comment-actions {
		display: flex;
		gap: 0.25rem;
		flex-shrink: 0;
	}

	.comment-actions :global(.bx--btn--ghost) {
		min-height: 1.5rem;
		padding: 0.25rem;
	}

	.comment-content {
		margin: 0;
		white-space: pre-wrap;
	}

	.comment-edit {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.comment-edit-actions {
		display: flex;
		gap: 0.5rem;
		justify-content: flex-end;
	}

	.comment-delete-confirm {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 0.5rem;
		background: var(--cds-layer-02);
		border-radius: 4px;
	}

	.comment-delete-confirm span {
		color: var(--cds-text-secondary);
		font-size: 0.875rem;
	}

	.comment-delete-actions {
		display: flex;
		gap: 0.5rem;
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

	/* Parent task card */
	:global(.parent-card) {
		background: var(--cds-layer-accent) !important;
		border-left: 3px solid var(--cds-border-interactive);
	}

	.parent-link {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		text-decoration: none;
		color: inherit;
		margin-bottom: 0.75rem;
	}

	.parent-link:hover {
		text-decoration: underline;
	}

	.parent-key {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
		font-weight: 500;
	}

	.parent-title {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--cds-text-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.parent-details {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.parent-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.5rem;
	}

	.parent-label {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}

	.parent-value {
		font-size: 0.75rem;
		color: var(--cds-text-primary);
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

	/* Custom field styles */
	.empty-value {
		color: var(--cds-text-secondary);
		font-style: italic;
	}

	.url-link {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--cds-link-primary);
		text-decoration: none;
		word-break: break-all;
	}

	.url-link:hover {
		text-decoration: underline;
	}

	/* MultiSelect in sidebar */
	.issue-sidebar :global(.bx--multi-select),
	.issue-sidebar :global(.bx--text-area-wrapper) {
		width: 100%;
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
