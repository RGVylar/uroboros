<!--
  GlassCard.svelte — tarjeta de cristal con backdrop-filter
  Props:
    - tint: neutral | green | blue | orange | violet
    - radius: number (px)
    - padding: number (px)
    - accent: color string (línea brillante arriba), opcional
    - onclick: handler opcional
-->
<script lang="ts">
	type Tint = 'neutral' | 'green' | 'blue' | 'orange' | 'violet';
	let {
		tint = 'neutral',
		radius = 24,
		padding = 16,
		accent = '',
		onclick,
		children,
	}: {
		tint?: Tint;
		radius?: number;
		padding?: number;
		accent?: string;
		onclick?: (e: MouseEvent) => void;
		children?: any;
	} = $props();

	const TINTS: Record<Tint, string> = {
		neutral: 'rgba(255,255,255,0.07)',
		green: 'linear-gradient(135deg, oklch(78% 0.16 165 / 0.18), rgba(255,255,255,0.05))',
		blue: 'linear-gradient(135deg, oklch(65% 0.18 235 / 0.18), rgba(255,255,255,0.05))',
		orange: 'linear-gradient(135deg, oklch(72% 0.18 45 / 0.18), rgba(255,255,255,0.05))',
		violet: 'linear-gradient(135deg, oklch(65% 0.2 295 / 0.18), rgba(255,255,255,0.05))',
	};
</script>

{#if onclick}
	<button
		class="glass"
		style:background={TINTS[tint]}
		style:border-radius="{radius}px"
		style:padding="{padding}px"
		style:cursor="pointer"
		{onclick}
	>
		{#if accent}<div class="accent" style:background="linear-gradient(90deg, transparent, {accent}, transparent)"></div>{/if}
		{@render children?.()}
	</button>
{:else}
	<div
		class="glass"
		style:background={TINTS[tint]}
		style:border-radius="{radius}px"
		style:padding="{padding}px"
	>
		{#if accent}<div class="accent" style:background="linear-gradient(90deg, transparent, {accent}, transparent)"></div>{/if}
		{@render children?.()}
	</div>
{/if}

<style>
	.glass {
		position: relative;
		backdrop-filter: blur(24px) saturate(180%);
		-webkit-backdrop-filter: blur(24px) saturate(180%);
		border: 1px solid rgba(255, 255, 255, 0.12);
		box-shadow:
			inset 0 1px 0 rgba(255, 255, 255, 0.14),
			inset 0 -1px 0 rgba(0, 0, 0, 0.15),
			0 10px 40px -10px rgba(0, 0, 0, 0.5);
		color: #f2f3f7;
		text-align: left;
		font: inherit;
		width: 100%;
	}
	button.glass {
		display: block;
	}
	.accent {
		position: absolute;
		top: 0;
		left: 10%;
		right: 10%;
		height: 1px;
		opacity: 0.6;
		border-radius: inherit;
	}
</style>
