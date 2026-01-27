<script lang="ts">
	import { Tile, Tag, ProgressBar, Button } from 'carbon-components-svelte';
	import {
		Calendar,
		ChevronDown,
		ChevronUp,
		Task,
		IbmCloudDirectLink_2Dedicated as Epic,
		Checkmark,
		Debug,
		CircleFilled
	} from 'carbon-icons-svelte';
	import type { Sprint, SprintWithStats, SprintIssue } from '$lib/stores/sprints';
	import type { ComponentType } from 'svelte';

	const issueTypeIcons: Record<string, ComponentType> = {
		task: Task,
		story: CircleFilled,
		epic: Epic,
		bug: Debug,
		subtask: Checkmark
	};

	interface Props {
		sprint: Sprint | SprintWithStats;
		issues?: SprintIssue[];
		isDragOver?: boolean;
		spCapacityWarning?: number;
		onDrop?: (sprintId: string) => void;
		onDragOver?: (event: DragEvent) => void;
		onDragLeave?: () => void;
		onStart?: (sprint: Sprint) => void;
		onComplete?: (sprint: Sprint) => void;
	}

	let {
		sprint,
		issues = [],
		isDragOver = false,
		spCapacityWarning = 40,
		onDrop,
		onDragOver,
		onDragLeave,
		onStart,
		onComplete
	}: Props = $props();

	let isExpanded = $state(false);

	$effect(() => {
		if (sprint.status === 'active') {
			isExpanded = true;
		}
	});

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

	const totalSP = $derived(
		'total_story_points' in sprint
			? sprint.total_story_points
			: issues.reduce((sum, i) => sum + (i.story_points || 0), 0)
	);
	const isOverCapacity = $derived(totalSP > spCapacityWarning);
	const daysRemaining = $derived(getDaysRemaining());
	const progress = $derived(getProgress());
	const hasStats = $derived('total_story_points' in sprint);

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		onDrop?.(sprint.id);
	}

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		if (event.dataTransfer) {
			event.dataTransfer.dropEffect = 'move';
		}
		onDragOver?.(event);
	}
</script>

<Tile
	class="sprint-panel {isDragOver ? 'drag-over' : ''} {isOverCapacity ? 'over-capacity' : ''}"
	ondrop={handleDrop}
	ondragover={handleDragOver}
	ondragleave={onDragLeave}
	role="region"
	aria-label="Спринт {sprint.name}"
>
	<button
		class="sprint-header"
		onclick={() => (isExpanded = !isExpanded)}
		type="button"
	>
		<div class="sprint-title">
			{#if isExpanded}
				<ChevronUp size={16} />
			{:else}
				<ChevronDown size={16} />
			{/if}
			<h4>{sprint.name}</h4>
			<Tag type={statusColors[sprint.status]} size="sm">
				{statusLabels[sprint.status]}
			</Tag>
		</div>
		<div class="sprint-stats-header">
			<span class="sp-count" class:warning={isOverCapacity}>
				{totalSP} SP
				{#if isOverCapacity}
					(превышение!)
				{/if}
			</span>
			<span class="issue-count">{issues.length} задач</span>
		</div>
	</button>

	{#if sprint.status === 'active'}
		<div class="sprint-dates">
			<Calendar size={16} />
			<span>{formatDate(sprint.start_date)} — {formatDate(sprint.end_date)}</span>
			<Tag type={daysRemaining <= 2 ? 'red' : daysRemaining <= 5 ? 'magenta' : 'gray'} size="sm">
				{daysRemaining > 0 ? `${daysRemaining} дн.` : 'Просрочен'}
			</Tag>
		</div>
		{#if hasStats}
			<div class="sprint-progress">
				<ProgressBar value={progress} max={100} size="sm" />
			</div>
		{/if}
	{/if}

	{#if isExpanded}
		<div class="sprint-content">
			{#if sprint.goal}
				<p class="sprint-goal">{sprint.goal}</p>
			{/if}

			{#if sprint.status === 'planned'}
				<div class="sprint-dates compact">
					<Calendar size={16} />
					<span>{formatDate(sprint.start_date)} — {formatDate(sprint.end_date)}</span>
				</div>
			{/if}

			<div class="issues-list">
				{#if issues.length === 0}
					<div class="empty-sprint">
						<p>Перетащите задачи из бэклога</p>
					</div>
				{:else}
					{#each issues as issue (issue.id)}
						{@const IconComponent = issueTypeIcons[issue.issue_type.icon] || Task}
						<div class="mini-issue">
							<span class="issue-type-icon" style="color: {issue.issue_type.color}">
								<IconComponent size={16} />
							</span>
							<a href="/issues/{issue.key}" class="issue-link">
								<span class="issue-key">{issue.key}</span>
								<span class="issue-title">{issue.title}</span>
							</a>
							{#if issue.story_points}
								<Tag size="sm" type="outline">{issue.story_points}</Tag>
							{/if}
						</div>
					{/each}
				{/if}
			</div>

			{#if sprint.status === 'planned' && onStart}
				<div class="sprint-actions">
					<Button
						kind="primary"
						size="small"
						on:click={(e) => {
							e.stopPropagation();
							onStart(sprint);
						}}
					>
						Запустить спринт
					</Button>
				</div>
			{/if}

			{#if sprint.status === 'active' && onComplete}
				<div class="sprint-actions">
					<Button
						kind="danger-tertiary"
						size="small"
						on:click={(e) => {
							e.stopPropagation();
							onComplete(sprint);
						}}
					>
						Завершить спринт
					</Button>
				</div>
			{/if}
		</div>
	{/if}
</Tile>

<style>
	:global(.sprint-panel) {
		margin-bottom: 0.75rem;
		transition:
			box-shadow 0.15s ease,
			border-color 0.15s ease;
	}

	:global(.sprint-panel.drag-over) {
		box-shadow: inset 0 0 0 2px var(--cds-support-success);
		background: rgba(36, 161, 72, 0.1);
	}

	:global(.sprint-panel.over-capacity) {
		border-left: 3px solid var(--cds-support-warning);
	}

	.sprint-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		width: 100%;
		background: none;
		border: none;
		padding: 0;
		cursor: pointer;
		text-align: left;
		color: inherit;
	}

	.sprint-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.sprint-title h4 {
		margin: 0;
		font-size: 0.875rem;
		font-weight: 600;
	}

	.sprint-stats-header {
		display: flex;
		align-items: center;
		gap: 1rem;
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}

	.sp-count {
		font-weight: 600;
	}

	.sp-count.warning {
		color: var(--cds-support-warning);
	}

	.sprint-dates {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
		margin-top: 0.5rem;
	}

	.sprint-dates.compact {
		margin-top: 0.75rem;
	}

	.sprint-progress {
		margin-top: 0.5rem;
	}

	.sprint-content {
		margin-top: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid var(--cds-border-subtle);
	}

	.sprint-goal {
		color: var(--cds-text-secondary);
		font-size: 0.75rem;
		margin: 0 0 0.75rem 0;
		font-style: italic;
	}

	.issues-list {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		max-height: 200px;
		overflow-y: auto;
	}

	.empty-sprint {
		padding: 1rem;
		text-align: center;
		color: var(--cds-text-secondary);
		font-size: 0.75rem;
		border: 1px dashed var(--cds-border-subtle);
		border-radius: 4px;
	}

	.mini-issue {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.25rem 0.5rem;
		background: var(--cds-layer-accent);
		border-radius: 4px;
		font-size: 0.75rem;
	}

	.issue-type-icon {
		display: flex;
		align-items: center;
		flex-shrink: 0;
	}

	.issue-link {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex: 1;
		min-width: 0;
		text-decoration: none;
		color: inherit;
	}

	.issue-link:hover .issue-title {
		color: var(--cds-link-primary);
	}

	.issue-key {
		color: var(--cds-text-secondary);
		flex-shrink: 0;
	}

	.issue-title {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.sprint-actions {
		margin-top: 0.75rem;
		display: flex;
		justify-content: flex-end;
	}
</style>
