<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { DaySummary, Goals } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	let today = $state(new Date().toISOString().slice(0, 10));
	let summary: DaySummary | null = $state(null);
	let goals: Goals | null = $state(null);
	let loading = $state(true);

	async function load() {
		loading = true;
		try {
			[summary, goals] = await Promise.all([
				api.get<DaySummary>(`/diary/day?day=${today}`),
				api.get<Goals>('/goals').catch(() => null)
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

	function fmtTime(iso: string) {
		return new Date(iso).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' });
	}
</script>

{#if !auth.isLoggedIn}
	<!-- redirect handled above -->
{:else}
	<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:1rem;">
		<button class="btn-secondary" onclick={() => changeDay(-1)}>◀</button>
		<h1 style="margin:0; font-size:1.1rem;">
			{new Date(today + 'T12:00').toLocaleDateString('es', { weekday: 'short', day: 'numeric', month: 'short' })}
		</h1>
		<button class="btn-secondary" onclick={() => changeDay(1)}>▶</button>
	</div>

	{#if loading}
		<p style="text-align:center; color:var(--text-muted);">Cargando...</p>
	{:else if summary}
		<div class="card" style="margin-bottom:1rem;">
			<div class="macro-grid">
				<div>
					<div class="label">Kcal</div>
					<div class="value" style="color:var(--cal);">{Math.round(summary.totals.calories)}</div>
					{#if goals}
						<div class="label">{goals.kcal}</div>
						<div class="progress-bar"><div class="fill" style="width:{pct(summary.totals.calories, goals.kcal)}%;background:var(--cal)"></div></div>
					{/if}
				</div>
				<div>
					<div class="label">Prot</div>
					<div class="value" style="color:var(--prot);">{Math.round(summary.totals.protein)}g</div>
					{#if goals}
						<div class="label">{goals.protein}g</div>
						<div class="progress-bar"><div class="fill" style="width:{pct(summary.totals.protein, goals.protein)}%;background:var(--prot)"></div></div>
					{/if}
				</div>
				<div>
					<div class="label">Carb</div>
					<div class="value" style="color:var(--carb);">{Math.round(summary.totals.carbs)}g</div>
					{#if goals}
						<div class="label">{goals.carbs}g</div>
						<div class="progress-bar"><div class="fill" style="width:{pct(summary.totals.carbs, goals.carbs)}%;background:var(--carb)"></div></div>
					{/if}
				</div>
				<div>
					<div class="label">Grasa</div>
					<div class="value" style="color:var(--fat);">{Math.round(summary.totals.fat)}g</div>
					{#if goals}
						<div class="label">{goals.fat}g</div>
						<div class="progress-bar"><div class="fill" style="width:{pct(summary.totals.fat, goals.fat)}%;background:var(--fat)"></div></div>
					{/if}
				</div>
			</div>
		</div>

		{#if summary.entries.length === 0}
			<p style="text-align:center; color:var(--text-muted); padding:2rem 0;">
				Sin registros hoy.<br /><a href="/add">Añadir comida</a>
			</p>
		{:else}
			{#each summary.entries as entry (entry.id)}
				<div class="card" style="margin-bottom:0.5rem; display:flex; justify-content:space-between; align-items:center;">
					<div style="flex:1; min-width:0;">
						<div style="font-weight:600; font-size:0.9rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
							{entry.product?.name ?? `Producto #${entry.product_id}`}
						</div>
						<div style="font-size:0.8rem; color:var(--text-muted);">
							{entry.grams}g · {fmtTime(entry.consumed_at)}
							{#if entry.product?.brand} · {entry.product.brand}{/if}
						</div>
					</div>
					<div style="text-align:right;">
						<div style="font-size:0.85rem; color:var(--cal);">{Math.round(entry.calories)} kcal</div>
						<div style="font-size:0.75rem; color:var(--text-muted);">
							P{Math.round(entry.protein)} C{Math.round(entry.carbs)} G{Math.round(entry.fat)}
						</div>
					</div>
					<button class="btn-danger" style="padding:0.3rem 0.5rem; font-size:0.75rem; margin-left:0.5rem;" onclick={() => deleteEntry(entry.id)}>X</button>
				</div>
			{/each}
		{/if}
	{/if}
{/if}
