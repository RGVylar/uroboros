<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Goals, DaySummary } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	let goals: Goals | null = $state(null);
	let streak = $state(0);
	let totalDays = $state(0);  // days with any log in last 6 months
	let loading = $state(true);

	const ACHIEVEMENTS = [
		{ id:1, label:'Primer log', desc:'Primera comida registrada', hue:160 },
		{ id:2, label:'7 días', desc:'Racha de 7 días', hue:45 },
		{ id:3, label:'Recetas', desc:'3 recetas creadas', hue:295 },
		{ id:4, label:'Peso', desc:'Primer registro de peso', hue:220 },
		{ id:5, label:'Amigos', desc:'Primer amigo añadido', hue:330 },
		{ id:6, label:'30 días', desc:'Racha de 30 días', hue:25 },
	];

	async function load() {
		loading = true;
		try {
			// Load goals and streak from diary
			const [g, today] = await Promise.all([
				api.get<Goals>('/goals').catch(() => null),
				api.get<DaySummary>(`/diary/day?day=${new Date().toISOString().slice(0,10)}`).catch(() => null),
			]);
			goals = g;
			streak = (g as any)?.streak ?? 0;

			// Count active days in last 30
			const dates: string[] = [];
			const now = new Date();
			for (let i = 0; i < 30; i++) {
				const d = new Date(now);
				d.setDate(d.getDate() - i);
				dates.push(d.toISOString().slice(0, 10));
			}
			const results = await Promise.all(
				dates.map(date =>
					api.get<DaySummary>(`/diary/day?day=${date}`)
						.then(s => s.totals.calories > 0 ? 1 : 0)
						.catch(() => 0)
				)
			);
			totalDays = results.reduce((a, b) => a + b, 0);
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
</script>

<!-- ── Header ── -->
<div style="display:flex; align-items:center; gap:0.75rem; padding:0.25rem 0 1rem;">
	<button onclick={() => goto('/settings')} style="width:36px; height:36px; border-radius:50%; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center; color:#fff; cursor:pointer; font-family:inherit; font-size:1rem; flex-shrink:0;">←</button>
	<div style="flex:1; min-width:0;">
		<h1 style="font-size:1.875rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1; margin:0; font-family:'Lora','Georgia',serif;">Perfil</h1>
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.25rem;">Tu progreso y logros</div>
	</div>
</div>

<!-- ── Hero card ── -->
<div class="glass-card" style="margin-bottom:0.75rem; text-align:center; padding:1.375rem;">
	<!-- Avatar with streak badge -->
	<div style="position:relative; display:inline-block; margin-bottom:0.625rem;">
		<div style="width:92px; height:92px; border-radius:50%; background:linear-gradient(135deg, oklch(72% 0.18 {nameHue}), oklch(55% 0.16 {(nameHue+40) % 360})); display:flex; align-items:center; justify-content:center; font-size:2.25rem; font-weight:800; color:#fff; box-shadow:0 10px 32px oklch(72% 0.18 {nameHue} / 0.3), inset 0 2px 0 rgba(255,255,255,0.25);">{userInitial}</div>
		{#if streak > 0}
			<div style="position:absolute; bottom:0; right:-4px; padding:0.25rem 0.5rem; border-radius:99px; background:linear-gradient(135deg, oklch(80% 0.19 45), oklch(70% 0.2 30)); font-size:0.6875rem; font-weight:800; color:#fff; display:flex; align-items:center; gap:0.2rem; box-shadow:0 4px 14px oklch(75% 0.2 40 / 0.5);">🔥 {streak}</div>
		{/if}
	</div>

	<div style="font-size:1.25rem; font-weight:800; color:#fff; letter-spacing:-0.02em;">{userName}</div>
	<div style="font-size:0.75rem; color:rgba(255,255,255,0.5); margin-top:0.25rem;">{userEmail}</div>

	<!-- Stats grid -->
	{#if !loading}
		<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.625rem; margin-top:1.125rem;">
			{#each [
				{ l:'Racha', v: streak > 0 ? String(streak) : '—', u:'días', hue:45 },
				{ l:'Activo este mes', v: String(totalDays), u:'/30', hue:160 },
				{ l:'Meta kcal', v: goals?.kcal ? String(Math.round(goals.kcal)) : '—', u:'kcal', hue:220 },
				{ l:'Proteína meta', v: goals?.protein ? String(Math.round(goals.protein)) : '—', u:'g/día', hue:295 },
			] as s}
				<div style="padding:0.625rem 0.75rem; border-radius:14px; background:oklch(72% 0.16 {s.hue} / 0.1); border:1px solid oklch(72% 0.16 {s.hue} / 0.2); text-align:left;">
					<div style="font-size:0.5625rem; color:oklch(80% 0.14 {s.hue}); font-weight:700; letter-spacing:0.03em; text-transform:uppercase;">{s.l}</div>
					<div style="font-size:1.25rem; font-weight:800; color:#fff; margin-top:0.125rem; font-variant-numeric:tabular-nums;">{s.v}<span style="font-size:0.6875rem; color:rgba(255,255,255,0.4); font-weight:500; margin-left:0.1875rem;">{s.u}</span></div>
				</div>
			{/each}
		</div>
	{:else}
		<div style="padding:1.5rem 0; color:rgba(255,255,255,0.4); font-size:0.8rem;">Cargando...</div>
	{/if}
</div>

<!-- ── Achievements ── -->
<div style="font-size:0.6875rem; letter-spacing:0.075em; text-transform:uppercase; color:rgba(255,255,255,0.45); font-weight:700; margin:0 0.25rem 0.625rem;">Logros</div>
<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:0.625rem;">
	{#each ACHIEVEMENTS as a}
		{@const unlocked = a.id <= 4}
		<div style="padding:0.875rem 0.625rem; border-radius:16px; background:{unlocked ? `linear-gradient(135deg, oklch(72% 0.18 ${a.hue} / 0.2), rgba(255,255,255,0.04))` : 'rgba(255,255,255,0.03)'}; border:{unlocked ? `1px solid oklch(72% 0.18 ${a.hue} / 0.35)` : '1px dashed rgba(255,255,255,0.08)'}; text-align:center; opacity:{unlocked ? 1 : 0.4}; backdrop-filter:blur(12px);">
			<div style="width:36px; height:36px; border-radius:50%; background:{unlocked ? `linear-gradient(135deg, oklch(80% 0.17 ${a.hue}), oklch(60% 0.16 ${(a.hue+20) % 360}))` : 'rgba(255,255,255,0.06)'}; display:flex; align-items:center; justify-content:center; margin:0 auto 0.5rem; font-size:1rem;">{unlocked ? '🏆' : '🔒'}</div>
			<div style="font-size:0.6875rem; font-weight:700; color:#fff;">{a.label}</div>
			<div style="font-size:0.5625rem; color:rgba(255,255,255,0.5); margin-top:0.125rem; line-height:1.3;">{a.desc}</div>
		</div>
	{/each}
</div>

<!-- Bottom spacing -->
<div style="height:6rem;"></div>

<style>
	.glass-card {
		background: rgba(255,255,255,0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 20px;
		padding: 1rem;
	}
</style>
