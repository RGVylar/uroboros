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
</script>

{#if selected}
	<h1>Registrar comida</h1>
	<div class="card" style="margin-bottom:1rem;">
		<div style="font-weight:700;">{selected.name}</div>
		{#if selected.brand}<div style="color:var(--text-muted); font-size:0.85rem;">{selected.brand}</div>{/if}
		<div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.25rem;">
			Por 100{unit}: {selected.calories_per_100g} kcal · P{selected.protein_per_100g} · C{selected.carbs_per_100g} · G{selected.fat_per_100g}
		</div>
	</div>

	<div class="form-group">
		<label for="entry-date">Fecha</label>
		<input id="entry-date" type="date" bind:value={selectedDate} max={new Date().toISOString().slice(0, 10)} />
	</div>

	<div class="form-group">
		<label>Tipo de comida</label>
		<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:0.4rem;">
			{#each MEAL_ORDER as mt}
				<button
					onclick={() => mealType = mt}
					class:btn-secondary={mealType !== mt}
					style="font-size:0.75rem; padding:0.4rem 0.2rem;">
					{MEAL_LABELS[mt]}
				</button>
			{/each}
		</div>
	</div>

	<div class="form-group">
		<label for="grams">Cantidad ({unit})</label>
		<input id="grams" type="number" bind:value={grams} min="1" step="1" />
	</div>

	<div class="card" style="margin-bottom:1rem;">
		<div class="macro-grid">
			<div>
				<div class="label">Kcal</div>
				<div class="value" style="color:var(--cal);">{preview(selected.calories_per_100g)}</div>
			</div>
			<div>
				<div class="label">Prot</div>
				<div class="value" style="color:var(--prot);">{preview(selected.protein_per_100g)}g</div>
			</div>
			<div>
				<div class="label">Carb</div>
				<div class="value" style="color:var(--carb);">{preview(selected.carbs_per_100g)}g</div>
			</div>
			<div>
				<div class="label">Grasa</div>
				<div class="value" style="color:var(--fat);">{preview(selected.fat_per_100g)}g</div>
			</div>
		</div>
	</div>

	{#if users.length > 1}
		<div class="form-group">
			<button
				type="button"
				class:enabled={alsoFor !== null}
				class="share-card"
				onclick={() => {
					alsoFor = alsoFor === null ? partner?.id ?? null : null;
				}}
				aria-pressed={alsoFor !== null}
			>
				<div class="share-copy">
					<div class="share-title-row">
						<span class="share-badge">2x</span>
						<span class="share-title">Añadir también para {partner?.name ?? 'otro usuario'}</span>
					</div>
					<p class="share-description">
						Registra esta misma comida en las dos cuentas con una sola acción.
					</p>
				</div>
				<span class="share-switch" aria-hidden="true">
					<span class="share-switch-thumb"></span>
				</span>
			</button>
		</div>
	{/if}

	{#if error}<p class="error">{error}</p>{/if}

	<div style="display:flex; gap:0.5rem;">
		<button class="btn-secondary" onclick={() => selected = null} style="flex:1;">Atrás</button>
		<button onclick={logEntry} disabled={saving} style="flex:2;">
			{saving ? 'Guardando...' : 'Registrar'}
		</button>
	</div>

{:else if showManual}
	<h1>Producto manual</h1>
	<div class="form-group"><label for="m-name">Nombre</label><input id="m-name" bind:value={manualName} required /></div>
	<div class="form-group"><label for="m-brand">Marca (opcional)</label><input id="m-brand" bind:value={manualBrand} /></div>
	<div class="form-group"><label for="m-cal">Kcal / 100g</label><input id="m-cal" type="number" bind:value={manualCal} min="0" step="0.1" /></div>
	<div class="form-group"><label for="m-prot">Proteína / 100g</label><input id="m-prot" type="number" bind:value={manualProt} min="0" step="0.1" /></div>
	<div class="form-group"><label for="m-carbs">Carbos / 100g</label><input id="m-carbs" type="number" bind:value={manualCarbs} min="0" step="0.1" /></div>
	<div class="form-group"><label for="m-fat">Grasa / 100g</label><input id="m-fat" type="number" bind:value={manualFat} min="0" step="0.1" /></div>

	{#if error}<p class="error">{error}</p>{/if}

	<div style="display:flex; gap:0.5rem;">
		<button class="btn-secondary" onclick={() => showManual = false} style="flex:1;">Atrás</button>
		<button onclick={createManual} style="flex:2;">Crear producto</button>
	</div>

{:else}
	<h1>Añadir comida</h1>

	{#if !loadingRecs && recommendations.length > 0}
		<div style="margin-bottom:1.5rem;">
			<div style="font-weight:700; font-size:0.9rem; margin-bottom:0.5rem; color:var(--text-muted);">
				Sugerencias
			</div>
			<div style="display:flex; flex-direction:column; gap:0.4rem;">
				{#each recommendations as rec (rec.product.id)}
					<button
						onclick={() => selectProduct(rec.product)}
						class="btn-secondary"
						style="text-align:left; padding:0.6rem; transition:border-color 0.2s;">
						<div style="display:flex; justify-content:space-between; align-items:start;">
							<div style="flex:1;">
								<div style="font-weight:600; font-size:0.9rem;">{rec.product.name}</div>
								{#if rec.product.brand}<div style="font-size:0.8rem; color:var(--text-muted);">{rec.product.brand}</div>{/if}
								<div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.25rem;">{rec.reason}</div>
							</div>
							<div style="text-align:right; margin-left:0.5rem; white-space:nowrap;">
								<div style="font-size:0.85rem; color:var(--cal); font-weight:600;">{Math.round(rec.estimated_calories)} kcal</div>
								<div style="font-size:0.75rem; color:var(--text-muted);">{rec.suggested_grams}g</div>
							</div>
						</div>
					</button>
				{/each}
			</div>
		</div>
	{/if}

	<div class="form-group">
		<label for="search">Buscar por nombre</label>
		<div style="display:flex; gap:0.5rem;">
			<input id="search" bind:value={query} placeholder="Avena, pollo..."
				onkeydown={(e) => { if (e.key === 'Enter') searchByName(); }} style="flex:1;" />
			<button onclick={searchByName} disabled={searching}>Buscar</button>
		</div>
	</div>

	<div class="form-group">
		<label for="barcode">Código de barras</label>
		<div style="display:flex; gap:0.5rem;">
			<input id="barcode" bind:value={barcode} placeholder="8410032002347" style="flex:1;" />
			<button onclick={searchByBarcode} disabled={searching}>Buscar</button>
		</div>
		{#if isNative}
			<button onclick={scanBarcode} style="width:100%; margin-top:0.5rem;">
				Escanear con cámara
			</button>
		{:else}
			<button onclick={startWebScan} style="width:100%; margin-top:0.5rem;" disabled={scanning}>
				{scanning ? 'Escaneando...' : 'Escanear con cámara'}
			</button>
		{/if}

		{#if scanError}<p class="error">{scanError}</p>{/if}

		{#if scanning}
			<div style="margin-top:0.75rem; position:relative;">
				<!-- svelte-ignore a11y_media_has_caption -->
				<video bind:this={videoEl} style="width:100%; border-radius:8px; background:#000;" playsinline></video>
				<button class="btn-danger" onclick={stopWebScan}
					style="position:absolute; top:0.5rem; right:0.5rem; padding:0.3rem 0.6rem; font-size:0.8rem;">
					✕
				</button>
			</div>
		{/if}
	</div>

	<button class="btn-secondary" onclick={() => showManual = true} style="width:100%; margin-bottom:1rem;">
		+ Crear producto manual
	</button>

	{#if error}<p class="error">{error}</p>{/if}

	{#if searching}
		<p style="text-align:center; color:var(--text-muted);">Buscando...</p>
	{/if}

	{#each results as product (product.id)}
		<div class="card" style="margin-bottom:0.5rem; display:flex; justify-content:space-between; align-items:center;">
			<button class="btn-secondary" style="flex:1; text-align:left; border:none;"
				onclick={() => selectProduct(product)}>
				<div style="font-weight:600;">{product.name}</div>
				{#if product.brand}<div style="color:var(--text-muted); font-size:0.8rem;">{product.brand}</div>{/if}
				<div style="font-size:0.8rem; color:var(--text-muted);">
					{product.calories_per_100g} kcal · P{product.protein_per_100g} · C{product.carbs_per_100g} · G{product.fat_per_100g}
				</div>
			</button>
			<a href="/add/product/{product.id}" style="padding:0.5rem; font-size:0.8rem;">Editar</a>
		</div>
	{/each}

	{#if hasMore}
		<button class="btn-secondary" onclick={loadMore} disabled={searching} style="width:100%; margin-top:0.25rem; font-size:0.85rem;">
			{searching ? 'Cargando...' : 'Mostrar más resultados'}
		</button>
	{/if}
{/if}
