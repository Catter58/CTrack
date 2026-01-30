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
	import { Save, Download, Checkmark } from 'carbon-icons-svelte';
	import { auth, user, isLoading as authLoading, type User } from '$lib/stores/auth';
	import { pwa, isInstalled } from '$lib/stores/pwa';
	import api from '$lib/api/client';
	import AvatarUploader from '$lib/components/AvatarUploader.svelte';

	let firstName = $state('');
	let lastName = $state('');

	let isSaving = $state(false);
	let isInstallingPwa = $state(false);
	let successMessage = $state<string | null>(null);
	let errorMessage = $state<string | null>(null);

	// Initialize form with user data
	$effect(() => {
		if ($user) {
			firstName = $user.first_name || '';
			lastName = $user.last_name || '';
		}
	});

	function handleAvatarUpdate(avatarUrl: string | null) {
		if ($user) {
			auth.updateUser({ avatar: avatarUrl });
			successMessage = avatarUrl ? 'Аватар обновлён' : 'Аватар удалён';
		}
	}

	async function handleSave() {
		if (!$user) return;

		isSaving = true;
		successMessage = null;
		errorMessage = null;

		try {
			const updated = await api.patch<User>(`/api/users/${$user.id}`, {
				first_name: firstName || null,
				last_name: lastName || null
			});

			// Update local user state
			auth.updateUser(updated);
			successMessage = 'Профиль успешно обновлён';
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : 'Не удалось сохранить профиль';
		} finally {
			isSaving = false;
		}
	}

	async function handleInstallPwa() {
		isInstallingPwa = true;
		try {
			const installed = await pwa.install();
			if (installed) {
				successMessage = 'CTrack успешно установлен';
			}
		} finally {
			isInstallingPwa = false;
		}
	}

	function handleResetDismissed() {
		pwa.resetDismissed();
		successMessage = 'Подсказка об установке снова будет показана';
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
				<h3>Аватар</h3>
				<AvatarUploader
					userId={$user.id}
					currentAvatar={$user.avatar}
					onUpdate={handleAvatarUpdate}
				/>
			</div>

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

		<Tile class="app-tile">
			<div class="form-section">
				<h3>Приложение</h3>

				<div class="app-install-section">
					{#if $isInstalled}
						<div class="install-status installed">
							<Checkmark size={20} />
							<span>CTrack установлен как приложение</span>
						</div>
					{:else}
						<p class="install-description">
							Установите CTrack как приложение для быстрого доступа с рабочего стола
						</p>
						<div class="install-actions">
							<Button
								kind="secondary"
								icon={Download}
								disabled={isInstallingPwa}
								on:click={handleInstallPwa}
							>
								{#if isInstallingPwa}
									Установка...
								{:else}
									Установить приложение
								{/if}
							</Button>
							<Button kind="ghost" size="small" on:click={handleResetDismissed}>
								Показать подсказку
							</Button>
						</div>
					{/if}
				</div>
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

	:global(.settings-page .app-tile) {
		margin-top: 1rem;
		padding: 1.5rem;
	}

	.app-install-section {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.install-description {
		color: var(--cds-text-secondary);
		font-size: 0.875rem;
		margin: 0;
	}

	.install-actions {
		display: flex;
		align-items: center;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.install-status {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
	}

	.install-status.installed {
		color: var(--cds-support-success, #24a148);
	}
</style>
