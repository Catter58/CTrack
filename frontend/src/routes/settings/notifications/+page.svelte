<script lang="ts">
	import {
		Breadcrumb,
		BreadcrumbItem,
		Tile,
		Toggle,
		Select,
		SelectItem,
		Button,
		InlineNotification,
		Loading
	} from 'carbon-components-svelte';
	import { Save } from 'carbon-icons-svelte';
	import api from '$lib/api/client';

	interface NotificationPreferences {
		notify_on_assign: boolean;
		notify_on_mention: boolean;
		notify_on_comment: boolean;
		notify_on_status_change: boolean;
		email_frequency: 'instant' | 'daily' | 'weekly';
	}

	let notifyOnAssign = $state(true);
	let notifyOnMention = $state(true);
	let notifyOnComment = $state(true);
	let notifyOnStatusChange = $state(true);
	let emailFrequency = $state<string>('instant');

	let isLoading = $state(true);
	let isSaving = $state(false);
	let successMessage = $state<string | null>(null);
	let errorMessage = $state<string | null>(null);

	async function loadPreferences(): Promise<void> {
		try {
			const prefs = await api.get<NotificationPreferences>('/api/users/me/notification-preferences');
			notifyOnAssign = prefs.notify_on_assign;
			notifyOnMention = prefs.notify_on_mention;
			notifyOnComment = prefs.notify_on_comment;
			notifyOnStatusChange = prefs.notify_on_status_change;
			emailFrequency = prefs.email_frequency;
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : 'Не удалось загрузить настройки';
		} finally {
			isLoading = false;
		}
	}

	async function handleSave(): Promise<void> {
		isSaving = true;
		successMessage = null;
		errorMessage = null;

		try {
			await api.patch('/api/users/me/notification-preferences', {
				notify_on_assign: notifyOnAssign,
				notify_on_mention: notifyOnMention,
				notify_on_comment: notifyOnComment,
				notify_on_status_change: notifyOnStatusChange,
				email_frequency: emailFrequency
			});

			successMessage = 'Настройки уведомлений сохранены';
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : 'Не удалось сохранить настройки';
		} finally {
			isSaving = false;
		}
	}

	$effect(() => {
		loadPreferences();
	});
</script>

<svelte:head>
	<title>Настройки уведомлений - CTrack</title>
</svelte:head>

<div class="settings-page">
	<Breadcrumb noTrailingSlash>
		<BreadcrumbItem href="/settings/profile">Настройки</BreadcrumbItem>
		<BreadcrumbItem href="/settings/notifications" isCurrentPage>Уведомления</BreadcrumbItem>
	</Breadcrumb>

	<h1>Настройки уведомлений</h1>

	{#if isLoading}
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

			{#if errorMessage}
				<InlineNotification
					kind="error"
					title="Ошибка"
					subtitle={errorMessage}
					on:close={() => (errorMessage = null)}
				/>
			{/if}

			<div class="form-section">
				<h3>Уведомления о задачах</h3>

				<div class="form-row">
					<Toggle
						bind:toggled={notifyOnAssign}
						labelText="Уведомлять при назначении задачи"
						labelA="Выкл"
						labelB="Вкл"
					/>
				</div>

				<div class="form-row">
					<Toggle
						bind:toggled={notifyOnMention}
						labelText="Уведомлять при упоминании"
						labelA="Выкл"
						labelB="Вкл"
					/>
				</div>

				<div class="form-row">
					<Toggle
						bind:toggled={notifyOnComment}
						labelText="Уведомлять о новых комментариях"
						labelA="Выкл"
						labelB="Вкл"
					/>
				</div>

				<div class="form-row">
					<Toggle
						bind:toggled={notifyOnStatusChange}
						labelText="Уведомлять об изменении статуса"
						labelA="Выкл"
						labelB="Вкл"
					/>
				</div>
			</div>

			<div class="form-section">
				<h3>Email-уведомления</h3>

				<div class="form-row">
					<Select
						bind:selected={emailFrequency}
						labelText="Частота email-уведомлений"
					>
						<SelectItem value="instant" text="Мгновенно" />
						<SelectItem value="daily" text="Ежедневный дайджест" />
						<SelectItem value="weekly" text="Еженедельный дайджест" />
					</Select>
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

	.form-actions {
		display: flex;
		justify-content: flex-end;
		padding-top: 1rem;
		border-top: 1px solid var(--cds-border-subtle);
	}
</style>
