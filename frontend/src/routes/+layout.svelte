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
		SideNav,
		SideNavItems,
		SideNavLink,
		SideNavDivider,
		Content,
		Theme,
		Loading
	} from 'carbon-components-svelte';
	import {
		UserAvatar,
		Logout,
		Home,
		FolderDetails,
		TaskView,
		Activity,
		Settings
	} from 'carbon-icons-svelte';
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { auth, user, isAuthenticated, isLoading } from '$lib/stores/auth';
	import { setup, setupRequired, setupLoading } from '$lib/stores/setup';
	import { events } from '$lib/stores/events';
	import { pwa } from '$lib/stores/pwa';
	import { isMobile } from '$lib/stores/mobile';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import EventNotification from '$lib/components/EventNotification.svelte';
	import InstallPrompt from '$lib/components/InstallPrompt.svelte';
	import MobileNav from '$lib/components/MobileNav.svelte';
	import PageTransition from '$lib/components/PageTransition.svelte';
	import GlobalProgress from '$lib/components/GlobalProgress.svelte';
	import { GlobalSearch } from '$lib/components/search';

	let { children } = $props();

	let isUserMenuOpen = $state(false);
	let isSideNavOpen = $state(false);
	let cleanupPwa: (() => void) | undefined;

	// Check if current route is auth or setup page
	const isAuthPage = $derived(page.url.pathname.startsWith('/auth'));
	const isSetupPage = $derived(page.url.pathname.startsWith('/setup'));

	// Combined loading state
	const isInitializing = $derived($isLoading || $setupLoading);

	// Close sidebar on route change (mobile)
	$effect(() => {
		// Track page changes - void used to satisfy eslint no-unused-expressions
		void page.url.pathname;
		if ($isMobile && isSideNavOpen) {
			isSideNavOpen = false;
		}
	});

	onMount(async () => {
		// Initialize PWA install prompt listener
		cleanupPwa = pwa.init();
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
		cleanupPwa?.();
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

	function handleSidenavLogout() {
		isSideNavOpen = false;
		handleLogout();
	}
</script>

<Theme theme="g90" />
<GlobalProgress />
<ToastContainer />
<EventNotification />
<InstallPrompt />

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
	{@const headerProps = { company: 'CTrack' } as unknown as Record<string, never>}
	<Header {...headerProps} bind:isSideNavOpen>
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
					<HeaderPanelLink href="/settings/notifications">Уведомления</HeaderPanelLink>
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

	<!-- Mobile Sidebar (only on mobile) -->
	{#if $isMobile}
		<SideNav bind:isOpen={isSideNavOpen} rail={false}>
			<SideNavItems>
				<SideNavLink icon={Home} href="/" text="Главная" isSelected={page.url.pathname === '/'} />
				<SideNavLink
					icon={FolderDetails}
					href="/projects"
					text="Проекты"
					isSelected={page.url.pathname.startsWith('/projects')}
				/>
				<SideNavLink
					icon={TaskView}
					href="/tasks"
					text="Задачи"
					isSelected={page.url.pathname.startsWith('/tasks')}
				/>
				<SideNavLink
					icon={Activity}
					href="/feed"
					text="Лента"
					isSelected={page.url.pathname.startsWith('/feed')}
				/>
				{#if $user?.is_staff}
					<SideNavLink
						icon={Settings}
						href="/admin"
						text="Админ"
						isSelected={page.url.pathname.startsWith('/admin')}
					/>
				{/if}
				<SideNavDivider />
				<SideNavLink icon={UserAvatar} href="/settings/profile" text="Профиль" />
				<SideNavLink icon={Logout} text="Выйти" on:click={handleSidenavLogout} />
			</SideNavItems>
		</SideNav>
	{/if}

	<Content class={$isMobile ? 'mobile-content' : ''}>
		<PageTransition>
			{@render children()}
		</PageTransition>
	</Content>

	<!-- Mobile bottom navigation -->
	{#if $isMobile}
		<MobileNav />
	{/if}
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

	/* Hide hamburger menu on desktop */
	:global(.bx--header__menu-trigger) {
		display: none;
	}

	/* Mobile-specific styles */
	@media (max-width: 768px) {
		/* Hide desktop header nav on mobile */
		:global(.bx--header__nav) {
			display: none !important;
		}

		/* Make header menu button visible */
		:global(.bx--header__menu-trigger) {
			display: flex !important;
		}

		/* Hide search trigger text on mobile */
		:global(.search-trigger .search-placeholder),
		:global(.search-trigger .search-shortcut) {
			display: none;
		}

		:global(.search-trigger) {
			min-width: auto !important;
			padding: 0 0.75rem !important;
		}

		/* Add padding bottom for mobile nav */
		:global(.bx--content.mobile-content) {
			padding-bottom: calc(64px + env(safe-area-inset-bottom)) !important;
		}

		/* Side nav overlay */
		:global(.bx--side-nav--ux) {
			top: 48px;
			z-index: 8999;
		}

		:global(.bx--side-nav__overlay) {
			top: 48px;
			z-index: 8998;
		}

		/* Full-screen modals on mobile */
		:global(.bx--modal-container) {
			width: 100% !important;
			max-width: 100% !important;
			height: 100% !important;
			max-height: 100% !important;
			margin: 0 !important;
			border-radius: 0 !important;
		}

		:global(.bx--modal-content) {
			max-height: calc(100vh - 120px) !important;
			padding-bottom: 1rem !important;
		}

		:global(.bx--modal-header) {
			padding: 1rem !important;
		}

		:global(.bx--modal-footer) {
			padding: 1rem !important;
		}

		/* User panel adjustments */
		:global(.bx--header-panel) {
			width: 100% !important;
			max-width: 100% !important;
		}
	}
</style>
