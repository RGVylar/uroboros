<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import Aurora from '$lib/components/uro/Aurora.svelte';
	import GlassCard from '$lib/components/uro/GlassCard.svelte';
	import Slider from '$lib/components/uro/Slider.svelte';

	let step = $state(0);

	// ── Objetivo y cuerpo ─────────────────────────────────────────────────
	let objective: 'lose' | 'maintain' | 'gain' = $state('maintain');
	let bodyWeight = $state(70);
	let bodyHeight = $state(170);
	let bodyAge = $state(25);
	let bodySex: 'male' | 'female' = $state('male');
	let bodyActivity = $state('moderate');
	let saving = $state(false);

	const objectives = [
		{ key: 'lose'     as const, emoji: '🔥', label: 'Perder peso',   sub: 'Déficit controlado',         kcalDelta: -400, pPct: 0.35, cPct: 0.35, fPct: 0.30, hue:  25 },
		{ key: 'maintain' as const, emoji: '⚖️', label: 'Mantenerme',    sub: 'Equilibrio',                 kcalDelta:    0, pPct: 0.30, cPct: 0.40, fPct: 0.30, hue: 165 },
		{ key: 'gain'     as const, emoji: '💪', label: 'Ganar músculo', sub: 'Superávit para crecer',      kcalDelta: +300, pPct: 0.30, cPct: 0.45, fPct: 0.25, hue: 220 },
	];

	const activities = [
		{ key: 'sedentary', label: 'Sedentario', sub: 'Sin ejercicio', factor: 1.2 },
		{ key: 'light',     label: 'Ligero',     sub: '1–3 días/sem',  factor: 1.375 },
		{ key: 'moderate',  label: 'Moderado',   sub: '3–5 días/sem',  factor: 1.55 },
		{ key: 'active',    label: 'Activo',     sub: '6–7 días/sem',  factor: 1.725 },
	];

	// TDEE en vivo (Mifflin–St Jeor)
	let calculated = $derived((() => {
		const bmr = bodySex === 'male'
			? 10 * bodyWeight + 6.25 * bodyHeight - 5 * bodyAge + 5
			: 10 * bodyWeight + 6.25 * bodyHeight - 5 * bodyAge - 161;
		const act = activities.find(a => a.key === bodyActivity)?.factor ?? 1.55;
		const tdee = Math.round(bmr * act);
		const obj = objectives.find(o => o.key === objective)!;
		const kcal = Math.max(1200, tdee + obj.kcalDelta);
		return {
			tdee,
			kcal,
			protein: Math.round((kcal * obj.pPct) / 4),
			carbs:   Math.round((kcal * obj.cPct) / 4),
			fat:     Math.round((kcal * obj.fPct) / 9),
		};
	})());

	let objMeta = $derived(objectives.find(o => o.key === objective)!);

	const TOTAL_STEPS = 7;

	async function next() {
		if (step < TOTAL_STEPS - 1) step++;
		else await finish();
	}
	function back() {
		if (step > 0) step--;
	}
	async function skip() { await finish(); }

	async function finish() {
		saving = true;
		try {
			await api.put('/goals', {
				kcal:    calculated.kcal,
				protein: calculated.protein,
				carbs:   calculated.carbs,
				fat:     calculated.fat,
				water_ml: 2500,
				track_creatine: false,
			});
		} catch {
			// silently continue
		} finally {
			saving = false;
		}
		goto('/');
	}
</script>

<Aurora />

<div class="ob-shell">

	<!-- Top bar: dots + skip -->
	<div class="ob-topbar">
		<div class="ob-dots">
			{#each Array(TOTAL_STEPS) as _, i}
				<div
					class="ob-dot"
					class:active={i === step}
					class:done={i < step}
				></div>
			{/each}
		</div>
		<button class="ob-skip" onclick={skip} disabled={saving}>Saltar</button>
	</div>

	<!-- Slide -->
	<div class="ob-content">

		<!-- Step 0: Welcome -->
		{#if step === 0}
			<div class="center">
				<div class="logo">U</div>
				<h1 class="serif big">Bienvenido a <em>uroboros</em></h1>
				<p class="sub">Vamos a ajustar tus calorías y macros en 6 pasos rápidos. Podrás cambiarlo todo más adelante.</p>
			</div>

		<!-- Step 1: Objetivo -->
		{:else if step === 1}
			<h1 class="serif">¿Cuál es tu objetivo?</h1>
			<p class="sub">Ajustaremos calorías y macros en base a esto.</p>
			<div class="stack">
				{#each objectives as o}
					{@const active = objective === o.key}
					<button
						class="opt-card"
						class:active
						style:--hue={o.hue}
						onclick={() => objective = o.key}
					>
						<div class="opt-icon">{o.emoji}</div>
						<div class="opt-texts">
							<div class="opt-label">{o.label}</div>
							<div class="opt-sub">{o.sub}</div>
						</div>
						<div class="opt-check">{active ? '✓' : ''}</div>
					</button>
				{/each}
			</div>

		<!-- Step 2: Cuerpo -->
		{:else if step === 2}
			<h1 class="serif">Cuéntanos sobre ti</h1>
			<p class="sub">Lo usamos para calcular tu metabolismo basal.</p>

			<div class="sex-grid">
				{#each [{ k: 'male' as const, l: 'Hombre', e: '♂' }, { k: 'female' as const, l: 'Mujer', e: '♀' }] as s}
					{@const a = bodySex === s.k}
					<button class="sex-card" class:active={a} onclick={() => bodySex = s.k}>
						<span class="sex-glyph">{s.e}</span>
						<span class="sex-label">{s.l}</span>
					</button>
				{/each}
			</div>

			<Slider label="Peso" bind:value={bodyWeight} min={40} max={150} unit="kg"/>
			<Slider label="Altura" bind:value={bodyHeight} min={140} max={210} unit="cm"/>
			<Slider label="Edad" bind:value={bodyAge} min={14} max={90} unit="años"/>

		<!-- Step 3: Actividad -->
		{:else if step === 3}
			<h1 class="serif">¿Cómo te mueves?</h1>
			<p class="sub">Tu nivel de actividad semanal.</p>
			<div class="act-grid">
				{#each activities as a}
					{@const active = bodyActivity === a.key}
					<button class="act-card" class:active onclick={() => bodyActivity = a.key}>
						<div class="act-factor">×{a.factor}</div>
						<div class="act-label">{a.label}</div>
						<div class="act-sub">{a.sub}</div>
					</button>
				{/each}
			</div>

		<!-- Step 4: Resumen -->
		{:else if step === 4}
			<h1 class="serif">Tu plan diario</h1>
			<p class="sub">Calculado con Mifflin–St Jeor. Lo puedes ajustar después.</p>

			<GlassCard padding={20}>
				<div class="summary">
					<div class="summary-pill">{objMeta.emoji} {objMeta.label}</div>
					<div class="summary-kcal">{calculated.kcal}</div>
					<div class="summary-tdee">kcal/día · TDEE {calculated.tdee}</div>
				</div>
			</GlassCard>

			<div class="macro-grid">
				{#each [
					{ l:'Proteína', v: calculated.protein, hue: 220 },
					{ l:'Carbs',    v: calculated.carbs,   hue: 275 },
					{ l:'Grasa',    v: calculated.fat,     hue: 355 },
				] as m}
					<div class="macro-card" style:--hue={m.hue}>
						<div class="macro-label">{m.l}</div>
						<div class="macro-value">{m.v}<span>g</span></div>
					</div>
				{/each}
			</div>

		<!-- Step 5: Pareja -->
		{:else if step === 5}
			<div class="center">
				<div class="pair-art">
					<div class="pair-bubble pair-left">{auth.user?.name?.[0]?.toUpperCase() ?? 'T'}</div>
					<div class="pair-bubble pair-right">?</div>
					<div class="pair-badge">2×</div>
				</div>
				<h1 class="serif">¿Comes con alguien?</h1>
				<p class="sub">Empareja vuestras cuentas para registrar una comida para los dos a la vez.</p>
				<button class="ghost-btn" onclick={() => { finish(); goto('/friends'); }}>＋ Invitar pareja</button>
				<div class="hint">O hazlo más tarde desde Ajustes.</div>
			</div>

		<!-- Step 6: Listo -->
		{:else if step === 6}
			<div class="center">
				<div class="check-big">✓</div>
				<h1 class="serif">Todo listo</h1>
				<p class="sub">Empieza añadiendo tu primera comida desde el botón ＋. Te enseñaré el resto sobre la marcha.</p>
			</div>
		{/if}
	</div>

	<!-- Bottom CTAs -->
	<div class="ob-actions">
		{#if step > 0}
			<button class="btn-back" onclick={back} disabled={saving}>Atrás</button>
		{/if}
		<button class="btn-next" onclick={next} disabled={saving}>
			{saving ? 'Guardando…' : step === TOTAL_STEPS - 1 ? 'Entrar a uroboros' : 'Siguiente'}
		</button>
	</div>
</div>

<style>
	.ob-shell {
		position: relative;
		z-index: 1;
		min-height: 100dvh;
		max-width: 480px;
		margin: 0 auto;
		padding: 20px 20px 32px;
		display: flex;
		flex-direction: column;
		color: #fff;
	}

	/* Top bar */
	.ob-topbar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 8px;
	}
	.ob-dots { display: flex; gap: 4px; }
	.ob-dot {
		width: 6px; height: 4px; border-radius: 99px;
		background: rgba(255,255,255,0.15);
		transition: all 0.3s;
	}
	.ob-dot.active { width: 22px; background: oklch(85% 0.17 160); }
	.ob-dot.done { background: oklch(85% 0.17 160); }
	.ob-skip {
		background: none; border: none;
		color: rgba(255,255,255,0.5);
		font-size: 12px; cursor: pointer; font-family: inherit;
	}
	.ob-skip:disabled { opacity: 0.5; }

	/* Content */
	.ob-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		justify-content: center;
		padding: 12px 0;
	}
	.center { text-align: center; }

	.serif {
		font-family: 'Instrument Serif', 'Lora', Georgia, serif;
		font-weight: 400;
		font-size: 30px;
		letter-spacing: -0.6px;
		line-height: 1.1;
		margin: 0 0 6px;
	}
	.serif.big { font-size: 36px; letter-spacing: -0.8px; margin-bottom: 14px; }
	.serif em { color: oklch(85% 0.17 160); font-style: italic; }
	.sub {
		font-size: 13px;
		color: rgba(255,255,255,0.6);
		line-height: 1.5;
		max-width: 320px;
		margin: 0 auto 18px;
	}
	.center .sub { margin-bottom: 18px; }

	/* Welcome logo */
	.logo {
		width: 88px; height: 88px; border-radius: 24px;
		margin: 0 auto 22px;
		background: linear-gradient(135deg, oklch(82% 0.18 160), oklch(62% 0.2 210));
		display: flex; align-items: center; justify-content: center;
		font-weight: 800; color: #041010; font-size: 44px; letter-spacing: -2px;
		box-shadow: 0 18px 50px oklch(75% 0.2 190 / 0.45);
	}

	/* Objective cards */
	.stack { display: flex; flex-direction: column; gap: 10px; }
	.opt-card {
		display: flex; align-items: center; gap: 14px;
		padding: 14px; border-radius: 18px;
		background: rgba(255,255,255,0.04);
		border: 1px solid rgba(255,255,255,0.08);
		color: #fff; cursor: pointer; font: inherit; text-align: left;
		transition: all 0.15s;
	}
	.opt-card.active {
		background: linear-gradient(135deg, oklch(72% 0.16 var(--hue) / 0.22), rgba(255,255,255,0.04));
		border-color: oklch(75% 0.18 var(--hue) / 0.55);
		box-shadow:
			0 12px 32px -10px oklch(72% 0.2 var(--hue) / 0.5),
			inset 0 1px 0 rgba(255,255,255,0.08);
	}
	.opt-icon {
		width: 48px; height: 48px; border-radius: 14px;
		display: flex; align-items: center; justify-content: center; font-size: 22px;
		background: rgba(255,255,255,0.06);
	}
	.opt-card.active .opt-icon {
		background: linear-gradient(135deg, oklch(80% 0.17 var(--hue)), oklch(60% 0.18 calc(var(--hue) + 20)));
	}
	.opt-texts { flex: 1; }
	.opt-label { font-size: 14px; font-weight: 800; }
	.opt-sub { font-size: 11px; color: rgba(255,255,255,0.55); margin-top: 2px; }
	.opt-check {
		width: 22px; height: 22px; border-radius: 50%;
		display: flex; align-items: center; justify-content: center;
		color: #041010; font-weight: 800; font-size: 12px;
		border: 1.5px solid rgba(255,255,255,0.2);
	}
	.opt-card.active .opt-check {
		background: oklch(80% 0.17 var(--hue));
		border-color: transparent;
	}

	/* Body */
	.sex-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
	.sex-card {
		padding: 14px 10px; border-radius: 16px;
		background: rgba(255,255,255,0.04);
		border: 1px solid rgba(255,255,255,0.08);
		color: #fff; display: flex; align-items: center; justify-content: center; gap: 8px;
		cursor: pointer; font: inherit;
	}
	.sex-card.active {
		background: linear-gradient(135deg, oklch(72% 0.16 165 / 0.22), rgba(255,255,255,0.04));
		border-color: oklch(75% 0.18 165 / 0.5);
	}
	.sex-glyph { font-size: 18px; }
	.sex-label { font-size: 13px; font-weight: 700; }

	/* Activity */
	.act-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
	.act-card {
		padding: 18px 12px; border-radius: 16px;
		background: rgba(255,255,255,0.04);
		border: 1px solid rgba(255,255,255,0.08);
		color: #fff; text-align: left; cursor: pointer; font: inherit;
	}
	.act-card.active {
		background: linear-gradient(135deg, oklch(72% 0.16 165 / 0.22), rgba(255,255,255,0.04));
		border-color: oklch(75% 0.18 165 / 0.5);
	}
	.act-factor { font-size: 11px; color: rgba(255,255,255,0.55); font-weight: 600; margin-bottom: 4px; }
	.act-label { font-size: 14px; font-weight: 800; margin-bottom: 2px; }
	.act-sub { font-size: 10px; color: rgba(255,255,255,0.5); }

	/* Summary */
	.summary { text-align: center; }
	.summary-pill {
		font-size: 10px; color: rgba(255,255,255,0.55);
		text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin-bottom: 6px;
	}
	.summary-kcal {
		font-size: 48px; font-weight: 800; color: #fff;
		letter-spacing: -2px; line-height: 1; font-variant-numeric: tabular-nums;
	}
	.summary-tdee {
		font-size: 11px; color: oklch(85% 0.16 160);
		margin-top: 4px; font-weight: 600;
	}
	.macro-grid {
		display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 12px;
	}
	.macro-card {
		padding: 14px 12px; border-radius: 14px; text-align: center;
		background: linear-gradient(180deg, oklch(72% 0.16 var(--hue) / 0.18), rgba(255,255,255,0.03));
		border: 1px solid oklch(72% 0.16 var(--hue) / 0.3);
	}
	.macro-label {
		font-size: 9px; color: oklch(80% 0.14 var(--hue));
		font-weight: 700; letter-spacing: 0.4px; text-transform: uppercase;
	}
	.macro-value {
		font-size: 22px; font-weight: 800; color: #fff;
		margin-top: 2px; font-variant-numeric: tabular-nums;
	}
	.macro-value span { font-size: 11px; color: rgba(255,255,255,0.4); margin-left: 2px; }

	/* Pair */
	.pair-art {
		position: relative; width: 200px; height: 120px; margin: 0 auto 28px;
	}
	.pair-bubble {
		position: absolute; top: 20px;
		width: 80px; height: 80px; border-radius: 50%;
		display: flex; align-items: center; justify-content: center;
		font-size: 32px; font-weight: 800;
	}
	.pair-left {
		left: 10px;
		background: linear-gradient(135deg, oklch(80% 0.18 160), oklch(60% 0.2 220));
		color: #041010;
	}
	.pair-right {
		right: 10px;
		background: linear-gradient(135deg, oklch(75% 0.18 330), oklch(55% 0.2 290));
		color: #fff;
	}
	.pair-badge {
		position: absolute; left: 50%; top: 45px; transform: translateX(-50%);
		width: 40px; height: 40px; border-radius: 12px;
		background: linear-gradient(135deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		display: flex; align-items: center; justify-content: center;
		font-size: 14px; font-weight: 800; color: #041010;
		box-shadow: 0 6px 20px oklch(75% 0.2 165 / 0.5);
	}
	.ghost-btn {
		padding: 12px 22px; border-radius: 14px; cursor: pointer; font: inherit;
		background: oklch(75% 0.18 165 / 0.15);
		border: 1px solid oklch(75% 0.18 165 / 0.4);
		color: oklch(85% 0.17 160); font-weight: 700; font-size: 13px;
	}
	.hint { font-size: 11px; color: rgba(255,255,255,0.4); margin-top: 14px; }

	/* Listo */
	.check-big {
		width: 96px; height: 96px; border-radius: 50%; margin: 0 auto 22px;
		background: linear-gradient(135deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		display: flex; align-items: center; justify-content: center;
		font-size: 46px; color: #041010;
		box-shadow: 0 18px 50px oklch(75% 0.2 165 / 0.5);
	}

	/* Bottom actions */
	.ob-actions { display: flex; gap: 10px; padding-top: 8px; }
	.btn-back {
		height: 54px; padding: 0 22px; border-radius: 18px;
		border: 1px solid rgba(255,255,255,0.1);
		background: rgba(255,255,255,0.04); color: #fff;
		cursor: pointer; font: inherit; font-weight: 600; font-size: 14px;
	}
	.btn-next {
		flex: 1;
		height: 54px; border-radius: 18px; border: none;
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010; cursor: pointer; font: inherit; font-weight: 800; font-size: 15px;
		box-shadow: 0 10px 30px -8px oklch(75% 0.22 165 / 0.55);
	}
	.btn-next:disabled, .btn-back:disabled { opacity: 0.5; cursor: default; }
</style>
