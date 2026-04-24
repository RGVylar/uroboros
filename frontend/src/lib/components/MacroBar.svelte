<!--
  MacroBar.svelte
  Barra de macro con label + valores + track glow.
  Reemplaza los tríos inline de div/span que hay en diario, history, etc.

  Uso:
    <MacroBar label="Prot" value={summary.totals.protein} goal={goals.protein} color="var(--prot)" />
-->
<script lang="ts">
	interface Props {
		label: string;
		value: number;
		goal: number;
		color: string;
		unit?: string;
		compact?: boolean;
	}
	let { label, value, goal, color, unit = 'g', compact = false }: Props = $props();

	let pct = $derived(goal > 0 ? Math.min((value / goal) * 100, 100) : 0);
	let over = $derived(goal > 0 && value > goal);
</script>

<div class="macro" class:compact>
	<div class="top">
		<span class="lbl" style="color:{color};">{label}</span>
		<span class="val">
			<strong>{Math.round(value)}</strong><span class="sep">/</span><span class="goal">{goal}{unit}</span>
		</span>
	</div>
	<div class="track">
		<div
			class="fill"
			style="width:{pct}%; background:linear-gradient(90deg, color-mix(in oklch, {color} 60%, black), {color}); box-shadow: 0 0 10px color-mix(in oklch, {color} 60%, transparent);"
			class:over
		></div>
	</div>
</div>

<style>
	.macro { width: 100%; }
	.top {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		margin-bottom: 0.3rem;
	}
	.lbl {
		font-size: 0.68rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		font-weight: 800;
	}
	.val {
		font-size: 0.72rem;
		color: var(--text-muted);
		font-variant-numeric: tabular-nums;
	}
	.val strong { color: var(--text); font-weight: 700; }
	.val .sep { margin: 0 0.15rem; opacity: 0.5; }
	.track {
		height: 6px;
		background: rgba(255, 255, 255, 0.05);
		border-radius: 99px;
		overflow: hidden;
	}
	.fill {
		height: 100%;
		border-radius: 99px;
		transition: width 0.5s cubic-bezier(0.22, 1, 0.36, 1);
	}
	.fill.over { filter: saturate(1.3); }

	.compact .top { margin-bottom: 0.2rem; }
	.compact .lbl { font-size: 0.6rem; }
	.compact .val { font-size: 0.66rem; }
	.compact .track { height: 4px; }
</style>
