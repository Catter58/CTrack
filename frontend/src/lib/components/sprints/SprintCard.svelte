<script lang="ts">
	import { Tile, Tag, ProgressBar, OverflowMenu, OverflowMenuItem } from 'carbon-components-svelte';
	import { Calendar } from 'carbon-icons-svelte';
	import type { Sprint, SprintWithStats } from '$lib/stores/sprints';

	interface Props {
		sprint: Sprint | SprintWithStats;
		onStart?: (sprint: Sprint) => void;
		onComplete?: (sprint: Sprint) => void;
		onEdit?: (sprint: Sprint) => void;
		onDelete?: (sprint: Sprint) => void;
		onClick?: (sprint: Sprint) => void;
	}

	let { sprint, onStart, onComplete, onEdit, onDelete, onClick }: Props = $props();

	const statusLabels: Record<string, string> = {
		planned: 'Запланирован',
		active: 'Активен',
		completed: 'Завершён'
	};

	const statusColors: Record<string, 'gray' | 'green' | 'blue'> = {
		planned: 'gray',
		active: 'green',
		completed: 'blue'
	};

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
		if (!('total_story_points' in sprint) || sprint.total_story_points === 0) {
			return 0;
		}
		const stats = sprint as SprintWithStats;
		return Math.round(
			((stats.total_story_points - stats.remaining_story_points) / stats.total_story_points) * 100
		);
	}

	const daysRemaining = $derived(getDaysRemaining());
	const progress = $derived(getProgress());
	const hasStats = $derived('total_story_points' in sprint);
</script>

<Tile
	class="sprint-card"
	on:click={() => onClick?.(sprint)}
	style="cursor: {onClick ? 'pointer' : 'default'}"
>
	<div class="sprint-header">
		<div class="sprint-title">
			<h4>{sprint.name}</h4>
			<Tag type={statusColors[sprint.status]} size="sm">
				{statusLabels[sprint.status]}
			</Tag>
		</div>
		<OverflowMenu flipped>
			{#if sprint.status === 'planned'}
				<OverflowMenuItem
					text="Запустить"
					on:click={(e) => {
						e.stopPropagation();
						onStart?.(sprint);
					}}
				/>
			{/if}
			{#if sprint.status === 'active'}
				<OverflowMenuItem
					text="Завершить"
					on:click={(e) => {
						e.stopPropagation();
						onComplete?.(sprint);
					}}
				/>
			{/if}
			<OverflowMenuItem
				text="Редактировать"
				on:click={(e) => {
					e.stopPropagation();
					onEdit?.(sprint);
				}}
			/>
			<OverflowMenuItem
				danger
				text="Удалить"
				on:click={(e) => {
					e.stopPropagation();
					onDelete?.(sprint);
				}}
			/>
		</OverflowMenu>
	</div>

	{#if sprint.goal}
		<p class="sprint-goal">{sprint.goal}</p>
	{/if}

	<div class="sprint-dates">
		<Calendar size={16} />
		<span>{formatDate(sprint.start_date)} — {formatDate(sprint.end_date)}</span>
		{#if sprint.status === 'active'}
			<Tag type={daysRemaining <= 2 ? 'red' : daysRemaining <= 5 ? 'magenta' : 'gray'} size="sm">
				{daysRemaining > 0 ? `${daysRemaining} дн.` : 'Просрочен'}
			</Tag>
		{/if}
	</div>

	{#if hasStats}
		{@const stats = sprint as SprintWithStats}
		<div class="sprint-stats">
			<ProgressBar value={progress} max={100} size="sm" />
			<div class="stats-row">
				<span>{stats.completed_issues} / {stats.total_issues} задач</span>
				<span>{stats.total_story_points - stats.remaining_story_points} / {stats.total_story_points} SP</span>
			</div>
		</div>
	{/if}
</Tile>

<style>
	:global(.sprint-card) {
		margin-bottom: 0.5rem;
	}

	.sprint-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 0.5rem;
	}

	.sprint-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.sprint-title h4 {
		margin: 0;
		font-size: 1rem;
		font-weight: 600;
	}

	.sprint-goal {
		color: var(--cds-text-secondary);
		font-size: 0.875rem;
		margin: 0 0 0.5rem 0;
	}

	.sprint-dates {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
		margin-bottom: 0.5rem;
	}

	.sprint-stats {
		margin-top: 0.75rem;
	}

	.stats-row {
		display: flex;
		justify-content: space-between;
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
		margin-top: 0.25rem;
	}
</style>
