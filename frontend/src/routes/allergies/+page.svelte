<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	if (!auth.isLoggedIn) goto('/login');

	const ALLERGENS = [
		{ key: 'gluten',          label: 'Gluten',        emoji: '🌾', note: 'Trigo, cebada, centeno, avena' },
		{ key: 'milk',            label: 'Leche',         emoji: '🥛', note: 'Lactosa y derivados lácteos' },
		{ key: 'eggs',            label: 'Huevos',        emoji: '🥚', note: null },
		{ key: 'peanuts',         label: 'Cacahuetes',    emoji: '🥜', note: null },
		{ key: 'nuts',            label: 'Frutos secos',  emoji: '🌰', note: 'Almendras, avellanas, nueces…' },
		{ key: 'soybeans',        label: 'Soja',          emoji: '🫘', note: null },
		{ key: 'fish',            label: 'Pescado',       emoji: '🐟', note: null },
		{ key: 'crustaceans',     label: 'Marisco',       emoji: '🦐', note: 'Crustáceos' },
		{ key: 'celery',          label: 'Apio',          emoji: '🥬', note: null },
		{ key: 'mustard',         label: 'Mostaza',       emoji: '🌿', note: null },
		{ key: 'sesame-seeds',    label: 'Sésamo',        emoji: '🌱', note: null },
		{ key: 'sulphur-dioxide', label: 'Sulfitos',      emoji: '🍷', note: 'Dióxido de azufre' },
		{ key: 'mollusks',        label: 'Moluscos',      emoji: '🦑', note: null },
		{ key: 'lupin',           label: 'Altramuces',    emoji: '🌻', note: null },
	] as const;

	type AllergenKey = typeof ALLERGENS[number]['key'];

	// active = keys currently saved for this user
	let active = $state(new Set<AllergenKey>());
	let saving = $state(new Set<AllergenKey>());
	let idMap = $state(new Map<AllergenKey, number>()); // key → allergy row id
	let loaded = $state(false);

	async function load() {
		try {
			const rows = await api.get<{ id: number; ingredient: string }[]>('/allergies');
			const newActive = new Set<AllergenKey>();
			const newIdMap = new Map<AllergenKey, number>();
			for (const row of rows) {
				const matched = ALLERGENS.find(a => a.key === row.ingredient);
				if (matched) {
					newActive.add(matched.key);
					newIdMap.set(matched.key, row.id);
				}
			}
			active = newActive;
			idMap = newIdMap;
		} catch {
			// ignore
		} finally {
			loaded = true;
		}
	}

	async function toggle(key: AllergenKey) {
		if (saving.has(key)) return;
		saving = new Set([...saving, key]);
		try {
			if (active.has(key)) {
				const id = idMap.get(key);
				if (id !== undefined) {
					await api.del(`/allergies/${id}`);
					active = new Set([...active].filter(k => k !== key));
					idMap.delete(key);
					idMap = new Map(idMap);
				}
			} else {
				const row = await api.post<{ id: number; ingredient: string }>('/allergies', { ingredient: key });
				active = new Set([...active, key]);
				idMap = new Map([...idMap, [key, row.id]]);
			}
		} catch {
			// ignore — leave state unchanged
		} finally {
			saving = new Set([...saving].filter(k => k !== key));
		}
	}

	load();
</script>

<!-- ── Header ── -->
<div style="display:flex; align-items:center; gap:0.75rem; padding:0.25rem 0 1.5rem;">
	<button onclick={() => goto('/settings')} style="background:none; border:none; color:rgba(255,255,255,0.5); font-size:1.25rem; cursor:pointer; padding:0; line-height:1; flex-shrink:0;">‹</button>
	<div style="flex:1; min-width:0;">
		<h1 style="font-size:1.875rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1; margin:0; font-family:'Lora','Georgia',serif;">Alergias</h1>
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.25rem;">Activadas según la normativa UE</div>
	</div>
	{#if active.size > 0}
		<div style="font-size:0.6875rem; color:oklch(80% 0.17 165); background:oklch(75% 0.18 165 / 0.12); border:1px solid oklch(75% 0.18 165 / 0.25); border-radius:99px; padding:0.25rem 0.625rem; flex-shrink:0;">
			{active.size} activa{active.size > 1 ? 's' : ''}
		</div>
	{/if}
</div>

<!-- ── List ── -->
<div class="allergen-group">
	{#each ALLERGENS as allergen, i (allergen.key)}
		{#if i > 0}<div class="row-divider"></div>{/if}
		<button
			class="allergen-row"
			class:is-active={active.has(allergen.key)}
			onclick={() => toggle(allergen.key)}
			disabled={saving.has(allergen.key)}
		>
			<div class="allergen-icon" class:icon-active={active.has(allergen.key)}>
				{allergen.emoji}
			</div>
			<div class="allergen-content">
				<div class="allergen-label">{allergen.label}</div>
				{#if allergen.note}
					<div class="allergen-note">{allergen.note}</div>
				{/if}
			</div>
			<div class="allergen-check" class:check-active={active.has(allergen.key)}>
				{#if saving.has(allergen.key)}
					<div class="spinner"></div>
				{:else if active.has(allergen.key)}
					✓
				{/if}
			</div>
		</button>
	{/each}
</div>

<!-- ── Disclaimer ── -->
<p style="font-size:0.625rem; color:rgba(255,255,255,0.28); line-height:1.5; margin-top:1.25rem; padding:0 0.25rem;">
	⚠️ Sistema orientativo basado en los ingredientes de Open Food Facts. Verifica siempre el etiquetado del producto.
</p>

<style>
	.allergen-group {
		background: rgba(255,255,255,0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 18px;
		overflow: hidden;
	}
	.allergen-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.875rem;
		width: 100%;
		background: none;
		border: none;
		color: #fff;
		font-family: inherit;
		text-align: left;
		cursor: pointer;
		transition: background 0.15s;
	}
	.allergen-row:hover:not(:disabled) {
		background: rgba(255,255,255,0.04);
	}
	.allergen-row:disabled {
		cursor: default;
	}
	.allergen-icon {
		width: 36px;
		height: 36px;
		border-radius: 10px;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.07);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1rem;
		flex-shrink: 0;
		transition: background 0.2s, border-color 0.2s;
	}
	.icon-active {
		background: oklch(35% 0.15 40 / 0.3);
		border-color: oklch(60% 0.2 40 / 0.35);
	}
	.allergen-content {
		flex: 1;
		min-width: 0;
	}
	.allergen-label {
		font-size: 0.8125rem;
		font-weight: 600;
		color: #fff;
	}
	.allergen-note {
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.4);
		margin-top: 0.125rem;
	}
	.allergen-check {
		width: 22px;
		height: 22px;
		border-radius: 50%;
		border: 1.5px solid rgba(255,255,255,0.15);
		background: rgba(255,255,255,0.04);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.75rem;
		color: transparent;
		flex-shrink: 0;
		transition: background 0.2s, border-color 0.2s, color 0.2s;
	}
	.check-active {
		background: oklch(35% 0.15 40 / 0.35);
		border-color: oklch(65% 0.2 40 / 0.6);
		color: oklch(85% 0.18 45);
	}
	.row-divider {
		height: 1px;
		background: rgba(255,255,255,0.05);
		margin: 0 0.875rem;
	}
	.spinner {
		width: 12px;
		height: 12px;
		border: 1.5px solid rgba(255,255,255,0.2);
		border-top-color: rgba(255,255,255,0.7);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}
	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
