<script lang="ts">
	import { goto } from '$app/navigation';
	import {
		Form,
		TextInput,
		PasswordInput,
		Button,
		InlineNotification,
		Link
	} from 'carbon-components-svelte';
	import { auth, authError, isLoading } from '$lib/stores/auth';

	let email = $state('');
	let username = $state('');
	let firstName = $state('');
	let lastName = $state('');
	let password = $state('');
	let confirmPassword = $state('');

	let errors = $state({
		email: '',
		username: '',
		password: '',
		confirmPassword: ''
	});

	function validateEmail(value: string): boolean {
		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		return emailRegex.test(value);
	}

	function validateUsername(value: string): boolean {
		return value.length >= 3 && /^[a-zA-Z0-9_]+$/.test(value);
	}

	function validatePassword(value: string): boolean {
		return value.length >= 8;
	}

	function validate(): boolean {
		errors = {
			email: '',
			username: '',
			password: '',
			confirmPassword: ''
		};

		let valid = true;

		if (!validateEmail(email)) {
			errors.email = 'Введите корректный email';
			valid = false;
		}

		if (!validateUsername(username)) {
			errors.username = 'Минимум 3 символа, только буквы, цифры и _';
			valid = false;
		}

		if (!validatePassword(password)) {
			errors.password = 'Минимум 8 символов';
			valid = false;
		}

		if (password !== confirmPassword) {
			errors.confirmPassword = 'Пароли не совпадают';
			valid = false;
		}

		return valid;
	}

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		auth.clearError();

		if (!validate()) {
			return;
		}

		const success = await auth.register({
			email,
			username,
			password,
			first_name: firstName,
			last_name: lastName
		});

		if (success) {
			goto('/');
		}
	}
</script>

<svelte:head>
	<title>Регистрация - CTrack</title>
</svelte:head>

<Form on:submit={handleSubmit}>
	<h2>Регистрация</h2>

	{#if $authError}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={$authError}
			lowContrast
			hideCloseButton
		/>
	{/if}

	<div class="form-field">
		<TextInput
			id="email"
			type="email"
			labelText="Email"
			placeholder="Введите email"
			bind:value={email}
			invalid={!!errors.email}
			invalidText={errors.email}
			disabled={$isLoading}
		/>
	</div>

	<div class="form-field">
		<TextInput
			id="username"
			labelText="Имя пользователя"
			placeholder="Введите имя пользователя"
			bind:value={username}
			invalid={!!errors.username}
			invalidText={errors.username}
			disabled={$isLoading}
		/>
	</div>

	<div class="form-row">
		<div class="form-field">
			<TextInput
				id="firstName"
				labelText="Имя"
				placeholder="Иван"
				bind:value={firstName}
				disabled={$isLoading}
			/>
		</div>
		<div class="form-field">
			<TextInput
				id="lastName"
				labelText="Фамилия"
				placeholder="Иванов"
				bind:value={lastName}
				disabled={$isLoading}
			/>
		</div>
	</div>

	<div class="form-field">
		<PasswordInput
			id="password"
			labelText="Пароль"
			placeholder="Минимум 8 символов"
			bind:value={password}
			invalid={!!errors.password}
			invalidText={errors.password}
			disabled={$isLoading}
		/>
	</div>

	<div class="form-field">
		<PasswordInput
			id="confirmPassword"
			labelText="Подтверждение пароля"
			placeholder="Повторите пароль"
			bind:value={confirmPassword}
			invalid={!!errors.confirmPassword}
			invalidText={errors.confirmPassword}
			disabled={$isLoading}
		/>
	</div>

	<div class="form-actions">
		<Button type="submit" disabled={$isLoading}>
			{$isLoading ? 'Регистрация...' : 'Зарегистрироваться'}
		</Button>
	</div>

	<div class="form-footer">
		<span>Уже есть аккаунт?</span>
		<Link href="/auth/login">Войти</Link>
	</div>
</Form>

<style>
	h2 {
		margin: 0 0 1.5rem;
		font-size: 1.25rem;
		font-weight: 600;
	}

	.form-field {
		margin-bottom: 1rem;
	}

	.form-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}

	.form-actions {
		margin-top: 1.5rem;
	}

	.form-actions :global(button) {
		width: 100%;
	}

	.form-footer {
		margin-top: 1.5rem;
		text-align: center;
		color: var(--cds-text-secondary);
	}

	.form-footer :global(a) {
		margin-left: 0.5rem;
	}

	:global(.bx--inline-notification) {
		margin-bottom: 1rem;
		max-width: 100%;
	}
</style>
