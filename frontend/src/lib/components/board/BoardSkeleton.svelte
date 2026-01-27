<script lang="ts">
	import { SkeletonText, SkeletonPlaceholder } from 'carbon-components-svelte';

	interface Props {
		columns?: number;
		cardsPerColumn?: number;
	}

	let { columns = 4, cardsPerColumn = 3 }: Props = $props();

	// Generate arrays of indices for iteration
	let columnIndices = $derived([...Array(columns).keys()]);
	let cardIndices = $derived([...Array(cardsPerColumn).keys()]);
</script>

<div class="board-skeleton">
	{#each columnIndices as colIndex (colIndex)}
		<div class="column-skeleton">
			<div class="column-header-skeleton">
				<SkeletonText width="60%" />
				<SkeletonText width="20%" />
			</div>
			<div class="column-content-skeleton">
				{#each cardIndices as cardIndex (cardIndex)}
					<div class="card-skeleton">
						<div class="card-header-skeleton">
							<SkeletonText width="40%" />
							<SkeletonText width="25%" />
						</div>
						<SkeletonText paragraph lines={2} />
						<div class="card-footer-skeleton">
							<SkeletonText width="30%" />
							<SkeletonPlaceholder style="width: 24px; height: 24px; border-radius: 50%;" />
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/each}
</div>

<style>
	.board-skeleton {
		display: flex;
		gap: 1rem;
		padding: 1rem;
		overflow-x: auto;
	}

	.column-skeleton {
		width: 320px;
		min-width: 320px;
		background: var(--cds-layer);
		border-radius: 8px;
		overflow: hidden;
	}

	.column-header-skeleton {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		border-bottom: 1px solid var(--cds-border-subtle);
	}

	.column-content-skeleton {
		padding: 0.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.card-skeleton {
		background: var(--cds-field);
		border: 1px solid var(--cds-border-subtle);
		border-radius: 6px;
		padding: 0.75rem;
	}

	.card-header-skeleton {
		display: flex;
		justify-content: space-between;
		margin-bottom: 0.5rem;
	}

	.card-footer-skeleton {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-top: 0.5rem;
	}
</style>
