<script lang="ts">
	import { onMount } from 'svelte';
	import '@carbon/charts-svelte/styles.css';
	import { Dropdown, Loading, InlineNotification } from 'carbon-components-svelte';
	import api from '$lib/api/client';
	import { format, parseISO } from 'date-fns';
	import { ru } from 'date-fns/locale';

	interface TimeSeriesPoint {
		date: string;
		value: number;
	}

	interface TimeSeriesData {
		name: string;
		data: TimeSeriesPoint[];
	}

	interface TimeSeriesStats {
		period: string;
		aggregation: string;
		start_date: string;
		end_date: string;
		users_registered: TimeSeriesData;
		issues_created: TimeSeriesData;
		active_users: TimeSeriesData;
	}

	interface PeriodConfig {
		days: number;
		aggregation: string;
	}

	const periodConfigs: Record<string, PeriodConfig> = {
		'7d': { days: 7, aggregation: 'day' },
		'30d': { days: 30, aggregation: 'day' },
		'90d': { days: 90, aggregation: 'week' },
		'180d': { days: 180, aggregation: 'week' },
		'365d': { days: 365, aggregation: 'month' }
	};

	const periodOptions = [
		{ id: '7d', text: '7 дней' },
		{ id: '30d', text: '30 дней' },
		{ id: '90d', text: '90 дней' },
		{ id: '180d', text: '180 дней' },
		{ id: '365d', text: '1 год' }
	];

	let selectedPeriodId = $state('30d');
	let stats = $state<TimeSeriesStats | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	let LineChart: typeof import('@carbon/charts-svelte').LineChart | undefined = $state();
	let BarChartSimple: typeof import('@carbon/charts-svelte').BarChartSimple | undefined = $state();

	onMount(async () => {
		const charts = await import('@carbon/charts-svelte');
		LineChart = charts.LineChart;
		BarChartSimple = charts.BarChartSimple;
		await loadStats();
	});

	async function loadStats(): Promise<void> {
		isLoading = true;
		error = null;

		const config = periodConfigs[selectedPeriodId];
		if (!config) return;

		try {
			stats = await api.get<TimeSeriesStats>('/api/admin/stats/timeseries', {
				days: String(config.days),
				aggregation: config.aggregation
			});
		} catch (err) {
			error = err instanceof Error ? err.message : 'Не удалось загрузить статистику';
		} finally {
			isLoading = false;
		}
	}

	function handlePeriodChange(event: CustomEvent<{ selectedId: string }>): void {
		selectedPeriodId = event.detail.selectedId;
		loadStats();
	}

	function formatDate(dateStr: string): string {
		const config = periodConfigs[selectedPeriodId];
		if (config?.aggregation === 'month') {
			return format(parseISO(dateStr), 'MMM yyyy', { locale: ru });
		}
		return format(parseISO(dateStr), 'd MMM', { locale: ru });
	}

	let usersChartData = $derived(() => {
		if (!stats?.users_registered?.data) return [];
		return stats.users_registered.data.map((point) => ({
			group: 'Регистрации',
			key: formatDate(point.date),
			value: point.value
		}));
	});

	let issuesChartData = $derived(() => {
		if (!stats?.issues_created?.data) return [];
		return stats.issues_created.data.map((point) => ({
			group: 'Задачи',
			key: formatDate(point.date),
			value: point.value
		}));
	});

	let activeUsersChartData = $derived(() => {
		if (!stats?.active_users?.data) return [];
		return stats.active_users.data.map((point) => ({
			group: 'Активные',
			key: formatDate(point.date),
			value: point.value
		}));
	});

	const lineChartOptions = {
		axes: {
			left: {
				title: 'Количество',
				mapsTo: 'value'
			},
			bottom: {
				mapsTo: 'key',
				scaleType: 'labels'
			}
		},
		height: '280px',
		theme: 'g100',
		legend: {
			enabled: false
		},
		points: {
			radius: 3,
			filled: true
		},
		curve: 'curveMonotoneX'
	} as import('@carbon/charts').LineChartOptions;

	const barChartOptions = {
		axes: {
			left: {
				mapsTo: 'value'
			},
			bottom: {
				mapsTo: 'key',
				scaleType: 'labels'
			}
		},
		height: '280px',
		theme: 'g100',
		legend: {
			enabled: false
		},
		color: {
			scale: {
				Активные: '#198038'
			}
		}
	} as import('@carbon/charts').BarChartOptions;

	let totalUsersRegistered = $derived(() => {
		if (!stats?.users_registered?.data) return 0;
		return stats.users_registered.data.reduce((sum, item) => sum + item.value, 0);
	});

	let totalIssuesCreated = $derived(() => {
		if (!stats?.issues_created?.data) return 0;
		return stats.issues_created.data.reduce((sum, item) => sum + item.value, 0);
	});

	let avgActiveUsers = $derived(() => {
		if (!stats?.active_users?.data || stats.active_users.data.length === 0) return 0;
		const total = stats.active_users.data.reduce((sum, item) => sum + item.value, 0);
		return Math.round(total / stats.active_users.data.length);
	});
</script>

<div class="usage-charts">
	<div class="charts-header">
		<h2>Графики использования</h2>
		<Dropdown
			label="Период"
			hideLabel
			selectedId={selectedPeriodId}
			items={periodOptions}
			on:select={handlePeriodChange}
			size="sm"
		/>
	</div>

	{#if isLoading}
		<div class="loading-container">
			<Loading withOverlay={false} small />
			<span>Загрузка графиков...</span>
		</div>
	{:else if error}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={error}
			on:close={() => (error = null)}
		/>
	{:else if stats && LineChart && BarChartSimple}
		<div class="charts-grid">
			<div class="chart-card">
				<h3>Регистрации пользователей</h3>
				{#if usersChartData().length > 0}
					<LineChart
						data={usersChartData()}
						options={{
							...lineChartOptions,
							color: { scale: { Регистрации: '#8a3ffc' } }
						}}
					/>
					<div class="chart-summary">
						<span class="summary-label">Всего за период:</span>
						<span class="summary-value">{totalUsersRegistered()}</span>
					</div>
				{:else}
					<div class="empty-chart">
						<p>Нет данных за выбранный период</p>
					</div>
				{/if}
			</div>

			<div class="chart-card">
				<h3>Созданные задачи</h3>
				{#if issuesChartData().length > 0}
					<LineChart
						data={issuesChartData()}
						options={{
							...lineChartOptions,
							color: { scale: { Задачи: '#1192e8' } }
						}}
					/>
					<div class="chart-summary">
						<span class="summary-label">Всего за период:</span>
						<span class="summary-value">{totalIssuesCreated()}</span>
					</div>
				{:else}
					<div class="empty-chart">
						<p>Нет данных за выбранный период</p>
					</div>
				{/if}
			</div>

			<div class="chart-card">
				<h3>Активные пользователи</h3>
				{#if activeUsersChartData().length > 0}
					<BarChartSimple data={activeUsersChartData()} options={barChartOptions} />
					<div class="chart-summary">
						<span class="summary-label">В среднем:</span>
						<span class="summary-value">{avgActiveUsers()}</span>
					</div>
				{:else}
					<div class="empty-chart">
						<p>Нет данных за выбранный период</p>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.usage-charts {
		margin-top: 2rem;
	}

	.charts-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
	}

	.charts-header h2 {
		font-size: 1.25rem;
		font-weight: 600;
		margin: 0;
	}

	.charts-header :global(.bx--dropdown) {
		min-width: 140px;
	}

	.loading-container {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		padding: 3rem;
		color: var(--cds-text-secondary);
	}

	.charts-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
		gap: 1.5rem;
	}

	.chart-card {
		background: var(--cds-layer);
		border: 1px solid var(--cds-border-subtle);
		padding: 1.25rem;
	}

	.chart-card h3 {
		font-size: 0.875rem;
		font-weight: 600;
		margin: 0 0 1rem;
		color: var(--cds-text-secondary);
	}

	.chart-summary {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-top: 1rem;
		padding-top: 0.75rem;
		border-top: 1px solid var(--cds-border-subtle);
	}

	.summary-label {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}

	.summary-value {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--cds-text-primary);
	}

	.empty-chart {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 280px;
		color: var(--cds-text-secondary);
	}

	.empty-chart p {
		margin: 0;
	}
</style>
