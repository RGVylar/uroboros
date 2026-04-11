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
	let tdeeResult: { tdee: number; bmr: number } | null = $state(null);

	const activityFactors: Record<string, { label: string; factor: number }> = {
		sedentary:    { label: 'Sedentario (sin ejercicio)',        factor: 1.2 },
		light:        { label: 'Ligero (1–3 días/semana)',          factor: 1.375 },
		moderate:     { label: 'Moderado (3–5 días/semana)',        factor: 1.55 },
		active:       { label: 'Activo (6–7 días/semana)',          factor: 1.725 },
		very_active:  { label: 'Muy activo (doble turno / físico)', factor: 1.9 },
	};

	function calcTdee() {
		// Mifflin-St Jeor
		const bmr = tdeeSex === 'male'
			? 10 * tdeeWeight + 6.25 * tdeeHeight - 5 * tdeeAge + 5
			: 10 * tdeeWeight + 6.25 * tdeeHeight - 5 * tdeeAge - 161;
		const tdee = Math.round(bmr * activityFactors[tdeeActivity].factor);
		tdeeResult = { tdee, bmr: Math.round(bmr) };
	}

	function applyTdee() {
		if (!tdeeResult) return;
		kcal = tdeeResult.tdee;
		// Distribute macros: 30% protein, 40% carbs, 30% fat (sensible defaults)
		protein = Math.round((tdeeResult.tdee * 0.30) / 4);
		carbs    = Math.round((tdeeResult.tdee * 0.40) / 4);
		fat      = Math.round((tdeeResult.tdee * 0.30) / 9);
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

				<button onclick={calcTdee} style="width:100%; margin-bottom:0.75rem; color: black;">Calcular</button>

				{#if tdeeResult}
					<div style="background:var(--bg); border-radius:10px; padding:0.85rem; margin-bottom:0.75rem;">
						<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; text-align:center;">
							<div>
								<div style="font-size:0.7rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em;">BMR</div>
								<div style="font-size:1.4rem; font-weight:800; color:var(--text);">{tdeeResult.bmr}</div>
								<div style="font-size:0.7rem; color:var(--text-muted);">kcal base</div>
							</div>
							<div>
								<div style="font-size:0.7rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em;">TDEE</div>
								<div style="font-size:1.4rem; font-weight:800; color:var(--primary);">{tdeeResult.tdee}</div>
								<div style="font-size:0.7rem; color:var(--text-muted);">kcal/día</div>
							</div>
						</div>
					</div>
					<button onclick={applyTdee} class="btn-secondary" style="width:100%; font-size:0.85rem;">
						Aplicar al objetivo (distribuye macros 30/40/30)
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
