<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		Breadcrumb,
		BreadcrumbItem,
		Tile,
		TextInput,
		PasswordInput,
		Toggle,
		Select,
		SelectItem,
		Button,
		NumberInput,
		Loading,
		InlineNotification
	} from 'carbon-components-svelte';
	import { Save, Email, Checkmark, Close } from 'carbon-icons-svelte';
	import { user, isLoading as authLoading } from '$lib/stores/auth';
	import api from '$lib/api/client';

	interface SMTPSettings {
		enabled: boolean;
		host: string;
		port: number;
		username: string;
		password: string;
		use_tls: boolean;
		use_ssl: boolean;
		from_email: string;
		from_name: string;
	}

	interface SystemSettings {
		organization_name: string;
		default_language: string;
		allow_registration: boolean;
		smtp_settings: SMTPSettings;
		storage_settings: Record<string, unknown>;
		updated_at: string;
	}

	interface SMTPTestResult {
		success: boolean;
		message: string;
	}

	let settings = $state<SystemSettings | null>(null);
	let isLoading = $state(true);
	let isSaving = $state(false);
	let isTesting = $state(false);
	let error = $state<string | null>(null);
	let successMessage = $state<string | null>(null);
	let smtpTestResult = $state<SMTPTestResult | null>(null);

	// General settings
	let organizationName = $state('');
	let defaultLanguage = $state('ru');
	let allowRegistration = $state(true);

	// SMTP settings
	let smtpEnabled = $state(false);
	let smtpHost = $state('');
	let smtpPort = $state(587);
	let smtpUsername = $state('');
	let smtpPassword = $state('');
	let smtpUseTls = $state(true);
	let smtpUseSsl = $state(false);
	let smtpFromEmail = $state('');
	let smtpFromName = $state('');
	let smtpTestRecipient = $state('');

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

			// Load SMTP settings
			const smtp = settings.smtp_settings || {};
			smtpEnabled = smtp.enabled || false;
			smtpHost = smtp.host || '';
			smtpPort = smtp.port || 587;
			smtpUsername = smtp.username || '';
			smtpPassword = smtp.password || '';
			smtpUseTls = smtp.use_tls !== false;
			smtpUseSsl = smtp.use_ssl || false;
			smtpFromEmail = smtp.from_email || '';
			smtpFromName = smtp.from_name || '';
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
		smtpTestResult = null;

		try {
			const smtpSettings: SMTPSettings = {
				enabled: smtpEnabled,
				host: smtpHost,
				port: smtpPort,
				username: smtpUsername,
				password: smtpPassword,
				use_tls: smtpUseTls,
				use_ssl: smtpUseSsl,
				from_email: smtpFromEmail,
				from_name: smtpFromName
			};

			settings = await api.patch<SystemSettings>('/api/admin/settings', {
				organization_name: organizationName,
				default_language: defaultLanguage,
				allow_registration: allowRegistration,
				smtp_settings: smtpSettings
			});
			successMessage = 'Настройки успешно сохранены';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Не удалось сохранить настройки';
		} finally {
			isSaving = false;
		}
	}

	async function handleTestSmtp(): Promise<void> {
		isTesting = true;
		smtpTestResult = null;
		error = null;

		try {
			smtpTestResult = await api.post<SMTPTestResult>('/api/admin/settings/smtp/test', {
				host: smtpHost,
				port: smtpPort,
				username: smtpUsername,
				password: smtpPassword,
				use_tls: smtpUseTls,
				use_ssl: smtpUseSsl,
				from_email: smtpFromEmail,
				test_recipient: smtpTestRecipient
			});
		} catch (err) {
			smtpTestResult = {
				success: false,
				message: err instanceof Error ? err.message : 'Ошибка тестирования соединения'
			};
		} finally {
			isTesting = false;
		}
	}

	// Handle TLS/SSL mutual exclusion
	function handleTlsChange(toggled: boolean): void {
		smtpUseTls = toggled;
		if (toggled) {
			smtpUseSsl = false;
		}
	}

	function handleSslChange(toggled: boolean): void {
		smtpUseSsl = toggled;
		if (toggled) {
			smtpUseTls = false;
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

		<Tile>
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
		</Tile>

		<Tile>
			<div class="form-section">
				<h3>Настройки SMTP (Email)</h3>

				<div class="form-row toggle-row">
					<Toggle
						bind:toggled={smtpEnabled}
						labelText="Включить отправку email"
						labelA="Выкл"
						labelB="Вкл"
					/>
				</div>

				{#if smtpEnabled}
					<div class="smtp-fields">
						<div class="form-row-grid">
							<TextInput
								bind:value={smtpHost}
								labelText="SMTP сервер"
								placeholder="smtp.example.com"
							/>
							<NumberInput
								bind:value={smtpPort}
								labelText="Порт"
								min={1}
								max={65535}
							/>
						</div>

						<div class="form-row-grid">
							<TextInput
								bind:value={smtpUsername}
								labelText="Имя пользователя"
								placeholder="user@example.com"
							/>
							<PasswordInput
								bind:value={smtpPassword}
								labelText="Пароль"
								placeholder="Введите пароль"
							/>
						</div>

						<div class="form-row toggle-grid">
							<Toggle
								toggled={smtpUseTls}
								on:toggle={(e) => handleTlsChange(e.detail.toggled)}
								labelText="STARTTLS"
								labelA="Выкл"
								labelB="Вкл"
							/>
							<Toggle
								toggled={smtpUseSsl}
								on:toggle={(e) => handleSslChange(e.detail.toggled)}
								labelText="SSL/TLS"
								labelA="Выкл"
								labelB="Вкл"
							/>
						</div>

						<div class="form-row-grid">
							<TextInput
								bind:value={smtpFromEmail}
								labelText="Email отправителя"
								placeholder="noreply@example.com"
							/>
							<TextInput
								bind:value={smtpFromName}
								labelText="Имя отправителя"
								placeholder="CTrack"
							/>
						</div>

						<div class="smtp-test-section">
							<h4>Тестирование соединения</h4>
							<div class="test-row">
								<TextInput
									bind:value={smtpTestRecipient}
									labelText="Email для тестового письма (опционально)"
									placeholder="test@example.com"
								/>
								<Button
									kind="secondary"
									icon={Email}
									disabled={!smtpHost || isTesting}
									on:click={handleTestSmtp}
								>
									{#if isTesting}
										Тестирование...
									{:else}
										Тест соединения
									{/if}
								</Button>
							</div>

							{#if smtpTestResult}
								<div class="test-result" class:success={smtpTestResult.success}>
									{#if smtpTestResult.success}
										<Checkmark size={16} />
									{:else}
										<Close size={16} />
									{/if}
									<span>{smtpTestResult.message}</span>
								</div>
							{/if}
						</div>
					</div>
				{/if}
			</div>
		</Tile>

		<div class="form-actions">
			<Button icon={Save} disabled={isSaving} on:click={handleSave}>
				{#if isSaving}
					Сохранение...
				{:else}
					Сохранить
				{/if}
			</Button>
		</div>
	{/if}
</div>

<style>
	.settings-page {
		padding: 1rem 2rem;
		max-width: 900px;
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

	h4 {
		font-size: 0.875rem;
		font-weight: 600;
		margin: 1.5rem 0 1rem;
		color: var(--cds-text-secondary);
	}

	.loading-container {
		display: flex;
		justify-content: center;
		padding: 3rem;
	}

	:global(.settings-page .bx--tile) {
		padding: 1.5rem;
		margin-bottom: 1rem;
	}

	.form-section {
		margin-bottom: 1rem;
	}

	.form-row {
		margin-bottom: 1rem;
	}

	.form-row-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
		margin-bottom: 1rem;
	}

	.toggle-row {
		padding-top: 0.5rem;
	}

	.toggle-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 2rem;
		margin-bottom: 1rem;
		padding-top: 0.5rem;
	}

	.smtp-fields {
		margin-top: 1.5rem;
		padding-top: 1rem;
		border-top: 1px solid var(--cds-border-subtle);
	}

	.smtp-test-section {
		margin-top: 1.5rem;
		padding-top: 1rem;
		border-top: 1px solid var(--cds-border-subtle);
	}

	.test-row {
		display: flex;
		gap: 1rem;
		align-items: flex-end;
	}

	.test-row :global(.bx--text-input-wrapper) {
		flex: 1;
	}

	.test-result {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-top: 1rem;
		padding: 0.75rem 1rem;
		border-radius: 4px;
		background: var(--cds-notification-error-background);
		color: var(--cds-support-error);
	}

	.test-result.success {
		background: var(--cds-notification-success-background);
		color: var(--cds-support-success);
	}

	.form-actions {
		display: flex;
		justify-content: flex-end;
		padding-top: 1rem;
	}

	@media (max-width: 768px) {
		.settings-page {
			padding: 1rem;
		}

		.form-row-grid,
		.toggle-grid {
			grid-template-columns: 1fr;
		}

		.test-row {
			flex-direction: column;
			align-items: stretch;
		}

		.test-row :global(.bx--btn) {
			width: 100%;
		}
	}
</style>
