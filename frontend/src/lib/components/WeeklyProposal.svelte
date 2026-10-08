<!--
  WeeklyProposal.svelte — revisión semanal de objetivos en el diario.

  El servidor calcula el gasto real (lo comido frente a lo que dice la
  báscula, últimas 3 semanas) y propone calorías nuevas. Sale hasta que se
  responde (Aplicar / Ahora no); la semana siguiente vuelve si hay algo que
  proponer. Sin PRO solo se avisa de que hay propuesta.
-->
<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import InfoTip from '$lib/components/InfoTip.svelte';
	import { api } from '$lib/api';
	import { toast } from '$lib/stores/toast.svelte';
	import { tips } from '$lib/stores/tips.svelte';
	import { t, i18n } from '$lib/i18n/index.svelte';
	import type { GoalProposal, Goals, Objective } from '$lib/types';

	let { onapplied }: { onapplied: (g: Goals) => void } = $props();

	let p = $state<GoalProposal | null>(null);
	let busy = $state(false);

	async function load() {
		p = await api.get<GoalProposal>('/goals/proposal').catch(() => null);
	}
	$effect(() => { load(); });

	let visible = $derived(
		!!p && (p.locked ? p.status === 'proposal' : p.status === 'proposal' || p.status === 'need_objective')
	);
	$effect(() => { if (visible && !p?.locked) tips.request('weekly_proposal'); });

	async function answer(action: 'apply' | 'dismiss') {
		busy = true;
		try {
			const g = await api.post<Goals>('/goals/proposal', { action });
			if (action === 'apply') {
				onapplied(g);
				toast.success(t('proposal.applied'));
			}
			p = null;
		} catch {
			toast.error(t('proposal.err'));
		} finally {
			busy = false;
		}
	}

	async function setObjective(objective: Objective) {
		busy = true;
		try {
			await api.patch('/goals/profile', { objective });
			await load();
		} catch {
			toast.error(t('proposal.err'));
		} finally {
			busy = false;
		}
	}

	function num(n: number | null | undefined, decimals = 0): string {
		if (n == null) return '—';
		return n.toLocaleString(i18n.locale, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
	}
	function signed(n: number): string {
		return `${n > 0 ? '+' : n < 0 ? '−' : ''}${num(Math.abs(n), 2)}`;
	}

	const OBJECTIVES: { key: Objective; label: Parameters<typeof t>[0]; icon: 'trendDown' | 'weight' | 'exercise' }[] = [
		{ key: 'lose', label: 'onb.objLose', icon: 'trendDown' },
		{ key: 'maintain', label: 'onb.objMaintain', icon: 'weight' },
		{ key: 'gain', label: 'onb.objGain', icon: 'exercise' },
	];
</script>

{#if visible && p}
	<div class="proposal">
		<div class="eyebrow"><Icon name="trend" /> {t('proposal.eyebrow')}{#if !p.locked}<InfoTip id="weekly_proposal" />{/if}</div>

		{#if p.locked}
			<div class="title">{t('proposal.lockedTitle')} <span class="pro">PRO</span></div>
			<p class="body">{t('proposal.lockedBody')}</p>
			<div class="actions">
				<a class="btn-main" href="/premium">{t('proposal.seePro')}</a>
				<button class="btn-ghost" onclick={() => answer('dismiss')} disabled={busy}>{t('proposal.notNow')}</button>
			</div>

		{:else if p.status === 'need_objective'}
			<div class="title">{t('proposal.objectiveTitle')}</div>
			<p class="body">{t('proposal.objectiveBody', { tdee: num(p.tdee) })}</p>
			<div class="objectives">
				{#each OBJECTIVES as o (o.key)}
					<button class="obj" onclick={() => setObjective(o.key)} disabled={busy}>
						<Icon name={o.icon} /> {t(o.label)}
					</button>
				{/each}
			</div>
			<button class="btn-ghost solo" onclick={() => answer('dismiss')} disabled={busy}>{t('proposal.notNow')}</button>

		{:else if p.proposed && p.current}
			<div class="title">{t('proposal.title')}</div>
			<div class="change">{t('proposal.change', { from: num(p.current.kcal), to: num(p.proposed.kcal) })}</div>
			<div class="macros">{t('proposal.macros', { p: p.proposed.protein, c: p.proposed.carbs, f: p.proposed.fat })}</div>
			<p class="body">{t('proposal.body', { intake: num(p.avg_intake), rate: signed(p.kg_per_week ?? 0), tdee: num(p.tdee) })}</p>
			<div class="actions">
				<button class="btn-main" onclick={() => answer('apply')} disabled={busy}>{t('proposal.apply')}</button>
				<button class="btn-ghost" onclick={() => answer('dismiss')} disabled={busy}>{t('proposal.notNow')}</button>
			</div>
		{/if}
	</div>
{/if}

<style>
	.proposal {
		--hue: 200;
		margin-bottom: 0.75rem;
		padding: 1rem 1rem 0.875rem;
		border-radius: 18px;
		background: linear-gradient(135deg, oklch(70% 0.12 var(--hue) / 0.16), oklch(55% 0.1 var(--hue) / 0.06));
		border: 1px solid oklch(75% 0.12 var(--hue) / 0.28);
	}
	.eyebrow {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		font-size: 0.6875rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: oklch(85% 0.1 var(--hue));
		margin-bottom: 0.375rem;
	}
	.title {
		font-size: 1rem;
		font-weight: 700;
		color: #fff;
		margin-bottom: 0.25rem;
	}
	.pro {
		font-size: 0.625rem;
		font-weight: 800;
		padding: 0.125rem 0.375rem;
		border-radius: 6px;
		background: oklch(80% 0.15 85 / 0.2);
		color: oklch(88% 0.14 85);
		vertical-align: middle;
	}
	.change {
		font-size: 1.375rem;
		font-weight: 700;
		color: oklch(90% 0.12 var(--hue));
		letter-spacing: -0.02em;
	}
	.macros {
		font-size: 0.75rem;
		color: rgba(255, 255, 255, 0.65);
		margin: 0.125rem 0 0.5rem;
	}
	.body {
		font-size: 0.75rem;
		line-height: 1.5;
		color: rgba(255, 255, 255, 0.6);
		margin: 0 0 0.75rem;
	}
	.actions {
		display: flex;
		gap: 0.5rem;
	}
	.btn-main,
	.btn-ghost {
		flex: 1;
		padding: 0.625rem 0.75rem;
		border-radius: 12px;
		font-size: 0.8125rem;
		font-weight: 700;
		text-align: center;
		text-decoration: none;
		cursor: pointer;
		font-family: inherit;
	}
	.btn-main {
		border: none;
		background: oklch(80% 0.13 var(--hue));
		color: #06070a;
	}
	.btn-ghost {
		border: 1px solid rgba(255, 255, 255, 0.12);
		background: transparent;
		color: rgba(255, 255, 255, 0.75);
		box-shadow: none;
	}
	.btn-ghost.solo {
		width: 100%;
		margin-top: 0.5rem;
	}
	.objectives {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}
	.obj {
		flex: 1;
		min-width: 6.5rem;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.375rem;
		padding: 0.5625rem 0.625rem;
		border-radius: 12px;
		border: 1px solid oklch(75% 0.12 var(--hue) / 0.35);
		background: oklch(70% 0.12 var(--hue) / 0.12);
		color: #fff;
		font-size: 0.8125rem;
		font-weight: 600;
		font-family: inherit;
		cursor: pointer;
		box-shadow: none;
	}
	button:disabled {
		opacity: 0.6;
		cursor: default;
	}
</style>
