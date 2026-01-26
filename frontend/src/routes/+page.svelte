<script lang="ts">
	import { Button, Tile } from 'carbon-components-svelte';
	import Dashboard from 'carbon-icons-svelte/lib/Dashboard.svelte';
</script>

<svelte:head>
	<title>CTrack - Главная</title>
</svelte:head>

<div class="welcome">
	<Tile>
		<h1>
			<Dashboard size={32} />
			CTrack
		</h1>
		<p>Система управления задачами</p>
		<Button>Начать работу</Button>
	</Tile>
</div>

<style>
	.welcome {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 80vh;
	}

	h1 {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	p {
		margin: 1rem 0;
		color: var(--cds-text-secondary);
	}
</style>
