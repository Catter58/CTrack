<script lang="ts">
	import type { CycleTimeData } from '$lib/stores/reports';

	interface Props {
		data: CycleTimeData;
	}

	let { data }: Props = $props();

	function formatDuration(hours: number | null): string {
		if (hours === null || hours === undefined || isNaN(hours)) {
			return '—';
		}
		if (hours < 1) {
			return `${Math.round(hours * 60)} мин`;
		}
		if (hours < 24) {
			return `${hours.toFixed(1)} ч`;
		}
		const days = hours / 24;
		if (days < 7) {
			return `${days.toFixed(1)} дн`;
		}
		const weeks = days / 7;
		return `${weeks.toFixed(1)} нед`;
	}
</script>

<div class="cycle-time-container">
	{#if !data || data.total_completed === 0}
		<div class="empty-state">
			<p>Нет данных о времени цикла</p>
			<p class="hint">Время цикла рассчитывается по решённым задачам</p>
		</div>
	{:else}
		<div class="main-metric">
			<span class="label">Среднее время цикла</span>
			<span class="value">{formatDuration(data.overall_avg_hours)}</span>
			<span class="subtext">на основе {data.total_completed} решённых задач</span>
			{#if data.overall_median_hours !== null}
				<span class="subtext">Медиана: {formatDuration(data.overall_median_hours)}</span>
			{/if}
		</div>

		{#if data.by_type && data.by_type.length > 0}
			<div class="breakdown">
				<h4>По типам задач</h4>
				<div class="type-list">
					{#each data.by_type as typeData (typeData.group_id || typeData.group_name)}
						<div class="type-row">
							<span class="type-name">{typeData.group_name}</span>
							<span class="type-stats">
								<span class="type-time">{formatDuration(typeData.avg_hours)}</span>
								<span class="type-count">({typeData.count} задач)</span>
							</span>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		{#if data.by_priority && data.by_priority.length > 0}
			<div class="breakdown">
				<h4>По приоритетам</h4>
				<div class="type-list">
					{#each data.by_priority as priorityData (priorityData.group_name)}
						<div class="type-row">
							<span class="type-name">{priorityData.group_name}</span>
							<span class="type-stats">
								<span class="type-time">{formatDuration(priorityData.avg_hours)}</span>
								<span class="type-count">({priorityData.count} задач)</span>
							</span>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	{/if}
</div>

<style>
	.cycle-time-container {
		padding: 1rem;
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
	}

	.empty-state .hint {
		font-size: 0.875rem;
		margin-top: 0.5rem;
		opacity: 0.8;
	}

	.main-metric {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 2rem 1rem;
		background: var(--cds-layer-accent);
		border-radius: 8px;
		text-align: center;
	}

	.main-metric .label {
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
		margin-bottom: 0.5rem;
	}

	.main-metric .value {
		font-size: 2.5rem;
		font-weight: 600;
		color: var(--cds-text-primary);
	}

	.main-metric .subtext {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
		margin-top: 0.5rem;
	}

	.breakdown {
		margin-top: 1.5rem;
	}

	.breakdown h4 {
		font-size: 0.875rem;
		font-weight: 600;
		margin: 0 0 1rem;
		color: var(--cds-text-secondary);
	}

	.type-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.type-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem;
		background: var(--cds-layer);
		border-radius: 4px;
	}

	.type-name {
		font-weight: 500;
	}

	.type-stats {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.type-time {
		font-weight: 600;
		color: var(--cds-text-primary);
	}

	.type-count {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}
</style>
