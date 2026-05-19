<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type {
		CostSummary,
		InventoryItem,
		InventoryLocation,
		InventoryUnit,
		Product,
	} from '$lib/types';
	import BarcodeScanner from '$lib/components/BarcodeScanner.svelte';
	import LocationPicker from '$lib/components/LocationPicker.svelte';
	import UnitSelector from '$lib/components/UnitSelector.svelte';
	import ConsumeFoodModal from '$lib/components/ConsumeFoodModal.svelte';

	if (!auth.isLoggedIn) goto('/login');

	// ── State ────────────────────────────────────────────────────────────────
	let items: InventoryItem[] = $state([]);
	let cost: CostSummary | null = $state(null);
	let loading = $state(true);
	let error = $state('');
	let scanError = $state('');

	// Add form
	let query = $state('');
	let searchResults: Product[] = $state([]);
	let searching = $state(false);
	let selectedProduct: Product | null = $state(null);
	let addQty = $state(100);
	let addUnit = $state<InventoryUnit>('g');
	let addLocation = $state<InventoryLocation>('pantry');
	let addPrice = $state<number | ''>('');
	let saving = $state(false);
	let showAddForm = $state(false);

	// Manual product creation
	let showManual = $state(false);
	let manualName = $state('');
	let manualBrand = $state('');
	let manualCal = $state<number | ''>(0);
	let manualProt = $state<number | ''>(0);
	let manualCarbs = $state<number | ''>(0);
	let manualFat = $state<number | ''>(0);
	let creatingManual = $state(false);

	// Edit state
	let editingId: number | null = $state(null);
	let editQty = $state(0);
	let editUnit = $state<InventoryUnit>('g');
	let editLocation = $state<InventoryLocation>('pantry');
	let editPrice = $state<number | ''>('');

	// Delete confirm
	let deletingId: number | null = $state(null);

	// Consume modal
	let consumingItem: InventoryItem | null = $state(null);

	// Filters
	let locationFilter = $state<'Todo' | InventoryLocation>('Todo');
	let invQuery = $state('');

	const LOCATION_LABEL: Record<InventoryLocation, string> = {
		pantry: 'Despensa',
		fridge: 'Nevera',
		freezer: 'Congelador',
	};

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

	$effect(() => {
		load();
	});

	// ── Barcode + Search ─────────────────────────────────────────────────────
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

	async function searchProducts() {
		if (!query.trim()) return;
		searching = true;
		try {
			searchResults = await api.get<Product[]>(
				`/products?q=${encodeURIComponent(query)}&limit=10&offset=0`
			);
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

	async function createManualProduct() {
		if (!manualName.trim()) {
			error = 'Falta el nombre';
			return;
		}
		creatingManual = true;
		error = '';
		try {
			const p = await api.post<Product>('/products', {
				name: manualName.trim(),
				brand: manualBrand.trim() || null,
				calories_per_100g: manualCal === '' ? 0 : manualCal,
				protein_per_100g: manualProt === '' ? 0 : manualProt,
				carbs_per_100g: manualCarbs === '' ? 0 : manualCarbs,
				fat_per_100g: manualFat === '' ? 0 : manualFat,
			});
			selectProduct(p);
			showManual = false;
			// reset manual fields
			manualName = '';
			manualBrand = '';
			manualCal = 0;
			manualProt = 0;
			manualCarbs = 0;
			manualFat = 0;
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'No se pudo crear el producto';
		} finally {
			creatingManual = false;
		}
	}

	// ── CRUD ─────────────────────────────────────────────────────────────────
	async function addItem() {
		if (!selectedProduct) return;
		saving = true;
		error = '';
		try {
			await api.post('/inventory', {
				product_id: selectedProduct.id,
				quantity_base: addQty,
				unit: addUnit,
				location: addLocation,
				price_per_100g: addPrice === '' ? null : addPrice,
			});
			selectedProduct = null;
			query = '';
			addQty = 100;
			addUnit = 'g';
			addLocation = 'pantry';
			addPrice = '';
			showAddForm = false;
			await load();
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		} finally {
			saving = false;
		}
	}

	function startEdit(item: InventoryItem) {
		editingId = item.id;
		editQty = item.quantity_base;
		editUnit = item.unit;
		editLocation = item.location;
		editPrice = item.price_per_100g ?? '';
	}

	async function saveEdit() {
		if (editingId === null) return;
		saving = true;
		try {
			await api.patch(`/inventory/${editingId}`, {
				quantity_base: editQty,
				unit: editUnit,
				location: editLocation,
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
		return p.toFixed(2).replace('.', ',') + ' €/100g';
	}

	function totalCost(item: InventoryItem): string {
		if (item.price_per_100g === null) return '';
		return ((item.price_per_100g / 100) * item.quantity_g).toFixed(2) + ' €';
	}

	function fmtQty(item: InventoryItem): string {
		const qty = item.quantity_base;
		const unit = item.unit === 'unit' ? (qty === 1 ? ' ud' : ' uds') : item.unit;
		return `${qty.toLocaleString()} ${unit}`;
	}

	let totalStock = $derived(
		items.reduce(
			(sum, i) =>
				sum +
				(i.price_per_100g !== null ? (i.price_per_100g / 100) * i.quantity_g : 0),
			0
		)
	);

	let filteredItems = $derived(
		items.filter((i) => {
			const matchesLoc = locationFilter === 'Todo' || i.location === locationFilter;
			const matchesQ =
				!invQuery.trim() ||
				i.product_name.toLowerCase().includes(invQuery.toLowerCase());
			return matchesLoc && matchesQ;
		})
	);

	function onConsumed(updated: InventoryItem) {
		// Update the local list with the new quantities
		items = items.map((i) => (i.id === updated.id ? updated : i));
	}
</script>

<!-- ── Header ── -->
<div
	style="display:flex; align-items:center; gap:0.75rem; padding:0.25rem 0 1rem;"
>
	<button
		onclick={() => goto('/settings')}
		style="width:36px; height:36px; border-radius:50%; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center; color:#fff; cursor:pointer; font-family:inherit; font-size:1rem; flex-shrink:0;"
	>
		←
	</button>
	<div style="flex:1; min-width:0;">
		<h1
			style="font-size:1.875rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1; margin:0; font-family:'Lora','Georgia',serif;"
		>
			Inventario
		</h1>
		<div
			style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.25rem;"
		>
			{items.length} productos
		</div>
	</div>
	<button
		onclick={() => (showAddForm = !showAddForm)}
		style="padding:0.5rem 0.875rem; border-radius:99px; border:none; cursor:pointer; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:700; font-size:0.75rem; font-family:inherit; white-space:nowrap;"
	>
		+ Añadir
	</button>
</div>

<!-- ── Cost summary ── -->
{#if cost && (cost.today !== null || cost.this_week !== null || cost.this_month !== null)}
	<div
		class="glass-card"
		style="margin-bottom:0.75rem; display:grid; grid-template-columns:1fr auto 1fr auto 1fr; gap:0; align-items:center; padding:0.875rem;"
	>
		<div style="text-align:center;">
			<div
				style="font-size:0.5625rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.08em;"
			>
				Hoy
			</div>
			<div
				style="font-size:1.25rem; font-weight:800; color:oklch(85% 0.17 160); letter-spacing:-0.03em; margin-top:0.25rem;"
			>
				{cost.today !== null ? cost.today.toFixed(2) + ' €' : '—'}
			</div>
		</div>
		<div style="width:1px; height:2rem; background:rgba(255,255,255,0.08);"></div>
		<div style="text-align:center;">
			<div
				style="font-size:0.5625rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.08em;"
			>
				Semana
			</div>
			<div
				style="font-size:1.25rem; font-weight:800; color:oklch(85% 0.17 160); letter-spacing:-0.03em; margin-top:0.25rem;"
			>
				{cost.this_week !== null ? cost.this_week.toFixed(2) + ' €' : '—'}
			</div>
		</div>
		<div style="width:1px; height:2rem; background:rgba(255,255,255,0.08);"></div>
		<div style="text-align:center;">
			<div
				style="font-size:0.5625rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.08em;"
			>
				Mes
			</div>
			<div
				style="font-size:1.25rem; font-weight:800; color:oklch(85% 0.17 160); letter-spacing:-0.03em; margin-top:0.25rem;"
			>
				{cost.this_month !== null ? cost.this_month.toFixed(2) + ' €' : '—'}
			</div>
		</div>
	</div>
{/if}

<!-- ── Search ── -->
<div style="position:relative; margin-bottom:0.625rem;">
	<input
		bind:value={invQuery}
		placeholder="Buscar producto…"
		style="width:100%; padding:0.8125rem 1rem 0.8125rem 2.625rem; border-radius:16px; font-size:0.8125rem; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); color:#fff; outline:none; font-family:inherit;"
	/>
	<div
		style="position:absolute; left:0.875rem; top:50%; transform:translateY(-50%); color:rgba(255,255,255,0.4); font-size:0.875rem; pointer-events:none;"
	>
		🔍
	</div>
</div>

<!-- ── Filter chips ── -->
<div
	style="display:flex; gap:0.375rem; margin-bottom:0.875rem; overflow-x:auto; scrollbar-width:none;"
>
	{#each ['Todo', 'fridge', 'pantry', 'freezer'] as f}
		{@const label = f === 'Todo' ? 'Todo' : LOCATION_LABEL[f as InventoryLocation]}
		<button
			onclick={() => (locationFilter = f as 'Todo' | InventoryLocation)}
			style="padding:0.4375rem 0.875rem; border-radius:99px; border:{locationFilter ===
			f
				? 'none'
				: '1px solid rgba(255,255,255,0.08)'}; background:{locationFilter === f
				? 'linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170))'
				: 'rgba(255,255,255,0.05)'}; color:{locationFilter === f
				? '#041010'
				: 'rgba(255,255,255,0.6)'}; font-size:0.6875rem; font-weight:700; cursor:pointer; font-family:inherit; white-space:nowrap; flex-shrink:0;"
		>
			{label}
		</button>
	{/each}
</div>

<!-- ── Add form ── -->
{#if showAddForm}
	<div class="glass-card" style="margin-bottom:0.875rem;">
		<div
			style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem;"
		>
			<div style="font-weight:700; font-size:0.875rem; color:#fff;">
				{showManual ? 'Nuevo producto' : 'Añadir al inventario'}
			</div>
			{#if !selectedProduct}
				<button
					onclick={() => {
						showManual = !showManual;
						if (showManual) {
							searchResults = [];
							query = '';
						}
					}}
					style="padding:0.3125rem 0.625rem; border-radius:99px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.7); font-family:inherit; font-size:0.6875rem; font-weight:700; cursor:pointer;"
				>
					{showManual ? '← Buscar' : '✏️ Manual'}
				</button>
			{/if}
		</div>

		{#if showManual}
			<!-- Manual product creation form -->
			<div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:0.75rem;">
				<div style="display:flex; flex-direction:column; gap:0.25rem;">
					<label
						for="m-name"
						style="font-size:0.6875rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.06em;"
					>Nombre *</label>
					<input
						id="m-name"
						bind:value={manualName}
						placeholder="Ej. Garbanzos cocidos"
						class="inv-field"
					/>
				</div>
				<div style="display:flex; flex-direction:column; gap:0.25rem;">
					<label
						for="m-brand"
						style="font-size:0.6875rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.06em;"
					>Marca (opcional)</label>
					<input
						id="m-brand"
						bind:value={manualBrand}
						placeholder="Ej. Mercadona"
						class="inv-field"
					/>
				</div>
				<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem;">
					<div style="display:flex; flex-direction:column; gap:0.25rem;">
						<label
							style="font-size:0.6875rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.06em;"
						>Kcal / 100g</label>
						<input type="number" bind:value={manualCal} min="0" step="any" class="inv-field" />
					</div>
					<div style="display:flex; flex-direction:column; gap:0.25rem;">
						<label
							style="font-size:0.6875rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.06em;"
						>Proteína / 100g</label>
						<input type="number" bind:value={manualProt} min="0" step="any" class="inv-field" />
					</div>
					<div style="display:flex; flex-direction:column; gap:0.25rem;">
						<label
							style="font-size:0.6875rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.06em;"
						>Carbs / 100g</label>
						<input type="number" bind:value={manualCarbs} min="0" step="any" class="inv-field" />
					</div>
					<div style="display:flex; flex-direction:column; gap:0.25rem;">
						<label
							style="font-size:0.6875rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.06em;"
						>Grasa / 100g</label>
						<input type="number" bind:value={manualFat} min="0" step="any" class="inv-field" />
					</div>
				</div>
				{#if error}
					<p style="color:oklch(75% 0.2 25); font-size:0.75rem; margin:0;">{error}</p>
				{/if}
				<button
					onclick={createManualProduct}
					disabled={creatingManual || !manualName.trim()}
					style="margin-top:0.25rem; padding:0.75rem; border-radius:12px; border:none; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-family:inherit; font-weight:700; font-size:0.8125rem; cursor:pointer;"
				>
					{creatingManual ? 'Creando...' : '+ Crear producto'}
				</button>
			</div>
		{:else}
			<!-- Search + barcode -->
			<BarcodeScanner
				bind:bind_query={query}
				placeholder="Buscar arroz, pollo..."
				onScan={searchByBarcode}
				onSearch={searchProducts}
			/>
		{/if}

		{#if scanError}
			<p style="color:oklch(75% 0.2 25); font-size:0.75rem; margin:0 0 0.5rem;">
				{scanError}
			</p>
		{/if}

		{#if searchResults.length > 0}
			<div
				style="border-radius:12px; overflow:hidden; margin-bottom:0.5rem; border:1px solid rgba(255,255,255,0.08);"
			>
				{#each searchResults as p (p.id)}
					<button
						onclick={() => selectProduct(p)}
						style="width:100%; text-align:left; padding:0.625rem 0.75rem; background:rgba(255,255,255,0.04); border:none; border-bottom:1px solid rgba(255,255,255,0.06); cursor:pointer; font-family:inherit;"
					>
						<div style="font-weight:600; font-size:0.8125rem; color:#fff;">
							{p.name}
						</div>
						{#if p.brand}
							<div style="font-size:0.7rem; color:rgba(255,255,255,0.45);">
								{p.brand}
							</div>
						{/if}
						<div style="font-size:0.7rem; color:rgba(255,255,255,0.4);">
							{p.calories_per_100g} kcal/100g
						</div>
					</button>
				{/each}
			</div>
		{/if}

		{#if selectedProduct}
			<div
				style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:0.625rem 0.75rem; margin-bottom:0.75rem;"
			>
				<div style="font-weight:700; font-size:0.8125rem; color:#fff;">
					{selectedProduct.name}
				</div>
				{#if selectedProduct.brand}
					<div
						style="font-size:0.7rem; color:rgba(255,255,255,0.45); margin-top:0.125rem;"
					>
						{selectedProduct.brand} · {selectedProduct.calories_per_100g} kcal/100g
					</div>
				{/if}
			</div>

			<!-- Location -->
			<div style="margin-bottom:0.75rem;">
				<LocationPicker bind:location={addLocation} label="Ubicación" />
			</div>

			<!-- Unit -->
			<div style="margin-bottom:0.75rem;">
				<UnitSelector bind:unit={addUnit} label="Unidad" />
			</div>

			<!-- Quantity + price -->
			<div
				style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; margin-bottom:0.75rem;"
			>
				<div style="display:flex; flex-direction:column; gap:0.25rem;">
					<label
						for="inv-qty"
						style="font-size:0.6875rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.06em;"
					>
						Cantidad ({addUnit === 'unit' ? 'uds' : addUnit})
					</label>
					<input
						id="inv-qty"
						type="number"
						bind:value={addQty}
						min="0"
						step="any"
						class="inv-field"
					/>
				</div>
				<div style="display:flex; flex-direction:column; gap:0.25rem;">
					<label
						for="inv-price"
						style="font-size:0.6875rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.06em;"
					>
						€ / 100g
						<span style="font-weight:400; text-transform:none;">(opc.)</span>
					</label>
					<input
						id="inv-price"
						type="number"
						bind:value={addPrice}
						min="0"
						step="0.01"
						placeholder="0.00"
						class="inv-field"
					/>
				</div>
			</div>

			{#if error}
				<p
					style="color:oklch(75% 0.2 25); font-size:0.75rem; margin:0 0 0.5rem;"
				>
					{error}
				</p>
			{/if}

			<div style="display:flex; gap:0.5rem;">
				<button
					onclick={() => {
						selectedProduct = null;
						query = '';
						searchResults = [];
					}}
					style="flex:1; padding:0.75rem; border-radius:12px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.7); font-family:inherit; font-size:0.8125rem; font-weight:600; cursor:pointer;"
				>
					Cancelar
				</button>
				<button
					onclick={addItem}
					disabled={saving}
					style="flex:2; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:700; border:none; border-radius:12px; cursor:pointer; font-family:inherit; padding:0.75rem; font-size:0.8125rem;"
				>
					{saving ? 'Guardando...' : 'Añadir al inventario'}
				</button>
			</div>
		{/if}
	</div>
{/if}

<!-- ── Inventory list ── -->
{#if loading}
	<p
		style="text-align:center; color:rgba(255,255,255,0.4); padding:3rem 0; font-size:0.85rem;"
	>
		Cargando...
	</p>
{:else if items.length === 0}
	<div
		class="glass-card"
		style="text-align:center; color:rgba(255,255,255,0.4); padding:2.5rem 1rem;"
	>
		<div style="font-size:2rem; margin-bottom:0.5rem;">🥫</div>
		<div style="font-size:0.875rem; font-weight:600;">El inventario está vacío</div>
		<div
			style="font-size:0.75rem; margin-top:0.25rem; color:rgba(255,255,255,0.3);"
		>
			Añade los alimentos que tienes en casa
		</div>
	</div>
{:else}
	{#if totalStock > 0}
		<div
			style="font-size:0.6875rem; color:rgba(255,255,255,0.4); text-align:right; margin-bottom:0.5rem; padding-right:0.25rem;"
		>
			Valor total estimado: <strong style="color:oklch(85% 0.17 160);"
				>{totalStock.toFixed(2)} €</strong
			>
		</div>
	{/if}

	<div class="glass-card" style="padding:0.375rem;">
		{#each filteredItems as item, idx (item.id)}
			{#if editingId === item.id}
				<!-- Edit mode -->
				<div
					style="padding:0.875rem; border-bottom:{idx < filteredItems.length - 1
						? '1px solid rgba(255,255,255,0.05)'
						: 'none'};"
				>
					<div style="font-weight:600; margin-bottom:0.5rem; font-size:0.875rem;">
						{item.product_name}
					</div>
					<div style="margin-bottom:0.5rem;">
						<LocationPicker bind:location={editLocation} size="sm" />
					</div>
					<div style="margin-bottom:0.5rem;">
						<UnitSelector bind:unit={editUnit} size="sm" />
					</div>
					<div
						style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; margin-bottom:0.5rem;"
					>
						<div class="form-group" style="margin:0;">
							<label
								style="font-size:0.6875rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase;"
							>Cantidad ({editUnit === 'unit' ? 'uds' : editUnit})</label>
							<input
								type="number"
								bind:value={editQty}
								min="0"
								step="any"
								class="inv-field"
							/>
						</div>
						<div class="form-group" style="margin:0;">
							<label
								style="font-size:0.6875rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase;"
							>€ / 100g</label>
							<input
								type="number"
								bind:value={editPrice}
								min="0"
								step="0.01"
								placeholder="—"
								class="inv-field"
							/>
						</div>
					</div>
					<div style="display:flex; gap:0.5rem;">
						<button
							onclick={() => (editingId = null)}
							style="flex:1; padding:0.5rem; border-radius:10px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.7); font-family:inherit; font-size:0.75rem; cursor:pointer;"
						>
							Cancelar
						</button>
						<button
							onclick={saveEdit}
							disabled={saving}
							style="flex:2; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:700; border:none; border-radius:10px; cursor:pointer; font-family:inherit; padding:0.5rem; font-size:0.75rem;"
						>
							Guardar
						</button>
					</div>
				</div>
			{:else if deletingId === item.id}
				<!-- Delete confirm -->
				<div
					style="padding:0.875rem; border-bottom:{idx < filteredItems.length - 1
						? '1px solid rgba(255,255,255,0.05)'
						: 'none'};"
				>
					<div style="font-weight:600; margin-bottom:0.375rem; font-size:0.875rem;">
						{item.product_name}
					</div>
					<p
						style="font-size:0.75rem; color:rgba(255,255,255,0.5); margin:0 0 0.625rem;"
					>
						¿Eliminar del inventario?
					</p>
					<div style="display:flex; gap:0.5rem;">
						<button
							onclick={() => (deletingId = null)}
							style="flex:1; padding:0.5rem; border-radius:10px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.7); font-family:inherit; font-size:0.75rem; cursor:pointer;"
						>
							Cancelar
						</button>
						<button
							onclick={() => deleteItem(item.id)}
							style="flex:1; padding:0.5rem; border-radius:10px; border:1px solid oklch(60% 0.22 25 / 0.4); background:oklch(55% 0.22 25 / 0.25); color:oklch(85% 0.17 25); font-family:inherit; font-size:0.75rem; cursor:pointer;"
						>
							Eliminar
						</button>
					</div>
				</div>
			{:else}
				<!-- View mode -->
				<div
					style="display:flex; align-items:center; gap:0.625rem; padding:0.75rem 0.75rem; border-bottom:{idx <
					filteredItems.length - 1
						? '1px solid rgba(255,255,255,0.05)'
						: 'none'};"
				>
					<div
						style="width:38px; height:38px; border-radius:10px; background:oklch(72% 0.15 70 / 0.15); border:1px solid oklch(72% 0.15 70 / 0.25); display:flex; align-items:center; justify-content:center; font-size:1rem; flex-shrink:0;"
					>
						{item.location === 'fridge' ? '❄️' : item.location === 'freezer' ? '🧊' : '🏠'}
					</div>
					<div style="flex:1; min-width:0;">
						<div
							style="font-weight:600; font-size:0.8125rem; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"
						>
							{item.product_name}
						</div>
						<div
							style="font-size:0.625rem; color:rgba(255,255,255,0.4); margin-top:0.125rem; display:flex; gap:0.5rem; flex-wrap:wrap;"
						>
							{#if item.product_brand}<span>{item.product_brand}</span>{/if}
							<span>{item.calories_per_100g} kcal/100g</span>
							{#if item.price_per_100g !== null}
								<span style="color:oklch(85% 0.17 160);">
									{fmtPrice(item.price_per_100g)}
								</span>
							{/if}
						</div>
					</div>
					<div style="text-align:right; flex-shrink:0; min-width:55px;">
						<div style="font-size:0.8125rem; font-weight:700; color:#fff;">
							{fmtQty(item)}
						</div>
						{#if item.price_per_100g !== null}
							<div style="font-size:0.625rem; color:rgba(255,255,255,0.4);">
								≈ {totalCost(item)}
							</div>
						{/if}
					</div>
					<div style="display:flex; gap:0.1875rem; flex-shrink:0;">
						<button
							onclick={() => (consumingItem = item)}
							title="Consumir del inventario"
							style="padding:0.25rem 0.4rem; font-size:0.625rem; border-radius:8px; border:1px solid oklch(75% 0.18 165 / 0.35); background:oklch(75% 0.18 165 / 0.15); color:oklch(85% 0.17 160); cursor:pointer; font-family:inherit;"
						>
							−
						</button>
						<button
							onclick={() => startEdit(item)}
							style="padding:0.25rem 0.4rem; font-size:0.625rem; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.6); cursor:pointer; font-family:inherit;"
						>
							✏️
						</button>
						<button
							onclick={() => (deletingId = item.id)}
							style="padding:0.25rem 0.4rem; font-size:0.625rem; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.5); cursor:pointer; font-family:inherit;"
						>
							✕
						</button>
					</div>
				</div>
			{/if}
		{/each}
	</div>
{/if}

<!-- ── Consume modal ── -->
{#if consumingItem}
	<ConsumeFoodModal
		item={consumingItem}
		onclose={() => (consumingItem = null)}
		onconsumed={onConsumed}
	/>
{/if}

<!-- ── Shopping list link ── -->
<div style="margin-top:1.25rem; text-align:center;">
	<button
		onclick={() => goto('/shopping-list')}
		style="display:inline-flex; align-items:center; gap:0.375rem; font-size:0.75rem; color:rgba(255,255,255,0.55); padding:0.5rem 1rem; border-radius:99px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.04); cursor:pointer; font-family:inherit;"
	>
		🛒 Ver lista de la compra
	</button>
</div>

<!-- Bottom spacing -->
<div style="height:6rem;"></div>

<style>
	.glass-card {
		background: rgba(255, 255, 255, 0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255, 255, 255, 0.09);
		border-radius: 20px;
		padding: 1rem;
	}

	/* ── Form inputs ── */
	.inv-field {
		width: 100%;
		background: rgba(255, 255, 255, 0.06);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 10px;
		color: #fff;
		font-family: inherit;
		font-size: 0.875rem;
		padding: 0.5rem 0.625rem;
		outline: none;
		box-sizing: border-box;
	}
	.inv-field::placeholder {
		color: rgba(255, 255, 255, 0.3);
	}
	.inv-field:focus {
		border-color: rgba(255, 255, 255, 0.25);
	}
</style>
