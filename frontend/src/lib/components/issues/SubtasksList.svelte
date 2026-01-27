<script lang="ts">
	import { ProgressBar, Checkbox, Tag, Button, InlineLoading } from 'carbon-components-svelte';
	import { Add } from 'carbon-icons-svelte';
	import type { ChildIssue } from '$lib/stores/issue';

	interface Props {
		children: ChildIssue[];
		childrenCount: number;
		completedChildrenCount: number;
		doneStatusId: string | null;
		onAddSubtask?: () => void;
		onComplete?: (childKey: string, doneStatusId: string) => Promise<boolean>;
	}

	let {
		children,
		childrenCount,
		completedChildrenCount,
		doneStatusId,
		onAddSubtask,
		onComplete
	}: Props = $props();

	let completingKey = $state<string | null>(null);

	let progressPercent = $derived(
		childrenCount > 0 ? Math.round((completedChildrenCount / childrenCount) * 100) : 0
	);

	async function handleComplete(child: ChildIssue) {
		if (!doneStatusId || !onComplete || child.status.category === 'done') return;

		completingKey = child.key;
		try {
			await onComplete(child.key, doneStatusId);
		} finally {
			completingKey = null;
		}
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
</script>

<div class="subtasks-section">
	<div class="subtasks-header">
		<h3>Подзадачи ({completedChildrenCount}/{childrenCount})</h3>
		{#if onAddSubtask}
			<Button kind="ghost" size="small" icon={Add} on:click={onAddSubtask}>
				Добавить
			</Button>
		{/if}
	</div>

	{#if childrenCount > 0}
		<div class="progress-wrapper">
			<ProgressBar
				value={progressPercent}
				max={100}
				labelText="{progressPercent}% завершено"
				size="sm"
				status={progressPercent === 100 ? 'finished' : 'active'}
			/>
		</div>

		<div class="subtasks-list">
			{#each children as child (child.id)}
				<div class="subtask-item" class:completed={child.status.category === 'done'}>
					{#if completingKey === child.key}
						<InlineLoading description="Завершаем..." />
					{:else}
						<Checkbox
							checked={child.status.category === 'done'}
							disabled={child.status.category === 'done' || !doneStatusId}
							on:change={() => handleComplete(child)}
						/>
					{/if}
					<a href="/issues/{child.key}" class="subtask-link">
						<span class="subtask-type" style="color: {child.issue_type.color}">
							{child.issue_type.name}
						</span>
						<span class="subtask-key">{child.key}</span>
						<span class="subtask-title">{child.title}</span>
					</a>
					<div class="subtask-meta">
						<span class="priority" style="color: {getPriorityColor(child.priority)}">
							{child.priority}
						</span>
						<Tag
							size="sm"
							style="background-color: {child.status.color}; color: white;"
						>
							{child.status.name}
						</Tag>
						{#if child.story_points}
							<Tag size="sm" type="outline">{child.story_points} SP</Tag>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{:else}
		<p class="empty-message">Нет подзадач</p>
	{/if}
</div>

<style>
	.subtasks-section {
		margin-top: 1.5rem;
		padding: 1rem;
		background: var(--cds-field);
		border-radius: 6px;
	}

	.subtasks-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.75rem;
	}

	.subtasks-header h3 {
		margin: 0;
		font-size: 0.875rem;
		font-weight: 600;
	}

	.progress-wrapper {
		margin-bottom: 1rem;
	}

	.subtasks-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.subtask-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem;
		background: var(--cds-layer);
		border-radius: 4px;
		border: 1px solid var(--cds-border-subtle);
	}

	.subtask-item.completed {
		opacity: 0.7;
	}

	.subtask-item.completed .subtask-title {
		text-decoration: line-through;
	}

	.subtask-link {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex: 1;
		text-decoration: none;
		color: inherit;
		min-width: 0;
	}

	.subtask-link:hover {
		text-decoration: underline;
	}

	.subtask-type {
		font-size: 0.75rem;
		font-weight: 500;
	}

	.subtask-key {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
		flex-shrink: 0;
	}

	.subtask-title {
		font-size: 0.875rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.subtask-meta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-shrink: 0;
	}

	.priority {
		font-size: 0.75rem;
		font-weight: 500;
		text-transform: capitalize;
	}

	.empty-message {
		color: var(--cds-text-secondary);
		font-size: 0.875rem;
		text-align: center;
		padding: 1rem;
	}
</style>
