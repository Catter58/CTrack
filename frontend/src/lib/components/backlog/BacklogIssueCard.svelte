<script lang="ts">
	import { Tag } from 'carbon-components-svelte';
	import { User, Calendar } from 'carbon-icons-svelte';
	import type { BacklogIssue } from '$lib/stores/backlog';

	interface Props {
		issue: BacklogIssue;
		draggable?: boolean;
		onDragStart?: (event: DragEvent, issue: BacklogIssue) => void;
		onDragEnd?: () => void;
		onUpdateStoryPoints?: (issueKey: string, storyPoints: number | null) => Promise<void>;
	}

	let { issue, draggable = true, onDragStart, onDragEnd, onUpdateStoryPoints }: Props = $props();

	let isEditingSP = $state(false);
	let editingSPValue = $state<number | null>(null);
	let spInputRef: HTMLInputElement | null = $state(null);

	const priorityColors: Record<string, string> = {
		highest: '#da1e28',
		high: '#ff832b',
		medium: '#f1c21b',
		low: '#0f62fe',
		lowest: '#6f6f6f'
	};

	const priorityLabels: Record<string, string> = {
		highest: 'Критический',
		high: 'Высокий',
		medium: 'Средний',
		low: 'Низкий',
		lowest: 'Минимальный'
	};

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

	function handleDragStart(event: DragEvent) {
		if (event.dataTransfer) {
			event.dataTransfer.effectAllowed = 'move';
			event.dataTransfer.setData('text/plain', issue.key);
			event.dataTransfer.setData('application/json', JSON.stringify(issue));
		}
		onDragStart?.(event, issue);
	}

	function handleSPClick(event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();
		if (!onUpdateStoryPoints) return;

		isEditingSP = true;
		editingSPValue = issue.story_points;

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
</script>

<a
	href="/issues/{issue.key}"
	class="issue-card"
	{draggable}
	ondragstart={handleDragStart}
	ondragend={onDragEnd}
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
			style="color: {priorityColors[issue.priority]}"
			title={priorityLabels[issue.priority]}
		>
			{priorityLabels[issue.priority]}
		</span>
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
		<span
			class="status"
			style="background-color: {issue.status.color}"
			title={issue.status.name}
		>
			{issue.status.name}
		</span>
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
		{#if issue.assignee}
			<span class="assignee" title={issue.assignee.full_name || issue.assignee.username}>
				<User size={16} />
				{issue.assignee.full_name?.split(' ')[0] || issue.assignee.username}
			</span>
		{/if}
	</div>
</a>

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

	.status {
		padding: 0.125rem 0.375rem;
		border-radius: 4px;
		font-size: 0.625rem;
		color: white;
		font-weight: 500;
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
</style>
