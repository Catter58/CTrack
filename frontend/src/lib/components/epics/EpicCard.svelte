<script lang="ts">
	import { Tag, ProgressBar } from 'carbon-components-svelte';
	import { Task, Checkmark } from 'carbon-icons-svelte';
	import type { Epic } from '$lib/stores/epics';

	interface Props {
		epic: Epic;
	}

	let { epic }: Props = $props();

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

	let progressPercent = $derived(
		epic.total_issues > 0
			? Math.round((epic.completed_issues / epic.total_issues) * 100)
			: 0
	);

	let spProgressPercent = $derived(
		epic.total_story_points > 0
			? Math.round((epic.completed_story_points / epic.total_story_points) * 100)
			: 0
	);

	let isCompleted = $derived(epic.status.category === 'done');
</script>

<a href="/issues/{epic.key}" class="epic-card" class:completed={isCompleted}>
	<div class="epic-header">
		<span class="epic-key">{epic.key}</span>
		<Tag
			size="sm"
			style="background-color: {epic.status.color}; color: white;"
		>
			{epic.status.name}
		</Tag>
	</div>

	<h3 class="epic-title">{epic.title}</h3>

	{#if epic.description}
		<p class="epic-description">{epic.description}</p>
	{/if}

	<div class="epic-progress">
		<div class="progress-header">
			<span class="progress-label">Прогресс</span>
			<span class="progress-value">{progressPercent}%</span>
		</div>
		<div class="progress-bar-wrapper">
			<ProgressBar
				value={progressPercent}
				max={100}
				size="sm"
				status={isCompleted ? 'finished' : 'active'}
			/>
		</div>
	</div>

	<div class="epic-stats">
		<div class="stat">
			<Task size={16} />
			<span>
				{epic.completed_issues} / {epic.total_issues} задач
			</span>
		</div>
		{#if epic.total_story_points > 0}
			<div class="stat">
				<Checkmark size={16} />
				<span>
					{epic.completed_story_points} / {epic.total_story_points} SP ({spProgressPercent}%)
				</span>
			</div>
		{/if}
	</div>

	<div class="epic-footer">
		<span
			class="priority"
			style="color: {getPriorityColor(epic.priority)}"
			title={getPriorityLabel(epic.priority)}
		>
			{getPriorityLabel(epic.priority)}
		</span>
	</div>
</a>

<style>
	.epic-card {
		display: block;
		background: var(--cds-field);
		border: 1px solid var(--cds-border-strong-01, #525252);
		border-left: 4px solid #7b68ee;
		border-radius: 6px;
		padding: 1rem;
		text-decoration: none;
		color: inherit;
		transition:
			transform 0.1s ease,
			box-shadow 0.1s ease,
			border-color 0.1s ease;
	}

	.epic-card:hover {
		border-color: var(--cds-interactive);
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
	}

	.epic-card.completed {
		border-left-color: var(--cds-support-success, #24a148);
		opacity: 0.8;
	}

	.epic-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.75rem;
	}

	.epic-key {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
		font-weight: 500;
	}

	.epic-title {
		font-size: 1rem;
		font-weight: 600;
		margin: 0 0 0.5rem;
		line-height: 1.4;
	}

	.epic-description {
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
		margin: 0 0 1rem;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.epic-progress {
		margin-bottom: 1rem;
	}

	.progress-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.25rem;
		font-size: 0.75rem;
	}

	.progress-label {
		color: var(--cds-text-secondary);
	}

	.progress-value {
		font-weight: 600;
	}

	.progress-bar-wrapper {
		height: 8px;
	}

	.progress-bar-wrapper :global(.bx--progress-bar) {
		height: 8px;
	}

	.epic-stats {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 0.75rem;
		font-size: 0.875rem;
	}

	.stat {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--cds-text-secondary);
	}

	.epic-footer {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 0.75rem;
	}

	.priority {
		font-weight: 500;
	}
</style>
