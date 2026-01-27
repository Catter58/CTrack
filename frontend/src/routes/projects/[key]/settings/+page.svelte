<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import {
		Breadcrumb,
		BreadcrumbItem,
		Tabs,
		Tab,
		TabContent,
		DataTable,
		Button,
		Modal,
		TextInput,
		TextArea,
		Select,
		SelectItem,
		InlineNotification,
		Tag,
		Loading,
		Tile
	} from 'carbon-components-svelte';
	import { Add, Edit, TrashCan, UserFollow, Save, Warning, Renew } from 'carbon-icons-svelte';
	import { issueTypes, issueTypesList, issueTypesLoading, issueTypesError } from '$lib/stores/issueTypes';
	import { statuses, statusesList, statusesLoading, statusesError, categoryLabels } from '$lib/stores/statuses';
	import { projects, currentProject, projectMembers, projectsLoading, projectsError } from '$lib/stores/projects';
	import type { IssueType } from '$lib/stores/issueTypes';
	import type { Status } from '$lib/stores/statuses';
	import type { ProjectMember } from '$lib/stores/projects';
	import api from '$lib/api/client';

	const projectKey = $page.params.key;

	let selectedTab = $state(0);

	// General settings form
	let projectName = $state('');
	let projectDescription = $state('');
	let isSaving = $state(false);
	let saveSuccess = $state(false);

	// Issue Type Modal
	let issueTypeModalOpen = $state(false);
	let editingIssueType = $state<IssueType | null>(null);
	let issueTypeForm = $state({
		name: '',
		icon: 'checkmark',
		color: '#1192e8',
		is_subtask: false,
		order: 1
	});

	// Status Modal
	let statusModalOpen = $state(false);
	let editingStatus = $state<Status | null>(null);
	let statusForm = $state({
		name: '',
		category: 'todo' as 'todo' | 'in_progress' | 'done',
		color: '#6f6f6f',
		order: 1
	});

	// Member Modal
	let memberModalOpen = $state(false);
	let editingMember = $state<ProjectMember | null>(null);
	let memberForm = $state({
		user_id: 0,
		role: 'developer' as string
	});
	let userSearchQuery = $state('');
	let userSearchResults = $state<Array<{ id: number; username: string; email: string; full_name: string }>>([]);
	let selectedUser = $state<{ id: number; username: string; email: string; full_name: string } | null>(null);

	// Delete confirmation
	let deleteModalOpen = $state(false);
	let deleteTarget = $state<{ type: 'issueType' | 'status' | 'member'; id: string; name: string } | null>(null);

	// Archive/Restore/Delete confirmation
	let archiveModalOpen = $state(false);
	let restoreModalOpen = $state(false);
	let permanentDeleteModalOpen = $state(false);

	const icons = [
		{ value: 'checkmark', label: 'Галочка' },
		{ value: 'target', label: 'Цель' },
		{ value: 'book', label: 'Книга' },
		{ value: 'debug', label: 'Баг' },
		{ value: 'subtract', label: 'Подзадача' },
		{ value: 'upgrade', label: 'Улучшение' },
		{ value: 'add', label: 'Добавить' }
	];

	const colors = [
		{ value: '#1192e8', label: 'Синий' },
		{ value: '#0f62fe', label: 'Тёмно-синий' },
		{ value: '#8a3ffc', label: 'Фиолетовый' },
		{ value: '#198038', label: 'Зелёный' },
		{ value: '#da1e28', label: 'Красный' },
		{ value: '#6f6f6f', label: 'Серый' },
		{ value: '#ff7700', label: 'Оранжевый' }
	];

	const categories = [
		{ value: 'todo', label: 'К выполнению' },
		{ value: 'in_progress', label: 'В работе' },
		{ value: 'done', label: 'Готово' }
	];

	const roles = [
		{ value: 'admin', label: 'Администратор' },
		{ value: 'manager', label: 'Менеджер' },
		{ value: 'developer', label: 'Разработчик' },
		{ value: 'viewer', label: 'Наблюдатель' }
	];

	const roleLabels: Record<string, string> = {
		admin: 'Администратор',
		manager: 'Менеджер',
		developer: 'Разработчик',
		viewer: 'Наблюдатель'
	};

	onMount(async () => {
		await projects.loadProject(projectKey);
		await Promise.all([
			issueTypes.load(projectKey),
			statuses.load(projectKey),
			projects.loadMembers(projectKey)
		]);
	});

	// Sync form with project data
	$effect(() => {
		if ($currentProject) {
			projectName = $currentProject.name;
			projectDescription = $currentProject.description || '';
		}
	});

	// General settings handlers
	async function handleSaveGeneral() {
		isSaving = true;
		saveSuccess = false;

		const result = await projects.updateProject(projectKey, {
			name: projectName,
			description: projectDescription
		});

		isSaving = false;
		if (result) {
			saveSuccess = true;
			setTimeout(() => (saveSuccess = false), 3000);
		}
	}

	// Issue Type handlers
	function openIssueTypeModal(item?: IssueType) {
		if (item) {
			editingIssueType = item;
			issueTypeForm = {
				name: item.name,
				icon: item.icon,
				color: item.color,
				is_subtask: item.is_subtask,
				order: item.order
			};
		} else {
			editingIssueType = null;
			issueTypeForm = {
				name: '',
				icon: 'checkmark',
				color: '#1192e8',
				is_subtask: false,
				order: ($issueTypesList?.length || 0) + 1
			};
		}
		issueTypeModalOpen = true;
	}

	async function handleIssueTypeSave() {
		if (editingIssueType) {
			await issueTypes.update(editingIssueType.id, {
				name: issueTypeForm.name,
				icon: issueTypeForm.icon,
				color: issueTypeForm.color,
				is_subtask: issueTypeForm.is_subtask,
				order: issueTypeForm.order
			});
		} else {
			await issueTypes.create(projectKey, {
				...issueTypeForm,
				parent_types: []
			});
		}
		issueTypeModalOpen = false;
	}

	// Status handlers
	function openStatusModal(item?: Status) {
		if (item) {
			editingStatus = item;
			statusForm = {
				name: item.name,
				category: item.category,
				color: item.color,
				order: item.order
			};
		} else {
			editingStatus = null;
			statusForm = {
				name: '',
				category: 'todo',
				color: '#6f6f6f',
				order: ($statusesList?.length || 0) + 1
			};
		}
		statusModalOpen = true;
	}

	async function handleStatusSave() {
		if (editingStatus) {
			await statuses.update(editingStatus.id, {
				name: statusForm.name,
				category: statusForm.category,
				color: statusForm.color,
				order: statusForm.order
			});
		} else {
			await statuses.create(projectKey, statusForm);
		}
		statusModalOpen = false;
	}

	// Member handlers
	async function searchUsers() {
		if (userSearchQuery.length < 2) {
			userSearchResults = [];
			return;
		}
		try {
			const results = await api.get<Array<{ id: number; username: string; email: string; full_name: string }>>(
				'/api/users',
				{ search: userSearchQuery }
			);
			// Filter out existing members
			const memberIds = new Set($projectMembers.map((m) => m.user_id));
			userSearchResults = results.filter((u) => !memberIds.has(u.id));
		} catch {
			userSearchResults = [];
		}
	}

	function selectUser(user: { id: number; username: string; email: string; full_name: string }) {
		selectedUser = user;
		memberForm.user_id = user.id;
		userSearchQuery = '';
		userSearchResults = [];
	}

	function openMemberModal(member?: ProjectMember) {
		if (member) {
			editingMember = member;
			memberForm = {
				user_id: member.user_id,
				role: member.role
			};
		} else {
			editingMember = null;
			memberForm = {
				user_id: 0,
				role: 'developer'
			};
			userSearchQuery = '';
			selectedUser = null;
		}
		memberModalOpen = true;
	}

	async function handleMemberSave() {
		if (editingMember) {
			await projects.updateMemberRole(projectKey, editingMember.user_id, memberForm.role);
			// Reload to get updated data
			await projects.loadMembers(projectKey);
		} else if (selectedUser) {
			await projects.addMember(projectKey, selectedUser.id, memberForm.role);
			// Reload to get properly formatted member data
			await projects.loadMembers(projectKey);
		}
		memberModalOpen = false;
		selectedUser = null;
		userSearchQuery = '';
	}

	// Delete handlers
	function confirmDelete(type: 'issueType' | 'status' | 'member', id: string, name: string) {
		deleteTarget = { type, id, name };
		deleteModalOpen = true;
	}

	async function handleDelete() {
		if (!deleteTarget) return;

		if (deleteTarget.type === 'issueType') {
			await issueTypes.delete(deleteTarget.id);
		} else if (deleteTarget.type === 'status') {
			await statuses.delete(deleteTarget.id);
		} else if (deleteTarget.type === 'member') {
			await projects.removeMember(projectKey, parseInt(deleteTarget.id));
		}

		deleteModalOpen = false;
		deleteTarget = null;
	}

	// Archive handler
	async function handleArchive() {
		const success = await projects.archiveProject(projectKey);
		if (success) {
			goto('/projects');
		}
		archiveModalOpen = false;
	}

	// Restore handler
	async function handleRestore() {
		const success = await projects.restoreProject(projectKey);
		restoreModalOpen = false;
		if (success) {
			// Reload project to get updated data
			await projects.loadProject(projectKey);
		}
	}

	// Permanent delete handler
	async function handlePermanentDelete() {
		const success = await projects.deleteProjectPermanently(projectKey);
		if (success) {
			goto('/projects');
		}
		permanentDeleteModalOpen = false;
	}

	// Table headers
	const issueTypeHeaders = [
		{ key: 'color', value: '' },
		{ key: 'name', value: 'Название' },
		{ key: 'icon', value: 'Иконка' },
		{ key: 'is_subtask', value: 'Подзадача' },
		{ key: 'order', value: 'Порядок' },
		{ key: 'actions', value: '' }
	];

	const statusHeaders = [
		{ key: 'color', value: '' },
		{ key: 'name', value: 'Название' },
		{ key: 'category', value: 'Категория' },
		{ key: 'order', value: 'Порядок' },
		{ key: 'actions', value: '' }
	];

	const memberHeaders = [
		{ key: 'username', value: 'Пользователь' },
		{ key: 'email', value: 'Email' },
		{ key: 'role', value: 'Роль' },
		{ key: 'joined_at', value: 'Дата добавления' },
		{ key: 'actions', value: '' }
	];
</script>

<svelte:head>
	<title>Настройки проекта {projectKey} - CTrack</title>
</svelte:head>

<div class="settings-page">
	<Breadcrumb noTrailingSlash>
		<BreadcrumbItem href="/projects">Проекты</BreadcrumbItem>
		<BreadcrumbItem href="/projects/{projectKey}">{projectKey}</BreadcrumbItem>
		<BreadcrumbItem href="/projects/{projectKey}/settings" isCurrentPage>Настройки</BreadcrumbItem>
	</Breadcrumb>

	<h1>Настройки проекта</h1>

	{#if $projectsError}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={$projectsError}
			on:close={() => projects.clearError()}
		/>
	{/if}

	<Tabs bind:selected={selectedTab}>
		<Tab label="Общие" />
		<Tab label="Участники" />
		<Tab label="Типы задач" />
		<Tab label="Статусы" />
		<svelte:fragment slot="content">
			<!-- General Settings Tab -->
			<TabContent>
				{#if $projectsLoading}
					<Loading withOverlay={false} small />
				{:else if $currentProject}
					<div class="general-settings">
						{#if saveSuccess}
							<InlineNotification
								kind="success"
								title="Сохранено"
								subtitle="Настройки проекта обновлены"
								hideCloseButton
							/>
						{/if}

						<div class="form-section">
							<TextInput
								bind:value={projectName}
								labelText="Название проекта"
								placeholder="Введите название"
							/>
						</div>

						<div class="form-section">
							<TextArea
								bind:value={projectDescription}
								labelText="Описание"
								placeholder="Описание проекта"
								rows={4}
							/>
						</div>

						<div class="form-section readonly">
							<TextInput
								value={$currentProject.key}
								labelText="Ключ проекта"
								disabled
								helperText="Ключ нельзя изменить"
							/>
						</div>

						<div class="form-actions">
							<Button icon={Save} disabled={isSaving} on:click={handleSaveGeneral}>
								{#if isSaving}
									Сохранение...
								{:else}
									Сохранить
								{/if}
							</Button>
						</div>

						<Tile class="danger-zone">
							<h3><Warning /> Опасная зона</h3>
							{#if $currentProject.is_archived}
								<div class="archived-notice">
									<Tag type="purple">Проект в архиве</Tag>
								</div>
								<div class="danger-actions">
									<div class="danger-action">
										<p>Восстановить проект из архива. Он снова появится в списке проектов.</p>
										<Button kind="tertiary" icon={Renew} on:click={() => (restoreModalOpen = true)}>
											Восстановить проект
										</Button>
									</div>
									<div class="danger-action">
										<p>Удалить проект навсегда. Это действие нельзя отменить, все данные будут потеряны.</p>
										<Button kind="danger" icon={TrashCan} on:click={() => (permanentDeleteModalOpen = true)}>
											Удалить навсегда
										</Button>
									</div>
								</div>
							{:else}
								<p>Архивация проекта скроет его из списка. Это действие можно отменить.</p>
								<Button kind="danger" on:click={() => (archiveModalOpen = true)}>
									Архивировать проект
								</Button>
							{/if}
						</Tile>
					</div>
				{/if}
			</TabContent>

			<!-- Members Tab -->
			<TabContent>
				<div class="tab-header">
					<h3>Участники проекта</h3>
					<Button size="small" icon={UserFollow} on:click={() => openMemberModal()}>
						Добавить участника
					</Button>
				</div>

				{#if $projectsLoading}
					<Loading withOverlay={false} small />
				{:else}
					<DataTable
						headers={memberHeaders}
						rows={$projectMembers.map((m) => ({ id: String(m.user_id), ...m }))}
					>
						<svelte:fragment slot="cell" let:row let:cell>
							{#if cell.key === 'username'}
								<div class="user-cell">
									<span class="username">{row.username}</span>
									{#if row.full_name}
										<span class="full-name">{row.full_name}</span>
									{/if}
								</div>
							{:else if cell.key === 'role'}
								<Tag type={row.role === 'admin' ? 'red' : row.role === 'manager' ? 'blue' : 'gray'}>
									{roleLabels[cell.value] || cell.value}
								</Tag>
							{:else if cell.key === 'joined_at'}
								{new Date(cell.value).toLocaleDateString('ru-RU')}
							{:else if cell.key === 'actions'}
								<div class="actions">
									<Button
										kind="ghost"
										size="small"
										iconDescription="Изменить роль"
										icon={Edit}
										on:click={() => openMemberModal(row)}
									/>
									{#if $currentProject && row.user_id !== $currentProject.owner_id}
										<Button
											kind="ghost"
											size="small"
											iconDescription="Удалить"
											icon={TrashCan}
											on:click={() => confirmDelete('member', String(row.user_id), row.username)}
										/>
									{/if}
								</div>
							{:else}
								{cell.value}
							{/if}
						</svelte:fragment>
					</DataTable>
				{/if}
			</TabContent>

			<!-- Issue Types Tab -->
			<TabContent>
				<div class="tab-header">
					<h3>Типы задач</h3>
					<Button size="small" icon={Add} on:click={() => openIssueTypeModal()}>
						Добавить тип
					</Button>
				</div>

				{#if $issueTypesError}
					<InlineNotification
						kind="error"
						title="Ошибка"
						subtitle={$issueTypesError}
						on:close={() => issueTypes.clearError()}
					/>
				{/if}

				{#if $issueTypesLoading}
					<Loading withOverlay={false} small />
				{:else}
					<DataTable
						headers={issueTypeHeaders}
						rows={$issueTypesList.map((item) => ({ id: item.id, ...item }))}
					>
						<svelte:fragment slot="cell" let:row let:cell>
							{#if cell.key === 'color'}
								<span class="color-dot" style="background-color: {row.color}"></span>
							{:else if cell.key === 'is_subtask'}
								{cell.value ? 'Да' : 'Нет'}
							{:else if cell.key === 'actions'}
								<div class="actions">
									<Button
										kind="ghost"
										size="small"
										iconDescription="Редактировать"
										icon={Edit}
										on:click={() => openIssueTypeModal(row)}
									/>
									<Button
										kind="ghost"
										size="small"
										iconDescription="Удалить"
										icon={TrashCan}
										on:click={() => confirmDelete('issueType', row.id, row.name)}
									/>
								</div>
							{:else}
								{cell.value}
							{/if}
						</svelte:fragment>
					</DataTable>
				{/if}
			</TabContent>

			<!-- Statuses Tab -->
			<TabContent>
				<div class="tab-header">
					<h3>Статусы</h3>
					<Button size="small" icon={Add} on:click={() => openStatusModal()}>
						Добавить статус
					</Button>
				</div>

				{#if $statusesError}
					<InlineNotification
						kind="error"
						title="Ошибка"
						subtitle={$statusesError}
						on:close={() => statuses.clearError()}
					/>
				{/if}

				{#if $statusesLoading}
					<Loading withOverlay={false} small />
				{:else}
					<DataTable
						headers={statusHeaders}
						rows={$statusesList.map((item) => ({ id: item.id, ...item }))}
					>
						<svelte:fragment slot="cell" let:row let:cell>
							{#if cell.key === 'color'}
								<span class="color-dot" style="background-color: {row.color}"></span>
							{:else if cell.key === 'category'}
								<Tag type={row.category === 'done' ? 'green' : row.category === 'in_progress' ? 'blue' : 'gray'}>
									{categoryLabels[cell.value as keyof typeof categoryLabels]}
								</Tag>
							{:else if cell.key === 'actions'}
								<div class="actions">
									<Button
										kind="ghost"
										size="small"
										iconDescription="Редактировать"
										icon={Edit}
										on:click={() => openStatusModal(row)}
									/>
									<Button
										kind="ghost"
										size="small"
										iconDescription="Удалить"
										icon={TrashCan}
										on:click={() => confirmDelete('status', row.id, row.name)}
									/>
								</div>
							{:else}
								{cell.value}
							{/if}
						</svelte:fragment>
					</DataTable>
				{/if}
			</TabContent>
		</svelte:fragment>
	</Tabs>
</div>

<!-- Issue Type Modal -->
<Modal
	bind:open={issueTypeModalOpen}
	modalHeading={editingIssueType ? 'Редактировать тип задачи' : 'Новый тип задачи'}
	primaryButtonText="Сохранить"
	secondaryButtonText="Отмена"
	on:click:button--primary={handleIssueTypeSave}
	on:click:button--secondary={() => (issueTypeModalOpen = false)}
>
	<div class="modal-form">
		<TextInput bind:value={issueTypeForm.name} labelText="Название" required />

		<Select bind:selected={issueTypeForm.icon} labelText="Иконка">
			{#each icons as icon}
				<SelectItem value={icon.value} text={icon.label} />
			{/each}
		</Select>

		<Select bind:selected={issueTypeForm.color} labelText="Цвет">
			{#each colors as color}
				<SelectItem value={color.value} text={color.label} />
			{/each}
		</Select>

		<TextInput
			bind:value={issueTypeForm.order}
			labelText="Порядок"
			type="number"
		/>
	</div>
</Modal>

<!-- Status Modal -->
<Modal
	bind:open={statusModalOpen}
	modalHeading={editingStatus ? 'Редактировать статус' : 'Новый статус'}
	primaryButtonText="Сохранить"
	secondaryButtonText="Отмена"
	on:click:button--primary={handleStatusSave}
	on:click:button--secondary={() => (statusModalOpen = false)}
>
	<div class="modal-form">
		<TextInput bind:value={statusForm.name} labelText="Название" required />

		<Select bind:selected={statusForm.category} labelText="Категория">
			{#each categories as cat}
				<SelectItem value={cat.value} text={cat.label} />
			{/each}
		</Select>

		<Select bind:selected={statusForm.color} labelText="Цвет">
			{#each colors as color}
				<SelectItem value={color.value} text={color.label} />
			{/each}
		</Select>

		<TextInput
			bind:value={statusForm.order}
			labelText="Порядок"
			type="number"
		/>
	</div>
</Modal>

<!-- Member Modal -->
<Modal
	bind:open={memberModalOpen}
	modalHeading={editingMember ? 'Изменить роль' : 'Добавить участника'}
	primaryButtonText={editingMember ? 'Сохранить' : 'Добавить'}
	secondaryButtonText="Отмена"
	on:click:button--primary={handleMemberSave}
	on:click:button--secondary={() => (memberModalOpen = false)}
>
	<div class="modal-form">
		{#if !editingMember}
			<div class="user-search">
				<TextInput
					bind:value={userSearchQuery}
					labelText="Найти пользователя"
					placeholder="Введите имя или email"
					on:input={searchUsers}
				/>
				{#if userSearchResults.length > 0}
					<div class="search-results">
						{#each userSearchResults as user}
							<button class="search-result" on:click={() => selectUser(user)}>
								<div class="result-avatar">
									{user.full_name?.charAt(0) || user.username.charAt(0)}
								</div>
								<div class="result-info">
									<span class="result-name">{user.full_name || user.username}</span>
									<span class="result-details">@{user.username} · {user.email}</span>
								</div>
							</button>
						{/each}
					</div>
				{:else if userSearchQuery.length >= 2}
					<div class="search-no-results">
						Пользователи не найдены
					</div>
				{/if}
				{#if selectedUser}
					<div class="selected-user-card">
						<div class="selected-avatar">
							{selectedUser.username.charAt(0).toUpperCase()}
						</div>
						<div class="selected-info">
							<span class="selected-name">{selectedUser.username}</span>
							<span class="selected-email">{selectedUser.email}</span>
						</div>
						<button class="selected-remove" on:click={() => { selectedUser = null; userSearchQuery = ''; }} title="Убрать">
							<TrashCan size={16} />
						</button>
					</div>
				{/if}
			</div>
		{:else}
			<div class="selected-user-card">
				<div class="selected-avatar">
					{editingMember.username.charAt(0).toUpperCase()}
				</div>
				<div class="selected-info">
					<span class="selected-name">{editingMember.full_name || editingMember.username}</span>
					<span class="selected-email">{editingMember.email}</span>
				</div>
			</div>
		{/if}

		<Select bind:selected={memberForm.role} labelText="Роль">
			{#each roles as role}
				<SelectItem value={role.value} text={role.label} />
			{/each}
		</Select>
	</div>
</Modal>

<!-- Delete Confirmation Modal -->
<Modal
	danger
	bind:open={deleteModalOpen}
	modalHeading={deleteTarget?.type === 'member' ? 'Удалить участника' : 'Удалить'}
	primaryButtonText="Удалить"
	secondaryButtonText="Отмена"
	on:click:button--primary={handleDelete}
	on:click:button--secondary={() => (deleteModalOpen = false)}
>
	{#if deleteTarget?.type === 'member'}
		<p>
			Вы уверены, что хотите удалить участника <strong>{deleteTarget?.name}</strong> из проекта?
		</p>
		<p style="color: var(--cds-text-secondary); margin-top: 0.5rem;">
			Пользователь потеряет доступ к проекту и его задачам.
		</p>
	{:else}
		<p>
			Вы уверены, что хотите удалить «{deleteTarget?.name}»?
			Это действие нельзя отменить.
		</p>
	{/if}
</Modal>

<!-- Archive Confirmation Modal -->
<Modal
	danger
	bind:open={archiveModalOpen}
	modalHeading="Архивировать проект"
	primaryButtonText="Архивировать"
	secondaryButtonText="Отмена"
	on:click:button--primary={handleArchive}
	on:click:button--secondary={() => (archiveModalOpen = false)}
>
	<p>
		Вы уверены, что хотите архивировать проект <strong>{$currentProject?.name}</strong>?
		Проект будет скрыт из списка, но данные сохранятся.
	</p>
</Modal>

<!-- Restore Confirmation Modal -->
<Modal
	bind:open={restoreModalOpen}
	modalHeading="Восстановить проект"
	primaryButtonText="Восстановить"
	secondaryButtonText="Отмена"
	on:click:button--primary={handleRestore}
	on:click:button--secondary={() => (restoreModalOpen = false)}
>
	<p>
		Восстановить проект <strong>{$currentProject?.name}</strong> из архива?
		Он снова станет доступен в списке проектов.
	</p>
</Modal>

<!-- Permanent Delete Confirmation Modal -->
<Modal
	danger
	bind:open={permanentDeleteModalOpen}
	modalHeading="Удалить проект навсегда"
	primaryButtonText="Удалить навсегда"
	secondaryButtonText="Отмена"
	on:click:button--primary={handlePermanentDelete}
	on:click:button--secondary={() => (permanentDeleteModalOpen = false)}
>
	<p>
		Вы уверены, что хотите <strong>навсегда удалить</strong> проект <strong>{$currentProject?.name}</strong>?
	</p>
	<p style="color: var(--cds-support-error); margin-top: 1rem;">
		Это действие нельзя отменить. Все задачи, комментарии и настройки проекта будут удалены безвозвратно.
	</p>
</Modal>

<style>
	.settings-page {
		padding: 1rem 2rem;
	}

	h1 {
		margin: 1.5rem 0;
		font-size: 1.75rem;
		font-weight: 600;
	}

	h3 {
		font-size: 1.25rem;
		font-weight: 600;
		margin: 0;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.tab-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
		padding: 1rem 0;
	}

	.general-settings {
		max-width: 600px;
	}

	.form-section {
		margin-bottom: 1.5rem;
	}

	.form-section.readonly {
		opacity: 0.7;
	}

	.form-actions {
		margin-bottom: 2rem;
	}

	:global(.danger-zone) {
		margin-top: 3rem;
		border: 1px solid var(--cds-support-error) !important;
		background-color: rgba(218, 30, 40, 0.05) !important;
	}

	:global(.danger-zone h3) {
		color: var(--cds-support-error);
		margin-bottom: 1rem;
	}

	:global(.danger-zone p) {
		margin-bottom: 1rem;
		color: var(--cds-text-secondary);
	}

	.archived-notice {
		margin-bottom: 1.5rem;
	}

	.danger-actions {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.danger-action {
		padding-top: 1rem;
		border-top: 1px solid var(--cds-border-subtle);
	}

	.danger-action:first-child {
		padding-top: 0;
		border-top: none;
	}

	.danger-action p {
		margin-bottom: 0.75rem;
	}

	.color-dot {
		display: inline-block;
		width: 16px;
		height: 16px;
		border-radius: 50%;
	}

	.actions {
		display: flex;
		gap: 0.25rem;
	}

	.user-cell {
		display: flex;
		flex-direction: column;
	}

	.user-cell .username {
		font-weight: 500;
	}

	.user-cell .full-name {
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
	}

	.modal-form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.user-search {
		position: relative;
	}

	.search-results {
		margin-top: 0.5rem;
		background: var(--cds-layer-02, #393939);
		border: 1px solid var(--cds-border-strong-01, #6f6f6f);
		border-radius: 4px;
		max-height: 240px;
		overflow-y: auto;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
	}

	.search-result {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
		padding: 0.75rem 1rem;
		text-align: left;
		background: none;
		border: none;
		border-bottom: 1px solid var(--cds-border-subtle);
		cursor: pointer;
		color: var(--cds-text-primary);
		transition: background-color 0.1s ease;
	}

	.search-result:last-child {
		border-bottom: none;
	}

	.search-result:hover {
		background: var(--cds-layer-hover, #474747);
	}

	.result-avatar {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: var(--cds-interactive, #0f62fe);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: 600;
		font-size: 0.875rem;
		text-transform: uppercase;
		flex-shrink: 0;
	}

	.result-info {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.result-name {
		font-weight: 500;
		color: var(--cds-text-primary);
	}

	.result-details {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.search-no-results {
		margin-top: 0.5rem;
		padding: 1rem;
		background: var(--cds-layer-02, #393939);
		border: 1px solid var(--cds-border-subtle);
		border-radius: 4px;
		color: var(--cds-text-secondary);
		text-align: center;
		font-size: 0.875rem;
	}

	.selected-user-card {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-top: 1rem;
		padding: 0.75rem 1rem;
		background: var(--cds-layer-accent-01, #002d9c);
		border-radius: 4px;
	}

	.selected-avatar {
		width: 40px;
		height: 40px;
		border-radius: 50%;
		background: var(--cds-interactive, #0f62fe);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: 600;
		font-size: 1rem;
		flex-shrink: 0;
	}

	.selected-info {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-width: 0;
	}

	.selected-name {
		font-weight: 600;
		color: var(--cds-text-on-color, white);
	}

	.selected-email {
		font-size: 0.75rem;
		color: var(--cds-text-on-color-secondary, rgba(255, 255, 255, 0.7));
	}

	.selected-remove {
		padding: 0.5rem;
		border-radius: 4px;
		border: none;
		background: transparent;
		color: rgba(255, 255, 255, 0.7);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: background-color 0.1s ease, color 0.1s ease;
	}

	.selected-remove:hover {
		background: rgba(255, 255, 255, 0.15);
		color: white;
	}

	:global(.bx--tab-content) {
		padding: 1rem 0;
	}
</style>
