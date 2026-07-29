<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import { Avatar, DuelBoard, Modal } from '$lib/components';
	import type { DuelData } from '$lib/duel-example';
	import { t } from '$lib/i18n/index.svelte';

	if (!auth.isLoggedIn) goto('/login');

	interface FriendProfile {
		id: number;
		name: string;
		avatar_id: string | null;
		avatar_photo: string | null;
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

	let profile = $state<FriendProfile | null>(null);
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

	// Duelo semanal de adherencia (datos reales del backend, gated por opt-in doble).
	interface DuelApi {
		active: boolean;
		my_opt_in: boolean;
		their_opt_in: boolean;
		friend_name: string;
		week?: number;
		phase?: string;
		me?: { name: string; avatar_id: string | null; avatar_photo: string | null; pct: number | null; days: string[] };
		them?: { name: string; avatar_id: string | null; avatar_photo: string | null; pct: number | null; days: string[] };
		seasons_won?: { me: number; them: number };
		history?: { week: number; winner: string }[];
		streak_weeks?: number;
		badges?: { icon: string; label: string; desc: string; unlocked: boolean }[];
	}

	let duelApi = $state<DuelApi | null>(null);
	async function loadDuel() {
		try {
			duelApi = await api.get<DuelApi>(`/duel/${userId}`);
		} catch {
			duelApi = null;
		}
	}
	$effect(() => { if (userId) loadDuel(); });

	// Map the snake_case API into the DuelData shape DuelBoard renders.
	const duel = $derived<DuelData | null>(
		duelApi?.active && duelApi.me && duelApi.them
			? {
				week: duelApi.week ?? 0,
				phase: duelApi.phase ?? '',
				me: { name: duelApi.me.name, avatarId: duelApi.me.avatar_id, avatarPhoto: duelApi.me.avatar_photo, pct: duelApi.me.pct, days: duelApi.me.days as DuelData['me']['days'] },
				them: { name: duelApi.them.name, avatarId: duelApi.them.avatar_id, avatarPhoto: duelApi.them.avatar_photo, pct: duelApi.them.pct, days: duelApi.them.days as DuelData['them']['days'] },
				seasonsWon: duelApi.seasons_won ?? { me: 0, them: 0 },
				history: (duelApi.history ?? []) as DuelData['history'],
				streakWeeks: duelApi.streak_weeks ?? 0,
				badges: duelApi.badges ?? [],
			}
			: null,
	);
	let showDuel = $state(false);
</script>

<!-- Header -->
<div style="display:flex; align-items:center; gap:0.75rem; padding:0.25rem 0 1rem;">
	<button onclick={() => history.back()} style="width:36px; height:36px; border-radius:50%; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center; color:#fff; cursor:pointer; font-family:inherit; font-size:1rem; flex-shrink:0;">←</button>
	<div style="flex:1; min-width:0;">
		<h1 style="font-size:1.875rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1; margin:0; font-family:'Lora','Georgia',serif;">{t('friendProfile.title')}</h1>
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.25rem;">{t('friendProfile.sub')}</div>
	</div>
</div>

{#if loading}
	<div style="text-align:center; padding:4rem 0; color:rgba(255,255,255,0.35); font-size:0.85rem;">{t('friendProfile.loading')}</div>
{:else if error}
	<div style="text-align:center; padding:4rem 0; color:oklch(75% 0.2 25); font-size:0.85rem;">{error}</div>
{:else if profile}
	<!-- Hero card -->
	<div style="background:rgba(255,255,255,0.05); backdrop-filter:blur(24px); border:1px solid rgba(255,255,255,0.09); border-radius:20px; padding:1.375rem; margin-bottom:0.75rem; text-align:center;">
		<div style="width:92px; height:92px; margin:0 auto 0.625rem; border-radius:50%; box-shadow:0 10px 32px oklch(72% 0.18 {nameHue} / 0.3); line-height:0;">
			<Avatar name={profile.name} avatarId={profile.avatar_id} avatarPhoto={profile.avatar_photo} size={92} />
		</div>
		<div style="font-size:1.1875rem; font-weight:700; color:#fff;">{profile.name}</div>

		<div style="display:grid; grid-template-columns:1fr 1px 1fr; gap:0; margin-top:1rem; align-items:center;">
			<div style="text-align:center;">
				<div style="font-size:0.5625rem; font-weight:700; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.25rem;">{t('friendProfile.streak')}</div>
				<div style="font-size:1.5rem; font-weight:800; color:oklch(85% 0.17 45); letter-spacing:-0.03em;">
					{profile.streak > 0 ? `${profile.streak}🔥` : '—'}
				</div>
				<div style="font-size:0.5625rem; color:rgba(255,255,255,0.35); margin-top:0.125rem;">{t('friendProfile.days')}</div>
			</div>
			<div style="width:1px; height:2.5rem; background:rgba(255,255,255,0.08);"></div>
			<div style="text-align:center;">
				<div style="font-size:0.5625rem; font-weight:700; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.25rem;">{t('friendProfile.activeMonth')}</div>
				<div style="font-size:1.5rem; font-weight:800; color:oklch(80% 0.17 220); letter-spacing:-0.03em;">{profile.active_days}</div>
				<div style="font-size:0.5625rem; color:rgba(255,255,255,0.35); margin-top:0.125rem;">{t('friendProfile.of30')}</div>
			</div>
		</div>
	</div>

	<!-- Duelo semanal -->
	{#if duel}
		<div style="background:rgba(255,255,255,0.05); backdrop-filter:blur(24px); border:1px solid rgba(255,255,255,0.09); border-radius:20px; padding:1.375rem; margin-bottom:0.75rem;">
			<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:1rem;">
				<div style="font-size:0.625rem; font-weight:700; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:0.1em;">{t('friendProfile.duelWeek')}</div>
				<div style="font-size:0.625rem; color:rgba(255,255,255,0.35);">Tú {duel.seasonsWon.me} — {profile.name} {duel.seasonsWon.them}</div>
			</div>
			<DuelBoard {duel} compact />
			<button
				onclick={() => (showDuel = true)}
				style="width:100%; margin-top:1.125rem; padding:0.75rem; border-radius:12px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); color:#fff; font-family:inherit; font-size:0.8125rem; font-weight:600; cursor:pointer;"
			>
				Ver duelo completo →
			</button>
		</div>
	{:else if duelApi && !duelApi.active}
		<!-- Duelo no activo: hace falta que ambos lo activen (en Amigos). -->
		<button
			onclick={() => goto('/friends')}
			style="width:100%; text-align:left; background:rgba(255,255,255,0.05); backdrop-filter:blur(24px); border:1px solid rgba(255,255,255,0.09); border-radius:20px; padding:1.375rem; margin-bottom:0.75rem; color:#fff; font-family:inherit; cursor:pointer;"
		>
			<div style="font-size:0.625rem; font-weight:700; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.5rem;">{t('friendProfile.duelTitle')}</div>
			<div style="font-size:0.875rem; font-weight:600;">
				{#if duelApi.my_opt_in && !duelApi.their_opt_in}
					Esperando a que {profile.name} lo active
				{:else if !duelApi.my_opt_in && duelApi.their_opt_in}
					{profile.name} quiere competir · <span style="color:oklch(85% 0.17 160);">{t('friendProfile.enableIt')}</span>
				{:else}
					Compite en adherencia con {profile.name}
				{/if}
			</div>
			<div style="font-size:0.6875rem; color:rgba(255,255,255,0.4); margin-top:0.25rem;">{t('friendProfile.enableInFriends')}</div>
		</button>
	{/if}

	<!-- Logros -->
	<div style="font-size:0.625rem; font-weight:700; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:0.1em; margin:1rem 0.25rem 0.625rem;">{t('friendProfile.achievements')}</div>
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

{#if showDuel && duel}
	<Modal onClose={() => (showDuel = false)} title={t('friendProfile.duelTitle')} subtitle={t('friendProfile.duelModalSub')}>
		<DuelBoard {duel} />
	</Modal>
{/if}
