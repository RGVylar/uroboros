<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { Capacitor } from '@capacitor/core';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import { connectivity } from '$lib/stores/connectivity.svelte';
	import { syncQueue } from '$lib/stores/sync-queue.svelte';
	import { cacheSet, cacheGet } from '$lib/cache';
	import type {
		Product,
		User,
		DiaryEntry,
		MealType,
		RecommendedProduct,
		FrequentProduct,
		FrequentRecipe,
		InventoryItem,
	} from '$lib/types';
	import { MEAL_LABELS, MEAL_ORDER } from '$lib/types';
	import ConsumeFoodModal from '$lib/components/ConsumeFoodModal.svelte';

	if (!auth.isLoggedIn) goto('/login');

	const urlDate = $page.url.searchParams.get('date');
	let selectedDate = $state(urlDate ?? new Date().toISOString().slice(0, 10));

	// Use current time for today's entries, noon for past dates
	function consumedAt(dateStr: string): string {
		const today = new Date().toISOString().slice(0, 10);
		return dateStr === today
			? new Date().toISOString()
			: new Date(dateStr + 'T12:00:00').toISOString();
	}

	let isNative = Capacitor.isNativePlatform();

	// Recommendations state
	let recommendations: RecommendedProduct[] = $state([]);
	let loadingRecs = $state(false);

	// Frequent / history state
	let frequent: FrequentProduct[] = $state([]);
	let frequentRecipes: FrequentRecipe[] = $state([]);
	let loadingFrequent = $state(false);
	let frequentFromCache = $state(false);

	// Favorites state
	let favorites: Product[] = $state([]);
	let favoriteIds = $state(new Set<number>());
	let favoriteToggling = $state(false);

	async function loadFavorites() {
		try {
			const [prods, ids] = await Promise.all([
				api.get<Product[]>('/favorites'),
				api.get<number[]>('/favorites/ids'),
			]);
			favorites = prods;
			favoriteIds = new Set(ids);
			// Persistir para uso offline
			if (prods.length > 0) cacheSet('favorite_products', prods);
		} catch {
			// Offline — intentar caché
			const cached = cacheGet<Product[]>('favorite_products');
			if (cached) {
				favorites = cached.data;
				favoriteIds = new Set(cached.data.map(p => p.id));
			}
		}
	}

	async function toggleFavorite(productId: number) {
		if (favoriteToggling) return;
		favoriteToggling = true;
		const isFav = favoriteIds.has(productId);
		// Optimistic update
		const next = new Set(favoriteIds);
		if (isFav) {
			next.delete(productId);
			favorites = favorites.filter(p => p.id !== productId);
		} else {
			next.add(productId);
			if (selected) favorites = [selected, ...favorites];
		}
		favoriteIds = next;
		try {
			if (isFav) {
				await api.del(`/favorites/${productId}`);
			} else {
				await api.post(`/favorites/${productId}`, {});
			}
		} catch {
			// Revert on error
			await loadFavorites();
		} finally {
			favoriteToggling = false;
		}
	}

	// Web barcode scanner state
	let scanning = $state(false);
	let videoEl: HTMLVideoElement | undefined = $state();
	let scanError = $state('');
	let stream: MediaStream | null = null;
	let zxingReader: import('@zxing/browser').BrowserMultiFormatReader | null = null;

	async function startWebScan() {
		scanError = '';
		scanning = true;
		barcode = '';
		barcodeNotFound = false;
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
	let barcodeNotFound = $state(false);
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

	let selected: Product | null = $state(null);
	let grams = $state(100);
	// null = solo yo | 'also' = los dos | 'only' = solo pareja
	type ShareMode = null | 'also' | 'only';
	let shareMode: ShareMode = $state(null);
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

	// ── Editar producto ─────────────────────────────────────────────────────────
	let showEdit = $state(false);
	let editName = $state('');
	let editBrand = $state('');
	let editCal = $state(0);
	let editProt = $state(0);
	let editCarbs = $state(0);
	let editFat = $state(0);
	let editSaving = $state(false);
	let editError = $state('');

	function startEdit() {
		if (!selected) return;
		editName = selected.name;
		editBrand = selected.brand ?? '';
		editCal = selected.calories_per_100g;
		editProt = selected.protein_per_100g;
		editCarbs = selected.carbs_per_100g;
		editFat = selected.fat_per_100g;
		editError = '';
		showEdit = true;
	}

	async function saveEdit() {
		if (!selected) return;
		editSaving = true;
		editError = '';
		try {
			const updated = await api.patch<Product>(`/products/${selected.id}`, {
				name: editName,
				brand: editBrand || null,
				calories_per_100g: editCal,
				protein_per_100g: editProt,
				carbs_per_100g: editCarbs,
				fat_per_100g: editFat,
			});
			selected = updated;
			showEdit = false;
		} catch (e: unknown) {
			editError = e instanceof Error ? e.message : 'Error al guardar';
		} finally {
			editSaving = false;
		}
	}

	// ── Allergies ──────────────────────────────────────────────────────────────
	type AllergyInfo = { id: number; ingredient: string };
	let myAllergies: AllergyInfo[] = $state([]);
	let partnerAllergies: AllergyInfo[] = $state([]);

	const ALLERGEN_LABELS: Record<string, string> = {
		gluten:           'Gluten',
		milk:             'Leche',
		eggs:             'Huevos',
		peanuts:          'Cacahuetes',
		nuts:             'Frutos secos',
		soybeans:         'Soja',
		fish:             'Pescado',
		crustaceans:      'Marisco',
		celery:           'Apio',
		mustard:          'Mostaza',
		'sesame-seeds':   'Sésamo',
		'sulphur-dioxide':'Sulfitos',
		mollusks:         'Moluscos',
		lupin:            'Altramuces',
	};

	function allergenLabel(key: string): string {
		return ALLERGEN_LABELS[key] ?? key;
	}

	function checkAllergens(product: Product, list: AllergyInfo[]): string[] {
		if (!list.length) return [];
		const userKeys = new Set(list.map(a => a.ingredient.toLowerCase()));
		const productAllergens: string[] = product.allergens ?? [];
		// Primary: match via structured allergens field from OFF
		const fromAllergens = productAllergens.filter(a => userKeys.has(a.toLowerCase()));
		if (fromAllergens.length > 0) return fromAllergens;
		// Fallback: keyword search in ingredients_text for legacy/manual products
		const text = (product.ingredients_text ?? '').toLowerCase();
		if (!text) return [];
		return list
			.filter(a => text.includes(a.ingredient.toLowerCase()))
			.map(a => a.ingredient);
	}

	let allergenWarnings = $derived((() => {
		if (!selected) return { mine: [], partner: [] };
		const mine    = shareMode !== 'only' ? checkAllergens(selected, myAllergies)      : [];
		const part    = shareMode !== null   ? checkAllergens(selected, partnerAllergies) : [];
		return { mine, partner: part };
	})());

	// Show a "no allergen info" notice when the product has no allergen data
	// and whoever is actually eating it has allergies registered, but no warning triggered.
	// If shareMode === 'only', I'm not eating it — only check partner.
	// If shareMode === null, only I'm eating it — only check mine.
	let noAllergenInfo = $derived(
		selected !== null &&
		selected.allergens === null &&
		allergenWarnings.mine.length === 0 &&
		allergenWarnings.partner.length === 0 &&
		(
			(shareMode !== 'only'  && myAllergies.length > 0) ||
			(shareMode !== null    && partnerAllergies.length > 0)
		)
	);

	function selectProduct(product: Product) {
		selected = product;
		grams = getLastGrams(product.id);
	}

	async function loadAllergies() {
		myAllergies = await api.get<AllergyInfo[]>('/allergies').catch(() => []);
	}

	async function loadPartnerAllergies(partnerId: number) {
		partnerAllergies = await api.get<AllergyInfo[]>(`/allergies?user_id=${partnerId}`).catch(() => []);
	}

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

	async function loadFrequent() {
		loadingFrequent = true;
		frequentFromCache = false;
		try {
			const [f, r] = await Promise.all([
				api.get<FrequentProduct[]>('/products/frequent?limit=15'),
				api.get<FrequentRecipe[]>('/recipes/frequent?limit=5').catch(() => []),
			]);
			frequent = f;
			frequentRecipes = r;
			// Persistir para uso offline
			if (f.length > 0) cacheSet('frequent_products', f);
		} catch {
			// Offline — intentar caché
			const cached = cacheGet<FrequentProduct[]>('frequent_products');
			if (cached) {
				frequent = cached.data;
				frequentFromCache = true;
			}
			frequentRecipes = [];
		} finally {
			loadingFrequent = false;
		}
	}

	async function logRecipe(recipe: FrequentRecipe['recipe']) {
		saving = true;
		error = '';
		try {
			await api.post<DiaryEntry[]>('/diary/recipe', {
				recipe_id: recipe.id,
				meal_type: mealType,
				consumed_at: consumedAt(selectedDate),
				also_for_user_id: shareMode === 'also' ? partner?.id : null,
			only_for_user_id: shareMode === 'only' ? partner?.id : null,
			});
			goto('/');
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		} finally {
			saving = false;
		}
	}

	$effect(() => {
		api.get<User[]>('/users').then(u => {
			users = u;
			const p = u.find(x => x.id !== auth.user?.id);
			if (p) loadPartnerAllergies(p.id);
		}).catch(() => {});
		loadRecommendations();
		loadFrequent();
		loadAllergies();
		loadFavorites();
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
		barcodeNotFound = false;
		error = '';
		try {
			const p = await api.get<Product>(`/products/barcode/${barcode.trim()}`);
			selectProduct(p);
		} catch {
			barcodeNotFound = true;
		} finally {
			searching = false;
		}
	}

	async function scanBarcode() {
		barcode = '';
		barcodeNotFound = false;
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

	// ── Inventory consumption (optional, after diary entry) ────────────────
	let inventoryMatch: InventoryItem | null = $state(null);
	let consumePromptOpen = $state(false);
	let showConsumeModal = $state(false);

	async function findInventoryMatch(productId: number): Promise<InventoryItem | null> {
		try {
			const items = await api.get<InventoryItem[]>('/inventory');
			return items.find((i) => i.product_id === productId && i.quantity_base > 0) ?? null;
		} catch {
			return null;
		}
	}

	function dismissConsumePrompt() {
		consumePromptOpen = false;
		inventoryMatch = null;
		goto('/');
	}

	function openConsumeModal() {
		consumePromptOpen = false;
		showConsumeModal = true;
	}

	function onConsumeModalClose() {
		showConsumeModal = false;
		inventoryMatch = null;
		goto('/');
	}

	async function logEntry() {
		if (!selected) return;
		saving = true;
		error = '';
		const payload = {
			product_id: selected.id,
			grams,
			meal_type: mealType,
			consumed_at: consumedAt(selectedDate),
			also_for_user_id: shareMode === 'also' ? partner?.id : null,
			only_for_user_id: shareMode === 'only' ? partner?.id : null,
		};
		try {
			if (connectivity.isOffline) {
				// Queue for later sync
				syncQueue.enqueue({
					method: 'POST',
					path: '/diary',
					body: payload,
					label: `${selected.name} · ${grams}g`,
				});
				saveLastGrams(selected.id, grams);
				goto('/?pending=1');
				return;
			}
			await api.post<DiaryEntry[]>('/diary', payload);
			saveLastGrams(selected.id, grams);

			// After successful diary entry, check inventory for this product
			const match = await findInventoryMatch(selected.id);
			if (match) {
				inventoryMatch = match;
				consumePromptOpen = true;
			} else {
				goto('/');
			}
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

	// ── Orden y agrupación de "Mis alimentos" ────────────────────────────────
	let sortOrder = $state<'frequency' | 'alpha'>('frequency');

	// Lista plana de productos frecuentes, con el orden elegido
	let sortedFrequentProducts = $derived((() => {
		const prods = frequent.map(f => f.product);
		if (sortOrder === 'alpha') {
			return [...prods].sort((a, b) => a.name.localeCompare(b.name, 'es', { sensitivity: 'base' }));
		}
		return prods; // ya viene ordenado por frecuencia del backend
	})());

	// Agrupado por primera letra (solo en modo alpha)
	type LetterGroup = { letter: string; products: typeof sortedFrequentProducts };
	let frequentByLetter = $derived((() => {
		if (sortOrder !== 'alpha') return [] as LetterGroup[];
		const groups: LetterGroup[] = [];
		for (const p of sortedFrequentProducts) {
			const letter = p.name[0].toUpperCase();
			const last = groups[groups.length - 1];
			if (last && last.letter === letter) {
				last.products.push(p);
			} else {
				groups.push({ letter, products: [p] });
			}
		}
		return groups;
	})());
</script>

<!-- ═══════════════════════════════════════════════════════
     DETAIL VIEW — producto seleccionado
═══════════════════════════════════════════════════════ -->
{#if selected && !showManual && !showEdit}
	<!-- Header -->
	<div class="add-header">
		<button class="glass-btn" onclick={() => (selected = null)} aria-label="Volver">
			<svg width="18" height="18" viewBox="0 0 24 24" fill="none">
				<path d="M15 6l-6 6 6 6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
			</svg>
		</button>
		<div style="flex:1; min-width:0;">
			<div class="header-eyebrow">Detalle</div>
			<div class="header-title" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{selected.name}</div>
		</div>
		<button
			class="glass-btn"
			onclick={() => toggleFavorite(selected!.id)}
			aria-label={favoriteIds.has(selected.id) ? 'Quitar de favoritos' : 'Añadir a favoritos'}
			title={favoriteIds.has(selected.id) ? 'Quitar de favoritos' : 'Añadir a favoritos'}
			disabled={favoriteToggling}
			style="color: {favoriteIds.has(selected.id) ? 'oklch(85% 0.22 55)' : 'rgba(255,255,255,0.5)'} !important;"
		>
			<svg width="17" height="17" viewBox="0 0 24 24" fill={favoriteIds.has(selected.id) ? 'currentColor' : 'none'}>
				<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
			</svg>
		</button>
		<button class="glass-btn" onclick={startEdit} aria-label="Editar producto" title="Corregir datos del producto">
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
				<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
				<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
			</svg>
		</button>
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

	<!-- Partner share (3 estados) -->
	{#if users.length > 1 && partner}
		<div
			class="share-card"
			class:share-card-also={shareMode === 'also'}
			class:share-card-only={shareMode === 'only'}
			style="margin-bottom:1rem;"
		>
			<div class="share-badge-icon"
				class:share-badge-icon-also={shareMode === 'also'}
				class:share-badge-icon-only={shareMode === 'only'}
			>
				{#if shareMode === null}👤{:else if shareMode === 'also'}👥{:else}<span style="font-size:0.625rem;">👤→</span>{/if}
			</div>
			<div style="flex:1; min-width:0; text-align:left;">
				{#if shareMode === null}
					<div style="font-size:0.8125rem; font-weight:700; color:rgba(255,255,255,0.5);">Sin compartir</div>
					<div style="font-size:0.6875rem; color:rgba(255,255,255,0.35); margin-top:0.125rem;">Solo tu cuenta</div>
				{:else if shareMode === 'also'}
					<div style="font-size:0.8125rem; font-weight:700;">También para {partner.name}</div>
					<div style="font-size:0.6875rem; color:rgba(255,255,255,0.55); margin-top:0.125rem;">Se registra en las dos cuentas</div>
				{:else}
					<div style="font-size:0.8125rem; font-weight:700; color:oklch(80% 0.18 45);">Solo para {partner.name}</div>
					<div style="font-size:0.6875rem; color:rgba(255,255,255,0.55); margin-top:0.125rem;">Tú no lo registras</div>
				{/if}
			</div>
			<!-- Segmented pill con sliding thumb -->
			<div class="seg-pill">
				<div class="seg-pill-thumb" style="
					left: {shareMode === null ? '3px' : shareMode === 'also' ? '33px' : '63px'};
					background: {shareMode === 'only'
						? 'linear-gradient(135deg, oklch(85% 0.18 45), oklch(68% 0.22 40))'
						: shareMode === 'also'
							? 'linear-gradient(135deg, oklch(82% 0.18 160), oklch(68% 0.2 170))'
							: 'rgba(255,255,255,0.12)'};
				"></div>
				<button class="seg-pill-btn" class:seg-pill-active={shareMode === null}
					onclick={() => shareMode = null} aria-label="Solo yo">👤</button>
				<button class="seg-pill-btn" class:seg-pill-active={shareMode === 'also'}
					onclick={() => shareMode = 'also'} aria-label="Los dos">👥</button>
				<button class="seg-pill-btn" class:seg-pill-active={shareMode === 'only'}
					onclick={() => shareMode = 'only'} aria-label="Solo {partner.name}">👤→</button>
			</div>
		</div>
	{/if}

	<!-- No allergen info notice -->
	{#if noAllergenInfo}
		<div class="allergen-unknown-notice">
			<span style="font-size:1rem; flex-shrink:0;">ℹ️</span>
			<span>No tenemos información sobre alérgenos de este producto. Revisa el envase antes de consumirlo.</span>
		</div>
	{/if}

	<!-- Allergy warning -->
	{#if allergenWarnings.mine.length > 0 || allergenWarnings.partner.length > 0}
		<div class="allergy-banner">
			<div class="allergy-banner-icon">⚠️</div>
			<div class="allergy-banner-body">
				<div class="allergy-banner-title">Alérgeno detectado</div>
				{#if allergenWarnings.mine.length > 0}
					<div class="allergy-banner-row">
						<span class="allergy-banner-who">Tú:</span>
						{#each allergenWarnings.mine as a}
							<span class="allergy-tag allergy-tag-mine">{allergenLabel(a)}</span>
						{/each}
					</div>
				{/if}
				{#if allergenWarnings.partner.length > 0 && partner}
					<div class="allergy-banner-row">
						<span class="allergy-banner-who">{partner.name}:</span>
						{#each allergenWarnings.partner as a}
							<span class="allergy-tag allergy-tag-partner">{allergenLabel(a)}</span>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	{/if}

	{#if error}<p class="add-error">{error}</p>{/if}

	<button class="btn-submit" onclick={logEntry} disabled={saving}>
		{#if saving}
			Guardando...
		{:else if shareMode === 'also'}
			Registrar · 👥
		{:else if shareMode === 'only'}
			Registrar solo para {partner?.name}
		{:else}
			Registrar
		{/if}
	</button>

<!-- ═══════════════════════════════════════════════════════
     EDIT PRODUCT FORM
═══════════════════════════════════════════════════════ -->
{:else if showEdit}
	<div class="add-header">
		<button class="glass-btn" onclick={() => (showEdit = false)} aria-label="Volver">
			<svg width="18" height="18" viewBox="0 0 24 24" fill="none">
				<path d="M15 6l-6 6 6 6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
			</svg>
		</button>
		<div style="flex:1; min-width:0;">
			<div class="header-eyebrow">Editar</div>
			<div class="header-title" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{selected?.name}</div>
		</div>
	</div>

	<p style="font-size:0.75rem; color:rgba(255,255,255,0.45); margin:0 0 0.875rem; line-height:1.4;">
		Corrige los valores si la información de la base de datos no es exacta. Los cambios se guardarán para todos.
	</p>

	<div class="glass-card" style="display:flex; flex-direction:column; gap:0.75rem; margin-bottom:1rem;">
		<div class="manual-field">
			<label for="e-name">Nombre</label>
			<input id="e-name" bind:value={editName} required class="field-input" />
		</div>
		<div class="manual-field">
			<label for="e-brand">Marca <span style="color:rgba(255,255,255,0.4);">(opcional)</span></label>
			<input id="e-brand" bind:value={editBrand} class="field-input" />
		</div>
		<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
			<div class="manual-field">
				<label for="e-cal">Kcal / 100g</label>
				<input id="e-cal" type="number" bind:value={editCal} min="0" step="0.1" class="field-input" />
			</div>
			<div class="manual-field">
				<label for="e-prot">Prot / 100g</label>
				<input id="e-prot" type="number" bind:value={editProt} min="0" step="0.1" class="field-input" />
			</div>
			<div class="manual-field">
				<label for="e-carbs">Carb / 100g</label>
				<input id="e-carbs" type="number" bind:value={editCarbs} min="0" step="0.1" class="field-input" />
			</div>
			<div class="manual-field">
				<label for="e-fat">Grasa / 100g</label>
				<input id="e-fat" type="number" bind:value={editFat} min="0" step="0.1" class="field-input" />
			</div>
		</div>
	</div>

	{#if editError}<p class="add-error">{editError}</p>{/if}

	<button class="btn-submit" onclick={saveEdit} disabled={editSaving}>
		{editSaving ? 'Guardando…' : 'Guardar cambios'}
	</button>

<!-- ═══════════════════════════════════════════════════════
     MANUAL PRODUCT FORM
═══════════════════════════════════════════════════════ -->
{:else if showManual}
	<div class="add-header">
		<button class="glass-btn" onclick={() => (showManual = false)} aria-label="Volver">
			<svg width="18" height="18" viewBox="0 0 24 24" fill="none">
				<path d="M15 6l-6 6 6 6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
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
			<svg width="18" height="18" viewBox="0 0 24 24" fill="none">
				<path d="M15 6l-6 6 6 6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
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
			<svg width="20" height="20" viewBox="0 0 24 24" fill="none">
				<path d="M4 6v12M7 6v12M10 6v12M13 6v12M17 6v12M20 6v12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
			</svg>
		</button>
	</div>

	<!-- Barcode row -->
	{#if barcode}
		{#if barcodeNotFound}
			<div style="margin-bottom:0.75rem; background:oklch(65% 0.22 25 / 0.08); border:1px solid oklch(65% 0.22 25 / 0.2); border-radius:16px; padding:0.875rem;">
				<div style="font-size:0.75rem; color:oklch(75% 0.18 25); font-weight:700; margin-bottom:0.25rem;">Producto no encontrado</div>
				<div style="font-size:0.7rem; color:rgba(255,255,255,0.5); margin-bottom:0.75rem;">El código <span style="font-variant-numeric:tabular-nums;">{barcode}</span> no está en la base de datos.</div>
				<div style="display:flex; gap:0.5rem;">
					<button onclick={() => { barcodeNotFound = false; barcode = ''; }} class="filter-chip" style="flex:1;">
						Escanear otro
					</button>
					<button onclick={() => { barcodeNotFound = false; barcode = ''; showManual = true; }} class="filter-chip" style="flex:1;">
						✏️ Crear manual
					</button>
				</div>
			</div>
		{:else}
			<div style="margin-bottom:0.5rem; display:flex; gap:0.5rem; align-items:center;">
				<div style="flex:1; min-width:0;">
					<div style="font-size:0.7rem; color:rgba(255,255,255,0.45); margin-bottom:0.2rem;">Código escaneado</div>
					<div style="font-size:0.875rem; font-weight:600; color:#fff; font-variant-numeric:tabular-nums;">{barcode}</div>
				</div>
				<button onclick={searchByBarcode} disabled={searching} class="btn-submit" style="padding:0 1.25rem; height:44px; border-radius:12px; width:auto; flex-shrink:0;">
					{searching ? 'Buscando...' : 'Añadir →'}
				</button>
			</div>
		{/if}
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
		<button onclick={() => { activeFilter = 'recent'; }}      class="filter-chip" class:filter-chip-active={activeFilter === 'recent'}>🕒 Recientes{#if frequentFromCache}<span class="chip-offline-dot" title="Guardado sin conexión">·</span>{/if}</button>
		<button onclick={() => { activeFilter = 'favorites'; }}   class="filter-chip" class:filter-chip-active={activeFilter === 'favorites'}>⭐ Favoritos</button>
		<button onclick={() => { activeFilter = 'manual'; showManual = true; }} class="filter-chip">✏️ Manual</button>
	</div>

	<!-- Results section (when query) -->
	{#if query}
		{#if searching && results.length === 0}
			<div class="loading-row">Buscando...</div>
		{:else if results.length > 0}
			<div class="section-header">
				<div><div class="section-title">Resultados</div></div>
				<div class="section-count">{results.length} encontrados</div>
			</div>
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
	{/if}

	<!-- Sin query: contenido según chip activo -->
	{#if !query}

		<!-- ── SUGERENCIAS ── -->
		{#if activeFilter === 'suggestions'}
			{#if loadingRecs}
				<div class="loading-row">Cargando sugerencias...</div>
			{:else if recommendations.length > 0}
				<div class="section-header">
					<div>
						<div class="section-title">Sugerencias para ahora</div>
						<div class="section-sub">Basado en tus calorías restantes</div>
					</div>
				</div>
				<div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:1.25rem;">
					{#each recommendations as rec (rec.product.id)}
						<button class="product-row" onclick={() => selectProduct(rec.product)}>
							<div class="product-avatar" style="background: linear-gradient(135deg, oklch(78% 0.12 {hashHue(rec.product.name)} / 0.35), oklch(60% 0.12 {hashHue(rec.product.name)} / 0.15));">{productGlyph(rec.product.name)}</div>
							<div style="flex:1; min-width:0; text-align:left;">
								<div class="product-name">{rec.product.name}</div>
								<div class="product-brand">{rec.reason}</div>
							</div>
							<div style="text-align:right; flex-shrink:0;">
								<div class="product-kcal">{Math.round(rec.estimated_calories)}<span class="product-kcal-unit">kcal</span></div>
								<div class="product-per">{rec.suggested_grams}g sugerido</div>
							</div>
						</button>
					{/each}
				</div>
			{:else}
				<div class="loading-row" style="color:rgba(255,255,255,0.35);">Sin sugerencias por ahora</div>
			{/if}
		{/if}

		<!-- ── FAVORITOS ── -->
		{#if activeFilter === 'favorites'}
			{#if favorites.length === 0}
				<div class="loading-row" style="color:rgba(255,255,255,0.35);">
					<div style="font-size:1.5rem; margin-bottom:0.5rem;">⭐</div>
					<div>Aún no tienes favoritos</div>
					<div style="font-size:0.7rem; margin-top:0.25rem; opacity:0.6;">Pulsa la estrella en cualquier producto para guardarlo aquí</div>
				</div>
			{:else}
				<div class="section-header">
					<div>
						<div class="section-title">Favoritos</div>
						<div class="section-sub">{favorites.length} producto{favorites.length !== 1 ? 's' : ''}</div>
					</div>
				</div>
				<div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:1.25rem;">
					{#each favorites as product (product.id)}
						<div class="fav-row-wrap">
							<button class="product-row" onclick={() => selectProduct(product)}>
								<div class="product-avatar" style="background: linear-gradient(135deg, oklch(78% 0.12 {hashHue(product.name)} / 0.35), oklch(60% 0.12 {hashHue(product.name)} / 0.15));">{productGlyph(product.name)}</div>
								<div style="flex:1; min-width:0; text-align:left;">
									<div class="product-name">{product.name}</div>
									<div class="product-brand">{product.brand ?? '—'}</div>
								</div>
								<div style="text-align:right; flex-shrink:0;">
									<div class="product-kcal">{product.calories_per_100g}<span class="product-kcal-unit">kcal</span></div>
									<div class="product-per">/100{isDrink(product) ? 'ml' : 'g'}</div>
								</div>
							</button>
							<button
								class="fav-star-btn"
								onclick={() => toggleFavorite(product.id)}
								aria-label="Quitar de favoritos"
								disabled={favoriteToggling}
							>★</button>
						</div>
					{/each}
				</div>
			{/if}
		{/if}

		<!-- ── RECIENTES ── -->
		{#if activeFilter === 'recent'}
			{#if loadingFrequent}
				<div class="loading-row">Cargando historial...</div>
			{:else if frequentRecipes.length === 0 && frequent.length === 0}
				<div class="loading-row" style="color:rgba(255,255,255,0.35);">Aún no tienes alimentos recientes</div>
			{:else}
				{#if frequentFromCache}
					<div class="offline-cache-notice">📦 Mostrando alimentos guardados · sin conexión</div>
				{/if}
				<!-- Header con toggle de orden -->
				<div class="section-header">
					<div>
						<div class="section-title">Mis alimentos</div>
						<div class="section-sub">Por frecuencia de uso</div>
					</div>
					<div style="display:flex; gap:0.25rem; background:rgba(255,255,255,0.05); border-radius:99px; padding:3px; border:1px solid rgba(255,255,255,0.08);">
						<button
							onclick={() => sortOrder = 'frequency'}
							style="padding:0.25rem 0.625rem; border-radius:99px; border:none; cursor:pointer; font-family:inherit; font-size:0.6875rem; font-weight:700; background:{sortOrder==='frequency' ? 'rgba(255,255,255,0.12)' : 'transparent'}; color:{sortOrder==='frequency' ? '#fff' : 'rgba(255,255,255,0.45)'};">
							🕒
						</button>
						<button
							onclick={() => sortOrder = 'alpha'}
							style="padding:0.25rem 0.625rem; border-radius:99px; border:none; cursor:pointer; font-family:inherit; font-size:0.6875rem; font-weight:700; background:{sortOrder==='alpha' ? 'rgba(255,255,255,0.12)' : 'transparent'}; color:{sortOrder==='alpha' ? '#fff' : 'rgba(255,255,255,0.45)'};">
							A-Z
						</button>
					</div>
				</div>

				<!-- Recetas frecuentes (sin agrupación, siempre primero) -->
				{#if frequentRecipes.length > 0}
					<div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:0.75rem;">
						{#each frequentRecipes as f (f.recipe.id)}
							{@const totalKcal = f.recipe.ingredients.reduce((sum, ing) => sum + (ing.product?.calories_per_100g ?? 0) * ing.grams / 100, 0)}
							<button class="product-row" onclick={() => logRecipe(f.recipe)} disabled={saving}>
								<div class="product-avatar" style="background: linear-gradient(135deg, oklch(75% 0.15 160 / 0.3), oklch(60% 0.15 160 / 0.15));">🍳</div>
								<div style="flex:1; min-width:0; text-align:left;">
									<div class="product-name">{f.recipe.name}</div>
									<div class="product-brand">{f.recipe.ingredients.length} ingredientes</div>
								</div>
								<div style="text-align:right; flex-shrink:0;">
									<div class="product-kcal">{Math.round(totalKcal)}<span class="product-kcal-unit">kcal</span></div>
									<div class="product-per" style="color:oklch(75% 0.15 160);">receta</div>
								</div>
							</button>
						{/each}
					</div>
				{/if}

				<!-- Productos frecuentes -->
				{#if sortOrder === 'frequency'}
					<!-- Sin agrupar, orden por frecuencia -->
					<div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:1.25rem;">
						{#each sortedFrequentProducts as product (product.id)}
							<button class="product-row" onclick={() => selectProduct(product)}>
								<div class="product-avatar" style="background: linear-gradient(135deg, oklch(78% 0.12 {hashHue(product.name)} / 0.35), oklch(60% 0.12 {hashHue(product.name)} / 0.15));">{productGlyph(product.name)}</div>
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
				{:else}
					<!-- Agrupado por letra -->
					<div style="margin-bottom:1.25rem;">
						{#each frequentByLetter as group (group.letter)}
							<div class="letter-divider">{group.letter}</div>
							<div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:0.75rem;">
								{#each group.products as product (product.id)}
									<button class="product-row" onclick={() => selectProduct(product)}>
										<div class="product-avatar" style="background: linear-gradient(135deg, oklch(78% 0.12 {hashHue(product.name)} / 0.35), oklch(60% 0.12 {hashHue(product.name)} / 0.15));">{productGlyph(product.name)}</div>
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
						{/each}
					</div>
				{/if}
			{/if}
		{/if}

	{/if} <!-- /!query -->

	{#if error}<p class="add-error">{error}</p>{/if}
{/if}

<!-- ── Consume prompt (after diary entry, if item exists in inventory) ── -->
{#if consumePromptOpen && inventoryMatch}
	<div
		class="consume-backdrop"
		role="presentation"
		onclick={dismissConsumePrompt}
	></div>
	<div class="consume-prompt" role="dialog" aria-modal="true">
		<div class="consume-prompt-icon">📦</div>
		<h2 class="consume-prompt-title">¿Consumir del inventario?</h2>
		<p class="consume-prompt-sub">
			Tienes <strong>{inventoryMatch.product_name}</strong> en tu inventario.
		</p>
		<div class="consume-prompt-stock">
			{inventoryMatch.quantity_base.toLocaleString()}
			{inventoryMatch.unit === 'unit'
				? inventoryMatch.quantity_base === 1
					? 'unidad'
					: 'unidades'
				: inventoryMatch.unit}
			disponibles
		</div>
		<div class="consume-prompt-actions">
			<button class="consume-prompt-no" onclick={dismissConsumePrompt}>
				No, solo registrar
			</button>
			<button class="consume-prompt-yes" onclick={openConsumeModal}>
				Sí, restar del stock
			</button>
		</div>
	</div>
{/if}

<!-- ── Consume modal (when user confirms "Sí, restar") ── -->
{#if showConsumeModal && inventoryMatch}
	<ConsumeFoodModal
		item={inventoryMatch}
		initialQuantity={inventoryMatch.unit === 'g' ? grams : 1}
		initialUnit={inventoryMatch.unit}
		onclose={onConsumeModalClose}
	/>
{/if}

<style>
	/* ── No allergen info notice ── */
	.allergen-unknown-notice {
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.1);
		border-radius: 0.75rem;
		padding: 0.625rem 0.875rem;
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.45);
		line-height: 1.4;
		margin-bottom: 0.75rem;
	}

	/* ── Allergy banner ── */
	.allergy-banner {
		display: flex;
		gap: 0.625rem;
		align-items: flex-start;
		background: oklch(35% 0.15 40 / 0.25);
		border: 1px solid oklch(60% 0.2 40 / 0.4);
		border-radius: 16px;
		padding: 0.75rem 0.875rem;
		margin-bottom: 0.875rem;
		animation: banner-in 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
	}
	@keyframes banner-in {
		from { opacity: 0; transform: translateY(-4px) scale(0.98); }
		to   { opacity: 1; transform: translateY(0) scale(1); }
	}
	.allergy-banner-icon {
		font-size: 1.125rem;
		flex-shrink: 0;
		margin-top: 0.05rem;
	}
	.allergy-banner-body { flex: 1; min-width: 0; }
	.allergy-banner-title {
		font-size: 0.75rem;
		font-weight: 700;
		color: oklch(82% 0.18 45);
		letter-spacing: 0.02em;
		margin-bottom: 0.375rem;
	}
	.allergy-banner-row {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 0.375rem;
		margin-bottom: 0.25rem;
	}
	.allergy-banner-row:last-child { margin-bottom: 0; }
	.allergy-banner-who {
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.45);
		font-weight: 600;
		flex-shrink: 0;
	}
	.allergy-tag {
		font-size: 0.6875rem;
		font-weight: 600;
		border-radius: 99px;
		padding: 0.15rem 0.5rem;
	}
	.allergy-tag-mine {
		background: oklch(45% 0.2 25 / 0.35);
		border: 1px solid oklch(60% 0.2 25 / 0.45);
		color: oklch(88% 0.15 25);
	}
	.allergy-tag-partner {
		background: oklch(45% 0.18 280 / 0.3);
		border: 1px solid oklch(60% 0.18 280 / 0.4);
		color: oklch(88% 0.12 280);
	}

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
		color: white !important;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		transition: background 0.15s;
		padding: 0 !important;
		box-shadow: none !important;
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
		color: oklch(85% 0.15 160) !important;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		transition: background 0.15s;
		padding: 0 !important;
		box-shadow: none !important;
	}
	.barcode-btn:hover { background: rgba(255,255,255,0.1); }

	/* ── Filter chips ── */
	/* ── Letter divider ── */
	.letter-divider {
		font-size: 0.625rem;
		font-weight: 800;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: rgba(255,255,255,0.35);
		padding: 0.5rem 0.25rem 0.3rem;
		border-bottom: 1px solid rgba(255,255,255,0.06);
		margin-bottom: 0.375rem;
	}

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
		transition: background 0.25s, border-color 0.25s;
	}
	.share-card-also {
		background: oklch(75% 0.18 165 / 0.08);
		border-color: oklch(80% 0.17 165 / 0.3);
	}
	.share-card-only {
		background: oklch(65% 0.2 45 / 0.08);
		border-color: oklch(70% 0.2 45 / 0.3);
	}
	.share-badge-icon {
		width: 40px;
		height: 40px;
		border-radius: 12px;
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.08);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.125rem;
		flex-shrink: 0;
		transition: background 0.25s, border-color 0.25s;
	}
	.share-badge-icon-also {
		background: oklch(75% 0.18 165 / 0.18);
		border-color: oklch(80% 0.17 165 / 0.4);
	}
	.share-badge-icon-only {
		background: oklch(65% 0.2 45 / 0.18);
		border-color: oklch(70% 0.2 45 / 0.4);
	}

	/* ── Segmented pill con sliding thumb ── */
	.seg-pill {
		position: relative;
		display: flex;
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.1);
		border-radius: 99px;
		padding: 3px;
		gap: 2px;
		flex-shrink: 0;
	}
	.seg-pill-thumb {
		position: absolute;
		top: 3px;
		width: 28px;
		height: 28px;
		border-radius: 99px;
		box-shadow: 0 2px 8px rgba(0,0,0,0.35);
		transition: left 0.28s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.22s ease;
		pointer-events: none;
		z-index: 1;
	}
	.seg-pill-btn {
		width: 28px;
		height: 28px;
		border-radius: 99px;
		border: none;
		background: transparent;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.75rem;
		position: relative;
		z-index: 2;
		opacity: 0.3;
		transition: opacity 0.18s;
		padding: 0;
		line-height: 1;
	}
	.seg-pill-active { opacity: 1; }

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

	/* ── Favorite row wrapper ── */
	.fav-row-wrap {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.fav-row-wrap .product-row {
		flex: 1;
		min-width: 0;
	}

	/* ── Favorite star button (inline in list) ── */
	.fav-star-btn {
		width: 30px;
		height: 30px;
		border-radius: 50%;
		border: none;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.875rem;
		flex-shrink: 0;
		transition: transform 0.15s, background 0.15s;
		padding: 0;
		background: oklch(85% 0.22 55 / 0.12);
		color: oklch(85% 0.22 55);
	}
	.fav-star-btn:hover { transform: scale(1.15); background: oklch(85% 0.22 55 / 0.2); }
	.fav-star-btn:disabled { opacity: 0.5; cursor: not-allowed; }

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
	.chip-offline-dot {
		display: inline-block;
		margin-left: 0.3rem;
		color: oklch(80% 0.18 55);
		font-weight: 900;
		font-size: 1rem;
		line-height: 1;
		vertical-align: middle;
	}
	.offline-cache-notice {
		font-size: 0.72rem;
		color: oklch(75% 0.14 55);
		background: oklch(75% 0.14 55 / 0.08);
		border: 1px solid oklch(75% 0.14 55 / 0.2);
		border-radius: 8px;
		padding: 0.4rem 0.75rem;
		margin-bottom: 0.75rem;
		text-align: center;
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

	/* ── Consume prompt ── */
	.consume-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		backdrop-filter: blur(4px);
		z-index: 90;
	}
	.consume-prompt {
		position: fixed;
		bottom: 0;
		left: 50%;
		transform: translateX(-50%);
		width: min(420px, 100vw);
		background: oklch(18% 0.03 260);
		border: 1px solid oklch(35% 0.06 260 / 0.5);
		border-bottom: none;
		border-radius: 20px 20px 0 0;
		padding: 1.5rem 1.5rem 2rem;
		z-index: 91;
		text-align: center;
	}
	.consume-prompt-icon {
		font-size: 2rem;
		margin-bottom: 0.5rem;
	}
	.consume-prompt-title {
		font-size: 1rem;
		font-weight: 800;
		color: #fff;
		margin: 0 0 0.25rem;
	}
	.consume-prompt-sub {
		font-size: 0.8125rem;
		color: rgba(255, 255, 255, 0.65);
		margin: 0 0 1rem;
	}
	.consume-prompt-stock {
		font-size: 0.75rem;
		color: oklch(85% 0.17 160);
		font-weight: 700;
		margin-bottom: 1rem;
	}
	.consume-prompt-actions {
		display: flex;
		gap: 0.5rem;
	}
	.consume-prompt-actions button {
		flex: 1;
		padding: 0.75rem;
		border-radius: 0.75rem;
		font-family: inherit;
		font-weight: 700;
		font-size: 0.875rem;
		cursor: pointer;
	}
	.consume-prompt-no {
		background: rgba(255, 255, 255, 0.06);
		border: 1px solid rgba(255, 255, 255, 0.1);
		color: rgba(255, 255, 255, 0.7);
	}
	.consume-prompt-yes {
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		border: none;
		color: #041010;
	}
</style>
