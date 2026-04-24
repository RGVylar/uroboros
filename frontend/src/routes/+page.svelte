<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { DaySummary, Goals, WaterDay, FrequentProduct, User, DiaryEntry, CreatineToday, CheatDayToday, MealSection } from '$lib/types';
	import { MEAL_LABELS, MEAL_ORDER } from '$lib/types';
	import {
		DayNav,
		CalorieRing,
		MacroBar,
		MealHeader,
		Modal,
		EmptyState,
	} from '$lib/components';

	if (!auth.isLoggedIn) goto('/login');

	let today = $state(new Date().toISOString().slice(0, 10));
	let summary: DaySummary | null = $state(null);
	let goals: Goals | null = $state(null);
	let water: WaterDay | null = $state(null);
	let frequent: FrequentProduct[] = $state([]);
	let streak = $state(0);
	let users: User[] = $state([]);
	let loading = $state(true);
	let copyingYesterday = $state(false);
	let creatine: CreatineToday | null = $state(null);
	let togglingCreatine = $state(false);
	let cheatDay: CheatDayToday | null = $state(null);
	let togglingCheatDay = $state(false);

	// Edit state
	let editingEntry: DiaryEntry | null = $state(null);
	let editGrams = $state(100);
	let editMealType = $state('snack');
	let editSaving = $state(false);

	// Delete confirm state
	let deletingEntry: DiaryEntry | null = $state(null);
	let savingRecipe = $state(false);
	let recipeMealToSave: MealSection | null = $state(null);
	let recipeNameDraft = $state('');
	let recipeSaveError = $state('');
	let recipeSaveSuccess = $state('');

	async function load() {
		loading = true;
		try {
			const isTodayVal = today === new Date().toISOString().slice(0, 10);
			const streakPromise = isTodayVal
				? api.get<{ streak: number }>('/diary/streak').catch(() => ({ streak: 0 }))
				: Promise.resolve({ streak: 0 });
			const [s, g, w, f, st, u] = await Promise.all([
				api.get<DaySummary>(`/diary/day?day=${today}`),
				api.get<Goals>('/goals').catch(() => null),
				api.get<WaterDay>(`/water/day?day=${today}`).catch(() => null),
				api.get<FrequentProduct[]>('/products/frequent?limit=5').catch(() => []),
				streakPromise,
				api.get<User[]>('/users').catch(() => []),
			]);
			summary = s;
			goals = g;
			water = w;
			frequent = f;
			streak = st.streak;
			users = u;
			// Load creatine status only if tracking enabled and viewing today
			if (g?.track_creatine && isTodayVal) {
				creatine = await api.get<CreatineToday>('/creatine/today').catch(() => null);
			} else {
				creatine = null;
			}
			// Load cheat day status only if enabled and viewing today
			if (g?.cheat_days_enabled && isTodayVal) {
				cheatDay = await api.get<CheatDayToday>('/cheat-days/today').catch(() => null);
			} else {
				cheatDay = null;
			}
		} catch {
			// handled
		} finally {
			loading = false;
		}
	}

	$effect(() => { today; load(); });

	function pct(current: number, goal: number) {
		if (!goal) return 0;
		return Math.min(Math.round((current / goal) * 100), 100);
	}

	let partner = $derived(users.find(u => u.id !== auth.user?.id) ?? null);

	function startDelete(entry: DiaryEntry) {
		if (partner) {
			deletingEntry = entry;
		} else {
			confirmDelete(entry.id, false);
		}
	}

	async function confirmDelete(id: number, alsoForPartner: boolean) {
		deletingEntry = null;
		const url = alsoForPartner && partner
			? `/diary/${id}?also_for_user_id=${partner.id}`
			: `/diary/${id}`;
		await api.del(url);
		load();
	}

	function startEdit(entry: DiaryEntry) {
		editingEntry = entry;
		editGrams = entry.grams;
		editMealType = entry.meal_type;
	}

	async function saveEdit() {
		if (!editingEntry) return;
		editSaving = true;
		try {
			await api.patch(`/diary/${editingEntry.id}`, { grams: editGrams, meal_type: editMealType });
			editingEntry = null;
			load();
		} catch {
			// ignore
		} finally {
			editSaving = false;
		}
	}

	async function addWater(ml: number) {
		water = await api.post<WaterDay>('/water/log', { ml, logged_date: today });
	}

	async function removeWater() {
		water = await api.del<WaterDay>(`/water/log/last?day=${today}`);
	}

	async function copyFromYesterday() {
		copyingYesterday = true;
		try {
			const res = await api.post<{ copied: number }>('/diary/copy-from-yesterday', {});
			if (res.copied > 0) load();
		} catch {
			// ignore
		} finally {
			copyingYesterday = false;
		}
	}

	async function toggleCreatine() {
		if (togglingCreatine) return;
		togglingCreatine = true;
		try {
			if (creatine?.taken) {
				creatine = await api.del<CreatineToday>('/creatine/today');
			} else {
				creatine = await api.post<CreatineToday>('/creatine/log', {});
			}
		} catch {
			// ignore
		} finally {
			togglingCreatine = false;
		}
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
				const st = await api.get<{ streak: number }>('/diary/streak').catch(() => ({ streak: 0 }));
				streak = st.streak;
			}
		} catch {
			// ignore
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
			await api.post('/recipes', { name, ingredients, is_shared: false });
			recipeSaveSuccess = 'Receta guardada.';
			closeRecipeModal();
		} catch (err: any) {
			recipeSaveError = 'Error guardando la receta: ' + (err?.message || err);
		} finally {
			savingRecipe = false;
		}
	}

	function fmtTime(iso: string) {
		return new Date(iso).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' });
	}

	let isToday = $derived(today === new Date().toISOString().slice(0, 10));
</script>

{#if !auth.isLoggedIn}
	<!-- redirect handled above -->
{:else}
	<DayNav bind:date={today} {streak} />

	{#if recipeSaveSuccess}
		<div class="card" style="margin-bottom:0.75rem; border-color:var(--primary); color:var(--primary); font-size:0.85rem; padding:0.65rem 0.8rem;">
			{recipeSaveSuccess}
		</div>
	{/if}

	<!-- Floating add button -->
	<button class="fab" aria-label="Añadir comida" title="Añadir comida" onclick={() => goto(`/add?date=${today}`)}>
		<span class="fab-icon">➕</span>
	</button>

	{#if loading}
		<p style="text-align:center; color:var(--text-muted); padding:2rem 0;">Cargando...</p>
	{:else if summary}

		<!-- Hero calories card -->
		<div class="card" style="margin-bottom:1rem; margin-top:0.75rem;">
			{#if goals}
				<CalorieRing
					consumed={summary.totals.calories}
					goal={goals.kcal}
					burned={summary.calories_burned}
					net={summary.net_calories}
				/>
				<div style="height:1rem;"></div>

				<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.75rem;">
					<MacroBar label="Prot"  value={summary.totals.protein} goal={goals.protein} color="var(--prot)" />
					<MacroBar label="Carb"  value={summary.totals.carbs}   goal={goals.carbs}   color="var(--carb)" />
					<MacroBar label="Grasa" value={summary.totals.fat}     goal={goals.fat}     color="var(--fat)" />
				</div>

			{:else}
				<!-- No goals -->
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

		<!-- Water section -->
		<div class="card" style="margin-bottom:1rem;">
			<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
				<span style="font-size:0.85rem; color:var(--water); font-weight:600;">Agua</span>
				{#if water}
					<span style="font-size:0.8rem; color:var(--text-muted);">
						{Math.round(water.total_ml)}ml / {water.goal_ml}ml
					</span>
				{/if}
			</div>
			{#if water}
				<div class="progress-bar" style="height:10px; margin-bottom:0.75rem;">
					<div class="fill" style="width:{pct(water.total_ml, water.goal_ml)}%; background:var(--water);"></div>
				</div>
			{/if}
			<div style="display:flex; gap:0.5rem;">
				<button onclick={() => addWater(250)} style="flex:1; font-size:0.8rem; padding:0.4rem;">+250ml</button>
				<button onclick={() => addWater(500)} style="flex:1; font-size:0.8rem; padding:0.4rem;">+500ml</button>
				<button class="btn-secondary" onclick={removeWater} style="flex:1; font-size:0.8rem; padding:0.4rem;" disabled={!water || water.total_ml <= 0}>
					Deshacer
				</button>
			</div>
		</div>

		<!-- Creatine check (only today + tracking enabled) -->
		{#if isToday && goals?.track_creatine && creatine !== null}
			<div class="card" style="margin-bottom:1rem;">
				<div style="display:flex; align-items:center; justify-content:space-between;">
					<div style="display:flex; align-items:center; gap:0.6rem;">
						<span style="font-size:1.3rem;">💊</span>
						<div>
							<div style="font-weight:700; font-size:0.9rem;">Creatina</div>
							<div style="font-size:0.75rem; color:var(--text-muted);">
								{creatine.taken ? '✅ Tomada hoy' : 'Sin registrar hoy'}
							</div>
						</div>
					</div>
					<button
						onclick={toggleCreatine}
						disabled={togglingCreatine}
						style="
							padding:0.45rem 1rem; border-radius:20px; font-size:0.8rem; font-weight:700;
							border:none; cursor:pointer; transition:background 0.2s, opacity 0.2s;
							background:{creatine.taken ? 'var(--surface)' : 'var(--primary)'};
							color:{creatine.taken ? 'var(--text-muted)' : '#000'};
							border:1px solid {creatine.taken ? 'var(--border-bright)' : 'transparent'};
							opacity:{togglingCreatine ? '0.6' : '1'};
						"
					>
						{creatine.taken ? 'Deshacer' : 'Marcar tomada'}
					</button>
				</div>
			</div>
		{/if}

		<!-- Cheat day (only today + enabled) -->
		{#if isToday && goals?.cheat_days_enabled && cheatDay !== null}
			<div class="card" style="margin-bottom:1rem; {cheatDay.active ? 'border-color: #ff6b35;' : ''}">
				<div style="display:flex; align-items:center; justify-content:space-between;">
					<div style="display:flex; align-items:center; gap:0.6rem;">
						<span style="font-size:1.3rem;">🍕</span>
						<div>
							<div style="font-weight:700; font-size:0.9rem;">Cheat day</div>
							<div style="font-size:0.75rem; color:var(--text-muted);">
								{cheatDay.active ? '✅ Racha protegida hoy' : 'Úsalo si no vas a registrar hoy'}
							</div>
						</div>
					</div>
					<button
						onclick={toggleCheatDay}
						disabled={togglingCheatDay}
						style="
							padding:0.45rem 1rem; border-radius:20px; font-size:0.8rem; font-weight:700;
							border:none; cursor:pointer; transition:background 0.2s, opacity 0.2s;
							background:{cheatDay.active ? 'var(--surface)' : '#ff6b35'};
							color:{cheatDay.active ? 'var(--text-muted)' : '#fff'};
							border:1px solid {cheatDay.active ? 'var(--border-bright)' : 'transparent'};
							opacity:{togglingCheatDay ? '0.6' : '1'};
						"
					>
						{cheatDay.active ? 'Cancelar' : 'Activar'}
					</button>
				</div>
			</div>
		{/if}

		<!-- Diary entries -->
		{#if summary.entries.length === 0}
			<EmptyState
				icon="🥣"
				title="Sin registros"
				description={isToday ? 'Añade tu primera comida del día' : 'Este día está vacío'}
				actionLabel={isToday ? 'Añadir comida' : undefined}
				actionHref={isToday ? `/add?date=${today}` : undefined}
			/>
			{#if isToday}
				<button
					class="btn-secondary"
					onclick={copyFromYesterday}
					disabled={copyingYesterday}
					style="width:100%; margin-top:0.75rem; margin-bottom:1rem;">
					{copyingYesterday ? 'Copiando...' : '↩ Igual que ayer'}
				</button>
			{/if}
			<!-- Frequently used -->
			{#if frequent.length > 0}
				<div style="margin-top:0.5rem;">
					<div style="font-weight:700; font-size:0.9rem; margin-bottom:0.5rem; color:var(--text-muted);">
						Usados frecuentemente
					</div>
					<div style="display:flex; flex-direction:column; gap:0.4rem;">
						{#each frequent as freq (freq.product.id)}
							<a href="/add?date={today}" style="text-decoration:none;">
								<div class="card" style="cursor:pointer; transition:border-color 0.2s;">
									<div style="display:flex; justify-content:space-between; align-items:start;">
										<div style="flex:1;">
											<div style="font-weight:600; font-size:0.9rem;">{freq.product.name}</div>
											{#if freq.product.brand}<div style="font-size:0.8rem; color:var(--text-muted);">{freq.product.brand}</div>{/if}
											<div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.25rem;">Usado {freq.count} veces</div>
										</div>
										<div style="text-align:right; margin-left:0.5rem; white-space:nowrap;">
											<div style="font-size:0.85rem; color:var(--cal); font-weight:600;">{freq.product.calories_per_100g} kcal/100g</div>
										</div>
									</div>
								</div>
							</a>
						{/each}
					</div>
				</div>
			{/if}
		{:else}
			<!-- Copy yesterday compact -->
			{#if isToday}
				<div style="display:flex; justify-content:flex-end; margin-bottom:0.5rem;">
					<button
						class="btn-secondary"
						onclick={copyFromYesterday}
						disabled={copyingYesterday}
						style="font-size:0.75rem; padding:0.3rem 0.7rem;">
						{copyingYesterday ? '...' : '↩ Igual que ayer'}
					</button>
				</div>
			{/if}

			{#if summary.meals && summary.meals.length > 0}
				{#each summary.meals as meal (meal.meal_type)}
					<div style="margin-bottom:1rem;">
						<MealHeader
							label={meal.label}
							kcal={meal.totals.calories}
							protein={meal.totals.protein}
							hasEntries={meal.entries.length > 0}
						>
							{#snippet actions()}
								<button
									class="btn-ghost"
									onclick={(e) => { e.stopPropagation(); startSaveMealAsRecipe(meal); }}
									disabled={meal.entries.length === 0}
									style="font-size:0.72rem; padding:0.25rem 0.55rem;"
								>
									＋ Receta
								</button>
							{/snippet}
						</MealHeader>
						{#each meal.entries as entry (entry.id)}
							{@render entryCard(entry)}
						{/each}
					</div>
				{/each}
			{:else}
				{#each summary.entries as entry (entry.id)}
					{@render entryCard(entry)}
				{/each}
			{/if}
		{/if}
	{/if}
{/if}

<!-- Save recipe modal -->
{#if recipeMealToSave}
	<Modal
		onClose={closeRecipeModal}
		title="Guardar receta"
		subtitle="{recipeMealToSave.label} · {recipeMealToSave.entries.length} ingredientes"
	>
		<div class="form-group">
			<label for="recipe-name">Nombre</label>
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
			<button class="btn-secondary" onclick={closeRecipeModal} style="flex:1;" disabled={savingRecipe}>Cancelar</button>
			<button onclick={confirmSaveMealAsRecipe} style="flex:2;" disabled={savingRecipe}>
				{savingRecipe ? 'Guardando...' : 'Guardar receta'}
			</button>
		</div>
	</Modal>
{/if}

<!-- Edit modal -->
{#if editingEntry}
	<Modal
		onClose={() => editingEntry = null}
		title={editingEntry.product?.name ?? 'Editar'}
		subtitle="Editar entrada"
	>
		<div class="form-group">
			<label for="edit-grams">Gramos</label>
			<input id="edit-grams" type="number" bind:value={editGrams} min="1" step="1" style="width:100%;" />
		</div>

		<div class="form-group">
			<label>Comida</label>
			<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:0.4rem;">
				{#each MEAL_ORDER as mt}
					<button
						onclick={() => editMealType = mt}
						class:btn-secondary={editMealType !== mt}
						style="font-size:0.75rem; padding:0.4rem 0.2rem;">
						{MEAL_LABELS[mt]}
					</button>
				{/each}
			</div>
		</div>

		<div style="display:flex; gap:0.5rem; margin-top:0.75rem;">
			<button class="btn-secondary" onclick={() => editingEntry = null} style="flex:1;">Cancelar</button>
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
		title="Borrar entrada"
		subtitle="{deletingEntry.product?.name} — {deletingEntry.grams}g"
	>
		<div style="color:var(--text-muted); font-size:0.85rem; margin-bottom:1rem;">
			¿Borrar también para {partner?.name}?
		</div>
		<div style="display:flex; flex-direction:column; gap:0.5rem;">
			<button class="btn-danger" onclick={() => confirmDelete(deletingEntry!.id, true)}>
				Borrar para los dos
			</button>
			<button class="btn-secondary" onclick={() => confirmDelete(deletingEntry!.id, false)}>
				Solo para mí
			</button>
			<button class="btn-secondary" onclick={() => deletingEntry = null}>Cancelar</button>
		</div>
	</Modal>
{/if}

{#snippet entryCard(entry: DiaryEntry)}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
	<div class="card" style="margin-bottom:0.4rem; display:flex; justify-content:space-between; align-items:center; cursor:pointer;"
		onclick={() => startEdit(entry)}
		role="button"
		tabindex="0"
		onkeydown={(e) => { if (e.key === 'Enter') startEdit(entry); }}>
		<div style="flex:1; min-width:0;">
			<div style="font-weight:600; font-size:0.9rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
				{entry.product?.name ?? `Producto #${entry.product_id}`}
			</div>
			<div style="font-size:0.78rem; color:var(--text-muted);">
				{entry.grams}g · {fmtTime(entry.consumed_at)}
			</div>
		</div>
		<div style="text-align:right; margin-right:0.5rem;">
			<div style="font-size:0.85rem; color:var(--cal);">{Math.round(entry.calories)} kcal</div>
			<div style="font-size:0.72rem; color:var(--text-muted);">
				P{Math.round(entry.protein)} C{Math.round(entry.carbs)} G{Math.round(entry.fat)}
			</div>
		</div>
		<button class="btn-danger" style="padding:0.3rem 0.5rem; font-size:0.75rem; flex-shrink:0;"
			onclick={(e) => { e.stopPropagation(); startDelete(entry); }}>✕</button>
	</div>
{/snippet}
