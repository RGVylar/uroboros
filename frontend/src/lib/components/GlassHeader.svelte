<!--
  GlassHeader.svelte
  Cabecera superior con título grande, subtítulo y slot derecho para acciones/navegación.
  Reemplaza el patrón "<h1> + flechas <div>" que ahora tienen muchas rutas.

  Uso:
    <GlassHeader title="Diario" subtitle="Hoy · 🔥 3 días">
      {#snippet left()}<button class="btn-ghost" onclick={...}>◀</button>{/snippet}
      {#snippet right()}<button class="btn-ghost" onclick={...}>▶</button>{/snippet}
    </GlassHeader>
-->
<script lang="ts">
	interface Props {
		title: string;
		subtitle?: string;
		serif?: boolean;
		left?: import('svelte').Snippet;
		right?: import('svelte').Snippet;
	}
	let { title, subtitle = '', serif = false, left, right }: Props = $props();
</script>

<header class="uro-header">
	{#if left}
		<div class="side">{@render left()}</div>
	{/if}

	<div class="titles">
		<h1 class:serif>{title}</h1>
		{#if subtitle}
			<div class="sub">{subtitle}</div>
		{/if}
	</div>

	{#if right}
		<div class="side right">{@render right()}</div>
	{/if}
</header>

<style>
	.uro-header {
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		gap: 0.5rem;
		padding: 0.25rem 0 1rem;
	}
	.titles { text-align: center; }
	h1 {
		margin: 0;
		font-size: 1.35rem;
		font-weight: 800;
		letter-spacing: -0.02em;
		line-height: 1.1;
	}
	h1.serif {
		font-family: 'Fraunces', 'Georgia', serif;
		font-weight: 600;
		font-size: 1.55rem;
	}
	.sub {
		margin-top: 0.2rem;
		font-size: 0.72rem;
		color: var(--text-muted);
		letter-spacing: 0.02em;
	}
	.side {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 2.25rem;
	}
	.side.right { justify-content: flex-end; }
</style>
