<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Recipe, SharedRecipe, Product, DiaryEntry, MealType } from '$lib/types';
	import { MEAL_LABELS, MEAL_ORDER } from '$lib/types';
	import { Modal } from '$lib/components';

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

	// ── Registrar receta con selector de comida ──────────────────────────────
	let logPendingRecipe: Recipe | null = $state(null);
	let logMealType: MealType = $state(guessMealType());
	let logging = $state(false);

	function guessMealType(): MealType {
		const h = new Date().getHours();
		if (h >= 6 && h < 11) return 'breakfast';
		if (h >= 11 && h < 16) return 'lunch';
		if (h >= 16 && h < 22) return 'dinner';
		return 'snack';
	}

	function logRecipe(recipe: Recipe) {
		logMealType = guessMealType();
		logPendingRecipe = recipe;
	}

	async function confirmLog() {
		if (!logPendingRecipe) return;
		logging = true;
		error = '';
		try {
			for (const ing of logPendingRecipe.ingredients) {
				await api.post<DiaryEntry[]>('/diary', {
					product_id: ing.product_id,
					grams: ing.grams,
					meal_type: logMealType,
					consumed_at: new Date().toISOString(),
				});
			}
			logPendingRecipe = null;
			goto('/');
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		} finally {
			logging = false;
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

	function hashHue(s: string): number {
		let h = 0;
		for (const c of s) h = (h * 31 + c.charCodeAt(0)) % 360;
		return h;
	}

	function recipeGlyph(name: string): string {
		const n = name.toLowerCase();
		if (/desayun|avena|porridge/.test(n)) return '🥣';
		if (/pollo|pechug/.test(n)) return '🍗';
		if (/ensalada/.test(n)) return '🥗';
		if (/pasta|espagueti/.test(n)) return '🍝';
		if (/batido|smoothie|protein/.test(n)) return '🥤';
		if (/pescado|salmón|atún/.test(n)) return '🐟';
		if (/arroz|bowl/.test(n)) return '🍚';
		if (/tosta|pan/.test(n)) return '🥪';
		return '🍽';
	}
</script>

<!-- Header -->
<div class="page-header">
	<div>
		<div class="header-eyebrow">Biblioteca</div>
		<div class="header-title">Recetas</div>
	</div>
	<button class="btn-new" onclick={() => showCreate = !showCreate}>＋ Nueva</button>
</div>

<!-- ═══════════════════════════════════════ CREAR ═══════════════════════════ -->
{#if showCreate}
	<div class="glass-card" style="margin-bottom:1rem;">
		<h2 style="margin-top:0; font-size:1rem; color:#fff;">Nueva receta</h2>

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
			<button class="action-btn action-btn-ghost" onclick={() => { showCreate = false; ingredients = []; }} style="flex:1;">Cancelar</button>
			<button class="action-btn action-btn-primary" onclick={createRecipe} style="flex:2;">Guardar receta</button>
		</div>
	</div>
{/if}

{#if recipes.length === 0 && !showCreate}
	<div style="text-align:center; padding:2rem 0; color:rgba(255,255,255,0.4);">
		<div style="font-size:2.5rem; margin-bottom:0.5rem;">🍳</div>
		<div style="font-size:0.875rem; font-weight:600;">Sin recetas</div>
		<div style="font-size:0.75rem; margin-top:0.25rem;">Crea una para registrar comidas más rápido</div>
	</div>
{/if}

<!-- ═══════════════════════════════════════ MIS RECETAS ═════════════════════ -->
{#each recipes as recipe (recipe.id)}
	{#if editingRecipe?.id === recipe.id}
		<!-- Edición inline -->
		<div class="glass-card" style="margin-bottom:0.75rem; border-color:oklch(75% 0.18 165 / 0.4);">
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
		{@const hue = hashHue(recipe.name)}
		{@const preview = recipe.ingredients.slice(0,3).map(i => i.product.name.split(' ')[0]).join(' · ')}
		<div class="glass-card recipe-card">
			<div style="display:flex; gap:0.75rem; margin-bottom:0.75rem;">
				<!-- Emoji avatar -->
				<div class="recipe-avatar" style="background:linear-gradient(135deg, oklch(72% 0.16 {hue}), oklch(55% 0.14 {(hue+30) % 360}));">
					{recipeGlyph(recipe.name)}
				</div>
				<div style="flex:1; min-width:0;">
					<div style="display:flex; align-items:center; gap:0.375rem;">
						<span class="recipe-name">{recipe.name}</span>
						{#if recipe.is_shared}
							<span class="shared-badge">🔗</span>
						{/if}
					</div>
					<div class="recipe-sub">{recipe.ingredients.length} ing · {preview}</div>
					<div class="recipe-macros">
						<span style="color:oklch(85% 0.17 55);">{macros.cal}</span><span class="macro-unit">kcal</span>
						<span style="color:oklch(78% 0.14 220); margin-left:0.5rem;">P{macros.p}</span>
						<span style="color:oklch(78% 0.16 275);"> C{macros.c}</span>
						<span style="color:oklch(75% 0.17 25);"> G{macros.f}</span>
					</div>
				</div>
			</div>
			<div style="display:flex; gap:0.375rem;">
				<button onclick={() => logRecipe(recipe)} class="action-btn action-btn-primary" style="flex:1;">Registrar</button>
				<button class="icon-btn" onclick={() => startEdit(recipe)} title="Editar">✏️</button>
				<button class="icon-btn" onclick={() => toggleShare(recipe)} title={recipe.is_shared ? 'Dejar de compartir' : 'Compartir'}>
					{recipe.is_shared ? '🔗' : '🔒'}
				</button>
				<button class="icon-btn icon-btn-danger" onclick={() => deleteRecipe(recipe.id)} title="Borrar">✕</button>
			</div>
		</div>
	{/if}
{/each}

<!-- ═══════════════════════════════════ RECETAS DE AMIGOS ═══════════════════ -->
{#if sharedRecipes.length > 0}
	<div class="section-header" style="margin:1.25rem 0.25rem 0.625rem;">
		<div style="font-size:0.8125rem; font-weight:700; color:#fff;">De tus amigos</div>
		<div style="font-size:0.625rem; color:rgba(255,255,255,0.45);">Cópialas o regístralas</div>
	</div>
	{#each sharedRecipes as recipe (recipe.id)}
		{@const macros = totalMacros(recipe.ingredients.map(ing => ({ product: ing.product, grams: ing.grams })))}
		{@const hue = hashHue(recipe.name)}
		<div class="glass-card recipe-card">
			<div style="display:flex; gap:0.75rem; margin-bottom:0.625rem;">
				<div class="recipe-avatar" style="width:48px; height:48px; background:linear-gradient(135deg, oklch(68% 0.15 {(hue+60) % 360}), oklch(50% 0.13 {(hue+90) % 360}));">
					{recipeGlyph(recipe.name)}
				</div>
				<div style="flex:1; min-width:0;">
					<div class="recipe-name">{recipe.name}</div>
					<div class="recipe-sub">
						<span class="owner-badge">@{recipe.owner_name}</span>
						{recipe.ingredients.length} ing
					</div>
					<div class="recipe-macros">
						<span style="color:oklch(85% 0.17 55);">{macros.cal}</span><span class="macro-unit">kcal</span>
						<span style="color:oklch(78% 0.14 220); margin-left:0.5rem;">P{macros.p}</span>
						<span style="color:oklch(78% 0.16 275);"> C{macros.c}</span>
					</div>
				</div>
			</div>
			<div style="display:flex; gap:0.375rem;">
				<button onclick={() => logRecipe(recipe)} class="action-btn action-btn-ghost" style="flex:1;">Registrar</button>
				<button class="action-btn" style="padding:0 0.875rem; background:oklch(75% 0.18 295 / 0.2); color:oklch(85% 0.15 295); border:none; border-radius:10px; font-family:inherit; cursor:pointer; font-weight:700; font-size:0.75rem;"
					onclick={() => copySharedRecipe(recipe.id)}>📋 Copiar</button>
			</div>
		</div>
	{/each}
{/if}

{#if error && !showCreate}
	<p class="error">{error}</p>
{/if}

<!-- ═══════════════════════ MODAL: elegir tipo de comida ════════════════════ -->
{#if logPendingRecipe}
	<Modal onClose={() => logPendingRecipe = null} title="¿A qué comida lo añades?" subtitle={logPendingRecipe.name}>
		<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:0.4rem; margin-bottom:1rem;">
			{#each MEAL_ORDER as mt}
				<button
					onclick={() => logMealType = mt}
					class="chip"
					class:active={logMealType === mt}
					style="font-size:0.78rem;">
					{MEAL_LABELS[mt]}
				</button>
			{/each}
		</div>
		<div style="display:flex; gap:0.5rem;">
			<button class="action-btn action-btn-ghost" onclick={() => logPendingRecipe = null} style="flex:1;">Cancelar</button>
			<button class="action-btn action-btn-primary" onclick={confirmLog} disabled={logging} style="flex:2;">
				{logging ? 'Registrando...' : 'Registrar'}
			</button>
		</div>
	</Modal>
{/if}

<style>
	/* ── Header ── */
	.page-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 1rem;
	}
	.header-eyebrow {
		font-size: 0.625rem;
		letter-spacing: 0.15em;
		color: rgba(255,255,255,0.45);
		text-transform: uppercase;
		font-weight: 600;
	}
	.header-title {
		font-size: 1.25rem;
		font-weight: 800;
		color: #fff;
		letter-spacing: -0.02em;
	}
	.btn-new {
		padding: 0.625rem 0.875rem;
		border-radius: 14px;
		border: none;
		cursor: pointer;
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		font-weight: 700;
		font-size: 0.75rem;
		font-family: inherit;
		box-shadow: 0 6px 18px -4px oklch(75% 0.22 165 / 0.5), inset 0 1px 0 rgba(255,255,255,0.4);
		white-space: nowrap;
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

	/* ── Recipe card ── */
	.recipe-card { margin-bottom: 0.625rem; border-radius: 20px; }
	.recipe-avatar {
		width: 52px;
		height: 52px;
		border-radius: 14px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.375rem;
		color: #fff;
		box-shadow: inset 0 1px 0 rgba(255,255,255,0.25);
	}
	.recipe-name {
		font-size: 0.875rem;
		font-weight: 700;
		color: #fff;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.recipe-sub {
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.45);
		margin-top: 0.125rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.recipe-macros {
		display: flex;
		align-items: baseline;
		gap: 0;
		margin-top: 0.5rem;
		font-size: 0.8125rem;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}
	.macro-unit { font-size: 0.5625rem; color: rgba(255,255,255,0.4); margin-left: 0.125rem; }
	.shared-badge {
		padding: 0.0625rem 0.375rem;
		border-radius: 99px;
		background: oklch(75% 0.18 160 / 0.18);
		color: oklch(85% 0.15 160);
		font-size: 0.5625rem;
		font-weight: 700;
	}
	.owner-badge {
		display: inline-flex;
		align-items: center;
		padding: 0.0625rem 0.375rem;
		border-radius: 99px;
		background: oklch(75% 0.18 295 / 0.18);
		color: oklch(85% 0.15 295);
		font-weight: 700;
		margin-right: 0.375rem;
	}
	.section-header { padding: 0 0.25rem; }

	/* ── Action buttons ── */
	.action-btn {
		height: 36px;
		border-radius: 12px;
		border: none;
		cursor: pointer;
		font-size: 0.75rem;
		font-weight: 700;
		font-family: inherit;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0 0.875rem;
		transition: opacity 0.15s, transform 0.1s;
	}
	.action-btn:disabled { opacity: 0.6; cursor: not-allowed; }
	.action-btn-primary {
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		box-shadow: inset 0 1px 0 rgba(255,255,255,0.4);
	}
	.action-btn-ghost {
		background: rgba(255,255,255,0.06);
		color: #fff;
		border: 1px solid rgba(255,255,255,0.1) !important;
	}
	.icon-btn {
		width: 36px;
		height: 36px;
		border-radius: 12px;
		border: 1px solid rgba(255,255,255,0.08);
		cursor: pointer;
		background: rgba(255,255,255,0.05);
		color: rgba(255,255,255,0.7);
		font-size: 0.75rem;
		font-family: inherit;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: background 0.15s;
	}
	.icon-btn:hover { background: rgba(255,255,255,0.1); }
	.icon-btn-danger {
		background: oklch(65% 0.22 25 / 0.15);
		border-color: oklch(65% 0.22 25 / 0.3);
		color: oklch(78% 0.2 25);
	}
	.icon-btn-danger:hover { background: oklch(65% 0.22 25 / 0.25); }
</style>
