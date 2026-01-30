<script lang="ts">
	import { page } from '$app/state';
	import { Home, TaskView, Activity, Search } from 'carbon-icons-svelte';
	import { search } from '$lib/stores/search';

	interface NavItem {
		href: string;
		icon: typeof Home;
		label: string;
		action?: () => void;
	}

	const navItems: NavItem[] = [
		{ href: '/', icon: Home, label: 'Главная' },
		{ href: '/tasks', icon: TaskView, label: 'Задачи' },
		{ href: '/feed', icon: Activity, label: 'Лента' },
		{ href: '#search', icon: Search, label: 'Поиск', action: () => search.open() }
	];

	function isActive(href: string): boolean {
		if (href === '#search') return false;
		if (href === '/') return page.url.pathname === '/';
		return page.url.pathname.startsWith(href);
	}

	function handleClick(item: NavItem, event: MouseEvent) {
		if (item.action) {
			event.preventDefault();
			item.action();
		}
	}
</script>

<nav class="mobile-nav" aria-label="Основная навигация">
	{#each navItems as item (item.href)}
		<a
			href={item.href}
			class="nav-item"
			class:active={isActive(item.href)}
			onclick={(e) => handleClick(item, e)}
			aria-current={isActive(item.href) ? 'page' : undefined}
		>
			<svelte:component this={item.icon} size={24} />
			<span class="nav-label">{item.label}</span>
		</a>
	{/each}
</nav>

<style>
	.mobile-nav {
		display: none;
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		height: 64px;
		background: var(--cds-layer);
		border-top: 1px solid var(--cds-border-subtle);
		z-index: 9000;
		padding-bottom: env(safe-area-inset-bottom);
	}

	@media (max-width: 768px) {
		.mobile-nav {
			display: flex;
			justify-content: space-around;
			align-items: center;
		}
	}

	.nav-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.25rem;
		padding: 0.5rem 1rem;
		color: var(--cds-text-secondary);
		text-decoration: none;
		transition: color 0.15s ease;
		min-width: 64px;
	}

	.nav-item:hover,
	.nav-item:focus {
		color: var(--cds-text-primary);
	}

	.nav-item.active {
		color: var(--cds-interactive);
	}

	.nav-item.active :global(svg) {
		color: var(--cds-interactive);
	}

	.nav-label {
		font-size: 0.6875rem;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.02em;
	}
</style>
