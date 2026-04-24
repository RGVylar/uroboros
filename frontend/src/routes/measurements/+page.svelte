<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { MEASUREMENT_COLORS, MEASUREMENT_FIELDS } from '$lib/measurements';
	import { auth } from '$lib/stores/auth.svelte';
	import type { BodyMeasurementLog } from '$lib/types';
	import { GlassHeader, EmptyState } from '$lib/components';

	if (!auth.isLoggedIn) goto('/login');

	let logs: BodyMeasurementLog[] = $state([]);
	let saving = $state(false);

	/** Form: only positive numbers are sent */
	let form: Record<string, number> = $state(
		Object.fromEntries(MEASUREMENT_FIELDS.map((f) => [f.key, 0]))
	);

	async function load() {
		logs = await api.get<BodyMeasurementLog[]>('/measurements');
	}

	$effect(() => {
		load();
	});

	async function addEntry() {
		const measurements: Record<string, number> = {};
		for (const f of MEASUREMENT_FIELDS) {
			const v = form[f.key];
			if (typeof v === 'number' && v > 0) measurements[f.key] = v;
		}
		if (Object.keys(measurements).length === 0) return;
		saving = true;
		await api.post('/measurements', {
			measurements,
			logged_at: new Date().toISOString()
		});
		for (const f of MEASUREMENT_FIELDS) form[f.key] = 0;
		saving = false;
		load();
	}

	async function deleteLog(id: number) {
		await api.del(`/measurements/${id}`);
		load();
	}

	function fmt(iso: string) {
		return new Date(iso).toLocaleDateString('es', {
			day: 'numeric',
			month: 'short',
			year: '2-digit'
		});
	}

	function fmtShort(iso: string) {
		return new Date(iso).toLocaleDateString('es', { day: 'numeric', month: 'short' });
	}

	function labelForKey(key: string) {
		return MEASUREMENT_FIELDS.find((f) => f.key === key)?.label ?? key;
	}

	const CHART_W = 300;
	const CHART_H = 120;
	const PAD = { top: 10, bottom: 24, left: 4, right: 4 };
	const PLOT_W = CHART_W - PAD.left - PAD.right;
	const PLOT_H = CHART_H - PAD.top - PAD.bottom;

	let chartData = $derived([...logs].reverse().slice(-30));

	let keysInChart = $derived.by(() => {
		const s = new Set<string>();
		for (const row of chartData) {
			for (const k of Object.keys(row.measurements)) {
				const v = row.measurements[k];
				if (typeof v === 'number' && !Number.isNaN(v)) s.add(k);
			}
		}
		return MEASUREMENT_FIELDS.map((f) => f.key).filter((k) => s.has(k));
	});

	let rangeByKey = $derived.by(() => {
		const out: Record<string, { min: number; max: number }> = {};
		for (const key of keysInChart) {
			const vals: number[] = [];
			for (const row of chartData) {
				const v = row.measurements[key];
				if (typeof v === 'number' && !Number.isNaN(v)) vals.push(v);
			}
			if (vals.length === 0) continue;
			const mn = Math.min(...vals);
			const mx = Math.max(...vals);
			const pad = mx === mn ? 1 : (mx - mn) * 0.08;
			out[key] = { min: mn - pad, max: mx + pad };
		}
		return out;
	});

	function cx(i: number, n: number): number {
		if (n <= 1) return PAD.left + PLOT_W / 2;
		return PAD.left + (i / (n - 1)) * PLOT_W;
	}

	function cy(val: number, key: string): number {
		const r = rangeByKey[key];
		if (!r) return PAD.top + PLOT_H;
		const ratio = (val - r.min) / (r.max - r.min || 1);
		return PAD.top + PLOT_H - ratio * PLOT_H;
	}

	function polylineSegmentsForKey(key: string): string[] {
		const n = chartData.length;
		if (n === 0) return [];
		const segments: string[] = [];
		let run: string[] = [];
		for (let i = 0; i < n; i++) {
			const v = chartData[i].measurements[key];
			const has = typeof v === 'number' && !Number.isNaN(v);
			if (has) {
				run.push(`${cx(i, n)},${cy(v, key)}`);
			} else if (run.length > 0) {
				if (run.length >= 2) segments.push(run.join(' '));
				run = [];
			}
		}
		if (run.length >= 2) segments.push(run.join(' '));
		return segments;
	}

	let showChart = $derived.by(() => chartData.length >= 2 && keysInChart.length > 0);
</script>

<GlassHeader title="Medidas" subtitle="Centímetros · rellena las zonas que quieras" />

<div class="card" style="margin-bottom:1rem;">
	<div
		style="display:grid; grid-template-columns:1fr 1fr; gap:0.65rem 0.75rem;"
	>
		{#each MEASUREMENT_FIELDS as f}
			<div class="form-group" style="margin:0;">
				<label for={f.key}>{f.label}</label>
				<input
					id={f.key}
					type="number"
					bind:value={form[f.key]}
					step="0.1"
					min="0"
					placeholder="—"
				/>
			</div>
		{/each}
	</div>
	<button style="margin-top:0.85rem; width:100%;" onclick={addEntry} disabled={saving}>
		Guardar medidas
	</button>
</div>

{#if showChart}
	<div class="card" style="margin-bottom:1rem;">
		<div
			style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.04em; margin-bottom:0.5rem;"
		>
			Evolución (últimos {Math.min(30, chartData.length)} registros)
		</div>
		<svg
			viewBox="0 0 {CHART_W} {CHART_H}"
			style="width:100%; height:120px; overflow:visible; display:block;"
			preserveAspectRatio="none"
		>
			{#each [0.25, 0.5, 0.75] as frac}
				{@const y = PAD.top + frac * PLOT_H}
				<line
					x1={PAD.left}
					y1={y}
					x2={CHART_W - PAD.right}
					y2={y}
					stroke="rgba(255,255,255,0.06)"
					stroke-width="0.5"
				/>
			{/each}

			{#each keysInChart as key}
				{@const color = MEASUREMENT_COLORS[key] ?? '#94a3b8'}
				{#each polylineSegmentsForKey(key) as pts}
					<polyline
						points={pts}
						fill="none"
						stroke={color}
						stroke-width="1.25"
						stroke-linejoin="round"
						stroke-linecap="round"
						opacity="0.95"
					/>
				{/each}
				<!-- último punto por serie -->
				{#if chartData.length}
					{@const lastI = chartData.length - 1}
					{@const v = chartData[lastI].measurements[key]}
					{#if typeof v === 'number' && !Number.isNaN(v)}
						<circle
							cx={cx(lastI, chartData.length)}
							cy={cy(v, key)}
							r="3"
							fill={color}
							stroke="var(--bg)"
							stroke-width="1"
						/>
					{/if}
				{/if}
			{/each}

			{#if chartData.length > 1}
				{@const n = chartData.length}
				<text
					x={PAD.left}
					y={CHART_H - 4}
					text-anchor="start"
					font-size="7"
					fill="var(--text-muted)">{fmtShort(chartData[0].logged_at)}</text>
				<text
					x={CHART_W - PAD.right}
					y={CHART_H - 4}
					text-anchor="end"
					font-size="7"
					fill="var(--text-muted)">{fmtShort(chartData[n - 1].logged_at)}</text>
			{/if}
		</svg>

		<div
			style="display:flex; flex-wrap:wrap; gap:0.45rem 0.75rem; margin-top:0.65rem;"
		>
			{#each keysInChart as key}
				<span
					style="display:inline-flex; align-items:center; gap:0.35rem; font-size:0.7rem; color:var(--text-muted);"
				>
					<span
						style="width:8px; height:8px; border-radius:2px; background:{MEASUREMENT_COLORS[
							key
						] ?? '#94a3b8'};"
					></span>
					{labelForKey(key)}
				</span>
			{/each}
		</div>
	</div>
{/if}

{#each logs as row (row.id)}
	<div
		class="card"
		style="margin-bottom:0.5rem; display:flex; flex-direction:column; gap:0.5rem;"
	>
		<div
			style="display:flex; justify-content:space-between; align-items:flex-start;"
		>
			<span style="color:var(--text-muted); font-size:0.8rem;">{fmt(row.logged_at)}</span>
			<button
				class="btn-danger"
				style="padding:0.3rem 0.5rem; font-size:0.75rem;"
				onclick={() => deleteLog(row.id)}>✕</button>
		</div>
		<div
			style="display:flex; flex-wrap:wrap; gap:0.35rem 0.65rem; font-size:0.85rem;"
		>
			{#each Object.entries(row.measurements) as [k, v]}
				<span>
					<span style="color:var(--text-muted);">{labelForKey(k)}:</span>
					<strong style="color:{MEASUREMENT_COLORS[k] ?? 'var(--text)'};">
						{typeof v === 'number' ? v.toFixed(1) : v}
					</strong>
					<span style="color:var(--text-muted);"> cm</span>
				</span>
			{/each}
		</div>
	</div>
{/each}
