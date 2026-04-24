<!--
  CalorieRing.svelte — hero calórico horizontal.
  Ring izquierda (muestra net) + columna de stats derecha.
  Macrobars van aparte debajo, en la página del diario.
-->
<script lang="ts">
	interface Props {
		consumed: number;
		goal: number;
		burned?: number;
		net?: number;
		size?: number;
	}
	let { consumed, goal, burned = 0, net = consumed - burned, size = 150 }: Props = $props();

	const stroke = 11;
	const r = $derived((size - stroke) / 2);
	const c = $derived(2 * Math.PI * r);

	let pct     = $derived(goal > 0 ? Math.min(net / goal, 1.15) : 0);
	let dash    = $derived(c * Math.max(0, pct));
	let remaining = $derived(goal - net);
	let isOver  = $derived(net > goal);
</script>

<div class="hero-row">
	<!-- Anillo -->
	<div class="ring-wrap" style="--size:{size}px;">
		<svg viewBox="0 0 {size} {size}" width={size} height={size} aria-hidden="true">
			<defs>
				<linearGradient id="uro-ring-grad" x1="0" y1="0" x2="1" y2="1">
					<stop offset="0%"   stop-color="oklch(85% 0.19 155)" />
					<stop offset="100%" stop-color="oklch(72% 0.18 200)" />
				</linearGradient>
				<linearGradient id="uro-ring-grad-over" x1="0" y1="0" x2="1" y2="1">
					<stop offset="0%"   stop-color="oklch(75% 0.2 40)" />
					<stop offset="100%" stop-color="oklch(70% 0.22 25)" />
				</linearGradient>
			</defs>

			<!-- Track -->
			<circle cx={size/2} cy={size/2} r={r}
				fill="none" stroke="rgba(255,255,255,0.08)" stroke-width={stroke} />

			<!-- Progress -->
			<circle cx={size/2} cy={size/2} r={r}
				fill="none"
				stroke={isOver ? 'url(#uro-ring-grad-over)' : 'url(#uro-ring-grad)'}
				stroke-width={stroke}
				stroke-linecap="round"
				stroke-dasharray="{dash} {c}"
				transform="rotate(-90 {size/2} {size/2})"
				style="filter: drop-shadow(0 0 8px var(--primary-glow)); transition: stroke-dashoffset 0.6s cubic-bezier(0.22,1,0.36,1);"
			/>
		</svg>

		<!-- Centro del ring -->
		<div class="ring-center">
			<div class="ring-label">kcal</div>
			<div class="ring-value" class:over={isOver}>{Math.round(net)}</div>
			<div class="ring-sub">de {goal}</div>
		</div>
	</div>

	<!-- Columna de stats -->
	<div class="stats-col">
		<div class="hero-stat">
			<div class="stat-label">{remaining >= 0 ? 'Restantes' : 'Exceso'}</div>
			<div class="stat-val" style="color:{remaining >= 0 ? 'var(--primary)' : 'var(--danger)'}">
				{Math.round(Math.abs(remaining))}<span class="stat-unit">kcal</span>
			</div>
		</div>
		<div class="hero-stat">
			<div class="stat-label">Consumidas</div>
			<div class="stat-val" style="color:var(--cal)">
				{Math.round(consumed)}<span class="stat-unit">kcal</span>
			</div>
		</div>
		{#if burned > 0}
			<div class="hero-stat">
				<div class="stat-label">Quemadas</div>
				<div class="stat-val" style="color:var(--danger)">
					-{Math.round(burned)}<span class="stat-unit">kcal</span>
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.hero-row {
		display: flex;
		align-items: center;
		gap: 1.15rem;
	}

	/* Ring */
	.ring-wrap {
		position: relative;
		width: var(--size);
		height: var(--size);
		flex-shrink: 0;
	}
	.ring-wrap svg { display: block; }
	.ring-center {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		pointer-events: none;
	}
	.ring-label {
		font-size: 0.55rem;
		letter-spacing: 0.15em;
		text-transform: uppercase;
		color: rgba(255,255,255,0.45);
		font-weight: 700;
	}
	.ring-value {
		font-size: 2.1rem;
		font-weight: 800;
		line-height: 1;
		color: #fff;
		letter-spacing: -0.04em;
		font-variant-numeric: tabular-nums;
	}
	.ring-value.over { color: var(--danger); }
	.ring-sub {
		font-size: 0.62rem;
		color: rgba(255,255,255,0.5);
		margin-top: 0.1rem;
		font-variant-numeric: tabular-nums;
	}

	/* Stats */
	.stats-col {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.7rem;
	}
	.hero-stat { display: flex; flex-direction: column; }
	.stat-label {
		font-size: 0.58rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: rgba(255,255,255,0.45);
		font-weight: 600;
	}
	.stat-val {
		font-size: 1.35rem;
		font-weight: 800;
		letter-spacing: -0.03em;
		font-variant-numeric: tabular-nums;
		display: inline-flex;
		align-items: baseline;
		gap: 0.2rem;
	}
	.stat-unit {
		font-size: 0.62rem;
		color: rgba(255,255,255,0.4);
		font-weight: 500;
	}
</style>
