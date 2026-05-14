<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';

	let step = $state(0);

	// ── Objective & body data ─────────────────────────────────────────────────
	let objective: 'lose' | 'maintain' | 'gain' = $state('maintain');
	let bodyWeight = $state(70);
	let bodyHeight = $state(170);
	let bodyAge = $state(25);
	let bodySex: 'male' | 'female' = $state('male');
	let bodyActivity = $state('moderate');
	let saving = $state(false);

	const objectives = [
		{ key: 'lose'     as const, emoji: '🔥', label: 'Perder peso',   sub: 'Déficit calórico controlado',  kcalDelta: -400, pPct: 0.35, cPct: 0.35, fPct: 0.30 },
		{ key: 'maintain' as const, emoji: '⚖️', label: 'Mantenerme',    sub: 'Equilibrio y bienestar',       kcalDelta:    0, pPct: 0.30, cPct: 0.40, fPct: 0.30 },
		{ key: 'gain'     as const, emoji: '💪', label: 'Ganar músculo', sub: 'Superávit para crecer',        kcalDelta: +300, pPct: 0.30, cPct: 0.45, fPct: 0.25 },
	];

	const activities = [
		{ key: 'sedentary', label: 'Sedentario',    sub: 'Sin ejercicio', factor: 1.2 },
		{ key: 'light',     label: 'Ligero',        sub: '1–3 días/sem',  factor: 1.375 },
		{ key: 'moderate',  label: 'Moderado',      sub: '3–5 días/sem',  factor: 1.55 },
		{ key: 'active',    label: 'Activo',        sub: '6–7 días/sem',  factor: 1.725 },
	];

	// Calculate TDEE from current inputs
	let calculated = $derived((() => {
		const bmr = bodySex === 'male'
			? 10 * bodyWeight + 6.25 * bodyHeight - 5 * bodyAge + 5
			: 10 * bodyWeight + 6.25 * bodyHeight - 5 * bodyAge - 161;
		const act = activities.find(a => a.key === bodyActivity)?.factor ?? 1.55;
		const tdee = Math.round(bmr * act);
		const obj = objectives.find(o => o.key === objective)!;
		const kcal = Math.max(1200, tdee + obj.kcalDelta);
		return {
			kcal,
			protein: Math.round((kcal * obj.pPct) / 4),
			carbs:   Math.round((kcal * obj.cPct) / 4),
			fat:     Math.round((kcal * obj.fPct) / 9),
		};
	})());

	const TOTAL_STEPS = 7; // 0-6

	async function next() {
		if (step < TOTAL_STEPS - 1) {
			step++;
		} else {
			await finish();
		}
	}

	async function skip() {
		await finish();
	}

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
			// If goals fail (e.g. first time), silently continue
		} finally {
			saving = false;
		}
		goto('/');
	}
</script>

<div class="ob-shell">

	<!-- Top bar: dots + skip -->
	<div class="ob-topbar">
		<div class="ob-dots">
			{#each Array(TOTAL_STEPS) as _, i}
				<div class="ob-dot" class:ob-dot-active={i === step} class:ob-dot-done={i < step}></div>
			{/each}
		</div>
		<button class="ob-skip" onclick={skip} disabled={saving}>Saltar</button>
	</div>

	<!-- ─── SLIDES ──────────────────────────────────────────────── -->
	<div class="ob-content">

		<!-- Step 0: Search -->
		{#if step === 0}
			<div class="ob-art">
				<div class="ob-card-art">
					<div class="ob-search-bar">
						<span>🔍</span>
						<span class="ob-search-text">Avena integral</span>
					</div>
					{#each ['Avena integral · 370 kcal', 'Avena bio · 362 kcal', 'Barras avena · 464 kcal'] as item, i}
						<div class="ob-result-row" class:ob-result-row-active={i === 0}>{item}</div>
					{/each}
				</div>
			</div>
			<h1 class="ob-title">Registra con un toque</h1>
			<p class="ob-sub">Busca por nombre o escanea el código de barras. Avena, pollo, plátano — en menos de 2 segundos.</p>

		<!-- Step 1: Pair -->
		{:else if step === 1}
			<div class="ob-art">
				<div class="ob-pair-wrap">
					<div class="ob-avatar ob-avatar-left">
						{auth.user?.name?.[0]?.toUpperCase() ?? 'T'}
					</div>
					<div class="ob-avatar ob-avatar-right">❤️</div>
					<div class="ob-pair-badge">2×</div>
				</div>
			</div>
			<h1 class="ob-title">Compartes con tu pareja</h1>
			<p class="ob-sub">Registra una comida para los dos a la vez. Dos cuentas sincronizadas, sin esfuerzo doble.</p>

		<!-- Step 2: Streak -->
		{:else if step === 2}
			<div class="ob-art">
				<div class="ob-bars">
					{#each [1,2,3,4,5,6,7] as d}
						<div class="ob-bar" class:ob-bar-filled={d <= 5}>
							{#if d <= 5}🔥{/if}
						</div>
					{/each}
				</div>
			</div>
			<h1 class="ob-title">Progreso, no perfección</h1>
			<p class="ob-sub">Rachas, cheat days y objetivos ajustables. Hecho para durar semanas, no solo días.</p>

		<!-- Step 3: Features ocultas -->
		{:else if step === 3}
			<div class="ob-art ob-art-sm" style="margin-bottom:1.25rem;">
				<span style="font-size:3rem;">✨</span>
			</div>
			<h1 class="ob-title" style="margin-bottom:0.5rem;">Más que un contador</h1>
			<p class="ob-sub" style="margin-bottom:1.5rem;">Todo lo que necesitas para cuidarte, en un solo sitio.</p>
			<div class="ob-feat-grid">
				{#each [
					{ emoji: '🍳', label: 'Recetas',      sub: 'Crea y comparte tus platos' },
					{ emoji: '💊', label: 'Suplementos',  sub: 'Proteína, vitaminas, creatina' },
					{ emoji: '💪', label: 'Ejercicios',   sub: 'Registra tus entrenos' },
					{ emoji: '⚖️', label: 'Peso',         sub: 'Curva de evolución' },
					{ emoji: '📏', label: 'Medidas',      sub: 'Cintura, brazos, pecho…' },
					{ emoji: '💧', label: 'Agua',         sub: 'Hidratación diaria' },
				] as feat}
					<div class="ob-feat-card">
						<span class="ob-feat-emoji">{feat.emoji}</span>
						<span class="ob-feat-label">{feat.label}</span>
						<span class="ob-feat-sub">{feat.sub}</span>
					</div>
				{/each}
			</div>

		<!-- Step 4: Objective picker -->
		{:else if step === 4}
			<div class="ob-art ob-art-sm">
				<span style="font-size: 3.5rem;">🎯</span>
			</div>
			<h1 class="ob-title">¿Qué quieres conseguir?</h1>
			<p class="ob-sub" style="margin-bottom: 1.5rem;">Elige tu objetivo y personalizamos todo para ti.</p>
			<div class="ob-obj-grid">
				{#each objectives as obj}
					<button
						class="ob-obj-card"
						class:ob-obj-card-active={objective === obj.key}
						onclick={() => objective = obj.key}
					>
						<span class="ob-obj-emoji">{obj.emoji}</span>
						<span class="ob-obj-label">{obj.label}</span>
						<span class="ob-obj-sub">{obj.sub}</span>
					</button>
				{/each}
			</div>

		<!-- Step 5: Body data -->
		{:else if step === 5}
			<h1 class="ob-title" style="margin-bottom:0.375rem;">Cuéntanos sobre ti</h1>
			<p class="ob-sub" style="margin-bottom:1.25rem;">Para calcular tus calorías con precisión.</p>

			<div class="ob-form-grid">
				<div class="ob-field">
					<label>Peso (kg)</label>
					<input type="number" bind:value={bodyWeight} min="30" max="300" step="0.5" />
				</div>
				<div class="ob-field">
					<label>Altura (cm)</label>
					<input type="number" bind:value={bodyHeight} min="100" max="250" step="1" />
				</div>
				<div class="ob-field">
					<label>Edad</label>
					<input type="number" bind:value={bodyAge} min="10" max="99" step="1" />
				</div>
				<div class="ob-field">
					<label>Sexo</label>
					<div class="ob-sex-toggle">
						<button class:ob-sex-active={bodySex === 'male'} onclick={() => bodySex = 'male'}>♂ Hombre</button>
						<button class:ob-sex-active={bodySex === 'female'} onclick={() => bodySex = 'female'}>♀ Mujer</button>
					</div>
				</div>
			</div>

			<div class="ob-field" style="margin-top:0.75rem;">
				<label>Actividad física</label>
				<div class="ob-activity-grid">
					{#each activities as act}
						<button
							class="ob-act-btn"
							class:ob-act-btn-active={bodyActivity === act.key}
							onclick={() => bodyActivity = act.key}
						>
							<span class="ob-act-label">{act.label}</span>
							<span class="ob-act-sub">{act.sub}</span>
						</button>
					{/each}
				</div>
			</div>

		<!-- Step 6: Result -->
		{:else if step === 6}
			<div class="ob-art ob-art-sm">
				<span style="font-size:3rem;">🎉</span>
			</div>
			<h1 class="ob-title">Tu plan personalizado</h1>
			<p class="ob-sub" style="margin-bottom:1.25rem;">Basado en tu perfil y objetivo. Puedes ajustarlo cuando quieras en Ajustes.</p>

			<div class="ob-result-card">
				<div class="ob-result-kcal">
					<span class="ob-result-num">{calculated.kcal}</span>
					<span class="ob-result-unit">kcal / día</span>
				</div>
				<div class="ob-result-macros">
					<div class="ob-macro-pill" style="--hue:220">
						<div class="ob-macro-pill-label">Proteína</div>
						<div class="ob-macro-pill-val">{calculated.protein}g</div>
					</div>
					<div class="ob-macro-pill" style="--hue:275">
						<div class="ob-macro-pill-label">Carbos</div>
						<div class="ob-macro-pill-val">{calculated.carbs}g</div>
					</div>
					<div class="ob-macro-pill" style="--hue:25">
						<div class="ob-macro-pill-label">Grasa</div>
						<div class="ob-macro-pill-val">{calculated.fat}g</div>
					</div>
				</div>
			</div>

			<p style="font-size:0.7rem; color:rgba(255,255,255,0.35); text-align:center; margin-top:0.875rem; line-height:1.5;">
				Objetivo: {objectives.find(o => o.key === objective)?.label} · Podrás cambiar esto en Ajustes → Objetivos
			</p>
		{/if}

	</div><!-- /ob-content -->

	<!-- CTA -->
	<button class="ob-cta" onclick={next} disabled={saving}>
		{#if saving}
			Guardando…
		{:else if step === TOTAL_STEPS - 1}
			¡Empezar! 🚀
		{:else if step >= 3}
			Continuar
		{:else}
			Siguiente
		{/if}
	</button>

</div>

<style>
	/* ── Shell ── */
	.ob-shell {
		display: flex;
		flex-direction: column;
		min-height: 85dvh;
		padding: 1.25rem 1.25rem max(2rem, calc(env(safe-area-inset-bottom, 0px) + 2rem));
	}

	/* ── Top bar ── */
	.ob-topbar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.25rem;
	}
	.ob-dots { display: flex; gap: 0.3rem; }
	.ob-dot {
		height: 4px;
		width: 8px;
		border-radius: 99px;
		background: rgba(255,255,255,0.15);
		transition: all 0.3s ease;
	}
	.ob-dot-active { width: 22px; background: oklch(85% 0.17 160); }
	.ob-dot-done   { background: oklch(75% 0.17 160 / 0.5); }
	.ob-skip {
		background: none;
		border: none;
		color: rgba(255,255,255,0.45);
		font-size: 0.75rem;
		cursor: pointer;
		font-family: inherit;
		padding: 0.25rem 0;
		min-width: 40px;
		text-align: right;
	}

	/* ── Content area ── */
	.ob-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		text-align: center;
		padding: 1.5rem 0 1rem;
	}

	/* ── Art ── */
	.ob-art {
		margin-bottom: 2rem;
		display: flex;
		justify-content: center;
	}
	.ob-art-sm { margin-bottom: 1rem; }

	/* Search art */
	.ob-card-art {
		width: 240px;
		background: rgba(255,255,255,0.05);
		backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 20px;
		padding: 1.25rem;
	}
	.ob-search-bar {
		display: flex;
		align-items: center;
		gap: 0.625rem;
		margin-bottom: 0.875rem;
		padding: 0.5rem 0.75rem;
		background: rgba(255,255,255,0.04);
		border-radius: 12px;
		font-size: 0.875rem;
	}
	.ob-search-text { font-size: 0.6875rem; color: rgba(255,255,255,0.6); }
	.ob-result-row {
		padding: 0.625rem 0.75rem;
		border-radius: 10px;
		background: rgba(255,255,255,0.03);
		margin-bottom: 0.375rem;
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.6);
	}
	.ob-result-row:last-child { margin-bottom: 0; }
	.ob-result-row-active {
		background: oklch(75% 0.18 165 / 0.15);
		color: oklch(85% 0.15 160);
		font-weight: 600;
	}

	/* Pair art */
	.ob-pair-wrap {
		position: relative;
		width: 180px;
		height: 120px;
	}
	.ob-avatar {
		position: absolute;
		top: 20px;
		width: 80px;
		height: 80px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 2rem;
		font-weight: 800;
	}
	.ob-avatar-left {
		left: 0;
		background: linear-gradient(135deg, oklch(80% 0.18 160), oklch(60% 0.2 220));
		color: #041010;
	}
	.ob-avatar-right {
		right: 0;
		background: linear-gradient(135deg, oklch(75% 0.18 330), oklch(55% 0.2 290));
		color: #fff;
	}
	.ob-pair-badge {
		position: absolute;
		left: 50%;
		top: 44px;
		transform: translateX(-50%);
		width: 42px;
		height: 42px;
		border-radius: 12px;
		background: linear-gradient(135deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.875rem;
		font-weight: 800;
		color: #041010;
		box-shadow: 0 6px 20px oklch(75% 0.2 165 / 0.5);
	}

	/* Streak bars art */
	.ob-bars { display: flex; gap: 0.5rem; align-items: flex-end; }
	.ob-bar {
		width: 26px;
		height: 32px;
		border-radius: 10px;
		background: rgba(255,255,255,0.06);
		display: flex;
		align-items: flex-end;
		justify-content: center;
		padding: 0.375rem;
		font-size: 0.875rem;
	}
	.ob-bar-filled {
		height: 70px;
		background: linear-gradient(180deg, oklch(80% 0.19 45), oklch(65% 0.2 25));
	}

	/* ── Text ── */
	.ob-title {
		font-size: 2.25rem;
		font-weight: 400;
		letter-spacing: -0.05em;
		color: #fff;
		line-height: 1.1;
		margin: 0 0 0.875rem;
		font-family: 'Lora', 'Georgia', serif;
	}
	.ob-sub {
		font-size: 0.875rem;
		color: rgba(255,255,255,0.55);
		line-height: 1.55;
		max-width: 290px;
		margin: 0 auto;
	}

	/* ── Feature grid ── */
	.ob-feat-grid {
		display: grid;
		grid-template-columns: 1fr 1fr 1fr;
		gap: 0.5rem;
		width: 100%;
	}
	.ob-feat-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.2rem;
		padding: 0.75rem 0.375rem;
		border-radius: 16px;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.07);
	}
	.ob-feat-emoji { font-size: 1.5rem; }
	.ob-feat-label {
		font-size: 0.72rem;
		font-weight: 700;
		color: #fff;
		margin-top: 0.1rem;
	}
	.ob-feat-sub {
		font-size: 0.6rem;
		color: rgba(255,255,255,0.4);
		text-align: center;
		line-height: 1.3;
	}

	/* ── Objective cards ── */
	.ob-obj-grid {
		display: grid;
		grid-template-columns: 1fr 1fr 1fr;
		gap: 0.5rem;
		width: 100%;
	}
	.ob-obj-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.25rem;
		padding: 0.875rem 0.5rem;
		border-radius: 18px;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.08);
		cursor: pointer;
		transition: background 0.15s, border-color 0.15s, transform 0.15s;
		font-family: inherit;
		color: rgba(255,255,255,0.7);
	}
	.ob-obj-card:hover { background: rgba(255,255,255,0.09); }
	.ob-obj-card-active {
		background: oklch(75% 0.18 165 / 0.15);
		border-color: oklch(80% 0.17 165 / 0.5);
		color: #fff;
		transform: translateY(-2px);
		box-shadow: 0 8px 24px oklch(75% 0.2 165 / 0.2);
	}
	.ob-obj-emoji { font-size: 1.75rem; }
	.ob-obj-label { font-size: 0.72rem; font-weight: 700; }
	.ob-obj-sub { font-size: 0.6rem; color: rgba(255,255,255,0.4); line-height: 1.3; }
	.ob-obj-card-active .ob-obj-sub { color: rgba(255,255,255,0.6); }

	/* ── Body form ── */
	.ob-form-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.75rem;
		width: 100%;
	}
	.ob-field {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		text-align: left;
	}
	.ob-field label {
		font-size: 0.6875rem;
		font-weight: 600;
		color: rgba(255,255,255,0.5);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.ob-field input {
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.1);
		border-radius: 12px;
		color: #fff;
		padding: 0.625rem 0.75rem;
		font-size: 0.9375rem;
		font-weight: 700;
		font-family: inherit;
		outline: none;
		width: 100%;
		box-sizing: border-box;
		font-variant-numeric: tabular-nums;
	}
	.ob-field input:focus { border-color: oklch(75% 0.18 165 / 0.6); }
	.ob-sex-toggle {
		display: flex;
		gap: 0.375rem;
	}
	.ob-sex-toggle button {
		flex: 1;
		padding: 0.625rem 0.25rem;
		border-radius: 12px;
		border: 1px solid rgba(255,255,255,0.1);
		background: rgba(255,255,255,0.05);
		color: rgba(255,255,255,0.55);
		font-size: 0.75rem;
		font-weight: 700;
		font-family: inherit;
		cursor: pointer;
		transition: background 0.15s, border-color 0.15s, color 0.15s;
	}
	.ob-sex-active {
		background: oklch(75% 0.18 165 / 0.18) !important;
		border-color: oklch(80% 0.17 165 / 0.5) !important;
		color: #fff !important;
	}
	.ob-activity-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.375rem;
	}
	.ob-act-btn {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		padding: 0.625rem 0.75rem;
		border-radius: 12px;
		border: 1px solid rgba(255,255,255,0.08);
		background: rgba(255,255,255,0.04);
		cursor: pointer;
		font-family: inherit;
		transition: background 0.15s, border-color 0.15s;
		text-align: left;
	}
	.ob-act-btn:hover { background: rgba(255,255,255,0.08); }
	.ob-act-btn-active {
		background: oklch(75% 0.18 165 / 0.15);
		border-color: oklch(80% 0.17 165 / 0.45);
	}
	.ob-act-label {
		font-size: 0.75rem;
		font-weight: 700;
		color: #fff;
	}
	.ob-act-sub {
		font-size: 0.6rem;
		color: rgba(255,255,255,0.4);
		margin-top: 0.1rem;
	}
	.ob-act-btn-active .ob-act-sub { color: rgba(255,255,255,0.6); }

	/* ── Result card ── */
	.ob-result-card {
		width: 100%;
		background: rgba(255,255,255,0.05);
		backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 24px;
		padding: 1.5rem 1.25rem;
	}
	.ob-result-kcal {
		display: flex;
		align-items: baseline;
		justify-content: center;
		gap: 0.4rem;
		margin-bottom: 1.25rem;
	}
	.ob-result-num {
		font-size: 3.5rem;
		font-weight: 800;
		color: oklch(85% 0.17 55);
		letter-spacing: -0.06em;
		font-variant-numeric: tabular-nums;
		line-height: 1;
	}
	.ob-result-unit {
		font-size: 0.875rem;
		color: rgba(255,255,255,0.45);
		font-weight: 500;
	}
	.ob-result-macros {
		display: grid;
		grid-template-columns: 1fr 1fr 1fr;
		gap: 0.5rem;
	}
	.ob-macro-pill {
		padding: 0.625rem 0.5rem;
		border-radius: 14px;
		background: oklch(72% 0.18 var(--hue) / 0.1);
		border: 1px solid oklch(72% 0.18 var(--hue) / 0.2);
		text-align: center;
	}
	.ob-macro-pill-label {
		font-size: 0.6rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: oklch(80% 0.15 var(--hue));
		margin-bottom: 0.25rem;
	}
	.ob-macro-pill-val {
		font-size: 1.125rem;
		font-weight: 800;
		color: #fff;
		font-variant-numeric: tabular-nums;
	}

	/* ── CTA button ── */
	.ob-cta {
		height: 54px;
		border-radius: 18px;
		border: none;
		cursor: pointer;
		font-family: inherit;
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		font-weight: 800;
		font-size: 0.9375rem;
		letter-spacing: -0.01em;
		box-shadow:
			0 10px 30px -8px oklch(75% 0.22 165 / 0.55),
			inset 0 1px 0 rgba(255,255,255,0.4);
		transition: opacity 0.15s, transform 0.15s;
	}
	.ob-cta:disabled { opacity: 0.6; cursor: not-allowed; }
	.ob-cta:not(:disabled):hover { transform: translateY(-1px); }
	.ob-cta:not(:disabled):active { transform: translateY(0); }
</style>
