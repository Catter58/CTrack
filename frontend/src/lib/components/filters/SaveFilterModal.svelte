<script lang="ts">
	import { Modal, TextInput, Checkbox, InlineNotification } from 'carbon-components-svelte';
	import type { FilterValues, CreateFilterData } from '$lib/stores/filters';

	interface Props {
		open: boolean;
		filters: FilterValues;
		onClose: () => void;
		onSave: (data: CreateFilterData) => Promise<void>;
	}

	let { open, filters, onClose, onSave }: Props = $props();

	let name = $state('');
	let isShared = $state(false);
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	$effect(() => {
		if (open) {
			name = '';
			isShared = false;
			error = null;
		}
	});

	async function handleSubmit() {
		if (!name.trim()) {
			error = 'Укажите название фильтра';
			return;
		}

		isSubmitting = true;
		error = null;

		try {
			const data: CreateFilterData = {
				name: name.trim(),
				is_shared: isShared,
				filters
			};
			await onSave(data);
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
	modalHeading="Сохранить фильтр"
	primaryButtonText="Сохранить"
	secondaryButtonText="Отмена"
	primaryButtonDisabled={isSubmitting || !name.trim()}
	on:click:button--primary={handleSubmit}
	on:click:button--secondary={onClose}
	on:close={onClose}
>
	<div class="form-content">
		{#if error}
			<InlineNotification kind="error" title="Ошибка" subtitle={error} hideCloseButton />
		{/if}

		<TextInput
			labelText="Название фильтра"
			placeholder="Например: Мои задачи в работе"
			bind:value={name}
			required
		/>

		<Checkbox labelText="Доступен всей команде" bind:checked={isShared} />
	</div>
</Modal>

<style>
	.form-content {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
</style>
