<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { DaySummary, Goals, WaterDay, FrequentProduct, User, DiaryEntry, CreatineToday } from '$lib/types';
	import { MEAL_LABELS, MEAL_ORDER } from '$lib/types';

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

	// Edit state
	let editingEntry: DiaryEntry | null = $state(null);
	let editGrams = $state(100);
	let editMealType = $state('snack');
	let editSaving = $state(false);

	// Delete confirm state
	let deletingEntry: DiaryEntry | null = $state(null);

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

	function calBarColor(consumed: number, goal: number): string {
		if (!goal) return 'var(--cal)';
		const ratio = consumed / goal;
		if (ratio >= 1.05) return 'var(--danger)';
		if (ratio >= 0.9) return '#ffaa44';
		return 'var(--primary)';
	}

	function changeDay(delta: number) {
		const d = new Date(today);
		d.setDate(d.getDate() + delta);
		today = d.toISOString().slice(0, 10);
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

	function fmtTime(iso: string) {
		return new Date(iso).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' });
	}

	let isToday = $derived(today === new Date().toISOString().slice(0, 10));
</script>

{#if !auth.isLoggedIn}
	<!-- redirect handled above -->
{:else}
	<!-- Day navigation -->
	<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.25rem;">
		<button class="btn-secondary" onclick={() => changeDay(-1)}>◀</button>
		<div style="text-align:center;">
			<h1 style="margin:0; font-size:1.1rem;">
				{isToday ? 'Hoy' : new Date(today + 'T12:00').toLocaleDateString('es', { weekday: 'short', day: 'numeric', month: 'short' })}
			</h1>
			{#if isToday && streak > 0}
				<div style="font-size:0.75rem; color:var(--primary); margin-top:0.1rem;">🔥 {streak} {streak === 1 ? 'día' : 'días'} de racha</div>
			{/if}
		</div>
		<button class="btn-secondary" onclick={() => changeDay(1)}>▶</button>
	</div>

	<!-- Floating add button -->
	<button class="fab" aria-label="Añadir comida" title="Añadir comida" onclick={() => goto('/add')}>
		<span class="fab-icon">➕</span>
	</button>

	{#if loading}
		<p style="text-align:center; color:var(--text-muted); padding:2rem 0;">Cargando...</p>
	{:else if summary}

		<!-- Hero calories card -->
		<div class="card" style="margin-bottom:1rem; margin-top:0.75rem;">
			{#if goals}
				{@const consumed = Math.round(summary.totals.calories)}
				{@const burned = Math.round(summary.calories_burned)}
				{@const net = Math.round(summary.net_calories)}
				{@const remaining = goals.kcal - net}
				{@const barColor = calBarColor(net, goals.kcal)}
				{@const consumedPct = pct(consumed, goals.kcal)}
				{@const netPct = pct(net, goals.kcal)}

				<!-- 3-column hero numbers -->
				<div style="display:grid; grid-template-columns:1fr auto 1fr; gap:0.5rem; align-items:center; margin-bottom:1rem;">
					<div style="text-align:center;">
						<div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.2rem;">Consumidas</div>
						<div style="font-size:1.6rem; font-weight:800; color:var(--cal); line-height:1;">{consumed}</div>
						{#if burned > 0}
							<div style="font-size:0.6rem; color:var(--danger); margin-top:0.15rem;">−{burned} 💪</div>
						{/if}
					</div>
					<div style="text-align:center; color:var(--border-bright); font-size:1.2rem;">/</div>
					<div style="text-align:center;">
						<div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.2rem;">
							{remaining >= 0 ? 'Restantes' : 'Exceso'}
						</div>
						<div style="font-size:1.6rem; font-weight:800; color:{remaining >= 0 ? barColor : 'var(--danger)'}; line-height:1;">
							{Math.abs(remaining)}
						</div>
					</div>
				</div>

				<!-- Calorie progress bar with burned segment -->
				<div class="progress-bar" style="height:10px; margin-bottom:0.35rem; position:relative;">
					<!-- Consumed (bruto) -->
					<div class="fill" style="width:{consumedPct}%; background:{calBarColor(consumed, goals.kcal)};"></div>
					<!-- Burned overlay (rojo) -->
					{#if burned > 0}
						<div style="position:absolute; top:0; left:{Math.max(0, netPct)}%; width:{Math.min(consumedPct - netPct, 100 - netPct)}%; height:100%; background:var(--danger); opacity:0.7;"></div>
					{/if}
				</div>
				<div style="display:flex; justify-content:space-between; font-size:0.7rem; color:var(--text-muted); margin-bottom:1rem;">
					{#if burned > 0}
						<span>{netPct}% · Bruto: <strong style="color:var(--cal);">{consumed}</strong> · Neto: <strong style="color:var(--primary);">{net}</strong></span>
						<span>/ {goals.kcal} kcal</span>
					{:else}
						<span>{consumedPct}%</span>
						<span>Objetivo: {goals.kcal} kcal</span>
					{/if}
				</div>

				<!-- Macro bars -->
				<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.75rem;">
					<div>
						<div style="display:flex; justify-content:space-between; margin-bottom:0.3rem;">
							<span style="font-size:0.75rem; color:var(--prot); font-weight:600;">Prot</span>
							<span style="font-size:0.7rem; color:var(--text-muted);">{Math.round(summary.totals.protein)}/{goals.protein}g</span>
						</div>
						<div class="progress-bar" style="height:6px;">
							<div class="fill" style="width:{pct(summary.totals.protein, goals.protein)}%; background:var(--prot);"></div>
						</div>
					</div>
					<div>
						<div style="display:flex; justify-content:space-between; margin-bottom:0.3rem;">
							<span style="font-size:0.75rem; color:var(--carb); font-weight:600;">Carb</span>
							<span style="font-size:0.7rem; color:var(--text-muted);">{Math.round(summary.totals.carbs)}/{goals.carbs}g</span>
						</div>
						<div class="progress-bar" style="height:6px;">
							<div class="fill" style="width:{pct(summary.totals.carbs, goals.carbs)}%; background:var(--carb);"></div>
						</div>
					</div>
					<div>
						<div style="display:flex; justify-content:space-between; margin-bottom:0.3rem;">
							<span style="font-size:0.75rem; color:var(--fat); font-weight:600;">Grasa</span>
							<span style="font-size:0.7rem; color:var(--text-muted);">{Math.round(summary.totals.fat)}/{goals.fat}g</span>
						</div>
						<div class="progress-bar" style="height:6px;">
							<div class="fill" style="width:{pct(summary.totals.fat, goals.fat)}%; background:var(--fat);"></div>
						</div>
					</div>
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

		<!-- Diary entries -->
		{#if summary.entries.length === 0}
			<p style="text-align:center; color:var(--text-muted); padding:1.5rem 0 0.5rem;">
				Sin registros hoy.<br /><a href="/add">Añadir comida</a>
			</p>
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
							<a href="/add" style="text-decoration:none;">
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
						<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem; padding:0 0.25rem;">
							<span style="font-weight:700; font-size:0.9rem;">{meal.label}</span>
							<span style="font-size:0.8rem; color:var(--cal);">{Math.round(meal.totals.calories)} kcal</span>
						</div>
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

<!-- Edit modal -->
{#if editingEntry}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div style="position:fixed; inset:0; background:rgba(0,0,0,0.65); z-index:300; display:flex; align-items:flex-end; justify-content:center; padding:1rem;" onclick={(e) => { if (e.target === e.currentTarget) editingEntry = null; }}>
		<div class="card" style="width:100%; max-width:480px; padding:1.25rem;">
			<div style="font-weight:700; margin-bottom:0.75rem;">{editingEntry.product?.name}</div>

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
		</div>
	</div>
{/if}

<!-- Delete confirm (when partner exists) -->
{#if deletingEntry}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div style="position:fixed; inset:0; background:rgba(0,0,0,0.65); z-index:300; display:flex; align-items:center; justify-content:center; padding:1rem;" onclick={(e) => { if (e.target === e.currentTarget) deletingEntry = null; }}>
		<div class="card" style="width:100%; max-width:380px; padding:1.25rem;">
			<div style="font-weight:700; margin-bottom:0.5rem;">Borrar entrada</div>
			<div style="color:var(--text-muted); font-size:0.85rem; margin-bottom:1rem;">
				{deletingEntry.product?.name} — {deletingEntry.grams}g<br/>
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
		</div>
	</div>
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
