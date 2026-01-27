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
	let password = $state('');
	let emailInvalid = $state(false);
	let passwordInvalid = $state(false);

	function validateEmail(value: string): boolean {
		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		return emailRegex.test(value);
	}

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		auth.clearError();

		// Validate
		emailInvalid = !validateEmail(email);
		passwordInvalid = password.length < 1;

		if (emailInvalid || passwordInvalid) {
			return;
		}

		const success = await auth.login(email, password);
		if (success) {
			goto('/');
		}
	}
</script>

<svelte:head>
	<title>Вход - CTrack</title>
</svelte:head>

<Form on:submit={handleSubmit}>
	<h2>Вход в систему</h2>

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
			invalid={emailInvalid}
			invalidText="Введите корректный email"
			disabled={$isLoading}
		/>
	</div>

	<div class="form-field">
		<PasswordInput
			id="password"
			labelText="Пароль"
			placeholder="Введите пароль"
			bind:value={password}
			invalid={passwordInvalid}
			invalidText="Введите пароль"
			disabled={$isLoading}
		/>
	</div>

	<div class="form-actions">
		<Button type="submit" disabled={$isLoading}>
			{$isLoading ? 'Вход...' : 'Войти'}
		</Button>
	</div>

	<div class="form-footer">
		<span>Нет аккаунта?</span>
		<Link href="/auth/register">Зарегистрироваться</Link>
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
