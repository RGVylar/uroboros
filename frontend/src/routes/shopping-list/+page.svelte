<script lang="ts">
	import { goto } from '$app/navigation';
	import { onDestroy } from 'svelte';
	import { Capacitor } from '@capacitor/core';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { InventoryUnit, Product, Recipe, ShoppingListItem } from '$lib/types';
	import { Modal } from '$lib/components';
	import UnitSelector from '$lib/components/UnitSelector.svelte';

	if (!auth.isLoggedIn) goto('/login');

	let isNative = Capacitor.isNativePlatform();

	// ── Web barcode scanner ───────────────────────────────────────────────────
	let scanning = $state(false);
	let scanError = $state('');
	let videoEl: HTMLVideoElement | undefined = $state();
	let stream: MediaStream | null = null;
	let zxingReader: import('@zxing/browser').BrowserMultiFormatReader | null = null;

	async function startWebScan() {
		scanError = '';
		scanning = true;
		try {
			const { BrowserMultiFormatReader } = await import('@zxing/browser');
			zxingReader = new BrowserMultiFormatReader();
			stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
			if (videoEl) {
				videoEl.srcObject = stream;
				videoEl.play();
				zxingReader.decodeFromVideoElement(videoEl, (result) => {
					if (result) {
						stopWebScan();
						searchByBarcode(result.getText());
					}
				});
			}
		} catch (e: unknown) {
			scanError = e instanceof Error ? e.message : 'No se pudo acceder a la cámara';
			scanning = false;
		}
	}

	function stopWebScan() {
		scanning = false;
		if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
		if (zxingReader) { zxingReader.reset(); zxingReader = null; }
	}

	async function scanNative() {
		try {
			const { BarcodeScanner } = await import('@capacitor-mlkit/barcode-scanning');
			const { supported } = await BarcodeScanner.isSupported();
			if (!supported) { scanError = 'Escáner no soportado en este dispositivo'; return; }
			const granted = await BarcodeScanner.requestPermissions();
			if (granted.camera !== 'granted') { scanError = 'Permiso de cámara denegado'; return; }
			const { barcodes } = await BarcodeScanner.scan();
			if (barcodes.length > 0) searchByBarcode(barcodes[0].rawValue);
		} catch (e: unknown) {
			scanError = e instanceof Error ? e.message : 'Error del escáner';
		}
	}

	onDestroy(() => stopWebScan());

	let items: ShoppingListItem[] = $state([]);
	let loading = $state(true);

	// Manual add
	let query = $state('');
	let searchResults: Product[] = $state([]);
	let searching = $state(false);
	let selectedProduct: Product | null = $state(null);
	let addQty = $state<number | ''>(100);
	let addUnit = $state<InventoryUnit>('g');
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

	async function searchByBarcode(code: string) {
		searching = true;
		scanError = '';
		try {
			const p = await api.get<Product>(`/products/barcode/${code.trim()}`);
			selectProduct(p);
		} catch {
			scanError = 'Producto no encontrado para ese código de barras';
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
					unit: addUnit,
				});
			} else if (addMode === 'text' && freeText.trim()) {
				await api.post('/shopping-list', { name: freeText.trim(), unit: addUnit });
			} else {
				error = 'Selecciona un producto o escribe un nombre.';
				return;
			}
			selectedProduct = null;
			query = '';
			freeText = '';
			addQty = 100;
			addUnit = 'g';
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
		const u = item.unit === 'unit' ? (item.quantity_g === 1 ? 'ud' : 'uds') : (item.unit ?? 'g');
		return ` · ${item.quantity_g}${u}`;
	}

	let showAddForm = $state(false);
</script>

<!-- ── Header ── -->
<div style="display:flex; align-items:center; gap:0.75rem; padding:0.25rem 0 1rem;">
	<button onclick={() => goto('/inventory')} style="width:36px; height:36px; border-radius:50%; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center; color:#fff; cursor:pointer; font-family:inherit; font-size:1rem; flex-shrink:0;">←</button>
	<div style="flex:1; min-width:0;">
		<h1 style="font-size:1.875rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1; margin:0; font-family:'Lora','Georgia',serif;">Lista</h1>
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.25rem;">{checked.length}/{items.length} completados</div>
	</div>
	<button onclick={() => showAddForm = !showAddForm} style="padding:0.5rem 0.875rem; border-radius:99px; border:none; cursor:pointer; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:700; font-size:0.75rem; font-family:inherit; white-space:nowrap;">+ Añadir</button>
</div>

<!-- ── Progress card ── -->
{#if items.length > 0}
	<div class="glass-card" style="margin-bottom:0.75rem; display:flex; align-items:center; gap:0.875rem;">
		<div style="flex:1;">
			<div style="font-size:0.625rem; letter-spacing:0.08em; color:rgba(255,255,255,0.45); text-transform:uppercase; font-weight:700;">Progreso</div>
			<div style="display:flex; align-items:baseline; gap:0.25rem; margin-top:0.25rem;">
				<div style="font-size:2rem; font-weight:800; color:#fff; letter-spacing:-0.05em; font-family:'Lora','Georgia',serif;">{checked.length}</div>
				<div style="font-size:0.875rem; color:rgba(255,255,255,0.5);">/ {items.length}</div>
			</div>
		</div>
		<div style="flex:1;">
			<div style="height:8px; border-radius:99px; background:rgba(255,255,255,0.08); overflow:hidden;">
				<div style="height:100%; width:{items.length > 0 ? (checked.length/items.length)*100 : 0}%; background:linear-gradient(90deg, oklch(85% 0.18 160), oklch(72% 0.2 180)); border-radius:99px; transition:width 0.3s;"></div>
			</div>
			{#if checked.length > 0}
				<button onclick={clearChecked} style="font-size:0.625rem; color:rgba(255,255,255,0.4); background:none; border:none; cursor:pointer; font-family:inherit; margin-top:0.375rem; padding:0;">🗑 Limpiar comprados</button>
			{/if}
		</div>
	</div>
{/if}

<!-- ── Add form ── -->
{#if showAddForm}
	<div class="glass-card" style="margin-bottom:0.875rem;">
		<div style="font-weight:700; font-size:0.875rem; margin-bottom:0.75rem; color:#fff;">Añadir elemento</div>

		<!-- Mode tabs -->
		<div style="display:flex; padding:3px; background:rgba(255,255,255,0.04); border-radius:99px; margin-bottom:0.75rem; border:1px solid rgba(255,255,255,0.08);">
			<button onclick={() => addMode = 'product'} style="flex:1; padding:0.5rem; border-radius:99px; border:none; cursor:pointer; font-family:inherit; font-weight:700; font-size:0.75rem; background:{addMode==='product' ? 'rgba(255,255,255,0.09)' : 'transparent'}; color:{addMode==='product' ? '#fff' : 'rgba(255,255,255,0.5)'};">Por producto</button>
			<button onclick={() => addMode = 'text'} style="flex:1; padding:0.5rem; border-radius:99px; border:none; cursor:pointer; font-family:inherit; font-weight:700; font-size:0.75rem; background:{addMode==='text' ? 'rgba(255,255,255,0.09)' : 'transparent'}; color:{addMode==='text' ? '#fff' : 'rgba(255,255,255,0.5)'};">Texto libre</button>
		</div>

		{#if addMode === 'product'}
			<!-- Search + barcode (igual que /add) -->
			<div class="sl-search-glass">
				<svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true" style="color:rgba(255,255,255,0.4); flex-shrink:0; margin-right:0.375rem;">
					<circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2"/>
					<path d="M16.5 16.5l4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
				</svg>
				<input
					bind:value={query}
					placeholder="Buscar producto..."
					class="sl-search-input"
					onkeydown={(e) => { if (e.key === 'Enter') searchProducts(); }}
				/>
				<button
					onclick={isNative ? scanNative : startWebScan}
					class="sl-barcode-btn"
					aria-label="Escanear código de barras"
					disabled={scanning}
				>
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none">
						<path d="M4 6v12M7 6v12M10 6v12M13 6v12M17 6v12M20 6v12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
					</svg>
				</button>
			</div>

			{#if scanning}
				<div style="margin-bottom:0.75rem; position:relative;">
					<!-- svelte-ignore a11y_media_has_caption -->
					<video bind:this={videoEl} style="width:100%; border-radius:16px; background:#000;" playsinline></video>
					<button onclick={stopWebScan} style="position:absolute; top:0.5rem; right:0.5rem; width:32px; height:32px; border-radius:50%; background:rgba(0,0,0,0.6); border:none; color:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center;" aria-label="Detener escáner">✕</button>
				</div>
			{/if}

			{#if scanError}<p style="color:oklch(75% 0.2 25); font-size:0.75rem; margin:0 0 0.5rem;">{scanError}</p>{/if}

			{#if searchResults.length > 0}
				<div style="border-radius:12px; overflow:hidden; margin-bottom:0.5rem; border:1px solid rgba(255,255,255,0.08);">
					{#each searchResults as p (p.id)}
						<button onclick={() => selectProduct(p)} style="width:100%; text-align:left; padding:0.625rem 0.75rem; background:rgba(255,255,255,0.04); border:none; border-bottom:1px solid rgba(255,255,255,0.06); cursor:pointer; color:#fff; font-family:inherit; display:block;">
							<div style="font-weight:600; font-size:0.8125rem;">{p.name}</div>
							{#if p.brand}<div style="font-size:0.6875rem; color:rgba(255,255,255,0.45);">{p.brand}</div>{/if}
						</button>
					{/each}
				</div>
			{/if}

			{#if selectedProduct}
				<div style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:0.625rem 0.75rem; margin-bottom:0.5rem;">
					<div style="font-weight:700; font-size:0.8125rem; color:#fff;">{selectedProduct.name}</div>
					{#if selectedProduct.brand}<div style="font-size:0.7rem; color:rgba(255,255,255,0.45); margin-top:0.125rem;">{selectedProduct.brand}</div>{/if}
				</div>
				<div style="display:grid; grid-template-columns:1fr 1.5fr; gap:0.5rem; margin-bottom:0.5rem;">
					<div style="display:flex; flex-direction:column; gap:0.25rem;">
						<label for="sl-qty" style="font-size:0.6875rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.06em;">Cantidad ({addUnit === 'unit' ? 'uds' : addUnit})</label>
						<input id="sl-qty" type="number" bind:value={addQty} min="0" step="any" class="sl-field" />
					</div>
					<div style="display:flex; flex-direction:column; gap:0.25rem;">
						<UnitSelector bind:unit={addUnit} label="Unidad" size="sm" />
					</div>
				</div>
			{/if}
		{:else}
			<div style="display:flex; flex-direction:column; gap:0.25rem; margin-bottom:0.5rem;">
				<label for="sl-text" style="font-size:0.6875rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.06em;">Nombre del artículo</label>
				<input id="sl-text" bind:value={freeText} placeholder="Pan de molde, detergente..." class="sl-field" />
			</div>
		{/if}

		{#if error}<p style="color:oklch(75% 0.2 25); font-size:0.75rem; margin:0 0 0.5rem;">{error}</p>{/if}

		<div style="display:flex; gap:0.5rem; margin-top:0.5rem;">
			<button onclick={() => openRecipeModal()} style="padding:0.75rem; border-radius:12px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.7); cursor:pointer; font-family:inherit; font-size:0.75rem; white-space:nowrap;">🍳 Desde receta</button>
			<button onclick={addItem} disabled={saving} style="flex:1; height:44px; border-radius:12px; border:none; cursor:pointer; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:700; font-size:0.8125rem; font-family:inherit;">
				{saving ? '...' : '+ Añadir'}
			</button>
		</div>
	</div>
{/if}

<!-- ── Shopping list ── -->
{#if loading}
	<p style="text-align:center; color:rgba(255,255,255,0.4); padding:3rem 0; font-size:0.85rem;">Cargando...</p>
{:else}
	<!-- Pending items -->
	{#if pending.length > 0}
		<div style="font-size:0.6875rem; letter-spacing:0.08em; text-transform:uppercase; color:rgba(255,255,255,0.45); font-weight:700; margin:0 0.25rem 0.5rem;">Por comprar · {pending.length}</div>
		<div class="glass-card" style="padding:0.375rem; margin-bottom:0.875rem;">
			{#each pending as item, i (item.id)}
				<div style="display:flex; align-items:center; gap:0.75rem; padding:0.75rem 0.875rem; border-bottom:{i < pending.length-1 ? '1px solid rgba(255,255,255,0.05)' : 'none'};">
					<button onclick={() => toggleCheck(item)} style="width:22px; height:22px; border-radius:50%; border:2px solid rgba(255,255,255,0.3); background:transparent; cursor:pointer; flex-shrink:0;" aria-label="Marcar como comprado"></button>
					<div style="flex:1; min-width:0;">
						<div style="font-weight:600; font-size:0.8125rem; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{item.product_name ?? '—'}</div>
						{#if item.product_brand || item.quantity_g}
							<div style="font-size:0.625rem; color:rgba(255,255,255,0.4); margin-top:0.1rem;">{item.product_brand ?? ''}{qtyLabel(item)}</div>
						{/if}
						{#if item.source === 'recipe'}
							<span style="font-size:0.5625rem; background:rgba(255,255,255,0.08); color:rgba(255,255,255,0.5); border-radius:4px; padding:0.1rem 0.375rem;">receta</span>
						{/if}
					</div>
					<button onclick={() => deleteItem(item.id)} style="color:rgba(255,255,255,0.4); background:none; border:none; font-size:0.875rem; cursor:pointer; padding:0.25rem; flex-shrink:0;">✕</button>
				</div>
			{/each}
		</div>
	{:else if !loading}
		<div class="glass-card" style="text-align:center; color:rgba(255,255,255,0.4); padding:2.5rem 1rem;">
			<div style="font-size:2rem; margin-bottom:0.5rem;">🛍</div>
			<div style="font-size:0.875rem; font-weight:600;">Lista vacía</div>
			<div style="font-size:0.75rem; margin-top:0.25rem; color:rgba(255,255,255,0.3);">¡A por ello!</div>
		</div>
	{/if}

	<!-- Checked items -->
	{#if checked.length > 0}
		<div style="font-size:0.6875rem; letter-spacing:0.08em; text-transform:uppercase; color:rgba(255,255,255,0.45); font-weight:700; margin:0 0.25rem 0.5rem;">En el carro · {checked.length}</div>
		<div class="glass-card" style="padding:0.375rem; opacity:0.7;">
			{#each checked as item, i (item.id)}
				<div style="display:flex; align-items:center; gap:0.75rem; padding:0.75rem 0.875rem; border-bottom:{i < checked.length-1 ? '1px solid rgba(255,255,255,0.05)' : 'none'};">
					<button onclick={() => toggleCheck(item)} style="width:22px; height:22px; border-radius:50%; border:2px solid oklch(75% 0.18 165); background:oklch(75% 0.18 165 / 0.35); cursor:pointer; flex-shrink:0; display:flex; align-items:center; justify-content:center; font-size:0.625rem; color:oklch(90% 0.15 165); font-weight:800;" aria-label="Desmarcar">✓</button>
					<div style="flex:1; min-width:0;">
						<div style="font-weight:600; font-size:0.8125rem; color:rgba(255,255,255,0.6); text-decoration:line-through; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{item.product_name ?? '—'}</div>
						{#if item.quantity_g}
							<div style="font-size:0.625rem; color:rgba(255,255,255,0.35);">{item.quantity_g}g → inventario</div>
						{/if}
					</div>
					<button onclick={() => deleteItem(item.id)} style="color:rgba(255,255,255,0.3); background:none; border:none; font-size:0.875rem; cursor:pointer; padding:0.25rem; flex-shrink:0;">✕</button>
				</div>
			{/each}
		</div>
	{/if}
{/if}

<!-- Bottom spacing -->
<div style="height:6rem;"></div>

<!-- Recipe modal -->
{#if showRecipeModal}
	<Modal onClose={() => { showRecipeModal = false; generateMsg = ''; }} title="Generar desde receta" subtitle="Se añadirán los ingredientes que falten en el inventario">
		{#if generateMsg}
			<div style="background:rgba(255,255,255,0.06); border-radius:10px; padding:0.625rem 0.75rem; margin-bottom:0.75rem; font-size:0.8125rem; color:oklch(85% 0.17 160); font-weight:600;">
				{generateMsg}
			</div>
		{/if}
		{#if loadingRecipes}
			<p style="text-align:center; color:rgba(255,255,255,0.4); font-size:0.85rem;">Cargando recetas...</p>
		{:else if recipes.length === 0}
			<div style="text-align:center; padding:1.5rem 0; color:rgba(255,255,255,0.4);">
				<div style="font-size:1.5rem; margin-bottom:0.375rem;">🍳</div>
				<div style="font-size:0.8125rem;">Sin recetas. Crea una primero.</div>
			</div>
		{:else}
			{#each recipes as recipe (recipe.id)}
				<div style="display:flex; justify-content:space-between; align-items:center; padding:0.625rem 0; border-bottom:1px solid rgba(255,255,255,0.05);">
					<div>
						<div style="font-weight:600; font-size:0.8125rem;">{recipe.name}</div>
						<div style="font-size:0.6875rem; color:rgba(255,255,255,0.45);">{recipe.ingredients.length} ingredientes</div>
					</div>
					<button onclick={() => generateFromRecipe(recipe.id)} disabled={generatingId === recipe.id} style="font-size:0.75rem; padding:0.375rem 0.75rem; border-radius:10px; border:none; cursor:pointer; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:700; font-family:inherit;">
						{generatingId === recipe.id ? '...' : 'Añadir'}
					</button>
				</div>
			{/each}
		{/if}
	</Modal>
{/if}

<style>
	.glass-card {
		background: rgba(255,255,255,0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 20px;
		padding: 1rem;
	}

	/* ── Search glass (igual que /add) ── */
	.sl-search-glass {
		display: flex;
		align-items: center;
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.1);
		border-radius: 16px;
		padding: 0 0.5rem 0 0.875rem;
		margin-bottom: 0.5rem;
	}
	.sl-search-input {
		flex: 1;
		background: none;
		border: none;
		outline: none;
		color: #fff;
		font-family: inherit;
		font-size: 0.8125rem;
		padding: 0.75rem 0.25rem;
	}
	.sl-search-input::placeholder { color: rgba(255,255,255,0.35); }
	.sl-barcode-btn {
		width: 38px;
		height: 38px;
		border-radius: 12px;
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.1);
		color: oklch(85% 0.15 160);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		transition: background 0.15s;
		padding: 0;
	}
	.sl-barcode-btn:hover { background: rgba(255,255,255,0.1); }
	.sl-barcode-btn:disabled { opacity: 0.5; cursor: default; }

	/* ── Form inputs ── */
	.sl-field {
		width: 100%;
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.1);
		border-radius: 10px;
		color: #fff;
		font-family: inherit;
		font-size: 0.875rem;
		padding: 0.5rem 0.625rem;
		outline: none;
		box-sizing: border-box;
	}
	.sl-field::placeholder { color: rgba(255,255,255,0.3); }
	.sl-field:focus { border-color: rgba(255,255,255,0.25); }
</style>
