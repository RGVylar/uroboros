<script lang="ts">
	// Tarjeta de una olla en marcha (Añadir y Recetas). La barra se vacía: lo
	// lleno es lo que queda y lo comido va al final en el color de cada uno.
	import Icon from '$lib/components/Icon.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { fmtServings, potEatenBy, type PotPeople } from '$lib/pots';
	import type { Pot } from '$lib/types';

	let { pot, people, onclick }: { pot: Pot; people: PotPeople; onclick?: () => void } = $props();

	const mine = $derived(potEatenBy(pot, people.meId));
	const theirs = $derived(people.partnerId ? potEatenBy(pot, people.partnerId) : 0);
	const perServing = $derived(Math.round(pot.calories / pot.servings));
	const pct = (n: number) => `${(n / pot.servings) * 100}%`;
</script>

<button class="pot-card" {onclick}>
	<div class="pot-top">
		<div class="pot-icon"><Icon name="pot" /></div>
		<div style="flex:1; min-width:0; text-align:left;">
			<div class="pot-name">{pot.name}</div>
			<div class="pot-sub">{t('pot.kcalPerServing', { kcal: perServing })}</div>
		</div>
		<div style="text-align:right;">
			<div class="pot-left">{fmtServings(pot.remaining)}<span> / {fmtServings(pot.servings)}</span></div>
			<div class="pot-sub">{t('pot.left')}</div>
		</div>
	</div>
	<div class="pot-bar">
		<div style="width:{pct(pot.remaining)}; background:linear-gradient(90deg, oklch(82% 0.18 160), oklch(70% 0.2 170));"></div>
		<div style="width:{pct(mine)}; background:{people.meColor}; opacity:0.5;"></div>
		{#if theirs}<div style="width:{pct(theirs)}; background:{people.partnerColor}; opacity:0.5;"></div>{/if}
	</div>
	{#if mine || theirs}
		<div class="pot-legend">
			<span style="color:{people.meColor}">{t('pot.you')} {fmtServings(mine)}</span>
			{#if people.partnerName}<span style="color:{people.partnerColor}">{people.partnerName} {fmtServings(theirs)}</span>{/if}
		</div>
	{/if}
</button>

<style>
	.pot-card {
		display: block; width: 100%; text-align: left; font-family: inherit; cursor: pointer;
		background: oklch(75% 0.15 160 / 0.07);
		border: 1px solid oklch(75% 0.18 160 / 0.3);
		border-radius: 18px; padding: 0.75rem 0.875rem; color: #fff; margin-bottom: 0.5rem;
	}
	.pot-top { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.625rem; }
	.pot-icon {
		width: 36px; height: 36px; border-radius: 11px; flex-shrink: 0;
		background: oklch(75% 0.15 160 / 0.18); color: oklch(85% 0.17 160);
		display: flex; align-items: center; justify-content: center; font-size: 1.1rem;
	}
	.pot-name { font-size: 0.875rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.pot-left { font-size: 1.125rem; font-weight: 800; letter-spacing: -0.03em; }
	.pot-left span { font-size: 0.75rem; color: rgba(255,255,255,0.45); font-weight: 600; }
	.pot-sub { font-size: 0.6875rem; color: rgba(255,255,255,0.45); }
	.pot-bar { display: flex; height: 7px; border-radius: 99px; overflow: hidden; background: rgba(255,255,255,0.08); }
	.pot-legend { display: flex; gap: 0.75rem; font-size: 0.6875rem; margin-top: 0.4rem; }
</style>
