<script lang="ts">
	import {
		Breadcrumb,
		BreadcrumbItem,
		Tile,
		PasswordInput,
		Button,
		InlineNotification
	} from 'carbon-components-svelte';
	import { Save } from 'carbon-icons-svelte';
	import { user } from '$lib/stores/auth';
	import api from '$lib/api/client';

	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');

	let isSaving = $state(false);
	let successMessage = $state<string | null>(null);
	let errorMessage = $state<string | null>(null);

	// Validation
	let currentPasswordError = $state('');
	let newPasswordError = $state('');
	let confirmPasswordError = $state('');

	function validate(): boolean {
		currentPasswordError = '';
		newPasswordError = '';
		confirmPasswordError = '';

		if (!currentPassword) {
			currentPasswordError = 'Введите текущий пароль';
			return false;
		}

		if (!newPassword) {
			newPasswordError = 'Введите новый пароль';
			return false;
		}

		if (newPassword.length < 8) {
			newPasswordError = 'Пароль должен содержать минимум 8 символов';
			return false;
		}

		if (newPassword !== confirmPassword) {
			confirmPasswordError = 'Пароли не совпадают';
			return false;
		}

		return true;
	}

	async function handleSubmit() {
		if (!$user || !validate()) return;

		isSaving = true;
		successMessage = null;
		errorMessage = null;

		try {
			await api.patch(`/api/users/${$user.id}/password`, {
				current_password: currentPassword,
				new_password: newPassword
			});

			successMessage = 'Пароль успешно изменён';

			// Clear form
			currentPassword = '';
			newPassword = '';
			confirmPassword = '';
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : 'Не удалось изменить пароль';
		} finally {
			isSaving = false;
		}
	}
</script>

<svelte:head>
	<title>Смена пароля - CTrack</title>
</svelte:head>

<div class="settings-page">
	<Breadcrumb noTrailingSlash>
		<BreadcrumbItem href="/">Главная</BreadcrumbItem>
		<BreadcrumbItem href="/settings/password" isCurrentPage>Смена пароля</BreadcrumbItem>
	</Breadcrumb>

	<h1>Смена пароля</h1>

	<Tile>
		{#if successMessage}
			<InlineNotification
				kind="success"
				title="Успешно"
				subtitle={successMessage}
				on:close={() => (successMessage = null)}
			/>
		{/if}

		{#if errorMessage}
			<InlineNotification
				kind="error"
				title="Ошибка"
				subtitle={errorMessage}
				on:close={() => (errorMessage = null)}
			/>
		{/if}

		<div class="form-section">
			<div class="form-row">
				<PasswordInput
					bind:value={currentPassword}
					labelText="Текущий пароль"
					placeholder="Введите текущий пароль"
					invalid={!!currentPasswordError}
					invalidText={currentPasswordError}
				/>
			</div>

			<div class="form-row">
				<PasswordInput
					bind:value={newPassword}
					labelText="Новый пароль"
					placeholder="Введите новый пароль"
					helperText="Минимум 8 символов"
					invalid={!!newPasswordError}
					invalidText={newPasswordError}
				/>
			</div>

			<div class="form-row">
				<PasswordInput
					bind:value={confirmPassword}
					labelText="Подтверждение пароля"
					placeholder="Повторите новый пароль"
					invalid={!!confirmPasswordError}
					invalidText={confirmPasswordError}
				/>
			</div>
		</div>

		<div class="form-actions">
			<Button icon={Save} disabled={isSaving} on:click={handleSubmit}>
				{#if isSaving}
					Сохранение...
				{:else}
					Изменить пароль
				{/if}
			</Button>
		</div>
	</Tile>
</div>

<style>
	.settings-page {
		padding: 1rem 2rem;
		max-width: 600px;
	}

	h1 {
		margin: 1.5rem 0;
		font-size: 1.75rem;
		font-weight: 600;
	}

	:global(.settings-page .bx--tile) {
		padding: 1.5rem;
	}

	.form-section {
		margin-bottom: 2rem;
	}

	.form-row {
		margin-bottom: 1rem;
	}

	.form-actions {
		display: flex;
		justify-content: flex-end;
		padding-top: 1rem;
		border-top: 1px solid var(--cds-border-subtle);
	}
</style>
