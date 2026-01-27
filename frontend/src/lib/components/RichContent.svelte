<script lang="ts">
	interface Block {
		type: string;
		data: {
			text?: string;
			level?: number;
			items?: string[];
			style?: string;
			caption?: string;
			code?: string;
		};
	}

	interface Props {
		content: string;
	}

	let { content }: Props = $props();

	let blocks = $derived.by((): Block[] => {
		if (!content) return [];
		try {
			const parsed = JSON.parse(content);
			return (parsed.blocks || []) as Block[];
		} catch {
			// Plain text fallback
			return content.trim()
				? [{ type: 'paragraph', data: { text: content } }]
				: [];
		}
	});
</script>

<!-- eslint-disable svelte/no-at-html-tags -- EditorJS content is trusted -->
{#if blocks.length > 0}
	<div class="rich-content">
		{#each blocks as block, i (i)}
			{#if block.type === 'paragraph'}
				<p>{@html block.data.text}</p>
			{:else if block.type === 'header'}
				{#if block.data.level === 2}
					<h2>{@html block.data.text}</h2>
				{:else if block.data.level === 3}
					<h3>{@html block.data.text}</h3>
				{:else}
					<h4>{@html block.data.text}</h4>
				{/if}
			{:else if block.type === 'list'}
				{#if block.data.style === 'ordered'}
					<ol>
						{#each block.data.items as item, j (j)}
							<li>{@html item}</li>
						{/each}
					</ol>
				{:else}
					<ul>
						{#each block.data.items as item, j (j)}
							<li>{@html item}</li>
						{/each}
					</ul>
				{/if}
			{:else if block.type === 'quote'}
				<blockquote>
					<p>{@html block.data.text}</p>
					{#if block.data.caption}
						<cite>{@html block.data.caption}</cite>
					{/if}
				</blockquote>
			{:else if block.type === 'code'}
				<pre><code>{block.data.code}</code></pre>
			{/if}
		{/each}
	</div>
{:else}
	<p class="no-content">Описание отсутствует</p>
{/if}

<style>
	.rich-content {
		line-height: 1.6;
	}

	.rich-content h2,
	.rich-content h3,
	.rich-content h4 {
		margin: 1rem 0 0.5rem;
		font-weight: 600;
	}

	.rich-content h2 {
		font-size: 1.25rem;
	}

	.rich-content h3 {
		font-size: 1.125rem;
	}

	.rich-content h4 {
		font-size: 1rem;
	}

	.rich-content p {
		margin: 0.5rem 0;
	}

	.rich-content ul,
	.rich-content ol {
		margin: 0.5rem 0;
		padding-left: 1.5rem;
	}

	.rich-content li {
		margin: 0.25rem 0;
	}

	.rich-content blockquote {
		border-left: 3px solid var(--cds-border-strong);
		padding-left: 1rem;
		margin: 0.5rem 0;
		color: var(--cds-text-secondary);
	}

	.rich-content blockquote cite {
		display: block;
		font-size: 0.875rem;
		color: var(--cds-text-helper);
		margin-top: 0.5rem;
	}

	.rich-content pre {
		background: var(--cds-layer);
		padding: 1rem;
		border-radius: 4px;
		overflow-x: auto;
		margin: 0.5rem 0;
	}

	.rich-content code {
		font-family: 'IBM Plex Mono', monospace;
		font-size: 0.875rem;
	}

	/* Marker highlighting */
	.rich-content :global(.cdx-marker),
	.rich-content :global(mark) {
		background: rgba(245, 235, 111, 0.3);
		padding: 0.1em 0.2em;
	}

	.no-content {
		color: var(--cds-text-secondary);
		font-style: italic;
		margin: 0;
	}
</style>
