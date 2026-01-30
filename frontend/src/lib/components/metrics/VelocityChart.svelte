<script lang="ts">
	import { onMount } from 'svelte';
	import '@carbon/charts-svelte/styles.css';
	import type { VelocityData } from '$lib/stores/metrics';

	interface Props {
		data: VelocityData;
	}

	let { data }: Props = $props();

	let ComboChart: typeof import('@carbon/charts-svelte').ComboChart | undefined = $state();

	onMount(async () => {
		const charts = await import('@carbon/charts-svelte');
		ComboChart = charts.ComboChart;
	});

	let chartData = $derived(() => {
		if (!data || data.sprints.length === 0) return [];

		const result: Array<{ group: string; key: string; value: number }> = [];

		for (const sprint of data.sprints) {
			result.push({
				group: 'Запланировано',
				key: sprint.name,
				value: sprint.committed_story_points
			});
			result.push({
				group: 'Выполнено',
				key: sprint.name,
				value: sprint.completed_story_points
			});
			result.push({
				group: 'Средняя velocity',
				key: sprint.name,
				value: data.average_velocity
			});
		}

		return result;
	});

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	let chartOptions = $derived((): any => ({
		title: 'Velocity команды',
		axes: {
			left: {
				title: 'Story Points',
				mapsTo: 'value'
			},
			bottom: {
				title: 'Спринт',
				mapsTo: 'key',
				scaleType: 'labels'
			}
		},
		comboChartTypes: [
			{
				type: 'grouped-bar',
				correspondingDatasets: ['Запланировано', 'Выполнено']
			},
			{
				type: 'line',
				correspondingDatasets: ['Средняя velocity']
			}
		],
		height: '400px',
		theme: 'g100',
		color: {
			scale: {
				'Запланировано': '#8a3ffc',
				'Выполнено': '#198038',
				'Средняя velocity': '#fa4d56'
			}
		},
		legend: {
			alignment: 'center'
		}
	}));
</script>

<div class="velocity-chart">
	{#if data.sprints.length === 0}
		<div class="empty-state">
			<p>Нет данных о velocity</p>
			<p class="hint">Завершите хотя бы один спринт, чтобы увидеть velocity</p>
		</div>
	{:else if ComboChart}
		<ComboChart data={chartData()} options={chartOptions()} />
		<div class="metrics-summary">
			<div class="metric">
				<span class="label">Средняя velocity:</span>
				<span class="value">{data.average_velocity} SP</span>
			</div>
			<div class="metric">
				<span class="label">Спринтов:</span>
				<span class="value">{data.total_sprints}</span>
			</div>
		</div>
	{:else}
		<div class="loading">Загрузка графика...</div>
	{/if}
</div>

<style>
	.velocity-chart {
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

	.empty-state .hint {
		font-size: 0.875rem;
		margin-top: 0.5rem;
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
