<script lang="ts">
	import 'carbon-components-svelte/css/g90.css';
	import {
		Header,
		HeaderNav,
		HeaderNavItem,
		HeaderUtilities,
		HeaderAction,
		HeaderPanelLinks,
		HeaderPanelLink,
		HeaderPanelDivider,
		SkipToContent,
		Content,
		Theme,
		Loading
	} from 'carbon-components-svelte';
	import { UserAvatar, Logout } from 'carbon-icons-svelte';
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { auth, user, isAuthenticated, isLoading } from '$lib/stores/auth';
	import { setup, setupRequired, setupLoading } from '$lib/stores/setup';
	import { events } from '$lib/stores/events';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import EventNotification from '$lib/components/EventNotification.svelte';
	import { GlobalSearch } from '$lib/components/search';

	let { children } = $props();

	let isUserMenuOpen = $state(false);

	// Check if current route is auth or setup page
	const isAuthPage = $derived($page.url.pathname.startsWith('/auth'));
	const isSetupPage = $derived($page.url.pathname.startsWith('/setup'));

	// Combined loading state
	const isInitializing = $derived($isLoading || $setupLoading);

	onMount(async () => {
		// First check if setup is required
		await setup.checkStatus();
		// Then init auth (will fail gracefully if no users exist)
		await auth.init();
	});

	// Connect/disconnect SSE based on authentication status
	$effect(() => {
		if ($isAuthenticated) {
			events.connect();
		} else {
			events.disconnect();
		}
	});

	onDestroy(() => {
		events.disconnect();
	});

	// Redirect logic
	$effect(() => {
		if (!isInitializing) {
			// If setup is required, redirect to setup page
			if ($setupRequired && !isSetupPage) {
				goto('/setup');
				return;
			}

			// If setup is complete but not authenticated, redirect to login
			if (!$setupRequired && !isAuthPage && !isSetupPage && !$isAuthenticated) {
				goto('/auth/login');
			}
		}
	});

	function handleLogout() {
		auth.logout();
		goto('/auth/login');
	}
</script>

<Theme theme="g90" />
<ToastContainer />
<EventNotification />

<svelte:head>
	<title>CTrack</title>
</svelte:head>

{#if isAuthPage || isSetupPage}
	{@render children()}
{:else if isInitializing}
	<div class="loading-container">
		<Loading withOverlay={false} />
	</div>
{:else if $isAuthenticated}
	<Header company="CTrack">
		<svelte:fragment slot="skip-to-content">
			<SkipToContent />
		</svelte:fragment>

		<HeaderNav>
			<HeaderNavItem href="/" text="Главная" />
			<HeaderNavItem href="/projects" text="Проекты" />
			<HeaderNavItem href="/tasks" text="Задачи" />
			<HeaderNavItem href="/feed" text="Лента" />
			{#if $user?.is_staff}
				<HeaderNavItem href="/admin" text="Админ" />
			{/if}
		</HeaderNav>

		<HeaderUtilities>
			<GlobalSearch />
			<HeaderAction bind:isOpen={isUserMenuOpen} icon={UserAvatar}>
				<HeaderPanelLinks>
					<div class="user-info">
						<span class="user-name">{$user?.first_name || $user?.username}</span>
						<span class="user-email">{$user?.email}</span>
					</div>
					<HeaderPanelDivider />
					<HeaderPanelLink href="/settings/profile">Профиль</HeaderPanelLink>
					<HeaderPanelLink href="/settings/password">Сменить пароль</HeaderPanelLink>
					<HeaderPanelDivider />
					<HeaderPanelLink onclick={handleLogout}>
						<Logout size={16} style="margin-right: 0.5rem; vertical-align: middle;" />
						Выйти
					</HeaderPanelLink>
				</HeaderPanelLinks>
			</HeaderAction>
		</HeaderUtilities>
	</Header>

	<Content>
		{@render children()}
	</Content>
{/if}

<style>
	:global(body) {
		margin: 0;
		padding: 0;
	}

	.loading-container {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--cds-background);
	}

	.user-info {
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.user-name {
		font-weight: 600;
		color: var(--cds-text-primary);
	}

	.user-email {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}

	/* Fix panel link styling */
	:global(.bx--header-panel-links) {
		padding: 0;
	}

	:global(.bx--header-panel-link) {
		padding: 0.75rem 1rem;
	}

	:global(.bx--header-panel-divider) {
		margin: 0.5rem 0;
		border-color: var(--cds-border-subtle);
	}

	/* Global fix for DatePicker calendar z-index in modals */
	:global(.flatpickr-calendar) {
		z-index: 10001 !important;
	}
</style>
