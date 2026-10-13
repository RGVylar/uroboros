<script lang="ts">
	// Tarjeta de una olla en marcha (Añadir y Recetas): la olla dibujada con el
	// caldo a la altura de lo que queda, y lo comido por cada uno en su color.
	import PotDrawing from '$lib/components/PotDrawing.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { fmtServings, potEatenBy, servingsLabel, type PotPeople } from '$lib/pots';
	import type { Pot } from '$lib/types';

	let { pot, people, onclick }: { pot: Pot; people: PotPeople; onclick?: () => void } = $props();

	const mine = $derived(potEatenBy(pot, people.meId));
	const theirs = $derived(people.partnerId ? potEatenBy(pot, people.partnerId) : 0);
	const perServing = $derived(Math.round(pot.calories / pot.servings));
</script>

<button class="pot-card" {onclick}>
	<PotDrawing left={pot.remaining / pot.servings} size={84} />
	<div style="flex:1; min-width:0;">
		<div class="pot-name">{pot.name}</div>
		<div class="pot-left">{fmtServings(pot.remaining)}<span>&nbsp;/ {servingsLabel(pot.servings)}</span></div>
		{#if mine || theirs}
			<div class="pot-legend">
				<span style="color:{people.meColor}">● {t('pot.you')} {fmtServings(mine)}</span>
				{#if people.partnerName}<span style="color:{people.partnerColor}">● {people.partnerName} {fmtServings(theirs)}</span>{/if}
			</div>
		{/if}
		<div class="pot-sub">{t('pot.kcalPerServing', { kcal: perServing })}</div>
	</div>
</button>

<style>
	.pot-card {
		display: flex; align-items: center; gap: 0.875rem; width: 100%; text-align: left; font-family: inherit; cursor: pointer;
		background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.09); box-shadow: none;
		border-radius: 20px; padding: 0.75rem 0.875rem; color: #fff; font-weight: 400; margin-bottom: 0.5rem;
	}
	.pot-name { font-size: 0.9375rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.pot-left { font-size: 1.5rem; font-weight: 800; letter-spacing: -0.03em; margin: 0.05rem 0 0.2rem; }
	.pot-left span { font-size: 0.75rem; font-weight: 600; color: rgba(255,255,255,0.45); letter-spacing: 0; }
	.pot-legend { display: flex; gap: 0.75rem; font-size: 0.6875rem; font-weight: 600; margin-bottom: 0.15rem; }
	.pot-sub { font-size: 0.6875rem; color: rgba(255,255,255,0.45); }
</style>
