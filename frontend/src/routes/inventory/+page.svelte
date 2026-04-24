<script lang="ts">
	import { goto } from '$app/navigation';
	import { Capacitor } from '@capacitor/core';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { CostSummary, InventoryItem, Product } from '$lib/types';
	import { GlassHeader, EmptyState } from '$lib/components';

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
</script>

<GlassHeader title="Inventario">
	{#snippet left()}
		<button class="btn-ghost" onclick={() => goto('/settings')} style="font-size:1.1rem; padding:0.3rem 0.6rem;">‹</button>
	{/snippet}
</GlassHeader>

<!-- Cost summary -->
{#if cost && (cost.today !== null || cost.this_week !== null || cost.this_month !== null)}
	<div class="card" style="margin-bottom:1rem; display:grid; grid-template-columns:repeat(3,1fr); gap:0.5rem; text-align:center;">
		<div>
			<div style="font-size:0.7rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.04em;">Hoy</div>
			<div style="font-weight:700; color:var(--primary);">{cost.today !== null ? cost.today.toFixed(2) + ' €' : '—'}</div>
		</div>
		<div>
			<div style="font-size:0.7rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.04em;">Semana</div>
			<div style="font-weight:700; color:var(--primary);">{cost.this_week !== null ? cost.this_week.toFixed(2) + ' €' : '—'}</div>
		</div>
		<div>
			<div style="font-size:0.7rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.04em;">Mes</div>
			<div style="font-weight:700; color:var(--primary);">{cost.this_month !== null ? cost.this_month.toFixed(2) + ' €' : '—'}</div>
		</div>
	</div>
{/if}

<!-- Add form -->
<div class="card" style="margin-bottom:1rem;">
	<div style="font-weight:700; font-size:0.9rem; margin-bottom:0.75rem;">Añadir al inventario</div>

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
			<button onclick={addItem} disabled={saving} style="flex:2;">
				{saving ? 'Guardando...' : 'Añadir al inventario'}
			</button>
		</div>
	{/if}
</div>

<!-- Inventory list -->
{#if loading}
	<p style="text-align:center; color:var(--text-muted);">Cargando...</p>
{:else if items.length === 0}
	<p style="text-align:center; color:var(--text-muted); padding:1.5rem 0;">
		El inventario está vacío.<br />Añade los alimentos que tienes en casa.
	</p>
{:else}
	{#if totalStock > 0}
		<div style="font-size:0.8rem; color:var(--text-muted); text-align:right; margin-bottom:0.5rem;">
			Valor total estimado: <strong style="color:var(--text);">{totalStock.toFixed(2)} €</strong>
		</div>
	{/if}

	{#each items as item (item.id)}
		<div class="card" style="margin-bottom:0.5rem;">
			{#if editingId === item.id}
				<!-- Edit mode -->
				<div style="font-weight:600; margin-bottom:0.5rem;">{item.product_name}</div>
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
					<button onclick={saveEdit} disabled={saving} style="flex:2;">Guardar</button>
				</div>
			{:else if deletingId === item.id}
				<!-- Delete confirm -->
				<div style="font-weight:600; margin-bottom:0.5rem;">{item.product_name}</div>
				<p style="font-size:0.85rem; color:var(--text-muted); margin:0 0 0.75rem;">¿Eliminar del inventario?</p>
				<div style="display:flex; gap:0.5rem;">
					<button class="btn-secondary" onclick={() => deletingId = null} style="flex:1;">Cancelar</button>
					<button class="btn-danger" onclick={() => deleteItem(item.id)} style="flex:1;">Eliminar</button>
				</div>
			{:else}
				<!-- View mode -->
				<div style="display:flex; justify-content:space-between; align-items:start;">
					<div style="flex:1; min-width:0;">
						<div style="font-weight:600; font-size:0.95rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
							{item.product_name}
						</div>
						{#if item.product_brand}
							<div style="font-size:0.75rem; color:var(--text-muted);">{item.product_brand}</div>
						{/if}
						<div style="font-size:0.8rem; margin-top:0.25rem; display:flex; gap:0.75rem; flex-wrap:wrap;">
							<span style="color:var(--cal);">{item.quantity_g} g</span>
							<span style="color:var(--text-muted);">{item.calories_per_100g} kcal/100g</span>
							{#if item.price_per_100g !== null}
								<span style="color:var(--primary);">{fmtPrice(item.price_per_100g)}</span>
								<span style="color:var(--text-muted);">≈ {totalCost(item)}</span>
							{/if}
						</div>
					</div>
					<div style="display:flex; gap:0.35rem; margin-left:0.5rem; flex-shrink:0;">
						<button class="btn-secondary" onclick={() => startEdit(item)}
							style="padding:0.3rem 0.5rem; font-size:0.75rem;">Editar</button>
						<button class="btn-danger" onclick={() => deletingId = item.id}
							style="padding:0.3rem 0.5rem; font-size:0.75rem;">✕</button>
					</div>
				</div>
			{/if}
		</div>
	{/each}
{/if}

<!-- Link to shopping list -->
<div style="margin-top:1.5rem; text-align:center;">
	<button class="btn-secondary" onclick={() => goto('/shopping-list')} style="font-size:0.85rem;">
		🛒 Ver lista de la compra
	</button>
</div>
