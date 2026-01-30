<script lang="ts">
	import { fly, fade } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import { page } from '$app/state';

	interface Props {
		children: import('svelte').Snippet;
	}

	let { children }: Props = $props();

	const pathname = $derived(page.url.pathname);
</script>

{#key pathname}
	<div
		class="page-transition"
		in:fly={{ y: 8, duration: 150, easing: cubicOut, delay: 50 }}
		out:fade={{ duration: 100 }}
	>
		{@render children()}
	</div>
{/key}

<style>
	.page-transition {
		min-height: 100%;
		will-change: transform, opacity;
	}
</style>
