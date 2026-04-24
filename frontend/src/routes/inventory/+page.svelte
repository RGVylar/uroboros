<script lang="ts">
	import { goto } from '$app/navigation';
	import { Capacitor } from '@capacitor/core';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { CostSummary, InventoryItem, Product } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	let isNative = Capacitor.isNativePlatform();

	// Barcode scanner (web)
	let scanning = $state(false);
	let videoEl: HTMLVideoElement | undefined = $state();
	let scanError = $state('');
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

	let items: InventoryItem[] = $state([]);
	let cost: CostSummary | null = $state(null);
	let loading = $state(true);
	let error = $state('');

	// Add form
	let query = $state('');
	let searchResults: Product[] = $state([]);
	let searching = $state(false);
	let selectedProduct: Product | null = $state(null);
	let addQty = $state(100);
	let addPrice = $state<number | ''>('');
	let saving = $state(false);

	// Edit state
	let editingId: number | null = $state(null);
	let editQty = $state(0);
	let editPrice = $state<number | ''>('');

	// Delete confirm
	let deletingId: number | null = $state(null);

	async function load() {
		loading = true;
		try {
			[items, cost] = await Promise.all([
				api.get<InventoryItem[]>('/inventory'),
				api.get<CostSummary>('/inventory/cost-summary').catch(() => null),
			]);
		} catch {
			// ignore
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
		if (!selectedProduct) return;
		saving = true;
		error = '';
		try {
			await api.post('/inventory', {
				product_id: selectedProduct.id,
				quantity_g: addQty,
				price_per_100g: addPrice === '' ? null : addPrice,
			});
			selectedProduct = null;
			query = '';
			addQty = 100;
			addPrice = '';
			await load();
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		} finally {
			saving = false;
		}
	}

	function startEdit(item: InventoryItem) {
		editingId = item.id;
		editQty = item.quantity_g;
		editPrice = item.price_per_100g ?? '';
	}

	async function saveEdit() {
		if (editingId === null) return;
		saving = true;
		try {
			await api.patch(`/inventory/${editingId}`, {
				quantity_g: editQty,
				price_per_100g: editPrice === '' ? null : editPrice,
			});
			editingId = null;
			await load();
		} finally {
			saving = false;
		}
	}

	async function deleteItem(id: number) {
		await api.del(`/inventory/${id}`);
		deletingId = null;
		await load();
	}

	function fmtPrice(p: number | null): string {
		if (p === null) return '—';
		return (p / 100 * 100).toFixed(2).replace('.', ',') + ' €/100g';
	}

	function totalCost(item: InventoryItem): string {
		if (item.price_per_100g === null) return '';
		return ((item.price_per_100g / 100) * item.quantity_g).toFixed(2) + ' €';
	}

	let totalStock = $derived(
		items.reduce((sum, i) => sum + (i.price_per_100g !== null ? (i.price_per_100g / 100) * i.quantity_g : 0), 0)
	);

	let locationFilter = $state('Todo');
	let invQuery = $state('');
	let showAddForm = $state(false);

	let filteredItems = $derived(items.filter(i => {
		const matchesLoc = locationFilter === 'Todo';
		const matchesQ = !invQuery.trim() || i.product_name.toLowerCase().includes(invQuery.toLowerCase());
		return matchesLoc && matchesQ;
	}));
</script>

<!-- ── Header ── -->
<div style="display:flex; align-items:center; gap:0.75rem; padding:0.25rem 0 1rem;">
	<button onclick={() => goto('/settings')} style="width:36px; height:36px; border-radius:50%; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center; color:#fff; cursor:pointer; font-family:inherit; font-size:1rem; flex-shrink:0;">←</button>
	<div style="flex:1; min-width:0;">
		<h1 style="font-size:1.875rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1; margin:0; font-family:'Lora','Georgia',serif;">Inventario</h1>
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.25rem;">{items.length} productos · despensa</div>
	</div>
	<button onclick={() => showAddForm = !showAddForm} style="padding:0.5rem 0.875rem; border-radius:99px; border:none; cursor:pointer; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:700; font-size:0.75rem; font-family:inherit; white-space:nowrap;">+ Añadir</button>
</div>

<!-- ── Cost summary ── -->
{#if cost && (cost.today !== null || cost.this_week !== null || cost.this_month !== null)}
	<div class="glass-card" style="margin-bottom:0.75rem; display:grid; grid-template-columns:1fr auto 1fr auto 1fr; gap:0; align-items:center; padding:0.875rem;">
		<div style="text-align:center;">
			<div style="font-size:0.5625rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.08em;">Hoy</div>
			<div style="font-size:1.25rem; font-weight:800; color:oklch(85% 0.17 160); letter-spacing:-0.03em; margin-top:0.25rem;">{cost.today !== null ? cost.today.toFixed(2) + ' €' : '—'}</div>
		</div>
		<div style="width:1px; height:2rem; background:rgba(255,255,255,0.08);"></div>
		<div style="text-align:center;">
			<div style="font-size:0.5625rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.08em;">Semana</div>
			<div style="font-size:1.25rem; font-weight:800; color:oklch(85% 0.17 160); letter-spacing:-0.03em; margin-top:0.25rem;">{cost.this_week !== null ? cost.this_week.toFixed(2) + ' €' : '—'}</div>
		</div>
		<div style="width:1px; height:2rem; background:rgba(255,255,255,0.08);"></div>
		<div style="text-align:center;">
			<div style="font-size:0.5625rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.08em;">Mes</div>
			<div style="font-size:1.25rem; font-weight:800; color:oklch(85% 0.17 160); letter-spacing:-0.03em; margin-top:0.25rem;">{cost.this_month !== null ? cost.this_month.toFixed(2) + ' €' : '—'}</div>
		</div>
	</div>
{/if}

<!-- ── Search ── -->
<div style="position:relative; margin-bottom:0.625rem;">
	<input bind:value={invQuery} placeholder="Buscar producto…" style="width:100%; padding:0.8125rem 1rem 0.8125rem 2.625rem; border-radius:16px; font-size:0.8125rem; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); color:#fff; outline:none; font-family:inherit;" />
	<div style="position:absolute; left:0.875rem; top:50%; transform:translateY(-50%); color:rgba(255,255,255,0.4); font-size:0.875rem; pointer-events:none;">🔍</div>
</div>

<!-- ── Filter chips ── -->
<div style="display:flex; gap:0.375rem; margin-bottom:0.875rem; overflow-x:auto; scrollbar-width:none;">
	{#each ['Todo','Nevera','Despensa','Congelador'] as f}
		<button onclick={() => locationFilter = f} style="padding:0.4375rem 0.875rem; border-radius:99px; border:{locationFilter===f ? 'none' : '1px solid rgba(255,255,255,0.08)'}; background:{locationFilter===f ? 'linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170))' : 'rgba(255,255,255,0.05)'}; color:{locationFilter===f ? '#041010' : 'rgba(255,255,255,0.6)'}; font-size:0.6875rem; font-weight:700; cursor:pointer; font-family:inherit; white-space:nowrap; flex-shrink:0;">{f}</button>
	{/each}
</div>

<!-- ── Add form ── -->
{#if showAddForm}
<div class="glass-card" style="margin-bottom:0.875rem;">
	<div style="font-weight:700; font-size:0.875rem; margin-bottom:0.75rem; color:#fff;">Añadir al inventario</div>

	<div class="form-group" style="margin-bottom:0.5rem;">
		<label for="inv-search">Buscar por nombre</label>
		<div style="display:flex; gap:0.5rem;">
			<input id="inv-search" bind:value={query}
				placeholder="Arroz, pollo..."
				onkeydown={(e) => { if (e.key === 'Enter') searchProducts(); }}
				style="flex:1;" />
			<button onclick={searchProducts} disabled={searching}>Buscar</button>
		</div>
	</div>

	<!-- Barcode -->
	<div class="form-group" style="margin-bottom:0.5rem;">
		<label>Código de barras</label>
		{#if isNative}
			<button onclick={scanNative} style="width:100%;" disabled={searching}>
				📷 Escanear con cámara
			</button>
		{:else}
			<button onclick={startWebScan} style="width:100%;" disabled={scanning || searching}>
				{scanning ? 'Escaneando...' : '📷 Escanear con cámara'}
			</button>
		{/if}
		{#if scanError}<p class="error" style="margin-top:0.4rem;">{scanError}</p>{/if}
		{#if scanning}
			<div style="margin-top:0.75rem; position:relative;">
				<!-- svelte-ignore a11y_media_has_caption -->
				<video bind:this={videoEl} style="width:100%; border-radius:8px; background:#000;" playsinline></video>
				<button class="btn-danger" onclick={stopWebScan}
					style="position:absolute; top:0.5rem; right:0.5rem; padding:0.3rem 0.6rem; font-size:0.8rem;">✕</button>
			</div>
		{/if}
	</div>

	{#if searchResults.length > 0}
		<div style="border:1px solid var(--border); border-radius:8px; overflow:hidden; margin-bottom:0.5rem;">
			{#each searchResults as p (p.id)}
				<button onclick={() => selectProduct(p)}
					style="width:100%; text-align:left; padding:0.6rem 0.75rem; background:var(--surface); border:none; border-bottom:1px solid var(--border); cursor:pointer; display:block;">
					<div style="font-weight:600; font-size:0.9rem;">{p.name}</div>
					{#if p.brand}<div style="font-size:0.75rem; color:var(--text-muted);">{p.brand}</div>{/if}
					<div style="font-size:0.75rem; color:var(--text-muted);">{p.calories_per_100g} kcal/100g</div>
				</button>
			{/each}
		</div>
	{/if}

	{#if selectedProduct}
		<div style="background:var(--surface2); border-radius:8px; padding:0.5rem 0.75rem; margin-bottom:0.75rem; font-size:0.85rem;">
			<strong>{selectedProduct.name}</strong>
			{#if selectedProduct.brand}<span style="color:var(--text-muted);"> · {selectedProduct.brand}</span>{/if}
		</div>

		<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; margin-bottom:0.75rem;">
			<div class="form-group" style="margin:0;">
				<label for="inv-qty">Cantidad (g)</label>
				<input id="inv-qty" type="number" bind:value={addQty} min="1" step="1" />
			</div>
			<div class="form-group" style="margin:0;">
				<label for="inv-price">€ / 100g (opcional)</label>
				<input id="inv-price" type="number" bind:value={addPrice} min="0" step="0.01" placeholder="0.00" />
			</div>
		</div>

		{#if error}<p class="error">{error}</p>{/if}

		<div style="display:flex; gap:0.5rem;">
			<button class="btn-secondary" onclick={() => { selectedProduct = null; query = ''; }} style="flex:1;">Cancelar</button>
			<button onclick={addItem} disabled={saving} style="flex:2; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:700; border:none; border-radius:12px; cursor:pointer; font-family:inherit; padding:0.75rem;">
				{saving ? 'Guardando...' : 'Añadir al inventario'}
			</button>
		</div>
	{/if}
</div>
{/if}

<!-- ── Inventory list ── -->
{#if loading}
	<p style="text-align:center; color:rgba(255,255,255,0.4); padding:3rem 0; font-size:0.85rem;">Cargando...</p>
{:else if items.length === 0}
	<div class="glass-card" style="text-align:center; color:rgba(255,255,255,0.4); padding:2.5rem 1rem;">
		<div style="font-size:2rem; margin-bottom:0.5rem;">🥫</div>
		<div style="font-size:0.875rem; font-weight:600;">El inventario está vacío</div>
		<div style="font-size:0.75rem; margin-top:0.25rem; color:rgba(255,255,255,0.3);">Añade los alimentos que tienes en casa</div>
	</div>
{:else}
	{#if totalStock > 0}
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.4); text-align:right; margin-bottom:0.5rem; padding-right:0.25rem;">
			Valor total estimado: <strong style="color:oklch(85% 0.17 160);">{totalStock.toFixed(2)} €</strong>
		</div>
	{/if}

	<div class="glass-card" style="padding:0.375rem;">
	{#each filteredItems as item, idx (item.id)}
		{#if editingId === item.id}
			<!-- Edit mode -->
			<div style="padding:0.875rem; border-bottom:{idx < filteredItems.length-1 ? '1px solid rgba(255,255,255,0.05)' : 'none'};">
				<div style="font-weight:600; margin-bottom:0.5rem; font-size:0.875rem;">{item.product_name}</div>
				<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; margin-bottom:0.5rem;">
					<div class="form-group" style="margin:0;">
						<label>Cantidad (g)</label>
						<input type="number" bind:value={editQty} min="0" step="1" />
					</div>
					<div class="form-group" style="margin:0;">
						<label>€ / 100g</label>
						<input type="number" bind:value={editPrice} min="0" step="0.01" placeholder="—" />
					</div>
				</div>
				<div style="display:flex; gap:0.5rem;">
					<button class="btn-secondary" onclick={() => editingId = null} style="flex:1;">Cancelar</button>
					<button onclick={saveEdit} disabled={saving} style="flex:2; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:700; border:none; border-radius:12px; cursor:pointer; font-family:inherit; padding:0.625rem;">Guardar</button>
				</div>
			</div>
		{:else if deletingId === item.id}
			<!-- Delete confirm -->
			<div style="padding:0.875rem; border-bottom:{idx < filteredItems.length-1 ? '1px solid rgba(255,255,255,0.05)' : 'none'};">
				<div style="font-weight:600; margin-bottom:0.375rem; font-size:0.875rem;">{item.product_name}</div>
				<p style="font-size:0.75rem; color:rgba(255,255,255,0.5); margin:0 0 0.625rem;">¿Eliminar del inventario?</p>
				<div style="display:flex; gap:0.5rem;">
					<button class="btn-secondary" onclick={() => deletingId = null} style="flex:1;">Cancelar</button>
					<button class="btn-danger" onclick={() => deleteItem(item.id)} style="flex:1;">Eliminar</button>
				</div>
			</div>
		{:else}
			<!-- View mode -->
			<div style="display:flex; align-items:center; gap:0.75rem; padding:0.75rem 0.875rem; border-bottom:{idx < filteredItems.length-1 ? '1px solid rgba(255,255,255,0.05)' : 'none'};">
				<div style="width:40px; height:40px; border-radius:10px; background:oklch(72% 0.15 70 / 0.15); border:1px solid oklch(72% 0.15 70 / 0.25); display:flex; align-items:center; justify-content:center; font-size:1rem; flex-shrink:0;">🥫</div>
				<div style="flex:1; min-width:0;">
					<div style="font-weight:600; font-size:0.8125rem; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{item.product_name}</div>
					<div style="font-size:0.625rem; color:rgba(255,255,255,0.4); margin-top:0.125rem; display:flex; gap:0.5rem; flex-wrap:wrap;">
						{#if item.product_brand}<span>{item.product_brand}</span>{/if}
						<span>{item.calories_per_100g} kcal/100g</span>
						{#if item.price_per_100g !== null}<span style="color:oklch(85% 0.17 160);">{fmtPrice(item.price_per_100g)}</span>{/if}
					</div>
				</div>
				<div style="text-align:right; flex-shrink:0;">
					<div style="font-size:0.8125rem; font-weight:700; color:#fff;">{item.quantity_g}g</div>
					{#if item.price_per_100g !== null}
						<div style="font-size:0.625rem; color:rgba(255,255,255,0.4);">≈ {totalCost(item)}</div>
					{/if}
				</div>
				<div style="display:flex; gap:0.25rem; flex-shrink:0;">
					<button onclick={() => startEdit(item)} style="padding:0.25rem 0.5rem; font-size:0.625rem; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.6); cursor:pointer; font-family:inherit;">✏️</button>
					<button onclick={() => deletingId = item.id} style="padding:0.25rem 0.4rem; font-size:0.625rem; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.5); cursor:pointer; font-family:inherit;">✕</button>
				</div>
			</div>
		{/if}
	{/each}
	</div>
{/if}

<!-- ── Shopping list link ── -->
<div style="margin-top:1.25rem; text-align:center;">
	<button onclick={() => goto('/shopping-list')} style="display:inline-flex; align-items:center; gap:0.375rem; font-size:0.75rem; color:rgba(255,255,255,0.55); padding:0.5rem 1rem; border-radius:99px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.04); cursor:pointer; font-family:inherit;">
		🛒 Ver lista de la compra
	</button>
</div>

<!-- Bottom spacing -->
<div style="height:6rem;"></div>

<style>
	.glass-card {
		background: rgba(255,255,255,0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 20px;
		padding: 1rem;
	}
</style>
