<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Recipe, Product, DiaryEntry } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	let recipes: Recipe[] = $state([]);
	let showCreate = $state(false);

	// create form
	let recipeName = $state('');
	let ingredients: { product: Product; grams: number }[] = $state([]);
	let searchQuery = $state('');
	let searchResults: Product[] = $state([]);
	let error = $state('');

	async function load() {
		recipes = await api.get<Recipe[]>('/recipes');
	}

	$effect(() => { load(); });

	async function searchProducts() {
		if (!searchQuery.trim()) return;
		searchResults = await api.get<Product[]>(`/products?q=${encodeURIComponent(searchQuery)}`);
	}

	function addIngredient(product: Product) {
		if (!ingredients.find(i => i.product.id === product.id)) {
			ingredients = [...ingredients, { product, grams: 100 }];
		}
		searchResults = [];
		searchQuery = '';
	}

	function removeIngredient(idx: number) {
		ingredients = ingredients.filter((_, i) => i !== idx);
	}

	async function createRecipe() {
		if (!recipeName.trim() || ingredients.length === 0) {
			error = 'Nombre y al menos un ingrediente requeridos';
			return;
		}
		error = '';
		try {
			await api.post('/recipes', {
				name: recipeName,
				ingredients: ingredients.map(i => ({ product_id: i.product.id, grams: i.grams }))
			});
			recipeName = '';
			ingredients = [];
			showCreate = false;
			load();
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		}
	}

	async function logRecipe(recipe: Recipe) {
		try {
			for (const ing of recipe.ingredients) {
				await api.post<DiaryEntry[]>('/diary', {
					product_id: ing.product_id,
					grams: ing.grams,
					consumed_at: new Date().toISOString()
				});
			}
			goto('/');
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		}
	}

	async function deleteRecipe(id: number) {
		await api.del(`/recipes/${id}`);
		load();
	}

	function totalMacros(ings: { product: Product; grams: number }[]) {
		let cal = 0, p = 0, c = 0, f = 0;
		for (const i of ings) {
			const factor = i.grams / 100;
			cal += i.product.calories_per_100g * factor;
			p += i.product.protein_per_100g * factor;
			c += i.product.carbs_per_100g * factor;
			f += i.product.fat_per_100g * factor;
		}
		return { cal: Math.round(cal), p: Math.round(p), c: Math.round(c), f: Math.round(f) };
	}
</script>

<h1>Recetas</h1>

{#if showCreate}
	<div class="card" style="margin-bottom:1rem;">
		<h2>Nueva receta</h2>
		<div class="form-group">
			<label for="r-name">Nombre</label>
			<input id="r-name" bind:value={recipeName} placeholder="Desayuno habitual" />
		</div>

		<div class="form-group">
			<label for="r-search">Añadir ingrediente</label>
			<div style="display:flex; gap:0.5rem;">
				<input id="r-search" bind:value={searchQuery} placeholder="Buscar producto..."
					onkeydown={(e) => { if (e.key === 'Enter') searchProducts(); }} style="flex:1;" />
				<button onclick={searchProducts}>Buscar</button>
			</div>
		</div>

		{#each searchResults as p (p.id)}
			<button class="btn-secondary" style="width:100%; text-align:left; margin-bottom:0.25rem; font-size:0.85rem;"
				onclick={() => addIngredient(p)}>
				+ {p.name} {#if p.brand}({p.brand}){/if}
			</button>
		{/each}

		{#if ingredients.length > 0}
			<div style="margin-top:0.75rem;">
				{#each ingredients as ing, idx}
					<div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;">
						<span style="flex:1; font-size:0.85rem;">{ing.product.name}</span>
						<input type="number" bind:value={ing.grams} min="1" step="1" style="width:5rem;" />
						<span style="font-size:0.8rem; color:var(--text-muted);">g</span>
						<button class="btn-danger" style="padding:0.2rem 0.5rem; font-size:0.75rem;" onclick={() => removeIngredient(idx)}>X</button>
					</div>
				{/each}
				{#if ingredients.length > 0}
					{@const t = totalMacros(ingredients)}
					<div style="font-size:0.85rem; color:var(--text-muted); margin-top:0.5rem;">
						Total: {t.cal} kcal · P{t.p}g · C{t.c}g · G{t.f}g
					</div>
				{/if}
			</div>
		{/if}

		{#if error}<p class="error">{error}</p>{/if}

		<div style="display:flex; gap:0.5rem; margin-top:0.75rem;">
			<button class="btn-secondary" onclick={() => { showCreate = false; ingredients = []; }} style="flex:1;">Cancelar</button>
			<button onclick={createRecipe} style="flex:2;">Guardar receta</button>
		</div>
	</div>
{:else}
	<button onclick={() => showCreate = true} style="width:100%; margin-bottom:1rem;">
		+ Nueva receta
	</button>
{/if}

{#if recipes.length === 0 && !showCreate}
	<p style="text-align:center; color:var(--text-muted); padding:2rem 0;">
		Sin recetas aún. Crea una para registrar comidas más rápido.
	</p>
{/if}

{#each recipes as recipe (recipe.id)}
	<div class="card" style="margin-bottom:0.5rem;">
		<div style="display:flex; justify-content:space-between; align-items:center;">
			<div style="font-weight:700;">{recipe.name}</div>
			<div style="display:flex; gap:0.25rem;">
				<button style="padding:0.3rem 0.6rem; font-size:0.8rem;" onclick={() => logRecipe(recipe)}>Registrar</button>
				<button class="btn-danger" style="padding:0.3rem 0.5rem; font-size:0.75rem;" onclick={() => deleteRecipe(recipe.id)}>X</button>
			</div>
		</div>
		<div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.25rem;">
			{recipe.ingredients.length} ingredientes
		</div>
	</div>
{/each}
