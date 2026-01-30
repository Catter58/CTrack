<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		Breadcrumb,
		BreadcrumbItem,
		DataTable,
		Toolbar,
		ToolbarContent,
		ToolbarSearch,
		Pagination,
		Tag,
		OverflowMenu,
		OverflowMenuItem,
		Modal,
		Loading,
		InlineNotification,
		CodeSnippet,
		Button,
		TextInput,
		PasswordInput,
		Toggle
	} from 'carbon-components-svelte';
	import { Add } from 'carbon-icons-svelte';
	import { user as currentUser, isLoading as authLoading } from '$lib/stores/auth';
	import api from '$lib/api/client';

	interface AdminUser {
		id: number;
		username: string;
		email: string;
		first_name: string | null;
		last_name: string | null;
		full_name: string;
		is_active: boolean;
		is_staff: boolean;
		date_joined: string;
		last_login: string | null;
	}

	interface UsersResponse {
		items: AdminUser[];
		total: number;
		limit: number;
		offset: number;
	}

	interface PasswordResetResponse {
		reset_token: string;
		expires_at: string;
	}

	let users = $state<AdminUser[]>([]);
	let total = $state(0);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let successMessage = $state<string | null>(null);

	let searchQuery = $state('');
	let page = $state(1);
	let pageSize = $state(25);

	let showResetModal = $state(false);
	let resetToken = $state('');
	let resetTokenExpires = $state('');

	// Create user modal state
	let showCreateModal = $state(false);
	let isCreating = $state(false);
	let createError = $state<string | null>(null);
	let newUsername = $state('');
	let newEmail = $state('');
	let newPassword = $state('');
	let newFirstName = $state('');
	let newLastName = $state('');
	let newIsStaff = $state(false);
	let sendWelcomeEmail = $state(false);

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const headers: any[] = [
		{ key: 'username', value: 'Имя пользователя' },
		{ key: 'email', value: 'Email' },
		{ key: 'is_active', value: 'Статус' },
		{ key: 'date_joined', value: 'Дата регистрации' },
		{ key: 'actions', value: '', empty: true }
	];

	const rows = $derived(
		users.map((u) => ({
			id: String(u.id),
			username: u.username,
			email: u.email,
			is_active: u.is_active,
			date_joined: formatDate(u.date_joined),
			_user: u
		}))
	);

	onMount(async () => {
		if (!$authLoading && !$currentUser?.is_staff) {
			goto('/');
			return;
		}

		await loadUsers();
	});

	$effect(() => {
		if (!$authLoading && !$currentUser?.is_staff) {
			goto('/');
		}
	});

	async function loadUsers(): Promise<void> {
		isLoading = true;
		error = null;

		const offset = (page - 1) * pageSize;
		const params: Record<string, string> = {
			limit: String(pageSize),
			offset: String(offset)
		};

		if (searchQuery) {
			params.search = searchQuery;
		}

		try {
			const response = await api.get<UsersResponse>('/api/admin/users', params);
			users = response.items;
			total = response.total;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Не удалось загрузить пользователей';
		} finally {
			isLoading = false;
		}
	}

	let searchTimeout: ReturnType<typeof setTimeout>;

	function handleSearchInput(e: Event): void {
		const target = e.target as HTMLInputElement;
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(() => {
			searchQuery = target.value;
			page = 1;
			loadUsers();
		}, 300);
	}

	function handlePagination(
		e: CustomEvent<{ page?: number; pageSize?: number }>
	): void {
		if (e.detail.page !== undefined) {
			page = e.detail.page;
		}
		if (e.detail.pageSize !== undefined) {
			pageSize = e.detail.pageSize;
		}
		loadUsers();
	}

	async function toggleUserActive(user: AdminUser): Promise<void> {
		error = null;
		successMessage = null;

		try {
			await api.patch(`/api/admin/users/${user.id}`, {
				is_active: !user.is_active
			});
			const action = user.is_active ? 'деактивирован' : 'активирован';
			successMessage = `Пользователь ${user.username} ${action}`;
			await loadUsers();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Не удалось изменить статус пользователя';
		}
	}

	async function resetPassword(user: AdminUser): Promise<void> {
		error = null;

		try {
			const response = await api.post<PasswordResetResponse>(
				`/api/admin/users/${user.id}/reset-password`
			);
			resetToken = response.reset_token;
			resetTokenExpires = formatDateTime(response.expires_at);
			showResetModal = true;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Не удалось сбросить пароль';
		}
	}

	function openCreateModal(): void {
		// Reset form
		newUsername = '';
		newEmail = '';
		newPassword = '';
		newFirstName = '';
		newLastName = '';
		newIsStaff = false;
		sendWelcomeEmail = false;
		createError = null;
		showCreateModal = true;
	}

	async function handleCreateUser(): Promise<void> {
		isCreating = true;
		createError = null;

		try {
			await api.post<AdminUser>('/api/admin/users', {
				username: newUsername,
				email: newEmail,
				password: newPassword,
				first_name: newFirstName,
				last_name: newLastName,
				is_staff: newIsStaff,
				send_welcome_email: sendWelcomeEmail
			});

			showCreateModal = false;
			successMessage = `Пользователь ${newUsername} успешно создан`;
			await loadUsers();
		} catch (err) {
			createError = err instanceof Error ? err.message : 'Не удалось создать пользователя';
		} finally {
			isCreating = false;
		}
	}

	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString('ru-RU', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	}

	function formatDateTime(dateString: string): string {
		return new Date(dateString).toLocaleString('ru-RU', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	const canCreate = $derived(
		newUsername.trim() !== '' &&
		newEmail.trim() !== '' &&
		newPassword.length >= 8
	);
</script>

<svelte:head>
	<title>Пользователи - CTrack</title>
</svelte:head>

<div class="users-page">
	<Breadcrumb noTrailingSlash>
		<BreadcrumbItem href="/">Главная</BreadcrumbItem>
		<BreadcrumbItem href="/admin">Администрирование</BreadcrumbItem>
		<BreadcrumbItem href="/admin/users" isCurrentPage>Пользователи</BreadcrumbItem>
	</Breadcrumb>

	<h1>Управление пользователями</h1>

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

	{#if isLoading || $authLoading}
		<div class="loading-container">
			<Loading withOverlay={false} />
		</div>
	{:else}
		<!-- @ts-expect-error Carbon DataTable typing issue with Svelte 5 -->
		<DataTable {headers} {rows} size="medium">
			<Toolbar>
				<ToolbarContent>
					<ToolbarSearch
						placeholder="Поиск по email или имени..."
						persistent
						on:input={handleSearchInput}
					/>
					<Button icon={Add} on:click={openCreateModal}>
						Создать пользователя
					</Button>
				</ToolbarContent>
			</Toolbar>
			<svelte:fragment slot="cell" let:row let:cell>
				{#if cell.key === 'is_active'}
					{#if cell.value}
						<Tag type="green">Активен</Tag>
					{:else}
						<Tag type="gray">Неактивен</Tag>
					{/if}
				{:else if cell.key === 'actions'}
					{@const userData = row._user as AdminUser}
					<OverflowMenu flipped>
						<OverflowMenuItem
							text={userData.is_active ? 'Деактивировать' : 'Активировать'}
							on:click={() => toggleUserActive(userData)}
							disabled={userData.id === $currentUser?.id}
						/>
						<OverflowMenuItem
							text="Сбросить пароль"
							on:click={() => resetPassword(userData)}
						/>
					</OverflowMenu>
				{:else}
					{cell.value}
				{/if}
			</svelte:fragment>
		</DataTable>

		<Pagination
			bind:pageSize
			bind:page
			totalItems={total}
			pageSizeInputDisabled
			on:change={handlePagination}
		/>
	{/if}
</div>

<!-- Password Reset Modal -->
<Modal
	bind:open={showResetModal}
	modalHeading="Токен сброса пароля"
	primaryButtonText="Закрыть"
	on:click:button--primary={() => (showResetModal = false)}
	on:close={() => (showResetModal = false)}
	passiveModal
>
	<p class="reset-info">
		Токен действителен до: <strong>{resetTokenExpires}</strong>
	</p>
	<p class="reset-info">Скопируйте токен и передайте его пользователю:</p>
	<CodeSnippet type="single" code={resetToken} />
</Modal>

<!-- Create User Modal -->
<Modal
	bind:open={showCreateModal}
	modalHeading="Создать пользователя"
	primaryButtonText={isCreating ? 'Создание...' : 'Создать'}
	secondaryButtonText="Отмена"
	primaryButtonDisabled={!canCreate || isCreating}
	on:click:button--primary={handleCreateUser}
	on:click:button--secondary={() => (showCreateModal = false)}
	on:close={() => (showCreateModal = false)}
>
	{#if createError}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={createError}
			lowContrast
			on:close={() => (createError = null)}
		/>
	{/if}

	<div class="create-form">
		<div class="form-row">
			<TextInput
				bind:value={newUsername}
				labelText="Имя пользователя *"
				placeholder="username"
				required
			/>
		</div>

		<div class="form-row">
			<TextInput
				bind:value={newEmail}
				labelText="Email *"
				placeholder="user@example.com"
				type="email"
				required
			/>
		</div>

		<div class="form-row">
			<PasswordInput
				bind:value={newPassword}
				labelText="Пароль *"
				placeholder="Минимум 8 символов"
				helperText="Минимум 8 символов"
			/>
		</div>

		<div class="form-row-grid">
			<TextInput
				bind:value={newFirstName}
				labelText="Имя"
				placeholder="Иван"
			/>
			<TextInput
				bind:value={newLastName}
				labelText="Фамилия"
				placeholder="Иванов"
			/>
		</div>

		<div class="form-row toggle-row">
			<Toggle
				bind:toggled={newIsStaff}
				labelText="Администратор"
				labelA="Нет"
				labelB="Да"
			/>
		</div>

		<div class="form-row toggle-row">
			<Toggle
				bind:toggled={sendWelcomeEmail}
				labelText="Отправить приветственное письмо"
				labelA="Нет"
				labelB="Да"
			/>
		</div>
	</div>
</Modal>

<style>
	.users-page {
		padding: 1rem 2rem;
		max-width: 1200px;
	}

	h1 {
		margin: 1.5rem 0;
		font-size: 1.75rem;
		font-weight: 600;
	}

	.loading-container {
		display: flex;
		justify-content: center;
		padding: 3rem;
	}

	.reset-info {
		margin: 0 0 1rem;
		color: var(--cds-text-secondary);
	}

	.reset-info strong {
		color: var(--cds-text-primary);
	}

	.create-form {
		padding-top: 1rem;
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

	:global(.users-page .bx--pagination) {
		margin-top: 1rem;
	}

	:global(.users-page .bx--data-table-container) {
		padding: 0;
	}

	:global(.users-page .bx--toolbar-content) {
		display: flex;
		gap: 1rem;
	}

	@media (max-width: 768px) {
		.users-page {
			padding: 1rem;
		}

		.form-row-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
