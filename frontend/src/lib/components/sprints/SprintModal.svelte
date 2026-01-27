<script lang="ts">
	import {
		Modal,
		TextInput,
		TextArea,
		DatePicker,
		DatePickerInput,
		InlineNotification
	} from 'carbon-components-svelte';
	import type { Sprint, CreateSprintData, UpdateSprintData } from '$lib/stores/sprints';

	interface Props {
		open: boolean;
		sprint?: Sprint | null;
		onClose: () => void;
		onSave: (data: CreateSprintData | UpdateSprintData) => Promise<void>;
	}

	let { open, sprint = null, onClose, onSave }: Props = $props();

	let name = $state('');
	let goal = $state('');
	let startDate = $state('');
	let endDate = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	const isEdit = $derived(!!sprint);
	const modalHeading = $derived(isEdit ? 'Редактировать спринт' : 'Создать спринт');
	const submitLabel = $derived(isEdit ? 'Сохранить' : 'Создать');

	$effect(() => {
		if (open && sprint) {
			name = sprint.name;
			goal = sprint.goal || '';
			startDate = sprint.start_date;
			endDate = sprint.end_date;
		} else if (open && !sprint) {
			const today = new Date();
			const twoWeeksLater = new Date(today.getTime() + 14 * 24 * 60 * 60 * 1000);
			name = '';
			goal = '';
			startDate = today.toISOString().split('T')[0];
			endDate = twoWeeksLater.toISOString().split('T')[0];
		}
		error = null;
	});

	function validateDates(): boolean {
		if (!startDate || !endDate) {
			error = 'Укажите даты начала и окончания';
			return false;
		}
		if (new Date(startDate) >= new Date(endDate)) {
			error = 'Дата начала должна быть раньше даты окончания';
			return false;
		}
		return true;
	}

	async function handleSubmit() {
		if (!name.trim()) {
			error = 'Укажите название спринта';
			return;
		}
		if (!validateDates()) {
			return;
		}

		isSubmitting = true;
		error = null;

		try {
			const data: CreateSprintData | UpdateSprintData = {
				name: name.trim(),
				goal: goal.trim(),
				start_date: startDate,
				end_date: endDate
			};
			await onSave(data);
			onClose();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Произошла ошибка';
		} finally {
			isSubmitting = false;
		}
	}

	function handleStartDateChange(e: CustomEvent) {
		const dates = e.detail.dateStr;
		if (dates) {
			startDate = dates;
		}
	}

	function handleEndDateChange(e: CustomEvent) {
		const dates = e.detail.dateStr;
		if (dates) {
			endDate = dates;
		}
	}
</script>

<Modal
	{open}
	modalHeading={modalHeading}
	primaryButtonText={submitLabel}
	secondaryButtonText="Отмена"
	primaryButtonDisabled={isSubmitting}
	on:click:button--primary={handleSubmit}
	on:click:button--secondary={onClose}
	on:close={onClose}
>
	<div class="form-content">
		{#if error}
			<InlineNotification
				kind="error"
				title="Ошибка"
				subtitle={error}
				hideCloseButton
			/>
		{/if}

		<TextInput
			labelText="Название"
			placeholder="Sprint 1"
			bind:value={name}
			required
		/>

		<TextArea
			labelText="Цель спринта"
			placeholder="Основные цели и задачи спринта..."
			bind:value={goal}
			rows={3}
		/>

		<div class="date-row">
			<DatePicker
				datePickerType="single"
				dateFormat="Y-m-d"
				value={startDate}
				on:change={handleStartDateChange}
			>
				<DatePickerInput labelText="Дата начала" placeholder="ГГГГ-ММ-ДД" />
			</DatePicker>

			<DatePicker
				datePickerType="single"
				dateFormat="Y-m-d"
				value={endDate}
				on:change={handleEndDateChange}
			>
				<DatePickerInput labelText="Дата окончания" placeholder="ГГГГ-ММ-ДД" />
			</DatePicker>
		</div>
	</div>
</Modal>

<style>
	.form-content {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.date-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}
</style>
