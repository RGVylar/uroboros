<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { MEASUREMENT_FIELDS } from '$lib/measurements';
	import { auth } from '$lib/stores/auth.svelte';
	import type { BodyMeasurementLog } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	let logs: BodyMeasurementLog[] = $state([]);
	let saving = $state(false);
	let showAdd = $state(false);

	// Hue per measurement key for oklch colors
	const HUES: Record<string, number> = {
		neck:    190,
		chest:   220,
		waist:   160,
		hips:    340,
		bicep_l: 45,
		bicep_r: 45,
		thigh_l: 295,
		thigh_r: 295,
		calf_l:  25,
		calf_r:  25,
	};

	const bodyPoints = [
		{ key: 'neck',    label: 'Cuello',  x: 50, y: 22 },
		{ key: 'chest',   label: 'Pecho',   x: 50, y: 38 },
		{ key: 'bicep_l', label: 'Brazo',   x: 22, y: 42 },
		{ key: 'waist',   label: 'Cintura', x: 50, y: 55 },
		{ key: 'hips',    label: 'Cadera',  x: 50, y: 66 },
		{ key: 'thigh_l', label: 'Muslo',   x: 42, y: 78 },
		{ key: 'calf_l',  label: 'Gemelo',  x: 42, y: 95 },
	];

	/** Form: only positive numbers are sent */
	let form: Record<string, number> = $state(
		Object.fromEntries(MEASUREMENT_FIELDS.map((f) => [f.key, 0]))
	);

	async function load() {
		logs = await api.get<BodyMeasurementLog[]>('/measurements');
	}

	$effect(() => { load(); });

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
		showAdd = false;
		load();
	}

	async function deleteLog(id: number) {
		await api.del(`/measurements/${id}`);
		load();
	}

	function fmt(iso: string) {
		return new Date(iso).toLocaleDateString('es', { day: 'numeric', month: 'short', year: '2-digit' });
	}
	function fmtShort(iso: string) {
		return new Date(iso).toLocaleDateString('es', { day: 'numeric', month: 'short' });
	}

	function labelForKey(key: string) {
		return MEASUREMENT_FIELDS.find((f) => f.key === key)?.label ?? key;
	}

	// Chronological logs for chart
	let chronological = $derived([...logs].reverse());

	// Get current value for a key (most recent log that has it)
	function currentFor(key: string): number | null {
		for (const log of logs) {
			const v = log.measurements[key];
			if (typeof v === 'number' && !Number.isNaN(v)) return v;
		}
		return null;
	}

	// Get previous value for a key (second most recent)
	function prevFor(key: string): number | null {
		let found = 0;
		for (const log of logs) {
			const v = log.measurements[key];
			if (typeof v === 'number' && !Number.isNaN(v)) {
				found++;
				if (found === 2) return v;
			}
		}
		return null;
	}

	// Sparkline data for a key (up to last 6 values)
	function sparkFor(key: string): number[] {
		const vals: number[] = [];
		for (const log of chronological) {
			const v = log.measurements[key];
			if (typeof v === 'number' && !Number.isNaN(v)) vals.push(v);
			if (vals.length >= 6) break;
		}
		return vals;
	}

	// Build smooth SVG path for sparkline
	function sparkPath(vals: number[], w: number, h: number): string {
		if (vals.length < 2) return '';
		const min = Math.min(...vals);
		const max = Math.max(...vals);
		const range = max - min || 1;
		const pad = 3;
		const pts = vals.map((v, i) => ({
			x: pad + (i / (vals.length - 1)) * (w - pad * 2),
			y: pad + (1 - (v - min) / range) * (h - pad * 2),
		}));
		let d = `M ${pts[0].x},${pts[0].y}`;
		for (let i = 1; i < pts.length; i++) {
			const p0 = pts[i - 1], p1 = pts[i];
			const mx = (p0.x + p1.x) / 2;
			d += ` Q ${mx},${p0.y} ${mx},${(p0.y + p1.y) / 2} T ${p1.x},${p1.y}`;
		}
		return d;
	}

	// Fields that have at least one value
	let activeFields = $derived(
		MEASUREMENT_FIELDS.filter(f => currentFor(f.key) !== null)
	);
</script>

<!-- Page header -->
<div class="trk-header">
	<div style="flex:1; min-width:0;">
		<h1 class="trk-title">Medidas</h1>
		<div class="trk-sub">Control corporal · mensual</div>
	</div>
	<button class="btn-reg" onclick={() => { showAdd = true; }}>+ Nueva</button>
</div>

<!-- 2-column grid of measurement cards -->
{#if activeFields.length > 0}
<div class="meas-grid">
	{#each activeFields as f}
		{@const cur = currentFor(f.key)}
		{@const prev = prevFor(f.key)}
		{@const delta = cur !== null && prev !== null ? cur - prev : null}
		{@const spark = sparkFor(f.key)}
		{@const hue = HUES[f.key] ?? 160}
		{@const color = `oklch(78% 0.16 ${hue})`}
		<div class="meas-card glass-card">
			<!-- Dot + label -->
			<div style="display:flex; align-items:center; gap:0.5rem;">
				<div class="meas-dot" style="background:{color}; box-shadow:0 0 12px {color};"></div>
				<span class="meas-label">{f.label}</span>
			</div>

			<!-- Current value -->
			{#if cur !== null}
				<div style="display:flex; align-items:baseline; gap:0.25rem; margin-top:0.625rem;">
					<div class="meas-value">{cur.toFixed(1)}</div>
					<div class="meas-unit">cm</div>
				</div>
			{:else}
				<div style="font-size:1.125rem; font-weight:700; color:rgba(255,255,255,0.3); margin-top:0.625rem;">—</div>
			{/if}

			<!-- Sparkline -->
			{#if spark.length >= 2}
				{@const path = sparkPath(spark, 130, 30)}
				<div style="margin-top:0.5rem; height:30px;">
					<svg viewBox="0 0 130 30" width="100%" height="30" style="display:block; overflow:visible;">
						<path d={path} fill="none" stroke={color} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/>
					</svg>
				</div>
			{/if}

			<!-- Delta -->
			{#if delta !== null}
				<div class="meas-delta" style="color:{delta === 0 ? 'rgba(255,255,255,0.4)' : delta > 0 ? 'oklch(85% 0.17 160)' : 'oklch(75% 0.18 30)'};">
					{delta === 0 ? '–' : delta > 0 ? '↑' : '↓'} {Math.abs(delta).toFixed(1)} cm
				</div>
			{/if}
		</div>
	{/each}
</div>
{/if}

<!-- Body silhouette map -->
<div class="section-eyebrow" style="margin:1.25rem 0.25rem 0.625rem;">Registro corporal</div>
<div class="glass-card" style="display:flex; flex-direction:column; align-items:center; padding:1.25rem 1rem 0.875rem;">
	<svg viewBox="0 0 100 130" width="200" height="260">
		<defs>
			<linearGradient id="body-grad" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0%" stop-color="oklch(85% 0.15 160 / 0.3)"/>
				<stop offset="100%" stop-color="oklch(65% 0.18 210 / 0.12)"/>
			</linearGradient>
		</defs>
		<!-- head -->
		<circle cx="50" cy="15" r="8" fill="url(#body-grad)" stroke="rgba(255,255,255,0.15)"/>
		<!-- torso -->
		<path d="M 38 26 L 62 26 L 66 58 L 58 70 L 42 70 L 34 58 Z" fill="url(#body-grad)" stroke="rgba(255,255,255,0.15)"/>
		<!-- arms -->
		<path d="M 38 28 L 28 32 L 22 55 L 28 58 L 34 38 Z" fill="url(#body-grad)" stroke="rgba(255,255,255,0.15)"/>
		<path d="M 62 28 L 72 32 L 78 55 L 72 58 L 66 38 Z" fill="url(#body-grad)" stroke="rgba(255,255,255,0.15)"/>
		<!-- legs -->
		<path d="M 42 70 L 40 115 L 46 115 L 50 78 L 54 115 L 60 115 L 58 70 Z" fill="url(#body-grad)" stroke="rgba(255,255,255,0.15)"/>

		<!-- measurement dots with labels -->
		{#each bodyPoints as pt}
			{@const cur = currentFor(pt.key)}
			{@const hue = HUES[pt.key] ?? 160}
			{@const col = `oklch(80% 0.16 ${hue})`}
			{#if cur !== null}
				<g>
					<circle cx={pt.x} cy={pt.y} r="5" fill={`oklch(80% 0.16 ${hue} / 0.3)`}/>
					<circle cx={pt.x} cy={pt.y} r="2" fill={col}/>
					<line x1={pt.x} y1={pt.y} x2={pt.x < 50 ? 8 : 92} y2={pt.y} stroke="rgba(255,255,255,0.15)" stroke-dasharray="1 2"/>
					<text x={pt.x < 50 ? 8 : 92} y={pt.y - 1.5} font-size="3.5" fill="rgba(255,255,255,0.7)"
						text-anchor={pt.x < 50 ? 'start' : 'end'}>{pt.label}</text>
					<text x={pt.x < 50 ? 8 : 92} y={pt.y + 3} font-size="3" fill={col}
						text-anchor={pt.x < 50 ? 'start' : 'end'} font-weight="600">{cur.toFixed(1)}cm</text>
				</g>
			{/if}
		{/each}
	</svg>
	<div style="font-size:0.6875rem; color:rgba(255,255,255,0.4); margin-top:0.25rem;">Toca + Nueva para registrar</div>
</div>

<!-- History log -->
{#if logs.length > 0}
<div class="section-eyebrow" style="margin:1.25rem 0.25rem 0.625rem;">Registros</div>
<div class="glass-card entry-list">
	{#each logs.slice(0, 10) as row, i (row.id)}
		<div class="entry-row" style="border-bottom:{i < Math.min(logs.length, 10) - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none'};">
			<div style="flex:1; min-width:0;">
				<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-bottom:0.25rem;">{fmt(row.logged_at)}</div>
				<div style="display:flex; flex-wrap:wrap; gap:0.25rem 0.625rem; font-size:0.75rem;">
					{#each Object.entries(row.measurements) as [k, v]}
						{@const hue = HUES[k] ?? 160}
						<span>
							<span style="color:rgba(255,255,255,0.45);">{labelForKey(k)}:</span>
							<strong style="color:oklch(78% 0.16 {hue});">
								{typeof v === 'number' ? v.toFixed(1) : v}
							</strong>
							<span style="color:rgba(255,255,255,0.35);"> cm</span>
						</span>
					{/each}
				</div>
			</div>
			<button class="del-btn" onclick={() => deleteLog(row.id)} aria-label="Eliminar">✕</button>
		</div>
	{/each}
</div>
{/if}

<!-- Add modal (bottom sheet) -->
{#if showAdd}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div class="modal-backdrop" onclick={() => (showAdd = false)}>
		<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
		<div class="modal-sheet" onclick={(e) => e.stopPropagation()}>
			<div class="modal-handle"></div>
			<div class="modal-title">Registrar medidas</div>
			<div class="modal-sub">Introduce los valores actuales</div>

			<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.625rem 0.75rem; margin-bottom:1.25rem; max-height:50dvh; overflow-y:auto;">
				{#each MEASUREMENT_FIELDS as f}
					{@const hue = HUES[f.key] ?? 160}
					<div class="form-field">
						<label class="form-label" style="color:oklch(78% 0.15 {hue});" for="m-{f.key}">{f.label}</label>
						<div style="display:flex; align-items:baseline; gap:0.25rem;">
							<input
								id="m-{f.key}"
								type="number"
								bind:value={form[f.key]}
								step="0.1"
								min="0"
								placeholder="—"
								class="field-input"
							/>
							<span style="font-size:0.7rem; color:rgba(255,255,255,0.4);">cm</span>
						</div>
					</div>
				{/each}
			</div>

			<button class="btn-submit" onclick={addEntry} disabled={saving}>
				{saving ? 'Guardando...' : 'Guardar medidas'}
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
		border-radius: 20px;
		padding: 0.875rem;
	}

	/* ── Measurement grid ── */
	.meas-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.625rem;
	}
	.meas-card { border-radius: 22px; }
	.meas-dot {
		width: 10px;
		height: 10px;
		border-radius: 3px;
		flex-shrink: 0;
	}
	.meas-label { font-size: 0.6875rem; color: rgba(255,255,255,0.6); font-weight: 600; }
	.meas-value {
		font-size: 1.625rem;
		font-weight: 700;
		color: #fff;
		letter-spacing: -0.05em;
		font-variant-numeric: tabular-nums;
	}
	.meas-unit { font-size: 0.625rem; color: rgba(255,255,255,0.4); }
	.meas-delta {
		margin-top: 0.25rem;
		font-size: 0.625rem;
		font-weight: 700;
	}

	/* ── Section ── */
	.section-eyebrow {
		font-size: 0.6875rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: rgba(255,255,255,0.45);
		font-weight: 700;
	}

	/* ── Log entries ── */
	.entry-list { padding: 0.25rem; }
	.entry-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 0.625rem;
	}
	.del-btn {
		background: none;
		border: none;
		color: rgba(255,255,255,0.3);
		cursor: pointer;
		font-size: 0.75rem;
		padding: 0.25rem;
		transition: color 0.15s;
		font-family: inherit;
		flex-shrink: 0;
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
		padding: 1.5rem 1.25rem max(5.5rem, calc(env(safe-area-inset-bottom, 0px) + 5.5rem));
		background: rgba(18,20,26,0.92);
		backdrop-filter: blur(40px) saturate(180%);
		-webkit-backdrop-filter: blur(40px) saturate(180%);
		border-top-left-radius: 28px;
		border-top-right-radius: 28px;
		border: 1px solid rgba(255,255,255,0.1);
		border-bottom: none;
		max-height: 90dvh;
		overflow-y: auto;
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

	/* ── Form ── */
	.form-field { display: flex; flex-direction: column; gap: 0.25rem; }
	.form-label { font-size: 0.6875rem; font-weight: 600; }
	.field-input {
		width: 100%;
		box-sizing: border-box;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.1);
		border-radius: 10px;
		color: #fff;
		padding: 0.375rem 0.625rem;
		font-size: 0.875rem;
		font-family: inherit;
		outline: none;
		font-variant-numeric: tabular-nums;
	}
	.field-input:focus { border-color: oklch(75% 0.18 165 / 0.5); }

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
