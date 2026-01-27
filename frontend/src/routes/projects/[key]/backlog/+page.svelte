<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { get } from 'svelte/store';
	import { page } from '$app/stores';
	import {
		Button,
		Tile,
		Loading,
		InlineNotification,
		Tag
	} from 'carbon-components-svelte';
	import { ArrowLeft, Add } from 'carbon-icons-svelte';
	import { projects, currentProject, projectsLoading } from '$lib/stores/projects';
	import {
		sprints,
		type Sprint,
		type SprintIssue,
		type CreateSprintData,
		type UpdateSprintData
	} from '$lib/stores/sprints';
	import { backlog, backlogIssues, backlogLoading, backlogLoadingMore, backlogHasMore, backlogError, backlogStoryPoints, type BacklogIssue } from '$lib/stores/backlog';
	import { BacklogIssueCard, SprintPanel } from '$lib/components/backlog';
	import { SprintModal, SprintCompleteModal } from '$lib/components/sprints';
	import { toasts } from '$lib/stores/toast';

	const projectKey = $derived($page.params.key);

	let draggedIssue = $state<BacklogIssue | null>(null);
	let dragOverSprintId = $state<string | null>(null);

	let showCreateSprintModal = $state(false);
	let showCompleteModal = $state(false);
	let selectedSprint = $state<Sprint | null>(null);
	let incompleteCount = $state(0);

	let sprintIssuesMap = $state<Record<string, SprintIssue[]>>({});

	// Infinite scroll
	let loadMoreTrigger: HTMLDivElement | null = $state(null);
	let observer: IntersectionObserver | null = null;

	function setupInfiniteScroll() {
		if (!loadMoreTrigger) return;

		observer = new IntersectionObserver(
			(entries) => {
				const [entry] = entries;
				if (entry.isIntersecting && $backlogHasMore && !$backlogLoadingMore) {
					backlog.loadMore();
				}
			},
			{
				rootMargin: '100px',
				threshold: 0.1
			}
		);

		observer.observe(loadMoreTrigger);
	}

	$effect(() => {
		if (loadMoreTrigger) {
			setupInfiniteScroll();
		}
	});

	onDestroy(() => {
		if (observer) {
			observer.disconnect();
		}
	});

	onMount(async () => {
		const key = get(page).params.key!;
		await Promise.all([
			projects.loadProject(key),
			sprints.loadSprints(key),
			backlog.loadBacklog(key)
		]);

		// Load issues for active and planned sprints
		const sprintsList = get(sprints).sprints;
		for (const sprint of sprintsList) {
			if (sprint.status === 'active' || sprint.status === 'planned') {
				const issues = await sprints.loadSprintIssues(sprint.id);
				sprintIssuesMap[sprint.id] = issues;
			}
		}
	});

	const activeSprints = $derived(
		$sprints.sprints.filter((s) => s.status === 'active')
	);
	const plannedSprints = $derived(
		$sprints.sprints.filter((s) => s.status === 'planned')
	);

	function handleDragStart(event: DragEvent, issue: BacklogIssue) {
		draggedIssue = issue;
	}

	function handleDragEnd() {
		draggedIssue = null;
		dragOverSprintId = null;
	}

	function handleSprintDragOver(event: DragEvent, sprintId: string) {
		event.preventDefault();
		dragOverSprintId = sprintId;
	}

	function handleSprintDragLeave() {
		dragOverSprintId = null;
	}

	async function handleUpdateStoryPoints(issueKey: string, storyPoints: number | null) {
		try {
			await backlog.updateIssueStoryPoints(issueKey, storyPoints);
		} catch {
			toasts.error('Ошибка', 'Не удалось обновить Story Points');
		}
	}

	async function handleDropOnSprint(sprintId: string) {
		if (!draggedIssue) return;

		// Capture the issue before async operation
		const issue = draggedIssue;
		draggedIssue = null;
		dragOverSprintId = null;

		const sprint = [...activeSprints, ...plannedSprints].find((s) => s.id === sprintId);
		if (!sprint) return;

		try {
			await backlog.updateIssueSprint(issue.key, sprintId);

			// Add to sprint issues map
			const newIssue: SprintIssue = {
				id: issue.id,
				key: issue.key,
				title: issue.title,
				status: issue.status,
				issue_type: issue.issue_type,
				assignee: issue.assignee,
				story_points: issue.story_points,
				priority: issue.priority
			};

			sprintIssuesMap[sprintId] = [...(sprintIssuesMap[sprintId] || []), newIssue];

			toasts.success('Задача перемещена', `${issue.key} добавлена в ${sprint.name}`);
		} catch (err) {
			const message = err instanceof Error ? err.message : 'Ошибка перемещения';
			toasts.error('Ошибка', message);
		}
	}

	async function handleCreateSprint(data: CreateSprintData | UpdateSprintData) {
		if (!projectKey) return;
		const sprint = await sprints.createSprint(projectKey, data as CreateSprintData);
		if (sprint) {
			sprintIssuesMap[sprint.id] = [];
			toasts.success('Спринт создан');
		}
	}

	async function handleStartSprint(sprint: Sprint) {
		const result = await sprints.startSprint(sprint.id);
		if (result) {
			toasts.success('Спринт запущен');
		}
	}

	async function handleOpenCompleteModal(sprint: Sprint) {
		selectedSprint = sprint;
		const issues = sprintIssuesMap[sprint.id] || [];
		incompleteCount = issues.filter((i) => i.status.category !== 'done').length;
		showCompleteModal = true;
	}

	async function handleCompleteSprint(moveIncompleteTo: string | null) {
		if (!selectedSprint || !projectKey) return;

		const result = await sprints.completeSprint(selectedSprint.id, moveIncompleteTo);
		if (result) {
			// Reload backlog to get moved issues
			await backlog.loadBacklog(projectKey);
			toasts.success('Спринт завершён');
		}
	}

	function getSprintIssues(sprintId: string): SprintIssue[] {
		return sprintIssuesMap[sprintId] || [];
	}
</script>

<svelte:head>
	<title>Бэклог — {$currentProject?.name || 'Проект'}</title>
</svelte:head>

<div class="backlog-page">
	<header class="page-header">
		<div class="header-left">
			<Button
				kind="ghost"
				size="small"
				icon={ArrowLeft}
				href="/projects/{projectKey}"
			>
				Назад к доске
			</Button>
			<h1>Бэклог</h1>
		</div>
		<Button icon={Add} on:click={() => (showCreateSprintModal = true)}>
			Создать спринт
		</Button>
	</header>

	{#if $projectsLoading || $backlogLoading || $sprints.isLoading}
		<Loading />
	{:else if $backlogError}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={$backlogError}
			on:close={() => backlog.clearError()}
		/>
	{:else}
		<div class="backlog-container">
			<div class="backlog-column">
				<div class="column-header">
					<h2>Бэклог</h2>
					<div class="column-stats">
						<Tag size="sm">{$backlogIssues.length} задач</Tag>
						<Tag size="sm" type="outline">{$backlogStoryPoints} SP</Tag>
					</div>
				</div>

				<div class="backlog-list">
					{#if $backlogIssues.length === 0}
						<Tile class="empty-state">
							<p>Бэклог пуст</p>
							<p class="hint">Создайте задачи на доске проекта</p>
						</Tile>
					{:else}
						{#each $backlogIssues as issue (issue.id)}
							<BacklogIssueCard
								{issue}
								onDragStart={handleDragStart}
								onDragEnd={handleDragEnd}
								onUpdateStoryPoints={handleUpdateStoryPoints}
							/>
						{/each}

						<!-- Infinite scroll trigger -->
						{#if $backlogHasMore}
							<div
								bind:this={loadMoreTrigger}
								class="load-more-trigger"
							>
								{#if $backlogLoadingMore}
									<Loading small withOverlay={false} />
								{/if}
							</div>
						{/if}
					{/if}
				</div>
			</div>

			<div class="sprints-column">
				<div class="column-header">
					<h2>Спринты</h2>
				</div>

				<div class="sprints-list">
					{#if activeSprints.length > 0}
						<div class="sprints-section">
							<h3 class="section-title">Активные</h3>
							{#each activeSprints as sprint (sprint.id)}
								<SprintPanel
									{sprint}
									issues={getSprintIssues(sprint.id)}
									isDragOver={dragOverSprintId === sprint.id}
									onDrop={handleDropOnSprint}
									onDragOver={(e) => handleSprintDragOver(e, sprint.id)}
									onDragLeave={handleSprintDragLeave}
									onComplete={handleOpenCompleteModal}
								/>
							{/each}
						</div>
					{/if}

					{#if plannedSprints.length > 0}
						<div class="sprints-section">
							<h3 class="section-title">Запланированные</h3>
							{#each plannedSprints as sprint (sprint.id)}
								<SprintPanel
									{sprint}
									issues={getSprintIssues(sprint.id)}
									isDragOver={dragOverSprintId === sprint.id}
									onDrop={handleDropOnSprint}
									onDragOver={(e) => handleSprintDragOver(e, sprint.id)}
									onDragLeave={handleSprintDragLeave}
									onStart={handleStartSprint}
								/>
							{/each}
						</div>
					{/if}

					{#if activeSprints.length === 0 && plannedSprints.length === 0}
						<Tile class="empty-state">
							<p>Нет активных или запланированных спринтов</p>
							<Button
								kind="tertiary"
								size="small"
								on:click={() => (showCreateSprintModal = true)}
							>
								Создать спринт
							</Button>
						</Tile>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>

<SprintModal
	open={showCreateSprintModal}
	onClose={() => (showCreateSprintModal = false)}
	onSave={handleCreateSprint}
/>

{#if selectedSprint}
	<SprintCompleteModal
		open={showCompleteModal}
		sprint={selectedSprint}
		{plannedSprints}
		{incompleteCount}
		onClose={() => {
			showCompleteModal = false;
			selectedSprint = null;
		}}
		onComplete={handleCompleteSprint}
	/>
{/if}

<style>
	.backlog-page {
		padding: 1rem 2rem;
		max-width: 1600px;
		margin: 0 auto;
		height: calc(100vh - 48px);
		display: flex;
		flex-direction: column;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
		flex-shrink: 0;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.header-left h1 {
		margin: 0;
		font-size: 1.5rem;
	}

	.backlog-container {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 2rem;
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}

	.backlog-column,
	.sprints-column {
		display: flex;
		flex-direction: column;
		min-height: 0;
	}

	.column-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
		flex-shrink: 0;
	}

	.column-header h2 {
		margin: 0;
		font-size: 1rem;
		font-weight: 600;
	}

	.column-stats {
		display: flex;
		gap: 0.5rem;
	}

	.backlog-list {
		flex: 1;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		padding-right: 0.5rem;
	}

	.load-more-trigger {
		display: flex;
		justify-content: center;
		align-items: center;
		padding: 1rem;
		min-height: 60px;
	}

	.sprints-list {
		flex: 1;
		overflow-y: auto;
		padding-right: 0.5rem;
	}

	.sprints-section {
		margin-bottom: 1.5rem;
	}

	.section-title {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--cds-text-secondary);
		text-transform: uppercase;
		margin: 0 0 0.75rem 0;
	}

	:global(.empty-state) {
		text-align: center;
		padding: 2rem;
		color: var(--cds-text-secondary);
	}

	.hint {
		font-size: 0.875rem;
		margin-top: 0.5rem;
	}
</style>
