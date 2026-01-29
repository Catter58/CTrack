<script lang="ts">
	import { onMount } from 'svelte';
	import '@carbon/charts-svelte/styles.css';
	import type { AssigneeCount } from '$lib/stores/reports';

	interface Props {
		data: AssigneeCount[];
	}

	let { data }: Props = $props();

	let BarChartSimple: typeof import('@carbon/charts-svelte').BarChartSimple | undefined = $state();

	onMount(async () => {
		const charts = await import('@carbon/charts-svelte');
		BarChartSimple = charts.BarChartSimple;
	});

	let chartData = $derived(() => {
		if (!data || data.length === 0) return [];

		return data.map((item) => ({
			group: item.assignee_name || 'Не назначен',
			value: item.count
		}));
	});

	let chartOptions = $derived(() => ({
		title: 'По исполнителям',
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
			scale: {
				'Не назначен': '#a8a8a8'
			}
		},
		legend: {
			enabled: false
		}
	} as import('@carbon/charts').BarChartOptions));
</script>

<div class="chart-container">
	{#if !data || data.length === 0}
		<div class="empty-state">
			<p>Нет данных по исполнителям</p>
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
