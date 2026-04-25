<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { Capacitor } from '@capacitor/core';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Product, User, DiaryEntry, MealType, RecommendedProduct } from '$lib/types';
	import { MEAL_LABELS, MEAL_ORDER } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	const urlDate = $page.url.searchParams.get('date');
	let selectedDate = $state(urlDate ?? new Date().toISOString().slice(0, 10));

	let isNative = Capacitor.isNativePlatform();

	// Recommendations state
	let recommendations: RecommendedProduct[] = $state([]);
	let loadingRecs = $state(false);

	// Web barcode scanner state
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
			stream = await navigator.mediaDevices.getUserMedia({
				video: { facingMode: 'environment' }
			});
			if (videoEl) {
				videoEl.srcObject = stream;
				videoEl.play();
				zxingReader.decodeFromVideoElement(videoEl, (result, err) => {
					if (result) {
						barcode = result.getText();
						stopWebScan();
						searchByBarcode();
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
		if (stream) {
			stream.getTracks().forEach(t => t.stop());
			stream = null;
		}
		if (zxingReader) {
			zxingReader.reset();
			zxingReader = null;
		}
	}

	let query = $state('');
	let barcode = $state('');
	let results: Product[] = $state([]);
	let searching = $state(false);
	let searchOffset = $state(0);
	let hasMore = $state(false);
	const PAGE_SIZE = 20;

	const DRINK_KEYWORDS = ['leche', 'zumo', 'jugo', 'agua', 'bebida', 'refresco', 'batido',
		'smoothie', 'néctar', 'nectar', 'cerveza', 'vino', 'caldo', 'té', 'te ', 'café', 'cafe',
		'yogur', 'kéfir', 'kefir', 'infusión', 'infusion', 'horchata', 'limonada', 'naranjada'];

	function isDrink(product: Product): boolean {
		const text = `${product.name} ${product.brand ?? ''}`.toLowerCase();
		return DRINK_KEYWORDS.some(k => text.includes(k));
	}

	function getLastGrams(productId: number): number {
		const stored = localStorage.getItem(`last_grams_${productId}`);
		return stored ? parseInt(stored) : 100;
	}

	function saveLastGrams(productId: number, g: number) {
		localStorage.setItem(`last_grams_${productId}`, String(g));
	}

	function selectProduct(product: Product) {
		selected = product;
		grams = getLastGrams(product.id);
	}
	let selected: Product | null = $state(null);
	let grams = $state(100);
	let alsoFor: number | null = $state(null);
	let mealType: MealType = $state(guessMealType());

	function guessMealType(): MealType {
		const h = new Date().getHours();
		if (h >= 6 && h < 11) return 'breakfast';
		if (h >= 11 && h < 16) return 'lunch';
		if (h >= 16 && h < 22) return 'dinner';
		return 'snack';
	}
	let users: User[] = $state([]);
	let saving = $state(false);
	let error = $state('');
	let showManual = $state(false);
	let partner = $derived(users.find((u) => u.id !== auth.user?.id) ?? null);

	// manual product fields
	let manualName = $state('');
	let manualBrand = $state('');
	let manualCal = $state(0);
	let manualProt = $state(0);
	let manualCarbs = $state(0);
	let manualFat = $state(0);

	// Active chip filter
	let activeFilter = $state<'suggestions' | 'recent' | 'favorites' | 'manual'>('suggestions');

	async function loadRecommendations() {
		loadingRecs = true;
		try {
			recommendations = await api.get<RecommendedProduct[]>('/products/recommendations');
		} catch (e: unknown) {
			recommendations = [];
		} finally {
			loadingRecs = false;
		}
	}

	$effect(() => {
		api.get<User[]>('/users').then(u => users = u).catch(() => {});
		loadRecommendations();
	});

	async function searchByName() {
		if (!query.trim()) return;
		searching = true;
		error = '';
		searchOffset = 0;
		try {
			const res = await api.get<Product[]>(`/products?q=${encodeURIComponent(query)}&limit=${PAGE_SIZE}&offset=0`);
			results = res;
			hasMore = res.length === PAGE_SIZE;
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		} finally {
			searching = false;
		}
	}

	async function loadMore() {
		if (!query.trim() || searching) return;
		searching = true;
		try {
			const nextOffset = searchOffset + PAGE_SIZE;
			const res = await api.get<Product[]>(`/products?q=${encodeURIComponent(query)}&limit=${PAGE_SIZE}&offset=${nextOffset}`);
			results = [...results, ...res];
			searchOffset = nextOffset;
			hasMore = res.length === PAGE_SIZE;
		} catch {
			// ignore
		} finally {
			searching = false;
		}
	}

	async function searchByBarcode() {
		if (!barcode.trim()) return;
		searching = true;
		error = '';
		try {
			const p = await api.get<Product>(`/products/barcode/${barcode.trim()}`);
			selectProduct(p);
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		} finally {
			searching = false;
		}
	}

	async function scanBarcode() {
		try {
			const { BarcodeScanner } = await import('@capacitor-mlkit/barcode-scanning');
			const { supported } = await BarcodeScanner.isSupported();
			if (!supported) {
				error = 'Barcode scanner not supported on this device';
				return;
			}

			const granted = await BarcodeScanner.requestPermissions();
			if (granted.camera !== 'granted') {
				error = 'Camera permission denied';
				return;
			}

			const { barcodes } = await BarcodeScanner.scan();
			if (barcodes.length > 0) {
				barcode = barcodes[0].rawValue;
				await searchByBarcode();
			}
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Scanner error';
		}
	}

	async function createManual() {
		error = '';
		try {
			const p = await api.post<Product>('/products', {
				name: manualName,
				brand: manualBrand || null,
				calories_per_100g: manualCal,
				protein_per_100g: manualProt,
				carbs_per_100g: manualCarbs,
				fat_per_100g: manualFat
			});
			selected = p;
			showManual = false;
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		}
	}

	async function logEntry() {
		if (!selected) return;
		saving = true;
		error = '';
		try {
			await api.post<DiaryEntry[]>('/diary', {
				product_id: selected.id,
				grams,
				meal_type: mealType,
				consumed_at: new Date(selectedDate + 'T12:00:00').toISOString(),
				also_for_user_id: alsoFor
			});
			saveLastGrams(selected.id, grams);
			goto('/');
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		} finally {
			saving = false;
		}
	}

	function preview(per100: number) {
		return Math.round(per100 * grams / 100);
	}

	let unit = $derived(selected && isDrink(selected) ? 'ml' : 'g');

	// Helpers for product visuals
	function hashHue(s: string): number {
		let h = 0;
		for (const c of s) h = (h * 31 + c.charCodeAt(0)) % 360;
		return h;
	}

	function productGlyph(name: string): string {
		const n = name.toLowerCase();
		if (/avena|cereal|arroz|pan|pasta/.test(n)) return '🌾';
		if (/pollo|pavo/.test(n)) return '🍗';
		if (/leche|yogur|queso/.test(n)) return '🥛';
		if (/huevo/.test(n)) return '🥚';
		if (/manzana|plátano|fruta/.test(n)) return '🍎';
		if (/jamón|ibérico|cerdo/.test(n)) return '🥩';
		if (/aceite|oliva/.test(n)) return '🫒';
		if (/cerveza/.test(n)) return '🍺';
		if (/barra|tierna/.test(n)) return '🍞';
		if (/kebab/.test(n)) return '🌯';
		if (/atún/.test(n)) return '🐟';
		return '🍽';
	}

	const QUICK_GRAMS = [50, 100, 150, 200, 250];

	const MACRO_CELLS = [
		{ label: 'Prot', key: 'protein_per_100g' as const, hue: 220 },
		{ label: 'Carb', key: 'carbs_per_100g' as const, hue: 275 },
		{ label: 'Grasa', key: 'fat_per_100g' as const, hue: 25 },
	];
</script>

<!-- ═══════════════════════════════════════════════════════
     DETAIL VIEW — producto seleccionado
═══════════════════════════════════════════════════════ -->
{#if selected && !showManual}
	<!-- Header -->
	<div class="add-header">
		<button class="glass-btn" onclick={() => (selected = null)} aria-label="Volver">
			<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
				<path d="M15 18l-6-6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
			</svg>
		</button>
		<div style="flex:1; min-width:0;">
			<div class="header-eyebrow">Detalle</div>
			<div class="header-title" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{selected.name}</div>
		</div>
	</div>

	<!-- Macro preview card -->
	<div class="glass-card" style="margin-bottom:0.875rem;">
		<div class="section-eyebrow" style="margin-bottom:0.625rem;">Para {grams}{unit}</div>
		<div style="display:flex; align-items:baseline; gap:0.4rem; margin-bottom:0.875rem;">
			<span class="big-kcal">{preview(selected.calories_per_100g)}</span>
			<span style="font-size:0.875rem; color:rgba(255,255,255,0.5); font-weight:500;">kcal</span>
		</div>
		<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.5rem;">
			{#each MACRO_CELLS as m}
				<div class="macro-cell" style="
					background: oklch(72% 0.18 {m.hue} / 0.1);
					border: 1px solid oklch(72% 0.18 {m.hue} / 0.2);
				">
					<div class="macro-cell-label" style="color: oklch(80% 0.15 {m.hue});">{m.label}</div>
					<div class="macro-cell-val">{preview(selected[m.key])}<span class="macro-cell-unit">g</span></div>
				</div>
			{/each}
		</div>
	</div>

	<!-- Grams picker -->
	<div class="glass-card" style="margin-bottom:0.875rem;">
		<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem;">
			<span style="font-size:0.8125rem; font-weight:700;">Cantidad</span>
			<div style="display:flex; align-items:baseline; gap:0.25rem;">
				<input
					type="number"
					bind:value={grams}
					min="1"
					step="1"
					class="grams-input"
				/>
				<span style="font-size:0.75rem; color:rgba(255,255,255,0.5);">{unit}</span>
			</div>
		</div>
		<div style="display:flex; gap:0.375rem;">
			{#each QUICK_GRAMS as g}
				<button
					onclick={() => (grams = g)}
					class="gram-chip"
					class:gram-chip-active={grams === g}
				>{g}</button>
			{/each}
		</div>
	</div>

	<!-- Meal type -->
	<div style="margin-bottom:0.875rem;">
		<div class="section-eyebrow" style="padding:0 0.25rem 0.5rem;">Comida</div>
		<div style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:0.375rem;">
			{#each MEAL_ORDER as mt}
				<button
					onclick={() => (mealType = mt)}
					class="meal-chip"
					class:meal-chip-active={mealType === mt}
				>{MEAL_LABELS[mt]}</button>
			{/each}
		</div>
	</div>

	<!-- Date picker -->
	<div style="margin-bottom:0.875rem;">
		<div class="section-eyebrow" style="padding:0 0.25rem 0.5rem;">Fecha</div>
		<input
			type="date"
			bind:value={selectedDate}
			max={new Date().toISOString().slice(0, 10)}
			class="date-input"
		/>
	</div>

	<!-- Partner share -->
	{#if users.length > 1 && partner}
		<button
			type="button"
			onclick={() => { alsoFor = alsoFor === null ? (partner?.id ?? null) : null; }}
			aria-pressed={alsoFor !== null}
			class="share-card"
			class:share-card-active={alsoFor !== null}
			style="margin-bottom:1rem;"
		>
			<div class="share-badge-icon" class:share-badge-icon-active={alsoFor !== null}>2×</div>
			<div style="flex:1; min-width:0; text-align:left;">
				<div style="font-size:0.8125rem; font-weight:700;">También para {partner.name}</div>
				<div style="font-size:0.6875rem; color:rgba(255,255,255,0.55); margin-top:0.125rem;">Registrar en las dos cuentas</div>
			</div>
			<!-- Toggle switch -->
			<div class="toggle-track" class:toggle-track-on={alsoFor !== null}>
				<div class="toggle-thumb" class:toggle-thumb-on={alsoFor !== null}></div>
			</div>
		</button>
	{/if}

	{#if error}<p class="add-error">{error}</p>{/if}

	<button class="btn-submit" onclick={logEntry} disabled={saving}>
		{saving ? 'Guardando...' : alsoFor !== null ? 'Registrar · 2×' : 'Registrar'}
	</button>

<!-- ═══════════════════════════════════════════════════════
     MANUAL PRODUCT FORM
═══════════════════════════════════════════════════════ -->
{:else if showManual}
	<div class="add-header">
		<button class="glass-btn" onclick={() => (showManual = false)} aria-label="Volver">
			<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
				<path d="M15 18l-6-6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
			</svg>
		</button>
		<div>
			<div class="header-eyebrow">Nuevo</div>
			<div class="header-title">Producto manual</div>
		</div>
	</div>

	<div class="glass-card" style="display:flex; flex-direction:column; gap:0.75rem; margin-bottom:1rem;">
		<div class="manual-field">
			<label for="m-name">Nombre</label>
			<input id="m-name" bind:value={manualName} required class="field-input" />
		</div>
		<div class="manual-field">
			<label for="m-brand">Marca <span style="color:rgba(255,255,255,0.4);">(opcional)</span></label>
			<input id="m-brand" bind:value={manualBrand} class="field-input" />
		</div>
		<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
			<div class="manual-field">
				<label for="m-cal">Kcal / 100g</label>
				<input id="m-cal" type="number" bind:value={manualCal} min="0" step="0.1" class="field-input" />
			</div>
			<div class="manual-field">
				<label for="m-prot">Prot / 100g</label>
				<input id="m-prot" type="number" bind:value={manualProt} min="0" step="0.1" class="field-input" />
			</div>
			<div class="manual-field">
				<label for="m-carbs">Carb / 100g</label>
				<input id="m-carbs" type="number" bind:value={manualCarbs} min="0" step="0.1" class="field-input" />
			</div>
			<div class="manual-field">
				<label for="m-fat">Grasa / 100g</label>
				<input id="m-fat" type="number" bind:value={manualFat} min="0" step="0.1" class="field-input" />
			</div>
		</div>
	</div>

	{#if error}<p class="add-error">{error}</p>{/if}

	<button class="btn-submit" onclick={createManual}>Crear producto</button>

<!-- ═══════════════════════════════════════════════════════
     SEARCH / LIST VIEW
═══════════════════════════════════════════════════════ -->
{:else}
	<!-- Header -->
	<div class="add-header">
		<button class="glass-btn" onclick={() => goto('/')} aria-label="Volver al diario">
			<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
				<path d="M15 18l-6-6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
			</svg>
		</button>
		<div>
			<div class="header-eyebrow">Registrar</div>
			<div class="header-title">Añadir comida</div>
		</div>
	</div>

	<!-- Unified search + barcode -->
	<div class="search-glass" style="margin-bottom:0.625rem;">
		<svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true" style="color:rgba(255,255,255,0.4); flex-shrink:0; margin:0 0.25rem 0 0.125rem;">
			<circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2"/>
			<path d="M16.5 16.5l4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
		</svg>
		<input
			bind:value={query}
			placeholder="Buscar avena, pollo, código de barras..."
			class="search-input"
			onkeydown={(e) => { if (e.key === 'Enter') searchByName(); }}
		/>
		<button
			onclick={isNative ? scanBarcode : startWebScan}
			class="barcode-btn"
			aria-label="Escanear código de barras"
			disabled={scanning}
		>
			<svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
				<rect x="2" y="6" width="2" height="12" rx="1" fill="currentColor"/>
				<rect x="6" y="6" width="1" height="12" rx="0.5" fill="currentColor"/>
				<rect x="9" y="6" width="2" height="12" rx="1" fill="currentColor"/>
				<rect x="13" y="6" width="1" height="12" rx="0.5" fill="currentColor"/>
				<rect x="16" y="6" width="2" height="12" rx="1" fill="currentColor"/>
				<rect x="20" y="6" width="2" height="12" rx="1" fill="currentColor"/>
			</svg>
		</button>
	</div>

	<!-- Barcode manual input -->
	{#if barcode}
		<div style="margin-bottom:0.5rem; display:flex; gap:0.5rem;">
			<input bind:value={barcode} placeholder="Código de barras" class="field-input" style="flex:1;" />
			<button onclick={searchByBarcode} disabled={searching} class="btn-submit" style="padding:0 1rem; height:44px; border-radius:12px;">Buscar</button>
		</div>
	{/if}

	{#if scanError}<p class="add-error">{scanError}</p>{/if}

	<!-- Camera scanner -->
	{#if scanning}
		<div style="margin-bottom:0.75rem; position:relative;">
			<!-- svelte-ignore a11y_media_has_caption -->
			<video bind:this={videoEl} style="width:100%; border-radius:16px; background:#000;" playsinline></video>
			<button
				onclick={stopWebScan}
				style="position:absolute; top:0.5rem; right:0.5rem; width:32px; height:32px; border-radius:50%; background:rgba(0,0,0,0.6); border:none; color:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center;"
				aria-label="Detener escáner"
			>✕</button>
		</div>
	{/if}

	<!-- Quick filter chips -->
	<div style="display:flex; gap:0.5rem; margin-bottom:1.125rem; flex-wrap:wrap;">
		<button onclick={() => { activeFilter = 'suggestions'; }} class="filter-chip" class:filter-chip-active={activeFilter === 'suggestions'}>⚡ Sugerencias</button>
		<button onclick={() => { activeFilter = 'recent'; }}      class="filter-chip" class:filter-chip-active={activeFilter === 'recent'}>🕒 Recientes</button>
		<button onclick={() => { activeFilter = 'favorites'; }}   class="filter-chip" class:filter-chip-active={activeFilter === 'favorites'}>⭐ Favoritos</button>
		<button onclick={() => { activeFilter = 'manual'; showManual = true; }} class="filter-chip">✏️ Manual</button>
	</div>

	<!-- Results section (when query) -->
	{#if query && (searching || results.length > 0)}
		<div class="section-header">
			<div>
				<div class="section-title">Resultados</div>
			</div>
			{#if results.length > 0}
				<div class="section-count">{results.length} resultados</div>
			{/if}
		</div>

		{#if searching && results.length === 0}
			<div class="loading-row">Buscando...</div>
		{/if}

		<div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:1.25rem;">
			{#each results as product (product.id)}
				<button class="product-row" onclick={() => selectProduct(product)}>
					<div class="product-avatar" style="
						background: linear-gradient(135deg, oklch(78% 0.12 {hashHue(product.name)} / 0.35), oklch(60% 0.12 {hashHue(product.name)} / 0.15));
					">{productGlyph(product.name)}</div>
					<div style="flex:1; min-width:0; text-align:left;">
						<div class="product-name">{product.name}</div>
						<div class="product-brand">{product.brand ?? '—'}</div>
					</div>
					<div style="text-align:right; flex-shrink:0;">
						<div class="product-kcal">{product.calories_per_100g}<span class="product-kcal-unit">kcal</span></div>
						<div class="product-per">/100{isDrink(product) ? 'ml' : 'g'}</div>
					</div>
				</button>
			{/each}
		</div>

		{#if hasMore}
			<button class="load-more-btn" onclick={loadMore} disabled={searching}>
				{searching ? 'Cargando...' : 'Mostrar más'}
			</button>
		{/if}
	{/if}

	<!-- Suggestions section (when no query) -->
	{#if !query && activeFilter === 'suggestions'}
		{#if loadingRecs}
			<div class="loading-row">Cargando sugerencias...</div>
		{:else if recommendations.length > 0}
			<div class="section-header">
				<div>
					<div class="section-title">Sugerencias para ti</div>
					<div class="section-sub">Basado en tu rutina</div>
				</div>
			</div>
			<div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:1.25rem;">
				{#each recommendations as rec (rec.product.id)}
					<button class="product-row" onclick={() => selectProduct(rec.product)}>
						<div class="product-avatar" style="
							background: linear-gradient(135deg, oklch(78% 0.12 {hashHue(rec.product.name)} / 0.35), oklch(60% 0.12 {hashHue(rec.product.name)} / 0.15));
						">{productGlyph(rec.product.name)}</div>
						<div style="flex:1; min-width:0; text-align:left;">
							<div class="product-name">{rec.product.name}</div>
							<div class="product-brand">{rec.reason}</div>
						</div>
						<div style="text-align:right; flex-shrink:0;">
							<div class="product-kcal">{Math.round(rec.estimated_calories)}<span class="product-kcal-unit">kcal</span></div>
							<div class="product-per">{rec.suggested_grams}g</div>
						</div>
					</button>
				{/each}
			</div>
		{/if}
	{/if}

	{#if error}<p class="add-error">{error}</p>{/if}
{/if}

<style>
	/* ── Page headers ── */
	.add-header {
		display: flex;
		align-items: center;
		gap: 0.625rem;
		margin-bottom: 0.875rem;
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

	/* ── Glass button (back arrow) ── */
	.glass-btn {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: rgba(255,255,255,0.07);
		border: 1px solid rgba(255,255,255,0.1);
		color: rgba(255,255,255,0.8);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		transition: background 0.15s;
	}
	.glass-btn:hover { background: rgba(255,255,255,0.12); }

	/* ── Glass card ── */
	.glass-card {
		background: rgba(255,255,255,0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 20px;
		padding: 1.125rem;
	}

	/* ── Search bar ── */
	.search-glass {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		background: rgba(255,255,255,0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 16px;
		padding: 0.375rem 0.5rem;
	}
	.search-input {
		flex: 1;
		background: transparent;
		border: none;
		outline: none;
		color: #fff;
		font-size: 0.875rem;
		font-family: inherit;
		padding: 0.5rem 0;
	}
	.search-input::placeholder { color: rgba(255,255,255,0.35); }
	.barcode-btn {
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
	}
	.barcode-btn:hover { background: rgba(255,255,255,0.1); }

	/* ── Filter chips ── */
	.filter-chip {
		padding: 0.4rem 0.75rem;
		border-radius: 99px;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.08);
		color: rgba(255,255,255,0.65);
		font-size: 0.72rem;
		font-weight: 600;
		font-family: inherit;
		cursor: pointer;
		transition: background 0.15s, color 0.15s, border-color 0.15s;
		white-space: nowrap;
	}
	.filter-chip:hover { background: rgba(255,255,255,0.09); color: #fff; }
	.filter-chip-active {
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		border-color: transparent;
		color: #041010;
		box-shadow: inset 0 1px 0 rgba(255,255,255,0.4);
	}

	/* ── Section headers ── */
	.section-header {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		padding: 0 0.25rem 0.625rem;
	}
	.section-title { font-size: 0.8125rem; font-weight: 700; color: #fff; }
	.section-sub { font-size: 0.625rem; color: rgba(255,255,255,0.45); margin-top: 0.125rem; }
	.section-count { font-size: 0.625rem; color: rgba(255,255,255,0.4); font-variant-numeric: tabular-nums; }
	.section-eyebrow {
		font-size: 0.6875rem;
		letter-spacing: 0.1em;
		color: rgba(255,255,255,0.45);
		text-transform: uppercase;
		font-weight: 600;
	}

	/* ── Product rows ── */
	.product-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.07);
		border-radius: 16px;
		padding: 0.75rem;
		cursor: pointer;
		transition: background 0.15s;
		width: 100%;
	}
	.product-row:hover { background: rgba(255,255,255,0.08); }
	.product-avatar {
		width: 38px;
		height: 38px;
		border-radius: 12px;
		flex-shrink: 0;
		border: 1px solid rgba(255,255,255,0.08);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1rem;
	}
	.product-name {
		font-size: 0.8125rem;
		font-weight: 600;
		color: #fff;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.product-brand {
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.45);
		margin-top: 0.125rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.product-kcal {
		font-size: 0.8125rem;
		font-weight: 700;
		color: oklch(85% 0.17 55);
		font-variant-numeric: tabular-nums;
		display: inline-flex;
		align-items: baseline;
		gap: 0.125rem;
	}
	.product-kcal-unit { font-size: 0.5625rem; color: rgba(255,255,255,0.4); margin-left: 0.125rem; }
	.product-per { font-size: 0.625rem; color: rgba(255,255,255,0.45); }

	/* ── Detail: Big kcal ── */
	.big-kcal {
		font-size: 2.75rem;
		font-weight: 800;
		color: oklch(85% 0.17 55);
		letter-spacing: -0.06em;
		font-variant-numeric: tabular-nums;
		line-height: 1;
	}

	/* ── Macro cells ── */
	.macro-cell {
		padding: 0.625rem 0.75rem;
		border-radius: 12px;
	}
	.macro-cell-label {
		font-size: 0.625rem;
		font-weight: 700;
		letter-spacing: 0.05em;
		text-transform: uppercase;
	}
	.macro-cell-val {
		font-size: 1rem;
		font-weight: 700;
		color: #fff;
		margin-top: 0.125rem;
		font-variant-numeric: tabular-nums;
	}
	.macro-cell-unit { font-size: 0.625rem; color: rgba(255,255,255,0.4); }

	/* ── Grams input ── */
	.grams-input {
		width: 70px;
		text-align: right;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.1);
		border-radius: 10px;
		color: #fff;
		padding: 0.375rem 0.625rem;
		font-size: 0.9375rem;
		font-weight: 700;
		font-family: inherit;
		outline: none;
		font-variant-numeric: tabular-nums;
	}
	.grams-input:focus { border-color: oklch(75% 0.18 165 / 0.5); }

	/* ── Quick gram chips ── */
	.gram-chip {
		flex: 1;
		padding: 0.375rem 0;
		border-radius: 99px;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.08);
		color: rgba(255,255,255,0.7);
		font-size: 0.72rem;
		font-weight: 600;
		font-family: inherit;
		cursor: pointer;
		text-align: center;
		transition: background 0.15s, color 0.15s;
	}
	.gram-chip:hover { background: rgba(255,255,255,0.09); color: #fff; }
	.gram-chip-active {
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		border-color: transparent;
		color: #041010;
		box-shadow: inset 0 1px 0 rgba(255,255,255,0.4);
	}

	/* ── Meal chips ── */
	.meal-chip {
		padding: 0.5rem 0;
		border-radius: 12px;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.08);
		color: rgba(255,255,255,0.65);
		font-size: 0.72rem;
		font-weight: 600;
		font-family: inherit;
		cursor: pointer;
		text-align: center;
		transition: background 0.15s, color 0.15s;
	}
	.meal-chip:hover { background: rgba(255,255,255,0.09); color: #fff; }
	.meal-chip-active {
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		border-color: transparent;
		color: #041010;
		box-shadow: inset 0 1px 0 rgba(255,255,255,0.4);
	}

	/* ── Date input ── */
	.date-input {
		width: 100%;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.1);
		border-radius: 12px;
		color: #fff;
		padding: 0.625rem 0.875rem;
		font-size: 0.875rem;
		font-family: inherit;
		outline: none;
		box-sizing: border-box;
	}
	.date-input:focus { border-color: oklch(75% 0.18 165 / 0.5); }
	.date-input::-webkit-calendar-picker-indicator { filter: invert(1) opacity(0.6); }

	/* ── Partner share card ── */
	.share-card {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 20px;
		padding: 0.875rem;
		cursor: pointer;
		transition: background 0.15s, border-color 0.15s;
	}
	.share-card:hover { background: rgba(255,255,255,0.08); }
	.share-card-active {
		background: oklch(75% 0.18 165 / 0.1);
		border-color: oklch(80% 0.17 165 / 0.3);
	}
	.share-badge-icon {
		width: 40px;
		height: 40px;
		border-radius: 12px;
		background: rgba(255,255,255,0.06);
		color: oklch(85% 0.15 160);
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: 800;
		font-size: 0.875rem;
		letter-spacing: -0.03em;
		flex-shrink: 0;
		transition: background 0.2s, color 0.2s;
	}
	.share-badge-icon-active {
		background: linear-gradient(135deg, oklch(85% 0.17 160), oklch(72% 0.18 170));
		color: #041010;
	}

	/* ── Toggle switch ── */
	.toggle-track {
		width: 44px;
		height: 26px;
		border-radius: 99px;
		background: rgba(255,255,255,0.08);
		border: 1px solid rgba(255,255,255,0.1);
		position: relative;
		transition: background 0.2s, border-color 0.2s;
		flex-shrink: 0;
	}
	.toggle-track-on {
		background: oklch(75% 0.18 165 / 0.3);
		border-color: oklch(80% 0.17 165 / 0.5);
	}
	.toggle-thumb {
		position: absolute;
		top: 2px;
		left: 2px;
		width: 20px;
		height: 20px;
		border-radius: 50%;
		background: #d0d4d8;
		box-shadow: 0 2px 6px rgba(0,0,0,0.3);
		transition: left 0.2s, background 0.2s;
	}
	.toggle-thumb-on {
		left: 20px;
		background: linear-gradient(135deg, #fff, oklch(85% 0.1 165));
	}

	/* ── Manual form ── */
	.manual-field { display: flex; flex-direction: column; gap: 0.25rem; }
	.manual-field label { font-size: 0.6875rem; font-weight: 600; color: rgba(255,255,255,0.55); }
	.field-input {
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.1);
		border-radius: 10px;
		color: #fff;
		padding: 0.5rem 0.75rem;
		font-size: 0.875rem;
		font-family: inherit;
		outline: none;
		width: 100%;
		box-sizing: border-box;
	}
	.field-input:focus { border-color: oklch(75% 0.18 165 / 0.5); }

	/* ── Submit button ── */
	.btn-submit {
		width: 100%;
		height: 52px;
		border-radius: 16px;
		border: none;
		cursor: pointer;
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		font-weight: 800;
		font-size: 0.9375rem;
		font-family: inherit;
		letter-spacing: -0.01em;
		box-shadow:
			0 10px 30px -8px oklch(75% 0.22 165 / 0.55),
			inset 0 -2px 6px oklch(60% 0.2 170),
			inset 0 1px 0 rgba(255,255,255,0.4);
		transition: opacity 0.15s, transform 0.15s;
	}
	.btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }
	.btn-submit:not(:disabled):hover { transform: translateY(-1px); }
	.btn-submit:not(:disabled):active { transform: translateY(0); }

	/* ── Misc ── */
	.add-error {
		color: var(--danger);
		font-size: 0.8rem;
		margin: 0.5rem 0;
		padding: 0.5rem 0.75rem;
		background: oklch(65% 0.22 25 / 0.1);
		border-radius: 10px;
		border: 1px solid oklch(65% 0.22 25 / 0.2);
	}
	.loading-row {
		text-align: center;
		color: rgba(255,255,255,0.45);
		font-size: 0.8rem;
		padding: 1.5rem 0;
	}
	.load-more-btn {
		width: 100%;
		padding: 0.625rem;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.08);
		border-radius: 12px;
		color: rgba(255,255,255,0.65);
		font-size: 0.8rem;
		font-weight: 600;
		font-family: inherit;
		cursor: pointer;
		transition: background 0.15s;
		margin-top: 0.25rem;
	}
	.load-more-btn:hover { background: rgba(255,255,255,0.09); }
	.load-more-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
