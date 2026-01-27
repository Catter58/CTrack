<script lang="ts">
	import {
		Modal,
		RadioButtonGroup,
		RadioButton,
		InlineNotification
	} from 'carbon-components-svelte';
	import type { Sprint } from '$lib/stores/sprints';

	interface Props {
		open: boolean;
		sprint: Sprint;
		plannedSprints: Sprint[];
		incompleteCount: number;
		onClose: () => void;
		onComplete: (moveIncompleteTo: string | null) => Promise<void>;
	}

	let {
		open,
		sprint,
		plannedSprints = [],
		incompleteCount = 0,
		onClose,
		onComplete
	}: Props = $props();

	let moveTarget = $state<string>('backlog');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	$effect(() => {
		if (open) {
			moveTarget = 'backlog';
			error = null;
		}
	});

	async function handleComplete() {
		isSubmitting = true;
		error = null;

		try {
			const target = moveTarget === 'backlog' ? 'backlog' : moveTarget;
			await onComplete(target);
			onClose();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Произошла ошибка';
		} finally {
			isSubmitting = false;
		}
	}
</script>

<Modal
	{open}
	modalHeading="Завершить спринт"
	primaryButtonText="Завершить"
	secondaryButtonText="Отмена"
	primaryButtonDisabled={isSubmitting}
	danger
	on:click:button--primary={handleComplete}
	on:click:button--secondary={onClose}
	on:close={onClose}
>
	<div class="complete-content">
		{#if error}
			<InlineNotification
				kind="error"
				title="Ошибка"
				subtitle={error}
				hideCloseButton
			/>
		{/if}

		<p>Вы уверены, что хотите завершить спринт <strong>{sprint.name}</strong>?</p>

		{#if incompleteCount > 0}
			<div class="incomplete-warning">
				<InlineNotification
					kind="warning"
					title="Незавершённые задачи"
					subtitle={`В спринте осталось ${incompleteCount} незавершённых задач`}
					hideCloseButton
				/>

				<p class="move-label">Куда перенести незавершённые задачи?</p>

				<RadioButtonGroup
					legendText=""
					bind:selected={moveTarget}
					orientation="vertical"
				>
					<RadioButton labelText="В бэклог" value="backlog" />
					{#each plannedSprints as plannedSprint (plannedSprint.id)}
						<RadioButton
							labelText={plannedSprint.name}
							value={plannedSprint.id}
						/>
					{/each}
				</RadioButtonGroup>
			</div>
		{:else}
			<p class="success-message">Все задачи в спринте завершены.</p>
		{/if}
	</div>
</Modal>

<style>
	.complete-content {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.incomplete-warning {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.move-label {
		font-weight: 500;
		margin-bottom: 0.25rem;
	}

	.success-message {
		color: var(--cds-support-success);
	}
</style>
