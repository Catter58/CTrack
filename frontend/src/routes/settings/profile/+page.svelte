<script lang="ts">
	import {
		Breadcrumb,
		BreadcrumbItem,
		Tile,
		TextInput,
		Button,
		InlineNotification,
		Loading
	} from 'carbon-components-svelte';
	import { Save } from 'carbon-icons-svelte';
	import { user, isLoading as authLoading } from '$lib/stores/auth';
	import api from '$lib/api/client';

	let firstName = $state('');
	let lastName = $state('');
	let avatarUrl = $state('');

	let isSaving = $state(false);
	let successMessage = $state<string | null>(null);
	let errorMessage = $state<string | null>(null);

	// Initialize form with user data
	$effect(() => {
		if ($user) {
			firstName = $user.first_name || '';
			lastName = $user.last_name || '';
			avatarUrl = $user.avatar_url || '';
		}
	});

	async function handleSave() {
		if (!$user) return;

		isSaving = true;
		successMessage = null;
		errorMessage = null;

		try {
			const updated = await api.patch(`/api/users/${$user.id}`, {
				first_name: firstName || null,
				last_name: lastName || null,
				avatar_url: avatarUrl || null
			});

			// Update local user state
			user.set(updated);
			successMessage = 'Профиль успешно обновлён';
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : 'Не удалось сохранить профиль';
		} finally {
			isSaving = false;
		}
	}
</script>

<svelte:head>
	<title>Профиль - CTrack</title>
</svelte:head>

<div class="settings-page">
	<Breadcrumb noTrailingSlash>
		<BreadcrumbItem href="/">Главная</BreadcrumbItem>
		<BreadcrumbItem href="/settings/profile" isCurrentPage>Профиль</BreadcrumbItem>
	</Breadcrumb>

	<h1>Настройки профиля</h1>

	{#if $authLoading}
		<div class="loading-container">
			<Loading withOverlay={false} />
		</div>
	{:else if $user}
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
				<h3>Основная информация</h3>

				<div class="form-row">
					<TextInput
						value={$user.username}
						labelText="Имя пользователя"
						disabled
						helperText="Имя пользователя нельзя изменить"
					/>
				</div>

				<div class="form-row">
					<TextInput
						value={$user.email}
						labelText="Email"
						disabled
						helperText="Email нельзя изменить"
					/>
				</div>

				<div class="form-row two-columns">
					<TextInput
						bind:value={firstName}
						labelText="Имя"
						placeholder="Введите имя"
					/>
					<TextInput
						bind:value={lastName}
						labelText="Фамилия"
						placeholder="Введите фамилию"
					/>
				</div>

				<div class="form-row">
					<TextInput
						bind:value={avatarUrl}
						labelText="URL аватара"
						placeholder="https://example.com/avatar.jpg"
					/>
				</div>
			</div>

			<div class="form-actions">
				<Button icon={Save} disabled={isSaving} on:click={handleSave}>
					{#if isSaving}
						Сохранение...
					{:else}
						Сохранить
					{/if}
				</Button>
			</div>
		</Tile>
	{/if}
</div>

<style>
	.settings-page {
		padding: 1rem 2rem;
		max-width: 800px;
	}

	h1 {
		margin: 1.5rem 0;
		font-size: 1.75rem;
		font-weight: 600;
	}

	h3 {
		font-size: 1.125rem;
		font-weight: 600;
		margin: 0 0 1.5rem;
	}

	.loading-container {
		display: flex;
		justify-content: center;
		padding: 3rem;
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

	.form-row.two-columns {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}

	.form-actions {
		display: flex;
		justify-content: flex-end;
		padding-top: 1rem;
		border-top: 1px solid var(--cds-border-subtle);
	}
</style>
