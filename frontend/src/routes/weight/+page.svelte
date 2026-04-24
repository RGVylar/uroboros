<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { WeightLog } from '$lib/types';
	import { GlassHeader, StatPill, EmptyState } from '$lib/components';

	if (!auth.isLoggedIn) goto('/login');

	let weights: WeightLog[] = $state([]);
	let newWeight = $state(0);
	let saving = $state(false);

	async function load() {
		weights = await api.get<WeightLog[]>('/weight');
	}

	$effect(() => { load(); });

	async function addWeight() {
		if (!newWeight) return;
		saving = true;
		await api.post('/weight', { weight: newWeight, logged_at: new Date().toISOString() });
		newWeight = 0;
		saving = false;
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

	// SVG chart helpers
	const CHART_W = 300;
	const CHART_H = 90;
	const PAD = { top: 10, bottom: 22, left: 4, right: 4 };
	const PLOT_W = CHART_W - PAD.left - PAD.right;
	const PLOT_H = CHART_H - PAD.top - PAD.bottom;

	// Chart data: oldest → newest (reverse the array which is newest-first)
	let chartData = $derived([...weights].reverse().slice(-30));

	let chartMin = $derived(chartData.length ? Math.min(...chartData.map(w => w.weight)) - 1 : 0);
	let chartMax = $derived(chartData.length ? Math.max(...chartData.map(w => w.weight)) + 1 : 100);

	function cx(i: number, n: number): number {
		if (n <= 1) return PAD.left + PLOT_W / 2;
		return PAD.left + (i / (n - 1)) * PLOT_W;
	}

	function cy(weight: number): number {
		const ratio = (weight - chartMin) / (chartMax - chartMin || 1);
		return PAD.top + PLOT_H - ratio * PLOT_H;
	}

	let polylinePoints = $derived(
		chartData.map((w, i) => `${cx(i, chartData.length)},${cy(w.weight)}`).join(' ')
	);

	let change = $derived(
		weights.length >= 2
			? weights[0].weight - weights[weights.length - 1].weight
			: null
	);
</script>

<GlassHeader title="Peso" subtitle="Últimos 30 días" />

<!-- Add form -->
<div class="card" style="margin-bottom:1rem;">
	<div style="display:flex; gap:0.5rem; align-items:end;">
		<div class="form-group" style="flex:1; margin:0;">
			<label for="w">Peso (kg)</label>
			<input id="w" type="number" bind:value={newWeight} step="0.1" min="0" />
		</div>
		<button onclick={addWeight} disabled={saving}>Añadir</button>
	</div>
</div>

<!-- Chart -->
{#if chartData.length >= 2}
	<div class="card" style="margin-bottom:1rem;">
		<!-- Stats row -->
		<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:0.5rem; margin-bottom:0.75rem;">
			<StatPill value={weights[0].weight.toFixed(1)} unit="kg" label="Actual" trend={change ?? undefined} trendBetterIsDown />
			<StatPill value={change !== null ? (change > 0 ? '+' : '') + change.toFixed(1) : '—'} unit={change !== null ? 'kg' : ''} label="Cambio" />
			<StatPill value={weights.length} label="Registros" />
		</div>

		<!-- SVG line chart -->
		<svg
			viewBox="0 0 {CHART_W} {CHART_H}"
			style="width:100%; height:90px; overflow:visible; display:block;"
			preserveAspectRatio="none"
		>
			<!-- Grid lines -->
			{#each [0.25, 0.5, 0.75] as frac}
				{@const y = PAD.top + frac * PLOT_H}
				<line x1={PAD.left} y1={y} x2={CHART_W - PAD.right} y2={y}
					stroke="rgba(255,255,255,0.06)" stroke-width="0.5" />
			{/each}

			<!-- Area fill under line -->
			{#if chartData.length >= 2}
				<polygon
					points="{PAD.left},{CHART_H - PAD.bottom} {polylinePoints} {CHART_W - PAD.right},{CHART_H - PAD.bottom}"
					fill="url(#weightGrad)"
					opacity="0.25"
				/>
				<defs>
					<linearGradient id="weightGrad" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stop-color="var(--primary)" stop-opacity="0.6" />
						<stop offset="100%" stop-color="var(--primary)" stop-opacity="0" />
					</linearGradient>
				</defs>

				<!-- Line -->
				<polyline
					points={polylinePoints}
					fill="none"
					stroke="var(--primary)"
					stroke-width="1.5"
					stroke-linejoin="round"
					stroke-linecap="round"
				/>
			{/if}

			<!-- Dots + labels for endpoints and every nth point -->
			{#each chartData as w, i}
				{@const x = cx(i, chartData.length)}
				{@const y = cy(w.weight)}
				{@const isFirst = i === 0}
				{@const isLast = i === chartData.length - 1}
				{@const n = chartData.length}
				{@const showDot = isFirst || isLast || (n <= 10) || (n > 10 && i % Math.ceil(n / 8) === 0)}

				{#if showDot}
					<circle cx={x} cy={y} r={isLast ? 3.5 : 2}
						fill={isLast ? 'var(--primary)' : 'var(--bg)'}
						stroke="var(--primary)" stroke-width="1.5" />
				{/if}

				<!-- Date labels: first, last, and ~every 7th -->
				{#if isFirst || isLast || (n > 7 && i % Math.ceil(n / 5) === 0)}
					<text x={x} y={CHART_H - 4}
						text-anchor={isFirst ? 'start' : isLast ? 'end' : 'middle'}
						font-size="7" fill="var(--text-muted)">
						{fmtShort(w.logged_at)}
					</text>
				{/if}
			{/each}
		</svg>
	</div>
{/if}

<!-- Weight list -->
{#each weights as w (w.id)}
	<div class="card" style="margin-bottom:0.5rem; display:flex; justify-content:space-between; align-items:center;">
		<div>
			<span style="font-weight:700; font-size:1.1rem;">{w.weight} kg</span>
			<span style="color:var(--text-muted); font-size:0.8rem; margin-left:0.5rem;">{fmt(w.logged_at)}</span>
		</div>
		<button class="btn-danger" style="padding:0.3rem 0.5rem; font-size:0.75rem;" onclick={() => deleteWeight(w.id)}>✕</button>
	</div>
{/each}
