<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Goals, Recipe, User, WeightLog, Friendship } from '$lib/types';
	import Aurora from '$lib/components/uro/Aurora.svelte';
	import ScreenHeader from '$lib/components/uro/ScreenHeader.svelte';
	import GlassCard from '$lib/components/uro/GlassCard.svelte';
	import { Avatar, Modal } from '$lib/components';
	import { AVATARS, IDENTITY_HUES, identityColor } from '$lib/avatars';
	import { t, avatarLabel, ordinal } from '$lib/i18n/index.svelte';
	import { toast } from '$lib/stores/toast.svelte';

	if (!auth.isLoggedIn) goto('/login');

	let showAvatarPicker = $state(false);
	let savingAvatar = $state(false);
	let savingColor = $state(false);

	async function pickAvatar(id: string | null) {
		if (savingAvatar) return;
		savingAvatar = true;
		try {
			// Si hay foto, la foto gana: elegir un dibujo sin quitarla antes no
			// cambiaría nada en pantalla y parecería que el botón está roto.
			if (auth.user?.avatar_photo) {
				await api.del<User>('/users/me/avatar-photo');
				auth.updateUser({ avatar_photo: null });
			}
			await api.patch('/users/me/avatar', { avatar_id: id });
			auth.updateUser({ avatar_id: id });
			showAvatarPicker = false;
		} catch {
			toast.error(t('profile.errAvatar'));
		} finally {
			savingAvatar = false;
		}
	}

	let photoInput = $state<HTMLInputElement | null>(null);
	let uploadingPhoto = $state(false);

	async function uploadPhoto(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file || uploadingPhoto) return;
		uploadingPhoto = true;
		try {
			const form = new FormData();
			form.append('file', file);
			const updated = await api.upload<User>('/users/me/avatar-photo', form);
			auth.updateUser({ avatar_photo: updated.avatar_photo });
			showAvatarPicker = false;
		} catch (err) {
			toast.error(err instanceof Error ? err.message : t('profile.errPhoto'));
		} finally {
			uploadingPhoto = false;
			// Sin esto, volver a elegir el mismo fichero no dispara el change.
			input.value = '';
		}
	}

	async function removePhoto() {
		if (uploadingPhoto) return;
		uploadingPhoto = true;
		try {
			await api.del<User>('/users/me/avatar-photo');
			auth.updateUser({ avatar_photo: null });
		} catch {
			toast.error(t('profile.errPhoto'));
		} finally {
			uploadingPhoto = false;
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

	// Podios semanales entre los amigos con los que dueles. Todo lo que rodea al
	// avatar sale de aquí menos la racha, que ya la traía el perfil.
	interface Awards {
		gold: number; silver: number; bronze: number;
		current_rank: number | null; current_total: number;
		best_rank: number | null; best_total: number | null;
		pool: number;
	}
	let awards = $state<Awards | null>(null);

	async function load() {
		loading = true;
		try {
			const [g, streakData, recipes, weights, friends, aw] = await Promise.all([
				api.get<Goals>('/goals').catch(() => null),
				api.get<{ streak: number; active_days: number }>('/diary/streak').catch(() => ({ streak: 0, active_days: 0 })),
				api.get<Recipe[]>('/recipes').catch(() => []),
				api.get<WeightLog[]>('/weight').catch(() => []),
				api.get<Friendship[]>('/friends').catch(() => []),
				api.get<Awards>('/duel/me/awards').catch(() => null),
			]);
			goals = g;
			streak = streakData.streak ?? 0;
			totalDays = streakData.active_days ?? 0;
			ownRecipes = recipes.filter(r => r.owner_id === auth.user?.id).length;
			weightLogs = weights.length;
			friendCount = friends.length;
			awards = aw;
		} finally {
			loading = false;
		}
	}

	$effect(() => { load(); });

	const userName = $derived(auth.user?.name ?? t('settings.user'));
	const userEmail = $derived(auth.user?.email ?? '');
	const userAvatar = $derived(auth.user?.avatar_id ?? null);
	const userPhoto = $derived(auth.user?.avatar_photo ?? null);
	const userColorHue = $derived(auth.user?.identity_hue ?? null);
	const nameHue = $derived((() => {
		let h = 0;
		for (const c of userName) h = (h * 31 + c.charCodeAt(0)) % 360;
		return h;
	})());

	// Lo que orbita el avatar. Izquierda: lo ganado. Derecha: lo que llevas.
	// Sólo entra lo que existe — un lado vacío no deja hueco porque los datos no
	// tienen ni fondo ni borde, sólo son texto en el aire.
	type Orbiter = { e: string; v: string; cls: string; title: string };

	const leftItems = $derived.by<Orbiter[]>(() => {
		const a = awards;
		if (!a) return [];
		const out: Orbiter[] = [];
		if (a.gold) out.push({ e: '🥇', v: String(a.gold), cls: 'gold', title: t('profile.awardsGold', { n: a.gold }) });
		if (a.silver) out.push({ e: '🥈', v: String(a.silver), cls: 'silver', title: t('profile.awardsSilver', { n: a.silver }) });
		if (a.bronze) out.push({ e: '🥉', v: String(a.bronze), cls: 'bronze', title: t('profile.awardsBronze', { n: a.bronze }) });
		return out;
	});

	const rightItems = $derived.by<Orbiter[]>(() => {
		const out: Orbiter[] = [];
		if (streak > 0) out.push({ e: '🔥', v: String(streak), cls: 'fire', title: t('profile.awardsStreak', { n: streak }) });
		const a = awards;
		if (a?.current_rank) out.push({
			e: '📊',
			v: t('profile.awardsPosition', { rank: ordinal(a.current_rank), total: a.current_total }),
			cls: 'now', title: t('profile.awardsNow'),
		});
		if (a?.best_rank) out.push({
			e: '👑',
			v: t('profile.awardsPosition', { rank: ordinal(a.best_rank), total: a.best_total ?? 0 }),
			cls: 'best', title: t('profile.awardsBest'),
		});
		return out;
	});

	// Posiciones *relativas al centro* del hero (dx), nunca absolutas dentro de
	// un lienzo de ancho fijo: un lienzo más ancho que el hueco disponible
	// desborda, y entonces `margin:auto` deja de centrar y todo se va de lado.
	// Cada lado se ancla además por su borde interior, así que una etiqueta
	// larga («1.º de 412») crece hacia fuera y nunca se come el aro del avatar.
	// La `y` es la del centro de cada pieza dentro del lienzo, que mide justo lo
	// que ocupa el conjunto (106): el avatar va de 14 a 106 y los 14 de arriba
	// son para el lápiz. Cualquier alto de más se convierte en un hueco entre la
	// foto y el nombre.
	const ORBIT_L = [{ dx: -58, y: 21 }, { dx: -68, y: 60 }, { dx: -58, y: 99 }];
	const ORBIT_R = [{ dx: 58, y: 21 }, { dx: 68, y: 60 }, { dx: 58, y: 99 }];
	// Con una sola pieza va al centro; con dos, arriba y abajo — nunca dos
	// seguidas dejando el hueco del medio a la vista.
	const slots = (n: number) => (n === 1 ? [1] : n === 2 ? [0, 2] : [0, 1, 2]);

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
			<div class="orbit-stage">
				<button class="avatar-wrap" onclick={() => showAvatarPicker = true} title={t('profile.changeAvatar')}>
					<div class="avatar-shadow" style:--hue={userColorHue ?? nameHue}>
						<Avatar name={userName} avatarId={userAvatar} avatarPhoto={userPhoto} size={92} identityHue={userColorHue} ring="2.5px solid {identityColor(userName, userColorHue)}" />
					</div>
					<div class="edit-badge">✏️</div>
				</button>
				{#each leftItems.slice(0, 3) as it, i (it.cls)}
					{@const p = ORBIT_L[slots(Math.min(leftItems.length, 3))[i]]}
					<span class="orbiter l {it.cls}" style="margin-left:{p.dx}px; top:{p.y}px;" title={it.title}>{it.e} {it.v}</span>
				{/each}
				{#each rightItems.slice(0, 3) as it, i (it.cls)}
					{@const p = ORBIT_R[slots(Math.min(rightItems.length, 3))[i]]}
					<span class="orbiter r {it.cls}" style="margin-left:{p.dx}px; top:{p.y}px;" title={it.title}>{it.e} {it.v}</span>
				{/each}
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
		<!-- La foto primero: es lo que la mayoría viene buscando -->
		<div class="photo-row">
			<!--
				Sin image/heic en el accept a propósito, aunque sea lo que dispara
				un iPhone por defecto: Pillow no lo decodifica. Y al no declararlo,
				iOS entrega la foto ya convertida a JPEG en vez del HEIC original,
				que es justo lo que nos conviene.
			-->
			<input
				bind:this={photoInput}
				type="file"
				accept="image/jpeg,image/png,image/webp"
				onchange={uploadPhoto}
				style="display:none"
			/>
			<button class="photo-btn" disabled={uploadingPhoto} onclick={() => photoInput?.click()}>
				{uploadingPhoto ? t('profile.photoUploading') : userPhoto ? t('profile.photoChange') : t('profile.photoUpload')}
			</button>
			{#if userPhoto}
				<button class="photo-btn ghost" disabled={uploadingPhoto} onclick={removePhoto}>
					{t('profile.photoRemove')}
				</button>
			{/if}
		</div>
		<p class="photo-hint">{t('profile.photoHint')}</p>

		<div class="avatar-grid">
			{#each AVATARS as a}
				<button
					class="avatar-opt"
					class:selected={userAvatar === a.id && !userPhoto}
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
	/* Lienzo fijo: el avatar va clavado en su centro, así que lo que orbita no
	   puede descentrarlo por muy largas que sean las etiquetas. */
	.orbit-stage {
		position: relative;
		width: 100%;
		/* Justo el alto del conjunto: 92 del avatar + 14 que asoma el lápiz. Con
		   más, el sobrante sale como un hueco entre la foto y el nombre. */
		height: 106px;
		margin: 0 0 10px;
	}
	.orbit-stage .avatar-wrap {
		position: absolute;
		left: 50%;
		top: 60px;
		transform: translate(-50%, -50%);
		margin: 0;
	}
	.orbiter {
		position: absolute;
		left: 50%;
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-size: 11px;
		font-weight: 800;
		line-height: 1;
		white-space: nowrap;
		font-variant-numeric: tabular-nums;
		/* Sin fondo ni borde: la legibilidad sobre una foto de perfil clara la
		   da la sombra. Y sin capturar toques, que debajo está el botón que
		   abre el selector de avatar. */
		text-shadow: 0 1px 6px rgba(0, 0, 0, 0.65);
		pointer-events: none;
	}
	/* En pantallas estrechas el hueco a cada lado del avatar baja de 60px, y la
	   pieza más larga («1.º de 412») se sale de la tarjeta. Un punto menos de
	   cuerpo la devuelve dentro sin tocar la composición. */
	@media (max-width: 360px) {
		.orbiter { font-size: 10px; }
	}
	.orbiter.l { transform: translate(-100%, -50%); }
	.orbiter.r { transform: translate(0, -50%); }
	.orbiter.gold { color: oklch(88% 0.15 95); }
	.orbiter.silver { color: rgba(255, 255, 255, 0.82); }
	.orbiter.bronze { color: oklch(80% 0.12 55); }
	.orbiter.fire { color: oklch(85% 0.16 45); }
	.orbiter.now { color: oklch(85% 0.13 200); }
	.orbiter.best { color: oklch(85% 0.14 300); }
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
	/* Arriba y centrado: los dos costados los ocupa ahora lo que orbita, y en
	   la esquina de siempre chocaba con la pieza de arriba a la derecha. */
	.edit-badge {
		position: absolute; top: -14px; left: 50%; transform: translateX(-50%);
		width: 28px; height: 28px; border-radius: 50%;
		background: rgba(20, 24, 34, 0.95);
		border: 1px solid rgba(255, 255, 255, 0.15);
		display: flex; align-items: center; justify-content: center;
		font-size: 12px;
		line-height: 1;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
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

	/* Subir foto */
	.photo-row { display: flex; gap: 8px; margin-bottom: 8px; }
	.photo-btn {
		flex: 1;
		padding: 12px;
		border-radius: 12px;
		border: none;
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		font-family: inherit;
		font-size: 13px;
		font-weight: 800;
		cursor: pointer;
	}
	.photo-btn.ghost {
		flex: 0 0 auto;
		border: 1px solid rgba(255, 255, 255, 0.12);
		background: rgba(255, 255, 255, 0.05);
		color: rgba(255, 255, 255, 0.75);
		font-weight: 600;
	}
	.photo-btn:disabled { opacity: 0.5; cursor: default; }
	.photo-hint {
		font-size: 11.5px;
		color: rgba(255, 255, 255, 0.45);
		margin: 0 0 16px;
		line-height: 1.45;
	}

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
