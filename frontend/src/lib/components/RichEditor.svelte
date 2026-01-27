<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import type EditorJS from '@editorjs/editorjs';

	interface Props {
		value?: string | null;
		readonly?: boolean;
		placeholder?: string;
		onchange?: (json: string) => void;
	}

	let { value = '', readonly = false, placeholder = 'Начните писать...', onchange }: Props = $props();

	// Normalize null to empty string
	const normalizedValue = $derived(value ?? '');

	let editorElement = $state<HTMLDivElement | null>(null);
	let editor: EditorJS | null = null;
	let isReady = $state(false);
	let initError = $state<string | null>(null);

	interface EditorData {
		time?: number;
		blocks: Array<{ id?: string; type: string; data: Record<string, unknown> }>;
		version?: string;
	}

	function parseValue(val: string | null | undefined): EditorData {
		if (!val) return { blocks: [] };
		try {
			const parsed = JSON.parse(val);
			if (parsed.blocks) return parsed as EditorData;
		} catch {
			// Plain text - convert to EditorJS format
			if (val.trim()) {
				return {
					blocks: [{ type: 'paragraph', data: { text: val } }]
				};
			}
		}
		return { blocks: [] };
	}

	onMount(async () => {
		// Wait a tick for the element to be bound
		await new Promise((resolve) => setTimeout(resolve, 0));

		if (!editorElement) {
			initError = 'Editor element not found';
			return;
		}

		try {
			// Dynamic imports for SSR compatibility
			const EditorJS = (await import('@editorjs/editorjs')).default;
			const Header = (await import('@editorjs/header')).default;
			const List = (await import('@editorjs/list')).default;
			const Quote = (await import('@editorjs/quote')).default;
			const CodeTool = (await import('@editorjs/code')).default;
			const Marker = (await import('@editorjs/marker')).default;

			const data = parseValue(normalizedValue);

			editor = new EditorJS({
				holder: editorElement,
				readOnly: readonly,
				placeholder,
				data,
				tools: {
					header: {
						class: Header,
						config: {
							levels: [2, 3, 4],
							defaultLevel: 2
						}
					},
					list: {
						class: List,
						inlineToolbar: true
					},
					quote: {
						class: Quote,
						inlineToolbar: true
					},
					code: CodeTool,
					marker: {
						class: Marker,
						shortcut: 'CMD+SHIFT+M'
					}
				},
				onChange: async () => {
					if (editor && onchange && isReady) {
						try {
							const output = await editor.save();
							onchange(JSON.stringify(output));
						} catch (err) {
							console.error('EditorJS save error:', err);
						}
					}
				},
				onReady: () => {
					isReady = true;
				}
			});

			// Wait for editor to be ready
			await editor.isReady;
		} catch (err) {
			console.error('EditorJS init error:', err);
			initError = err instanceof Error ? err.message : 'Failed to initialize editor';
		}
	});

	onDestroy(() => {
		if (editor) {
			editor.destroy();
			editor = null;
		}
	});
</script>

<div class="editor-container">
	{#if initError}
		<div class="editor-error">
			<p>Ошибка инициализации редактора: {initError}</p>
		</div>
	{/if}
	<div bind:this={editorElement} class="editor-wrapper" class:readonly class:hidden={!!initError}></div>
</div>

<style>
	.editor-container {
		min-height: 150px;
		width: 100%;
		max-width: 100%;
		overflow: hidden;
	}

	.editor-error {
		background: var(--cds-notification-error-background, #fff1f1);
		border: 1px solid var(--cds-support-error, #da1e28);
		border-radius: 4px;
		padding: 1rem;
		color: var(--cds-support-error, #da1e28);
	}

	.editor-wrapper.hidden {
		display: none;
	}

	.editor-wrapper {
		background: var(--cds-field);
		border: 1px solid var(--cds-border-subtle);
		border-radius: 4px;
		padding: 1rem;
		min-height: 150px;
		width: 100%;
		max-width: 100%;
		box-sizing: border-box;
	}

	.editor-wrapper.readonly {
		border: none;
		padding: 0;
		background: transparent;
	}

	/* EditorJS dark theme overrides */
	:global(.codex-editor) {
		color: var(--cds-text-primary);
	}

	:global(.ce-block__content),
	:global(.ce-toolbar__content) {
		max-width: 100%;
	}

	:global(.ce-paragraph) {
		line-height: 1.6;
	}

	:global(.cdx-block) {
		padding: 0.3em 0;
	}

	:global(.ce-toolbar__plus),
	:global(.ce-toolbar__settings-btn) {
		color: var(--cds-text-secondary);
		background: var(--cds-layer);
	}

	:global(.ce-toolbar__plus:hover),
	:global(.ce-toolbar__settings-btn:hover) {
		background: var(--cds-layer-hover);
	}

	:global(.ce-inline-toolbar) {
		background: var(--cds-layer);
		border: 1px solid var(--cds-border-subtle);
	}

	:global(.ce-inline-tool) {
		color: var(--cds-text-primary);
	}

	:global(.ce-inline-tool:hover) {
		background: var(--cds-layer-hover);
	}

	:global(.ce-popover) {
		background: var(--cds-layer);
		border: 1px solid var(--cds-border-subtle);
	}

	:global(.ce-popover__item) {
		color: var(--cds-text-primary);
	}

	:global(.ce-popover__item:hover) {
		background: var(--cds-layer-hover);
	}

	:global(.ce-popover__item-icon) {
		background: var(--cds-field);
	}

	:global(.cdx-marker) {
		background: rgba(245, 235, 111, 0.3);
		padding: 0.1em 0.2em;
	}

	:global(.cdx-quote) {
		border-left: 3px solid var(--cds-border-strong);
		padding-left: 1rem;
		color: var(--cds-text-secondary);
	}

	:global(.cdx-quote__caption) {
		font-size: 0.875rem;
		color: var(--cds-text-helper);
	}

	:global(.ce-code__textarea) {
		background: var(--cds-layer);
		color: var(--cds-text-primary);
		border: 1px solid var(--cds-border-subtle);
		font-family: 'IBM Plex Mono', monospace;
	}
</style>
