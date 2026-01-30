<script lang="ts">
	import { onMount } from 'svelte';
	import '@carbon/charts-svelte/styles.css';
	import type { BurndownData } from '$lib/stores/metrics';
	import { format, parseISO } from 'date-fns';
	import { ru } from 'date-fns/locale';

	interface Props {
		data: BurndownData;
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
		if (!data) return [];

		const result: Array<{ group: string; key: string; value: number }> = [];

		// Add ideal line
		for (const point of data.ideal) {
			result.push({
				group: 'Идеальная линия',
				key: formatDate(point.date),
				value: point.value
			});
		}

		// Add actual line
		for (const point of data.actual) {
			result.push({
				group: 'Фактически',
				key: formatDate(point.date),
				value: point.value
			});
		}

		return result;
	});

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	let chartOptions = $derived((): any => ({
		title: `Burndown: ${data?.sprint_name || 'Спринт'}`,
		axes: {
			left: {
				title: 'Story Points',
				mapsTo: 'value'
			},
			bottom: {
				title: 'Дата',
				mapsTo: 'key',
				scaleType: 'labels'
			}
		},
		height: '400px',
		theme: 'g100',
		color: {
			scale: {
				'Идеальная линия': '#8a3ffc',
				'Фактически': '#198038'
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
	}));

	let progressPercent = $derived(() => {
		if (!data || data.initial_story_points === 0) return 0;
		const actualLast = data.actual[data.actual.length - 1];
		if (!actualLast) return 0;
		const remaining = actualLast.value;
		return Math.round(
			((data.initial_story_points - remaining) / data.initial_story_points) * 100
		);
	});
</script>

<div class="burndown-chart">
	{#if !data}
		<div class="empty-state">
			<p>Выберите спринт для отображения burndown</p>
		</div>
	{:else if LineChart}
		<LineChart data={chartData()} options={chartOptions()} />
		<div class="metrics-summary">
			<div class="metric">
				<span class="label">Начальный объём:</span>
				<span class="value">{data.initial_story_points} SP</span>
			</div>
			<div class="metric">
				<span class="label">Осталось:</span>
				<span class="value">{data.actual[data.actual.length - 1]?.value || 0} SP</span>
			</div>
			<div class="metric">
				<span class="label">Прогресс:</span>
				<span class="value">{progressPercent()}%</span>
			</div>
		</div>
	{:else}
		<div class="loading">Загрузка графика...</div>
	{/if}
</div>

<style>
	.burndown-chart {
		background: var(--cds-layer);
		border-radius: 6px;
		padding: 1rem;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 300px;
		color: var(--cds-text-secondary);
	}

	.empty-state p {
		margin: 0;
		font-size: 1rem;
	}

	.loading {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 400px;
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
</style>
