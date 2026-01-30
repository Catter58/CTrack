<script lang="ts">
	import { Tag } from 'carbon-components-svelte';
	import { Add, ChevronLeft, ChevronRight } from 'carbon-icons-svelte';
	import { dndzone, type DndEvent } from 'svelte-dnd-action';
	import { flip } from 'svelte/animate';
	import { IssueCard } from '$lib/components/board';
	import { isMobile } from '$lib/stores/mobile';
	import type { Issue, BoardColumn } from '$lib/stores/board';

	interface WorkflowTransition {
		id: string;
		from_status: { id: string; name: string };
		to_status: { id: string; name: string };
		name: string;
	}

	interface Assignee {
		id: number;
		username: string;
		full_name: string | null;
	}

	interface Props {
		columns: BoardColumn[];
		workflowTransitions: WorkflowTransition[];
		members: Assignee[];
		onStatusUpdate: (issueKey: string, statusId: string) => Promise<void>;
		onPriorityUpdate: (issueKey: string, priority: string) => Promise<void>;
		onAssigneeUpdate: (issueKey: string, assigneeId: number | null) => Promise<void>;
		onStoryPointsUpdate: (issueKey: string, storyPoints: number | null) => Promise<void>;
		onQuickCreate: (statusId: string) => void;
		onTransitionError?: (message: string, fromStatus: string, toStatus: string) => void;
	}

	let {
		columns,
		workflowTransitions,
		members,
		onStatusUpdate,
		onPriorityUpdate,
		onAssigneeUpdate,
		onStoryPointsUpdate,
		onQuickCreate,
		onTransitionError
	}: Props = $props();

	// Local state for columns - required for svelte-dnd-action to work properly
	let localColumns = $state<BoardColumn[]>([]);
	let draggedIssueId = $state<string | null>(null);
	const flipDurationMs = 200;

	// Mobile column navigation
	let currentColumnIndex = $state(0);
	let boardContainerRef: HTMLDivElement | null = $state(null);
	let touchStartX = $state(0);
	let touchCurrentX = $state(0);
	let isSwiping = $state(false);

	// Navigate to specific column on mobile
	function goToColumn(index: number) {
		if (index < 0 || index >= localColumns.length) return;
		currentColumnIndex = index;
		if (boardContainerRef && $isMobile) {
			const columnWidth = boardContainerRef.offsetWidth;
			boardContainerRef.scrollTo({
				left: index * columnWidth,
				behavior: 'smooth'
			});
		}
	}

	function goToPrevColumn() {
		goToColumn(currentColumnIndex - 1);
	}

	function goToNextColumn() {
		goToColumn(currentColumnIndex + 1);
	}

	// Touch handlers for swipe navigation
	function handleTouchStart(e: TouchEvent) {
		if (!$isMobile) return;
		touchStartX = e.touches[0].clientX;
		touchCurrentX = touchStartX;
		isSwiping = true;
	}

	function handleTouchMove(e: TouchEvent) {
		if (!$isMobile || !isSwiping) return;
		touchCurrentX = e.touches[0].clientX;
	}

	function handleTouchEnd() {
		if (!$isMobile || !isSwiping) return;
		isSwiping = false;

		const swipeDistance = touchStartX - touchCurrentX;
		const threshold = 50;

		if (swipeDistance > threshold) {
			goToNextColumn();
		} else if (swipeDistance < -threshold) {
			goToPrevColumn();
		}

		touchStartX = 0;
		touchCurrentX = 0;
	}

	// Update current column index on scroll (for snap scrolling)
	function handleScroll() {
		if (!boardContainerRef || !$isMobile) return;
		const columnWidth = boardContainerRef.offsetWidth;
		const newIndex = Math.round(boardContainerRef.scrollLeft / columnWidth);
		if (newIndex !== currentColumnIndex && newIndex >= 0 && newIndex < localColumns.length) {
			currentColumnIndex = newIndex;
		}
	}

	// Sync local columns when props change (but not during drag)
	$effect(() => {
		if (!draggedIssueId && columns.length > 0) {
			localColumns = columns.map(col => ({
				...col,
				issues: [...col.issues]
			}));
		}
	});

	// Get the dragged issue from its ID
	let draggedIssue = $derived.by(() => {
		if (!draggedIssueId) return null;
		for (const col of localColumns) {
			const found = col.issues.find(i => i.id === draggedIssueId);
			if (found) return found;
		}
		return null;
	});

	// Get allowed target status IDs for the currently dragged issue
	let allowedTargetStatusIds = $derived.by(() => {
		if (!draggedIssue) return [];
		if (workflowTransitions.length === 0) return [];
		const currentStatusId = draggedIssue.status.id;
		return workflowTransitions
			.filter((t) => t.from_status.id === currentStatusId)
			.map((t) => t.to_status.id);
	});

	// Check if a column is a valid drop target for the dragged issue
	function isValidDropTarget(columnStatusId: string): boolean {
		if (!draggedIssue) return false;
		if (draggedIssue.status.id === columnStatusId) return false;
		if (workflowTransitions.length === 0) return true;
		return allowedTargetStatusIds.includes(columnStatusId);
	}

	function getColumnStoryPoints(column: BoardColumn): number {
		return column.issues.reduce((sum, issue) => sum + (issue.story_points || 0), 0);
	}

	// svelte-dnd-action handlers
	function handleDndConsider(columnStatusId: string, e: CustomEvent<DndEvent<Issue>>) {
		const columnIndex = localColumns.findIndex(c => c.status.id === columnStatusId);
		if (columnIndex !== -1) {
			localColumns[columnIndex] = {
				...localColumns[columnIndex],
				issues: e.detail.items
			};
		}
		if (e.detail.info.trigger === 'dragStarted') {
			draggedIssueId = e.detail.info.id as string;
		}
	}

	async function handleDndFinalize(columnStatusId: string, e: CustomEvent<DndEvent<Issue>>) {
		const columnIndex = localColumns.findIndex(c => c.status.id === columnStatusId);
		if (columnIndex === -1) return;

		const column = localColumns[columnIndex];

		localColumns[columnIndex] = {
			...column,
			issues: e.detail.items
		};

		const movedIssueId = e.detail.info.id as string;
		const movedIssue = e.detail.items.find(i => i.id === movedIssueId);

		draggedIssueId = null;

		if (movedIssue && movedIssue.status.id !== columnStatusId) {
			const transition = workflowTransitions.find(
				t => t.from_status.id === movedIssue.status.id && t.to_status.id === columnStatusId
			);

			if (workflowTransitions.length > 0 && !transition) {
				onTransitionError?.(
					'Переход недоступен',
					movedIssue.status.name,
					column.status.name
				);
				// Parent should reload board to revert
				return;
			}

			await onStatusUpdate(movedIssue.key, columnStatusId);
		}
	}
</script>

<!-- Mobile column indicator and navigation -->
{#if $isMobile && localColumns.length > 0}
	<div class="mobile-column-nav">
		<button
			class="nav-arrow"
			onclick={goToPrevColumn}
			disabled={currentColumnIndex === 0}
			aria-label="Предыдущая колонка"
		>
			<ChevronLeft size={24} />
		</button>
		<div class="column-indicators">
			{#each localColumns as column, index (column.status.id)}
				<button
					class="indicator"
					class:active={index === currentColumnIndex}
					style="--status-color: {column.status.color}"
					onclick={() => goToColumn(index)}
					aria-label={column.status.name}
					aria-current={index === currentColumnIndex ? 'true' : undefined}
				>
					<span class="indicator-dot"></span>
					<span class="indicator-label">{column.status.name}</span>
				</button>
			{/each}
		</div>
		<button
			class="nav-arrow"
			onclick={goToNextColumn}
			disabled={currentColumnIndex === localColumns.length - 1}
			aria-label="Следующая колонка"
		>
			<ChevronRight size={24} />
		</button>
	</div>
{/if}

<div
	class="board-container"
	class:mobile={$isMobile}
	bind:this={boardContainerRef}
	ontouchstart={handleTouchStart}
	ontouchmove={handleTouchMove}
	ontouchend={handleTouchEnd}
	onscroll={handleScroll}
>
	<div class="board">
		{#each localColumns as column (column.status.id)}
			<div
				class="column"
				class:drag-over={draggedIssueId && isValidDropTarget(column.status.id)}
				class:drag-invalid={draggedIssueId && !isValidDropTarget(column.status.id) && draggedIssue?.status.id !== column.status.id}
				role="region"
				aria-label={column.status.name}
			>
				<div class="column-header">
					<span class="column-title">
						<span class="status-dot" style="background-color: {column.status.color}"></span>
						{column.status.name}
					</span>
					<div class="column-actions">
						<button
							class="quick-add-btn"
							title="Добавить задачу в {column.status.name}"
							onclick={() => onQuickCreate(column.status.id)}
						>
							<Add size={16} />
						</button>
						<div class="column-stats">
							<Tag size="sm">{column.count}</Tag>
							{#if getColumnStoryPoints(column) > 0}
								<Tag size="sm" type="outline">{getColumnStoryPoints(column)} SP</Tag>
							{/if}
						</div>
					</div>
				</div>
				<div
					class="column-content"
					use:dndzone={{
						items: column.issues,
						flipDurationMs,
						type: 'board-issues'
					}}
					onconsider={(e) => handleDndConsider(column.status.id, e)}
					onfinalize={(e) => handleDndFinalize(column.status.id, e)}
				>
					{#each column.issues as issue (issue.id)}
						<article class="dnd-item" animate:flip={{ duration: flipDurationMs }}>
							<IssueCard
								{issue}
								isDragging={draggedIssueId === issue.id}
								onUpdateStoryPoints={onStoryPointsUpdate}
								onUpdatePriority={onPriorityUpdate}
								onUpdateAssignee={onAssigneeUpdate}
								availableAssignees={members}
							/>
						</article>
					{/each}
				</div>
			</div>
		{/each}
	</div>
</div>

<style>
	.board-container {
		flex: 1;
		overflow-x: auto;
		padding: 1rem;
	}

	.board {
		display: flex;
		gap: 1rem;
		height: 100%;
		min-width: max-content;
	}

	.column {
		width: 320px;
		min-width: 320px;
		background: var(--cds-layer);
		border-radius: 8px;
		display: flex;
		flex-direction: column;
		max-height: 100%;
		transition:
			box-shadow 0.2s ease,
			background-color 0.2s ease,
			opacity 0.2s ease,
			transform 0.2s ease;
	}

	.column.drag-over {
		box-shadow: inset 0 0 0 2px var(--cds-support-success);
		background: rgba(36, 161, 72, 0.15);
		transform: scale(1.01);
	}

	.column.drag-invalid {
		opacity: 0.4;
		box-shadow: inset 0 0 0 1px var(--cds-support-error);
		background: rgba(218, 30, 40, 0.05);
	}

	.column-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		border-bottom: 1px solid var(--cds-border-subtle);
	}

	.column-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-weight: 600;
	}

	.column-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.quick-add-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		border: none;
		border-radius: 4px;
		background: transparent;
		color: var(--cds-text-secondary);
		cursor: pointer;
		transition: all 0.1s ease;
	}

	.quick-add-btn:hover {
		background: var(--cds-layer-hover);
		color: var(--cds-interactive);
	}

	.column-stats {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.status-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
	}

	.column-content {
		flex: 1;
		overflow-y: auto;
		padding: 0.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		min-height: 100px;
		transition: background-color 0.2s ease;
	}

	/* Mobile column navigation */
	.mobile-column-nav {
		display: none;
	}

	@media (max-width: 768px) {
		.mobile-column-nav {
			display: flex;
			align-items: center;
			justify-content: space-between;
			padding: 0.5rem 0.75rem;
			background: var(--cds-layer);
			border-bottom: 1px solid var(--cds-border-subtle);
			position: sticky;
			top: 0;
			z-index: 10;
		}

		.nav-arrow {
			display: flex;
			align-items: center;
			justify-content: center;
			width: 36px;
			height: 36px;
			border: none;
			border-radius: 50%;
			background: transparent;
			color: var(--cds-text-primary);
			cursor: pointer;
			transition: all 0.15s ease;
		}

		.nav-arrow:hover:not(:disabled) {
			background: var(--cds-layer-hover);
		}

		.nav-arrow:disabled {
			color: var(--cds-text-disabled);
			cursor: not-allowed;
		}

		.column-indicators {
			display: flex;
			align-items: center;
			gap: 0.25rem;
			overflow-x: auto;
			max-width: calc(100% - 80px);
			scrollbar-width: none;
			-ms-overflow-style: none;
		}

		.column-indicators::-webkit-scrollbar {
			display: none;
		}

		.indicator {
			display: flex;
			flex-direction: column;
			align-items: center;
			gap: 0.25rem;
			padding: 0.25rem 0.5rem;
			border: none;
			background: transparent;
			cursor: pointer;
			transition: all 0.15s ease;
			min-width: 0;
			flex-shrink: 0;
		}

		.indicator-dot {
			width: 8px;
			height: 8px;
			border-radius: 50%;
			background: var(--status-color, var(--cds-border-subtle));
			opacity: 0.5;
			transition: all 0.15s ease;
		}

		.indicator.active .indicator-dot {
			opacity: 1;
			transform: scale(1.25);
		}

		.indicator-label {
			font-size: 0.625rem;
			color: var(--cds-text-secondary);
			white-space: nowrap;
			max-width: 60px;
			overflow: hidden;
			text-overflow: ellipsis;
		}

		.indicator.active .indicator-label {
			color: var(--cds-text-primary);
			font-weight: 600;
		}

		/* Mobile board container */
		.board-container.mobile {
			padding: 0;
			scroll-snap-type: x mandatory;
			-webkit-overflow-scrolling: touch;
			scrollbar-width: none;
			-ms-overflow-style: none;
		}

		.board-container.mobile::-webkit-scrollbar {
			display: none;
		}

		.board-container.mobile .board {
			gap: 0;
		}

		.board-container.mobile .column {
			width: 100vw;
			min-width: 100vw;
			max-width: 100vw;
			scroll-snap-align: start;
			border-radius: 0;
			flex-shrink: 0;
		}

		.board-container.mobile .column-header {
			position: sticky;
			top: 0;
			z-index: 5;
			background: var(--cds-layer);
		}

		.board-container.mobile .column-content {
			padding: 0.75rem;
			min-height: calc(100vh - 200px);
		}
	}
</style>
