<script lang="ts">
	// Bloque "¿Cuánto?" al registrar una receta: toda, una ración en gramos del
	// plato hecho, o retocando ingrediente a ingrediente ("hoy menos huevo y más
	// pan"). Lo usan la página de Recetas y la de Añadir; el payload lo montan
	// ellas a partir de `grams` y `overrides`.
	import { t } from '$lib/i18n/index.svelte';
	import { productUnitOf, unitSuffix, gramsToQty, qtyToGrams, type ProductUnit } from '$lib/drink';

	type MacroSource = {
		name: string;
		brand?: string | null;
		unit?: ProductUnit | null;
		calories_per_100g: number;
		protein_per_100g: number;
		carbs_per_100g: number;
		fat_per_100g: number;
	};
	type Ingredient = { id: number; grams: number; product?: MacroSource | null };

	interface Props {
		ingredients: Ingredient[];
		/** Lo que pesa "toda la receta" (plato hecho o suma de ingredientes). */
		weight: number;
		/** Ración en gramos del plato hecho; null = toda la receta. */
		grams: number | null;
		/** Gramos internos por ingrediente (id → g) cuando se ajusta a mano; null = sin ajustar. */
		overrides: Record<number, number> | null;
	}

	let { ingredients, weight, grams = $bindable(null), overrides = $bindable(null) }: Props = $props();

	// Escalado uniforme (toda la receta o ración): cada ingrediente por k.
	function scaled(g: number) {
		const k = weight > 0 ? g / weight : 0;
		let cal = 0, p = 0, c = 0, f = 0;
		for (const i of ingredients) {
			const factor = (i.grams * k) / 100;
			cal += (i.product?.calories_per_100g ?? 0) * factor;
			p += (i.product?.protein_per_100g ?? 0) * factor;
			c += (i.product?.carbs_per_100g ?? 0) * factor;
			f += (i.product?.fat_per_100g ?? 0) * factor;
		}
		return { grams: g, cal, p, c, f };
	}

	// Ajuste manual: la suma de lo que se ha puesto en cada fila.
	function adjusted(o: Record<number, number>) {
		let g = 0, cal = 0, p = 0, c = 0, f = 0;
		for (const i of ingredients) {
			const ig = o[i.id] ?? i.grams;
			const factor = ig / 100;
			g += ig;
			cal += (i.product?.calories_per_100g ?? 0) * factor;
			p += (i.product?.protein_per_100g ?? 0) * factor;
			c += (i.product?.carbs_per_100g ?? 0) * factor;
			f += (i.product?.fat_per_100g ?? 0) * factor;
		}
		return { grams: g, cal, p, c, f };
	}

	let summary = $derived(overrides ? adjusted(overrides) : scaled(grams ?? weight));

	function startAdjust() {
		grams = null;
		overrides = Object.fromEntries(ingredients.map(i => [i.id, i.grams]));
	}

	function unitOf(i: Ingredient): ProductUnit {
		return i.product ? productUnitOf(i.product) : 'g';
	}

	function setQty(i: Ingredient, raw: string) {
		if (!overrides) return;
		const q = parseFloat(raw);
		overrides[i.id] = Number.isFinite(q) && q >= 0 ? qtyToGrams(q, unitOf(i)) : 0;
	}
</script>

<div class="amount-row">
	<button
		type="button"
		class="chip"
		class:active={grams === null && overrides === null}
		onclick={() => { grams = null; overrides = null; }}>
		{t('recipes.wholeRecipe')} · {Math.round(weight)} g
	</button>
	<input
		type="number"
		min="1"
		step="1"
		inputmode="numeric"
		placeholder={t('recipes.portionGrams')}
		bind:value={grams}
		oninput={() => { overrides = null; }}
		class="portion-input"
	/>
</div>
<button
	type="button"
	class="chip adjust-chip"
	class:active={overrides !== null}
	onclick={() => overrides ? (overrides = null) : startAdjust()}>
	✎ {t('recipes.adjustIngredients')}
</button>

{#if overrides}
	<div class="adjust-hint">{t('recipes.adjustHint')}</div>
	<div class="adjust-list">
		{#each ingredients as i (i.id)}
			{@const u = unitOf(i)}
			<div class="adjust-item" class:adjust-item-off={(overrides[i.id] ?? i.grams) <= 0}>
				<div class="adjust-name">
					<div class="adjust-title">{i.product?.name ?? '—'}</div>
					<div class="adjust-sub">{t('recipes.adjustDefault', { qty: `${gramsToQty(i.grams, u)}${unitSuffix(u)}` })}</div>
				</div>
				<div class="adjust-input-wrap">
					<input
						type="number"
						min="0"
						step={u === 'unit' ? '0.5' : '1'}
						inputmode="decimal"
						value={gramsToQty(overrides[i.id] ?? i.grams, u)}
						oninput={(e) => setQty(i, (e.currentTarget as HTMLInputElement).value)}
						class="adjust-input"
					/>
					<span class="adjust-unit">{unitSuffix(u).trim()}</span>
				</div>
			</div>
		{/each}
	</div>
{/if}

<div class="amount-summary">
	{t('recipes.portionSummary', {
		grams: Math.round(summary.grams),
		kcal: Math.round(summary.cal),
		p: Math.round(summary.p),
		c: Math.round(summary.c),
		f: Math.round(summary.f),
	})}
</div>

<style>
	.amount-row {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		margin-bottom: 0.5rem;
	}
	.amount-row .chip { flex: 1; font-size: 0.78rem; justify-content: center; }
	.portion-input {
		flex: 1;
		min-width: 0;
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
	.portion-input:focus { border-color: oklch(75% 0.18 165 / 0.5); }
	.adjust-chip {
		width: 100%;
		justify-content: center;
		font-size: 0.78rem;
		margin-bottom: 0.5rem;
	}
	.adjust-hint {
		font-size: 0.7rem;
		color: rgba(255,255,255,0.45);
		padding: 0 0.25rem 0.5rem;
	}
	.adjust-list {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
		margin-bottom: 0.5rem;
	}
	.adjust-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background: rgba(255,255,255,0.04);
		border: 1px solid rgba(255,255,255,0.08);
		border-radius: 12px;
		padding: 0.5rem 0.625rem;
		transition: opacity 0.15s;
	}
	.adjust-item-off { opacity: 0.45; }
	.adjust-name { flex: 1; min-width: 0; }
	.adjust-title {
		font-size: 0.8125rem;
		font-weight: 600;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.adjust-sub { font-size: 0.65rem; color: rgba(255,255,255,0.4); margin-top: 0.1rem; }
	.adjust-input-wrap {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		flex-shrink: 0;
	}
	.adjust-input {
		width: 4.25rem;
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.12);
		border-radius: 10px;
		color: #fff;
		padding: 0.4rem 0.5rem;
		font-size: 0.875rem;
		font-weight: 600;
		font-family: inherit;
		text-align: right;
		outline: none;
	}
	.adjust-input:focus { border-color: oklch(75% 0.18 165 / 0.5); }
	.adjust-unit { font-size: 0.7rem; color: rgba(255,255,255,0.5); width: 1.4rem; }
	.amount-summary {
		font-size: 0.75rem;
		color: rgba(255,255,255,0.55);
		padding: 0 0.25rem;
	}
</style>
