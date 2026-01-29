<script lang="ts">
	import { onMount } from 'svelte';
	import '@carbon/charts-svelte/styles.css';
	import type { PriorityCount } from '$lib/stores/reports';

	interface Props {
		data: PriorityCount[];
	}

	let { data }: Props = $props();

	let BarChartSimple: typeof import('@carbon/charts-svelte').BarChartSimple | undefined = $state();

	onMount(async () => {
		const charts = await import('@carbon/charts-svelte');
		BarChartSimple = charts.BarChartSimple;
	});

	const priorityLabels: Record<string, string> = {
		highest: 'Критический',
		high: 'Высокий',
		medium: 'Средний',
		low: 'Низкий',
		lowest: 'Минимальный'
	};

	const priorityColors: Record<string, string> = {
		highest: '#da1e28',
		high: '#fa4d56',
		medium: '#f1c21b',
		low: '#42be65',
		lowest: '#a8a8a8'
	};

	let chartData = $derived(() => {
		if (!data || data.length === 0) return [];

		return data.map((item) => ({
			group: priorityLabels[item.priority] || item.priority,
			value: item.count
		}));
	});

	let colorScale = $derived(() => {
		const scale: Record<string, string> = {};
		if (!data) return scale;
		for (const item of data) {
			const label = priorityLabels[item.priority] || item.priority;
			scale[label] = priorityColors[item.priority] || '#8a3ffc';
		}
		return scale;
	});

	let chartOptions = $derived(() => ({
		title: 'По приоритету',
		axes: {
			left: {
				mapsTo: 'value'
			},
			bottom: {
				mapsTo: 'group',
				scaleType: 'labels'
			}
		},
		height: '300px',
		theme: 'g100',
		color: {
			scale: colorScale()
		},
		legend: {
			enabled: false
		}
	} as import('@carbon/charts').BarChartOptions));
</script>

<div class="chart-container">
	{#if !data || data.length === 0}
		<div class="empty-state">
			<p>Нет данных по приоритетам</p>
		</div>
	{:else if BarChartSimple}
		<BarChartSimple data={chartData()} options={chartOptions()} />
	{:else}
		<div class="loading">Загрузка графика...</div>
	{/if}
</div>

<style>
	.chart-container {
		width: 100%;
		min-height: 300px;
	}

	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 300px;
		color: var(--cds-text-secondary);
	}

	.empty-state p {
		margin: 0;
	}

	.loading {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 300px;
		color: var(--cds-text-secondary);
	}
</style>
