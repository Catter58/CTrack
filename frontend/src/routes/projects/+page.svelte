<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import {
		Button,
		Tile,
		ClickableTile,
		Loading,
		Modal,
		TextInput,
		TextArea,
		InlineNotification,
		Tag,
		Toggle
	} from 'carbon-components-svelte';
	import { Add, FolderDetails, Archive, Demo } from 'carbon-icons-svelte';
	import api from '$lib/api/client';
	import {
		projects,
		projectsList,
		projectsLoading,
		projectsError
	} from '$lib/stores/projects';

	let showCreateModal = $state(false);
	let newProjectName = $state('');
	let newProjectKey = $state('');
	let newProjectDescription = $state('');
	let isCreating = $state(false);
	let createError = $state<string | null>(null);
	let showArchived = $state(false);
	let isCreatingDemo = $state(false);
	let demoError = $state<string | null>(null);

	// Check URL params for ?new=true
	$effect(() => {
		if (page.url.searchParams.get('new') === 'true') {
			showCreateModal = true;
		}
	});

	onMount(() => {
		projects.loadProjects(showArchived);
	});

	// Reload when showArchived changes
	$effect(() => {
		projects.loadProjects(showArchived);
	});

	// Auto-generate key from name
	$effect(() => {
		if (newProjectName && !newProjectKey) {
			const generated = newProjectName
				.toUpperCase()
				.replace(/[^A-Z0-9]/g, '')
				.slice(0, 10);
			newProjectKey = generated;
		}
	});

	async function handleCreate() {
		if (!newProjectName.trim() || !newProjectKey.trim()) {
			createError = 'Название и ключ обязательны';
			return;
		}

		isCreating = true;
		createError = null;

		const project = await projects.createProject({
			name: newProjectName.trim(),
			key: newProjectKey.trim().toUpperCase(),
			description: newProjectDescription.trim()
		});

		isCreating = false;

		if (project) {
			showCreateModal = false;
			newProjectName = '';
			newProjectKey = '';
			newProjectDescription = '';
			goto(`/projects/${project.key}`);
		} else {
			createError = $projectsError || 'Не удалось создать проект';
		}
	}

	function handleCloseModal() {
		showCreateModal = false;
		createError = null;
		// Remove ?new=true from URL
		if (page.url.searchParams.get('new')) {
			goto('/projects', { replaceState: true });
		}
	}

	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString('ru-RU', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	}

	async function handleCreateDemo() {
		isCreatingDemo = true;
		demoError = null;

		try {
			const response = await api.post<{ project_key: string; message: string }>(
				'/api/demo/create-demo'
			);
			await projects.loadProjects(showArchived);
			goto(`/projects/${response.project_key}`);
		} catch (err) {
			demoError = err instanceof Error ? err.message : 'Не удалось создать демо-проект';
		} finally {
			isCreatingDemo = false;
		}
	}
</script>

<svelte:head>
	<title>Проекты - CTrack</title>
</svelte:head>

<div class="projects-page">
	<header class="page-header">
		<div class="header-content">
			<h1>Проекты</h1>
			<p>Управление проектами и задачами</p>
		</div>
		<div class="header-actions">
			<Toggle
				bind:toggled={showArchived}
				labelText="Показать архивные"
				labelA=""
				labelB=""
				size="sm"
			/>
			<Button
				kind="tertiary"
				icon={Demo}
				disabled={isCreatingDemo}
				on:click={handleCreateDemo}
			>
				{isCreatingDemo ? 'Создание...' : 'Демо-проект'}
			</Button>
			<Button icon={Add} on:click={() => (showCreateModal = true)}>Новый проект</Button>
		</div>
	</header>

	{#if $projectsError && !showCreateModal}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={$projectsError}
			on:close={() => projects.clearError()}
		/>
	{/if}

	{#if demoError}
		<InlineNotification
			kind="error"
			title="Ошибка создания демо-проекта"
			subtitle={demoError}
			on:close={() => (demoError = null)}
		/>
	{/if}

	{#if $projectsLoading}
		<div class="loading-state">
			<Loading withOverlay={false} />
		</div>
	{:else if $projectsList.length === 0}
		<div class="empty-state">
			<Tile>
				<FolderDetails size={32} />
				<h3>Нет проектов</h3>
				<p>Создайте первый проект или загрузите демо-проект с примерами</p>
				<div class="empty-actions">
					<Button icon={Add} on:click={() => (showCreateModal = true)}>Создать проект</Button>
					<Button
						kind="tertiary"
						icon={Demo}
						disabled={isCreatingDemo}
						on:click={handleCreateDemo}
					>
						{isCreatingDemo ? 'Создание...' : 'Демо-проект'}
					</Button>
				</div>
			</Tile>
		</div>
	{:else}
		<div class="projects-grid">
			{#each $projectsList as project (project.id)}
				<ClickableTile href="/projects/{project.key}" class="project-tile">
					<div class="project-content">
						<div class="project-header">
							<Tag type="blue">{project.key}</Tag>
							{#if project.is_archived}
								<Tag type="gray" icon={Archive}>Архив</Tag>
							{/if}
						</div>
						<h3>{project.name}</h3>
						{#if project.description}
							<p class="description">{project.description}</p>
						{/if}
						<div class="project-meta">
							<span>Создан: {formatDate(project.created_at)}</span>
						</div>
					</div>
				</ClickableTile>
			{/each}
		</div>
	{/if}
</div>

<Modal
	bind:open={showCreateModal}
	modalHeading="Новый проект"
	primaryButtonText="Создать"
	secondaryButtonText="Отмена"
	primaryButtonDisabled={isCreating || !newProjectName.trim() || !newProjectKey.trim()}
	on:click:button--primary={handleCreate}
	on:click:button--secondary={handleCloseModal}
	on:close={handleCloseModal}
>
	{#if createError}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={createError}
			hideCloseButton
			lowContrast
		/>
	{/if}

	<TextInput
		bind:value={newProjectName}
		labelText="Название проекта"
		placeholder="Мой проект"
		required
	/>

	<TextInput
		bind:value={newProjectKey}
		labelText="Ключ проекта"
		placeholder="MYPROJ"
		helperText="Уникальный идентификатор (до 10 символов, латиница)"
		maxlength={10}
		style="text-transform: uppercase"
		required
	/>

	<TextArea
		bind:value={newProjectDescription}
		labelText="Описание"
		placeholder="Опишите проект..."
		rows={3}
	/>
</Modal>

<style>
	.projects-page {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 2rem;
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.header-content h1 {
		font-size: 1.75rem;
		font-weight: 600;
		margin: 0 0 0.5rem;
	}

	.header-content p {
		color: var(--cds-text-secondary);
		margin: 0;
	}

	.projects-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
		gap: 1rem;
	}

	.projects-grid :global(.project-tile) {
		height: 100%;
	}

	.project-content {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.project-header {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}

	.project-content h3 {
		font-size: 1.125rem;
		font-weight: 600;
		margin: 0;
	}

	.project-content .description {
		color: var(--cds-text-secondary);
		margin: 0;
		font-size: 0.875rem;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.project-meta {
		margin-top: auto;
		padding-top: 0.5rem;
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}

	.loading-state {
		display: flex;
		justify-content: center;
		padding: 3rem;
	}

	.empty-state {
		display: flex;
		justify-content: center;
		padding: 3rem;
	}

	.empty-state :global(.bx--tile) {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		gap: 1rem;
		padding: 3rem;
		max-width: 400px;
	}

	.empty-state h3 {
		margin: 0;
		font-size: 1.25rem;
	}

	.empty-state p {
		margin: 0;
		color: var(--cds-text-secondary);
	}

	.empty-state :global(svg) {
		color: var(--cds-icon-secondary);
	}

	.empty-actions {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
		justify-content: center;
	}
</style>
