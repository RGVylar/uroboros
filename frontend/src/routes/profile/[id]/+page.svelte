<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';

	if (!auth.isLoggedIn) goto('/login');

	interface FriendProfile {
		id: number;
		name: string;
		streak: number;
		active_days: number;
		recipe_count: number;
	}

	const ACHIEVEMENTS = [
		{ id: 1, label: 'Primer log',  desc: 'Primera comida registrada', hue: 160, check: (p: FriendProfile) => p.active_days >= 1 },
		{ id: 2, label: '7 días',      desc: 'Racha de 7 días',           hue: 45,  check: (p: FriendProfile) => p.streak >= 7 },
		{ id: 3, label: 'Recetas',     desc: '3 recetas creadas',          hue: 295, check: (p: FriendProfile) => p.recipe_count >= 3 },
		{ id: 5, label: 'Activo',      desc: '20 días activos este mes',   hue: 330, check: (p: FriendProfile) => p.active_days >= 20 },
		{ id: 6, label: '30 días',     desc: 'Racha de 30 días',           hue: 25,  check: (p: FriendProfile) => p.streak >= 30 },
	];

	let profile: FriendProfile | null = $state(null);
	let loading = $state(true);
	let error = $state('');

	const userId = $derived(Number(page.params.id));

	async function load() {
		loading = true;
		error = '';
		try {
			profile = await api.get<FriendProfile>(`/users/${userId}/profile`);
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'No se pudo cargar el perfil';
		} finally {
			loading = false;
		}
	}

	$effect(() => { if (userId) load(); });

	const nameHue = $derived((() => {
		if (!profile) return 220;
		let h = 0;
		for (const c of profile.name) h = (h * 31 + c.charCodeAt(0)) % 360;
		return h;
	})());
</script>

<!-- Header -->
<div style="display:flex; align-items:center; gap:0.75rem; padding:0.25rem 0 1rem;">
	<button onclick={() => history.back()} style="width:36px; height:36px; border-radius:50%; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center; color:#fff; cursor:pointer; font-family:inherit; font-size:1rem; flex-shrink:0;">←</button>
	<div style="flex:1; min-width:0;">
		<h1 style="font-size:1.875rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1; margin:0; font-family:'Lora','Georgia',serif;">Perfil</h1>
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.25rem;">Progreso de tu amig@</div>
	</div>
</div>

{#if loading}
	<div style="text-align:center; padding:4rem 0; color:rgba(255,255,255,0.35); font-size:0.85rem;">Cargando...</div>
{:else if error}
	<div style="text-align:center; padding:4rem 0; color:oklch(75% 0.2 25); font-size:0.85rem;">{error}</div>
{:else if profile}
	<!-- Hero card -->
	<div style="background:rgba(255,255,255,0.05); backdrop-filter:blur(24px); border:1px solid rgba(255,255,255,0.09); border-radius:20px; padding:1.375rem; margin-bottom:0.75rem; text-align:center;">
		<div style="width:92px; height:92px; border-radius:50%; background:linear-gradient(135deg, oklch(72% 0.18 {nameHue}), oklch(55% 0.16 {(nameHue+40) % 360})); display:flex; align-items:center; justify-content:center; font-size:2.25rem; font-weight:800; color:#fff; margin:0 auto 0.625rem; box-shadow:0 10px 32px oklch(72% 0.18 {nameHue} / 0.3);">
			{profile.name[0].toUpperCase()}
		</div>
		<div style="font-size:1.1875rem; font-weight:700; color:#fff;">{profile.name}</div>

		<div style="display:grid; grid-template-columns:1fr 1px 1fr; gap:0; margin-top:1rem; align-items:center;">
			<div style="text-align:center;">
				<div style="font-size:0.5625rem; font-weight:700; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.25rem;">Racha</div>
				<div style="font-size:1.5rem; font-weight:800; color:oklch(85% 0.17 45); letter-spacing:-0.03em;">
					{profile.streak > 0 ? `${profile.streak}🔥` : '—'}
				</div>
				<div style="font-size:0.5625rem; color:rgba(255,255,255,0.35); margin-top:0.125rem;">días</div>
			</div>
			<div style="width:1px; height:2.5rem; background:rgba(255,255,255,0.08);"></div>
			<div style="text-align:center;">
				<div style="font-size:0.5625rem; font-weight:700; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.25rem;">Activo este mes</div>
				<div style="font-size:1.5rem; font-weight:800; color:oklch(80% 0.17 220); letter-spacing:-0.03em;">{profile.active_days}</div>
				<div style="font-size:0.5625rem; color:rgba(255,255,255,0.35); margin-top:0.125rem;">/30 días</div>
			</div>
		</div>
	</div>

	<!-- Logros -->
	<div style="font-size:0.625rem; font-weight:700; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:0.1em; margin:1rem 0.25rem 0.625rem;">Logros</div>
	<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:0.5rem; margin-bottom:2rem;">
		{#each ACHIEVEMENTS as a}
			{@const unlocked = a.check(profile)}
			<div style="background:{unlocked ? `oklch(30% 0.1 {a.hue} / 0.4)` : 'rgba(255,255,255,0.03)'}; border:1px solid {unlocked ? `oklch(65% 0.18 {a.hue} / 0.4)` : 'rgba(255,255,255,0.07)'}; border-radius:16px; padding:0.875rem 0.5rem; text-align:center;">
				<div style="font-size:1.5rem; margin-bottom:0.375rem; filter:{unlocked ? 'none' : 'grayscale(1) opacity(0.3)'};">
					{#if a.id === 1}🥗{:else if a.id === 2}🔥{:else if a.id === 3}🍳{:else if a.id === 5}⚡{:else}🏆{/if}
				</div>
				<div style="font-size:0.6875rem; font-weight:700; color:{unlocked ? '#fff' : 'rgba(255,255,255,0.25)'};">{a.label}</div>
				<div style="font-size:0.5625rem; color:{unlocked ? `oklch(75% 0.12 {a.hue})` : 'rgba(255,255,255,0.2)'}; margin-top:0.2rem; line-height:1.3;">{a.desc}</div>
			</div>
		{/each}
	</div>
{/if}

<div style="height:5rem;"></div>
