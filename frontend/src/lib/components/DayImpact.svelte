<!--
  DayImpact.svelte
  "Cómo queda tu día si registras esto": para kcal y los tres macros, muestra
  lo que ya llevas (relleno sólido), lo que añadiría el alimento (segmento a
  rayas) y el objetivo. Si con el añadido se pasa del objetivo, el segmento y
  el número se tiñen de aviso.

  Uso:
    <DayImpact title="Tu día" totals={summary.totals} goals={effectiveGoals} added={{ calories, protein, carbs, fat }} />
-->
<script lang="ts">
	import type { DayTotals, Goals } from '$lib/types';
	import { t } from '$lib/i18n/index.svelte';

	interface Props {
		title: string;
		totals: DayTotals;
		goals: Goals;
		added: DayTotals;
		hue?: number | null;
	}
	let { title, totals, goals, added, hue = null }: Props = $props();

	type Row = { label: string; color: string; unit: string; current: number; add: number; goal: number };

	let rows = $derived<Row[]>([
		{ label: 'kcal',                    color: 'var(--cal)',  unit: '',  current: totals.calories, add: added.calories, goal: goals.kcal },
		{ label: t('diary.macroProtein'),   color: 'var(--prot)', unit: 'g', current: totals.protein,  add: added.protein,  goal: goals.protein },
		{ label: t('diary.macroCarbs'),     color: 'var(--carb)', unit: 'g', current: totals.carbs,    add: added.carbs,    goal: goals.carbs },
		{ label: t('diary.macroFat'),       color: 'var(--fat)',  unit: 'g', current: totals.fat,      add: added.fat,      goal: goals.fat },
	]);

	function pct(v: number, goal: number) {
		return goal > 0 ? Math.min((v / goal) * 100, 100) : 0;
	}
</script>

<div class="impact">
	<div class="impact-title">
		{#if hue !== null}<span class="dot" style="background: oklch(75% 0.18 {hue});"></span>{/if}
		{title}
	</div>
	{#each rows as r}
		{@const after = r.current + r.add}
		{@const over = r.goal > 0 && after > r.goal}
		{@const base = pct(r.current, r.goal)}
		{@const top = pct(after, r.goal)}
		<div class="row">
			<div class="top">
				<span class="lbl" style="color:{r.color};">{r.label}</span>
				<span class="val" class:over>
					<span class="now">{Math.round(r.current)}</span>
					<span class="arrow">→</span>
					<strong>{Math.round(after)}</strong>
					<span class="sep">/</span>
					<span class="goal">{Math.round(r.goal)}{r.unit}</span>
					{#if over}
						<span class="over-tag">+{Math.round(after - r.goal)}{r.unit}</span>
					{/if}
				</span>
			</div>
			<div class="track">
				<div class="fill" style="width:{base}%; background:{r.color};"></div>
				<div
					class="fill-add"
					class:over
					style="left:{base}%; width:{Math.max(top - base, 0)}%; --c:{r.color};"
				></div>
			</div>
		</div>
	{/each}
</div>

<style>
	.impact { display: flex; flex-direction: column; gap: 0.5rem; }
	.impact-title {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		font-size: 0.6875rem;
		letter-spacing: 0.1em;
		color: rgba(255,255,255,0.45);
		text-transform: uppercase;
		font-weight: 600;
		margin-bottom: 0.125rem;
	}
	.dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
	.row { width: 100%; }
	.top {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		margin-bottom: 0.25rem;
	}
	.lbl {
		font-size: 0.62rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		font-weight: 800;
	}
	.val {
		font-size: 0.72rem;
		color: var(--text-muted);
		font-variant-numeric: tabular-nums;
		display: flex;
		align-items: baseline;
		gap: 0.2rem;
	}
	.val .now { opacity: 0.7; }
	.val .arrow { opacity: 0.45; font-size: 0.65rem; }
	.val strong { color: var(--text); font-weight: 700; font-size: 0.8rem; }
	.val .sep { opacity: 0.5; }
	.val.over strong { color: oklch(82% 0.18 45); }
	.over-tag {
		margin-left: 0.2rem;
		padding: 0 0.35rem;
		border-radius: 99px;
		font-size: 0.6rem;
		font-weight: 700;
		color: oklch(85% 0.18 45);
		background: oklch(70% 0.18 45 / 0.18);
		border: 1px solid oklch(70% 0.18 45 / 0.35);
	}
	.track {
		position: relative;
		height: 6px;
		background: rgba(255,255,255,0.06);
		border-radius: 99px;
		overflow: hidden;
	}
	.fill {
		position: absolute;
		left: 0; top: 0; bottom: 0;
		border-radius: 99px;
		opacity: 0.85;
		transition: width 0.4s cubic-bezier(0.22, 1, 0.36, 1);
	}
	/* El tramo que añade este alimento: rayas del mismo color, para que se
	   distinga de lo que ya está registrado sin meter otro tono. */
	.fill-add {
		position: absolute;
		top: 0; bottom: 0;
		background: repeating-linear-gradient(
			-45deg,
			var(--c) 0 3px,
			color-mix(in oklch, var(--c) 45%, transparent) 3px 6px
		);
		box-shadow: 0 0 8px color-mix(in oklch, var(--c) 55%, transparent);
		transition: left 0.4s cubic-bezier(0.22, 1, 0.36, 1), width 0.4s cubic-bezier(0.22, 1, 0.36, 1);
	}
	.fill-add.over { --c: oklch(78% 0.2 45); }
</style>
