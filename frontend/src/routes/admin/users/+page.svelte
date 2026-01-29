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
		CodeSnippet
	} from 'carbon-components-svelte';
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
		<DataTable {headers} {rows} size="medium">
			<Toolbar>
				<ToolbarContent>
					<ToolbarSearch
						placeholder="Поиск по email или имени..."
						persistent
						on:input={handleSearchInput}
					/>
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

	:global(.users-page .bx--pagination) {
		margin-top: 1rem;
	}

	:global(.users-page .bx--data-table-container) {
		padding: 0;
	}
</style>
