<script lang="ts">
	import { Tile, Button } from 'carbon-components-svelte';
	import { Add, FolderDetails } from 'carbon-icons-svelte';
	import { user } from '$lib/stores/auth';
</script>

<svelte:head>
	<title>Главная - CTrack</title>
</svelte:head>

<div class="dashboard">
	<header class="dashboard-header">
		<h1>Добро пожаловать, {$user?.first_name || $user?.username}!</h1>
		<p>Управляйте своими проектами и задачами</p>
	</header>

	<div class="dashboard-actions">
		<Tile>
			<div class="action-tile">
				<FolderDetails size={32} />
				<h3>Проекты</h3>
				<p>Просмотр и управление проектами</p>
				<Button href="/projects" icon={FolderDetails}>Открыть проекты</Button>
			</div>
		</Tile>

		<Tile>
			<div class="action-tile">
				<Add size={32} />
				<h3>Новый проект</h3>
				<p>Создайте новый проект для команды</p>
				<Button kind="secondary" href="/projects?new=true" icon={Add}>Создать проект</Button>
			</div>
		</Tile>
	</div>
</div>

<style>
	.dashboard {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem;
	}

	.dashboard-header {
		margin-bottom: 2rem;
	}

	.dashboard-header h1 {
		font-size: 1.75rem;
		font-weight: 600;
		margin: 0 0 0.5rem;
	}

	.dashboard-header p {
		color: var(--cds-text-secondary);
		margin: 0;
	}

	.dashboard-actions {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 1rem;
	}

	.action-tile {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.75rem;
	}

	.action-tile h3 {
		font-size: 1.125rem;
		font-weight: 600;
		margin: 0;
	}

	.action-tile p {
		color: var(--cds-text-secondary);
		margin: 0;
		flex-grow: 1;
	}

	.action-tile :global(svg) {
		color: var(--cds-icon-primary);
	}
</style>
