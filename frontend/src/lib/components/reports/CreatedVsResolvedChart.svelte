<script lang="ts">
	import { onMount } from 'svelte';
	import '@carbon/charts-svelte/styles.css';
	import type { CreatedVsResolved } from '$lib/stores/reports';
	import { format, parseISO } from 'date-fns';
	import { ru } from 'date-fns/locale';

	interface Props {
		data: CreatedVsResolved;
	}

	let { data }: Props = $props();

	let LineChart: typeof import('@carbon/charts-svelte').LineChart | undefined = $state();

	onMount(async () => {
		const charts = await import('@carbon/charts-svelte');
		LineChart = charts.LineChart;
	});

	function formatDate(dateStr: string): string {
		return format(parseISO(dateStr), 'd MMM', { locale: ru });
	}

	let chartData = $derived(() => {
		if (!data?.data || data.data.length === 0) return [];

		const result: Array<{ group: string; key: string; value: number }> = [];

		for (const point of data.data) {
			result.push({
				group: 'Создано',
				key: formatDate(point.date),
				value: point.created
			});
			result.push({
				group: 'Решено',
				key: formatDate(point.date),
				value: point.resolved
			});
		}

		return result;
	});

	let totalCreated = $derived(() => {
		if (!data?.data) return 0;
		return data.data.reduce((sum, item) => sum + item.created, 0);
	});

	let totalResolved = $derived(() => {
		if (!data?.data) return 0;
		return data.data.reduce((sum, item) => sum + item.resolved, 0);
	});

	let chartOptions = $derived(() => ({
		title: 'Создано vs Решено',
		axes: {
			left: {
				title: 'Задачи',
				mapsTo: 'value'
			},
			bottom: {
				title: 'Дата',
				mapsTo: 'key',
				scaleType: 'labels'
			}
		},
		height: '350px',
		theme: 'g100',
		color: {
			scale: {
				Создано: '#8a3ffc',
				Решено: '#198038'
			}
		},
		legend: {
			alignment: 'center'
		},
		points: {
			radius: 3,
			filled: true
		},
		curve: 'curveMonotoneX'
	} as import('@carbon/charts').LineChartOptions));
</script>

<div class="chart-container">
	{#if !data?.data || data.data.length === 0}
		<div class="empty-state">
			<p>Нет данных за выбранный период</p>
		</div>
	{:else if LineChart}
		<LineChart data={chartData()} options={chartOptions()} />
		<div class="metrics-summary">
			<div class="metric">
				<span class="label">Создано за период:</span>
				<span class="value created">{totalCreated()}</span>
			</div>
			<div class="metric">
				<span class="label">Решено за период:</span>
				<span class="value resolved">{totalResolved()}</span>
			</div>
			<div class="metric">
				<span class="label">Баланс:</span>
				<span class="value" class:positive={totalResolved() >= totalCreated()} class:negative={totalResolved() < totalCreated()}>
					{totalResolved() >= totalCreated() ? '+' : ''}{totalResolved() - totalCreated()}
				</span>
			</div>
		</div>
	{:else}
		<div class="loading">Загрузка графика...</div>
	{/if}
</div>

<style>
	.chart-container {
		width: 100%;
	}

	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 350px;
		color: var(--cds-text-secondary);
	}

	.empty-state p {
		margin: 0;
	}

	.loading {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 350px;
		color: var(--cds-text-secondary);
	}

	.metrics-summary {
		display: flex;
		gap: 2rem;
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid var(--cds-border-subtle);
	}

	.metric {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.metric .label {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}

	.metric .value {
		font-size: 1.25rem;
		font-weight: 600;
	}

	.metric .value.created {
		color: #8a3ffc;
	}

	.metric .value.resolved {
		color: #198038;
	}

	.metric .value.positive {
		color: #198038;
	}

	.metric .value.negative {
		color: #da1e28;
	}
</style>
