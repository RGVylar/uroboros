<!--
  MealHeader.svelte — cabecera de comida con dot coloreado por tipo.
  Props: label, kcal, protein, hasEntries, hue, actions (snippet)
-->
<script lang="ts">
	interface Props {
		label: string;
		kcal: number;
		protein?: number;
		hasEntries?: boolean;
		hue?: number;          // oklch hue del tipo de comida (45=breakfast, 165=lunch, 285=dinner, 220=snack)
		actions?: import('svelte').Snippet;
	}
	let { label, kcal, protein, hasEntries = true, hue = 160, actions }: Props = $props();
</script>

<div class="meal-header">
	<div class="left">
		<!-- Dot coloreado con glow -->
		<div class="dot" style="
			background: oklch(78% 0.16 {hue});
			box-shadow: 0 0 8px oklch(78% 0.16 {hue});
		"></div>

		<span class="label">{label}</span>

		{#if actions && hasEntries}
			<div class="actions">{@render actions()}</div>
		{/if}
	</div>

	<div class="totals">
		<span class="kcal">
			<strong style="color:oklch(85% 0.15 55);">{Math.round(kcal)}</strong>
			<span class="muted"> kcal</span>
		</span>
		{#if protein !== undefined}
			<span class="prot" style="color:oklch(78% 0.14 220);">· P{Math.round(protein)}</span>
		{/if}
	</div>
</div>

<style>
	.meal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.5rem;
		padding: 0 0.25rem 0.5rem;
	}
	.left {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		min-width: 0;
		flex: 1;
	}
	.dot {
		width: 6px;
		height: 6px;
		border-radius: 99px;
		flex-shrink: 0;
	}
	.label {
		font-weight: 700;
		font-size: 0.88rem;
		letter-spacing: -0.01em;
	}
	.actions { display: inline-flex; gap: 0.3rem; }
	.totals {
		display: inline-flex;
		align-items: baseline;
		gap: 0.25rem;
		font-variant-numeric: tabular-nums;
		font-size: 0.78rem;
		white-space: nowrap;
	}
	.muted { color: rgba(255,255,255,0.5); }
	.prot { font-weight: 700; font-size: 0.72rem; }
</style>
