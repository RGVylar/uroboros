<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Goals } from '$lib/types';
	import Aurora from '$lib/components/uro/Aurora.svelte';
	import ScreenHeader from '$lib/components/uro/ScreenHeader.svelte';
	import GlassCard from '$lib/components/uro/GlassCard.svelte';

	if (!auth.isLoggedIn) goto('/login');

	let goals: Goals | null = $state(null);
	let streak = $state(0);
	let totalDays = $state(0);
	let loading = $state(true);

	const ACHIEVEMENTS = [
		{ id: 1, label: 'Primer log',  desc: 'Primera comida registrada', hue: 160 },
		{ id: 2, label: '7 días',      desc: 'Racha de 7 días',           hue:  45 },
		{ id: 3, label: 'Recetas',     desc: '3 recetas creadas',         hue: 295 },
		{ id: 4, label: 'Peso',        desc: 'Primer registro de peso',   hue: 220 },
		{ id: 5, label: 'Amigos',      desc: 'Primer amigo añadido',      hue: 330 },
		{ id: 6, label: '30 días',     desc: 'Racha de 30 días',          hue:  25 },
	];

	async function load() {
		loading = true;
		try {
			const [g, streakData] = await Promise.all([
				api.get<Goals>('/goals').catch(() => null),
				api.get<{ streak: number; active_days: number }>('/diary/streak').catch(() => ({ streak: 0, active_days: 0 })),
			]);
			goals = g;
			streak = streakData.streak ?? 0;
			totalDays = streakData.active_days ?? 0;
		} finally {
			loading = false;
		}
	}

	$effect(() => { load(); });

	const userName = $derived(auth.user?.name ?? 'Usuario');
	const userEmail = $derived(auth.user?.email ?? '');
	const userInitial = $derived(userName[0]?.toUpperCase() ?? 'U');
	const nameHue = $derived((() => {
		let h = 0;
		for (const c of userName) h = (h * 31 + c.charCodeAt(0)) % 360;
		return h;
	})());

	const stats = $derived([
		{ l: 'Racha',           v: streak > 0 ? String(streak) : '—',                       u: 'días',   hue:  45 },
		{ l: 'Activo este mes', v: String(totalDays),                                       u: '/30',    hue: 160 },
		{ l: 'Meta kcal',       v: goals?.kcal    ? String(Math.round(goals.kcal))    : '—', u: 'kcal',   hue: 220 },
		{ l: 'Proteína meta',   v: goals?.protein ? String(Math.round(goals.protein)) : '—', u: 'g/día',  hue: 295 },
	]);
</script>

<Aurora />

<div class="page">
	<ScreenHeader
		title="Perfil"
		sub="Tu progreso y logros"
		onBack={() => goto('/settings')}
	/>

	<!-- Hero -->
	<GlassCard padding={22}>
		<div class="hero">
			<div class="avatar-wrap">
				<div class="avatar" style:--hue={nameHue}>{userInitial}</div>
				{#if streak > 0}
					<div class="streak-badge">🔥 {streak}</div>
				{/if}
			</div>
			<div class="name">{userName}</div>
			<div class="email">{userEmail}</div>

			{#if !loading}
				<div class="stats-grid">
					{#each stats as s}
						<div class="stat" style:--hue={s.hue}>
							<div class="stat-label">{s.l}</div>
							<div class="stat-value">{s.v}<span class="stat-unit">{s.u}</span></div>
						</div>
					{/each}
				</div>
			{:else}
				<div class="loading">Cargando…</div>
			{/if}
		</div>
	</GlassCard>

	<!-- Achievements -->
	<div class="section-title">Logros</div>
	<div class="ach-grid">
		{#each ACHIEVEMENTS as a}
			{@const unlocked = a.id <= 4}
			<div class="ach" class:unlocked style:--hue={a.hue}>
				<div class="ach-icon">{unlocked ? '🏆' : '🔒'}</div>
				<div class="ach-label">{a.label}</div>
				<div class="ach-desc">{a.desc}</div>
			</div>
		{/each}
	</div>

	<div class="spacer"></div>
</div>

<style>
	.page {
		position: relative;
		z-index: 1;
		max-width: 560px;
		margin: 0 auto;
		padding: 8px 16px 120px;
	}

	/* Hero */
	.hero { text-align: center; }
	.avatar-wrap {
		position: relative;
		display: inline-block;
		margin-bottom: 10px;
	}
	.avatar {
		width: 92px; height: 92px; border-radius: 50%;
		background: linear-gradient(135deg, oklch(72% 0.18 var(--hue)), oklch(55% 0.16 calc(var(--hue) + 40)));
		display: flex; align-items: center; justify-content: center;
		font-size: 36px; font-weight: 800; color: #fff;
		box-shadow:
			0 10px 32px oklch(72% 0.18 var(--hue) / 0.3),
			inset 0 2px 0 rgba(255, 255, 255, 0.25);
	}
	.streak-badge {
		position: absolute; bottom: 0; right: -4px;
		padding: 4px 10px; border-radius: 99px;
		background: linear-gradient(135deg, oklch(80% 0.19 45), oklch(70% 0.2 30));
		font-size: 11px; font-weight: 800; color: #fff;
		display: flex; align-items: center; gap: 3px;
		box-shadow: 0 4px 14px oklch(75% 0.2 40 / 0.5);
	}
	.name {
		font-size: 20px; font-weight: 800; color: #fff;
		letter-spacing: -0.3px;
	}
	.email {
		font-size: 12px; color: rgba(255, 255, 255, 0.5);
		margin-top: 4px;
	}

	.stats-grid {
		display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
		margin-top: 18px;
	}
	.stat {
		padding: 10px 12px; border-radius: 14px;
		background: oklch(72% 0.16 var(--hue) / 0.1);
		border: 1px solid oklch(72% 0.16 var(--hue) / 0.2);
		text-align: left;
	}
	.stat-label {
		font-size: 10px;
		color: oklch(80% 0.14 var(--hue));
		font-weight: 700;
		letter-spacing: 0.3px;
		text-transform: uppercase;
	}
	.stat-value {
		font-size: 20px; font-weight: 800; color: #fff;
		margin-top: 2px;
		font-variant-numeric: tabular-nums;
	}
	.stat-unit {
		font-size: 11px;
		color: rgba(255, 255, 255, 0.4);
		font-weight: 500;
		margin-left: 3px;
	}

	.loading {
		padding: 24px 0;
		color: rgba(255, 255, 255, 0.4);
		font-size: 13px;
	}

	/* Achievements */
	.section-title {
		font-size: 11px;
		letter-spacing: 1.2px;
		text-transform: uppercase;
		color: rgba(255, 255, 255, 0.5);
		font-weight: 700;
		margin: 18px 4px 10px;
	}
	.ach-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 10px;
	}
	.ach {
		padding: 14px 10px;
		border-radius: 16px;
		background: rgba(255, 255, 255, 0.03);
		border: 1px dashed rgba(255, 255, 255, 0.08);
		text-align: center;
		opacity: 0.4;
		backdrop-filter: blur(12px);
	}
	.ach.unlocked {
		background: linear-gradient(135deg, oklch(72% 0.18 var(--hue) / 0.2), rgba(255, 255, 255, 0.04));
		border: 1px solid oklch(72% 0.18 var(--hue) / 0.35);
		opacity: 1;
	}
	.ach-icon {
		width: 36px; height: 36px; border-radius: 50%;
		margin: 0 auto 8px;
		display: flex; align-items: center; justify-content: center;
		background: rgba(255, 255, 255, 0.06);
		font-size: 16px;
	}
	.ach.unlocked .ach-icon {
		background: linear-gradient(135deg, oklch(80% 0.17 var(--hue)), oklch(60% 0.16 calc(var(--hue) + 20)));
	}
	.ach-label { font-size: 11px; font-weight: 700; color: #fff; }
	.ach-desc {
		font-size: 9px;
		color: rgba(255, 255, 255, 0.5);
		margin-top: 2px;
		line-height: 1.3;
	}

	.spacer { height: 60px; }
</style>
