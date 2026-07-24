<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Goals, Recipe, WeightLog, Friendship } from '$lib/types';
	import Aurora from '$lib/components/uro/Aurora.svelte';
	import ScreenHeader from '$lib/components/uro/ScreenHeader.svelte';
	import GlassCard from '$lib/components/uro/GlassCard.svelte';
	import { Avatar, Modal } from '$lib/components';
	import { AVATARS, IDENTITY_HUES, identityColor } from '$lib/avatars';
	import { t, avatarLabel } from '$lib/i18n/index.svelte';
	import { toast } from '$lib/stores/toast.svelte';

	if (!auth.isLoggedIn) goto('/login');

	let showAvatarPicker = $state(false);
	let savingAvatar = $state(false);
	let savingColor = $state(false);

	async function pickAvatar(id: string | null) {
		if (savingAvatar) return;
		savingAvatar = true;
		try {
			await api.patch('/users/me/avatar', { avatar_id: id });
			auth.updateUser({ avatar_id: id });
			showAvatarPicker = false;
		} catch {
			toast.error(t('profile.errAvatar'));
		} finally {
			savingAvatar = false;
		}
	}

	async function pickColor(hue: number | null) {
		if (savingColor) return;
		savingColor = true;
		try {
			await api.patch('/users/me/identity-color', { identity_hue: hue });
			auth.updateUser({ identity_hue: hue });
		} catch {
			toast.error(t('profile.errColour'));
		} finally {
			savingColor = false;
		}
	}

	let goals: Goals | null = $state(null);
	let streak = $state(0);
	let totalDays = $state(0);
	let ownRecipes = $state(0);
	let weightLogs = $state(0);
	let friendCount = $state(0);
	let loading = $state(true);

	// Los logros se evalúan en cliente con los datos disponibles (no se
	// persisten en el servidor), así que las condiciones son aproximadas
	// pero deben reflejar el progreso real del usuario.
	let ACHIEVEMENTS = $derived([
		{ id: 1, label: t('profile.achFirstLog'), desc: t('profile.achFirstLogDesc'), hue: 160, unlocked: () => totalDays >= 1 || streak >= 1 },
		{ id: 2, label: t('profile.ach7'),        desc: t('profile.ach7Desc'),        hue:  45, unlocked: () => streak >= 7 },
		{ id: 3, label: t('profile.achRecipes'),  desc: t('profile.achRecipesDesc'),  hue: 295, unlocked: () => ownRecipes >= 3 },
		{ id: 4, label: t('profile.achWeight'),   desc: t('profile.achWeightDesc'),   hue: 220, unlocked: () => weightLogs >= 1 },
		{ id: 5, label: t('profile.achFriends'),  desc: t('profile.achFriendsDesc'),  hue: 330, unlocked: () => friendCount >= 1 },
		{ id: 6, label: t('profile.ach30'),       desc: t('profile.ach30Desc'),       hue:  25, unlocked: () => streak >= 30 },
	]);

	async function load() {
		loading = true;
		try {
			const [g, streakData, recipes, weights, friends] = await Promise.all([
				api.get<Goals>('/goals').catch(() => null),
				api.get<{ streak: number; active_days: number }>('/diary/streak').catch(() => ({ streak: 0, active_days: 0 })),
				api.get<Recipe[]>('/recipes').catch(() => []),
				api.get<WeightLog[]>('/weight').catch(() => []),
				api.get<Friendship[]>('/friends').catch(() => []),
			]);
			goals = g;
			streak = streakData.streak ?? 0;
			totalDays = streakData.active_days ?? 0;
			ownRecipes = recipes.filter(r => r.owner_id === auth.user?.id).length;
			weightLogs = weights.length;
			friendCount = friends.length;
		} finally {
			loading = false;
		}
	}

	$effect(() => { load(); });

	const userName = $derived(auth.user?.name ?? t('settings.user'));
	const userEmail = $derived(auth.user?.email ?? '');
	const userAvatar = $derived(auth.user?.avatar_id ?? null);
	const userColorHue = $derived(auth.user?.identity_hue ?? null);
	const nameHue = $derived((() => {
		let h = 0;
		for (const c of userName) h = (h * 31 + c.charCodeAt(0)) % 360;
		return h;
	})());

	const stats = $derived([
		{ l: t('profile.statStreak'),  v: streak > 0 ? String(streak) : '—',                       u: streak === 1 ? t('profile.unitDay') : t('profile.unitDays'), hue: 45 },
		{ l: t('profile.statActive'),  v: String(totalDays),                                       u: '/30',                  hue: 160 },
		{ l: t('profile.statKcal'),    v: goals?.kcal    ? String(Math.round(goals.kcal))    : '—', u: 'kcal',                 hue: 220 },
		{ l: t('profile.statProtein'), v: goals?.protein ? String(Math.round(goals.protein)) : '—', u: t('profile.unitGDay'),  hue: 295 },
	]);
</script>

<Aurora />

<div class="page">
	<ScreenHeader
		title={t('profile.title')}
		sub={t('profile.sub')}
		onBack={() => goto('/settings')}
	/>

	<!-- Hero -->
	<GlassCard padding={22}>
		<div class="hero">
			<button class="avatar-wrap" onclick={() => showAvatarPicker = true} title={t('profile.changeAvatar')}>
				<div class="avatar-shadow" style:--hue={userColorHue ?? nameHue}>
					<Avatar name={userName} avatarId={userAvatar} size={92} identityHue={userColorHue} ring="2.5px solid {identityColor(userName, userColorHue)}" />
				</div>
				<div class="edit-badge">✏️</div>
				{#if streak > 0}
					<div class="streak-badge">🔥 {streak}</div>
				{/if}
			</button>
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
				<div class="loading">{t('profile.loading')}</div>
			{/if}
		</div>
	</GlassCard>

	<!-- Color de identidad: propia sección, siempre visible (antes vivía escondida dentro del modal de avatar) -->
	<div class="section-title">{t('profile.yourColour')}</div>
	<GlassCard padding={18}>
		<div class="color-sub">{t('profile.yourColourSub')}</div>
		<div class="color-row">
			{#each IDENTITY_HUES as hue}
				<button
					class="color-opt"
					class:selected={userColorHue === hue}
					disabled={savingColor}
					style="background:{identityColor(userName, hue)};"
					onclick={() => pickColor(hue)}
					aria-label={t('profile.colourAria', { hue })}
				></button>
			{/each}
			<button
				class="color-opt color-auto"
				class:selected={userColorHue === null}
				disabled={savingColor}
				onclick={() => pickColor(null)}
				aria-label={t('profile.autoColourAria')}
				title={t('profile.autoColourTitle')}
			>A</button>
		</div>
	</GlassCard>

	<!-- Achievements -->
	<div class="section-title">{t('profile.achievements')}</div>
	<div class="ach-grid">
		{#each ACHIEVEMENTS as a}
			{@const unlocked = !loading && a.unlocked()}
			<div class="ach" class:unlocked style:--hue={a.hue}>
				<div class="ach-icon">{unlocked ? '🏆' : '🔒'}</div>
				<div class="ach-label">{a.label}</div>
				<div class="ach-desc">{a.desc}</div>
			</div>
		{/each}
	</div>

	<div class="spacer"></div>
</div>

{#if showAvatarPicker}
	<Modal onClose={() => showAvatarPicker = false} title={t('profile.pickAvatar')} subtitle={t('profile.pickAvatarSub')}>
		<div class="avatar-grid">
			{#each AVATARS as a}
				<button
					class="avatar-opt"
					class:selected={userAvatar === a.id}
					disabled={savingAvatar}
					onclick={() => pickAvatar(a.id)}
					title={avatarLabel(a.id)}
				>
					<Avatar name={avatarLabel(a.id)} avatarId={a.id} size={72} />
				</button>
			{/each}
		</div>
		<button class="avatar-clear" disabled={savingAvatar || !userAvatar} onclick={() => pickAvatar(null)}>
			{t('profile.useInitial', { initial: userName[0]?.toUpperCase() ?? 'U' })}
		</button>
	</Modal>
{/if}

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
		padding: 0;
		border: none;
		background: none;
		cursor: pointer;
		line-height: 0;
		/* Undo the global button chrome (gradient glow, hover brighten) */
		box-shadow: none;
		border-radius: 50%;
	}
	.avatar-wrap:hover { filter: none; box-shadow: none; }
	.avatar-shadow {
		width: 92px; height: 92px; border-radius: 50%;
		box-shadow: 0 10px 32px oklch(72% 0.18 var(--hue) / 0.3);
	}
	.edit-badge {
		position: absolute; top: 0; right: -4px;
		width: 28px; height: 28px; border-radius: 50%;
		background: rgba(20, 24, 34, 0.95);
		border: 1px solid rgba(255, 255, 255, 0.15);
		display: flex; align-items: center; justify-content: center;
		font-size: 12px;
		line-height: 1;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
	}
	.streak-badge {
		position: absolute; bottom: 0; right: -4px;
		padding: 4px 10px; border-radius: 99px;
		background: linear-gradient(135deg, oklch(80% 0.19 45), oklch(70% 0.2 30));
		font-size: 11px; font-weight: 800; color: #fff;
		/* The wrapper zeroes line-height for the avatar image; restore it here
		   or the badge has no text height and collapses to its padding. */
		line-height: 1.4;
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

	/* Avatar picker */
	.avatar-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 12px;
		justify-items: center;
	}
	.avatar-opt {
		padding: 4px;
		border-radius: 50%;
		border: 2px solid transparent;
		background: none;
		cursor: pointer;
		line-height: 0;
		/* Global button styling would glow as a rounded square behind the disc */
		box-shadow: none;
		transition: transform 0.12s, border-color 0.12s;
	}
	.avatar-opt:hover { transform: scale(1.06); filter: none; box-shadow: none; }
	.avatar-opt.selected {
		border-color: oklch(80% 0.17 165);
		box-shadow: 0 0 16px oklch(75% 0.2 165 / 0.4);
	}
	.avatar-opt:disabled { opacity: 0.5; cursor: default; }
	.avatar-clear {
		width: 100%;
		margin-top: 16px;
		padding: 12px;
		border-radius: 12px;
		border: 1px solid rgba(255, 255, 255, 0.12);
		background: rgba(255, 255, 255, 0.05);
		color: rgba(255, 255, 255, 0.75);
		font-family: inherit;
		font-size: 13px;
		font-weight: 600;
		cursor: pointer;
	}
	.avatar-clear:disabled { opacity: 0.4; cursor: default; }

	/* Color picker */
	.color-sub { font-size: 11.5px; color: rgba(255,255,255,0.5); margin: 0 0 12px; line-height: 1.4; }
	.color-row { display: flex; gap: 12px; flex-wrap: wrap; }
	.color-opt {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		border: 2px solid transparent;
		cursor: pointer;
		padding: 0;
		box-shadow: none;
		transition: transform 0.12s, border-color 0.12s;
	}
	.color-opt:hover { transform: scale(1.08); filter: none; box-shadow: none; }
	.color-opt.selected { border-color: #fff; box-shadow: 0 0 12px rgba(255,255,255,0.25); }
	.color-opt:disabled { opacity: 0.5; cursor: default; }
	.color-auto {
		background: rgba(255,255,255,0.06);
		color: rgba(255,255,255,0.7);
		font-size: 13px;
		font-weight: 800;
		display: flex;
		align-items: center;
		justify-content: center;
	}
</style>
