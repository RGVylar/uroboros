<!--
  CalorieRing.svelte
  Anillo circular SVG para el hero calórico del diario.
  Reemplaza la "progress-bar + 3 columnas" actual.

  Uso:
    <CalorieRing
      consumed={summary.totals.calories}
      goal={goals.kcal}
      burned={summary.calories_burned}
      net={summary.net_calories}
    />
-->
<script lang="ts">
	interface Props {
		consumed: number;
		goal: number;
		burned?: number;
		net?: number;
		size?: number;
	}
	let { consumed, goal, burned = 0, net = consumed - burned, size = 220 }: Props = $props();

	const stroke = 14;
	const r = $derived((size - stroke) / 2);
	const c = $derived(2 * Math.PI * r);

	let pct = $derived(goal > 0 ? Math.min(net / goal, 1.15) : 0);
	let dash = $derived(c * pct);
	let remaining = $derived(Math.max(goal - net, 0));
	let isOver = $derived(net > goal);
</script>

<div class="ring-wrap" style="--size:{size}px;">
	<svg viewBox="0 0 {size} {size}" width={size} height={size} aria-hidden="true">
		<defs>
			<linearGradient id="uro-ring-grad" x1="0" y1="0" x2="1" y2="1">
				<stop offset="0%" stop-color="oklch(60% 0.2 195)" />
				<stop offset="100%" stop-color="oklch(88% 0.19 160)" />
			</linearGradient>
			<linearGradient id="uro-ring-grad-over" x1="0" y1="0" x2="1" y2="1">
				<stop offset="0%" stop-color="oklch(75% 0.2 40)" />
				<stop offset="100%" stop-color="oklch(70% 0.22 25)" />
			</linearGradient>
		</defs>

		<!-- Track -->
		<circle
			cx={size/2} cy={size/2} r={r}
			fill="none"
			class="ring-track"
			stroke-width={stroke}
		/>

		<!-- Progress -->
		<circle
			cx={size/2} cy={size/2} r={r}
			fill="none"
			stroke={isOver ? 'url(#uro-ring-grad-over)' : 'url(#uro-ring-grad)'}
			stroke-width={stroke}
			stroke-linecap="round"
			stroke-dasharray="{dash} {c}"
			transform="rotate(-90 {size/2} {size/2})"
			style="filter: drop-shadow(0 0 10px var(--primary-glow));"
		/>
	</svg>

	<div class="ring-center">
		<div class="ring-label">{isOver ? 'Exceso' : 'Restantes'}</div>
		<div class="ring-value" class:over={isOver}>
			{Math.round(Math.abs(goal - net))}
		</div>
		<div class="ring-unit">kcal</div>

		<div class="ring-breakdown">
			<span><strong style="color:var(--cal);">{Math.round(consumed)}</strong> in</span>
			{#if burned > 0}
				<span class="dot">·</span>
				<span><strong style="color:var(--danger);">{Math.round(burned)}</strong> out</span>
			{/if}
			<span class="dot">·</span>
			<span>{goal} meta</span>
		</div>
	</div>
</div>

<style>
	.ring-wrap {
		position: relative;
		width: var(--size);
		height: var(--size);
		margin: 0 auto;
		display: grid;
		place-items: center;
	}
	.ring-wrap svg {
		display: block;
	}
	.ring-center {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		padding: 0 1rem;
	}
	.ring-label {
		font-size: 0.62rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-muted);
		font-weight: 700;
	}
	.ring-value {
		font-size: 2.8rem;
		font-weight: 800;
		line-height: 1;
		margin-top: 0.25rem;
		color: var(--text);
		letter-spacing: -0.03em;
		font-variant-numeric: tabular-nums;
	}
	.ring-value.over { color: var(--danger); }
	.ring-unit {
		font-size: 0.75rem;
		color: var(--text-muted);
		margin-top: 0.15rem;
		font-weight: 600;
	}
	.ring-breakdown {
		margin-top: 0.55rem;
		font-size: 0.7rem;
		color: var(--text-muted);
		display: inline-flex;
		gap: 0.3rem;
		align-items: center;
		font-variant-numeric: tabular-nums;
	}
	.ring-breakdown .dot { opacity: 0.4; }
</style>
