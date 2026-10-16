<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import InfoTip from '$lib/components/InfoTip.svelte';
	import type { WeightLog, WeightTrend } from '$lib/types';
	import { tips } from '$lib/stores/tips.svelte';
	import { undoable } from '$lib/stores/undo';
	import { t, fmtDate, fmtNumber, i18n } from '$lib/i18n/index.svelte';
	// "68,0" en español y portugués; con toFixed salía "68.0" en todos.
	const kg1 = (n: number) => fmtNumber(n, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

	if (!auth.isLoggedIn) goto('/login');

	let weights: WeightLog[] = $state([]);
	let saving = $state(false);
	let showAdd = $state(false);

	// Quick-add modal value
	let newWeightValue = $state(0);

	// Range selector
	let range = $state<'7d' | '1m' | '3m' | '1a'>('1m');

	// Tendencia (media móvil del servidor): un punto por día con pesaje.
	let trend = $state<WeightTrend | null>(null);

	async function load() {
		weights = await api.get<WeightLog[]>('/weight');
		trend = await api.get<WeightTrend>('/weight/trend?days=400').catch(() => null);
		// Con unos cuantos pesajes ya hay tendencia que mirar: se explica una vez.
		if (weights.length >= 3) tips.request('weight_trend');
	}

	let trendByDay = $derived(new Map((trend?.points ?? []).map(p => [p.day, p.trend])));

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

	// Borrar = deslizar la fila a la izquierda. Sale de la lista al momento y el
	// toast ofrece "Deshacer" unos segundos antes de borrarlo de verdad.
	function deleteWeight(w: WeightLog) {
		swipeId = null;
		swipeX = 0;
		weights = weights.filter(x => x.id !== w.id);
		undoable(
			t('weight.deleted', { kg: kg1(w.weight) }),
			async () => { await api.del(`/weight/${w.id}`); load(); },
			() => {
				weights = [...weights, w].sort((a, b) => b.logged_at.localeCompare(a.logged_at));
			},
		);
	}

	// ── Deslizar para borrar ──
	// Arrastre corto: deja a la vista el botón "Borrar". Largo: borra al soltar.
	const REVEAL = 88;
	let swipeId = $state<number | null>(null);
	let swipeX = $state(0);
	let dragging = $state(false);
	let drag: { id: number; x0: number; y0: number; base: number; width: number; locked: boolean } | null = null;

	function onRowDown(e: PointerEvent, id: number) {
		const base = swipeId === id ? swipeX : 0;
		if (swipeId !== id) { swipeId = null; swipeX = 0; }
		drag = { id, x0: e.clientX, y0: e.clientY, base, width: (e.currentTarget as HTMLElement).offsetWidth, locked: false };
	}
	function onRowMove(e: PointerEvent) {
		if (!drag) return;
		const dx = e.clientX - drag.x0, dy = e.clientY - drag.y0;
		if (!drag.locked) {
			if (Math.abs(dy) > 8 && Math.abs(dy) > Math.abs(dx)) { drag = null; return; }  // es scroll
			if (Math.abs(dx) < 8) return;
			drag.locked = true;
			dragging = true;
			swipeId = drag.id;
			(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
		}
		swipeX = Math.min(0, drag.base + dx);
	}
	function onRowUp() {
		if (!drag) return;
		const d = drag;
		drag = null;
		if (!d.locked) {
			// Un toque en una fila abierta la cierra.
			if (swipeId === d.id && swipeX !== 0) { swipeId = null; swipeX = 0; }
			return;
		}
		dragging = false;
		const w = weights.find(x => x.id === d.id);
		if (w && swipeX < -d.width * 0.5) deleteWeight(w);
		else if (swipeX < -REVEAL / 2) swipeX = -REVEAL;
		else { swipeId = null; swipeX = 0; }
	}

	function fmt(iso: string) {
		return fmtDate(new Date(iso), { day: 'numeric', month: 'short', year: '2-digit' });
	}
	function fmtShort(iso: string) {
		return fmtDate(new Date(iso), { day: 'numeric', month: 'short' });
	}

	// Derived chart data — oldest → newest
	let allChronological = $derived([...weights].reverse());

	let chartData = $derived.by(() => {
		const days = range === '7d' ? 7 : range === '1m' ? 30 : range === '3m' ? 90 : 365;
		const cutoff = Date.now() - days * 86_400_000;
		return allChronological.filter(w => new Date(w.logged_at).getTime() >= cutoff);
	});

	// La tendencia de cada pesaje del gráfico (por su día UTC, como el servidor).
	let chartTrend = $derived(chartData.map(w => trendByDay.get(w.logged_at.slice(0, 10)) ?? null));

	let chartValues = $derived([...chartData.map(w => w.weight), ...chartTrend.filter((v): v is number => v !== null)]);
	let chartMin = $derived(chartValues.length ? Math.min(...chartValues) - 0.5 : 0);
	let chartMax = $derived(chartValues.length ? Math.max(...chartValues) + 0.5 : 100);

	// Stats
	let current = $derived(weights.length ? weights[0].weight : null);
	// Cambio desde el inicio del historial (primera pesada registrada).
	let change = $derived(
		weights.length >= 2
			? weights[0].weight - weights[weights.length - 1].weight
			: null
	);
	// Cambio desde la medición anterior — el dato del día a día, no el acumulado.
	let sinceLast = $derived(
		weights.length >= 2
			? weights[0].weight - weights[1].weight
			: null
	);
	let records = $derived(weights.length);

	// Gráfico: cada pesaje es un punto suelto y la tendencia es la línea. El eje X
	// es temporal (no por índice), así los huecos sin pesajes se ven como huecos.
	const W = 320;
	const H = 150;
	const PAD_L = 28;   // hueco para las etiquetas de kg
	const PAD_R = 8;
	const PAD_T = 10;
	const PAD_B = 20;

	let tStart = $derived(chartData.length ? new Date(chartData[0].logged_at).getTime() : 0);
	let tEnd = $derived(chartData.length ? new Date(chartData[chartData.length - 1].logged_at).getTime() : 1);

	function cx(iso: string): number {
		const span = tEnd - tStart;
		if (span <= 0) return PAD_L + (W - PAD_L - PAD_R) / 2;
		return PAD_L + ((new Date(iso).getTime() - tStart) / span) * (W - PAD_L - PAD_R);
	}
	function cy(w: number): number {
		const ratio = (w - chartMin) / (chartMax - chartMin || 1);
		return PAD_T + (1 - ratio) * (H - PAD_T - PAD_B);
	}

	// Marcas del eje Y en números redondos (0,5 / 1 / 2 kg según el rango).
	let yTicks = $derived.by(() => {
		const span = chartMax - chartMin;
		const step = span <= 3 ? 0.5 : span <= 6 ? 1 : 2;
		const out: number[] = [];
		for (let v = Math.ceil(chartMin / step) * step; v <= chartMax; v += step) out.push(+v.toFixed(1));
		return out;
	});
	const kgTick = (n: number) => fmtNumber(n, { maximumFractionDigits: 1 });

	let trendPts = $derived(
		chartData
			.map((w, i) => (chartTrend[i] === null ? null : { x: cx(w.logged_at), y: cy(chartTrend[i]!) }))
			.filter((p): p is { x: number; y: number } => p !== null)
	);
	let trendPath = $derived(trendPts.length >= 2 ? `M ${trendPts.map(p => `${p.x},${p.y}`).join(' L ')}` : '');

	// Ritmo de la tendencia: por debajo de 0,05 kg/semana es "estable".
	let rate = $derived(trend?.weekly_rate ?? null);
	let rateText = $derived(
		rate === null ? null
			: Math.abs(rate) < 0.05 ? t('weight.trendStable')
			: t('weight.trendRate', { rate: `${rate > 0 ? '+' : '−'}${Math.abs(rate).toLocaleString(i18n.locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` })
	);

	let areaPath = $derived(
		trendPts.length >= 2
			? `${trendPath} L ${trendPts[trendPts.length - 1].x},${H - PAD_B} L ${trendPts[0].x},${H - PAD_B} Z`
			: ''
	);
</script>

<!-- Page header -->
<div class="trk-header">
	<button class="trk-back" aria-label={t('screenHeader.back')} onclick={() => goto('/settings')}><Icon name="back" /></button>
	<div style="flex:1; min-width:0;">
		<h1 class="trk-title">{t('weight.title')}</h1>
		<div class="trk-sub">{t('weight.subtitle')}</div>
	</div>
	<button class="btn-reg" onclick={() => { newWeightValue = current ?? 75; showAdd = true; }}>
		{t('weight.add')}
	</button>
</div>

<!-- Hero card -->
{#if current !== null}
<div class="glass-card hero-card">
	<div style="display:flex; align-items:baseline; gap:0.5rem; margin-bottom:0.25rem;">
		<div class="eyebrow">{t('common.today')}</div>
		<div style="flex:1;"></div>
		<div class="unit-label">kg</div>
	</div>

	<div style="display:flex; align-items:flex-end; gap:0.875rem; margin-bottom:{sinceLast !== null ? '0.375rem' : '1.125rem'};">
		<div class="big-weight">{kg1(current)}</div>
		{#if sinceLast !== null}
			<div style="padding-bottom:0.75rem;">
				<div class="delta-badge" class:delta-down={sinceLast < 0} class:delta-up={sinceLast > 0}>
					{sinceLast < 0 ? '↓' : '↑'} {kg1(Math.abs(sinceLast))} kg
				</div>
			</div>
		{/if}
	</div>
	{#if sinceLast !== null}
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.4); margin-bottom:0.75rem;">
			{t('weight.sinceLast', { date: fmtShort(weights[1].logged_at) })}
		</div>
	{/if}

	<div class="hero-stats-row">
		<div class="mini-stat">
			<div class="mini-stat-label">{t('weight.records')}</div>
			<div class="mini-stat-val">{records}<span class="mini-stat-unit">{t('weight.total')}</span></div>
		</div>
		{#if change !== null}
			<div class="mini-stat">
				<div class="mini-stat-label">{t('weight.totalChange')}</div>
				<div class="mini-stat-val" style="color:{change < 0 ? 'oklch(85% 0.17 160)' : 'oklch(75% 0.18 30)'};">
					{change < 0 ? '' : '+'}{kg1(change)}<span class="mini-stat-unit">kg</span>
				</div>
			</div>
		{/if}
		{#if trend?.latest_trend != null && weights.length >= 3}
			<div class="mini-stat">
				<div class="mini-stat-label">{t('weight.trend')}<InfoTip id="weight_trend" /></div>
				<div class="mini-stat-val">{kg1(trend.latest_trend)}<span class="mini-stat-unit">kg</span></div>
				{#if rateText}<div class="mini-stat-sub">{rateText}</div>{/if}
			</div>
		{:else if weights.length > 0}
			<div class="mini-stat">
				<div class="mini-stat-label">{t('weight.start')}</div>
				<div class="mini-stat-val">{kg1(weights[weights.length - 1].weight)}<span class="mini-stat-unit">kg</span></div>
			</div>
		{/if}
	</div>
</div>
{:else}
<!-- Estado vacío: antes la pantalla quedaba completamente en blanco -->
<div class="glass-card" style="text-align:center; padding:2.5rem 1.25rem;">
	<div style="font-size:2rem; margin-bottom:0.625rem; color:var(--text-faint);"><Icon name="weight" strokeWidth={1.5} /></div>
	<div style="font-size:0.9375rem; font-weight:700; color:#fff;">{t('weight.empty')}</div>
	<div style="font-size:0.75rem; color:rgba(255,255,255,0.5); margin-top:0.375rem; line-height:1.5;">
		Registra tu peso de hoy con el botón <strong>{t('weight.add')}</strong> y aquí verás tu evolución con gráfica.
	</div>
</div>
{/if}

<!-- Chart card -->
{#if weights.length >= 2}
<div class="glass-card" style="margin-top:0.75rem;">
	<div style="display:flex; align-items:center; margin-bottom:0.875rem;">
		<div class="section-title">{t('weight.evolution')}</div>
		<div style="flex:1;"></div>
		<!-- Range selector -->
		<div class="range-selector">
			{#each (['7d', '1m', '3m', '1a'] as const) as r}
				<button onclick={() => range = r} class="range-btn" class:range-btn-active={range === r}>{r}</button>
			{/each}
		</div>
	</div>

	{#if chartData.length < 2}
		<div style="text-align:center; padding:1.5rem 0.5rem; color:rgba(255,255,255,0.4); font-size:0.8125rem;">
			{t('weight.empty')}
		</div>
	{:else}
	<svg viewBox="0 0 {W} {H}" style="width:100%; height:{H}px; overflow:visible; display:block;">
		<defs>
			<linearGradient id="wgt-grad" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0%" stop-color="oklch(82% 0.18 160)" stop-opacity="0.35"/>
				<stop offset="100%" stop-color="oklch(82% 0.18 160)" stop-opacity="0"/>
			</linearGradient>
		</defs>

		<!-- Rejilla con su valor en kg -->
		{#each yTicks as v}
			<line
				x1={PAD_L} x2={W - PAD_R} y1={cy(v)} y2={cy(v)}
				stroke="rgba(255,255,255,0.06)" stroke-dasharray="2 4"
			/>
			<text x={PAD_L - 6} y={cy(v) + 3} text-anchor="end" fill="rgba(255,255,255,0.35)" font-size="9" font-family="Geist, sans-serif">{kgTick(v)}</text>
		{/each}

		<!-- Área bajo la tendencia -->
		{#if areaPath}
			<path d={areaPath} fill="url(#wgt-grad)"/>
		{/if}

		<!-- Pesajes: puntos sueltos -->
		{#each chartData as w (w.id)}
			<circle cx={cx(w.logged_at)} cy={cy(w.weight)} r="2.75" fill="#06070a" stroke="oklch(82% 0.18 160 / 0.7)" stroke-width="1.5"/>
		{/each}

		<!-- Tendencia: la línea protagonista -->
		{#if trendPath}
			<path d={trendPath} fill="none" stroke="oklch(82% 0.18 160)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
		{/if}

		<!-- Último punto de la tendencia -->
		{#if trendPts.length >= 1}
			{@const last = trendPts[trendPts.length - 1]}
			<circle cx={last.x} cy={last.y} r="8" fill="oklch(82% 0.18 160)" opacity="0.25"/>
			<circle cx={last.x} cy={last.y} r="4" fill="oklch(82% 0.18 160)" stroke="#06070a" stroke-width="2"/>
		{/if}

		<!-- Fechas del primer y último pesaje -->
		{#if chartData.length >= 2}
			<text x={PAD_L} y={H - 4} text-anchor="start" fill="rgba(255,255,255,0.35)" font-size="9" font-family="Geist, sans-serif">
				{fmtShort(chartData[0].logged_at)}
			</text>
			<text x={W - PAD_R} y={H - 4} text-anchor="end" fill="rgba(255,255,255,0.35)" font-size="9" font-family="Geist, sans-serif">
				{fmtShort(chartData[chartData.length - 1].logged_at)}
			</text>
		{/if}
	</svg>
	{#if trendPath}
		<div class="trend-legend">{t('weight.trendLegend')}</div>
	{/if}
	{/if}
</div>
{/if}

<!-- Recent entries -->
{#if weights.length > 0}
<div class="section-eyebrow" style="margin:1.25rem 0.25rem 0.625rem;">{t('weight.recent')}</div>
<div class="glass-card entry-list" role="list">
	{#each weights.slice(0, 8) as w, i (w.id)}
		{@const prev = weights[i + 1]}
		{@const diff = prev ? Math.round((w.weight - prev.weight) * 10) / 10 : null}
		<div class="entry-swipe" class:entry-swipe-open={swipeId === w.id} style="border-bottom:{i < Math.min(weights.length, 8) - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none'};">
			<!-- Detrás de la fila: el botón que deja ver el deslizamiento -->
			<button
				class="entry-del"
				onclick={() => deleteWeight(w)}
				onfocus={() => { swipeId = w.id; swipeX = -REVEAL; }}
				aria-label={t('weight.deleteAria', { kg: kg1(w.weight) })}
			><Icon name="delete" />{t('common.delete')}</button>
			<div
				class="entry-row"
				class:entry-row-anim={!dragging || swipeId !== w.id}
				style="transform:translateX({swipeId === w.id ? swipeX : 0}px);"
				onpointerdown={(e) => onRowDown(e, w.id)}
				onpointermove={onRowMove}
				onpointerup={onRowUp}
				onpointercancel={onRowUp}
				role="listitem"
			>
				<div style="flex:1;">
					<div class="entry-val">{kg1(w.weight)} kg</div>
					<div class="entry-date">{fmt(w.logged_at)}</div>
				</div>
				{#if diff !== null}
					<div class="entry-diff" class:delta-down={diff < 0} class:delta-up={diff > 0}>
						{diff > 0 ? '+' : diff < 0 ? '−' : '±'}{kg1(Math.abs(diff))}
					</div>
				{/if}
			</div>
		</div>
	{/each}
</div>
<div class="swipe-hint">{t('weight.swipeHint')}</div>
{/if}

<!-- Quick-add bottom sheet modal -->
{#if showAdd}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div class="modal-backdrop" onclick={() => (showAdd = false)}>
		<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
		<div class="modal-sheet" onclick={(e) => e.stopPropagation()}>
			<div class="modal-handle"></div>
			<div class="modal-title">{t('weight.logTitle')}</div>
			<div class="modal-sub">{t('weight.logSub')}</div>

			<div class="modal-stepper">
				<button class="stepper-btn" onclick={() => (newWeightValue = Math.max(0, +(newWeightValue - 0.1).toFixed(1)))}>−</button>
				<div style="text-align:center;">
					<div class="big-weight">{kg1(newWeightValue)}</div>
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
				{saving ? t('weight.saving') : t('common.save')}
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
		font-family: var(--uro-font-serif);
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
		font-family: var(--uro-font-serif);
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
	.mini-stat-sub {
		font-size: 0.625rem;
		color: rgba(255,255,255,0.5);
		margin-top: 0.125rem;
	}
	.trend-legend {
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.4);
		margin-top: 0.5rem;
		line-height: 1.4;
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
	.entry-swipe {
		position: relative;
		overflow: hidden;
	}
	.entry-del {
		position: absolute;
		inset: 0 0 0 auto;
		width: 88px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.125rem;
		border: none;
		background: oklch(58% 0.2 25);
		color: #fff;
		font: inherit;
		font-size: 0.625rem;
		font-weight: 700;
		cursor: pointer;
		opacity: 0;
	}
	/* El botón solo existe a la vista mientras se desliza (o tiene el foco). */
	.entry-swipe-open { border-radius: 14px; }
	.entry-swipe-open .entry-del { opacity: 1; }
	.entry-row {
		position: relative;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 0.875rem;
		touch-action: pan-y;
		user-select: none;
		cursor: grab;
	}
	/* Opaca al deslizar para tapar el botón de detrás. */
	.entry-swipe-open .entry-row { background: #16181d; }
	.entry-row-anim { transition: transform 0.2s ease; }
	.entry-val { font-size: 0.8125rem; font-weight: 600; }
	.entry-date { font-size: 0.625rem; color: rgba(255,255,255,0.4); margin-top: 0.125rem; }
	.entry-diff {
		font-size: 0.75rem;
		font-weight: 600;
		color: rgba(255,255,255,0.45);
		font-variant-numeric: tabular-nums;
	}
	.entry-diff.delta-down { color: oklch(85% 0.17 160); background: none; }
	.entry-diff.delta-up { color: oklch(75% 0.18 30); background: none; }
	.swipe-hint {
		font-size: 0.625rem;
		color: rgba(255,255,255,0.35);
		text-align: center;
		margin: 0.625rem 0 calc(96px + env(safe-area-inset-bottom));
	}

	/* ── Modal ── */
	.modal-backdrop {
		position: fixed;
		inset: 0;
		z-index: 200;
		display: flex;
		align-items: flex-end;
		background: rgba(0,0,0,0.5);
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
		font-family: var(--uro-font-serif);
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
	/* En móvil se llega desde Ajustes y no había forma de volver salvo la barra. */
	.trk-back {
		width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
		background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.1);
		color: #fff; font: inherit; font-size: 1rem; cursor: pointer;
		display: flex; align-items: center; justify-content: center;
	}
</style>
