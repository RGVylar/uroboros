<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { DaySummary, Goals, WaterDay, FrequentProduct } from '$lib/types';
	import { MEAL_LABELS } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	let today = $state(new Date().toISOString().slice(0, 10));
	let summary: DaySummary | null = $state(null);
	let goals: Goals | null = $state(null);
	let water: WaterDay | null = $state(null);
	let frequent: FrequentProduct[] = $state([]);
	let loading = $state(true);

	async function load() {
		loading = true;
		try {
			[summary, goals, water, frequent] = await Promise.all([
				api.get<DaySummary>(`/diary/day?day=${today}`),
				api.get<Goals>('/goals').catch(() => null),
				api.get<WaterDay>(`/water/day?day=${today}`).catch(() => null),
				api.get<FrequentProduct[]>('/products/frequent?limit=5').catch(() => []),
			]);
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

	function changeDay(delta: number) {
		const d = new Date(today);
		d.setDate(d.getDate() + delta);
		today = d.toISOString().slice(0, 10);
	}

	async function deleteEntry(id: number) {
		await api.del(`/diary/${id}`);
		load();
	}

	async function addWater(ml: number) {
		water = await api.post<WaterDay>('/water/log', { ml, logged_date: today });
	}

	async function removeWater() {
		water = await api.del<WaterDay>(`/water/log/last?day=${today}`);
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
	<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:1rem;">
		<button class="btn-secondary" onclick={() => changeDay(-1)}>◀</button>
		<h1 style="margin:0; font-size:1.1rem;">
			{isToday ? 'Hoy' : new Date(today + 'T12:00').toLocaleDateString('es', { weekday: 'short', day: 'numeric', month: 'short' })}
		</h1>
		<button class="btn-secondary" onclick={() => changeDay(1)}>▶</button>
	</div>

	{#if loading}
		<p style="text-align:center; color:var(--text-muted); padding:2rem 0;">Cargando...</p>
	{:else if summary}

		<!-- Macro progress bars -->
		<div class="card" style="margin-bottom:1rem;">
			{#if goals}
				<!-- Calories — big featured bar -->
				<div style="margin-bottom:1.25rem;">
					<div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:0.4rem;">
						<span style="font-weight:700; font-size:1rem; color:var(--cal);">Calorías</span>
						<span style="font-size:0.9rem; color:var(--text-muted);">
							<span style="color:var(--cal); font-weight:700;">{Math.round(summary.totals.calories)}</span>
							/ {goals.kcal} kcal
						</span>
					</div>
					<div class="progress-bar" style="height:14px;">
						<div class="fill" style="width:{pct(summary.totals.calories, goals.kcal)}%; background:var(--cal);"></div>
					</div>
					<div style="text-align:right; font-size:0.72rem; color:var(--text-muted); margin-top:0.2rem;">
						{pct(summary.totals.calories, goals.kcal)}%
					</div>
				</div>

				<!-- Protein -->
				<div style="margin-bottom:1rem;">
					<div style="display:flex; justify-content:space-between; margin-bottom:0.35rem;">
						<span style="font-size:0.85rem; color:var(--prot); font-weight:600;">Proteína</span>
						<span style="font-size:0.8rem; color:var(--text-muted);">{Math.round(summary.totals.protein)}g / {goals.protein}g</span>
					</div>
					<div class="progress-bar" style="height:10px;">
						<div class="fill" style="width:{pct(summary.totals.protein, goals.protein)}%; background:var(--prot);"></div>
					</div>
				</div>

				<!-- Carbs -->
				<div style="margin-bottom:1rem;">
					<div style="display:flex; justify-content:space-between; margin-bottom:0.35rem;">
						<span style="font-size:0.85rem; color:var(--carb); font-weight:600;">Carbohidratos</span>
						<span style="font-size:0.8rem; color:var(--text-muted);">{Math.round(summary.totals.carbs)}g / {goals.carbs}g</span>
					</div>
					<div class="progress-bar" style="height:10px;">
						<div class="fill" style="width:{pct(summary.totals.carbs, goals.carbs)}%; background:var(--carb);"></div>
					</div>
				</div>

				<!-- Fat -->
				<div>
					<div style="display:flex; justify-content:space-between; margin-bottom:0.35rem;">
						<span style="font-size:0.85rem; color:var(--fat); font-weight:600;">Grasa</span>
						<span style="font-size:0.8rem; color:var(--text-muted);">{Math.round(summary.totals.fat)}g / {goals.fat}g</span>
					</div>
					<div class="progress-bar" style="height:10px;">
						<div class="fill" style="width:{pct(summary.totals.fat, goals.fat)}%; background:var(--fat);"></div>
					</div>
				</div>

			{:else}
				<!-- No goals set -->
				<div style="display:flex; justify-content:space-between; align-items:center;">
					<div>
						<div style="font-size:1.4rem; font-weight:700; color:var(--cal);">{Math.round(summary.totals.calories)} kcal</div>
						<div style="font-size:0.8rem; color:var(--text-muted);">
							P{Math.round(summary.totals.protein)}g · C{Math.round(summary.totals.carbs)}g · G{Math.round(summary.totals.fat)}g
						</div>
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
				<span style="font-size:0.85rem; color:#4fc3f7; font-weight:600;">Agua</span>
				{#if water}
					<span style="font-size:0.8rem; color:var(--text-muted);">
						{Math.round(water.total_ml)}ml / {water.goal_ml}ml
					</span>
				{/if}
			</div>
			{#if water}
				<div class="progress-bar" style="height:10px; margin-bottom:0.75rem;">
					<div class="fill" style="width:{pct(water.total_ml, water.goal_ml)}%; background:#4fc3f7;"></div>
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

		<!-- Frequently used products (if any) -->
		{#if frequent.length > 0 && summary.entries.length === 0}
			<div style="margin-bottom:1rem;">
				<div style="font-weight:700; font-size:0.9rem; margin-bottom:0.5rem; color:var(--text-muted);">
					Usados frecuentemente
				</div>
				<div style="display:flex; flex-direction:column; gap:0.4rem;">
					{#each frequent as freq (freq.product.id)}
						<a href="/add" style="text-decoration:none;">
							<div style="border:1px solid var(--border); border-radius:8px; padding:0.6rem; background:var(--surface); cursor:pointer; transition:border-color 0.2s;">
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

		<!-- Diary entries grouped by meal -->
		{#if summary.entries.length === 0}
			<p style="text-align:center; color:var(--text-muted); padding:2rem 0;">
				Sin registros hoy.<br /><a href="/add">Añadir comida</a>
			</p>
		{:else if summary.meals && summary.meals.length > 0}
			{#each summary.meals as meal (meal.meal_type)}
				<div style="margin-bottom:1rem;">
					<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem; padding:0 0.25rem;">
						<span style="font-weight:700; font-size:0.9rem;">{meal.label}</span>
						<span style="font-size:0.8rem; color:var(--cal);">{Math.round(meal.totals.calories)} kcal</span>
					</div>
					{#each meal.entries as entry (entry.id)}
						<div class="card" style="margin-bottom:0.4rem; display:flex; justify-content:space-between; align-items:center;">
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
							<button class="btn-danger" style="padding:0.3rem 0.5rem; font-size:0.75rem;" onclick={() => deleteEntry(entry.id)}>✕</button>
						</div>
					{/each}
				</div>
			{/each}
		{:else}
			{#each summary.entries as entry (entry.id)}
				<div class="card" style="margin-bottom:0.5rem; display:flex; justify-content:space-between; align-items:center;">
					<div style="flex:1; min-width:0;">
						<div style="font-weight:600; font-size:0.9rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
							{entry.product?.name ?? `Producto #${entry.product_id}`}
						</div>
						<div style="font-size:0.8rem; color:var(--text-muted);">
							{entry.grams}g · {fmtTime(entry.consumed_at)}
						</div>
					</div>
					<div style="text-align:right; margin-right:0.5rem;">
						<div style="font-size:0.85rem; color:var(--cal);">{Math.round(entry.calories)} kcal</div>
						<div style="font-size:0.75rem; color:var(--text-muted);">
							P{Math.round(entry.protein)} C{Math.round(entry.carbs)} G{Math.round(entry.fat)}
						</div>
					</div>
					<button class="btn-danger" style="padding:0.3rem 0.5rem; font-size:0.75rem;" onclick={() => deleteEntry(entry.id)}>✕</button>
				</div>
			{/each}
		{/if}
	{/if}
{/if}
