<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import { connectivity } from '$lib/stores/connectivity.svelte';
	import { cacheSet, cacheGet } from '$lib/cache';
	import { syncQueue } from '$lib/stores/sync-queue.svelte';
	import { pushStore } from '$lib/stores/push.svelte';
	import NotifModal from '$lib/components/NotifModal.svelte';
	import { toast } from '$lib/stores/toast.svelte';
	import { productUnit } from '$lib/drink';
	import type { DaySummary, Goals, WaterDay, FrequentProduct, FrequentRecipe, User, DiaryEntry, CreatineToday, CheatDayToday, MealSection, DayTotals, SupplementToday, UserSupplement, MoodEntry } from '$lib/types';
	import { MEAL_ORDER, MOOD_WORST_EMOJI } from '$lib/types';
	import { t, tc, mealLabel, fmtTime as fmtTimeI18n } from '$lib/i18n/index.svelte';
	import { identityColor, nameHue } from '$lib/avatars';

	const MEAL_HUES: Record<string, number> = { breakfast: 45, lunch: 165, dinner: 285, snack: 220 };
	import {
		DayNav,
		CalorieRing,
		MacroBar,
		MealHeader,
		Modal,
		EmptyState,
		Avatar,
	} from '$lib/components';
	import TrialBanner from '$lib/components/uro/TrialBanner.svelte';

	if (!auth.isLoggedIn) goto('/login');

	let today = $state(new Date().toISOString().slice(0, 10));
	let isToday = $derived(today === new Date().toISOString().slice(0, 10));
	let summary: DaySummary | null = $state(null);
	let goals: Goals | null = $state(null);
	let water: WaterDay | null = $state(null);
	let frequent: FrequentProduct[] = $state([]);
	let frequentRecipes: FrequentRecipe[] = $state([]);
	// The streak itself doesn't depend on which day is being browsed (the
	// endpoint always answers for "now"); only whether we SHOW it does — the
	// flame badge is hidden while looking at a past day, same as before.
	let currentStreak = $state(0);
	let streak = $derived(isToday ? currentStreak : 0);
	let users: User[] = $state([]);
	// ── Pareja: ver su día intercalado en el mío ──
	// El resumen de la pareja se carga siempre (si la tienes); el chip solo decide
	// si sus comidas se intercalan entre las tuyas.
	let showPartner = $state(typeof localStorage !== 'undefined' && localStorage.getItem('uro_show_partner') === '1');
	let partnerSummary: DaySummary | null = $state(null);
	let loading = $state(true);
	let fromCache = $state(false);
	let copyingYesterday = $state(false);
	let copyingMealType: string | null = $state(null);
	let creatine: CreatineToday | null = $state(null);
	let togglingCreatine = $state(false);
	let supplements: SupplementToday[] = $state([]);
	let showSupplModal = $state(false);
	let newSuppName = $state('');
	let addingSuppName = $state(false);
	let suppEnabled = $derived(typeof localStorage !== 'undefined' ? localStorage.getItem('supplements_enabled') !== 'false' : true);
	let lastWaterMl = $state(250); // tracks last addWater amount for offline undo

	function sumTotals(entries: DiaryEntry[]): DayTotals {
		return {
			calories: entries.reduce((s, e) => s + e.calories, 0),
			protein:  entries.reduce((s, e) => s + e.protein, 0),
			carbs:    entries.reduce((s, e) => s + e.carbs, 0),
			fat:      entries.reduce((s, e) => s + e.fat, 0),
		};
	}

	// Reagrupa las entradas en secciones por comida (orden fijo). Reconstruir en vez
	// de mutar in-place hace que al cambiar el meal_type de una entrada su tarjeta se
	// mueva de sección al instante, y que las comidas vacías desaparezcan.
	function regroupMeals(entries: DiaryEntry[]): MealSection[] {
		const meals: MealSection[] = [];
		for (const mt of MEAL_ORDER) {
			const me = entries.filter(e => e.meal_type === mt);
			if (me.length === 0) continue;
			meals.push({ meal_type: mt, label: mealLabel(mt), totals: sumTotals(me), entries: me });
		}
		return meals;
	}

	function optimisticDeleteEntry(id: number) {
		if (!summary) return;
		const entries = summary.entries.filter(e => e.id !== id);
		const totals = sumTotals(entries);
		// net_calories = consumidas - quemadas (el ejercicio no cambia al borrar comida);
		// hay que recalcularlo o el número central del anillo se queda obsoleto.
		summary = { ...summary, totals, net_calories: totals.calories - (summary.calories_burned ?? 0), entries, meals: regroupMeals(entries) };
	}

	function optimisticEditEntry(id: number, newGrams: number, newMealType: MealType) {
		if (!summary) return;
		const entry = summary.entries.find(e => e.id === id);
		if (!entry?.product) return;
		const p = entry.product;
		const f = newGrams / 100;
		const updated: DiaryEntry = {
			...entry,
			grams:     newGrams,
			meal_type: newMealType,
			calories:  Math.round(p.calories_per_100g * f),
			protein:   Math.round(p.protein_per_100g  * f * 10) / 10,
			carbs:     Math.round(p.carbs_per_100g    * f * 10) / 10,
			fat:       Math.round(p.fat_per_100g      * f * 10) / 10,
		};
		const entries = summary.entries.map(e => e.id === id ? updated : e);
		const totals = sumTotals(entries);
		summary = { ...summary, totals, net_calories: totals.calories - (summary.calories_burned ?? 0), entries, meals: regroupMeals(entries) };
	}

	// ── Notification modal ─────────────────────────────────────────────────────
	let showNotifModal = $state(false);

	function maybeShowNotifModal() {
		if (!pushStore.isSupported) return;
		if (pushStore.isSubscribed) return;
		if (pushStore.permission === 'denied') return;
		// Don't show if snoozed
		const snoozed = localStorage.getItem('uro_notif_snoozed');
		if (snoozed && Date.now() < Number(snoozed)) return;
		// Don't show if already asked and dismissed permanently
		if (localStorage.getItem('uro_notif_asked') === 'permanent') return;
		showNotifModal = true;
		localStorage.setItem('uro_notif_asked', 'shown');
	}
	let suppCount = $derived(supplements.length);
	let suppTaken = $derived(supplements.filter(s => s.taken).length);
	let cheatDay: CheatDayToday | null = $state(null);
	let togglingCheatDay = $state(false);
	let moodEntry: MoodEntry | null = $state(null);
	let moodEnabled = $derived(typeof localStorage !== 'undefined' ? localStorage.getItem('mood_enabled') === 'true' : false);

	// Edit state
	let editingEntry: DiaryEntry | null = $state(null);
	let editGrams = $state(100);
	let editMealType = $state('snack');
	let editSaving = $state(false);
	// Pareja en editar: si la pareja ya tiene este producto en esta comida hoy.
	let partnerEntry: { entry_id: number; grams: number } | null = $state(null);
	let sharePartner = $state(false);          // "comida compartida" on/off
	let partnerGrams = $state(100);            // gramos/ml de la pareja
	// Unidad (g o ml) del producto en edición — se conserva en los "platos".
	let editUnit = $derived(editingEntry?.product ? productUnit(editingEntry.product) : 'g');

	// Delete confirm state
	let deletingEntry: DiaryEntry | null = $state(null);
	let savingRecipe = $state(false);
	let recipeMealToSave: MealSection | null = $state(null);
	let recipeNameDraft = $state('');
	let recipeSaveError = $state('');
	let recipeSaveSuccess = $state('');

	// Clear meal state
	let clearingMeal: MealSection | null = $state(null);

	async function confirmClearMeal() {
		if (!clearingMeal) return;
		await api.del(`/diary/meal/${clearingMeal.meal_type}?day=${today}`);
		clearingMeal = null;
		await loadDay();
		refreshStreak();
	}

	// Refetches the current streak. Only meaningful while looking at today
	// (the flame is hidden otherwise via the `streak` derived above), so this
	// is a no-op elsewhere — keeps callers simple.
	async function refreshStreak() {
		if (!isToday) return;
		const st = await api.get<{ streak: number }>('/diary/streak').catch(() => null);
		if (st) currentStreak = st.streak;
	}

	// goals/frequent/frequentRecipes/users/streak don't depend on which day is
	// being browsed — fetched once on mount instead of on every day change.
	// Kept as a promise so loadDay() can wait on it the first time (goals
	// decides whether creatine/cheat-day extras are fetched below).
	let staticLoaded: Promise<void> | null = null;
	async function loadStatic() {
		const [g, f, fr, u, st] = await Promise.all([
			api.get<Goals>('/goals').catch(() => null),
			api.get<FrequentProduct[]>('/products/frequent?limit=5').catch(() => []),
			api.get<FrequentRecipe[]>('/recipes/frequent?limit=3').catch(() => []),
			api.get<User[]>('/users').catch(() => []),
			api.get<{ streak: number }>('/diary/streak').catch(() => ({ streak: 0 })),
		]);
		goals = g;
		frequent = f;
		frequentRecipes = fr;
		users = u;
		currentStreak = st.streak;
		if (g) cacheSet('goals', g);
	}

	async function loadDay() {
		fromCache = false;
		// Cache-first: paint instantly with cached data, then refresh in background
		const cachedSummary0 = cacheGet<DaySummary>(`diary_${today}`);
		const cachedGoals0 = cacheGet<Goals>('goals');
		if (cachedSummary0) {
			summary = cachedSummary0.data;
			if (cachedGoals0 && !goals) goals = cachedGoals0.data;
			loading = false; // we already have something to show
		} else {
			loading = true;
		}
		try {
			const [s, w] = await Promise.all([
				api.get<DaySummary>(`/diary/day?day=${today}`),
				api.get<WaterDay>(`/water/day?day=${today}`).catch(() => null),
			]);
			summary = s;
			water = w;

			// goals may still be in flight on the very first load (loadStatic
			// runs in parallel, not before) — wait for it just this once so the
			// creatine/cheat-day decision below isn't made on a stale `null`.
			if (!goals && staticLoaded) await staticLoaded.catch(() => {});

			// H5: these 4 only depend on goals (already resolved above) and
			// localStorage, so they run as one parallel batch instead of 4
			// sequential awaits.
			const [c, sup, cd, mood] = await Promise.all([
				goals?.track_creatine && isToday
					? api.get<CreatineToday>('/creatine/today').catch(() => null)
					: Promise.resolve(null),
				isToday
					? api.get<SupplementToday[]>('/supplements/today').catch(() => [])
					: Promise.resolve([]),
				goals?.cheat_days_enabled && isToday
					? api.get<CheatDayToday>('/cheat-days/today').catch(() => null)
					: Promise.resolve(null),
				typeof localStorage !== 'undefined' && localStorage.getItem('mood_enabled') === 'true'
					? api.get<MoodEntry | null>(`/mood/day?day=${today}`).catch(() => null)
					: Promise.resolve(null),
			]);
			creatine = c;
			supplements = sup;
			cheatDay = cd;
			moodEntry = mood;

			// Persist to cache for offline use
			cacheSet(`diary_${today}`, s);
			// Show notification modal once after user has their first entry
			if (s.totals.calories > 0 && !sessionStorage.getItem('uro_notif_modal_shown')) {
				sessionStorage.setItem('uro_notif_modal_shown', '1');
				setTimeout(maybeShowNotifModal, 1200);
			}
		} catch {
			// Network failed — try loading from cache
			const cachedSummary = cacheGet<DaySummary>(`diary_${today}`);
			const cachedGoals = cacheGet<Goals>('goals');
			if (cachedSummary) {
				summary = cachedSummary.data;
				fromCache = true;
			}
			if (cachedGoals && !goals) {
				goals = cachedGoals.data;
			}
		} finally {
			loading = false;
		}
	}

	// Sin sesión no lanzamos la batería de fetches: antes disparaban peticiones
	// con 401 mientras el goto('/login') aún no había navegado.
	$effect(() => {
		if (auth.isLoggedIn && !staticLoaded) staticLoaded = loadStatic();
	});
	$effect(() => { today; if (auth.isLoggedIn) loadDay(); });

	function pct(current: number, goal: number) {
		if (!goal) return 0;
		return Math.min(Math.round((current / goal) * 100), 100);
	}

	let partner = $derived(users.find(u => u.id !== auth.user?.id) ?? null);
	let partnerHue = $derived(partner ? (partner.identity_hue ?? nameHue(partner.name)) : 320);
	// Tu propio color: lo usa la tarjeta compartida, que va del tuyo al suyo.
	let myHue = $derived(auth.user ? (auth.user.identity_hue ?? nameHue(auth.user.name)) : 235);

	async function loadPartnerDay() {
		if (!partner || connectivity.isOffline) { partnerSummary = null; return; }
		const day = today;
		try {
			partnerSummary = await api.get<DaySummary>(`/diary/day?day=${day}&user_id=${partner.id}`);
		} catch {
			partnerSummary = null;
		}
	}
	// Refresca el día de la pareja al cambiar de día o cuando aparece la pareja.
	$effect(() => { const p = partner; today; if (auth.isLoggedIn && p) loadPartnerDay(); });

	function toggleShowPartner() {
		showPartner = !showPartner;
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem('uro_show_partner', showPartner ? '1' : '0');
		}
	}

	// Comidas a pintar: las tuyas y, si el chip está activo, las de la pareja
	// intercaladas por hora dentro de cada comida. Sus kcal NO suman a tus totales:
	// la cabecera usa solo tus totales y las suyas van en una línea aparte.
	let displayMeals = $derived((() => {
		if (!summary) return [];
		const myByType = new Map(summary.meals.map(m => [m.meal_type, m]));
		const showP = showPartner && !!partner && !!partnerSummary;
		const pByType = new Map((showP ? partnerSummary!.meals : []).map(m => [m.meal_type, m]));
		const out = [];
		for (const mt of MEAL_ORDER) {
			const mine = myByType.get(mt);
			const theirs = pByType.get(mt);
			const myEntries = mine?.entries ?? [];
			const pEntries = theirs?.entries ?? [];
			if (myEntries.length === 0 && pEntries.length === 0) continue;
			// Si los dos tenéis el mismo producto en la misma comida, se pinta UNA sola
			// tarjeta (la tuya) marcada como compartida con sus gramos, en vez de
			// duplicarla. El emparejado es por producto dentro de la comida, igual que
			// hace el modal de editar; uno a uno, por si hay repetidos.
			const pRemaining = [...pEntries];
			const items: { entry: DiaryEntry; mine: boolean; shared: DiaryEntry | null }[] =
				myEntries.map(e => {
					const i = pRemaining.findIndex(pe => pe.product_id === e.product_id);
					const shared = i >= 0 ? pRemaining.splice(i, 1)[0] : null;
					return { entry: e, mine: true, shared };
				});
			for (const pe of pRemaining) items.push({ entry: pe, mine: false, shared: null });
			items.sort((a, b) => new Date(a.entry.consumed_at).getTime() - new Date(b.entry.consumed_at).getTime());
			out.push({
				meal_type: mt,
				label: mealLabel(mt),
				hue: MEAL_HUES[mt] ?? 160,
				headerKcal: mine?.totals.calories ?? 0,
				headerProtein: mine?.totals.protein ?? 0,
				hasMyEntries: myEntries.length > 0,
				partnerKcal: pEntries.reduce((s, e) => s + e.calories, 0),
				mySection: mine,
				items,
			});
		}
		return out;
	})());
	let partnerHasEntries = $derived(showPartner && !!partner && !!partnerSummary && partnerSummary.entries.length > 0);

	async function copyToMe(entry: DiaryEntry) {
		try {
			await api.post('/diary', {
				product_id: entry.product_id,
				grams: entry.grams,
				meal_type: entry.meal_type,
				// Hereda su hora: es una comida compartida, así queda en el mismo
				// punto del día que la suya en vez de "ahora" (que descoloca la tarjeta).
				consumed_at: entry.consumed_at,
			});
			toast.success(t('diary.okAdd'));
			await loadDay();
		} catch {
			toast.error(t('diary.errAdd'));
		}
	}

	// Adjust macro targets for the day based on exercise calories burned
	let effectiveGoals = $derived((() => {
		if (!goals || !summary) return goals;
		const burned = summary.calories_burned ?? 0;
		const mode = goals.macro_adjust_mode ?? 'off';
		if (burned <= 0 || mode === 'off') return goals;

		if (mode === 'proportional') {
			const ratio = (goals.kcal + burned) / goals.kcal;
			return {
				...goals,
				kcal:    goals.kcal + burned,
				protein: Math.round(goals.protein * ratio * 10) / 10,
				carbs:   Math.round(goals.carbs   * ratio * 10) / 10,
				fat:     Math.round(goals.fat     * ratio * 10) / 10,
			};
		}

		if (mode === 'performance') {
			const extraCarbs = burned / 4;
			return {
				...goals,
				kcal:  goals.kcal + burned,
				carbs: Math.round((goals.carbs + extraCarbs) * 10) / 10,
				// protein and fat stay fixed
			};
		}

		return goals;
	})());

	// ¿La pareja tiene una copia de ESTA entrada (mismo producto/comida/día)?
	// Solo si la tiene ofrecemos "Solo para la pareja" en el menú de borrar.
	let deletingPartnerHas = $state(false);

	async function startDelete(entry: DiaryEntry) {
		if (!partner) {
			confirmDelete(entry.id, 'mine');
			return;
		}
		if (connectivity.isOffline) {
			// Sin conexión no podemos consultar: modal simple (los dos / solo yo).
			deletingPartnerHas = false;
			deletingEntry = entry;
			return;
		}
		try {
			const res = await api.get<{ entry_id: number | null }>(
				`/diary/partner-entry?user_id=${partner.id}&product_id=${entry.product_id}&day=${today}&meal_type=${entry.meal_type}`
			);
			if (res.entry_id != null) {
				deletingPartnerHas = true;
				deletingEntry = entry;          // hay copia → preguntar de quién
			} else {
				confirmDelete(entry.id, 'mine'); // solo es tuya → borrar directo
			}
		} catch {
			confirmDelete(entry.id, 'mine');
		}
	}

	async function confirmDelete(id: number, mode: 'both' | 'mine' | 'partner') {
		deletingEntry = null;
		let url = `/diary/${id}`;
		if (partner && mode === 'both') url += `?also_for_user_id=${partner.id}`;
		else if (partner && mode === 'partner') url += `?only_for_user_id=${partner.id}`;
		const removesMine = mode !== 'partner';  // "solo para la pareja" conserva la mía
		if (connectivity.isOffline) {
			syncQueue.enqueue({ method: 'DELETE', path: url, label: 'Borrar entrada' });
			if (removesMine) optimisticDeleteEntry(id);
			return;
		}
		// Online: update UI instantly, send request in background, revert on failure
		if (removesMine) optimisticDeleteEntry(id);
		try {
			await api.del(url);
			if (mode === 'partner') toast.success(`Quitado del diario de ${partner?.name}`);
		} catch {
			toast.error(t('diary.errDelete'));
			loadDay();
		}
	}

	function startEdit(entry: DiaryEntry) {
		editingEntry = entry;
		editGrams = entry.grams;
		editMealType = entry.meal_type;
		// Reset del bloque de pareja y consulta si ya lo tiene (solo online).
		partnerEntry = null;
		sharePartner = false;
		partnerGrams = entry.grams;
		if (partner && !connectivity.isOffline) refreshPartnerEntry();
	}

	// Interruptor "comida compartida": al activarlo, si la pareja aún no lo tiene,
	// hereda tus gramos/ml como punto de partida (luego se editan por separado).
	function toggleSharePartner() {
		sharePartner = !sharePartner;
		if (sharePartner && !partnerEntry) partnerGrams = editGrams;
	}

	async function refreshPartnerEntry() {
		if (!editingEntry || !partner) return;
		const pid = editingEntry.product_id;
		const mt = editMealType;
		try {
			const res = await api.get<{ entry_id: number | null; grams: number | null; count: number }>(
				`/diary/partner-entry?user_id=${partner.id}&product_id=${pid}&day=${today}&meal_type=${mt}`
			);
			// Descarta respuesta obsoleta (modal cerrado o cambiado de producto)
			if (!editingEntry || editingEntry.product_id !== pid) return;
			if (res.entry_id != null) {
				partnerEntry = { entry_id: res.entry_id, grams: res.grams ?? 0 };
				sharePartner = true;
				partnerGrams = res.grams ?? editGrams;
			}
		} catch {
			// Si falla la consulta, dejamos el bloque en "no lo tiene" (default seguro)
		}
	}

	async function saveEdit() {
		if (!editingEntry) return;
		editSaving = true;
		// Capturamos lo necesario antes de cerrar el modal.
		const editId = editingEntry.id;
		const consumedAt = editingEntry.consumed_at;
		const productId = editingEntry.product_id;
		const name = editingEntry.product?.name ?? 'entrada';
		const myGrams = editGrams;
		const mt = editMealType as MealType;
		const pGrams = partnerGrams;
		const existing = partnerEntry;
		// Añadir a la pareja solo si NO lo tenía y activaste el interruptor.
		const wantAdd = !!(partner && sharePartner && !existing);
		try {
			if (connectivity.isOffline) {
				syncQueue.enqueue({ method: 'PATCH', path: `/diary/${editId}`, body: { grams: myGrams, meal_type: mt }, label: `Editar ${name}` });
				optimisticEditEntry(editId, myGrams, mt);
				editingEntry = null;
				return;
			}
			// Online: update UI instantly, send request in background, revert on failure
			optimisticEditEntry(editId, myGrams, mt);
			editingEntry = null;
			try {
				await api.patch(`/diary/${editId}`, { grams: myGrams, meal_type: mt });
				// Reconciliar la copia de la pareja (afecta a SU diario, no al mío)
				if (partner) {
					if (existing) {
						// Ya la tiene: actualizar SOLO sus gramos y solo si los cambiaste.
						if (pGrams !== existing.grams) {
							await api.patch(`/diary/${existing.entry_id}`, { grams: pGrams });
						}
					} else if (wantAdd) {
						await api.post('/diary', { product_id: productId, grams: pGrams, consumed_at: consumedAt, meal_type: mt, only_for_user_id: partner.id });
					}
				}
			} catch {
				toast.error(t('diary.errSave'));
				loadDay();
			}
		} catch {
			toast.error(t('diary.errSave'));
		} finally {
			editSaving = false;
		}
	}

	async function addWater(ml: number) {
		lastWaterMl = ml;
		if (connectivity.isOffline) {
			syncQueue.enqueue({ method: 'POST', path: '/water/log', body: { ml, logged_date: today }, label: `Agua +${ml}ml` });
			if (water) water = { ...water, total_ml: water.total_ml + ml };
			else water = { total_ml: ml, goal_ml: goals?.water_ml ?? 2000 };
			return;
		}
		water = await api.post<WaterDay>('/water/log', { ml, logged_date: today });
	}

	async function removeWater() {
		if (connectivity.isOffline) {
			syncQueue.enqueue({ method: 'DELETE', path: `/water/log/last?day=${today}`, label: t('diary.waterUndo') });
			if (water) water = { ...water, total_ml: Math.max(0, water.total_ml - lastWaterMl) };
			return;
		}
		water = await api.del<WaterDay>(`/water/log/last?day=${today}`);
	}

	async function copyFromYesterday() {
		copyingYesterday = true;
		try {
			const res = await api.post<{ copied: number }>('/diary/copy-from-yesterday', {});
			if (res.copied > 0) {
				toast.success(`Copiado de ayer: ${res.copied} ${res.copied === 1 ? 'alimento' : 'alimentos'}`);
				await loadDay();
				refreshStreak();
			} else {
				// Antes esto no daba ningún feedback y parecía que el botón no hacía nada
				toast.info(t('diary.nothingYesterday'));
			}
		} catch {
			toast.error(t('diary.errCopyYesterday'));
		} finally {
			copyingYesterday = false;
		}
	}

	async function copyMeal(mealType: string) {
		if (copyingMealType) return;
		copyingMealType = mealType;
		try {
			const res = await api.post<{ copied: number }>(`/diary/copy-meal?source_date=${today}&meal_type=${mealType}`, {});
			if (res.copied > 0) {
				toast.success(`Copiado a hoy: ${res.copied} ${res.copied === 1 ? 'alimento' : 'alimentos'}`);
			} else {
				toast.info(t('diary.nothingYesterday'));
			}
		} catch {
			toast.error(t('diary.errCopyYesterday'));
		} finally {
			copyingMealType = null;
		}
	}

	async function toggleCreatine() {
		if (togglingCreatine) return;
		togglingCreatine = true;
		try {
			if (connectivity.isOffline) {
				if (creatine?.taken) {
					syncQueue.enqueue({ method: 'DELETE', path: '/creatine/today', label: 'Creatina — desmarcar' });
					creatine = { ...creatine!, taken: false };
				} else {
					syncQueue.enqueue({ method: 'POST', path: '/creatine/log', body: {}, label: 'Creatina ✓' });
					creatine = { taken: true, logged_date: today };
				}
				return;
			}
			if (creatine?.taken) {
				creatine = await api.del<CreatineToday>('/creatine/today');
			} else {
				creatine = await api.post<CreatineToday>('/creatine/log', {});
			}
		} catch {
			toast.error(t('diary.errCreatine'));
		} finally {
			togglingCreatine = false;
		}
	}

	async function toggleSupp(suppId: number, taken: boolean) {
		if (connectivity.isOffline) {
			if (taken) {
				syncQueue.enqueue({ method: 'DELETE', path: `/supplements/log/${suppId}`, label: 'Suplemento — desmarcar' });
			} else {
				syncQueue.enqueue({ method: 'POST', path: `/supplements/log/${suppId}`, body: {}, label: 'Suplemento ✓' });
			}
			supplements = supplements.map(s => s.supplement_id === suppId ? { ...s, taken: !taken } : s);
			return;
		}
		try {
			if (taken) {
				supplements = await api.del<SupplementToday[]>(`/supplements/log/${suppId}`);
			} else {
				supplements = await api.post<SupplementToday[]>(`/supplements/log/${suppId}`, {});
			}
		} catch { toast.error(t('diary.errSupplement')); }
	}

	async function addSupp() {
		if (!newSuppName.trim()) return;
		addingSuppName = true;
		try {
			await api.post<UserSupplement>('/supplements', { name: newSuppName.trim() });
			newSuppName = '';
			supplements = await api.get<SupplementToday[]>('/supplements/today');
		} catch { toast.error(t('diary.errAddSupplement')); } finally {
			addingSuppName = false;
		}
	}

	// Borrado en dos toques: el primer ✕ pide confirmación en la propia fila
	let confirmingSuppDelete: number | null = $state(null);
	let confirmSuppTimer: ReturnType<typeof setTimeout> | undefined;

	async function deleteSupp(suppId: number) {
		if (confirmingSuppDelete !== suppId) {
			confirmingSuppDelete = suppId;
			clearTimeout(confirmSuppTimer);
			confirmSuppTimer = setTimeout(() => (confirmingSuppDelete = null), 3000);
			return;
		}
		clearTimeout(confirmSuppTimer);
		confirmingSuppDelete = null;
		try {
			await api.del(`/supplements/${suppId}`);
			supplements = await api.get<SupplementToday[]>('/supplements/today');
		} catch { toast.error(t('diary.errDeleteSupplement')); }
	}

	async function toggleCheatDay() {
		if (togglingCheatDay) return;
		togglingCheatDay = true;
		try {
			if (cheatDay?.active) {
				cheatDay = await api.del<CheatDayToday>('/cheat-days/today');
			} else {
				cheatDay = await api.post<CheatDayToday>('/cheat-days/use', {});
				// Reload streak so the 🔥 updates immediately
				await refreshStreak();
			}
		} catch {
			toast.error(t('diary.errCheatDay'));
		} finally {
			togglingCheatDay = false;
		}
	}

	function startSaveMealAsRecipe(meal: MealSection) {
		recipeSaveError = '';
		recipeSaveSuccess = '';
		recipeMealToSave = meal;
		recipeNameDraft = `${meal.label} - ${today}`;
	}

	function closeRecipeModal() {
		recipeMealToSave = null;
		recipeNameDraft = '';
		recipeSaveError = '';
	}

	async function confirmSaveMealAsRecipe() {
		if (!recipeMealToSave || !recipeMealToSave.entries || recipeMealToSave.entries.length === 0) {
			recipeSaveError = 'No hay entradas en esta comida para guardar como receta.';
			return;
		}

		const name = recipeNameDraft.trim();
		if (!name) {
			recipeSaveError = 'Pon un nombre para la receta.';
			return;
		}

		const ingredients = recipeMealToSave.entries
			.filter((e) => e.product_id)
			.map((e) => ({ product_id: e.product_id, grams: e.grams }));

		if (ingredients.length === 0) {
			recipeSaveError = 'No hay ingredientes validos para guardar.';
			return;
		}

		savingRecipe = true;
		recipeSaveError = '';
		try {
			await api.post('/recipes', { name, ingredients, share_scope: 'friends' });
			recipeSaveSuccess = t('diary.recipeSaved');
			closeRecipeModal();
			// Invalidate the frequent-recipes part of loadStatic (skipped on plain
			// day navigation, but a new recipe should still show up promptly).
			frequentRecipes = await api.get<FrequentRecipe[]>('/recipes/frequent?limit=3').catch(() => frequentRecipes);
		} catch (err: any) {
			recipeSaveError = 'Error guardando la receta: ' + (err?.message || err);
		} finally {
			savingRecipe = false;
		}
	}

	function fmtTime(iso: string) {
		return fmtTimeI18n(new Date(iso), { hour: '2-digit', minute: '2-digit' });
	}
</script>

{#if !auth.isLoggedIn}
	<!-- redirect handled above -->
{:else}
	<DayNav bind:date={today} {streak} />
	<TrialBanner />


	{#if recipeSaveSuccess}
		<div class="card" style="margin-bottom:0.75rem; border-color:var(--primary); color:var(--primary); font-size:0.85rem; padding:0.65rem 0.8rem;">
			{recipeSaveSuccess}
		</div>
	{/if}


{#if loading}
		<p style="text-align:center; color:var(--text-muted); padding:2rem 0;">{t('diary.loading')}</p>
	{:else if summary}

		{#if fromCache}
			<div class="cache-notice">
				<span>📦</span>
				<span>{t('diary.offlineSaved')}</span>
			</div>
		{/if}
		{#if syncQueue.count > 0}
			<div class="cache-notice" style="border-color: oklch(75% 0.18 55 / 0.25); background: oklch(75% 0.18 55 / 0.06);">
				<span>⏳</span>
				<span style="color: oklch(82% 0.15 55);">
					{syncQueue.count} {tc('diary.pending', syncQueue.count)} de sincronizar
					{#if syncQueue.isSyncing}· sincronizando…{/if}
				</span>
			</div>
		{/if}

		<div class="diary-body">

		<!-- ── LEFT: stats panel ── -->
		<div class="diary-left">

			<!-- Hero calories card -->
			<div class="card" style="margin-bottom:0.75rem; margin-top:0.75rem;">
				{#if effectiveGoals}
					<CalorieRing
						consumed={summary.totals.calories}
						goal={effectiveGoals.kcal}
						burned={summary.calories_burned}
						net={summary.net_calories}
						size={175}
					/>
					<div style="height:1rem;"></div>
					<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.75rem;">
						<MacroBar label={t('diary.macroProtein')}  value={summary.totals.protein} goal={effectiveGoals.protein} color="var(--prot)" />
						<MacroBar label={t('diary.macroCarbs')}  value={summary.totals.carbs}   goal={effectiveGoals.carbs}   color="var(--carb)" />
						<MacroBar label={t('diary.macroFat')} value={summary.totals.fat}     goal={effectiveGoals.fat}     color="var(--fat)" />
					</div>
				{:else}
					<div style="display:flex; justify-content:space-between; align-items:center;">
						<div>
							<div style="font-size:1.8rem; font-weight:800; color:var(--cal);">{Math.round(summary.totals.calories)}</div>
							<div style="font-size:0.75rem; color:var(--text-muted);">kcal · P{Math.round(summary.totals.protein)}g · C{Math.round(summary.totals.carbs)}g · G{Math.round(summary.totals.fat)}g</div>
						</div>
						<a href="/goals" class="btn-secondary" style="font-size:0.8rem; padding:0.4rem 0.8rem; border-radius:8px; border:1px solid var(--border);">
							Fijar objetivos
						</a>
					</div>
				{/if}
			</div>

			<!-- Water + Supplements -->
			<div style="display:grid; grid-template-columns:{isToday && suppCount > 0 ? '1fr 1fr' : '1fr'}; gap:0.6rem; margin-bottom:0.75rem;">
				<div class="card" style="padding:0.85rem;">
					<div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.5rem;">
						<span style="font-size:0.95rem;">💧</span>
						<span style="font-size:0.82rem; color:var(--water); font-weight:700;">{t('diary.water')}</span>
						{#if water}
							<span style="font-size:0.72rem; color:var(--text-muted); margin-left:auto;">
								{Math.round(water.total_ml)} / {water.goal_ml} ml
							</span>
						{/if}
					</div>
					{#if water}
						<div class="progress-bar" style="height:6px; margin-bottom:0.65rem;">
							<div class="fill" style="width:{pct(water.total_ml, water.goal_ml)}%; background:var(--water);"></div>
						</div>
					{/if}
					<div style="display:flex; gap:0.35rem;">
						<button onclick={() => addWater(250)} style="flex:1; font-size:0.72rem; padding:0.35rem 0.2rem;">+250</button>
						<button onclick={() => addWater(500)} style="flex:1; font-size:0.72rem; padding:0.35rem 0.2rem;">+500</button>
						<button class="btn-secondary" onclick={removeWater}
							style="flex:1; font-size:0.72rem; padding:0.35rem 0.2rem;"
							disabled={!water || water.total_ml <= 0}>↩</button>
					</div>
				</div>
				{#if isToday && suppEnabled}
					{#if suppCount === 1}
						<!-- Single supplement: tap to toggle directly -->
						<div class="card" role="button" tabindex="0"
							onclick={() => toggleSupp(supplements[0].supplement_id, supplements[0].taken)}
							onkeydown={(e) => e.key === 'Enter' && toggleSupp(supplements[0].supplement_id, supplements[0].taken)}
							style="padding:0.85rem; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:0.55rem; text-align:center; cursor:pointer;
							{supplements[0].taken ? 'background:linear-gradient(135deg, var(--primary) -20%, var(--surface) 70%); border-color: var(--primary);' : ''}">
							<div style="
								width:42px; height:42px; border-radius:50%;
								background:{supplements[0].taken ? 'linear-gradient(135deg, var(--primary), var(--primary-dim))' : 'transparent'};
								border:{supplements[0].taken ? 'none' : '1.5px dashed rgba(255,255,255,0.25)'};
								display:flex; align-items:center; justify-content:center;
								font-size:1.05rem; font-weight:800; color:var(--primary-ink);
								transition: background 0.25s;
							">{supplements[0].taken ? '✓' : ''}</div>
							<div style="font-weight:700; font-size:0.82rem; color:#fff;">{supplements[0].name}</div>
							<!-- Dos acciones = dos controles separados (antes era un único target confuso) -->
							<div style="display:flex; align-items:center; gap:0.4rem; font-size:0.72rem; font-weight:600; color:var(--text-muted);">
								<span role="button" tabindex="0"
									onclick={(e) => { e.stopPropagation(); toggleSupp(supplements[0].supplement_id, supplements[0].taken); }}
									onkeydown={(e) => e.key === 'Enter' && (e.stopPropagation(), toggleSupp(supplements[0].supplement_id, supplements[0].taken))}
									style="cursor:pointer; padding:0.2rem 0.1rem;">
									{supplements[0].taken ? t('diary.suppUndo') : t('diary.suppMark')}
								</span>
								<span aria-hidden="true">·</span>
								<span role="button" tabindex="0"
									onclick={(e) => { e.stopPropagation(); showSupplModal = true; }}
									onkeydown={(e) => e.key === 'Enter' && (e.stopPropagation(), showSupplModal = true)}
									style="cursor:pointer; padding:0.2rem 0.1rem;">
									{t('diary.suppManage')}
								</span>
							</div>
						</div>
					{:else if suppCount > 1}
						<!-- Multiple supplements: tap opens modal with ring -->
						<button class="card" onclick={() => showSupplModal = true} style="padding:0.85rem; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:0.5rem; text-align:center; cursor:pointer; border:none; width:100%;">
							<div style="position:relative; width:42px; height:42px;">
								<svg viewBox="0 0 42 42" style="width:42px; height:42px; transform:rotate(-90deg);">
									<circle cx="21" cy="21" r="17" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="4"/>
									<circle cx="21" cy="21" r="17" fill="none"
										stroke="{suppTaken === suppCount ? 'var(--primary)' : 'oklch(75% 0.18 160)'}"
										stroke-width="4"
										stroke-dasharray="{Math.round(2 * 3.14159 * 17)}"
										stroke-dashoffset="{Math.round(2 * 3.14159 * 17 * (1 - suppTaken / suppCount))}"
										stroke-linecap="round"/>
								</svg>
								<div style="position:absolute; inset:0; display:flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:800; color:{suppTaken === suppCount ? 'var(--primary)' : '#fff'};">
									{suppTaken}/{suppCount}
								</div>
							</div>
							<div style="font-weight:700; font-size:0.82rem; color:#fff;">{t('diary.supplements')}</div>
							<div style="font-size:0.7rem; color:var(--text-muted);">{suppTaken === suppCount ? t('diary.suppAllTaken') : t('diary.suppTapToMark')}</div>
						</button>
					{:else}
						<!-- No supplements yet -->
						<button class="card" onclick={() => showSupplModal = true} style="padding:0.85rem; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:0.5rem; text-align:center; cursor:pointer; border:none; width:100%;">
							<div style="width:42px; height:42px; border-radius:50%; border:1.5px dashed rgba(255,255,255,0.2); display:flex; align-items:center; justify-content:center; font-size:1.2rem;">＋</div>
							<div style="font-weight:700; font-size:0.82rem; color:#fff;">{t('diary.supplements')}</div>
							<div style="font-size:0.7rem; color:var(--text-muted);">{t('diary.addSupplement')}</div>
						</button>
					{/if}
				{/if}
			</div>

			<!-- Mood chip -->
			{#if moodEnabled}
				<a href="/mood?day={today}" class="mood-chip" style="text-decoration:none; display:block; margin-bottom:0.75rem;">
					<div class="card" style="padding:0.75rem 1rem; display:flex; align-items:center; gap:0.75rem; cursor:pointer;">
						<div style="width:36px; height:36px; border-radius:12px; flex-shrink:0; background:rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center; font-size:1.2rem;">
							{moodEntry?.worst ? MOOD_WORST_EMOJI[moodEntry.worst] : '🫥'}
						</div>
						<div style="flex:1; min-width:0;">
							<div style="font-weight:700; font-size:0.85rem; color:#fff;">{t('diary.moodTitle')}</div>
							<div style="font-size:0.75rem; color:var(--text-muted);">
								{#if moodEntry?.worst}
									{moodEntry.energy ? '⚡' : ''}{moodEntry.digestion ? t('diary.moodDigestion') : ''}{moodEntry.mood ? t('diary.moodMood') : ''}{t('diary.moodEdit')}
								{:else}
									{t('diary.moodAsk')}
								{/if}
							</div>
						</div>
						<div style="font-size:0.75rem; color:var(--text-muted);">›</div>
					</div>
				</a>
			{/if}

			<!-- Cheat day -->
			{#if isToday && goals?.cheat_days_enabled && cheatDay !== null}
				<div class="card" style="margin-bottom:0.75rem; {cheatDay.active ? 'border-color:oklch(70% 0.18 45 / 0.6); background:linear-gradient(135deg, oklch(70% 0.18 45 / 0.08), transparent 60%), var(--surface);' : ''}">
					<div style="display:flex; align-items:center; justify-content:space-between; gap:0.75rem;">
						<div style="display:flex; align-items:center; gap:0.65rem; min-width:0;">
							<div style="
								width:36px; height:36px; border-radius:12px; flex-shrink:0;
								background:linear-gradient(135deg, oklch(70% 0.2 45 / 0.25), oklch(70% 0.2 35 / 0.1));
								border:1px solid oklch(70% 0.18 45 / 0.3);
								display:flex; align-items:center; justify-content:center;
								font-size:1.1rem;
							">🍕</div>
							<div style="min-width:0;">
								<div style="font-weight:700; font-size:0.88rem;">{t('diary.cheatDay')}</div>
								<div style="font-size:0.72rem; color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
									{cheatDay.active ? t('diary.cheatDayOn') : t('diary.cheatDayOff')}
								</div>
							</div>
						</div>
						<button
							onclick={toggleCheatDay}
							disabled={togglingCheatDay}
							class:btn-secondary={cheatDay.active}
							style="flex-shrink:0; padding:0.45rem 1rem; font-size:0.8rem; font-weight:700; opacity:{togglingCheatDay ? '0.6' : '1'}; {!cheatDay.active ? 'background:oklch(70% 0.18 45 / 0.2); color:oklch(80% 0.18 45); border:1px solid oklch(70% 0.18 45 / 0.4); box-shadow:none;' : ''}"
						>{cheatDay.active ? t('diary.cheatDayCancel') : t('diary.cheatDayActivate')}</button>
					</div>
				</div>
			{/if}

			<!-- Frequent products (desktop: show in left panel when there are entries) -->
			{#if frequent.length > 0 && summary.entries.length > 0}
				<div class="diary-frequent-desktop">
					<div style="font-size:0.7rem; letter-spacing:0.08em; text-transform:uppercase; color:var(--text-muted); font-weight:700; margin-bottom:0.5rem;">{t('diary.frequent')}</div>
					<div style="display:flex; flex-direction:column; gap:0.35rem;">
						{#each frequent as freq (freq.product.id)}
							<a href="/add?date={today}&product={freq.product.id}" style="text-decoration:none;">
								<div class="card" style="cursor:pointer; padding:0.6rem 0.75rem;">
									<div style="display:flex; justify-content:space-between; align-items:center;">
										<div class="diary-frequent-name" style="font-size:0.82rem; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{freq.product.name}</div>
										<div class="diary-frequent-kcal" style="font-size:0.72rem; color:var(--cal); font-weight:600; flex-shrink:0; margin-left:0.5rem;">{freq.product.calories_per_100g} kcal</div>
									</div>
								</div>
							</a>
						{/each}
					</div>
				</div>
			{/if}

		</div><!-- /diary-left -->

		<!-- ── RIGHT: diary entries ── -->
		<div class="diary-right" style="margin-top:0.75rem;">

			{#if (partner && !connectivity.isOffline) || (isToday && summary.entries.length > 0)}
				<div class="diary-toolbar">
					{#if partner && !connectivity.isOffline}
						<button
							type="button"
							class="partner-chip"
							class:on={showPartner}
							style="--phue:{partnerHue};"
							onclick={toggleShowPartner}
							aria-pressed={showPartner}
						>
							<span class="pc-av"><Avatar name={partner.name} avatarId={partner.avatar_id} identityHue={partnerHue} size={28} ring="2px solid {identityColor(partner.name, partner.identity_hue)}" /></span>
							<span class="pc-body">
								<span class="pc-name">{partner.name}</span>
								{#if partnerSummary && goals}
									<span class="pc-mac"><span class="pc-k">{Math.round(partnerSummary.totals.calories)} / {Math.round(goals.kcal)} kc</span> · <span class="pc-p">{Math.round(partnerSummary.totals.protein)} / {Math.round(goals.protein)} P</span>{#if partnerSummary.supplements_done}<span class="pc-supp" title={t('diary.partnerSupplementsDone')}>💊</span>{/if}</span>
								{:else}
									<span class="pc-mac pc-hint">{t('diary.seeTheirDay')}</span>
								{/if}
							</span>
							<span class="pc-state">{showPartner ? t('diary.hide') : t('diary.show')}</span>
						</button>
					{/if}
					{#if isToday && summary.entries.length > 0}
						<button
							class="btn-secondary"
							onclick={copyFromYesterday}
							disabled={copyingYesterday}
							style="font-size:0.75rem; padding:0.3rem 0.7rem; margin-left:auto;">
							{copyingYesterday ? '...' : t('diary.sameAsYesterday')}
						</button>
					{/if}
				</div>
			{/if}

			{#if summary.entries.length === 0 && !partnerHasEntries}
				<EmptyState
					icon="🥣"
					title={t('diary.emptyTitle')}
					description={isToday ? t('diary.emptyToday') : t('diary.emptyOther')}
					actionLabel={isToday ? t('diary.addFood') : undefined}
					actionHref={isToday ? `/add?date=${today}` : undefined}
				/>
				{#if isToday}
					<button
						class="btn-secondary"
						onclick={copyFromYesterday}
						disabled={copyingYesterday}
						style="width:100%; margin-top:0.75rem; margin-bottom:1rem;">
						{copyingYesterday ? t('diary.copying') : t('diary.sameAsYesterday')}
					</button>
				{/if}
				{#if frequentRecipes.length > 0 || frequent.length > 0}
					<div style="margin-top:0.5rem;">
						<div style="font-weight:700; font-size:0.9rem; margin-bottom:0.5rem; color:var(--text-muted);">{t('diary.frequentlyUsed')}</div>

						{#if frequentRecipes.length > 0}
							<div style="font-size:0.72rem; font-weight:700; letter-spacing:0.05em; text-transform:uppercase; color:var(--text-muted); opacity:0.6; margin-bottom:0.35rem; padding-left:0.25rem;">{t('diary.recipes')}</div>
							<div style="display:flex; flex-direction:column; gap:0.4rem; margin-bottom:0.75rem;">
								{#each frequentRecipes as freq (freq.recipe.id)}
									{@const totalKcal = freq.recipe.ingredients.reduce((s, i) => s + (i.product.calories_per_100g * i.grams / 100), 0)}
									<a href="/add?date={today}&recipe={freq.recipe.id}" style="text-decoration:none;">
										<div class="card" style="cursor:pointer;">
											<div style="display:flex; justify-content:space-between; align-items:center;">
												<div style="display:flex; align-items:center; gap:0.6rem; flex:1; min-width:0;">
													<span style="font-size:1.2rem; flex-shrink:0;">🍳</span>
													<div style="min-width:0;">
														<div style="font-weight:600; font-size:0.9rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{freq.recipe.name}</div>
														<div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.1rem;">{t('diary.usedFem', { count: freq.count, times: tc('diary.time', freq.count) })}</div>
													</div>
												</div>
												<div style="text-align:right; margin-left:0.5rem; white-space:nowrap; flex-shrink:0;">
													<div style="font-size:0.85rem; color:var(--cal); font-weight:600;">{Math.round(totalKcal)} kcal</div>
												</div>
											</div>
										</div>
									</a>
								{/each}
							</div>
						{/if}

						{#if frequent.length > 0}
							{#if frequentRecipes.length > 0}
								<div style="font-size:0.72rem; font-weight:700; letter-spacing:0.05em; text-transform:uppercase; color:var(--text-muted); opacity:0.6; margin-bottom:0.35rem; padding-left:0.25rem;">{t('diary.foods')}</div>
							{/if}
							<div style="display:flex; flex-direction:column; gap:0.4rem;">
								{#each frequent as freq (freq.product.id)}
									<a href="/add?date={today}&product={freq.product.id}" style="text-decoration:none;">
										<div class="card" style="cursor:pointer;">
											<div style="display:flex; justify-content:space-between; align-items:start;">
												<div style="flex:1;">
													<div style="font-weight:600; font-size:0.9rem;">{freq.product.name}</div>
													{#if freq.product.brand}<div style="font-size:0.8rem; color:var(--text-muted);">{freq.product.brand}</div>{/if}
													<div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.25rem;">{t('diary.usedMasc', { count: freq.count, times: tc('diary.time', freq.count) })}</div>
												</div>
												<div style="text-align:right; margin-left:0.5rem; white-space:nowrap;">
													<div style="font-size:0.85rem; color:var(--cal); font-weight:600;">{freq.product.calories_per_100g} kcal/100g</div>
												</div>
											</div>
										</div>
									</a>
								{/each}
							</div>
						{/if}
					</div>
				{/if}
			{:else}
				{#if displayMeals.length > 0}
					{#each displayMeals as meal (meal.meal_type)}
						<div style="margin-bottom:1rem;">
							<MealHeader
								label={meal.label}
								kcal={meal.headerKcal}
								protein={meal.headerProtein}
								hasEntries={meal.hasMyEntries}
								hue={meal.hue}
							>
								{#snippet iconRepeat()}
									<svg viewBox="0 0 20 20" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7a5 5 0 0 1 5-4h5M14 3v4h-4"/><path d="M16 13a5 5 0 0 1-5 4H6M6 17v-4h4"/></svg>
								{/snippet}
								{#snippet iconBook()}
									<svg viewBox="0 0 20 20" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 5.5c-1.2-1-3-1.5-5.5-1.5v11c2.5 0 4.3.5 5.5 1.5c1.2-1 3-1.5 5.5-1.5V4c-2.5 0-4.3.5-5.5 1.5z"/><path d="M10 5.5v11"/></svg>
								{/snippet}
								{#snippet iconTrash()}
									<svg viewBox="0 0 20 20" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.5 6h11M8 6V4.5h4V6M6 6l.6 9.5a1 1 0 0 0 1 .9h4.8a1 1 0 0 0 1-.9L14 6"/><path d="M8.5 9v4M11.5 9v4"/></svg>
								{/snippet}
								{#snippet actions()}
									{#if !isToday}
										<button
											class="btn-ghost"
											onclick={(e) => { e.stopPropagation(); copyMeal(meal.meal_type); }}
											disabled={!meal.hasMyEntries || copyingMealType === meal.meal_type}
											aria-label={t('diary.copyMeal')}
											title={t('diary.copyMeal')}
											style="display:inline-flex; align-items:center; padding:0.3rem 0.4rem; line-height:1;"
										>
											{#if copyingMealType === meal.meal_type}…{:else}{@render iconRepeat()}{/if}
										</button>
									{/if}
									<button
										class="btn-ghost"
										onclick={(e) => { e.stopPropagation(); if (meal.mySection) startSaveMealAsRecipe(meal.mySection); }}
										disabled={!meal.hasMyEntries}
										aria-label={t('diary.mealRecipe')}
										title={t('diary.mealRecipe')}
										style="display:inline-flex; align-items:center; padding:0.3rem 0.4rem; line-height:1;"
									>
										{@render iconBook()}
									</button>
									<button
										class="btn-ghost"
										onclick={(e) => { e.stopPropagation(); if (meal.mySection) clearingMeal = meal.mySection; }}
										disabled={!meal.hasMyEntries}
										aria-label={t('diary.mealClear')}
										title={t('diary.mealClear')}
										style="display:inline-flex; align-items:center; padding:0.3rem 0.4rem; line-height:1; color:oklch(70% 0.18 25);"
									>
										{@render iconTrash()}
									</button>
								{/snippet}
							</MealHeader>
							{#if showPartner && meal.partnerKcal > 0}
								<div class="partner-meal-line" style="--phue:{partnerHue};">{partner?.name}: {Math.round(meal.partnerKcal)} kcal</div>
							{/if}
							{#each meal.items as it (it.mine ? 'm' + it.entry.id : 'p' + it.entry.id)}
								{#if it.mine}
									{@render entryCard(it.entry, it.shared)}
								{:else}
									{@render partnerEntryCard(it.entry)}
								{/if}
							{/each}
						</div>
					{/each}
				{:else}
					{#each summary.entries as entry (entry.id)}
						{@render entryCard(entry, null)}
					{/each}
				{/if}
			{/if}

		</div><!-- /diary-right -->
		</div><!-- /diary-body -->

	{/if}
{/if}

<!-- Save recipe modal -->
{#if recipeMealToSave}
	<Modal
		onClose={closeRecipeModal}
		title={t('diary.saveRecipe')}
		subtitle={t('diary.saveRecipeSub', { meal: recipeMealToSave.label, count: recipeMealToSave.entries.length })}
	>
		<div class="form-group">
			<label for="recipe-name">{t('diary.recipeName')}</label>
			<input
				id="recipe-name"
				type="text"
				bind:value={recipeNameDraft}
				autocapitalize="sentences"
				autocomplete="off"
				onkeydown={(e) => { if (e.key === 'Enter') confirmSaveMealAsRecipe(); }}
			/>
		</div>

		{#if recipeSaveError}
			<div style="color:var(--danger); font-size:0.8rem; margin-top:0.2rem;">{recipeSaveError}</div>
		{/if}

		<div style="display:flex; gap:0.5rem; margin-top:0.9rem;">
			<button class="btn-secondary" onclick={closeRecipeModal} style="flex:1;" disabled={savingRecipe}>{t('common.cancel')}</button>
			<button onclick={confirmSaveMealAsRecipe} style="flex:2;" disabled={savingRecipe}>
				{savingRecipe ? t('diary.saving') : t('diary.saveRecipe')}
			</button>
		</div>
	</Modal>
{/if}

<!-- Edit modal -->
{#if editingEntry}
	<Modal
		onClose={() => editingEntry = null}
		title={editingEntry.product?.name ?? t('diary.edit')}
		subtitle={t('diary.editEntry')}
	>
		{#if !(partner && !connectivity.isOffline && (partnerEntry || sharePartner))}
			<div class="form-group">
				<label for="edit-grams">{editUnit === 'ml' ? 'Mililitros' : 'Gramos'}</label>
				<input id="edit-grams" type="number" bind:value={editGrams} min="1" step="1" style="width:100%;" />
			</div>
		{/if}

		<div class="form-group">
			<label>{t('diary.mealField')}</label>
			<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:0.4rem;">
				{#each MEAL_ORDER as mt}
					<button
						onclick={() => editMealType = mt}
						class:btn-secondary={editMealType !== mt}
						style="font-size:0.75rem; padding:0.4rem 0.2rem;">
						{mealLabel(mt)}
					</button>
				{/each}
			</div>
		</div>

		{#if partner && !connectivity.isOffline}
			<div class="form-group">
				<label>{t('diary.partnerField')}</label>

				{#snippet plates()}
					<div class="edit-plates">
						<div class="edit-plate you">
							<div class="edit-plate-av"><Avatar name={auth.user?.name ?? t('diary.you')} avatarId={auth.user?.avatar_id} size={34} /></div>
							<div class="edit-plate-who">{t('diary.you')}</div>
							<div class="edit-plate-g">
								<input type="number" bind:value={editGrams} min="1" step="1" aria-label={t('diary.yoursAria', { unit: editUnit })} />
								<span>{editUnit}</span>
							</div>
						</div>
						<div class="edit-plate her">
							<div class="edit-plate-av"><Avatar name={partner.name} avatarId={partner.avatar_id} size={34} /></div>
							<div class="edit-plate-who">{partner.name}</div>
							<div class="edit-plate-g">
								<input type="number" bind:value={partnerGrams} min="1" step="1" aria-label={t('diary.partnerAria', { unit: editUnit, name: partner.name })} />
								<span>{editUnit}</span>
							</div>
						</div>
					</div>
				{/snippet}

				{#if partnerEntry}
					<!-- Ya la tiene: sin interruptor. Ajusta cantidades; para quitarla, se usa Borrar. -->
					<div class="edit-share-row on">
						<div style="flex:1; min-width:0;">
							<div style="font-weight:700; font-size:0.85rem;">
								Comida compartida
								<span class="edit-has-badge">{t('diary.alreadyHasIt')}</span>
							</div>
							<div class="edit-share-sub" style="margin-top:0.1rem;">{t('diary.editingPartnerToo', { name: partner.name })}</div>
						</div>
					</div>
					{@render plates()}
					<div class="edit-share-sub" style="margin-top:0.5rem;">{t('diary.removeHint')}</div>
				{:else}
					<div class="edit-share-row" class:on={sharePartner}>
						<div style="flex:1; min-width:0;">
							<div style="font-weight:700; font-size:0.85rem;">{t('diary.sharedMeal')}</div>
							<div class="edit-share-sub" style="margin-top:0.1rem;">
								{sharePartner ? `Cada uno con sus ${editUnit}` : `Añadirla también para ${partner.name}`}
							</div>
						</div>
						<button
							type="button"
							class="edit-switch"
							class:on={sharePartner}
							onclick={toggleSharePartner}
							role="switch"
							aria-checked={sharePartner}
							aria-label={t('diary.sharedMealAria', { name: partner.name })}></button>
					</div>
					{#if sharePartner}
						{@render plates()}
					{/if}
				{/if}
			</div>
		{/if}

		<div style="display:flex; gap:0.5rem; margin-top:0.75rem;">
			<button class="btn-secondary" onclick={() => editingEntry = null} style="flex:1;">{t('common.cancel')}</button>
			<button onclick={saveEdit} disabled={editSaving} style="flex:2;">
				{editSaving ? 'Guardando...' : 'Guardar'}
			</button>
		</div>
	</Modal>
{/if}

<!-- Delete confirm (when partner exists) -->
{#if deletingEntry}
	<Modal
		onClose={() => deletingEntry = null}
		title={t('diary.deleteEntry')}
		subtitle="{deletingEntry.product?.name} — {deletingEntry.grams}{deletingEntry.product ? productUnit(deletingEntry.product) : 'g'}"
	>
		<div class="del-q">
			{deletingPartnerHas
				? t('diary.deleteAskPartner', { name: partner?.name ?? '' })
				: t('diary.deleteAsk')}
		</div>
		<div class="del-cards">
			<button class="del-card danger" onclick={() => confirmDelete(deletingEntry!.id, 'both')}>
				<div class="del-avs"><Avatar name={auth.user?.name ?? t('diary.you')} avatarId={auth.user?.avatar_id} size={34} /><Avatar name={partner?.name ?? ''} avatarId={partner?.avatar_id} size={34} /></div>
				<div class="del-txt"><div class="del-t">{t('diary.deleteBoth')}</div><div class="del-s">{t('diary.deleteBothSub')}</div></div>
				<div class="del-chev">›</div>
			</button>
			<button class="del-card" onclick={() => confirmDelete(deletingEntry!.id, 'mine')}>
				<div class="del-avs"><Avatar name={auth.user?.name ?? t('diary.you')} avatarId={auth.user?.avatar_id} size={34} /></div>
				<div class="del-txt"><div class="del-t">{t('diary.deleteMine')}</div><div class="del-s">{deletingPartnerHas ? `${partner?.name} lo conserva` : 'Se borra de tu diario'}</div></div>
				<div class="del-chev">›</div>
			</button>
			{#if deletingPartnerHas}
				<button class="del-card" onclick={() => confirmDelete(deletingEntry!.id, 'partner')}>
					<div class="del-avs"><Avatar name={partner?.name ?? ''} avatarId={partner?.avatar_id} size={34} /></div>
					<div class="del-txt"><div class="del-t">Solo para {partner?.name}</div><div class="del-s">{t('diary.deleteMineSub')}</div></div>
					<div class="del-chev">›</div>
				</button>
			{/if}
		</div>
		<button class="btn-secondary" style="width:100%; margin-top:0.6rem;" onclick={() => deletingEntry = null}>{t('common.cancel')}</button>
		</Modal>
{/if}

<!-- Clear meal modal -->
{#if clearingMeal}
	<Modal onClose={() => clearingMeal = null} title={t('diary.clearMeal', { meal: clearingMeal.label })} subtitle={showPartner && partner ? t('diary.clearMealSubPartner', { name: partner.name }) : t('diary.clearMealSub')}>
		<div style="display:flex; gap:0.75rem; margin-top:0.5rem;">
			<button class="btn-danger" onclick={confirmClearMeal}>{t('diary.clear')}</button>
			<button class="btn-secondary" onclick={() => clearingMeal = null}>{t('common.cancel')}</button>
		</div>
	</Modal>
{/if}

<!-- Supplements modal -->
{#if showSupplModal}
	<Modal onClose={() => showSupplModal = false} title={t('diary.suppModalTitle')} subtitle={t('diary.suppModalSub')}>
		<div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:1rem;">
			{#each supplements as s (s.supplement_id)}
				<div style="display:flex; align-items:center; gap:0.75rem; padding:0.625rem 0.75rem; background:rgba(255,255,255,0.04); border-radius:12px; border:1px solid rgba(255,255,255,0.07);">
					<button
						onclick={() => toggleSupp(s.supplement_id, s.taken)}
						aria-label="{s.taken ? t('diary.suppUncheck') : t('diary.suppCheck')} {s.name}"
						aria-pressed={s.taken}
						style="
							width:44px; height:44px; border-radius:50%; flex-shrink:0; cursor:pointer;
							background:{s.taken ? 'linear-gradient(135deg, var(--primary), var(--primary-dim))' : 'transparent'};
							border:{s.taken ? 'none' : '1.5px dashed rgba(255,255,255,0.3)'};
							color:var(--primary-ink); font-size:0.95rem; font-weight:800;
							display:flex; align-items:center; justify-content:center;
							transition: background 0.2s; box-shadow:none; padding:0;
						">{s.taken ? '✓' : ''}</button>
					<span style="flex:1; font-size:0.875rem; font-weight:600; color:{s.taken ? 'rgba(255,255,255,0.5)' : '#fff'}; text-decoration:{s.taken ? 'line-through' : 'none'};">{s.name}</span>
					{#if confirmingSuppDelete === s.supplement_id}
						<button
							onclick={() => deleteSupp(s.supplement_id)}
							style="background:oklch(65% 0.22 25 / 0.12); border:1px solid oklch(65% 0.22 25 / 0.4); border-radius:8px; color:oklch(75% 0.2 25); font-size:0.6875rem; font-weight:700; cursor:pointer; padding:0.375rem 0.5rem; box-shadow:none; line-height:1;"
						>{t('diary.suppDeleteAsk')}</button>
					{:else}
						<button
							onclick={() => deleteSupp(s.supplement_id)}
							style="background:none; border:none; color:rgba(255,255,255,0.25); font-size:1rem; cursor:pointer; padding:0.625rem; box-shadow:none; line-height:1;"
							aria-label={t('diary.suppDelete', { name: s.name })}>✕</button>
					{/if}
				</div>
			{/each}
			{#if supplements.length === 0}
				<div style="text-align:center; color:rgba(255,255,255,0.4); font-size:0.8rem; padding:1rem 0;">
					Aún no tienes suplementos. Añade uno abajo.
				</div>
			{/if}
		</div>
		<div style="display:flex; gap:0.5rem;">
			<input
				bind:value={newSuppName}
				placeholder={t('diary.supplementName')}
				onkeydown={(e) => { if (e.key === 'Enter') addSupp(); }}
				style="flex:1; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:10px; color:#fff; padding:0.5rem 0.75rem; font-size:0.875rem; font-family:inherit; outline:none;"
			/>
			<button onclick={addSupp} disabled={addingSuppName || !newSuppName.trim()} style="padding:0.5rem 0.875rem; border-radius:10px; background:var(--primary); color:var(--primary-ink); font-weight:700; font-size:0.8rem; border:none; cursor:pointer; opacity:{!newSuppName.trim() ? '0.5' : '1'};">
				+ Añadir
			</button>
		</div>
	</Modal>
{/if}

{#snippet entryCard(entry: DiaryEntry, shared: DiaryEntry | null = null)}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
	<div class="card" class:shared-card={!!shared} class:mine-card={!shared && showPartner && !!partner} style="--phue:{partnerHue}; --mhue:{myHue}; margin-bottom:0.4rem; display:flex; justify-content:space-between; align-items:center; cursor:pointer;"
		onclick={() => startEdit(entry)}
		role="button"
		tabindex="0"
		onkeydown={(e) => { if (e.key === 'Enter') startEdit(entry); }}>
		<div style="flex:1; min-width:0;">
			<div class="diary-entry-name" style="font-weight:600; font-size:0.9rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
				{entry.product?.name ?? `Producto #${entry.product_id}`}
			</div>
			<div class="diary-entry-detail" style="font-size:0.78rem; color:var(--text-muted);">
				{entry.grams}{entry.product ? productUnit(entry.product) : 'g'} · {fmtTime(entry.consumed_at)}
			</div>
			{#if shared}
				<div class="shared-line">
					<span class="shared-avs">
						<span class="shared-av"><Avatar name={auth.user?.name ?? t('diary.you')} avatarId={auth.user?.avatar_id} identityHue={myHue} size={16} /></span>
						<span class="shared-av"><Avatar name={partner?.name ?? ''} avatarId={partner?.avatar_id} identityHue={partnerHue} size={16} /></span>
					</span>
					<span class="shared-txt">Los dos · tú {Math.round(entry.grams)}{entry.product ? productUnit(entry.product) : 'g'} · {partner?.name} {Math.round(shared.grams)}{shared.product ? productUnit(shared.product) : 'g'}</span>
				</div>
			{/if}
		</div>
		<div style="text-align:right; margin-right:0.5rem;">
			<div class="diary-entry-kcal" style="font-size:0.85rem; color:var(--cal);">{Math.round(entry.calories)} kcal</div>
			<div class="diary-entry-macros" style="font-size:0.72rem; font-variant-numeric:tabular-nums;">
				<span style="color:oklch(78% 0.14 220);">P{Math.round(entry.protein)}</span>
				<span style="color:oklch(78% 0.16 275);"> C{Math.round(entry.carbs)}</span>
				<span style="color:oklch(75% 0.17 25);"> G{Math.round(entry.fat)}</span>
			</div>
		</div>
		<button class="btn-danger" style="padding:0.3rem 0.5rem; font-size:0.75rem; flex-shrink:0;"
			onclick={(e) => { e.stopPropagation(); startDelete(entry); }}>✕</button>
	</div>
{/snippet}

{#snippet partnerEntryCard(entry: DiaryEntry)}
	<!-- La entrada de la pareja: solo lectura, con su color. El ＋ te la copia a ti. -->
	<div class="card partner-card" style="--phue:{partnerHue}; margin-bottom:0.4rem; display:flex; align-items:center; gap:0.6rem;">
		<span class="pe-av"><Avatar name={partner?.name ?? ''} avatarId={partner?.avatar_id} identityHue={partnerHue} size={30} /></span>
		<div style="flex:1; min-width:0;">
			<div style="font-weight:600; font-size:0.9rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
				{entry.product?.name ?? `Producto #${entry.product_id}`}
				<span class="pe-tag">{partner?.name}</span>
			</div>
			<div style="font-size:0.78rem; color:var(--text-muted);">
				{entry.grams}{entry.product ? productUnit(entry.product) : 'g'} · {fmtTime(entry.consumed_at)}
			</div>
		</div>
		<div style="text-align:right; margin-right:0.35rem;">
			<div style="font-size:0.85rem; color:var(--cal); opacity:0.85;">{Math.round(entry.calories)} kcal</div>
			<div style="font-size:0.72rem; font-variant-numeric:tabular-nums;">
				<span style="color:oklch(78% 0.14 220);">P{Math.round(entry.protein)}</span>
				<span style="color:oklch(78% 0.16 275);"> C{Math.round(entry.carbs)}</span>
				<span style="color:oklch(75% 0.17 25);"> G{Math.round(entry.fat)}</span>
			</div>
		</div>
		<button class="pe-copy" title={t('diary.copyToMineTitle')} aria-label={t('diary.copyToMine')}
			onclick={() => copyToMe(entry)}>＋</button>
	</div>
{/snippet}

{#if showNotifModal}
	<NotifModal onclose={() => showNotifModal = false} />
{/if}

<style>
	/* ── Pareja: chip + su día intercalado ── */
	.diary-toolbar {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
		margin-bottom: 0.75rem;
	}
	.partner-chip {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		width: auto;
		background: var(--surface, rgba(255,255,255,0.055));
		border: 1px solid var(--border, rgba(255,255,255,0.09));
		border-radius: 14px;
		padding: 0.4rem 0.7rem 0.4rem 0.45rem;
		cursor: pointer;
		box-shadow: none;
		transition: background 0.2s, border-color 0.2s;
	}
	.partner-chip:hover { filter: none; box-shadow: none; }
	.partner-chip.on {
		background: oklch(72% 0.15 var(--phue) / 0.14);
		border-color: oklch(72% 0.15 var(--phue) / 0.34);
	}
	.pc-av { display: flex; flex-shrink: 0; }
	.pc-body { display: flex; flex-direction: column; line-height: 1.15; text-align: left; }
	.pc-name { font-size: 0.8rem; font-weight: 800; color: var(--text); }
	.partner-chip.on .pc-name { color: oklch(78% 0.15 var(--phue)); }
	.pc-mac { font-size: 0.68rem; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--text-muted); margin-top: 0.05rem; }
	.pc-mac .pc-k { color: var(--cal); }
	.pc-mac .pc-p { color: oklch(78% 0.14 220); }
	.pc-supp { margin-left: 0.3rem; font-size: 0.8rem; }
	.pc-hint { color: var(--text-muted); font-weight: 600; }
	.pc-state { margin-left: auto; font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); }
	.partner-chip.on .pc-state { color: oklch(78% 0.15 var(--phue)); }

	.partner-meal-line {
		font-size: 0.7rem;
		font-weight: 600;
		color: oklch(78% 0.15 var(--phue));
		text-align: right;
		margin: -0.15rem 0.15rem 0.4rem;
	}

	/* Lo que tenéis los dos: resplandor radial desde cada borde (el tuyo desde la
	   izquierda, el suyo desde la derecha) que se funde solo en el centro — sin
	   parada transparente explícita, así no queda un "valle" oscuro entre los dos
	   tonos. La de solo-ella/solo-mío usa el mismo gesto pero con un único
	   resplandor. Ninguna lleva borde de color: el sistema entero vive solo en el
	   relleno, muy tenue, para no comerse el contraste de las kcal ni de los macros. */
	.shared-card {
		background:
			radial-gradient(110% 100% at 0% 50%,   oklch(72% 0.15 var(--mhue) / 0.16), transparent 60%),
			radial-gradient(110% 100% at 100% 50%, oklch(72% 0.15 var(--phue) / 0.16), transparent 60%),
			var(--surface, rgba(255,255,255,0.055));
		border-color: rgba(255, 255, 255, 0.12);
	}
	.shared-line {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--text-muted, rgba(255,255,255,0.55));
		margin-top: 0.2rem;
		min-width: 0;
	}
	.shared-txt { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.shared-avs { display: flex; align-items: center; flex-shrink: 0; }
	.shared-av { display: flex; flex-shrink: 0; border-radius: 50%; box-shadow: 0 0 0 1.5px #0d0f14; }
	.shared-avs .shared-av:nth-child(2) { margin-left: -6px; }

	.partner-card {
		background:
			radial-gradient(130% 100% at 0% 50%, oklch(72% 0.15 var(--phue) / 0.18), transparent 65%),
			var(--surface, rgba(255,255,255,0.055));
		border-color: rgba(255, 255, 255, 0.12);
	}
	/* Tus propias entradas cuando el modo pareja está activo: mismo tratamiento
	   que .partner-card pero con tu color, para distinguir "mío" de "suyo" de un
	   vistazo sin depender solo del texto. */
	.mine-card {
		background:
			radial-gradient(130% 100% at 0% 50%, oklch(72% 0.15 var(--mhue) / 0.18), transparent 65%),
			var(--surface, rgba(255,255,255,0.055));
		border-color: rgba(255, 255, 255, 0.12);
	}
	.pe-av { display: flex; flex-shrink: 0; }
	.pe-tag {
		display: inline-block;
		font-size: 0.6rem;
		font-weight: 700;
		color: oklch(78% 0.15 var(--phue));
		background: oklch(72% 0.15 var(--phue) / 0.16);
		border: 1px solid oklch(72% 0.15 var(--phue) / 0.32);
		padding: 0.05rem 0.4rem;
		border-radius: 99px;
		margin-left: 0.3rem;
		vertical-align: middle;
	}
	.pe-copy {
		flex-shrink: 0;
		width: 30px;
		height: 30px;
		border-radius: 50%;
		background: transparent;
		border: 1px solid oklch(72% 0.15 var(--phue) / 0.34);
		color: oklch(78% 0.15 var(--phue));
		font-size: 1rem;
		font-weight: 700;
		line-height: 1;
		padding: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: none;
	}
	.pe-copy:hover { background: oklch(72% 0.15 var(--phue) / 0.14); filter: none; box-shadow: none; }

	/* ── Pareja en editar · "dos platos" ── */
	.edit-share-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		background: var(--surface, rgba(255,255,255,0.055));
		border: 1px solid var(--border, rgba(255,255,255,0.09));
		border-radius: 16px;
		padding: 0.7rem 0.85rem;
		transition: background 0.25s, border-color 0.25s;
	}
	.edit-share-row.on {
		background: oklch(75% 0.18 165 / 0.10);
		border-color: oklch(80% 0.17 165 / 0.32);
	}
	.edit-share-sub {
		font-size: 0.72rem;
		color: var(--text-muted, rgba(255,255,255,0.55));
		transition: color 0.2s;
	}
	.edit-has-badge {
		display: inline-block;
		font-size: 0.6rem;
		font-weight: 700;
		letter-spacing: 0.03em;
		color: var(--primary, oklch(85% 0.17 160));
		background: oklch(80% 0.17 165 / 0.14);
		border: 1px solid oklch(80% 0.17 165 / 0.32);
		padding: 0.08rem 0.4rem;
		border-radius: 99px;
		margin-left: 0.35rem;
		vertical-align: middle;
	}
	.edit-switch {
		width: 46px;
		height: 28px;
		flex-shrink: 0;
		border-radius: 99px;
		background: rgba(255,255,255,0.14);
		border: 1px solid rgba(255,255,255,0.12);
		position: relative;
		cursor: pointer;
		padding: 0;
		box-shadow: none;
		transition: background 0.25s;
	}
	.edit-switch::after {
		content: '';
		position: absolute;
		top: 2px;
		left: 2px;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: #fff;
		box-shadow: 0 2px 6px rgba(0,0,0,0.4);
		transition: left 0.26s cubic-bezier(0.34,1.56,0.64,1);
	}
	.edit-switch.on {
		background: linear-gradient(135deg, var(--primary, oklch(85% 0.17 160)), var(--primary-dim, oklch(72% 0.18 170)));
		border-color: transparent;
	}
	.edit-switch.on::after { left: 22px; }

	.edit-plates {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.6rem;
		margin-top: 0.6rem;
	}
	.edit-plate {
		background: var(--surface, rgba(255,255,255,0.055));
		border: 1px solid var(--border, rgba(255,255,255,0.09));
		border-radius: 14px;
		padding: 0.75rem 0.6rem;
		text-align: center;
	}
	.edit-plate.you {
		border-color: oklch(72% 0.14 220 / 0.35);
		background: oklch(72% 0.14 220 / 0.07);
	}
	.edit-plate.her {
		border-color: oklch(80% 0.17 165 / 0.32);
		background: oklch(75% 0.18 165 / 0.08);
	}
	.edit-plate-av { display: flex; justify-content: center; }
	.edit-plate-who {
		font-size: 0.72rem;
		color: var(--text-muted, rgba(255,255,255,0.55));
		margin-top: 0.45rem;
	}
	.edit-plate-g {
		display: flex;
		align-items: baseline;
		justify-content: center;
		gap: 0.2rem;
		margin-top: 0.35rem;
	}
	.edit-plate-g input {
		width: 62px;
		background: rgba(0,0,0,0.25);
		border: 1px solid var(--border, rgba(255,255,255,0.09));
		border-radius: 10px;
		color: #fff;
		font-size: 1rem;
		font-weight: 800;
		padding: 0.3rem 0.35rem;
		text-align: center;
		font-family: inherit;
		outline: none;
	}
	.edit-plate-g span {
		font-size: 0.72rem;
		color: var(--text-faint, rgba(255,255,255,0.35));
	}

	/* ── Modal de borrado · tarjetas por persona ── */
	.del-q { color: var(--text-muted, rgba(255,255,255,0.55)); font-size: 0.85rem; margin-bottom: 0.9rem; }
	.del-cards { display: flex; flex-direction: column; gap: 0.5rem; }
	.del-card {
		display: flex; align-items: center; gap: 0.75rem; width: 100%;
		background: var(--surface, rgba(255,255,255,0.055));
		border: 1px solid var(--border, rgba(255,255,255,0.09));
		border-radius: 14px; padding: 0.7rem 0.85rem; cursor: pointer; text-align: left;
		color: var(--text, #eef1f5);
		box-shadow: none; transition: background 0.18s, border-color 0.18s;
	}
	.del-card:hover { background: var(--surface-hover, rgba(255,255,255,0.09)); }
	.del-card.danger {
		border-color: oklch(70% 0.2 25 / 0.35);
		background: oklch(65% 0.2 25 / 0.08);
	}
	/* Ancho fijo y centrado para que el título de las 3 tarjetas quede alineado,
	   tenga 1 avatar o 2 (los dos). */
	.del-avs { display: flex; align-items: center; justify-content: center; width: 56px; flex-shrink: 0; }
	.del-avs > :global(:nth-child(2)) { margin-left: -14px; box-shadow: 0 0 0 2px rgba(0,0,0,0.45); border-radius: 50%; }
	.del-txt { flex: 1; min-width: 0; }
	.del-t { font-size: 0.9rem; font-weight: 700; }
	.del-card.danger .del-t { color: oklch(80% 0.15 25); }
	.del-s { font-size: 0.72rem; color: var(--text-muted, rgba(255,255,255,0.55)); margin-top: 0.05rem; }
	.del-chev { color: var(--text-faint, rgba(255,255,255,0.35)); font-size: 1.1rem; flex-shrink: 0; }

	.cache-notice {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.4rem;
		font-size: 0.72rem;
		color: rgba(255,255,255,0.45);
		background: rgba(255,255,255,0.04);
		border: 1px solid rgba(255,255,255,0.07);
		border-radius: 10px;
		padding: 0.4rem 0.875rem;
		margin-bottom: 0.5rem;
	}
</style>
