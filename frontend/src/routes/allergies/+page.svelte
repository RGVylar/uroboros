<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import { subscription } from '$lib/stores/subscription.svelte';
	import Aurora from '$lib/components/uro/Aurora.svelte';
	import ScreenHeader from '$lib/components/uro/ScreenHeader.svelte';
	import PaywallCard from '$lib/components/uro/PaywallCard.svelte';
	if (!auth.isLoggedIn) goto('/login');

	const ALLERGENS = [
		{ key: 'gluten',          label: 'Gluten',         emoji: '🌾', note: 'Trigo, cebada, centeno, avena' },
		{ key: 'milk',            label: 'Leche',          emoji: '🥛', note: 'Lactosa y derivados lácteos' },
		{ key: 'eggs',            label: 'Huevos',         emoji: '🥚', note: null },
		{ key: 'peanuts',         label: 'Cacahuetes',     emoji: '🥜', note: null },
		{ key: 'nuts',            label: 'Frutos secos',   emoji: '🌰', note: 'Almendras, avellanas, nueces…' },
		{ key: 'soybeans',        label: 'Soja',           emoji: '🫘', note: null },
		{ key: 'fish',            label: 'Pescado',        emoji: '🐟', note: null },
		{ key: 'crustaceans',     label: 'Marisco',        emoji: '🦐', note: 'Crustáceos' },
		{ key: 'celery',          label: 'Apio',           emoji: '🥬', note: null },
		{ key: 'mustard',         label: 'Mostaza',        emoji: '🌿', note: null },
		{ key: 'sesame-seeds',    label: 'Sésamo',         emoji: '🌱', note: null },
		{ key: 'sulphur-dioxide', label: 'Sulfitos',       emoji: '🍷', note: 'Dióxido de azufre' },
		{ key: 'mollusks',        label: 'Moluscos',       emoji: '🦑', note: null },
		{ key: 'lupin',           label: 'Altramuces',     emoji: '🌻', note: null },
	] as const;

	type AllergenKey = typeof ALLERGENS[number]['key'];

	let active = $state(new Set<AllergenKey>());
	let saving = $state(new Set<AllergenKey>());
	let idMap = $state(new Map<AllergenKey, number>());
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
			// ignore
		} finally {
			saving = new Set([...saving].filter(k => k !== key));
		}
	}

	load();
</script>

<Aurora />

<div class="page">
	<ScreenHeader
		title="Alergias"
		sub={active.size > 0 ? `${active.size} marcad${active.size === 1 ? 'a' : 'as'} · te avisaremos al añadir productos` : 'Te avisaremos si un producto contiene alguna'}
		onBack={() => goto('/settings')}
	/>

	{#if !subscription.is_premium}
		<PaywallCard
			title="Alertas de alérgenos"
			description="Detectamos automáticamente gluten, lactosa, frutos secos y 11 alérgenos más al escanear productos."
		/>
	{:else}

	<!-- Info banner -->
	<div class="banner">
		<div class="banner-icon">⚠️</div>
		<div class="banner-text">
			<div class="banner-title">Detectaremos alérgenos automáticamente</div>
			<div class="banner-sub">Al escanear o buscar productos en Open Food Facts.</div>
		</div>
	</div>

	<!-- Grid -->
	<div class="grid">
		{#each ALLERGENS as a (a.key)}
			{@const on = active.has(a.key)}
			{@const isSaving = saving.has(a.key)}
			<button
				class="chip"
				class:on
				onclick={() => toggle(a.key)}
				disabled={isSaving}
			>
				<div class="chip-icon" class:on>{a.emoji}</div>
				<div class="chip-texts">
					<div class="chip-label">{a.label}</div>
					{#if a.note}<div class="chip-note">{a.note}</div>{/if}
				</div>
				<div class="chip-check" class:on>
					{#if isSaving}
						<div class="spinner"></div>
					{:else if on}
						✓
					{/if}
				</div>
			</button>
		{/each}
	</div>

	<p class="disclaimer">
		⚠️ Sistema orientativo basado en los ingredientes de Open Food Facts. Verifica siempre el etiquetado del producto.
	</p>

	{/if}
</div>

<style>
	.page {
		position: relative;
		z-index: 1;
		max-width: 560px;
		margin: 0 auto;
		padding: 8px 16px 120px;
	}

	/* Banner */
	.banner {
		display: flex; align-items: center; gap: 12px;
		padding: 14px;
		margin-bottom: 14px;
		border-radius: 16px;
		background: rgba(255, 255, 255, 0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255, 255, 255, 0.09);
	}
	.banner-icon {
		width: 36px; height: 36px; border-radius: 12px;
		background: linear-gradient(135deg, oklch(78% 0.18 45 / 0.3), oklch(60% 0.2 30 / 0.15));
		border: 1px solid oklch(75% 0.18 45 / 0.35);
		display: flex; align-items: center; justify-content: center;
		font-size: 16px;
		flex-shrink: 0;
	}
	.banner-text { flex: 1; min-width: 0; }
	.banner-title { font-size: 12px; color: #fff; font-weight: 700; }
	.banner-sub { font-size: 10px; color: rgba(255, 255, 255, 0.5); margin-top: 2px; line-height: 1.4; }

	/* Grid */
	.grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 10px;
	}
	@media (max-width: 380px) {
		.grid { grid-template-columns: 1fr; }
	}

	.chip {
		display: flex; align-items: center; gap: 10px;
		padding: 12px;
		border-radius: 14px;
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid rgba(255, 255, 255, 0.08);
		color: #fff;
		font: inherit;
		text-align: left;
		cursor: pointer;
		position: relative;
		transition: all 0.15s;
	}
	.chip:hover:not(:disabled) { background: rgba(255, 255, 255, 0.06); }
	.chip:disabled { cursor: default; }
	.chip.on {
		background: linear-gradient(135deg, oklch(75% 0.18 30 / 0.22), rgba(255, 255, 255, 0.04));
		border-color: oklch(75% 0.18 30 / 0.5);
		box-shadow: 0 8px 24px -8px oklch(72% 0.18 30 / 0.4);
	}

	.chip-icon {
		width: 36px; height: 36px; border-radius: 11px;
		background: rgba(255, 255, 255, 0.05);
		border: 1px solid rgba(255, 255, 255, 0.07);
		display: flex; align-items: center; justify-content: center;
		font-size: 18px;
		flex-shrink: 0;
		filter: grayscale(0.4);
		transition: all 0.15s;
	}
	.chip-icon.on {
		background: oklch(75% 0.18 30 / 0.18);
		border-color: oklch(65% 0.2 40 / 0.35);
		filter: none;
	}

	.chip-texts { flex: 1; min-width: 0; }
	.chip-label { font-size: 13px; font-weight: 700; }
	.chip-note {
		font-size: 9px;
		color: rgba(255, 255, 255, 0.45);
		margin-top: 1px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.chip-check {
		width: 22px; height: 22px; border-radius: 50%;
		border: 1.5px solid rgba(255, 255, 255, 0.18);
		background: transparent;
		display: flex; align-items: center; justify-content: center;
		font-size: 12px; font-weight: 800;
		color: transparent;
		flex-shrink: 0;
		transition: all 0.15s;
	}
	.chip-check.on {
		background: oklch(78% 0.18 30);
		border-color: transparent;
		color: #1a0a05;
	}

	.spinner {
		width: 12px; height: 12px;
		border: 1.5px solid rgba(255, 255, 255, 0.2);
		border-top-color: rgba(255, 255, 255, 0.7);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}
	@keyframes spin { to { transform: rotate(360deg); } }

	.disclaimer {
		font-size: 10px;
		color: rgba(255, 255, 255, 0.28);
		line-height: 1.5;
		margin-top: 18px;
		padding: 0 4px;
	}
</style>
