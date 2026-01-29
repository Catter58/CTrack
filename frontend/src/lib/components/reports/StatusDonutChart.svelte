<script lang="ts">
	import { onMount } from 'svelte';
	import '@carbon/charts-svelte/styles.css';
	import type { StatusCount } from '$lib/stores/reports';

	interface Props {
		data: StatusCount[];
	}

	let { data }: Props = $props();

	let DonutChart: typeof import('@carbon/charts-svelte').DonutChart | undefined = $state();

	onMount(async () => {
		const charts = await import('@carbon/charts-svelte');
		DonutChart = charts.DonutChart;
	});

	let chartData = $derived(() => {
		if (!data || data.length === 0) return [];

		return data.map((item) => ({
			group: item.status_name,
			value: item.count
		}));
	});

	let colorScale = $derived(() => {
		const scale: Record<string, string> = {};
		if (!data) return scale;
		for (const item of data) {
			scale[item.status_name] = item.status_color;
		}
		return scale;
	});

	let chartOptions = $derived(() => ({
		title: 'По статусам',
		resizable: true,
		height: '300px',
		theme: 'g100' as const,
		color: {
			scale: colorScale()
		},
		legend: {
			alignment: 'center' as const
		},
		donut: {
			center: {
				label: 'Всего'
			}
		},
		pie: {
			labels: {
				enabled: false
			}
		}
	}));
</script>

<div class="chart-container">
	{#if !data || data.length === 0}
		<div class="empty-state">
			<p>Нет данных по статусам</p>
		</div>
	{:else if DonutChart}
		<DonutChart data={chartData()} options={chartOptions()} />
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
