<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Product, Recipe, ShoppingListItem } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	let items: ShoppingListItem[] = $state([]);
	let loading = $state(true);

	// Manual add
	let query = $state('');
	let searchResults: Product[] = $state([]);
	let searching = $state(false);
	let selectedProduct: Product | null = $state(null);
	let addQty = $state<number | ''>(100);
	let freeText = $state('');
	let addMode: 'product' | 'text' = $state('product');
	let saving = $state(false);
	let error = $state('');

	// From recipe
	let showRecipeModal = $state(false);
	let recipes: Recipe[] = $state([]);
	let loadingRecipes = $state(false);
	let generatingId: number | null = $state(null);
	let generateMsg = $state('');

	let pending = $derived(items.filter(i => !i.is_checked));
	let checked = $derived(items.filter(i => i.is_checked));

	async function load() {
		loading = true;
		try {
			items = await api.get<ShoppingListItem[]>('/shopping-list');
		} catch {
			items = [];
		} finally {
			loading = false;
		}
	}

	$effect(() => { load(); });

	async function searchProducts() {
		if (!query.trim()) return;
		searching = true;
		try {
			searchResults = await api.get<Product[]>(`/products?q=${encodeURIComponent(query)}&limit=10&offset=0`);
		} catch {
			searchResults = [];
		} finally {
			searching = false;
		}
	}

	function selectProduct(p: Product) {
		selectedProduct = p;
		searchResults = [];
		query = p.name;
	}

	async function addItem() {
		saving = true;
		error = '';
		try {
			if (addMode === 'product' && selectedProduct) {
				await api.post('/shopping-list', {
					product_id: selectedProduct.id,
					quantity_g: addQty === '' ? null : addQty,
				});
			} else if (addMode === 'text' && freeText.trim()) {
				await api.post('/shopping-list', { name: freeText.trim() });
			} else {
				error = 'Selecciona un producto o escribe un nombre.';
				return;
			}
			selectedProduct = null;
			query = '';
			freeText = '';
			addQty = 100;
			await load();
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		} finally {
			saving = false;
		}
	}

	async function toggleCheck(item: ShoppingListItem) {
		// If checking and it has a product + qty → purchase (adds to inventory)
		if (!item.is_checked && item.product_id && item.quantity_g) {
			await api.post(`/shopping-list/${item.id}/purchase`, {});
		} else {
			await api.patch(`/shopping-list/${item.id}`, { is_checked: !item.is_checked });
		}
		await load();
	}

	async function deleteItem(id: number) {
		await api.del(`/shopping-list/${id}`);
		await load();
	}

	async function clearChecked() {
		await api.del('/shopping-list/checked');
		await load();
	}

	async function openRecipeModal() {
		showRecipeModal = true;
		loadingRecipes = true;
		try {
			recipes = await api.get<Recipe[]>('/recipes');
		} finally {
			loadingRecipes = false;
		}
	}

	async function generateFromRecipe(recipeId: number) {
		generatingId = recipeId;
		generateMsg = '';
		try {
			const created = await api.post<ShoppingListItem[]>(`/shopping-list/from-recipe/${recipeId}`, {});
			generateMsg = created.length === 0
				? '¡Tienes todo en el inventario!'
				: `${created.length} ingrediente${created.length > 1 ? 's' : ''} añadido${created.length > 1 ? 's' : ''}.`;
			await load();
		} finally {
			generatingId = null;
		}
	}

	function qtyLabel(item: ShoppingListItem): string {
		if (!item.quantity_g) return '';
		return ` · ${item.quantity_g} g`;
	}
</script>

<div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:1.25rem;">
	<button class="btn-secondary" onclick={() => goto('/settings')}
		style="padding:0.4rem 0.7rem; font-size:0.85rem;">‹</button>
	<h1 style="margin:0; font-size:1.3rem; font-weight:800;">Lista de la compra</h1>
</div>

<!-- Actions bar -->
<div style="display:flex; gap:0.5rem; margin-bottom:1rem; flex-wrap:wrap;">
	<button class="btn-secondary" onclick={openRecipeModal} style="font-size:0.85rem; flex:1;">
		🍳 Generar desde receta
	</button>
	{#if checked.length > 0}
		<button class="btn-secondary" onclick={clearChecked} style="font-size:0.85rem; flex:1;">
			🗑 Limpiar comprados ({checked.length})
		</button>
	{/if}
</div>

<!-- Add form -->
<div class="card" style="margin-bottom:1rem;">
	<div style="font-weight:700; font-size:0.9rem; margin-bottom:0.75rem;">Añadir elemento</div>

	<!-- Mode tabs -->
	<div style="display:flex; gap:0.4rem; margin-bottom:0.75rem;">
		<button
			onclick={() => addMode = 'product'}
			class:btn-secondary={addMode !== 'product'}
			style="flex:1; font-size:0.8rem; padding:0.4rem;">
			Por producto
		</button>
		<button
			onclick={() => addMode = 'text'}
			class:btn-secondary={addMode !== 'text'}
			style="flex:1; font-size:0.8rem; padding:0.4rem;">
			Texto libre
		</button>
	</div>

	{#if addMode === 'product'}
		<div class="form-group" style="margin-bottom:0.5rem;">
			<div style="display:flex; gap:0.5rem;">
				<input bind:value={query} placeholder="Buscar producto..."
					onkeydown={(e) => { if (e.key === 'Enter') searchProducts(); }}
					style="flex:1;" />
				<button onclick={searchProducts} disabled={searching}>Buscar</button>
			</div>
		</div>

		{#if searchResults.length > 0}
			<div style="border:1px solid var(--border); border-radius:8px; overflow:hidden; margin-bottom:0.5rem;">
				{#each searchResults as p (p.id)}
					<button onclick={() => selectProduct(p)}
						style="width:100%; text-align:left; padding:0.6rem 0.75rem; background:var(--surface); border:none; border-bottom:1px solid var(--border); cursor:pointer; display:block;">
						<div style="font-weight:600; font-size:0.9rem;">{p.name}</div>
						{#if p.brand}<div style="font-size:0.75rem; color:var(--text-muted);">{p.brand}</div>{/if}
					</button>
				{/each}
			</div>
		{/if}

		{#if selectedProduct}
			<div style="background:var(--surface2); border-radius:8px; padding:0.5rem 0.75rem; margin-bottom:0.5rem; font-size:0.85rem;">
				<strong>{selectedProduct.name}</strong>
			</div>
			<div class="form-group" style="margin-bottom:0.5rem;">
				<label>Cantidad (g, opcional)</label>
				<input type="number" bind:value={addQty} min="1" step="1" />
			</div>
		{/if}
	{:else}
		<div class="form-group" style="margin-bottom:0.5rem;">
			<label>Nombre del artículo</label>
			<input bind:value={freeText} placeholder="Pan de molde, detergente..." />
		</div>
	{/if}

	{#if error}<p class="error">{error}</p>{/if}

	<button onclick={addItem} disabled={saving} style="width:100%;">
		{saving ? 'Añadiendo...' : '+ Añadir a la lista'}
	</button>
</div>

<!-- Shopping list -->
{#if loading}
	<p style="text-align:center; color:var(--text-muted);">Cargando...</p>
{:else}
	<!-- Pending items -->
	{#if pending.length > 0}
		<div style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.4rem; font-weight:700;">
			Por comprar ({pending.length})
		</div>
		{#each pending as item (item.id)}
			<div class="card" style="margin-bottom:0.4rem; display:flex; align-items:center; gap:0.75rem;">
				<button
					onclick={() => toggleCheck(item)}
					style="
						width:22px; height:22px; border-radius:50%; border:2px solid var(--border-bright);
						background:transparent; cursor:pointer; flex-shrink:0;
						display:flex; align-items:center; justify-content:center;
					"
					aria-label="Marcar como comprado">
				</button>
				<div style="flex:1; min-width:0;">
					<div style="font-weight:600; font-size:0.9rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
						{item.product_name ?? '—'}
					</div>
					{#if item.product_brand || item.quantity_g}
						<div style="font-size:0.75rem; color:var(--text-muted);">
							{item.product_brand ?? ''}{qtyLabel(item)}
						</div>
					{/if}
					{#if item.source === 'recipe'}
						<span style="font-size:0.65rem; background:var(--surface2); color:var(--text-muted); border-radius:4px; padding:0.1rem 0.4rem;">receta</span>
					{/if}
				</div>
				<button onclick={() => deleteItem(item.id)}
					style="color:var(--text-muted); background:none; border:none; font-size:1rem; cursor:pointer; padding:0.2rem; flex-shrink:0;">✕</button>
			</div>
		{/each}
	{:else if !loading}
		<p style="text-align:center; color:var(--text-muted); padding:1rem 0;">
			Lista vacía. ¡A por ello! 🛍
		</p>
	{/if}

	<!-- Checked items -->
	{#if checked.length > 0}
		<div style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em; margin:1rem 0 0.4rem; font-weight:700;">
			En el carro ({checked.length})
		</div>
		{#each checked as item (item.id)}
			<div class="card" style="margin-bottom:0.4rem; display:flex; align-items:center; gap:0.75rem; opacity:0.6;">
				<button
					onclick={() => toggleCheck(item)}
					style="
						width:22px; height:22px; border-radius:50%; border:2px solid var(--primary);
						background:var(--primary); cursor:pointer; flex-shrink:0;
						display:flex; align-items:center; justify-content:center;
						font-size:0.7rem; color:#000; font-weight:800;
					"
					aria-label="Desmarcar">✓</button>
				<div style="flex:1; min-width:0;">
					<div style="font-weight:600; font-size:0.9rem; text-decoration:line-through; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
						{item.product_name ?? '—'}
					</div>
					{#if item.quantity_g}
						<div style="font-size:0.75rem; color:var(--text-muted);">{item.quantity_g} g → añadido al inventario</div>
					{/if}
				</div>
				<button onclick={() => deleteItem(item.id)}
					style="color:var(--text-muted); background:none; border:none; font-size:1rem; cursor:pointer; padding:0.2rem; flex-shrink:0;">✕</button>
			</div>
		{/each}
	{/if}
{/if}

<!-- Recipe modal -->
{#if showRecipeModal}
	<div style="
		position:fixed; inset:0; background:rgba(0,0,0,0.7);
		display:flex; align-items:flex-end; justify-content:center;
		z-index:100; padding:0 0 env(safe-area-inset-bottom,0);
	" onclick={(e) => { if (e.target === e.currentTarget) { showRecipeModal = false; generateMsg = ''; } }}>
		<div style="
			background:var(--surface); border-radius:20px 20px 0 0;
			padding:1.25rem; width:100%; max-width:480px; max-height:70vh; overflow-y:auto;
		">
			<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
				<div style="font-weight:800; font-size:1rem;">Generar desde receta</div>
				<button onclick={() => { showRecipeModal = false; generateMsg = ''; }}
					style="background:none; border:none; font-size:1.2rem; cursor:pointer; color:var(--text-muted);">✕</button>
			</div>

			<p style="font-size:0.82rem; color:var(--text-muted); margin:0 0 0.75rem;">
				Se añadirán a la lista los ingredientes que falten en tu inventario.
			</p>

			{#if generateMsg}
				<div style="background:var(--surface2); border-radius:8px; padding:0.6rem 0.75rem; margin-bottom:0.75rem; font-size:0.85rem; color:var(--primary); font-weight:600;">
					{generateMsg}
				</div>
			{/if}

			{#if loadingRecipes}
				<p style="text-align:center; color:var(--text-muted);">Cargando recetas...</p>
			{:else if recipes.length === 0}
				<p style="text-align:center; color:var(--text-muted);">No tienes recetas guardadas.</p>
			{:else}
				{#each recipes as recipe (recipe.id)}
					<div class="card" style="margin-bottom:0.5rem; display:flex; justify-content:space-between; align-items:center;">
						<div>
							<div style="font-weight:600;">{recipe.name}</div>
							<div style="font-size:0.75rem; color:var(--text-muted);">{recipe.ingredients.length} ingredientes</div>
						</div>
						<button
							onclick={() => generateFromRecipe(recipe.id)}
							disabled={generatingId === recipe.id}
							style="font-size:0.8rem; padding:0.4rem 0.75rem;">
							{generatingId === recipe.id ? '...' : 'Añadir'}
						</button>
					</div>
				{/each}
			{/if}
		</div>
	</div>
{/if}
