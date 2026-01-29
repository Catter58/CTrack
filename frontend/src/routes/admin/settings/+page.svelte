<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		Breadcrumb,
		BreadcrumbItem,
		Tile,
		TextInput,
		Toggle,
		Select,
		SelectItem,
		Button,
		Loading,
		InlineNotification
	} from 'carbon-components-svelte';
	import { Save } from 'carbon-icons-svelte';
	import { user, isLoading as authLoading } from '$lib/stores/auth';
	import api from '$lib/api/client';

	interface SystemSettings {
		organization_name: string;
		default_language: string;
		allow_registration: boolean;
		smtp_settings: Record<string, unknown>;
		storage_settings: Record<string, unknown>;
		updated_at: string;
	}

	let settings = $state<SystemSettings | null>(null);
	let isLoading = $state(true);
	let isSaving = $state(false);
	let error = $state<string | null>(null);
	let successMessage = $state<string | null>(null);

	let organizationName = $state('');
	let defaultLanguage = $state('ru');
	let allowRegistration = $state(true);

	onMount(async () => {
		if (!$authLoading && !$user?.is_staff) {
			goto('/');
			return;
		}

		await loadSettings();
	});

	$effect(() => {
		if (!$authLoading && !$user?.is_staff) {
			goto('/');
		}
	});

	async function loadSettings(): Promise<void> {
		isLoading = true;
		error = null;

		try {
			settings = await api.get<SystemSettings>('/api/admin/settings');
			organizationName = settings.organization_name;
			defaultLanguage = settings.default_language;
			allowRegistration = settings.allow_registration;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Не удалось загрузить настройки';
		} finally {
			isLoading = false;
		}
	}

	async function handleSave(): Promise<void> {
		isSaving = true;
		error = null;
		successMessage = null;

		try {
			settings = await api.patch<SystemSettings>('/api/admin/settings', {
				organization_name: organizationName,
				default_language: defaultLanguage,
				allow_registration: allowRegistration
			});
			successMessage = 'Настройки успешно сохранены';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Не удалось сохранить настройки';
		} finally {
			isSaving = false;
		}
	}
</script>

<svelte:head>
	<title>Настройки системы - CTrack</title>
</svelte:head>

<div class="settings-page">
	<Breadcrumb noTrailingSlash>
		<BreadcrumbItem href="/">Главная</BreadcrumbItem>
		<BreadcrumbItem href="/admin">Администрирование</BreadcrumbItem>
		<BreadcrumbItem href="/admin/settings" isCurrentPage>Настройки</BreadcrumbItem>
	</Breadcrumb>

	<h1>Настройки системы</h1>

	{#if isLoading || $authLoading}
		<div class="loading-container">
			<Loading withOverlay={false} />
		</div>
	{:else}
		<Tile>
			{#if successMessage}
				<InlineNotification
					kind="success"
					title="Успешно"
					subtitle={successMessage}
					on:close={() => (successMessage = null)}
				/>
			{/if}

			{#if error}
				<InlineNotification
					kind="error"
					title="Ошибка"
					subtitle={error}
					on:close={() => (error = null)}
				/>
			{/if}

			<div class="form-section">
				<h3>Основные настройки</h3>

				<div class="form-row">
					<TextInput
						bind:value={organizationName}
						labelText="Название организации"
						placeholder="Введите название"
					/>
				</div>

				<div class="form-row">
					<Select bind:selected={defaultLanguage} labelText="Язык по умолчанию">
						<SelectItem value="ru" text="Русский" />
						<SelectItem value="en" text="English" />
					</Select>
				</div>

				<div class="form-row toggle-row">
					<Toggle
						bind:toggled={allowRegistration}
						labelText="Разрешить регистрацию"
						labelA="Выкл"
						labelB="Вкл"
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

	.toggle-row {
		padding-top: 0.5rem;
	}

	.form-actions {
		display: flex;
		justify-content: flex-end;
		padding-top: 1rem;
		border-top: 1px solid var(--cds-border-subtle);
	}
</style>
