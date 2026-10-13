<script lang="ts">
	// Crear una olla: ingredientes en crudo (a mano o copiados de una receta),
	// para cuántas raciones da y, si se quiere, el peso ya cocinada.
	import Icon from '$lib/components/Icon.svelte';
	import { api } from '$lib/api';
	import { t } from '$lib/i18n/index.svelte';
	import { gramsToQty, productUnitOf, qtyToGrams, unitSuffix } from '$lib/drink';
	import type { Pot, Product, Recipe, User } from '$lib/types';

	type Item = { product: Pick<Product, 'id' | 'name' | 'brand' | 'unit' | 'calories_per_100g'>; grams: number };

	let {
		partner,
		recipes,
		fromRecipe = null,
		oncreated,
		oncancel,
	}: {
		partner: User | null;
		recipes: Recipe[];
		fromRecipe?: Recipe | null;
		oncreated: (pot: Pot) => void;
		oncancel: () => void;
	} = $props();

	let name = $state('');
	let items = $state<Item[]>([]);
	let servings = $state(4);
	let shared = $state(true);
	let weigh = $state(false);
	let gross = $state<number | null>(null);
	let tare = $state<number | null>(null);
	let query = $state('');
	let results = $state<Product[]>([]);
	let saving = $state(false);
	let error = $state('');
	let pickRecipe = $state(false);
	let searchTimer: ReturnType<typeof setTimeout> | undefined;

	const net = $derived(gross ? Math.max(0, gross - (tare ?? 0)) : null);
	const rawWeight = $derived(items.reduce((s, i) => s + i.grams, 0));
	const totalKcal = $derived(items.reduce((s, i) => s + (i.product.calories_per_100g * i.grams) / 100, 0));
	// Mismo peso que en crudo: casi seguro que no está pesada ya cocinada.
	const rawWarn = $derived(!!net && rawWeight > 0 && Math.abs(net - rawWeight) / rawWeight < 0.08);

	function loadRecipe(r: Recipe) {
		if (!name) name = r.name;
		if (r.servings) servings = r.servings;
		items = r.ingredients.map((i) => ({ product: i.product, grams: i.grams }));
		pickRecipe = false;
	}

	$effect(() => {
		if (fromRecipe) loadRecipe(fromRecipe);
	});

	function onSearch() {
		clearTimeout(searchTimer);
		const q = query.trim();
		if (q.length < 2) {
			results = [];
			return;
		}
		searchTimer = setTimeout(async () => {
			results = await api.get<Product[]>(`/products?q=${encodeURIComponent(q)}&limit=8`).catch(() => []);
		}, 300);
	}

	function add(p: Product) {
		items = [...items, { product: p, grams: 100 }];
		query = '';
		results = [];
	}

	async function create() {
		if (!items.length) {
			error = t('pot.errNoIngredients');
			return;
		}
		saving = true;
		error = '';
		try {
			const pot = await api.post<Pot>('/pots', {
				name: name.trim() || t('pot.namePlaceholder'),
				servings,
				cooked_weight: weigh && net ? net : null,
				shared: !!partner && shared,
				ingredients: items.map((i) => ({ product_id: i.product.id, grams: i.grams })),
			});
			oncreated(pot);
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		} finally {
			saving = false;
		}
	}
</script>

<div class="glass-card pot-form">
	<div style="display:flex; align-items:center; margin-bottom:0.75rem;">
		<h2 style="margin:0; font-size:1rem; color:#fff; flex:1;">{t('pot.new')}</h2>
		<button class="pf-x" onclick={oncancel} aria-label={t('common.cancel')}><Icon name="close" /></button>
	</div>

	<div class="form-group">
		<label for="pf-name">{t('pot.name')}</label>
		<input id="pf-name" bind:value={name} placeholder={t('pot.namePlaceholder')} />
	</div>

	<div class="form-group">
		<label for="pf-search">{t('pot.ingredients')}</label>
		{#if recipes.length}
			<button class="btn-secondary pf-wide" onclick={() => (pickRecipe = !pickRecipe)}><Icon name="cook" /> {t('pot.fromRecipe')}</button>
			{#if pickRecipe}
				<div class="pf-list">
					{#each recipes as r (r.id)}
						<button class="pf-row" onclick={() => loadRecipe(r)}>{r.name}</button>
					{/each}
				</div>
			{/if}
		{/if}
		<input id="pf-search" bind:value={query} oninput={onSearch} placeholder={t('pot.searchIngredient')} />
		{#if results.length}
			<div class="pf-list">
				{#each results as p (p.id)}
					<button class="pf-row" onclick={() => add(p)}>+ {p.name}{#if p.brand} <span style="color:rgba(255,255,255,0.45);">({p.brand})</span>{/if}</button>
				{/each}
			</div>
		{/if}
		{#each items as item, i (i)}
			{@const u = productUnitOf(item.product)}
			<div class="pf-item">
				<span style="flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{item.product.name}</span>
				<input
					type="number" min="0" inputmode="decimal" class="pf-qty"
					value={gramsToQty(item.grams, u)}
					oninput={(e) => (item.grams = qtyToGrams(Number((e.target as HTMLInputElement).value) || 0, u))}
				/>
				<span style="width:1.75rem; color:rgba(255,255,255,0.5);">{unitSuffix(u).trim()}</span>
				<button class="pf-x" onclick={() => (items = items.filter((_, j) => j !== i))} aria-label={t('common.delete')}><Icon name="close" /></button>
			</div>
		{/each}
		<div class="pf-hint">{t('pot.ingredientsHint')}</div>
	</div>

	<div class="form-group">
		<label for="pf-serv">{t('pot.servingsQ')}</label>
		<div style="display:flex; align-items:center; gap:0.75rem;">
			<input id="pf-serv" type="range" min="1" max="20" step="1" bind:value={servings} style="flex:1;" />
			<span style="font-size:1.25rem; font-weight:800; min-width:2ch; text-align:right;">{servings}</span>
		</div>
		{#if totalKcal}<div style="font-size:0.75rem; color:oklch(85% 0.17 160); margin-top:0.25rem;">≈ {t('pot.kcalPerServing', { kcal: Math.round(totalKcal / servings) })}</div>{/if}
	</div>

	<!-- Pesar: opcional y plegado. Sin peso, la olla va solo por raciones. -->
	<div class="pf-weigh">
		<button class="pf-weigh-head" onclick={() => (weigh = !weigh)}>
			<Icon name="weight" />
			<span style="flex:1;">
				<span style="display:block; font-size:0.8125rem; font-weight:700;">{t('pot.weigh')} <span style="font-weight:500; color:rgba(255,255,255,0.45);">· {t('pot.optional')}</span></span>
				<span style="display:block; font-size:0.6875rem; color:rgba(255,255,255,0.45);">{t('pot.weighHint')}</span>
			</span>
			<span style="color:rgba(255,255,255,0.4); transform:rotate({weigh ? 180 : 0}deg); transition:transform .2s;"><Icon name="down" /></span>
		</button>
		{#if weigh}
			<div style="padding:0.75rem;">
				<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; align-items:end;">
					<div class="form-group" style="margin:0;">
						<label for="pf-gross">{t('pot.weighFull')}</label>
						<input id="pf-gross" type="number" inputmode="numeric" min="0" bind:value={gross} />
					</div>
					<div class="form-group" style="margin:0;">
						<label for="pf-tare">{t('pot.weighEmpty')}</label>
						<input id="pf-tare" type="number" inputmode="numeric" min="0" bind:value={tare} />
					</div>
				</div>
				<div class="pf-hint">{t('pot.weighTareHint')}</div>
				{#if net}
					<div class="pf-result">
						<span>{t('pot.weighFood', { g: Math.round(net) })}</span>
						<span style="color:oklch(85% 0.17 160);">{t('pot.perServingG', { g: Math.round(net / servings) })}</span>
					</div>
					{#if rawWarn}<div class="pf-hint" style="color:oklch(82% 0.15 75);">{t('pot.weighRawWarn')}</div>{/if}
				{/if}
			</div>
		{/if}
	</div>

	{#if partner}
		<label class="pf-share">
			<input type="checkbox" bind:checked={shared} style="width:auto;" />
			<span>
				<span style="display:block;">{t('pot.shared', { name: partner.name })}</span>
				<span style="display:block; font-size:0.6875rem; color:rgba(255,255,255,0.45);">{t('pot.sharedSub')}</span>
			</span>
		</label>
	{/if}

	{#if error}<p class="error" style="margin:0 0 0.5rem;">{error}</p>{/if}
	<button style="width:100%;" onclick={create} disabled={saving}>{t('pot.create')}</button>
</div>

<style>
	.pot-form { margin-bottom: 1rem; }
	.pf-wide { width: 100%; margin-bottom: 0.5rem; display: flex; align-items: center; justify-content: center; gap: 0.4rem; }
	.pf-list { display: flex; flex-direction: column; gap: 0.25rem; margin: 0.375rem 0 0.5rem; }
	.pf-row {
		text-align: left; font-weight: 500; font-size: 0.8125rem; padding: 0.5rem 0.625rem; border-radius: 10px;
		background: rgba(255,255,255,0.05); color: #fff; border: 1px solid rgba(255,255,255,0.08); box-shadow: none;
	}
	.pf-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; padding: 0.375rem 0; border-bottom: 1px solid rgba(255,255,255,0.06); }
	.pf-qty { width: 5rem; padding: 0.35rem 0.5rem; text-align: right; }
	.pf-x {
		width: 28px; height: 28px; padding: 0; border-radius: 50%; flex-shrink: 0; box-shadow: none;
		background: rgba(255,255,255,0.07); color: rgba(255,255,255,0.55); display: flex; align-items: center; justify-content: center;
	}
	.pf-hint { font-size: 0.6875rem; color: rgba(255,255,255,0.45); margin-top: 0.375rem; }
	.pf-weigh { border: 1px solid rgba(255,255,255,0.09); border-radius: 14px; margin-bottom: 0.875rem; overflow: hidden; }
	.pf-weigh-head {
		width: 100%; display: flex; align-items: center; gap: 0.625rem; padding: 0.75rem; box-shadow: none;
		background: rgba(255,255,255,0.03); color: #fff; font-weight: 500; text-align: left; border-radius: 0;
	}
	.pf-result { display: flex; justify-content: space-between; gap: 0.5rem; margin-top: 0.625rem; padding: 0.5rem 0.625rem; border-radius: 10px; background: oklch(75% 0.15 160 / 0.1); font-size: 0.8125rem; }
	.pf-share { display: flex; align-items: center; gap: 0.625rem; font-size: 0.8125rem; margin-bottom: 0.875rem; cursor: pointer; }
</style>
