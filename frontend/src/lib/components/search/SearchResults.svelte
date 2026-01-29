<script lang="ts">
	import { goto } from '$app/navigation';
	import { Document, Folder } from 'carbon-icons-svelte';
	import type { SearchIssue, SearchProject } from '$lib/stores/search';

	interface Props {
		issues: SearchIssue[];
		projects: SearchProject[];
		selectedIndex: number;
		onSelect?: () => void;
	}

	let { issues, projects, selectedIndex, onSelect }: Props = $props();

	function handleIssueClick(issue: SearchIssue) {
		goto(`/issues/${issue.key}`);
		onSelect?.();
	}

	function handleProjectClick(project: SearchProject) {
		goto(`/projects/${project.key}/board`);
		onSelect?.();
	}

	function getItemIndex(type: 'issue' | 'project', index: number): number {
		if (type === 'issue') return index;
		return issues.length + index;
	}
</script>

<div class="search-results">
	{#if issues.length > 0}
		<div class="results-section">
			<div class="section-header">
				<Document size={16} />
				<span>Задачи</span>
			</div>
			{#each issues as issue, i (issue.id)}
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="result-item"
					class:selected={selectedIndex === getItemIndex('issue', i)}
					onclick={() => handleIssueClick(issue)}
				>
					<div class="result-main">
						<span class="result-key">{issue.key}</span>
						<span class="result-title">{issue.title}</span>
					</div>
					<div class="result-meta">
						<span class="result-project">{issue.project.name}</span>
						<span
							class="result-status"
							style="background-color: {issue.status.color}20; color: {issue.status.color}"
						>
							{issue.status.name}
						</span>
					</div>
				</div>
			{/each}
		</div>
	{/if}

	{#if projects.length > 0}
		<div class="results-section">
			<div class="section-header">
				<Folder size={16} />
				<span>Проекты</span>
			</div>
			{#each projects as project, i (project.id)}
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="result-item"
					class:selected={selectedIndex === getItemIndex('project', i)}
					onclick={() => handleProjectClick(project)}
				>
					<div class="result-main">
						<span class="result-key">{project.key}</span>
						<span class="result-title">{project.name}</span>
					</div>
				</div>
			{/each}
		</div>
	{/if}

	{#if issues.length === 0 && projects.length === 0}
		<div class="no-results">
			<span>Ничего не найдено</span>
		</div>
	{/if}
</div>

<style>
	.search-results {
		max-height: 400px;
		overflow-y: auto;
		background: var(--cds-layer, #262626);
	}

	.results-section {
		padding: 0.5rem 0;
		background: var(--cds-layer, #262626);
	}

	.results-section:not(:last-child) {
		border-bottom: 1px solid var(--cds-border-subtle, #525252);
	}

	.section-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--cds-text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.result-item {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		padding: 0.75rem 1rem;
		cursor: pointer;
		transition: background-color 0.1s ease;
	}

	.result-item:hover,
	.result-item.selected {
		background-color: var(--cds-layer-hover, #353535);
	}

	.result-item.selected {
		background-color: var(--cds-layer-selected, #393939);
	}

	.result-main {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.result-key {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--cds-link-primary);
		flex-shrink: 0;
	}

	.result-title {
		font-size: 0.875rem;
		color: var(--cds-text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.result-meta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-left: 0;
	}

	.result-project {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}

	.result-status {
		font-size: 0.625rem;
		font-weight: 500;
		padding: 0.125rem 0.375rem;
		border-radius: 2px;
		text-transform: uppercase;
	}

	.no-results {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
		color: var(--cds-text-secondary, #c6c6c6);
		font-size: 0.875rem;
		background: var(--cds-layer, #262626);
	}
</style>
