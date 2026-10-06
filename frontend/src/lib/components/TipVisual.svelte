<!--
  TipVisual.svelte — la maqueta de lo que explica cada tip. "Este chip" o "toca
  el icono" no se entienden si no ves de qué hablamos, y una captura se queda
  vieja al primer cambio y habría que hacerla en tres idiomas. Esto se dibuja
  con los mismos colores que la app y se traduce solo.
  Es decorativo (aria-hidden): el texto del tip dice lo mismo.
-->
<script lang="ts">
	import type { TipId } from '$lib/stores/tips.svelte';
	import { t } from '$lib/i18n/index.svelte';

	let { id }: { id: TipId } = $props();

	const PARTNER_HUE = 330;
	let partner = $derived(t('tipv.partnerName'));
	let dow = $derived(t('tipv.dow').split(','));

	// Adherencia: una semana con huecos (los días sin registrar no cuentan).
	const WEEK = [85, 62, null, 40, 91, null, 70];
	const scored = WEEK.filter((s): s is number => s !== null);
	const avg = Math.round(scored.reduce((a, b) => a + b, 0) / scored.length);
	const ok = scored.filter((s) => s >= 50).length;
	function tone(s: number | null) {
		if (s === null) return 'none';
		return s >= 50 ? 'good' : 'low';
	}
</script>

<figure class="tv" aria-hidden="true">
	<figcaption class="cap">{t('tipv.example')}</figcaption>

	{#if id === 'partner_day'}
		<div class="chip on" style="--phue:{PARTNER_HUE}">
			<span class="av" style="--phue:{PARTNER_HUE}">{partner[0]}</span>
			<span class="chip-body">
				<span class="chip-name">{partner}</span>
				<span class="chip-mac"><span class="k">1240 / 1900 kc</span> · <span class="p">80 / 120 P</span></span>
			</span>
			<span class="chip-state">{t('diary.show')}</span>
		</div>
		<div class="arrow">↓ {t('tipv.partnerTap')}</div>
		<div class="row partner" style="--phue:{PARTNER_HUE}">
			<span class="av sm" style="--phue:{PARTNER_HUE}">{partner[0]}</span>
			<span class="row-main">
				<span class="row-name">{t('tipv.foodLentils')} <span class="tag">{partner}</span></span>
				<span class="row-sub">250 g · 14:05</span>
			</span>
			<span class="row-kcal">330 kcal</span>
			<span class="plus pulse">＋</span>
		</div>
		<div class="callout right">{t('tipv.partnerCopy')} ↑</div>

	{:else if id === 'duel'}
		<div class="card">
			<div class="mini-title">{t('tipv.duelWeek')}</div>
			<div class="vs">
				<span class="who">{t('tipv.you')}</span><span class="bar"><span style="width:82%"></span></span><b>82</b>
			</div>
			<div class="vs other" style="--phue:{PARTNER_HUE}">
				<span class="who">{partner}</span><span class="bar"><span style="width:74%"></span></span><b>74</b>
			</div>
		</div>
		<div class="card">
			<div class="mini-title">{t('tipv.oneDay')} · 64 / 100</div>
			<div class="pts"><span class="lbl k">{t('tipv.kcal')}</span><span class="bar"><span class="k" style="width:{48 / 70 * 100}%"></span></span><span class="num">48 / 70</span></div>
			<div class="pts"><span class="lbl p">{t('tipv.protein')}</span><span class="bar"><span class="p" style="width:{16 / 30 * 100}%"></span></span><span class="num">16 / 30</span></div>
		</div>

	{:else if id === 'adherence'}
		<div class="week">
			{#each WEEK as s, i}
				<div class="day {tone(s)}">
					<span class="dl">{dow[i]}</span>
					<span class="ds">{s ?? '—'}</span>
				</div>
			{/each}
		</div>
		<div class="foot">{t('tipv.adhSummary', { avg, ok, n: scored.length })}</div>
		<div class="legend">
			<span><i class="good"></i>{t('tipv.adhMet')}</span>
			<span><i class="low"></i>{t('tipv.adhMissed')}</span>
			<span><i class="none"></i>{t('tipv.adhBlank')}</span>
		</div>

	{:else if id === 'consistency'}
		<div class="card rank">
			{#each [[1, 96], [2, 91], [3, 88], [4, 85]] as [pos, pts]}
				<div class="rank-row" class:me={pos === 3}>
					<span class="pos">{pos}.º</span>
					<span class="rn">{pos === 3 ? t('tipv.you') : t('tipv.anon')}</span>
					<span class="rp">{pts}</span>
				</div>
			{/each}
		</div>

	{:else if id === 'circles'}
		<div class="card cmp">
			<div class="cmp-row head"><span></span><b>{t('friends.kindPartner')}</b><b>{t('friends.kindFriend')}</b></div>
			{#each [['tipv.cmpPantry', true, false], ['tipv.cmpSeeDay', true, false], ['tipv.cmpLogFor', true, false], ['tipv.cmpRecipes', true, true], ['tipv.cmpDuel', true, true]] as [key, a, b]}
				<div class="cmp-row">
					<span>{t(key as 'tipv.cmpPantry')}</span>
					<span class={a ? 'yes' : 'no'}>{a ? '✓' : '—'}</span>
					<span class={b ? 'yes' : 'no'}>{b ? '✓' : '—'}</span>
				</div>
			{/each}
			<div class="cmp-note">{t('tipv.cmpOnePartner')}</div>
		</div>

	{:else if id === 'recipe_sharing'}
		<div class="row">
			<span class="thumb">🥣</span>
			<span class="row-main">
				<span class="row-name">{t('tipv.recipeName')}</span>
				<span class="row-sub">223 kcal · P8 C35 G4</span>
			</span>
			<span class="circle-btn pulse">
				<svg viewBox="0 0 24 24" width="16" height="16"><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
			</span>
		</div>
		<div class="callout right">↑ {t('tipv.recipeTap')}</div>
		<div class="seg">
			<span>
				<svg viewBox="0 0 24 24" width="14" height="14"><rect x="5" y="11" width="14" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3" fill="none" stroke="currentColor" stroke-width="2"/></svg>
				{t('tipv.circleMe')}
			</span>
			<span>
				<svg viewBox="0 0 24 24" width="14" height="14"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>
				{t('friends.kindPartner')}
			</span>
			<span class="on">
				<svg viewBox="0 0 24 24" width="14" height="14"><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
				{t('tipv.circleFriends')}
			</span>
		</div>

	{:else if id === 'macro_adjust'}
		<div class="sum">
			<span><small>{t('tipv.goal')}</small>2000</span>
			<b>+</b>
			<span class="burn"><small>{t('tipv.burned')}</small>300</span>
			<b>=</b>
			<span class="res"><small>{t('tipv.today')}</small>2300</span>
		</div>
		<div class="card modes">
			{#each [['settings.macroOff', '2000', '150', '200', '67'], ['settings.macroProportional', '2300', '173', '230', '77'], ['settings.macroPerformance', '2300', '150', '275', '67']] as [key, k, p, c, g]}
				<div class="mode-row">
					<span class="mode">{t(key as 'settings.macroOff')}</span>
					<span class="k">{k}</span>
					<span class="p">P{p}</span>
					<span class="c">C{c}</span>
					<span class="g">G{g}</span>
				</div>
			{/each}
		</div>

	{:else if id === 'module.inventory'}
		<div class="flow">
			<div class="step"><small>{t('tipv.invPantry')}</small><b>{t('tipv.invRice')}</b><span>1000 g</span></div>
			<span class="to">→</span>
			<div class="step hl"><small>{t('tipv.invLog')}</small><b>{t('tipv.invRice')}</b><span>−100 g</span></div>
			<span class="to">→</span>
			<div class="step"><small>{t('tipv.invLeft')}</small><b>{t('tipv.invRice')}</b><span>900 g</span></div>
		</div>

	{:else if id === 'module.cheat_days'}
		<div class="week">
			{#each [80, 72, 66, 'cheat', 90, null, null] as s, i}
				<div class="day {s === 'cheat' ? 'cheat' : tone(s as number | null)}">
					<span class="dl">{dow[i]}</span>
					<span class="ds">{s === 'cheat' ? '🍕' : (s ?? '—')}</span>
				</div>
			{/each}
		</div>
		<div class="foot">{t('tipv.cheatSummary')}</div>

	{:else if id === 'module.mood'}
		<div class="card">
			{#each [['energy', 3], ['digestion', 2], ['mood', 3]] as [axis, picked]}
				<div class="mood-row">
					<span class="mood-axis">{t(`mood.${axis}` as 'mood.energy')}</span>
					<span class="levels">
						{#each [1, 2, 3] as lvl}
							<span class:on={lvl === picked}>{t(`mood.${axis}${lvl}` as 'mood.energy1')}</span>
						{/each}
					</span>
				</div>
			{/each}
		</div>
	{/if}
</figure>

<style>
	.tv {
		margin: 0 0 0.9rem;
		padding: 0.75rem;
		border-radius: 16px;
		background: rgba(255, 255, 255, 0.03);
		border: 1px dashed rgba(255, 255, 255, 0.14);
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		pointer-events: none;
		user-select: none;
	}
	.cap {
		font-size: 0.6rem;
		font-weight: 800;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: rgba(255, 255, 255, 0.4);
	}
	.card {
		padding: 0.6rem 0.7rem;
		border-radius: 12px;
		background: var(--surface, rgba(255, 255, 255, 0.055));
		border: 1px solid var(--border, rgba(255, 255, 255, 0.09));
	}
	.mini-title {
		font-size: 0.68rem;
		font-weight: 700;
		color: var(--text-muted);
		margin-bottom: 0.4rem;
	}
	.foot { font-size: 0.72rem; color: rgba(255, 255, 255, 0.7); text-align: center; }
	.k { color: var(--cal); }
	.p { color: oklch(78% 0.14 220); }
	.c { color: oklch(78% 0.16 275); }
	.g { color: oklch(75% 0.17 25); }

	/* Avatar y chip de la pareja (copia de los del diario) */
	.av {
		width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
		display: flex; align-items: center; justify-content: center;
		font-size: 0.8rem; font-weight: 800; color: #fff;
		background: linear-gradient(135deg, oklch(70% 0.17 var(--phue)), oklch(55% 0.18 calc(var(--phue) + 30)));
		box-shadow: 0 0 0 2px oklch(75% 0.15 var(--phue));
	}
	.av.sm { width: 26px; height: 26px; box-shadow: none; }
	.chip {
		display: flex; align-items: center; gap: 0.6rem;
		padding: 0.4rem 0.7rem 0.4rem 0.45rem;
		border-radius: 14px;
		background: oklch(72% 0.15 var(--phue) / 0.14);
		border: 1px solid oklch(72% 0.15 var(--phue) / 0.34);
		align-self: flex-start;
		min-width: 70%;
	}
	.chip-body { display: flex; flex-direction: column; line-height: 1.15; }
	.chip-name { font-size: 0.8rem; font-weight: 800; color: oklch(78% 0.15 var(--phue)); }
	.chip-mac { font-size: 0.68rem; font-weight: 700; font-variant-numeric: tabular-nums; }
	.chip-state {
		margin-left: auto; font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
		letter-spacing: 0.04em; color: oklch(78% 0.15 var(--phue));
	}
	.arrow { font-size: 0.7rem; color: rgba(255, 255, 255, 0.6); }
	.callout { font-size: 0.7rem; font-weight: 700; color: oklch(85% 0.15 160); }
	.callout.right { text-align: right; }

	/* Fila tipo entrada del diario / receta */
	.row {
		display: flex; align-items: center; gap: 0.55rem;
		padding: 0.5rem 0.6rem;
		border-radius: 12px;
		background: var(--surface, rgba(255, 255, 255, 0.055));
		border: 1px solid var(--border, rgba(255, 255, 255, 0.09));
	}
	.row.partner {
		background: oklch(72% 0.15 var(--phue) / 0.08);
		border-color: oklch(72% 0.15 var(--phue) / 0.28);
	}
	.row-main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
	.row-name { font-size: 0.8rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.row-sub { font-size: 0.68rem; color: var(--text-muted); }
	.row-kcal { font-size: 0.75rem; color: var(--cal); }
	.tag {
		font-size: 0.6rem; font-weight: 700; padding: 0.05rem 0.35rem; border-radius: 6px;
		color: oklch(80% 0.14 var(--phue)); background: oklch(72% 0.15 var(--phue) / 0.16);
	}
	.plus, .circle-btn {
		width: 28px; height: 28px; border-radius: 9px; flex-shrink: 0;
		display: flex; align-items: center; justify-content: center;
		font-weight: 800; color: oklch(85% 0.15 160);
		border: 1px solid oklch(75% 0.15 160 / 0.5);
		background: oklch(75% 0.15 160 / 0.12);
	}
	.thumb {
		width: 32px; height: 32px; border-radius: 10px; flex-shrink: 0;
		display: flex; align-items: center; justify-content: center;
		background: linear-gradient(135deg, oklch(70% 0.15 250), oklch(55% 0.18 280));
	}
	.pulse { animation: pulse 1.8s ease-in-out infinite; }
	@keyframes pulse {
		0%, 100% { box-shadow: 0 0 0 0 oklch(80% 0.17 160 / 0.55); }
		50% { box-shadow: 0 0 0 6px oklch(80% 0.17 160 / 0); }
	}
	@media (prefers-reduced-motion: reduce) { .pulse { animation: none; box-shadow: 0 0 0 2px oklch(80% 0.17 160 / 0.6); } }

	/* Barras */
	.bar { flex: 1; height: 6px; border-radius: 99px; background: rgba(255, 255, 255, 0.07); overflow: hidden; }
	.bar > span { display: block; height: 100%; border-radius: 99px; background: oklch(78% 0.17 160); }
	.bar > span.k { background: var(--cal); }
	.bar > span.p { background: oklch(72% 0.14 220); }
	.vs, .pts { display: flex; align-items: center; gap: 0.5rem; font-size: 0.72rem; margin-top: 0.3rem; }
	.vs .who { width: 3.2rem; font-weight: 700; }
	.vs b { width: 1.6rem; text-align: right; font-variant-numeric: tabular-nums; }
	.vs.other .bar > span { background: oklch(72% 0.15 var(--phue)); }
	.vs.other .who { color: oklch(80% 0.14 var(--phue)); }
	.pts .lbl { width: 4.2rem; font-weight: 700; }
	.pts .num { width: 2.8rem; text-align: right; color: var(--text-muted); font-variant-numeric: tabular-nums; }

	/* Semana */
	.week { display: grid; grid-template-columns: repeat(7, 1fr); gap: 0.3rem; }
	.day {
		display: flex; flex-direction: column; align-items: center; gap: 0.15rem;
		padding: 0.35rem 0; border-radius: 10px;
		border: 1px solid rgba(255, 255, 255, 0.08);
	}
	.dl { font-size: 0.6rem; color: var(--text-muted); font-weight: 700; }
	.ds { font-size: 0.78rem; font-weight: 800; font-variant-numeric: tabular-nums; }
	.day.good { background: oklch(75% 0.16 160 / 0.16); border-color: oklch(75% 0.16 160 / 0.4); }
	.day.low { background: oklch(78% 0.15 70 / 0.14); border-color: oklch(78% 0.15 70 / 0.35); }
	.day.none .ds { color: rgba(255, 255, 255, 0.3); }
	.day.cheat { background: oklch(72% 0.17 330 / 0.16); border-color: oklch(72% 0.17 330 / 0.4); }
	.legend { display: flex; justify-content: center; gap: 0.75rem; font-size: 0.62rem; color: var(--text-muted); }
	.legend i { display: inline-block; width: 8px; height: 8px; border-radius: 3px; margin-right: 0.25rem; vertical-align: -1px; }
	.legend i.good { background: oklch(75% 0.16 160); }
	.legend i.low { background: oklch(78% 0.15 70); }
	.legend i.none { background: rgba(255, 255, 255, 0.2); }

	/* Ranking */
	.rank-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; padding: 0.22rem 0.35rem; border-radius: 8px; }
	.rank-row .pos { width: 1.8rem; color: var(--text-muted); font-weight: 700; }
	.rank-row .rn { flex: 1; color: rgba(255, 255, 255, 0.45); }
	.rank-row .rp { font-weight: 800; font-variant-numeric: tabular-nums; }
	.rank-row.me { background: oklch(75% 0.16 160 / 0.15); }
	.rank-row.me .rn { color: oklch(85% 0.15 160); font-weight: 800; }

	/* Pareja vs amigo */
	.cmp-row { display: grid; grid-template-columns: 1fr 3.6rem 3.6rem; font-size: 0.72rem; padding: 0.2rem 0; align-items: center; }
	.cmp-row > :not(:first-child) { text-align: center; }
	.cmp-row.head b { font-size: 0.68rem; color: oklch(85% 0.15 160); }
	.yes { color: oklch(82% 0.17 160); font-weight: 800; }
	.no { color: rgba(255, 255, 255, 0.3); }
	.cmp-note { font-size: 0.65rem; color: var(--text-muted); margin-top: 0.3rem; }

	/* Círculos de receta */
	.seg { display: flex; gap: 0.3rem; }
	.seg span {
		flex: 1; display: flex; align-items: center; justify-content: center; gap: 0.3rem;
		font-size: 0.68rem; font-weight: 700; padding: 0.35rem 0;
		border-radius: 10px; color: var(--text-muted);
		border: 1px solid rgba(255, 255, 255, 0.1);
	}
	.seg span.on { color: oklch(85% 0.15 160); border-color: oklch(75% 0.15 160 / 0.5); background: oklch(75% 0.15 160 / 0.12); }

	/* Ajuste por ejercicio */
	.sum { display: flex; align-items: center; justify-content: center; gap: 0.45rem; font-weight: 800; font-variant-numeric: tabular-nums; }
	.sum span { display: flex; flex-direction: column; align-items: center; font-size: 0.95rem; }
	.sum small { font-size: 0.58rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; }
	.sum .burn { color: oklch(78% 0.17 30); }
	.sum .res { color: oklch(85% 0.15 160); }
	.sum b { color: var(--text-muted); }
	.mode-row { display: grid; grid-template-columns: 1fr 2.6rem 2.4rem 2.4rem 2.2rem; gap: 0.2rem; font-size: 0.68rem; padding: 0.15rem 0; font-variant-numeric: tabular-nums; }
	.mode-row .mode { font-weight: 700; }

	/* Despensa */
	.flow { display: flex; align-items: center; gap: 0.25rem; }
	.step {
		flex: 1; display: flex; flex-direction: column; align-items: center; gap: 0.1rem;
		padding: 0.45rem 0.2rem; border-radius: 10px; text-align: center;
		border: 1px solid rgba(255, 255, 255, 0.1);
		font-variant-numeric: tabular-nums;
	}
	.step small { font-size: 0.56rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.03em; }
	.step b { font-size: 0.75rem; }
	.step span { font-size: 0.72rem; color: oklch(85% 0.15 160); font-weight: 700; }
	.step.hl { background: oklch(75% 0.15 160 / 0.1); border-color: oklch(75% 0.15 160 / 0.4); }
	.to { color: var(--text-muted); font-size: 0.8rem; }

	/* Ánimo */
	.mood-row { display: flex; align-items: center; gap: 0.4rem; font-size: 0.72rem; padding: 0.2rem 0; }
	.mood-axis { width: 4.4rem; flex-shrink: 0; font-weight: 700; }
	.levels { flex: 1; display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.25rem; }
	.levels span {
		text-align: center; font-size: 0.62rem; font-weight: 700; padding: 0.25rem 0.1rem;
		border-radius: 8px; color: var(--text-muted); border: 1px solid rgba(255, 255, 255, 0.08);
		white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
	}
	.levels span.on { color: oklch(85% 0.15 160); border-color: oklch(75% 0.15 160 / 0.5); background: oklch(75% 0.15 160 / 0.12); }
</style>
