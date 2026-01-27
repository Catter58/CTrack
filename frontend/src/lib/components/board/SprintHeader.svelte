<script lang="ts">
	import { Tag, ProgressBar } from 'carbon-components-svelte';
	import { Calendar, Timer } from 'carbon-icons-svelte';
	import type { SprintWithStats } from '$lib/stores/sprints';

	interface Props {
		sprint: SprintWithStats;
	}

	let { sprint }: Props = $props();

	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString('ru-RU', {
			day: 'numeric',
			month: 'short'
		});
	}

	function getDaysRemaining(): number {
		const today = new Date();
		const endDate = new Date(sprint.end_date);
		const diff = endDate.getTime() - today.getTime();
		return Math.ceil(diff / (1000 * 60 * 60 * 24));
	}

	function getProgress(): number {
		if (sprint.total_story_points === 0) return 0;
		return Math.round(
			((sprint.total_story_points - sprint.remaining_story_points) / sprint.total_story_points) *
				100
		);
	}

	const daysRemaining = $derived(getDaysRemaining());
	const progress = $derived(getProgress());
	const completedSP = $derived(sprint.total_story_points - sprint.remaining_story_points);
</script>

<div class="sprint-header">
	<div class="sprint-info">
		<div class="sprint-name">
			<h2>{sprint.name}</h2>
			<Tag type={sprint.status === 'active' ? 'green' : 'gray'} size="sm">
				{sprint.status === 'active' ? 'Активен' : 'Завершён'}
			</Tag>
		</div>

		{#if sprint.goal}
			<p class="sprint-goal">{sprint.goal}</p>
		{/if}
	</div>

	<div class="sprint-stats">
		<div class="stat-item">
			<Calendar size={16} />
			<span>{formatDate(sprint.start_date)} — {formatDate(sprint.end_date)}</span>
		</div>

		{#if sprint.status === 'active'}
			<div class="stat-item">
				<Timer size={16} />
				<Tag type={daysRemaining <= 2 ? 'red' : daysRemaining <= 5 ? 'magenta' : 'gray'} size="sm">
					{daysRemaining > 0 ? `${daysRemaining} дн. осталось` : 'Просрочен'}
				</Tag>
			</div>
		{/if}

		<div class="stat-item stats-numbers">
			<span>{sprint.completed_issues} / {sprint.total_issues} задач</span>
			<span class="sp-stats">{completedSP} / {sprint.total_story_points} SP</span>
		</div>
	</div>

	<div class="progress-container">
		<ProgressBar value={progress} max={100} size="sm" />
		<span class="progress-label">{progress}%</span>
	</div>
</div>

<style>
	.sprint-header {
		background: var(--cds-layer);
		border: 1px solid var(--cds-border-subtle);
		border-radius: 8px;
		padding: 1rem 1.5rem;
		margin-bottom: 1rem;
	}

	.sprint-info {
		margin-bottom: 0.75rem;
	}

	.sprint-name {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.sprint-name h2 {
		margin: 0;
		font-size: 1.125rem;
		font-weight: 600;
	}

	.sprint-goal {
		margin: 0.25rem 0 0;
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
		font-style: italic;
	}

	.sprint-stats {
		display: flex;
		align-items: center;
		gap: 1.5rem;
		margin-bottom: 0.75rem;
	}

	.stat-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
	}

	.stats-numbers {
		margin-left: auto;
		gap: 1rem;
	}

	.sp-stats {
		font-weight: 500;
		color: var(--cds-text-primary);
	}

	.progress-container {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.progress-container :global(.bx--progress-bar) {
		flex: 1;
	}

	.progress-label {
		font-size: 0.75rem;
		font-weight: 500;
		color: var(--cds-text-secondary);
		min-width: 2.5rem;
		text-align: right;
	}
</style>
