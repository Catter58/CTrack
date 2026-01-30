<script lang="ts">
	import { page } from '$app/state';
	import { onMount, onDestroy } from 'svelte';
	import {
		Breadcrumb,
		BreadcrumbItem,
		Select,
		SelectItem,
		InlineLoading,
		InlineNotification
	} from 'carbon-components-svelte';
	import { ChartColumn, ChartLine } from 'carbon-icons-svelte';
	import {
		metrics,
		velocityData,
		burndownData,
		isLoadingVelocity,
		isLoadingBurndown,
		metricsError
	} from '$lib/stores/metrics';
	import { sprints } from '$lib/stores/sprints';
	import type { Sprint } from '$lib/stores/sprints';

	// Lazy load chart components
	const velocityChartPromise = import('$lib/components/metrics/VelocityChart.svelte');
	const burndownChartPromise = import('$lib/components/metrics/BurndownChart.svelte');

	let projectKey = $derived(page.params.key);
	let selectedSprintId = $state<string>('');

	// Filter sprints that have been started (active or completed)
	let availableSprints = $derived(
		($sprints.sprints || []).filter(
			(s: Sprint) => s.status === 'active' || s.status === 'completed'
		)
	);

	onMount(async () => {
		if (!projectKey) return;

		// Load velocity data
		await metrics.loadVelocity(projectKey);

		// Load sprints to populate select
		await sprints.loadSprints(projectKey);
	});

	onDestroy(() => {
		metrics.reset();
	});

	async function handleSprintSelect(event: Event) {
		const target = event.target as HTMLSelectElement;
		selectedSprintId = target.value;
		if (selectedSprintId) {
			await metrics.loadBurndown(selectedSprintId);
		}
	}

	// Auto-select active sprint if available
	$effect(() => {
		if (availableSprints.length > 0 && !selectedSprintId) {
			const activeSprint = availableSprints.find((s: Sprint) => s.status === 'active');
			if (activeSprint) {
				selectedSprintId = activeSprint.id;
				metrics.loadBurndown(activeSprint.id);
			}
		}
	});
</script>

<svelte:head>
	<title>Метрики - {projectKey}</title>
</svelte:head>

<div class="metrics-page">
	<Breadcrumb noTrailingSlash>
		<BreadcrumbItem href="/projects">Проекты</BreadcrumbItem>
		<BreadcrumbItem href="/projects/{projectKey}">{projectKey}</BreadcrumbItem>
		<BreadcrumbItem href="/projects/{projectKey}/metrics" isCurrentPage>Метрики</BreadcrumbItem>
	</Breadcrumb>

	<header class="page-header">
		<h1>Метрики проекта</h1>
	</header>

	{#if $metricsError}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={$metricsError}
			on:close={() => metrics.clearError()}
		/>
	{/if}

	<div class="metrics-grid">
		<section class="metric-section">
			<div class="section-header">
				<ChartColumn size={24} />
				<h2>Velocity</h2>
			</div>

			{#if $isLoadingVelocity}
				<div class="loading-container">
					<InlineLoading description="Загрузка данных velocity..." />
				</div>
			{:else if $velocityData}
				{#await velocityChartPromise}
					<div class="loading-container">
						<InlineLoading description="Загрузка компонента..." />
					</div>
				{:then module}
					<module.default data={$velocityData} />
				{:catch}
					<div class="empty-state">
						<p>Ошибка загрузки компонента графика</p>
					</div>
				{/await}
			{:else}
				<div class="empty-state">
					<p>Нет данных о velocity</p>
				</div>
			{/if}
		</section>

		<section class="metric-section">
			<div class="section-header">
				<ChartLine size={24} />
				<h2>Burndown</h2>
				<div class="sprint-select">
					<Select
						labelText=""
						hideLabel
						size="sm"
						bind:selected={selectedSprintId}
						on:change={handleSprintSelect}
					>
						<SelectItem value="" text="Выберите спринт" />
						{#each availableSprints as sprint (sprint.id)}
							<SelectItem
								value={sprint.id}
								text="{sprint.name} ({sprint.status === 'active' ? 'активный' : 'завершён'})"
							/>
						{/each}
					</Select>
				</div>
			</div>

			{#if $isLoadingBurndown}
				<div class="loading-container">
					<InlineLoading description="Загрузка burndown..." />
				</div>
			{:else if $burndownData}
				{#await burndownChartPromise}
					<div class="loading-container">
						<InlineLoading description="Загрузка компонента..." />
					</div>
				{:then module}
					<module.default data={$burndownData} />
				{:catch}
					<div class="empty-state">
						<p>Ошибка загрузки компонента графика</p>
					</div>
				{/await}
			{:else}
				<div class="empty-state">
					<p>Выберите спринт для отображения burndown диаграммы</p>
					<p class="hint">Доступны только активные или завершённые спринты</p>
				</div>
			{/if}
		</section>
	</div>
</div>

<style>
	.metrics-page {
		max-width: 1400px;
		margin: 0 auto;
		padding: 1rem 2rem;
	}

	.page-header {
		margin: 1.5rem 0;
	}

	.page-header h1 {
		margin: 0;
		font-size: 1.75rem;
		font-weight: 400;
	}

	.metrics-grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: 2rem;
	}

	@media (min-width: 1200px) {
		.metrics-grid {
			grid-template-columns: 1fr 1fr;
		}
	}

	.metric-section {
		background: var(--cds-field);
		border-radius: 6px;
		padding: 1.5rem;
	}

	.section-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	.section-header h2 {
		margin: 0;
		font-size: 1.25rem;
		font-weight: 600;
		flex: 1;
	}

	.sprint-select {
		min-width: 250px;
	}

	.loading-container {
		display: flex;
		justify-content: center;
		align-items: center;
		height: 400px;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 300px;
		color: var(--cds-text-secondary);
		text-align: center;
	}

	.empty-state p {
		margin: 0;
		font-size: 1rem;
	}

	.empty-state .hint {
		font-size: 0.875rem;
		margin-top: 0.5rem;
		opacity: 0.8;
	}
</style>
