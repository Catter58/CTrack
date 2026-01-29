<script lang="ts">
	import { Grid, List } from 'carbon-icons-svelte';

	interface Props {
		currentView: 'board' | 'list';
		onViewChange: (view: 'board' | 'list') => void;
	}

	let { currentView, onViewChange }: Props = $props();
</script>

<div class="view-switcher" role="tablist" aria-label="Переключение представления">
	<button
		class="view-btn"
		class:active={currentView === 'board'}
		role="tab"
		aria-selected={currentView === 'board'}
		aria-label="Доска"
		title="Доска"
		onclick={() => onViewChange('board')}
	>
		<Grid size={20} />
	</button>
	<button
		class="view-btn"
		class:active={currentView === 'list'}
		role="tab"
		aria-selected={currentView === 'list'}
		aria-label="Список"
		title="Список"
		onclick={() => onViewChange('list')}
	>
		<List size={20} />
	</button>
</div>

<style>
	.view-switcher {
		display: inline-flex;
		gap: 2px;
		background: var(--cds-field);
		border-radius: 4px;
		padding: 2px;
	}

	.view-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border: none;
		border-radius: 2px;
		background: transparent;
		color: var(--cds-text-secondary);
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.view-btn:hover {
		background: var(--cds-layer-hover);
		color: var(--cds-text-primary);
	}

	.view-btn.active {
		background: var(--cds-layer);
		color: var(--cds-interactive);
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
	}
</style>
