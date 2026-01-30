<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import {
		Button,
		Tile,
		Loading,
		InlineNotification,
		ToastNotification,
		Tabs,
		Tab,
		TabContent
	} from 'carbon-components-svelte';
	import { Add, ArrowLeft } from 'carbon-icons-svelte';
	import { projects, currentProject, projectsLoading } from '$lib/stores/projects';
	import {
		sprints,
		type Sprint,
		type CreateSprintData,
		type UpdateSprintData
	} from '$lib/stores/sprints';
	import { SprintCard, SprintModal, SprintCompleteModal } from '$lib/components/sprints';

	const projectKey = $derived(page.params.key);

	let showCreateModal = $state(false);
	let showEditModal = $state(false);
	let showCompleteModal = $state(false);
	let selectedSprint = $state<Sprint | null>(null);
	let incompleteCount = $state(0);

	let toastMessage = $state<string | null>(null);
	let toastKind = $state<'success' | 'error'>('success');

	function showToast(message: string, kind: 'success' | 'error' = 'success') {
		toastMessage = message;
		toastKind = kind;
		setTimeout(() => {
			toastMessage = null;
		}, 4000);
	}

	onMount(async () => {
		const key = page.params.key;
		if (!key) return;
		await Promise.all([projects.loadProject(key), sprints.loadSprints(key)]);
	});

	async function handleCreateSprint(data: CreateSprintData | UpdateSprintData) {
		if (!projectKey) return;
		const sprint = await sprints.createSprint(projectKey, data as CreateSprintData);
		if (sprint) {
			showToast('Спринт создан');
		}
	}

	async function handleUpdateSprint(data: CreateSprintData | UpdateSprintData) {
		if (!selectedSprint) return;
		const sprint = await sprints.updateSprint(selectedSprint.id, data);
		if (sprint) {
			showToast('Спринт обновлён');
		}
	}

	async function handleStartSprint(sprint: Sprint) {
		const result = await sprints.startSprint(sprint.id);
		if (result) {
			showToast('Спринт запущен');
		}
	}

	async function handleOpenCompleteModal(sprint: Sprint) {
		selectedSprint = sprint;
		const issues = await sprints.loadSprintIssues(sprint.id);
		incompleteCount = issues.filter(
			(i) => i.status.category !== 'done'
		).length;
		showCompleteModal = true;
	}

	async function handleCompleteSprint(moveIncompleteTo: string | null) {
		if (!selectedSprint) return;
		const result = await sprints.completeSprint(
			selectedSprint.id,
			moveIncompleteTo
		);
		if (result) {
			showToast('Спринт завершён');
		}
	}

	async function handleDeleteSprint(sprint: Sprint) {
		if (!confirm(`Удалить спринт "${sprint.name}"?`)) return;
		const result = await sprints.deleteSprint(sprint.id);
		if (result) {
			showToast('Спринт удалён');
		}
	}

	function handleEditSprint(sprint: Sprint) {
		selectedSprint = sprint;
		showEditModal = true;
	}

	// Filtered sprints by status
	const activeSprints = $derived(
		$sprints.sprints.filter((s) => s.status === 'active')
	);
	const plannedSprints = $derived(
		$sprints.sprints.filter((s) => s.status === 'planned')
	);
	const completedSprints = $derived(
		$sprints.sprints.filter((s) => s.status === 'completed')
	);
</script>

<svelte:head>
	<title>Спринты — {$currentProject?.name || 'Проект'}</title>
</svelte:head>

{#if toastMessage}
	<ToastNotification
		kind={toastKind}
		title={toastKind === 'success' ? 'Успешно' : 'Ошибка'}
		subtitle={toastMessage}
		timeout={4000}
		on:close={() => (toastMessage = null)}
		style="position: fixed; top: 1rem; right: 1rem; z-index: 9999;"
	/>
{/if}

<div class="sprints-page">
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
			<h1>Спринты</h1>
		</div>
		<Button icon={Add} on:click={() => (showCreateModal = true)}>
			Создать спринт
		</Button>
	</header>

	{#if $projectsLoading || $sprints.isLoading}
		<Loading />
	{:else if $sprints.error}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={$sprints.error}
		/>
	{:else}
		<Tabs>
			<Tab label="Активные ({activeSprints.length})" />
			<Tab label="Запланированные ({plannedSprints.length})" />
			<Tab label="Завершённые ({completedSprints.length})" />
			<svelte:fragment slot="content">
				<TabContent>
					{#if activeSprints.length === 0}
						<Tile class="empty-state">
							<p>Нет активных спринтов</p>
							{#if plannedSprints.length > 0}
								<p class="hint">Запустите один из запланированных спринтов</p>
							{/if}
						</Tile>
					{:else}
						<div class="sprints-grid">
							{#each activeSprints as sprint (sprint.id)}
								<SprintCard
									{sprint}
									onComplete={handleOpenCompleteModal}
									onEdit={handleEditSprint}
									onDelete={handleDeleteSprint}
								/>
							{/each}
						</div>
					{/if}
				</TabContent>
				<TabContent>
					{#if plannedSprints.length === 0}
						<Tile class="empty-state">
							<p>Нет запланированных спринтов</p>
							<Button
								kind="tertiary"
								size="small"
								on:click={() => (showCreateModal = true)}
							>
								Создать спринт
							</Button>
						</Tile>
					{:else}
						<div class="sprints-grid">
							{#each plannedSprints as sprint (sprint.id)}
								<SprintCard
									{sprint}
									onStart={handleStartSprint}
									onEdit={handleEditSprint}
									onDelete={handleDeleteSprint}
								/>
							{/each}
						</div>
					{/if}
				</TabContent>
				<TabContent>
					{#if completedSprints.length === 0}
						<Tile class="empty-state">
							<p>Нет завершённых спринтов</p>
						</Tile>
					{:else}
						<div class="sprints-grid">
							{#each completedSprints as sprint (sprint.id)}
								<SprintCard
									{sprint}
									onEdit={handleEditSprint}
									onDelete={handleDeleteSprint}
								/>
							{/each}
						</div>
					{/if}
				</TabContent>
			</svelte:fragment>
		</Tabs>
	{/if}
</div>

<SprintModal
	open={showCreateModal}
	onClose={() => (showCreateModal = false)}
	onSave={handleCreateSprint}
/>

<SprintModal
	open={showEditModal}
	sprint={selectedSprint}
	onClose={() => {
		showEditModal = false;
		selectedSprint = null;
	}}
	onSave={handleUpdateSprint}
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
	.sprints-page {
		padding: 1rem 2rem;
		max-width: 1200px;
		margin: 0 auto;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
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

	.sprints-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
		gap: 1rem;
		padding: 1rem 0;
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
