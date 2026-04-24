<!--
  StatPill.svelte
  Mini-tarjeta de dato (valor + label) para grids de métricas (peso, medidas, perfil).

  Uso:
    <StatPill value="76.2" unit="kg" label="Peso" trend={-0.4} />
-->
<script lang="ts">
	interface Props {
		value: string | number;
		unit?: string;
		label: string;
		trend?: number;           // positivo = subió
		trendBetterIsDown?: boolean; // peso ↓ = mejor
		accent?: string;          // color personalizado
	}
	let {
		value,
		unit = '',
		label,
		trend,
		trendBetterIsDown = false,
		accent,
	}: Props = $props();

	let trendColor = $derived(() => {
		if (trend === undefined || trend === 0) return 'var(--text-muted)';
		const up = trend > 0;
		const good = trendBetterIsDown ? !up : up;
		return good ? 'var(--primary)' : 'var(--danger)';
	});
</script>

<div class="stat-pill" style={accent ? `--accent:${accent};` : ''}>
	<div class="value-row">
		<span class="value">{value}</span>
		{#if unit}<span class="unit">{unit}</span>{/if}
	</div>
	<div class="label">{label}</div>
	{#if trend !== undefined && trend !== 0}
		<div class="trend" style="color:{trendColor()};">
			{trend > 0 ? '▲' : '▼'} {Math.abs(trend).toFixed(1)}
		</div>
	{/if}
</div>

<style>
	.stat-pill {
		position: relative;
		background: var(--surface);
		border: 1px solid var(--border);
		backdrop-filter: var(--blur-s);
		-webkit-backdrop-filter: var(--blur-s);
		border-radius: var(--r-md);
		padding: 0.8rem 0.9rem;
		min-width: 0;
	}
	.value-row {
		display: flex;
		align-items: baseline;
		gap: 0.25rem;
	}
	.value {
		font-size: 1.4rem;
		font-weight: 800;
		letter-spacing: -0.02em;
		color: var(--accent, var(--text));
		line-height: 1;
		font-variant-numeric: tabular-nums;
	}
	.unit {
		font-size: 0.75rem;
		color: var(--text-muted);
		font-weight: 600;
	}
	.label {
		font-size: 0.65rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		font-weight: 700;
		margin-top: 0.3rem;
	}
	.trend {
		position: absolute;
		top: 0.75rem;
		right: 0.75rem;
		font-size: 0.7rem;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}
</style>
