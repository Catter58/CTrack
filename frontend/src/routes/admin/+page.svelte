<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		Breadcrumb,
		BreadcrumbItem,
		Tile,
		ClickableTile,
		Loading,
		InlineNotification
	} from 'carbon-components-svelte';
	import { User, Settings } from 'carbon-icons-svelte';
	import { user, isLoading as authLoading } from '$lib/stores/auth';
	import api from '$lib/api/client';

	interface SystemStats {
		total_users: number;
		active_users: number;
		total_projects: number;
		total_issues: number;
		issues_this_month: number;
	}

	let stats = $state<SystemStats | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		if (!$authLoading && !$user?.is_staff) {
			goto('/');
			return;
		}

		await loadStats();
	});

	$effect(() => {
		if (!$authLoading && !$user?.is_staff) {
			goto('/');
		}
	});

	async function loadStats(): Promise<void> {
		isLoading = true;
		error = null;

		try {
			stats = await api.get<SystemStats>('/api/admin/stats');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Не удалось загрузить статистику';
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Администрирование - CTrack</title>
</svelte:head>

<div class="admin-page">
	<Breadcrumb noTrailingSlash>
		<BreadcrumbItem href="/">Главная</BreadcrumbItem>
		<BreadcrumbItem href="/admin" isCurrentPage>Администрирование</BreadcrumbItem>
	</Breadcrumb>

	<h1>Администрирование</h1>

	{#if isLoading || $authLoading}
		<div class="loading-container">
			<Loading withOverlay={false} />
		</div>
	{:else if error}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={error}
			on:close={() => (error = null)}
		/>
	{:else if stats}
		<section class="stats-section">
			<h2>Статистика системы</h2>
			<div class="stats-grid">
				<Tile class="stat-tile">
					<div class="stat-content">
						<span class="stat-value">{stats.total_users}</span>
						<span class="stat-label">Всего пользователей</span>
					</div>
				</Tile>
				<Tile class="stat-tile">
					<div class="stat-content">
						<span class="stat-value">{stats.active_users}</span>
						<span class="stat-label">Активных</span>
					</div>
				</Tile>
				<Tile class="stat-tile">
					<div class="stat-content">
						<span class="stat-value">{stats.total_projects}</span>
						<span class="stat-label">Проектов</span>
					</div>
				</Tile>
				<Tile class="stat-tile">
					<div class="stat-content">
						<span class="stat-value">{stats.total_issues}</span>
						<span class="stat-label">Задач</span>
					</div>
				</Tile>
				<Tile class="stat-tile">
					<div class="stat-content">
						<span class="stat-value">{stats.issues_this_month}</span>
						<span class="stat-label">Задач за месяц</span>
					</div>
				</Tile>
			</div>
		</section>

		<section class="nav-section">
			<h2>Разделы</h2>
			<div class="nav-grid">
				<ClickableTile href="/admin/settings" class="nav-tile">
					<Settings size={32} />
					<div class="nav-content">
						<h3>Настройки</h3>
						<p>Системные настройки приложения</p>
					</div>
				</ClickableTile>
				<ClickableTile href="/admin/users" class="nav-tile">
					<User size={32} />
					<div class="nav-content">
						<h3>Пользователи</h3>
						<p>Управление пользователями</p>
					</div>
				</ClickableTile>
			</div>
		</section>
	{/if}
</div>

<style>
	.admin-page {
		padding: 1rem 2rem;
		max-width: 1200px;
	}

	h1 {
		margin: 1.5rem 0;
		font-size: 1.75rem;
		font-weight: 600;
	}

	h2 {
		font-size: 1.25rem;
		font-weight: 600;
		margin: 0 0 1rem;
	}

	.loading-container {
		display: flex;
		justify-content: center;
		padding: 3rem;
	}

	.stats-section {
		margin-bottom: 2rem;
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 1rem;
	}

	.stats-grid :global(.stat-tile) {
		padding: 1.5rem;
	}

	.stat-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
	}

	.stat-value {
		font-size: 2.5rem;
		font-weight: 600;
		line-height: 1;
		color: var(--cds-text-primary);
	}

	.stat-label {
		margin-top: 0.5rem;
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
	}

	.nav-section {
		margin-bottom: 2rem;
	}

	.nav-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 1rem;
	}

	.nav-grid :global(.nav-tile) {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		padding: 1.5rem;
	}

	.nav-grid :global(.nav-tile svg) {
		flex-shrink: 0;
		color: var(--cds-icon-secondary);
	}

	.nav-content h3 {
		font-size: 1rem;
		font-weight: 600;
		margin: 0 0 0.25rem;
	}

	.nav-content p {
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
		margin: 0;
	}
</style>
