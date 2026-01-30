<script lang="ts">
	import { goto } from '$app/navigation';
	import {
		Button,
		TextInput,
		PasswordInput,
		Select,
		SelectItem,
		Tile,
		ProgressIndicator,
		ProgressStep,
		InlineNotification,
		Loading
	} from 'carbon-components-svelte';
	import { ArrowRight, ArrowLeft, Checkmark } from 'carbon-icons-svelte';
	import { setup, setupError, setupLoading } from '$lib/stores/setup';
	import { auth } from '$lib/stores/auth';
	import api from '$lib/api/client';

	let currentStep = $state(0);
	let isSubmitting = $state(false);

	// Form data
	let adminEmail = $state('');
	let adminUsername = $state('');
	let adminPassword = $state('');
	let adminPasswordConfirm = $state('');
	let adminFullName = $state('');

	let orgName = $state('');
	let orgTimezone = $state('Europe/Moscow');

	let issueTypeTemplate = $state('scrum');

	// Validation
	let emailError = $state('');
	let passwordError = $state('');
	let usernameError = $state('');
	let orgNameError = $state('');

	const steps = ['Приветствие', 'Администратор', 'Организация', 'Шаблон', 'Готово'];

	const templates = [
		{
			value: 'scrum',
			label: 'Scrum',
			description: 'Эпики, Истории, Задачи, Баги, Подзадачи — полный набор для Agile-команд'
		},
		{
			value: 'kanban',
			label: 'Kanban',
			description: 'Задачи, Баги, Улучшения — простой набор для потокового управления'
		},
		{
			value: 'bug_tracking',
			label: 'Баг-трекер',
			description: 'Баги, Улучшения, Фичи — для отслеживания дефектов'
		},
		{
			value: 'empty',
			label: 'Пустой',
			description: 'Начните с чистого листа и создайте свои типы задач'
		}
	];

	const timezones = [
		{ value: 'Europe/Moscow', label: 'Москва (UTC+3)' },
		{ value: 'Europe/Kaliningrad', label: 'Калининград (UTC+2)' },
		{ value: 'Europe/Samara', label: 'Самара (UTC+4)' },
		{ value: 'Asia/Yekaterinburg', label: 'Екатеринбург (UTC+5)' },
		{ value: 'Asia/Novosibirsk', label: 'Новосибирск (UTC+7)' },
		{ value: 'Asia/Vladivostok', label: 'Владивосток (UTC+10)' },
		{ value: 'UTC', label: 'UTC' }
	];

	function validateStep(step: number): boolean {
		switch (step) {
			case 1:
				emailError = '';
				usernameError = '';
				passwordError = '';

				if (!adminEmail) {
					emailError = 'Email обязателен';
					return false;
				}
				if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(adminEmail)) {
					emailError = 'Некорректный формат email';
					return false;
				}
				if (!adminUsername) {
					usernameError = 'Имя пользователя обязательно';
					return false;
				}
				if (adminUsername.length < 3) {
					usernameError = 'Минимум 3 символа';
					return false;
				}
				if (!adminPassword) {
					passwordError = 'Пароль обязателен';
					return false;
				}
				if (adminPassword.length < 8) {
					passwordError = 'Минимум 8 символов';
					return false;
				}
				if (adminPassword !== adminPasswordConfirm) {
					passwordError = 'Пароли не совпадают';
					return false;
				}
				return true;

			case 2:
				orgNameError = '';
				if (!orgName) {
					orgNameError = 'Название организации обязательно';
					return false;
				}
				return true;

			default:
				return true;
		}
	}

	function nextStep() {
		if (validateStep(currentStep)) {
			currentStep++;
		}
	}

	function prevStep() {
		if (currentStep > 0) {
			currentStep--;
		}
	}

	async function handleComplete() {
		if (!validateStep(currentStep)) return;

		isSubmitting = true;

		const result = await setup.completeSetup({
			admin_user: {
				email: adminEmail,
				username: adminUsername,
				password: adminPassword,
				full_name: adminFullName || undefined
			},
			org_settings: {
				name: orgName,
				timezone: orgTimezone
			},
			issue_type_template: issueTypeTemplate
		});

		if (result) {
			// Set tokens in auth store and API client
			api.setToken(result.access_token);
			localStorage.setItem(
				'ctrack_auth',
				JSON.stringify({
					accessToken: result.access_token,
					refreshToken: result.refresh_token
				})
			);

			// Initialize auth
			await auth.init();

			currentStep = 4; // Show completion step
		}

		isSubmitting = false;
	}

	function goToDashboard() {
		goto('/');
	}
</script>

<svelte:head>
	<title>Настройка CTrack</title>
</svelte:head>

<div class="setup-page">
	<div class="setup-container">
		<header class="setup-header">
			<h1>CTrack</h1>
			<p>Настройка таск-трекера</p>
		</header>

		<ProgressIndicator currentIndex={currentStep} spaceEqually>
			{#each steps as step, i}
				<ProgressStep
					label={step}
					complete={i < currentStep}
					current={i === currentStep}
				/>
			{/each}
		</ProgressIndicator>

		{#if $setupError}
			<InlineNotification
				kind="error"
				title="Ошибка"
				subtitle={$setupError}
				on:close={() => setup.clearError()}
			/>
		{/if}

		<div class="step-content">
			{#if currentStep === 0}
				<!-- Welcome -->
				<Tile class="step-tile">
					<div class="welcome-content">
						<h2>Добро пожаловать в CTrack!</h2>
						<p>
							CTrack — минималистичный таск-трекер для управления проектами и задачами.
							Поддерживает Agile/Scrum методологии, Kanban-доски и гибкие рабочие процессы.
						</p>
						<ul>
							<li>Управление проектами и командами</li>
							<li>Kanban-доски с drag-and-drop</li>
							<li>Настраиваемые типы задач и статусы</li>
							<li>Гибкий Workflow для каждого проекта</li>
						</ul>
						<p>Давайте настроим систему для вашей команды.</p>
					</div>
				</Tile>
			{:else if currentStep === 1}
				<!-- Admin User -->
				<Tile class="step-tile">
					<h2>Учётная запись администратора</h2>
					<p>Создайте первую учётную запись с правами администратора.</p>

					<div class="form-group">
						<TextInput
							bind:value={adminEmail}
							labelText="Email"
							placeholder="admin@example.com"
							invalid={!!emailError}
							invalidText={emailError}
							required
						/>
					</div>

					<div class="form-group">
						<TextInput
							bind:value={adminUsername}
							labelText="Имя пользователя"
							placeholder="admin"
							invalid={!!usernameError}
							invalidText={usernameError}
							required
						/>
					</div>

					<div class="form-group">
						<TextInput
							bind:value={adminFullName}
							labelText="Полное имя"
							placeholder="Иван Иванов"
						/>
					</div>

					<div class="form-group">
						<PasswordInput
							bind:value={adminPassword}
							labelText="Пароль"
							placeholder="Минимум 8 символов"
							invalid={!!passwordError}
							invalidText={passwordError}
							required
						/>
					</div>

					<div class="form-group">
						<PasswordInput
							bind:value={adminPasswordConfirm}
							labelText="Подтверждение пароля"
							placeholder="Повторите пароль"
							required
						/>
					</div>
				</Tile>
			{:else if currentStep === 2}
				<!-- Organization -->
				<Tile class="step-tile">
					<h2>Настройки организации</h2>
					<p>Укажите основные данные вашей организации.</p>

					<div class="form-group">
						<TextInput
							bind:value={orgName}
							labelText="Название организации"
							placeholder="Моя компания"
							invalid={!!orgNameError}
							invalidText={orgNameError}
							required
						/>
					</div>

					<div class="form-group">
						<Select bind:selected={orgTimezone} labelText="Часовой пояс">
							{#each timezones as tz}
								<SelectItem value={tz.value} text={tz.label} />
							{/each}
						</Select>
					</div>
				</Tile>
			{:else if currentStep === 3}
				<!-- Template -->
				<Tile class="step-tile">
					<h2>Шаблон типов задач</h2>
					<p>Выберите начальный набор типов задач для ваших проектов.</p>

					<div class="templates-grid">
						{#each templates as template}
							<button
								class="template-card"
								class:selected={issueTypeTemplate === template.value}
								onclick={() => (issueTypeTemplate = template.value)}
							>
								<h4>{template.label}</h4>
								<p>{template.description}</p>
								{#if issueTypeTemplate === template.value}
									<Checkmark class="check-icon" />
								{/if}
							</button>
						{/each}
					</div>
				</Tile>
			{:else if currentStep === 4}
				<!-- Complete -->
				<Tile class="step-tile">
					<div class="complete-content">
						<div class="success-icon">
							<Checkmark size={32} />
						</div>
						<h2>Настройка завершена!</h2>
						<p>
							CTrack готов к использованию. Теперь вы можете создавать проекты,
							добавлять участников и управлять задачами.
						</p>
						<Button icon={ArrowRight} on:click={goToDashboard}>
							Перейти к панели управления
						</Button>
					</div>
				</Tile>
			{/if}
		</div>

		{#if currentStep < 4}
			<div class="step-actions">
				{#if currentStep > 0}
					<Button kind="secondary" icon={ArrowLeft} on:click={prevStep}>
						Назад
					</Button>
				{:else}
					<div></div>
				{/if}

				{#if currentStep < 3}
					<Button icon={ArrowRight} on:click={nextStep}>
						Далее
					</Button>
				{:else}
					<Button
						icon={Checkmark}
						on:click={handleComplete}
						disabled={isSubmitting || $setupLoading}
					>
						{#if isSubmitting}
							<Loading withOverlay={false} small />
						{:else}
							Завершить настройку
						{/if}
					</Button>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	.setup-page {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
		background: var(--cds-background);
	}

	.setup-container {
		width: 100%;
		max-width: 700px;
	}

	.setup-header {
		text-align: center;
		margin-bottom: 2rem;
	}

	.setup-header h1 {
		font-size: 2rem;
		font-weight: 600;
		margin: 0;
		color: var(--cds-text-primary);
	}

	.setup-header p {
		color: var(--cds-text-secondary);
		margin: 0.5rem 0 0;
	}

	.step-content {
		margin: 2rem 0;
	}

	.step-content :global(.step-tile) {
		padding: 2rem;
	}

	.step-content h2 {
		font-size: 1.25rem;
		font-weight: 600;
		margin: 0 0 0.5rem;
	}

	.step-content :global(.bx--tile p) {
		color: var(--cds-text-secondary);
		margin: 0 0 1.5rem;
	}

	.form-group {
		margin-bottom: 1rem;
	}

	.welcome-content {
		text-align: center;
	}

	.welcome-content ul {
		text-align: left;
		display: inline-block;
		margin: 1rem 0;
		padding-left: 1.5rem;
	}

	.welcome-content li {
		margin: 0.5rem 0;
		color: var(--cds-text-secondary);
	}

	.templates-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 1rem;
	}

	.template-card {
		position: relative;
		padding: 1rem;
		border: 2px solid var(--cds-border-subtle);
		border-radius: 8px;
		background: var(--cds-field);
		cursor: pointer;
		text-align: left;
		transition:
			border-color 0.15s ease,
			background-color 0.15s ease;
	}

	.template-card:hover {
		border-color: var(--cds-border-strong);
	}

	.template-card.selected {
		border-color: var(--cds-interactive);
		background: var(--cds-highlight);
	}

	.template-card h4 {
		font-size: 1rem;
		font-weight: 600;
		margin: 0 0 0.5rem;
	}

	.template-card p {
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
		margin: 0;
	}

	.template-card :global(.check-icon) {
		position: absolute;
		top: 0.5rem;
		right: 0.5rem;
		color: var(--cds-interactive);
	}

	.complete-content {
		text-align: center;
	}

	.success-icon {
		width: 80px;
		height: 80px;
		margin: 0 auto 1.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--cds-support-success);
		border-radius: 50%;
		color: white;
	}

	.step-actions {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
	}

	.step-actions :global(.bx--btn) {
		min-width: 120px;
	}

	/* Fix ProgressIndicator label overlap */
	:global(.bx--progress) {
		margin-bottom: 1rem;
		gap: 0.5rem;
	}

	:global(.bx--progress-step) {
		flex: 1;
		min-width: 0;
	}

	:global(.bx--progress-label) {
		font-size: 0.75rem;
		white-space: nowrap;
	}
</style>
