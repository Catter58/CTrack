<script lang="ts">
	import { DataTable, Tag, Link } from 'carbon-components-svelte';
	import { goto } from '$app/navigation';
	import type { Issue } from '$lib/stores/board';

	interface Assignee {
		id: number;
		username: string;
		full_name: string | null;
	}

	interface Props {
		issues: Issue[];
		members: Assignee[];
		onPriorityUpdate?: (issueKey: string, priority: string) => Promise<void>;
		onAssigneeUpdate?: (issueKey: string, assigneeId: number | null) => Promise<void>;
	}

	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	let { issues, members, onPriorityUpdate, onAssigneeUpdate }: Props = $props();

	const headers = [
		{ key: 'key', value: 'Ключ' },
		{ key: 'title', value: 'Название' },
		{ key: 'status', value: 'Статус' },
		{ key: 'priority', value: 'Приоритет' },
		{ key: 'assignee', value: 'Исполнитель' },
		{ key: 'story_points', value: 'SP' },
		{ key: 'due_date', value: 'Срок' }
	];

	const priorityLabels: Record<string, string> = {
		highest: 'Критический',
		high: 'Высокий',
		medium: 'Средний',
		low: 'Низкий',
		lowest: 'Минимальный'
	};

	const priorityColors: Record<string, string> = {
		highest: '#da1e28',
		high: '#ff832b',
		medium: '#f1c21b',
		low: '#0f62fe',
		lowest: '#6f6f6f'
	};

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('ru-RU', {
			day: 'numeric',
			month: 'short'
		});
	}

	function isOverdue(dateStr: string): boolean {
		const dueDate = new Date(dateStr);
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		return dueDate < today;
	}

	function isDueSoon(dateStr: string): boolean {
		const dueDate = new Date(dateStr);
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		const twoDaysFromNow = new Date(today);
		twoDaysFromNow.setDate(today.getDate() + 2);
		return dueDate >= today && dueDate <= twoDaysFromNow;
	}

	function getAssigneeName(assignee: { username: string; full_name: string | null } | null): string {
		if (!assignee) return '-';
		return assignee.full_name || assignee.username;
	}

	// Transform issues for DataTable rows
	let rows = $derived(
		issues.map((issue) => ({
			id: issue.id,
			key: issue.key,
			title: issue.title,
			status: issue.status.name,
			status_color: issue.status.color,
			priority: issue.priority,
			assignee: getAssigneeName(issue.assignee),
			story_points: issue.story_points,
			due_date: issue.due_date,
			issue_type: issue.issue_type,
			_original: issue
		}))
	);

	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	function handleRowClick(issueKey: string) {
		goto(`/issues/${issueKey}`);
	}
</script>

<div class="list-view-container">
	{#if issues.length === 0}
		<div class="empty-state">
			<p>Нет задач для отображения</p>
		</div>
	{:else}
		<DataTable sortable {headers} {rows} size="short">
			<svelte:fragment slot="cell" let:row let:cell>
				{#if cell.key === 'key'}
					<Link href="/issues/{row.key}">{cell.value}</Link>
				{:else if cell.key === 'title'}
					<div class="title-cell">
						<span
							class="type-icon"
							style="background-color: {row.issue_type.color}"
							title={row.issue_type.name}
						></span>
						<Link href="/issues/{row.key}">{cell.value}</Link>
					</div>
				{:else if cell.key === 'status'}
					<Tag size="sm" style="--tag-background-color: {row.status_color}">
						{cell.value}
					</Tag>
				{:else if cell.key === 'priority'}
					<div class="priority-cell">
						<span
							class="priority-dot"
							style="background-color: {priorityColors[cell.value] || '#6f6f6f'}"
						></span>
						<span>{priorityLabels[cell.value] || cell.value}</span>
					</div>
				{:else if cell.key === 'assignee'}
					<span class="assignee-cell">{cell.value}</span>
				{:else if cell.key === 'story_points'}
					{#if cell.value}
						<Tag size="sm" type="outline">{cell.value}</Tag>
					{:else}
						<span class="no-value">-</span>
					{/if}
				{:else if cell.key === 'due_date'}
					{#if cell.value}
						<span
							class="due-date"
							class:overdue={isOverdue(cell.value)}
							class:due-soon={isDueSoon(cell.value)}
						>
							{formatDate(cell.value)}
						</span>
					{:else}
						<span class="no-value">-</span>
					{/if}
				{:else}
					{cell.value}
				{/if}
			</svelte:fragment>
		</DataTable>
	{/if}
</div>

<style>
	.list-view-container {
		flex: 1;
		overflow: auto;
		padding: 1rem;
	}

	.empty-state {
		display: flex;
		justify-content: center;
		align-items: center;
		height: 200px;
		color: var(--cds-text-secondary);
	}

	.title-cell {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.type-icon {
		width: 12px;
		height: 12px;
		border-radius: 2px;
		flex-shrink: 0;
	}

	.priority-cell {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.priority-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.assignee-cell {
		color: var(--cds-text-secondary);
	}

	.no-value {
		color: var(--cds-text-disabled);
	}

	.due-date {
		color: var(--cds-text-secondary);
	}

	.due-date.overdue {
		color: var(--cds-support-error);
		font-weight: 500;
	}

	.due-date.due-soon {
		color: var(--cds-support-warning);
		font-weight: 500;
	}

	:global(.list-view-container .bx--data-table) {
		background: var(--cds-layer);
	}

	:global(.list-view-container .bx--data-table tbody tr) {
		cursor: pointer;
	}

	:global(.list-view-container .bx--data-table tbody tr:hover) {
		background: var(--cds-layer-hover);
	}

	:global(.list-view-container .bx--link) {
		color: var(--cds-link-primary);
	}

	:global(.list-view-container .bx--link:hover) {
		color: var(--cds-link-primary-hover);
	}
</style>
