<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Recipe, SharedRecipe, Product, DiaryEntry } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	// ── Estado general ──────────────────────────────────────────────────────
	let recipes: Recipe[] = $state([]);
	let sharedRecipes: SharedRecipe[] = $state([]);
	let showCreate = $state(false);
	let error = $state('');

	// ── Crear receta ────────────────────────────────────────────────────────
	let recipeName = $state('');
	let ingredients: { product: Product; grams: number }[] = $state([]);
	let searchQuery = $state('');
	let searchResults: Product[] = $state([]);
	let barcodeQuery = $state('');
	let barcodeLoading = $state(false);
	let barcodeError = $state('');

	// ── Editar receta ───────────────────────────────────────────────────────
	let editingRecipe: Recipe | null = $state(null);
	let editName = $state('');
	let editIngredients: { product: Product; grams: number }[] = $state([]);
	let editSearchQuery = $state('');
	let editSearchResults: Product[] = $state([]);
	let editBarcodeQuery = $state('');
	let editBarcodeLoading = $state(false);
	let editBarcodeError = $state('');
	let editError = $state('');
	let editSaving = $state(false);

	// ── Carga ────────────────────────────────────────────────────────────────
	async function load() {
		[recipes, sharedRecipes] = await Promise.all([
			api.get<Recipe[]>('/recipes'),
			api.get<SharedRecipe[]>('/recipes/shared').catch(() => []),
		]);
	}

	$effect(() => { load(); });

	// ── Búsqueda por nombre ──────────────────────────────────────────────────
	async function searchProducts() {
		if (!searchQuery.trim()) return;
		searchResults = await api.get<Product[]>(`/products?q=${encodeURIComponent(searchQuery)}`);
	}

	async function searchEditProducts() {
		if (!editSearchQuery.trim()) return;
		editSearchResults = await api.get<Product[]>(`/products?q=${encodeURIComponent(editSearchQuery)}`);
	}

	// ── Búsqueda por código de barras ────────────────────────────────────────
	let barcodeTimer: ReturnType<typeof setTimeout> | null = null;

	function onBarcodeInput(value: string, isEdit: boolean) {
		const v = value.replace(/\D/g, '');
		if (isEdit) editBarcodeQuery = v; else barcodeQuery = v;
		if (barcodeTimer) clearTimeout(barcodeTimer);
		// EAN-8 (8), UPC-A (12), EAN-13 (13)
		if (v.length === 8 || v.length === 12 || v.length === 13) {
			barcodeTimer = setTimeout(() => fetchBarcode(v, isEdit), 300);
		}
	}

	async function fetchBarcode(code: string, isEdit: boolean) {
		if (isEdit) { editBarcodeLoading = true; editBarcodeError = ''; }
		else { barcodeLoading = true; barcodeError = ''; }
		try {
			const product = await api.get<Product>(`/products/barcode/${code}`);
			if (isEdit) {
				addEditIngredient(product);
				editBarcodeQuery = '';
			} else {
				addIngredient(product);
				barcodeQuery = '';
			}
		} catch {
			if (isEdit) editBarcodeError = 'Código no encontrado';
			else barcodeError = 'Código no encontrado';
		} finally {
			if (isEdit) editBarcodeLoading = false;
			else barcodeLoading = false;
		}
	}

	// ── Añadir / quitar ingredientes ─────────────────────────────────────────
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

	function removeIngredient(idx: number) { ingredients = ingredients.filter((_, i) => i !== idx); }
	function removeEditIngredient(idx: number) { editIngredients = editIngredients.filter((_, i) => i !== idx); }

	// ── CRUD recetas ──────────────────────────────────────────────────────────
	async function createRecipe() {
		if (!recipeName.trim() || ingredients.length === 0) {
			error = 'Nombre y al menos un ingrediente requeridos';
			return;
		}
		error = '';
		try {
			await api.post('/recipes', {
				name: recipeName,
				ingredients: ingredients.map(i => ({ product_id: i.product.id, grams: i.grams })),
				is_shared: false,
			});
			recipeName = ''; ingredients = []; showCreate = false;
			load();
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		}
	}

	function startEdit(recipe: Recipe) {
		editingRecipe = recipe;
		editName = recipe.name;
		editIngredients = recipe.ingredients.map(ing => ({ product: ing.product, grams: ing.grams }));
		editSearchQuery = ''; editSearchResults = []; editBarcodeQuery = ''; editError = '';
	}

	function cancelEdit() { editingRecipe = null; editIngredients = []; }

	async function saveEdit() {
		if (!editingRecipe) return;
		if (!editName.trim() || editIngredients.length === 0) {
			editError = 'Nombre y al menos un ingrediente requeridos';
			return;
		}
		editError = ''; editSaving = true;
		try {
			await api.put(`/recipes/${editingRecipe.id}`, {
				name: editName,
				ingredients: editIngredients.map(i => ({ product_id: i.product.id, grams: i.grams })),
				is_shared: editingRecipe.is_shared,
			});
			cancelEdit(); load();
		} catch (e: unknown) {
			editError = e instanceof Error ? e.message : 'Error';
		} finally {
			editSaving = false;
		}
	}

	async function toggleShare(recipe: Recipe) {
		await api.patch(`/recipes/${recipe.id}/share`, {});
		load();
	}

	async function copySharedRecipe(id: number) {
		await api.post(`/recipes/${id}/copy`, {});
		load();
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
					consumed_at: new Date().toISOString(),
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

	// ── Helpers ───────────────────────────────────────────────────────────────
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

	function macroLine(product: Product) {
		return `${Math.round(product.calories_per_100g)} kcal · P${Math.round(product.protein_per_100g)} C${Math.round(product.carbs_per_100g)} G${Math.round(product.fat_per_100g)} (por 100g)`;
	}
</script>

<h1>Recetas</h1>

<!-- ═══════════════════════════════════════ CREAR ═══════════════════════════ -->
{#if showCreate}
	<div class="card" style="margin-bottom:1rem;">
		<h2 style="margin-top:0; color:var(--text);">Nueva receta</h2>

		<div class="form-group">
			<label for="r-name">Nombre</label>
			<input id="r-name" bind:value={recipeName} placeholder="Desayuno habitual" />
		</div>

		<!-- Búsqueda por nombre -->
		<div class="form-group">
			<label for="r-search">Buscar por nombre</label>
			<div style="display:flex; gap:0.5rem;">
				<input id="r-search" bind:value={searchQuery} placeholder="Avena, pollo..."
					onkeydown={(e) => { if (e.key === 'Enter') searchProducts(); }} style="flex:1;" />
				<button onclick={searchProducts} style="color:black;">Buscar</button>
			</div>
		</div>

		<!-- Búsqueda por código de barras -->
		<div class="form-group">
			<label for="r-barcode">Código de barras</label>
			<div style="display:flex; gap:0.5rem; align-items:center;">
				<input id="r-barcode" value={barcodeQuery}
					oninput={(e) => onBarcodeInput((e.target as HTMLInputElement).value, false)}
					placeholder="Escanea o escribe el código..."
					inputmode="numeric" style="flex:1;" />
				{#if barcodeLoading}
					<span style="font-size:0.8rem; color:var(--text-muted);">...</span>
				{/if}
			</div>
			{#if barcodeError}<p class="error" style="margin:0.25rem 0 0;">{barcodeError}</p>{/if}
		</div>

		<!-- Resultados de búsqueda con macros -->
		{#each searchResults as p (p.id)}
			<button class="btn-secondary" style="width:100%; text-align:left; margin-bottom:0.25rem;"
				onclick={() => addIngredient(p)}>
				<div style="font-size:0.85rem; font-weight:600;">+ {p.name}{#if p.brand} <span style="font-weight:400; color:var(--text-muted);">({p.brand})</span>{/if}</div>
				<div style="font-size:0.72rem; color:var(--text-muted); margin-top:0.1rem;">{macroLine(p)}</div>
			</button>
		{/each}

		<!-- Lista de ingredientes -->
		{#if ingredients.length > 0}
			{@const m = totalMacros(ingredients)}
			<div style="margin-top:0.75rem;">
				{#each ingredients as ing, idx}
					<div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.4rem;">
						<span style="flex:1; font-size:0.85rem;">{ing.product.name}</span>
						<input type="number" bind:value={ing.grams} min="1" step="1" style="width:5rem;" />
						<span style="font-size:0.8rem; color:var(--text-muted);">g</span>
						<button class="btn-danger" style="padding:0.2rem 0.5rem; font-size:0.75rem;" onclick={() => removeIngredient(idx)}>✕</button>
					</div>
				{/each}
				<div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.4rem;">
					Total: {m.cal} kcal · P{m.p}g · C{m.c}g · G{m.f}g
				</div>
			</div>
		{/if}

		{#if error}<p class="error">{error}</p>{/if}

		<div style="display:flex; gap:0.5rem; margin-top:0.75rem;">
			<button class="btn-secondary" onclick={() => { showCreate = false; ingredients = []; }} style="flex:1;">Cancelar</button>
			<button onclick={createRecipe} style="flex:2; color:black;">Guardar receta</button>
		</div>
	</div>
{:else}
	<button onclick={() => showCreate = true} style="width:100%; margin-bottom:1rem; color:black;">
		+ Nueva receta
	</button>
{/if}

{#if recipes.length === 0 && !showCreate}
	<p style="text-align:center; color:var(--text-muted); padding:2rem 0;">
		Sin recetas aún. Crea una para registrar comidas más rápido.
	</p>
{/if}

<!-- ═══════════════════════════════════════ MIS RECETAS ═════════════════════ -->
{#each recipes as recipe (recipe.id)}
	{#if editingRecipe?.id === recipe.id}
		<!-- Edición inline -->
		<div class="card" style="margin-bottom:0.75rem; border-color:var(--primary);">
			<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
				<h2 style="margin:0; font-size:1rem; color:var(--text);">Editar receta</h2>
				<button class="btn-secondary" onclick={cancelEdit} style="font-size:0.75rem; padding:0.25rem 0.6rem;">✕</button>
			</div>

			<div class="form-group">
				<label for="edit-name">Nombre</label>
				<input id="edit-name" bind:value={editName} />
			</div>

			{#if editIngredients.length > 0}
				{@const m = totalMacros(editIngredients)}
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
						Total: {m.cal} kcal · P{m.p}g · C{m.c}g · G{m.f}g
					</div>
				</div>
			{/if}

			<!-- Buscar por nombre -->
			<div class="form-group" style="margin-bottom:0.4rem;">
				<label for="edit-search">Buscar por nombre</label>
				<div style="display:flex; gap:0.5rem;">
					<input id="edit-search" bind:value={editSearchQuery} placeholder="Buscar..."
						onkeydown={(e) => { if (e.key === 'Enter') searchEditProducts(); }} style="flex:1;" />
					<button onclick={searchEditProducts} style="font-size:0.85rem; padding:0.4rem 0.7rem; color:black;">Buscar</button>
				</div>
			</div>

			<!-- Buscar por barcode -->
			<div class="form-group" style="margin-bottom:0.5rem;">
				<label for="edit-barcode">Código de barras</label>
				<div style="display:flex; gap:0.5rem; align-items:center;">
					<input id="edit-barcode" value={editBarcodeQuery}
						oninput={(e) => onBarcodeInput((e.target as HTMLInputElement).value, true)}
						placeholder="Escanea o escribe..." inputmode="numeric" style="flex:1;" />
					{#if editBarcodeLoading}
						<span style="font-size:0.8rem; color:var(--text-muted);">...</span>
					{/if}
				</div>
				{#if editBarcodeError}<p class="error" style="margin:0.25rem 0 0;">{editBarcodeError}</p>{/if}
			</div>

			{#each editSearchResults as p (p.id)}
				<button class="btn-secondary" style="width:100%; text-align:left; margin-bottom:0.25rem;"
					onclick={() => addEditIngredient(p)}>
					<div style="font-size:0.85rem; font-weight:600;">+ {p.name}{#if p.brand} <span style="font-weight:400; color:var(--text-muted);">({p.brand})</span>{/if}</div>
					<div style="font-size:0.72rem; color:var(--text-muted); margin-top:0.1rem;">{macroLine(p)}</div>
				</button>
			{/each}

			{#if editError}<p class="error">{editError}</p>{/if}

			<button onclick={saveEdit} disabled={editSaving} style="width:100%; margin-top:0.5rem; color:black;">
				{editSaving ? 'Guardando...' : 'Guardar cambios'}
			</button>
		</div>
	{:else}
		{@const macros = totalMacros(recipe.ingredients.map(ing => ({ product: ing.product, grams: ing.grams })))}
		<div class="card" style="margin-bottom:0.5rem;">
			<button onclick={() => startEdit(recipe)}
				style="width:100%; display:flex; justify-content:space-between; align-items:start; background:none; border:none; cursor:pointer; padding:0; margin-bottom:0.5rem; text-align:left;">
				<div style="flex:1;">
					<div style="font-weight:700; font-size:0.95rem; color:var(--text);">{recipe.name}</div>
					<div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.2rem;">
						{recipe.ingredients.length} ingrediente{recipe.ingredients.length !== 1 ? 's' : ''}
						{#each recipe.ingredients.slice(0, 3) as ing}· {ing.product.name.split(' ')[0]}{/each}{#if recipe.ingredients.length > 3}…{/if}
					</div>
				</div>
				<div style="text-align:right; margin-left:0.5rem;">
					<div style="font-size:0.85rem; color:var(--cal); font-weight:600;">{macros.cal} kcal</div>
					<div style="font-size:0.72rem; color:var(--text-muted);">P{macros.p} C{macros.c} G{macros.f}g</div>
					<div style="font-size:0.7rem; color:var(--text-muted); margin-top:0.15rem;">✏️ Editar</div>
				</div>
			</button>
			<div style="display:flex; gap:0.4rem;">
				<button onclick={() => logRecipe(recipe)} style="flex:1; font-size:0.85rem; color:black;">Registrar</button>
				<button class="btn-secondary" style="font-size:0.75rem; padding:0.4rem 0.6rem;"
					title={recipe.is_shared ? 'Dejar de compartir' : 'Compartir con amigos'}
					onclick={() => toggleShare(recipe)}>
					{recipe.is_shared ? '🔗' : '🔒'}
				</button>
				<button class="btn-danger" style="padding:0.4rem 0.65rem; font-size:0.8rem;" onclick={() => deleteRecipe(recipe.id)}>✕</button>
			</div>
		</div>
	{/if}
{/each}

<!-- ═══════════════════════════════════ RECETAS DE AMIGOS ═══════════════════ -->
{#if sharedRecipes.length > 0}
	<h2 style="font-size:1rem; color:var(--text); margin-top:1.5rem; margin-bottom:0.5rem;">
		Recetas de amigos
	</h2>
	{#each sharedRecipes as recipe (recipe.id)}
		{@const macros = totalMacros(recipe.ingredients.map(ing => ({ product: ing.product, grams: ing.grams })))}
		<div class="card" style="margin-bottom:0.5rem;">
			<div style="display:flex; justify-content:space-between; align-items:start; margin-bottom:0.5rem;">
				<div style="flex:1;">
					<div style="font-weight:700; font-size:0.95rem; color:var(--text);">{recipe.name}</div>
					<div style="font-size:0.72rem; color:var(--text-muted); margin-top:0.15rem;">
						de {recipe.owner_name} · {recipe.ingredients.length} ing.
						{#each recipe.ingredients.slice(0, 2) as ing}· {ing.product.name.split(' ')[0]}{/each}{#if recipe.ingredients.length > 2}…{/if}
					</div>
				</div>
				<div style="text-align:right; margin-left:0.5rem;">
					<div style="font-size:0.85rem; color:var(--cal); font-weight:600;">{macros.cal} kcal</div>
					<div style="font-size:0.72rem; color:var(--text-muted);">P{macros.p} C{macros.c} G{macros.f}g</div>
				</div>
			</div>
			<div style="display:flex; gap:0.4rem;">
				<button onclick={() => logRecipe(recipe)} style="flex:1; font-size:0.85rem; color:black;">Registrar</button>
				<button class="btn-secondary" style="font-size:0.75rem; padding:0.4rem 0.7rem;"
					onclick={() => copySharedRecipe(recipe.id)}>📋 Copiar</button>
			</div>
		</div>
	{/each}
{/if}

{#if error && !showCreate}
	<p class="error">{error}</p>
{/if}
