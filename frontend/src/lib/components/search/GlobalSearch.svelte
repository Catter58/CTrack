<script lang="ts">
	import { Search, Close } from 'carbon-icons-svelte';
	import { Loading } from 'carbon-components-svelte';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import {
		search,
		searchQuery,
		searchResults,
		searchIsLoading,
		searchIsOpen
	} from '$lib/stores/search';
	import SearchResults from './SearchResults.svelte';

	let inputRef: HTMLInputElement | null = $state(null);
	let containerRef: HTMLDivElement | null = $state(null);
	let selectedIndex = $state(-1);
	// eslint-disable-next-line svelte/prefer-writable-derived -- localQuery is modified both by store sync and user input
	let localQuery = $state('');

	// Sync local query with store
	$effect(() => {
		localQuery = $searchQuery;
	});

	// Calculate total items for keyboard navigation
	const totalItems = $derived(
		($searchResults?.issues.length ?? 0) + ($searchResults?.projects.length ?? 0)
	);

	// Keyboard shortcut (Cmd+K / Ctrl+K)
	$effect(() => {
		if (!browser) return;

		const handler = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
				e.preventDefault();
				search.open();
				// Focus input after opening
				setTimeout(() => inputRef?.focus(), 0);
			}
		};

		window.addEventListener('keydown', handler);
		return () => window.removeEventListener('keydown', handler);
	});

	// Handle click outside
	$effect(() => {
		if (!browser || !$searchIsOpen) return;

		const handler = (e: MouseEvent) => {
			if (containerRef && !containerRef.contains(e.target as Node)) {
				search.close();
			}
		};

		// Delay to prevent immediate close on open
		setTimeout(() => {
			document.addEventListener('click', handler);
		}, 0);

		return () => document.removeEventListener('click', handler);
	});

	// Reset selected index when results change
	$effect(() => {
		if ($searchResults) {
			selectedIndex = -1;
		}
	});

	function handleInput(e: Event) {
		const target = e.target as HTMLInputElement;
		localQuery = target.value;
		search.setQuery(target.value);
		selectedIndex = -1;
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			e.preventDefault();
			if (localQuery) {
				search.reset();
				localQuery = '';
			} else {
				search.close();
			}
			return;
		}

		if (e.key === 'Enter') {
			e.preventDefault();
			if (selectedIndex >= 0 && $searchResults) {
				// Navigate to selected item
				const issues = $searchResults.issues;
				const projects = $searchResults.projects;

				if (selectedIndex < issues.length) {
					goto(`/issues/${issues[selectedIndex].key}`);
				} else {
					const projectIndex = selectedIndex - issues.length;
					goto(`/projects/${projects[projectIndex].key}/board`);
				}
				search.close();
			} else if (localQuery.trim()) {
				// Go to search page
				goto(`/search?q=${encodeURIComponent(localQuery)}`);
				search.close();
			}
			return;
		}

		if (e.key === 'ArrowDown') {
			e.preventDefault();
			if (totalItems > 0) {
				selectedIndex = (selectedIndex + 1) % totalItems;
			}
			return;
		}

		if (e.key === 'ArrowUp') {
			e.preventDefault();
			if (totalItems > 0) {
				selectedIndex = selectedIndex <= 0 ? totalItems - 1 : selectedIndex - 1;
			}
			return;
		}
	}

	function handleFocus() {
		search.open();
	}

	function handleClear() {
		search.reset();
		localQuery = '';
		inputRef?.focus();
	}

	function handleResultSelect() {
		search.close();
	}

	function handleSearchClick() {
		search.open();
		setTimeout(() => inputRef?.focus(), 0);
	}

	// Platform detection for shortcut hint
	const isMac = $derived(browser && navigator.platform.toUpperCase().indexOf('MAC') >= 0);
	const shortcutHint = $derived(isMac ? '⌘K' : 'Ctrl+K');
</script>

<div class="global-search" bind:this={containerRef}>
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="search-trigger" class:is-open={$searchIsOpen} onclick={handleSearchClick}>
		<Search size={20} />
		{#if !$searchIsOpen}
			<span class="search-placeholder">Поиск...</span>
			<span class="search-shortcut">{shortcutHint}</span>
		{/if}
	</div>

	{#if $searchIsOpen}
		<div class="search-dropdown">
			<div class="search-input-wrapper">
				<Search size={20} class="search-icon" />
				<input
					bind:this={inputRef}
					type="text"
					class="search-input"
					placeholder="Поиск задач и проектов..."
					value={localQuery}
					oninput={handleInput}
					onkeydown={handleKeyDown}
					onfocus={handleFocus}
				/>
				{#if $searchIsLoading}
					<div class="search-loading">
						<Loading withOverlay={false} small />
					</div>
				{:else if localQuery}
					<button class="search-clear" onclick={handleClear} aria-label="Очистить">
						<Close size={20} />
					</button>
				{/if}
			</div>

			{#if $searchResults}
				<SearchResults
					issues={$searchResults.issues.slice(0, 5)}
					projects={$searchResults.projects.slice(0, 3)}
					{selectedIndex}
					onSelect={handleResultSelect}
				/>
				{#if localQuery.trim()}
					<div class="search-footer">
						<span class="search-hint">
							Нажмите <kbd>Enter</kbd> для полного поиска
						</span>
					</div>
				{/if}
			{:else if localQuery && !$searchIsLoading}
				<div class="search-empty">
					<span>Начните вводить для поиска</span>
				</div>
			{:else if !localQuery}
				<div class="search-empty">
					<span>Введите запрос для поиска задач и проектов</span>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.global-search {
		position: relative;
		display: flex;
		align-items: center;
		height: 3rem; /* Match Carbon header height (48px) */
	}

	.search-trigger {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0 1rem;
		height: 100%;
		background: transparent;
		border: none;
		border-radius: 0;
		cursor: pointer;
		transition: background-color 0.15s ease;
		min-width: 180px;
	}

	.search-trigger:hover {
		background: var(--cds-layer-hover, #353535);
	}

	.search-trigger.is-open {
		background: var(--cds-layer-selected, #393939);
	}

	.search-trigger :global(svg) {
		color: var(--cds-icon-secondary, #c6c6c6);
		flex-shrink: 0;
	}

	.search-placeholder {
		font-size: 0.875rem;
		color: var(--cds-text-placeholder, #6f6f6f);
		flex: 1;
	}

	.search-shortcut {
		font-size: 0.6875rem;
		color: var(--cds-text-secondary, #c6c6c6);
		background: var(--cds-layer-accent, #333333);
		padding: 0.125rem 0.375rem;
		border-radius: 2px;
		border: 1px solid var(--cds-border-subtle, #525252);
	}

	.search-dropdown {
		position: fixed;
		top: 3rem;
		left: 50%;
		transform: translateX(-50%);
		width: 480px;
		max-width: calc(100vw - 2rem);
		background: var(--cds-layer, #262626);
		border: 1px solid var(--cds-border-subtle, #525252);
		border-radius: 8px;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
		overflow: hidden;
		z-index: 9999;
	}

	.search-input-wrapper {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid var(--cds-border-subtle, #525252);
		background: var(--cds-layer, #262626);
	}

	.search-input-wrapper :global(.search-icon) {
		color: var(--cds-icon-secondary);
		flex-shrink: 0;
	}

	.search-input {
		flex: 1;
		background: transparent;
		border: none;
		outline: none;
		font-size: 1rem;
		color: var(--cds-text-primary);
	}

	.search-input::placeholder {
		color: var(--cds-text-placeholder);
	}

	.search-loading {
		display: flex;
		align-items: center;
	}

	.search-loading :global(.bx--loading) {
		width: 20px;
		height: 20px;
	}

	.search-clear {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0.25rem;
		background: transparent;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		color: var(--cds-icon-secondary);
		transition: all 0.1s ease;
	}

	.search-clear:hover {
		background: var(--cds-layer-hover);
		color: var(--cds-text-primary);
	}

	.search-empty {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
		color: var(--cds-text-secondary, #c6c6c6);
		font-size: 0.875rem;
		background: var(--cds-layer, #262626);
	}

	.search-footer {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0.75rem;
		border-top: 1px solid var(--cds-border-subtle, #525252);
		background: var(--cds-layer-accent, #333333);
	}

	.search-hint {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}

	.search-hint kbd {
		display: inline-block;
		padding: 0.125rem 0.375rem;
		font-size: 0.6875rem;
		font-family: inherit;
		background: var(--cds-layer);
		border: 1px solid var(--cds-border-subtle);
		border-radius: 3px;
		margin: 0 0.25rem;
	}
</style>
