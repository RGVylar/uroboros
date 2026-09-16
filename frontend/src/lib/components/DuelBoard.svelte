<!--
  DuelBoard.svelte
  Marcador del Duelo semanal de adherencia.

  - compact  → marcador + tira de la semana con los puntos de cada día. Es la
               entrada que va en el perfil del amigo; debajo se pone el botón
               "Ver duelo completo".
  - !compact → todo: marcador + semana con leyenda y desglose del día que se
               toque + histórico de temporadas + insignias. Es lo que se
               muestra dentro del modal.

  Datos: recibe un `DuelData` (hoy de ejemplo, ver $lib/duel-example).
-->
<script lang="ts">
	import Avatar from './Avatar.svelte';
	import type { DuelData, DuelDay, DuelSide } from '$lib/duel-example';
	import { t, fmtDate } from '$lib/i18n/index.svelte';

	interface Props {
		duel: DuelData;
		compact?: boolean;
	}
	let { duel, compact = false }: Props = $props();

	const DOW = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];
	const DAY_GLYPH: Record<DuelDay, string> = {
		perfect: '🎯', hit: '✓', miss: '·', empty: '○', joker: '🍕', today: '◌',
	};

	// Día seleccionado para ver el desglose (solo en la vista completa).
	type Who = 'me' | 'them';
	let picked = $state<{ who: Who; idx: number } | null>(null);
	function pick(who: Who, idx: number) {
		// Solo los días puntuados tienen algo que contar.
		if (duel[who].scores[idx] == null) return;
		picked = picked?.who === who && picked.idx === idx ? null : { who, idx };
	}
	const pickedSide = $derived(picked ? duel[picked.who] : null);
	const pickedDetail = $derived(picked && pickedSide ? pickedSide.details[picked.idx] : null);

	// El que va por delante lidera (barra y % resaltados, coronita).
	let meLeads = $derived((duel.me.pct ?? 0) >= (duel.them.pct ?? 0) && (duel.me.pct ?? 0) > 0);

	// "Semana 29" (ISO) no le dice nada a nadie: mostramos las fechas reales.
	const monday = (() => {
		const now = new Date();
		const mon = new Date(now);
		mon.setDate(now.getDate() - ((now.getDay() + 6) % 7));
		return mon;
	})();
	const weekLabel = (() => {
		const sun = new Date(monday);
		sun.setDate(monday.getDate() + 6);
		const short = (d: Date) => fmtDate(d, { day: 'numeric', month: 'short' });
		const sameMonth = monday.getMonth() === sun.getMonth();
		return t('duel.weekRange', { from: sameMonth ? String(monday.getDate()) : short(monday), to: short(sun) });
	})();
	function dayName(idx: number): string {
		const d = new Date(monday);
		d.setDate(monday.getDate() + idx);
		const name = fmtDate(d, { weekday: 'long' });
		return name.charAt(0).toUpperCase() + name.slice(1);
	}
	const signed = (n: number) => (n > 0 ? `+${n}` : String(n));
</script>

<!-- ── Marcador ── -->
{#snippet scoreRow(side: DuelSide, lead: boolean)}
	<div class="row" class:lead>
		<div class="ava"><Avatar name={side.name} avatarId={side.avatarId} avatarPhoto={side.avatarPhoto} size={34} /></div>
		<div class="rowmid">
			<div class="name">{side.name}{#if lead}<span class="crown">👑</span>{/if}</div>
			<div class="bar"><span style="width:{side.pct ?? 0}%"></span></div>
		</div>
		<div class="pct">{side.pct === null ? '—' : `${side.pct}%`}</div>
	</div>
{/snippet}

{#snippet weekRow(side: DuelSide, who: Who)}
	<div class="who">{side.name}</div>
	{#each side.days as d, i}
		{@const score = side.scores[i]}
		{#if compact}
			<div class="dot {d}">
				<span class="glyph">{DAY_GLYPH[d]}</span>
				{#if score != null}<span class="pts">{score}</span>{/if}
			</div>
		{:else}
			<button
				type="button"
				class="dot {d}"
				class:picked={picked?.who === who && picked.idx === i}
				disabled={score == null}
				onclick={() => pick(who, i)}
			>
				<span class="glyph">{DAY_GLYPH[d]}</span>
				{#if score != null}<span class="pts">{score}</span>{/if}
			</button>
		{/if}
	{/each}
{/snippet}

<div class="board" class:compact>
	<div class="scorecard">
		<div class="season">
			<div class="season-title">⚔️ {weekLabel}</div>
			<div class="season-phase">{duel.phase}</div>
		</div>
		{@render scoreRow(duel.me, meLeads)}
		{@render scoreRow(duel.them, !meLeads)}
	</div>

	<!-- ── Semana día a día ── -->
	<div class="week">
		<div class="week-grid">
			{#if !compact}
				<div></div>
				{#each DOW as d}<div class="dow">{d}</div>{/each}
			{/if}
			{@render weekRow(duel.me, 'me')}
			{@render weekRow(duel.them, 'them')}
		</div>
		{#if !compact}
			<div class="legend">
				<i>{t('duel.perfect')}</i>
				<i>{t('duel.inGoal')}</i>
				<i>{t('duel.outOfRange')}</i>
				<i>{t('duel.notLogged')}</i>
				<i>{t('duel.joker')}</i>
			</div>

			<!-- ── Desglose del día tocado ── -->
			{#if picked && pickedSide}
				<div class="detail">
					<div class="detail-title">
						{t('duel.dayPoints', { day: dayName(picked.idx), name: pickedSide.name, score: pickedSide.scores[picked.idx] ?? 0 })}
					</div>
					{#if pickedDetail}
						<div class="detail-grid">
							<span class="dlabel">{t('duel.kcalRow')}</span>
							<div class="dbar"><span style="width:{(pickedDetail.kcalPts / 70) * 100}%"></span></div>
							<span class="dval">{t('duel.kcalDelta', { delta: signed(pickedDetail.kcal - pickedDetail.kcalGoal), pts: pickedDetail.kcalPts })}</span>
							<span class="dlabel">{t('duel.proteinRow')}</span>
							<div class="dbar"><span style="width:{(pickedDetail.proteinPts / 30) * 100}%"></span></div>
							<span class="dval">{t('duel.proteinOf', { protein: pickedDetail.protein, goal: pickedDetail.proteinGoal, pts: pickedDetail.proteinPts })}</span>
						</div>
					{:else}
						<div class="dval">{t('duel.dayEmpty')}</div>
					{/if}
				</div>
			{:else}
				<div class="hint">{t('duel.pointsHint')}</div>
			{/if}
		{/if}
	</div>

	{#if !compact}
		<!-- ── Histórico de temporadas ── -->
		<div class="hist">
			<div class="eyebrow">{t('duel.seasonsWon')}</div>
			<div class="tally">
				<div>
					<div class="n win">{duel.seasonsWon.me}</div>
					<div class="who2">{duel.me.name}</div>
				</div>
				<div class="dash">—</div>
				<div>
					<div class="n lose">{duel.seasonsWon.them}</div>
					<div class="who2">{duel.them.name}</div>
				</div>
			</div>
			<div class="weeks">
				{#each duel.history as h}
					<div class:me={h.winner === 'me'} class:them={h.winner === 'them'} class:current={h.winner === 'current'}>{h.week}</div>
				{/each}
			</div>
			{#if duel.streakWeeks > 1}
				<div class="streak">{t('duel.streakPre')} <b>{t('duel.streakWeeks', { count: duel.streakWeeks })}</b> 🔥</div>
			{/if}
		</div>

		<!-- ── Insignias ── -->
		<div class="eyebrow badges-label">{t('duel.badges')}</div>
		<div class="badges">
			{#each duel.badges as b}
				<div class="badge" class:on={b.unlocked}>
					<div class="ico">{b.icon}</div>
					<div class="lab">{b.label}</div>
					<div class="desc">{b.desc}</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.board { display: flex; flex-direction: column; gap: 0.75rem; }

	.scorecard, .week, .hist {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--r-lg);
		padding: 1.1rem;
	}
	.compact .scorecard, .compact .week {
		background: none;
		border: none;
		border-radius: 0;
		padding: 0;
	}
	.compact .week { margin-top: 0.5rem; }

	.season { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 1rem; }
	.compact .season { margin-bottom: 0.75rem; }
	.season-title { font-size: 1.15rem; font-weight: 400; letter-spacing: -0.03em; font-family: 'Lora', Georgia, serif; }
	.compact .season-title { font-size: 0.95rem; }
	.season-phase {
		font-size: 0.6rem; font-weight: 700; color: var(--cal);
		background: oklch(80% 0.17 45 / 0.14); border-radius: 99px; padding: 0.2rem 0.55rem;
	}

	.row { display: grid; grid-template-columns: 34px 1fr auto; align-items: center; gap: 0.6rem; margin-bottom: 0.7rem; }
	.row:last-child { margin-bottom: 0; }
	.ava { width: 34px; height: 34px; line-height: 0; }
	.name { font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.3rem; display: flex; align-items: center; gap: 0.3rem; }
	.row.lead .name { color: var(--text); font-weight: 700; }
	.crown { font-size: 0.7rem; }
	.bar { height: 8px; border-radius: 99px; background: rgba(255,255,255,0.07); overflow: hidden; }
	.bar span { display: block; height: 100%; border-radius: 99px; background: rgba(255,255,255,0.22); transition: width 0.5s cubic-bezier(0.22,1,0.36,1); }
	.row.lead .bar span {
		background: linear-gradient(90deg, var(--primary-dim), var(--primary));
		box-shadow: 0 0 14px var(--primary-glow);
	}
	.pct { font-size: 1.25rem; font-weight: 800; letter-spacing: -0.03em; color: var(--text-faint); min-width: 2.6rem; text-align: right; font-variant-numeric: tabular-nums; }
	.row.lead .pct { color: var(--primary); }

	.week-grid { display: grid; grid-template-columns: 2.4rem repeat(7, 1fr); gap: 0.35rem; align-items: center; }
	.dow { text-align: center; font-size: 0.55rem; font-weight: 700; color: var(--text-faint); text-transform: uppercase; }
	.who { font-size: 0.62rem; color: var(--text-muted); }
	.dot {
		border-radius: 0.55rem; display: flex; flex-direction: column; align-items: center; justify-content: center;
		gap: 0.05rem; padding: 0.3rem 0; min-height: 2.4rem; font: inherit;
		font-size: 0.68rem; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); color: var(--text-muted);
	}
	.compact .dot { min-height: 2rem; padding: 0.2rem 0; }
	button.dot { cursor: pointer; transition: transform 0.15s ease, border-color 0.15s ease; }
	button.dot:disabled { cursor: default; }
	button.dot:not(:disabled):active { transform: scale(0.94); }
	.dot.picked { border-color: var(--primary); box-shadow: 0 0 0 2px var(--primary-glow); }
	.glyph { line-height: 1; }
	.pts { font-size: 0.58rem; font-weight: 700; line-height: 1; font-variant-numeric: tabular-nums; opacity: 0.85; }
	.compact .pts { font-size: 0.52rem; }
	.dot.perfect { background: oklch(70% 0.18 165 / 0.34); border-color: oklch(80% 0.18 165 / 0.7); color: oklch(92% 0.16 160); font-weight: 700; }
	.dot.hit { background: oklch(70% 0.18 165 / 0.18); border-color: oklch(75% 0.18 165 / 0.4); color: oklch(88% 0.16 160); font-weight: 700; }
	.dot.miss { color: var(--text-faint); }
	.dot.empty { border-style: dashed; color: rgba(255,255,255,0.18); }
	.dot.joker { background: oklch(70% 0.17 45 / 0.16); border-color: oklch(75% 0.17 45 / 0.4); }
	.dot.today { border-color: rgba(255,255,255,0.3); box-shadow: 0 0 0 2px rgba(255,255,255,0.06); }
	.legend { display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 0.75rem; font-size: 0.6rem; color: var(--text-faint); }
	.legend i { font-style: normal; }
	.hint { margin-top: 0.75rem; font-size: 0.62rem; color: var(--text-faint); line-height: 1.4; }

	.detail { margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid rgba(255,255,255,0.07); }
	.detail-title { font-size: 0.68rem; color: var(--text-muted); margin-bottom: 0.5rem; }
	.detail-grid { display: grid; grid-template-columns: auto 1fr auto; gap: 0.45rem 0.6rem; align-items: center; font-size: 0.68rem; }
	.dlabel { color: var(--text-muted); }
	.dval { color: var(--text-muted); font-variant-numeric: tabular-nums; white-space: nowrap; }
	.dbar { height: 6px; border-radius: 99px; background: rgba(255,255,255,0.07); overflow: hidden; }
	.dbar span { display: block; height: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--primary-dim), var(--primary)); transition: width 0.4s cubic-bezier(0.22,1,0.36,1); }

	.eyebrow { font-size: 0.6rem; font-weight: 700; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.1em; }
	.tally { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; text-align: center; margin-top: 0.9rem; }
	.tally .n { font-size: 2rem; font-weight: 800; letter-spacing: -0.04em; }
	.tally .n.win { color: var(--primary); }
	.tally .n.lose { color: var(--text-faint); }
	.who2 { font-size: 0.7rem; color: var(--text-muted); margin-top: 0.1rem; }
	.dash { font-size: 1.1rem; color: rgba(255,255,255,0.2); padding: 0 0.5rem; }
	.weeks { display: flex; gap: 0.25rem; justify-content: center; margin-top: 0.9rem; }
	.weeks div {
		width: 1.4rem; height: 1.4rem; border-radius: 0.45rem; font-size: 0.55rem;
		display: flex; align-items: center; justify-content: center;
		background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); color: var(--text-muted);
	}
	.weeks div.me { background: oklch(70% 0.18 165 / 0.25); border-color: oklch(75% 0.18 165 / 0.4); color: var(--text); }
	.weeks div.them { background: oklch(70% 0.14 300 / 0.25); border-color: oklch(75% 0.14 300 / 0.4); color: var(--text); }
	.weeks div.current { border-style: dashed; }
	.streak { margin-top: 0.9rem; padding-top: 0.85rem; border-top: 1px solid rgba(255,255,255,0.07); font-size: 0.75rem; color: var(--text-muted); text-align: center; }
	.streak b { color: var(--text); }

	.badges-label { margin: 0.4rem 0.25rem 0; }
	.badges { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; }
	.badge { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: var(--r-md); padding: 0.85rem 0.5rem; text-align: center; }
	.badge .ico { font-size: 1.4rem; filter: grayscale(1) opacity(0.3); }
	.badge .lab { font-size: 0.68rem; font-weight: 700; color: rgba(255,255,255,0.25); margin-top: 0.35rem; }
	.badge .desc { font-size: 0.55rem; color: rgba(255,255,255,0.2); margin-top: 0.15rem; line-height: 1.3; }
	.badge.on { background: oklch(30% 0.1 165 / 0.4); border-color: oklch(65% 0.18 165 / 0.4); }
	.badge.on .ico { filter: none; }
	.badge.on .lab { color: var(--text); }
	.badge.on .desc { color: oklch(75% 0.12 165); }
</style>
