<script lang="ts">
	import { Theme } from 'carbon-components-svelte';

	let { children } = $props();
</script>

<Theme theme="g90" />

<div class="auth-layout">
	<div class="auth-container">
		<div class="auth-header">
			<h1>CTrack</h1>
			<p>Система управления задачами</p>
		</div>
		<div class="auth-content">
			{@render children()}
		</div>
	</div>
</div>

<style>
	.auth-layout {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--cds-background);
		padding: 1rem;
	}

	.auth-container {
		width: 100%;
		max-width: 400px;
	}

	.auth-header {
		text-align: center;
		margin-bottom: 2rem;
	}

	.auth-header h1 {
		font-size: 2rem;
		font-weight: 600;
		color: var(--cds-text-primary);
		margin: 0 0 0.5rem;
	}

	.auth-header p {
		color: var(--cds-text-secondary);
		margin: 0;
	}

	.auth-content {
		background: var(--cds-layer-01);
		padding: 2rem;
		border-radius: 4px;
	}
</style>
