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
	let saved = $state(false);
	let loading = $state(true);

	$effect(() => {
		api.get<Goals>('/goals')
			.then(g => {
				kcal = g.kcal;
				protein = g.protein;
				carbs = g.carbs;
				fat = g.fat;
				water_ml = g.water_ml;
			})
			.catch(() => {})
			.finally(() => loading = false);
	});

	async function save() {
		await api.put('/goals', { kcal, protein, carbs, fat, water_ml });
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
