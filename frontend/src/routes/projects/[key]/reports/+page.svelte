<script lang="ts">
	import { page } from '$app/stores';
	import { onMount, onDestroy } from 'svelte';
	import {
		Breadcrumb,
		BreadcrumbItem,
		Select,
		SelectItem,
		InlineLoading,
		InlineNotification,
		Tile
	} from 'carbon-components-svelte';
	import { ChartPie, ChartLine, Time } from 'carbon-icons-svelte';
	import {
		StatusDonutChart,
		PriorityBarChart,
		AssigneeBarChart,
		CreatedVsResolvedChart,
		CycleTimeDisplay
	} from '$lib/components/reports';
	import {
		reports,
		summaryData,
		createdVsResolvedData,
		cycleTimeData,
		isLoadingSummary,
		isLoadingCreatedVsResolved,
		isLoadingCycleTime,
		reportsError
	} from '$lib/stores/reports';

	let projectKey = $derived($page.params.key!);
	let selectedDays = $state('30');

	const dayOptions = [
		{ value: '7', text: '7 дней' },
		{ value: '14', text: '14 дней' },
		{ value: '30', text: '30 дней' },
		{ value: '90', text: '90 дней' }
	];

	// Dynamically calculate completed tasks based on statuses with category="done"
	let completedCount = $derived(() => {
		if (!$summaryData?.by_status) return 0;
		return $summaryData.by_status
			.filter((s) => s.category === 'done')
			.reduce((sum, s) => sum + s.count, 0);
	});

	// Calculate in-progress tasks (category="in_progress")
	let inProgressCount = $derived(() => {
		if (!$summaryData?.by_status) return 0;
		return $summaryData.by_status
			.filter((s) => s.category === 'in_progress')
			.reduce((sum, s) => sum + s.count, 0);
	});

	onMount(async () => {
		await loadAllReports();
	});

	onDestroy(() => {
		reports.reset();
	});

	async function loadAllReports(): Promise<void> {
		const days = parseInt(selectedDays);
		await Promise.all([
			reports.loadSummary(projectKey),
			reports.loadCreatedVsResolved(projectKey, days),
			reports.loadCycleTime(projectKey, days)
		]);
	}

	async function handleDaysChange(event: Event): Promise<void> {
		const target = event.target as HTMLSelectElement;
		selectedDays = target.value;
		const days = parseInt(selectedDays);
		await Promise.all([
			reports.loadCreatedVsResolved(projectKey, days),
			reports.loadCycleTime(projectKey, days)
		]);
	}
</script>

<svelte:head>
	<title>Отчёты - {projectKey}</title>
</svelte:head>

<div class="reports-page">
	<Breadcrumb noTrailingSlash>
		<BreadcrumbItem href="/projects">Проекты</BreadcrumbItem>
		<BreadcrumbItem href="/projects/{projectKey}">{projectKey}</BreadcrumbItem>
		<BreadcrumbItem href="/projects/{projectKey}/reports" isCurrentPage>Отчёты</BreadcrumbItem>
	</Breadcrumb>

	<header class="page-header">
		<h1>Отчёты</h1>
	</header>

	{#if $reportsError}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={$reportsError}
			on:close={() => reports.clearError()}
		/>
	{/if}

	<section class="report-section summary-section">
		<div class="section-header">
			<ChartPie size={24} />
			<h2>Сводка по проекту</h2>
		</div>

		{#if $isLoadingSummary}
			<div class="loading-container">
				<InlineLoading description="Загрузка сводки..." />
			</div>
		{:else if $summaryData}
			<div class="summary-header">
				<Tile class="metric-tile">
					<div class="total-metric">
						<span class="total-label">Всего задач</span>
						<span class="total-value">{$summaryData.total_issues}</span>
					</div>
				</Tile>
				<Tile class="metric-tile">
					<div class="total-metric">
						<span class="total-label">В работе</span>
						<span class="total-value in-progress">{inProgressCount()}</span>
					</div>
				</Tile>
				<Tile class="metric-tile">
					<div class="total-metric">
						<span class="total-label">Завершено</span>
						<span class="total-value completed">{completedCount()}</span>
					</div>
				</Tile>
			</div>

			<div class="charts-grid">
				<div class="chart-card">
					<StatusDonutChart data={$summaryData.by_status} />
				</div>
				<div class="chart-card">
					<PriorityBarChart data={$summaryData.by_priority} />
				</div>
				<div class="chart-card">
					<AssigneeBarChart data={$summaryData.by_assignee} />
				</div>
			</div>
		{:else}
			<div class="empty-state">
				<p>Нет данных для отображения</p>
			</div>
		{/if}
	</section>

	<section class="report-section">
		<div class="section-header">
			<ChartLine size={24} />
			<h2>Создано vs Решено</h2>
			<div class="days-select">
				<Select
					labelText=""
					hideLabel
					size="sm"
					bind:selected={selectedDays}
					on:change={handleDaysChange}
				>
					{#each dayOptions as option (option.value)}
						<SelectItem value={option.value} text={option.text} />
					{/each}
				</Select>
			</div>
		</div>

		{#if $isLoadingCreatedVsResolved}
			<div class="loading-container">
				<InlineLoading description="Загрузка данных..." />
			</div>
		{:else if $createdVsResolvedData}
			<CreatedVsResolvedChart data={$createdVsResolvedData} />
		{:else}
			<div class="empty-state">
				<p>Нет данных за выбранный период</p>
			</div>
		{/if}
	</section>

	<section class="report-section">
		<div class="section-header">
			<Time size={24} />
			<h2>Время цикла</h2>
		</div>

		{#if $isLoadingCycleTime}
			<div class="loading-container">
				<InlineLoading description="Загрузка данных..." />
			</div>
		{:else if $cycleTimeData}
			<CycleTimeDisplay data={$cycleTimeData} />
		{:else}
			<div class="empty-state">
				<p>Нет данных о времени цикла</p>
			</div>
		{/if}
	</section>
</div>

<style>
	.reports-page {
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

	.report-section {
		background: var(--cds-field);
		border-radius: 6px;
		padding: 1.5rem;
		margin-bottom: 2rem;
	}

	.section-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 1.5rem;
	}

	.section-header h2 {
		margin: 0;
		font-size: 1.25rem;
		font-weight: 600;
		flex: 1;
	}

	.days-select {
		min-width: 120px;
	}

	.summary-header {
		display: flex;
		gap: 1rem;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
	}

	.summary-header :global(.bx--tile) {
		display: inline-block;
	}

	:global(.metric-tile) {
		min-width: 140px;
	}

	.total-metric {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.total-label {
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
	}

	.total-value {
		font-size: 2rem;
		font-weight: 600;
	}

	.total-value.in-progress {
		color: #0f62fe;
	}

	.total-value.completed {
		color: #198038;
	}

	.charts-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
		gap: 1.5rem;
	}

	.chart-card {
		background: var(--cds-layer);
		border-radius: 6px;
		padding: 1rem;
	}

	.loading-container {
		display: flex;
		justify-content: center;
		align-items: center;
		height: 300px;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 200px;
		color: var(--cds-text-secondary);
		text-align: center;
	}

	.empty-state p {
		margin: 0;
		font-size: 1rem;
	}
</style>
