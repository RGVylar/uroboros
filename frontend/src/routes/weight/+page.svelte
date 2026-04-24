<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { WeightLog } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	let weights: WeightLog[] = $state([]);
	let saving = $state(false);
	let showAdd = $state(false);

	// Quick-add modal value
	let newWeightValue = $state(0);

	// Range selector
	let range = $state<'7d' | '1m' | '3m' | '1a'>('1m');

	async function load() {
		weights = await api.get<WeightLog[]>('/weight');
	}

	$effect(() => { load(); });

	async function addWeight() {
		if (!newWeightValue) return;
		saving = true;
		await api.post('/weight', { weight: newWeightValue, logged_at: new Date().toISOString() });
		newWeightValue = 0;
		saving = false;
		showAdd = false;
		load();
	}

	async function deleteWeight(id: number) {
		await api.del(`/weight/${id}`);
		load();
	}

	function fmt(iso: string) {
		return new Date(iso).toLocaleDateString('es', { day: 'numeric', month: 'short', year: '2-digit' });
	}
	function fmtShort(iso: string) {
		return new Date(iso).toLocaleDateString('es', { day: 'numeric', month: 'short' });
	}

	// Derived chart data — oldest → newest
	let allChronological = $derived([...weights].reverse());

	let chartData = $derived.by(() => {
		const n = range === '7d' ? 7 : range === '1m' ? 30 : range === '3m' ? 90 : 365;
		return allChronological.slice(-n);
	});

	let chartMin = $derived(chartData.length ? Math.min(...chartData.map(w => w.weight)) - 0.5 : 0);
	let chartMax = $derived(chartData.length ? Math.max(...chartData.map(w => w.weight)) + 0.5 : 100);

	// Stats
	let current = $derived(weights.length ? weights[0].weight : null);
	let change = $derived(
		weights.length >= 2
			? weights[0].weight - weights[weights.length - 1].weight
			: null
	);
	let records = $derived(weights.length);

	// SVG line chart helpers
	const W = 320;
	const H = 150;
	const PAD = 20;

	function cx(i: number, n: number): number {
		if (n <= 1) return PAD + (W - PAD * 2) / 2;
		return PAD + (i / (n - 1)) * (W - PAD * 2);
	}
	function cy(w: number): number {
		const ratio = (w - chartMin) / (chartMax - chartMin || 1);
		return PAD + (1 - ratio) * (H - PAD * 2);
	}

	// Smooth quadratic path
	let smoothPath = $derived.by(() => {
		if (chartData.length < 2) return '';
		const pts = chartData.map((w, i) => ({ x: cx(i, chartData.length), y: cy(w.weight) }));
		let d = `M ${pts[0].x},${pts[0].y}`;
		for (let i = 1; i < pts.length; i++) {
			const p0 = pts[i - 1], p1 = pts[i];
			const mx = (p0.x + p1.x) / 2;
			d += ` Q ${mx},${p0.y} ${mx},${(p0.y + p1.y) / 2} T ${p1.x},${p1.y}`;
		}
		return d;
	});

	let areaPath = $derived(
		chartData.length >= 2
			? `${smoothPath} L ${cx(chartData.length - 1, chartData.length)},${H - PAD} L ${cx(0, chartData.length)},${H - PAD} Z`
			: ''
	);
</script>

<!-- Page header -->
<div class="trk-header">
	<div style="flex:1; min-width:0;">
		<h1 class="trk-title">Peso</h1>
		<div class="trk-sub">Seguimiento mensual</div>
	</div>
	<button class="btn-reg" onclick={() => { newWeightValue = current ?? 75; showAdd = true; }}>
		+ Registrar
	</button>
</div>

<!-- Hero card -->
{#if current !== null}
<div class="glass-card hero-card">
	<div style="display:flex; align-items:baseline; gap:0.5rem; margin-bottom:0.25rem;">
		<div class="eyebrow">Hoy</div>
		<div style="flex:1;"></div>
		<div class="unit-label">kg</div>
	</div>

	<div style="display:flex; align-items:flex-end; gap:0.875rem; margin-bottom:1.125rem;">
		<div class="big-weight">{current.toFixed(1)}</div>
		{#if change !== null}
			<div style="padding-bottom:0.75rem;">
				<div class="delta-badge" class:delta-down={change < 0} class:delta-up={change > 0}>
					{change < 0 ? '↓' : '↑'} {Math.abs(change).toFixed(1)} kg
				</div>
			</div>
		{/if}
	</div>

	<div class="hero-stats-row">
		<div class="mini-stat">
			<div class="mini-stat-label">Registros</div>
			<div class="mini-stat-val">{records}<span class="mini-stat-unit">total</span></div>
		</div>
		{#if change !== null}
			<div class="mini-stat">
				<div class="mini-stat-label">Cambio total</div>
				<div class="mini-stat-val" style="color:{change < 0 ? 'oklch(85% 0.17 160)' : 'oklch(75% 0.18 30)'};">
					{change < 0 ? '' : '+'}{change.toFixed(1)}<span class="mini-stat-unit">kg</span>
				</div>
			</div>
		{/if}
		{#if weights.length > 0}
			<div class="mini-stat">
				<div class="mini-stat-label">Inicio</div>
				<div class="mini-stat-val">{weights[weights.length - 1].weight.toFixed(1)}<span class="mini-stat-unit">kg</span></div>
			</div>
		{/if}
	</div>
</div>
{/if}

<!-- Chart card -->
{#if chartData.length >= 2}
<div class="glass-card" style="margin-top:0.75rem;">
	<div style="display:flex; align-items:center; margin-bottom:0.875rem;">
		<div class="section-title">Evolución</div>
		<div style="flex:1;"></div>
		<!-- Range selector -->
		<div class="range-selector">
			{#each (['7d', '1m', '3m', '1a'] as const) as r}
				<button onclick={() => range = r} class="range-btn" class:range-btn-active={range === r}>{r}</button>
			{/each}
		</div>
	</div>

	<svg viewBox="0 0 {W} {H}" style="width:100%; height:{H}px; overflow:visible; display:block;">
		<defs>
			<linearGradient id="wgt-grad" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0%" stop-color="oklch(82% 0.18 160)" stop-opacity="0.35"/>
				<stop offset="100%" stop-color="oklch(82% 0.18 160)" stop-opacity="0"/>
			</linearGradient>
		</defs>

		<!-- Grid lines -->
		{#each [0.25, 0.5, 0.75] as t}
			<line
				x1={PAD} x2={W - PAD}
				y1={PAD + t * (H - PAD * 2)} y2={PAD + t * (H - PAD * 2)}
				stroke="rgba(255,255,255,0.05)" stroke-dasharray="2 4"
			/>
		{/each}

		<!-- Area fill -->
		{#if areaPath}
			<path d={areaPath} fill="url(#wgt-grad)"/>
		{/if}

		<!-- Line -->
		{#if smoothPath}
			<path d={smoothPath} fill="none" stroke="oklch(82% 0.18 160)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
		{/if}

		<!-- Last point highlight -->
		{#if chartData.length >= 1}
			{@const lx = cx(chartData.length - 1, chartData.length)}
			{@const ly = cy(chartData[chartData.length - 1].weight)}
			<circle cx={lx} cy={ly} r="8" fill="oklch(82% 0.18 160)" opacity="0.25"/>
			<circle cx={lx} cy={ly} r="4" fill="oklch(82% 0.18 160)" stroke="#06070a" stroke-width="2"/>
		{/if}

		<!-- Date labels for first and last -->
		{#if chartData.length >= 2}
			<text x={PAD} y={H - 4} text-anchor="start" fill="rgba(255,255,255,0.35)" font-size="9" font-family="Geist, sans-serif">
				{fmtShort(chartData[0].logged_at)}
			</text>
			<text x={W - PAD} y={H - 4} text-anchor="end" fill="rgba(255,255,255,0.35)" font-size="9" font-family="Geist, sans-serif">
				{fmtShort(chartData[chartData.length - 1].logged_at)}
			</text>
		{/if}
	</svg>
</div>
{/if}

<!-- Recent entries -->
{#if weights.length > 0}
<div class="section-eyebrow" style="margin:1.25rem 0.25rem 0.625rem;">Registros recientes</div>
<div class="glass-card entry-list">
	{#each weights.slice(0, 8) as w, i (w.id)}
		<div class="entry-row" style="border-bottom:{i < Math.min(weights.length, 8) - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none'};">
			<div class="entry-icon">⚖</div>
			<div style="flex:1;">
				<div class="entry-val">{w.weight.toFixed(1)} kg</div>
				<div class="entry-date">{fmt(w.logged_at)}</div>
			</div>
			<button class="del-btn" onclick={() => deleteWeight(w.id)} aria-label="Eliminar">✕</button>
		</div>
	{/each}
</div>
{/if}

<!-- Quick-add bottom sheet modal -->
{#if showAdd}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div class="modal-backdrop" onclick={() => (showAdd = false)}>
		<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
		<div class="modal-sheet" onclick={(e) => e.stopPropagation()}>
			<div class="modal-handle"></div>
			<div class="modal-title">Registrar peso</div>
			<div class="modal-sub">Introduce el valor actual</div>

			<div class="modal-stepper">
				<button class="stepper-btn" onclick={() => (newWeightValue = Math.max(0, +(newWeightValue - 0.1).toFixed(1)))}>−</button>
				<div style="text-align:center;">
					<div class="big-weight">{newWeightValue.toFixed(1)}</div>
					<div style="font-size:0.75rem; color:rgba(255,255,255,0.4); margin-top:0.25rem;">kg</div>
				</div>
				<button class="stepper-btn" onclick={() => (newWeightValue = +(newWeightValue + 0.1).toFixed(1))}>+</button>
			</div>

			<!-- Direct number input -->
			<div style="margin-bottom:1.25rem; display:flex; justify-content:center;">
				<input
					type="number"
					bind:value={newWeightValue}
					step="0.1"
					min="0"
					style="width:120px; text-align:center; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:12px; color:#fff; padding:0.5rem; font-size:1rem; font-family:inherit; outline:none;"
				/>
			</div>

			<button class="btn-submit" onclick={addWeight} disabled={saving}>
				{saving ? 'Guardando...' : 'Guardar'}
			</button>
		</div>
	</div>
{/if}

<style>
	/* ── Header ── */
	.trk-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.25rem 0 0.875rem;
	}
	.trk-title {
		font-size: 1.875rem;
		font-weight: 400;
		letter-spacing: -0.05em;
		color: #fff;
		line-height: 1;
		margin: 0;
		font-family: 'Lora', 'Georgia', serif;
	}
	.trk-sub {
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.5);
		margin-top: 0.25rem;
		letter-spacing: 0.02em;
	}
	.btn-reg {
		padding: 0.5rem 0.875rem;
		border-radius: 99px;
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		font-weight: 700;
		font-size: 0.75rem;
		border: none;
		cursor: pointer;
		box-shadow: inset 0 1px 0 rgba(255,255,255,0.4), 0 6px 20px oklch(75% 0.2 160 / 0.3);
		white-space: nowrap;
		font-family: inherit;
	}

	/* ── Glass card ── */
	.glass-card {
		background: rgba(255,255,255,0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 24px;
		padding: 1.25rem;
	}
	.hero-card {
		border-color: oklch(82% 0.18 160 / 0.2);
	}

	/* ── Hero ── */
	.eyebrow {
		font-size: 0.6875rem;
		letter-spacing: 0.15em;
		color: rgba(255,255,255,0.45);
		text-transform: uppercase;
		font-weight: 700;
	}
	.unit-label {
		font-size: 0.625rem;
		color: rgba(255,255,255,0.45);
	}
	.big-weight {
		font-size: 4rem;
		font-weight: 400;
		line-height: 0.95;
		letter-spacing: -0.05em;
		color: #fff;
		font-family: 'Lora', 'Georgia', serif;
	}
	.delta-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.1875rem 0.5625rem;
		border-radius: 99px;
		font-size: 0.6875rem;
		font-weight: 700;
	}
	.delta-down {
		background: oklch(75% 0.18 160 / 0.22);
		color: oklch(85% 0.17 160);
	}
	.delta-up {
		background: oklch(65% 0.2 30 / 0.22);
		color: oklch(75% 0.18 30);
	}

	/* ── Hero stats row ── */
	.hero-stats-row {
		display: flex;
		gap: 1rem;
		padding-top: 1rem;
		border-top: 1px solid rgba(255,255,255,0.08);
	}
	.mini-stat { flex: 1; }
	.mini-stat-label {
		font-size: 0.5625rem;
		letter-spacing: 0.1em;
		color: rgba(255,255,255,0.4);
		text-transform: uppercase;
		font-weight: 700;
	}
	.mini-stat-val {
		display: flex;
		align-items: baseline;
		gap: 0.1875rem;
		margin-top: 0.25rem;
		font-size: 1.125rem;
		font-weight: 700;
		color: #fff;
		letter-spacing: -0.03em;
		font-variant-numeric: tabular-nums;
	}
	.mini-stat-unit {
		font-size: 0.625rem;
		color: rgba(255,255,255,0.4);
		font-weight: 500;
	}

	/* ── Chart section ── */
	.section-title { font-size: 0.75rem; color: rgba(255,255,255,0.7); font-weight: 600; }
	.range-selector {
		display: inline-flex;
		gap: 0.125rem;
		padding: 0.1875rem;
		border-radius: 99px;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.06);
	}
	.range-btn {
		padding: 0.25rem 0.625rem;
		border-radius: 99px;
		border: none;
		cursor: pointer;
		background: transparent;
		color: rgba(255,255,255,0.5);
		font-size: 0.625rem;
		font-weight: 700;
		font-family: inherit;
		transition: background 0.15s, color 0.15s;
	}
	.range-btn-active {
		background: rgba(255,255,255,0.12);
		color: #fff;
	}

	/* ── Recent entries ── */
	.section-eyebrow {
		font-size: 0.6875rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: rgba(255,255,255,0.45);
		font-weight: 700;
	}
	.entry-list { padding: 0.375rem; }
	.entry-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 0.875rem;
	}
	.entry-icon {
		width: 34px;
		height: 34px;
		border-radius: 10px;
		background: oklch(75% 0.18 160 / 0.12);
		border: 1px solid oklch(75% 0.18 160 / 0.2);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.75rem;
		font-weight: 700;
		color: oklch(85% 0.17 160);
		flex-shrink: 0;
	}
	.entry-val { font-size: 0.8125rem; font-weight: 600; }
	.entry-date { font-size: 0.625rem; color: rgba(255,255,255,0.4); margin-top: 0.125rem; }
	.del-btn {
		background: none;
		border: none;
		color: rgba(255,255,255,0.3);
		cursor: pointer;
		font-size: 0.75rem;
		padding: 0.25rem;
		transition: color 0.15s;
		font-family: inherit;
	}
	.del-btn:hover { color: oklch(75% 0.2 25); }

	/* ── Modal ── */
	.modal-backdrop {
		position: fixed;
		inset: 0;
		z-index: 200;
		display: flex;
		align-items: flex-end;
		background: rgba(0,0,0,0.5);
		backdrop-filter: blur(8px);
		-webkit-backdrop-filter: blur(8px);
	}
	.modal-sheet {
		width: 100%;
		padding: 1.5rem 1.25rem 2.5rem;
		background: rgba(18,20,26,0.92);
		backdrop-filter: blur(40px) saturate(180%);
		-webkit-backdrop-filter: blur(40px) saturate(180%);
		border-top-left-radius: 28px;
		border-top-right-radius: 28px;
		border: 1px solid rgba(255,255,255,0.1);
		border-bottom: none;
	}
	.modal-handle {
		width: 40px;
		height: 4px;
		border-radius: 99px;
		background: rgba(255,255,255,0.2);
		margin: 0 auto 1.125rem;
	}
	.modal-title {
		font-size: 1.625rem;
		color: #fff;
		letter-spacing: -0.05em;
		margin-bottom: 0.375rem;
		font-family: 'Lora', 'Georgia', serif;
		font-weight: 400;
	}
	.modal-sub {
		font-size: 0.75rem;
		color: rgba(255,255,255,0.5);
		margin-bottom: 1.25rem;
	}
	.modal-stepper {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 1.125rem;
		margin-bottom: 0.875rem;
	}
	.stepper-btn {
		width: 52px;
		height: 52px;
		border-radius: 50%;
		background: rgba(255,255,255,0.08);
		border: 1px solid rgba(255,255,255,0.12);
		color: #fff;
		font-size: 1.375rem;
		cursor: pointer;
		font-family: inherit;
		transition: background 0.15s;
	}
	.stepper-btn:hover { background: rgba(255,255,255,0.14); }

	/* ── Submit ── */
	.btn-submit {
		width: 100%;
		height: 52px;
		border-radius: 16px;
		border: none;
		cursor: pointer;
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		font-weight: 800;
		font-size: 0.9375rem;
		font-family: inherit;
		box-shadow:
			0 10px 30px -8px oklch(75% 0.22 165 / 0.55),
			inset 0 -2px 6px oklch(60% 0.2 170),
			inset 0 1px 0 rgba(255,255,255,0.4);
	}
	.btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
