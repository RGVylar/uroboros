<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Goals } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	let isOnboarding = $derived($page.url.searchParams.get('new') === '1');

	let kcal = $state(2000);
	let protein = $state(150);
	let carbs = $state(250);
	let fat = $state(65);
	let water_ml = $state(2000);
	let track_creatine = $state(false);
	let saved = $state(false);
	let loading = $state(true);

	// TDEE calculator state
	let showTdee = $state(false);
	let tdeeWeight = $state(75);
	let tdeeHeight = $state(175);
	let tdeeAge = $state(25);
	let tdeeSex: 'male' | 'female' = $state('male');
	let tdeeActivity = $state('moderate');
	let tdeeObjective = $state('maintain');
	let tdeeResult: { tdee: number; bmr: number; target: number } | null = $state(null);

	const activityFactors: Record<string, { label: string; factor: number }> = {
		sedentary:    { label: 'Sedentario (sin ejercicio)',        factor: 1.2 },
		light:        { label: 'Ligero (1–3 días/semana)',          factor: 1.375 },
		moderate:     { label: 'Moderado (3–5 días/semana)',        factor: 1.55 },
		active:       { label: 'Activo (6–7 días/semana)',          factor: 1.725 },
		very_active:  { label: 'Muy activo (doble turno / físico)', factor: 1.9 },
	};

	const objectives: Record<string, { label: string; emoji: string; kcalDelta: number; pPct: number; cPct: number; fPct: number; hint: string }> = {
		lose:     { label: 'Perder peso',     emoji: '🔥', kcalDelta: -400, pPct: 0.35, cPct: 0.35, fPct: 0.30, hint: 'Déficit de 400 kcal · más proteína para preservar músculo' },
		maintain: { label: 'Mantener',        emoji: '⚖️', kcalDelta:    0, pPct: 0.30, cPct: 0.40, fPct: 0.30, hint: 'Mantenimiento · distribución equilibrada' },
		gain:     { label: 'Ganar músculo',   emoji: '💪', kcalDelta: +300, pPct: 0.30, cPct: 0.45, fPct: 0.25, hint: 'Superávit de 300 kcal · más carbohidratos para el entrenamiento' },
	};

	function calcTdee() {
		// Mifflin-St Jeor
		const bmr = tdeeSex === 'male'
			? 10 * tdeeWeight + 6.25 * tdeeHeight - 5 * tdeeAge + 5
			: 10 * tdeeWeight + 6.25 * tdeeHeight - 5 * tdeeAge - 161;
		const tdee = Math.round(bmr * activityFactors[tdeeActivity].factor);
		const target = tdee + objectives[tdeeObjective].kcalDelta;
		tdeeResult = { tdee, bmr: Math.round(bmr), target };
	}

	function applyTdee() {
		if (!tdeeResult) return;
		const obj = objectives[tdeeObjective];
		kcal    = tdeeResult.target;
		protein = Math.round((tdeeResult.target * obj.pPct) / 4);
		carbs   = Math.round((tdeeResult.target * obj.cPct) / 4);
		fat     = Math.round((tdeeResult.target * obj.fPct) / 9);
		showTdee = false;
	}

	$effect(() => {
		api.get<Goals>('/goals')
			.then(g => {
				kcal = g.kcal;
				protein = g.protein;
				carbs = g.carbs;
				fat = g.fat;
				water_ml = g.water_ml;
				track_creatine = g.track_creatine ?? false;
			})
			.catch(() => {})
			.finally(() => loading = false);
	});

	async function save() {
		await api.put('/goals', { kcal, protein, carbs, fat, water_ml, track_creatine });
		if (isOnboarding) {
			goto('/');
		} else {
			saved = true;
			setTimeout(() => saved = false, 2000);
		}
	}
</script>

{#if isOnboarding}
	<div style="text-align:center; margin-bottom:1.5rem;">
		<div style="font-size:2rem; margin-bottom:0.5rem;">Hola, {auth.user?.name}!</div>
		<p style="color:var(--text-muted);">Configura tus objetivos diarios para empezar a trackear</p>
	</div>
{:else}
	<h1>Objetivos diarios</h1>
{/if}

{#if loading}
	<p style="color:var(--text-muted);">Cargando...</p>
{:else}

	<!-- TDEE Calculator -->
	<div class="card" style="margin-bottom:1rem;">
		<button
			onclick={() => { showTdee = !showTdee; tdeeResult = null; }}
			style="width:100%; display:flex; align-items:center; justify-content:space-between; background:none; border:none; cursor:pointer; padding:0;"
		>
			<div style="display:flex; align-items:center; gap:0.6rem;">
				<span style="font-size:1.2rem;">🧮</span>
				<div style="text-align:left;">
					<div style="font-weight:700; font-size:0.95rem; color:var(--text);">Calculadora TDEE / BMR</div>
					<div style="font-size:0.75rem; color:var(--text-muted);">Calcula tus calorías según tu metabolismo</div>
				</div>
			</div>
			<span style="color:var(--text-muted); font-size:1rem; transition:transform 0.2s; transform:{showTdee ? 'rotate(90deg)' : 'rotate(0)'};">›</span>
		</button>

		{#if showTdee}
			<div style="margin-top:1rem; border-top:1px solid var(--border); padding-top:1rem;">
				<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem; margin-bottom:0.75rem;">
					<div class="form-group" style="margin-bottom:0;">
						<label for="tdee-weight">Peso (kg)</label>
						<input id="tdee-weight" type="number" bind:value={tdeeWeight} min="30" max="300" step="0.5" />
					</div>
					<div class="form-group" style="margin-bottom:0;">
						<label for="tdee-height">Altura (cm)</label>
						<input id="tdee-height" type="number" bind:value={tdeeHeight} min="100" max="250" step="1" />
					</div>
					<div class="form-group" style="margin-bottom:0;">
						<label for="tdee-age">Edad</label>
						<input id="tdee-age" type="number" bind:value={tdeeAge} min="10" max="120" step="1" />
					</div>
					<div class="form-group" style="margin-bottom:0;">
						<label for="tdee-sex">Sexo</label>
						<select id="tdee-sex" bind:value={tdeeSex} style="width:100%; padding:0.5rem; border-radius:8px; border:1px solid var(--border); background:var(--surface); color:var(--text);">
							<option value="male">Hombre</option>
							<option value="female">Mujer</option>
						</select>
					</div>
				</div>

				<div class="form-group" style="margin-bottom:0.75rem;">
					<label for="tdee-activity">Nivel de actividad</label>
					<select id="tdee-activity" bind:value={tdeeActivity} style="width:100%; padding:0.5rem; border-radius:8px; border:1px solid var(--border); background:var(--surface); color:var(--text);">
						{#each Object.entries(activityFactors) as [key, val]}
							<option value={key}>{val.label}</option>
						{/each}
					</select>
				</div>

				<div class="form-group" style="margin-bottom:0.75rem;">
					<label>Objetivo</label>
					<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.4rem;">
						{#each Object.entries(objectives) as [key, obj]}
							<button
								onclick={() => { tdeeObjective = key; tdeeResult = null; }}
								style="padding:0.5rem 0.25rem; border-radius:8px; border:1px solid {tdeeObjective === key ? 'var(--primary)' : 'var(--border)'}; background:{tdeeObjective === key ? 'color-mix(in srgb, var(--primary) 15%, transparent)' : 'var(--surface)'}; color:var(--text); cursor:pointer; font-size:0.78rem; text-align:center; line-height:1.3;">
								<div style="font-size:1rem;">{obj.emoji}</div>
								{obj.label}
							</button>
						{/each}
					</div>
				</div>

				<button onclick={calcTdee} style="width:100%; margin-bottom:0.75rem; color: black;">Calcular</button>

				{#if tdeeResult}
					{@const obj = objectives[tdeeObjective]}
					<div style="background:var(--bg); border-radius:10px; padding:0.85rem; margin-bottom:0.6rem;">
						<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.5rem; text-align:center;">
							<div>
								<div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em;">BMR</div>
								<div style="font-size:1.2rem; font-weight:800; color:var(--text);">{tdeeResult.bmr}</div>
								<div style="font-size:0.65rem; color:var(--text-muted);">metabolismo base</div>
							</div>
							<div>
								<div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em;">TDEE</div>
								<div style="font-size:1.2rem; font-weight:800; color:var(--text);">{tdeeResult.tdee}</div>
								<div style="font-size:0.65rem; color:var(--text-muted);">con actividad</div>
							</div>
							<div>
								<div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em;">OBJETIVO</div>
								<div style="font-size:1.2rem; font-weight:800; color:var(--primary);">{tdeeResult.target}</div>
								<div style="font-size:0.65rem; color:var(--text-muted);">kcal/día</div>
							</div>
						</div>
					</div>
					<p style="font-size:0.75rem; color:var(--text-muted); margin:0 0 0.6rem; text-align:center;">
						{obj.hint}
					</p>
					<button onclick={applyTdee} class="btn-secondary" style="width:100%; font-size:0.85rem;">
						Aplicar objetivo · P{Math.round(obj.pPct*100)}% C{Math.round(obj.cPct*100)}% G{Math.round(obj.fPct*100)}%
					</button>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Manual goals -->
	<div class="card">
		<div class="form-group">
			<label for="g-kcal">Calorías (kcal)</label>
			<input id="g-kcal" type="number" bind:value={kcal} min="0" step="50" />
		</div>
		<div class="form-group">
			<label for="g-prot">Proteína (g)</label>
			<input id="g-prot" type="number" bind:value={protein} min="0" step="5" />
		</div>
		<div class="form-group">
			<label for="g-carb">Carbohidratos (g)</label>
			<input id="g-carb" type="number" bind:value={carbs} min="0" step="5" />
		</div>
		<div class="form-group">
			<label for="g-fat">Grasa (g)</label>
			<input id="g-fat" type="number" bind:value={fat} min="0" step="5" />
		</div>
		<div class="form-group">
			<label for="g-water">Agua (ml)</label>
			<input id="g-water" type="number" bind:value={water_ml} min="0" step="250" />
		</div>

		<button onclick={save} style="width:100%;">
			{#if isOnboarding}
				Empezar
			{:else}
				{saved ? 'Guardado!' : 'Guardar objetivos'}
			{/if}
		</button>
	</div>
{/if}
