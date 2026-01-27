<script lang="ts">
	import { onMount } from 'svelte';
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
	import { epicsStore, epicsList, epicsLoading, epicsError, epicsStats } from '$lib/stores/epics';
	import { EpicCard } from '$lib/components/epics';

	const projectKey = $derived($page.params.key);

	onMount(async () => {
		const key = get(page).params.key!;
		await Promise.all([projects.loadProject(key), epicsStore.loadEpics(key)]);
	});

	const activeEpics = $derived($epicsList.filter((e) => e.status.category !== 'done'));
	const completedEpics = $derived($epicsList.filter((e) => e.status.category === 'done'));
</script>

<svelte:head>
	<title>Эпики — {$currentProject?.name || 'Проект'}</title>
</svelte:head>

<div class="epics-page">
	<header class="page-header">
		<div class="header-left">
			<Button kind="ghost" size="small" icon={ArrowLeft} href="/projects/{projectKey}">
				Назад к доске
			</Button>
			<h1>Эпики</h1>
		</div>
		<Button icon={Add} href="/projects/{projectKey}?create=epic">Создать эпик</Button>
	</header>

	{#if $projectsLoading || $epicsLoading}
		<Loading />
	{:else if $epicsError}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={$epicsError}
			on:close={() => epicsStore.clearError()}
		/>
	{:else}
		<div class="epics-stats">
			<Tag size="sm">{$epicsStats.total} эпиков</Tag>
			<Tag size="sm" type="outline">
				{$epicsStats.completedIssues} / {$epicsStats.totalIssues} задач
			</Tag>
			{#if $epicsStats.totalSP > 0}
				<Tag size="sm" type="outline">
					{$epicsStats.completedSP} / {$epicsStats.totalSP} SP
				</Tag>
			{/if}
		</div>

		{#if $epicsList.length === 0}
			<Tile class="empty-state">
				<p>Нет эпиков</p>
				<p class="hint">
					Создайте эпик для группировки связанных задач
				</p>
				<Button kind="tertiary" size="small" href="/projects/{projectKey}?create=epic">
					Создать эпик
				</Button>
			</Tile>
		{:else}
			{#if activeEpics.length > 0}
				<section class="epics-section">
					<h2 class="section-title">Активные ({activeEpics.length})</h2>
					<div class="epics-grid">
						{#each activeEpics as epic (epic.id)}
							<EpicCard {epic} />
						{/each}
					</div>
				</section>
			{/if}

			{#if completedEpics.length > 0}
				<section class="epics-section">
					<h2 class="section-title">Завершённые ({completedEpics.length})</h2>
					<div class="epics-grid">
						{#each completedEpics as epic (epic.id)}
							<EpicCard {epic} />
						{/each}
					</div>
				</section>
			{/if}
		{/if}
	{/if}
</div>

<style>
	.epics-page {
		padding: 1rem 2rem;
		max-width: 1400px;
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

	.epics-stats {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1.5rem;
	}

	.epics-section {
		margin-bottom: 2rem;
	}

	.section-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--cds-text-secondary);
		text-transform: uppercase;
		margin: 0 0 1rem 0;
	}

	.epics-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
		gap: 1rem;
	}

	:global(.empty-state) {
		text-align: center;
		padding: 3rem 2rem;
		color: var(--cds-text-secondary);
	}

	.hint {
		font-size: 0.875rem;
		margin: 0.5rem 0 1rem;
	}
</style>
