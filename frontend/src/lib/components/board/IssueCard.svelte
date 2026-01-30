<script lang="ts">
	import { Tag, Portal } from 'carbon-components-svelte';
	import { Calendar, User, ChevronDown, Edit, UserFollow, Checkmark } from 'carbon-icons-svelte';
	import { goto } from '$app/navigation';
	import type { Issue } from '$lib/stores/board';
	import SwipeActions from '$lib/components/SwipeActions.svelte';
	import LongPressMenu from '$lib/components/LongPressMenu.svelte';

	interface Assignee {
		id: number;
		username: string;
		full_name?: string | null;
	}

	interface Props {
		issue: Issue;
		isDragging?: boolean;
		onUpdateStoryPoints?: (issueKey: string, storyPoints: number | null) => Promise<void>;
		onUpdatePriority?: (issueKey: string, priority: string) => Promise<void>;
		onUpdateAssignee?: (issueKey: string, assigneeId: number | null) => Promise<void>;
		onQuickStatusChange?: (issueKey: string) => void;
		availableAssignees?: Assignee[];
		enableSwipe?: boolean;
		enableLongPress?: boolean;
	}

	let {
		issue,
		isDragging = false,
		onUpdateStoryPoints,
		onUpdatePriority,
		onUpdateAssignee,
		onQuickStatusChange,
		availableAssignees = [],
		enableSwipe = true,
		enableLongPress = true
	}: Props = $props();

	let isEditingSP = $state(false);
	let editingSPValue = $state<number | null>(null);
	let spInputRef: HTMLInputElement | null = $state(null);
	let showPriorityMenu = $state(false);
	let showAssigneeMenu = $state(false);

	// Refs for dropdown positioning
	let priorityTriggerRef: HTMLElement | null = $state(null);
	let assigneeTriggerRef: HTMLElement | null = $state(null);

	// Dropdown positions (for fixed positioning)
	let priorityMenuStyle = $state('');
	let assigneeMenuStyle = $state('');

	const priorities = [
		{ value: 'highest', label: 'Критический', color: '#da1e28' },
		{ value: 'high', label: 'Высокий', color: '#ff832b' },
		{ value: 'medium', label: 'Средний', color: '#f1c21b' },
		{ value: 'low', label: 'Низкий', color: '#0f62fe' },
		{ value: 'lowest', label: 'Минимальный', color: '#6f6f6f' }
	];

	// Swipe actions configuration
	const swipeLeftActions = $derived(
		onUpdateAssignee
			? [
					{
						id: 'assign',
						label: 'Назначить',
						icon: UserFollow,
						color: '#ffffff',
						backgroundColor: '#0f62fe'
					}
				]
			: []
	);

	const swipeRightActions = $derived(
		onQuickStatusChange
			? [
					{
						id: 'status',
						label: 'Статус',
						icon: Checkmark,
						color: '#ffffff',
						backgroundColor: '#24a148'
					}
				]
			: []
	);

	// Long press menu items
	const longPressMenuItems = $derived(() => {
		const items: {
			id: string;
			label: string;
			icon?: typeof Edit;
			danger?: boolean;
			disabled?: boolean;
		}[] = [{ id: 'open', label: 'Открыть задачу', icon: Edit }];

		if (onUpdateAssignee) {
			if (issue.assignee) {
				items.push({ id: 'unassign', label: 'Снять исполнителя', icon: User });
			} else {
				items.push({ id: 'assign-self', label: 'Назначить на себя', icon: UserFollow });
			}
		}

		if (onQuickStatusChange) {
			items.push({ id: 'status', label: 'Изменить статус', icon: Checkmark });
		}

		return items;
	});

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

	function handleSPClick(event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();
		if (!onUpdateStoryPoints) return;

		isEditingSP = true;
		editingSPValue = issue.story_points;

		// Focus the input after it renders
		setTimeout(() => {
			spInputRef?.focus();
			spInputRef?.select();
		}, 0);
	}

	async function handleSPSave() {
		if (!onUpdateStoryPoints) return;

		try {
			await onUpdateStoryPoints(issue.key, editingSPValue);
		} catch (err) {
			console.error('Failed to update story points:', err);
		}

		isEditingSP = false;
	}

	function handleSPKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			handleSPSave();
		} else if (event.key === 'Escape') {
			isEditingSP = false;
		}
	}

	function handleSPBlur() {
		handleSPSave();
	}

	function handleCardClick(event: MouseEvent) {
		// Don't navigate if clicking on dropdowns or inputs
		const target = event.target as HTMLElement;
		if (
			target.closest('.priority-container') ||
			target.closest('.assignee-container') ||
			target.closest('.sp-tag') ||
			target.closest('.sp-edit')
		) {
			return;
		}

		// Navigate to issue page
		goto(`/issues/${issue.key}`);
	}

	function handlePriorityClick(event: MouseEvent) {
		if (!onUpdatePriority) return;
		event.preventDefault();
		event.stopPropagation();
		showAssigneeMenu = false;

		if (!showPriorityMenu && priorityTriggerRef) {
			const rect = priorityTriggerRef.getBoundingClientRect();
			priorityMenuStyle = `top: ${rect.bottom + 4}px; left: ${rect.left}px;`;
		}
		showPriorityMenu = !showPriorityMenu;
	}

	async function handlePrioritySelect(priority: string, event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();
		showPriorityMenu = false;
		if (onUpdatePriority && priority !== issue.priority) {
			await onUpdatePriority(issue.key, priority);
		}
	}

	function handleAssigneeClick(event: MouseEvent) {
		if (!onUpdateAssignee) return;
		event.preventDefault();
		event.stopPropagation();
		showPriorityMenu = false;

		if (!showAssigneeMenu && assigneeTriggerRef) {
			const rect = assigneeTriggerRef.getBoundingClientRect();
			// Position to the right edge of the trigger
			assigneeMenuStyle = `top: ${rect.bottom + 4}px; right: ${window.innerWidth - rect.right}px;`;
		}
		showAssigneeMenu = !showAssigneeMenu;
	}

	async function handleAssigneeSelect(assigneeId: number | null, event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();
		showAssigneeMenu = false;
		if (onUpdateAssignee) {
			await onUpdateAssignee(issue.key, assigneeId);
		}
	}

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		// Don't close if clicking inside a dropdown or its trigger
		if (target.closest('.priority-container') || target.closest('.assignee-container')) {
			return;
		}
		showPriorityMenu = false;
		showAssigneeMenu = false;
	}

	// Swipe action handler
	function handleSwipeAction(actionId: string) {
		if (actionId === 'assign') {
			// Show assignee dropdown
			showAssigneeMenu = true;
		} else if (actionId === 'status') {
			onQuickStatusChange?.(issue.key);
		}
	}

	// Long press menu handler
	function handleLongPressSelect(itemId: string) {
		switch (itemId) {
			case 'open':
				goto(`/issues/${issue.key}`);
				break;
			case 'unassign':
				onUpdateAssignee?.(issue.key, null);
				break;
			case 'assign-self':
				// This would need current user ID - for now open assignee dropdown
				showAssigneeMenu = true;
				break;
			case 'status':
				onQuickStatusChange?.(issue.key);
				break;
		}
	}
</script>

<svelte:window onclick={handleClickOutside} />

<LongPressMenu
	items={enableLongPress ? longPressMenuItems() : []}
	onSelect={handleLongPressSelect}
	disabled={isDragging}
>
	<SwipeActions
		leftActions={enableSwipe ? swipeLeftActions : []}
		rightActions={enableSwipe ? swipeRightActions : []}
		onAction={handleSwipeAction}
		disabled={isDragging}
	>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="issue-card"
			class:is-dragging={isDragging}
			onclick={handleCardClick}
			onkeydown={(e) => e.key === 'Enter' && handleCardClick(e as unknown as MouseEvent)}
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
				{#if onUpdatePriority}
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div class="priority-container" onclick={handlePriorityClick}>
						<span
							class="priority clickable"
							style="color: {getPriorityColor(issue.priority)}"
							title="Клик для изменения приоритета"
							bind:this={priorityTriggerRef}
						>
							{getPriorityLabel(issue.priority)}
							<ChevronDown size={16} />
						</span>
					</div>
					{#if showPriorityMenu}
						<Portal>
							<div class="dropdown-menu dropdown-fixed" style={priorityMenuStyle}>
								{#each priorities as p}
									<!-- svelte-ignore a11y_click_events_have_key_events -->
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<div
										class="dropdown-item"
										class:selected={issue.priority === p.value}
										style="--item-color: {p.color}"
										onclick={(e) => handlePrioritySelect(p.value, e)}
									>
										<span class="priority-dot" style="background: {p.color}"></span>
										{p.label}
									</div>
								{/each}
							</div>
						</Portal>
					{/if}
				{:else}
					<span
						class="priority"
						style="color: {getPriorityColor(issue.priority)}"
						title={getPriorityLabel(issue.priority)}
					>
						{getPriorityLabel(issue.priority)}
					</span>
				{/if}
				{#if isEditingSP}
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div class="sp-edit" onclick={(e) => e.preventDefault()}>
						<input
							type="number"
							class="sp-input"
							bind:this={spInputRef}
							bind:value={editingSPValue}
							onkeydown={handleSPKeyDown}
							onblur={handleSPBlur}
							min="0"
							placeholder="SP"
						/>
					</div>
				{:else if onUpdateStoryPoints}
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<span class="sp-tag" onclick={handleSPClick} title="Клик для редактирования">
						<Tag size="sm" type="outline">{issue.story_points ?? '—'} SP</Tag>
					</span>
				{:else if issue.story_points}
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
						<Calendar size={16} />
						{formatDueDate(issue.due_date)}
					</span>
				{/if}
				{#if onUpdateAssignee}
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div class="assignee-container" onclick={handleAssigneeClick}>
						<span
							class="assignee clickable"
							title={issue.assignee
								? issue.assignee.full_name || issue.assignee.username
								: 'Назначить'}
							bind:this={assigneeTriggerRef}
						>
							<User size={16} />
							{#if issue.assignee}
								{issue.assignee.full_name?.split(' ')[0] || issue.assignee.username}
							{:else}
								<span class="unassigned">Назначить</span>
							{/if}
							<ChevronDown size={16} />
						</span>
					</div>
					{#if showAssigneeMenu}
						<Portal>
							<div class="dropdown-menu dropdown-fixed" style={assigneeMenuStyle}>
								<!-- svelte-ignore a11y_click_events_have_key_events -->
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<div
									class="dropdown-item"
									class:selected={!issue.assignee}
									onclick={(e) => handleAssigneeSelect(null, e)}
								>
									<User size={16} />
									<span class="unassigned">Не назначен</span>
								</div>
								{#each availableAssignees as assignee (assignee.id)}
									<!-- svelte-ignore a11y_click_events_have_key_events -->
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<div
										class="dropdown-item"
										class:selected={issue.assignee?.id === assignee.id}
										onclick={(e) => handleAssigneeSelect(assignee.id, e)}
									>
										<User size={16} />
										{assignee.full_name || assignee.username}
									</div>
								{/each}
							</div>
						</Portal>
					{/if}
				{:else if issue.assignee}
					<span class="assignee" title={issue.assignee.full_name || issue.assignee.username}>
						<User size={16} />
						{issue.assignee.full_name?.split(' ')[0] || issue.assignee.username}
					</span>
				{/if}
			</div>
		</div>
	</SwipeActions>
</LongPressMenu>

<style>
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
			box-shadow 0.15s ease,
			border-color 0.15s ease,
			opacity 0.15s ease;
	}

	.issue-card:hover {
		border-color: var(--cds-interactive);
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
	}

	.issue-card:active {
		cursor: grabbing;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
	}

	.issue-card.is-dragging {
		opacity: 0.5;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
		border-color: var(--cds-interactive);
		pointer-events: none;
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

	.sp-tag {
		cursor: pointer;
	}

	.sp-tag:hover :global(.bx--tag) {
		background: var(--cds-interactive);
		color: var(--cds-text-on-color);
	}

	.sp-edit {
		display: inline-flex;
	}

	.sp-input {
		width: 48px;
		height: 20px;
		padding: 0 4px;
		border: 1px solid var(--cds-interactive);
		border-radius: 4px;
		background: var(--cds-field);
		color: var(--cds-text-primary);
		font-size: 0.75rem;
		text-align: center;
	}

	.sp-input:focus {
		outline: none;
		border-color: var(--cds-focus);
		box-shadow: 0 0 0 1px var(--cds-focus);
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

	.priority-container,
	.assignee-container {
		position: relative;
	}

	.priority.clickable,
	.assignee.clickable {
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.125rem 0.25rem;
		border-radius: 4px;
		transition: background 0.1s ease;
	}

	.priority.clickable:hover,
	.assignee.clickable:hover {
		background: var(--cds-layer-hover);
	}

	/* Dropdown styles - global because they render in Portal */
	:global(.dropdown-menu.dropdown-fixed) {
		min-width: 160px;
		background: #262626;
		border: 1px solid #525252;
		border-radius: 4px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
		color: #f4f4f4;
		position: fixed;
		z-index: 10000;
	}

	:global(.dropdown-menu .dropdown-item) {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.75rem;
		font-size: 0.875rem;
		cursor: pointer;
		transition: background 0.1s ease;
		color: #f4f4f4;
		white-space: nowrap;
	}

	:global(.dropdown-menu .dropdown-item:hover) {
		background: #393939;
	}

	:global(.dropdown-menu .dropdown-item.selected) {
		background: #4c4c4c;
		font-weight: 600;
	}

	:global(.dropdown-menu .priority-dot) {
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}

	:global(.dropdown-menu .dropdown-item svg) {
		flex-shrink: 0;
		color: var(--cds-text-secondary);
	}

	:global(.dropdown-menu .unassigned) {
		color: var(--cds-text-secondary);
		font-style: italic;
	}

	.unassigned {
		color: var(--cds-text-secondary);
		font-style: italic;
	}
</style>
