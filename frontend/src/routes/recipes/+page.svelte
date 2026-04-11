<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Recipe, Product, DiaryEntry } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	let recipes: Recipe[] = $state([]);
	let showCreate = $state(false);

	// Create form
	let recipeName = $state('');
	let ingredients: { product: Product; grams: number }[] = $state([]);
	let searchQuery = $state('');
	let searchResults: Product[] = $state([]);
	let error = $state('');

	// Edit state
	let editingRecipe: Recipe | null = $state(null);
	let editName = $state('');
	let editIngredients: { product: Product; grams: number }[] = $state([]);
	let editSearchQuery = $state('');
	let editSearchResults: Product[] = $state([]);
	let editError = $state('');
	let editSaving = $state(false);

	async function load() {
		recipes = await api.get<Recipe[]>('/recipes');
	}

	$effect(() => { load(); });

	async function searchProducts() {
		if (!searchQuery.trim()) return;
		searchResults = await api.get<Product[]>(`/products?q=${encodeURIComponent(searchQuery)}`);
	}

	async function searchEditProducts() {
		if (!editSearchQuery.trim()) return;
		editSearchResults = await api.get<Product[]>(`/products?q=${encodeURIComponent(editSearchQuery)}`);
	}

	function addIngredient(product: Product) {
		if (!ingredients.find(i => i.product.id === product.id)) {
			ingredients = [...ingredients, { product, grams: 100 }];
		}
		searchResults = [];
		searchQuery = '';
	}

	function addEditIngredient(product: Product) {
		if (!editIngredients.find(i => i.product.id === product.id)) {
			editIngredients = [...editIngredients, { product, grams: 100 }];
		}
		editSearchResults = [];
		editSearchQuery = '';
	}

	function removeIngredient(idx: number) {
		ingredients = ingredients.filter((_, i) => i !== idx);
	}

	function removeEditIngredient(idx: number) {
		editIngredients = editIngredients.filter((_, i) => i !== idx);
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

	function startEdit(recipe: Recipe) {
		editingRecipe = recipe;
		editName = recipe.name;
		editIngredients = recipe.ingredients.map(ing => ({ product: ing.product, grams: ing.grams }));
		editSearchQuery = '';
		editSearchResults = [];
		editError = '';
	}

	function cancelEdit() {
		editingRecipe = null;
		editIngredients = [];
	}

	async function saveEdit() {
		if (!editingRecipe) return;
		if (!editName.trim() || editIngredients.length === 0) {
			editError = 'Nombre y al menos un ingrediente requeridos';
			return;
		}
		editError = '';
		editSaving = true;
		try {
			await api.put(`/recipes/${editingRecipe.id}`, {
				name: editName,
				ingredients: editIngredients.map(i => ({ product_id: i.product.id, grams: i.grams }))
			});
			cancelEdit();
			load();
		} catch (e: unknown) {
			editError = e instanceof Error ? e.message : 'Error';
		} finally {
			editSaving = false;
		}
	}

	async function logRecipe(recipe: Recipe) {
		try {
			const now = new Date();
			const hour = now.getHours();
			let mealType = 'snack';
			if (hour >= 6 && hour < 11) mealType = 'breakfast';
			else if (hour >= 11 && hour < 16) mealType = 'lunch';
			else if (hour >= 16 && hour < 22) mealType = 'dinner';

			for (const ing of recipe.ingredients) {
				await api.post<DiaryEntry[]>('/diary', {
					product_id: ing.product_id,
					grams: ing.grams,
					meal_type: mealType,
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

<!-- Create form -->
{#if showCreate}
	<div class="card" style="margin-bottom:1rem;">
		<h2 style="margin-top:0;">Nueva receta</h2>
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
						<button class="btn-danger" style="padding:0.2rem 0.5rem; font-size:0.75rem;" onclick={() => removeIngredient(idx)}>✕</button>
					</div>
				{/each}
				<div style="font-size:0.85rem; color:var(--text-muted); margin-top:0.5rem;">
					Total: {totalMacros(ingredients).cal} kcal · P{totalMacros(ingredients).p}g · C{totalMacros(ingredients).c}g · G{totalMacros(ingredients).f}g
				</div>
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

<!-- Recipe list -->
{#each recipes as recipe (recipe.id)}
	{#if editingRecipe?.id === recipe.id}
		<!-- Edit form -->
		<div class="card" style="margin-bottom:0.75rem; border-color:var(--primary);">
			<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
				<h2 style="margin:0; font-size:1rem;">Editar receta</h2>
				<button class="btn-secondary" onclick={cancelEdit} style="font-size:0.75rem; padding:0.25rem 0.6rem;">✕ Cancelar</button>
			</div>

			<div class="form-group">
				<label for="edit-name">Nombre</label>
				<input id="edit-name" bind:value={editName} />
			</div>

			<!-- Existing edit ingredients -->
			{#if editIngredients.length > 0}
				<div style="margin-bottom:0.75rem;">
					{#each editIngredients as ing, idx}
						<div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.4rem;">
							<span style="flex:1; font-size:0.85rem;">{ing.product.name}</span>
							<input type="number" bind:value={ing.grams} min="1" step="1" style="width:5rem;" />
							<span style="font-size:0.8rem; color:var(--text-muted);">g</span>
							<button class="btn-danger" style="padding:0.2rem 0.5rem; font-size:0.75rem;" onclick={() => removeEditIngredient(idx)}>✕</button>
						</div>
					{/each}
					<div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.4rem;">
						Total: {totalMacros(editIngredients).cal} kcal · P{totalMacros(editIngredients).p}g · C{totalMacros(editIngredients).c}g · G{totalMacros(editIngredients).f}g
					</div>
				</div>
			{/if}

			<!-- Add ingredient to edit -->
			<div class="form-group" style="margin-bottom:0.5rem;">
				<label for="edit-search">Añadir ingrediente</label>
				<div style="display:flex; gap:0.5rem;">
					<input id="edit-search" bind:value={editSearchQuery} placeholder="Buscar..."
						onkeydown={(e) => { if (e.key === 'Enter') searchEditProducts(); }} style="flex:1;" />
					<button onclick={searchEditProducts} style="font-size:0.85rem; padding:0.4rem 0.7rem;">Buscar</button>
				</div>
			</div>
			{#each editSearchResults as p (p.id)}
				<button class="btn-secondary" style="width:100%; text-align:left; margin-bottom:0.25rem; font-size:0.85rem;"
					onclick={() => addEditIngredient(p)}>
					+ {p.name} {#if p.brand}({p.brand}){/if}
				</button>
			{/each}

			{#if editError}<p class="error">{editError}</p>{/if}

			<button onclick={saveEdit} disabled={editSaving} style="width:100%; margin-top:0.5rem;">
				{editSaving ? 'Guardando...' : 'Guardar cambios'}
			</button>
		</div>
	{:else}
		<!-- Normal recipe card -->
		{@const macros = totalMacros(recipe.ingredients.map(ing => ({ product: ing.product, grams: ing.grams })))}
		<div class="card" style="margin-bottom:0.5rem;">
			<!-- Tap header to expand/collapse ingredients -->
			<button
				onclick={() => startEdit(recipe)}
				style="width:100%; display:flex; justify-content:space-between; align-items:start; background:none; border:none; cursor:pointer; padding:0; margin-bottom:0.5rem; text-align:left;"
			>
				<div style="flex:1;">
					<div style="font-weight:700; font-size:0.95rem;">{recipe.name}</div>
					<div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.2rem;">
						{recipe.ingredients.length} ingrediente{recipe.ingredients.length !== 1 ? 's' : ''}
						{#each recipe.ingredients.slice(0, 3) as ing}
							· {ing.product.name.split(' ')[0]}
						{/each}{#if recipe.ingredients.length > 3}…{/if}
					</div>
				</div>
				<div style="text-align:right; margin-left:0.5rem;">
					<div style="font-size:0.85rem; color:var(--cal); font-weight:600;">{macros.cal} kcal</div>
					<div style="font-size:0.72rem; color:var(--text-muted);">P{macros.p} C{macros.c} G{macros.f}g</div>
					<div style="font-size:0.7rem; color:var(--text-muted); margin-top:0.15rem;">✏️ Editar</div>
				</div>
			</button>
			<div style="display:flex; gap:0.4rem;">
				<button onclick={() => logRecipe(recipe)} style="flex:1; font-size:0.85rem;">Registrar</button>
				<button class="btn-danger" style="flex:0; padding:0.4rem 0.65rem; font-size:0.8rem;" onclick={() => deleteRecipe(recipe.id)}>✕</button>
			</div>
		</div>
	{/if}
{/each}

{#if error && !showCreate}
	<p class="error">{error}</p>
{/if}
