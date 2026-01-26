<script lang="ts">
	import 'carbon-components-svelte/css/all.css';
	import { Content } from 'carbon-components-svelte';

	let { children } = $props();
</script>

<svelte:head>
	<title>CTrack</title>
</svelte:head>

<Content>
	{@render children()}
</Content>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
	}
</style>
