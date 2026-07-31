<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import { pendingFriends } from '$lib/stores/friends.svelte';
	import { pushStore, isNativeApp } from '$lib/stores/push.svelte';
	import { toast } from '$lib/stores/toast.svelte';
	import { subscription } from '$lib/stores/subscription.svelte';
	import { APP_VERSION } from '$lib/changelog';
	import type { Goals, User } from '$lib/types';
	import { t, tc, i18n, setLocale, mealLabel, ordinal, LOCALE_NAMES, type Locale } from '$lib/i18n/index.svelte';
	import Flag from '$lib/components/Flag.svelte';
	import { Avatar } from '$lib/components';
	import { identityColor } from '$lib/avatars';

	const LOCALES: Locale[] = ['es', 'en', 'pt'];
	if (!auth.isLoggedIn) goto('/login');

	// ── Percentil anónimo de constancia ─────────────────────────────────────────
	interface Percentile {
		in_ranking: boolean;
		pct?: number;
		rank?: number;
		active_users: number;
		top_percent?: number;
		gap_to_next?: number | null;
		medal?: number | null;
		prev_rank?: number | null;
		prev_active_users?: number | null;
		prev_top_percent?: number | null;
		week: number;
	}
	let percentile = $state<Percentile | null>(null);
	api.get<Percentile>('/duel/me/percentile').then((p) => (percentile = p)).catch(() => {});

	const MEDALS = ['🥇', '🥈', '🥉'];

	// A band needs a crowd to mean anything: with 4 people active, the best
	// possible band is "top 25%", which reads like mediocrity when you're
	// actually first. Under this many the row shows the exact position; above
	// it only the podium keeps it, because "37.º de 412" tells you less than
	// "top 9%" does.
	const SMALL_POPULATION = 10;
	let showRank = $derived(
		!!percentile?.in_ranking && (percentile.active_users < SMALL_POPULATION || !!percentile.medal)
	);

	// Only rises get a chip. A fall never gets its own badge: the position is
	// already on screen, so stamping it red adds no information — the row shows
	// `gap_to_next` instead, which says the same thing pointing forwards.
	//
	// Measured on whatever the row displays (raw position in rank mode, share of
	// people strictly above me in band mode) and never on the band itself: #1 of
	// 5 is top 20% and #1 of 4 is top 25%, so a week where someone stopped
	// logging would invent a movement that never happened.
	let rise = $derived.by(() => {
		const p = percentile;
		if (!p?.in_ranking || p.rank == null || p.prev_rank == null || !p.prev_active_users) return null;
		const [now, before] = showRank
			? [p.rank, p.prev_rank]
			: [(p.rank - 1) / p.active_users, (p.prev_rank - 1) / p.prev_active_users];
		if (now >= before) return null;
		return showRank ? ordinal(p.prev_rank) : `${p.prev_top_percent ?? 0} %`;
	});

	// ── Compartir la app ─────────────────────────────────────────────────────────
	// Enlaza a la landing /unete (con Open Graph → tarjeta con imagen en WhatsApp),
	// no al APK a pelo: una redirección a un binario no puede tener preview.
	// El ?lang= no es decorativo: los crawlers de WhatsApp no mandan
	// Accept-Language, así que sin él la tarjeta saldría siempre en español. Al ir
	// en la query, cada idioma se cachea por separado tanto en WhatsApp como en el
	// edge (Cloudflare ignora Vary salvo Cache Rule, la query string no).
	let INVITE_URL = $derived(`https://comida.mugrelore.com/unete?lang=${i18n.locale}`);
	let INVITE_TEXT = $derived(t('settings.inviteText', { url: INVITE_URL }));
	let inviteCopied = $state(false);
	async function shareApp() {
		if (navigator.share) {
			try {
				await navigator.share({ text: INVITE_TEXT });
				return;
			} catch {
				return; // usuario canceló el share sheet — no hacer fallback
			}
		}
		try {
			await navigator.clipboard.writeText(INVITE_TEXT);
		} catch {
			// Clipboard API bloqueada (WebView viejo, permisos): fallback clásico.
			const ta = document.createElement('textarea');
			ta.value = INVITE_TEXT;
			ta.style.position = 'fixed';
			ta.style.opacity = '0';
			document.body.appendChild(ta);
			ta.select();
			const ok = document.execCommand('copy');
			ta.remove();
			if (!ok) {
				toast.error(t('settings.errCopy'));
				return;
			}
		}
		inviteCopied = true;
		setTimeout(() => (inviteCopied = false), 3000);
	}

	// ── Changelog / update-nudge subscription ──────────────────────────────────
	let changelogOptOut = $state(auth.user?.changelog_opt_out ?? false);
	let savingChangelog = $state(false);
	async function toggleChangelog() {
		savingChangelog = true;
		const next = !changelogOptOut;
		try {
			const u = await api.patch<User>('/users/me/changelog-subscription', { opt_out: next });
			changelogOptOut = u.changelog_opt_out ?? next;
			auth.updateUser(u);
		} catch {
			toast.error(t('settings.errSavePref'));
		} finally {
			savingChangelog = false;
		}
	}

	// ── Notification prefs ─────────────────────────────────────────────────────
	interface NotifPrefs {
		enabled: boolean;
		quiet_start: number; quiet_end: number;
		breakfast_on: boolean; breakfast_time: string;
		lunch_on: boolean; lunch_time: string;
		dinner_on: boolean; dinner_time: string;
		streak_on: boolean; streak_time: string; streak_min_days: number;
		summary_on: boolean; summary_time: string;
		water_on: boolean; water_time: string;
		timezone: string;
	}

	// Common IANA timezones for the selector
	// Lisboa entra ahora que la app habla portugués.
	let TIMEZONES = $derived([
		{ value: 'Europe/Madrid',      label: t('settings.tzMadrid') },
		{ value: 'Europe/Lisbon',      label: t('settings.tzLisbon') },
		{ value: 'Europe/London',      label: t('settings.tzLondon') },
		{ value: 'Europe/Paris',       label: t('settings.tzParis') },
		{ value: 'America/Mexico_City',label: t('settings.tzMexico') },
		{ value: 'America/Bogota',     label: t('settings.tzBogota') },
		{ value: 'America/Caracas',    label: t('settings.tzCaracas') },
		{ value: 'America/Santiago',   label: t('settings.tzSantiago') },
		{ value: 'America/Argentina/Buenos_Aires', label: t('settings.tzBuenosAires') },
		{ value: 'America/Sao_Paulo',  label: t('settings.tzSaoPaulo') },
		{ value: 'America/New_York',   label: t('settings.tzNewYork') },
		{ value: 'America/Los_Angeles',label: t('settings.tzLosAngeles') },
		{ value: 'UTC',                label: 'UTC' },
	]);
	let prefs: NotifPrefs | null = $state(null);
	let savingPrefs = $state(false);
	let testSent = $state(false);

	async function loadPrefs() {
		prefs = await api.get<NotifPrefs>('/push/prefs').catch(() => null);
	}
	loadPrefs();

	async function savePrefs(patch: Partial<NotifPrefs>) {
		if (!prefs) return;
		prefs = { ...prefs, ...patch };
		savingPrefs = true;
		try {
			prefs = await api.put<NotifPrefs>('/push/prefs', patch);
			// Re-schedule local notifications on native whenever prefs change
			await pushStore.reschedule();
		} catch { toast.error(t('settings.errSavePref')); } finally {
			savingPrefs = false;
		}
	}

	async function enableNotifs() {
		const ok = await pushStore.subscribe();
		if (ok) await savePrefs({ enabled: true });
	}

	async function disableNotifs() {
		await savePrefs({ enabled: false });
		await pushStore.unsubscribe();
	}

	async function sendTestNotif() {
		await pushStore.sendTest();
		testSent = true;
		setTimeout(() => testSent = false, 3000);
	}

	let goals: Goals | null = $state(null);
	let savingCreatine = $state(false);
	let savingCheatDays = $state(false);
	let savingInventory = $state(false);
	let moodEnabled = $state(typeof localStorage !== 'undefined' ? localStorage.getItem('mood_enabled') === 'true' : false);
	let showDeleteModal = $state(false);
	let deletingAccount = $state(false);
	let deleteConfirmText = $state('');
	let allergyCount = $state(0);

	async function deleteAccount() {
		if (deleteConfirmText !== t('settings.deleteConfirmWord')) return;
		deletingAccount = true;
		try {
			await api.del('/users/me');
			auth.logout();
			goto('/login');
		} catch {
			deletingAccount = false;
			showDeleteModal = false;
			toast.error(t('settings.errDelete'));
		}
	}

	async function loadGoals() {
		goals = await api.get<Goals>('/goals').catch(() => null);
	}

	async function loadAllergyCount() {
		const rows = await api.get<Array<{id: number, ingredient: string}>>('/allergies').catch(() => []);
		allergyCount = rows.length;
	}

	loadGoals();
	loadAllergyCount();

	async function toggleCreatine() {
		if (!goals) return;
		savingCreatine = true;
		try {
			goals = await api.put<Goals>('/goals', { ...goals, track_creatine: !goals.track_creatine });
		} catch {
			toast.error(t('settings.errSaveConfig'));
		} finally {
			savingCreatine = false;
		}
	}

	async function toggleCheatDays() {
		if (!goals) return;
		savingCheatDays = true;
		try {
			goals = await api.put<Goals>('/goals', { ...goals, cheat_days_enabled: !goals.cheat_days_enabled });
		} catch {
			toast.error(t('settings.errSaveConfig'));
		} finally {
			savingCheatDays = false;
		}
	}

	function toggleMood() {
		moodEnabled = !moodEnabled;
		localStorage.setItem('mood_enabled', moodEnabled ? 'true' : 'false');
	}

	async function toggleInventory() {
		savingInventory = true;
		try {
			const base = goals ?? { kcal: 2000, protein: 150, carbs: 250, fat: 65, water_ml: 2000, track_creatine: false, cheat_days_enabled: false, inventory_enabled: false, macro_adjust_mode: 'off' as const };
			goals = await api.put<Goals>('/goals', { ...base, inventory_enabled: !base.inventory_enabled });
		} catch {
			toast.error(t('settings.errSaveConfig'));
		} finally {
			savingInventory = false;
		}
	}

	let savingMacroMode = $state(false);
	async function setMacroAdjustMode(mode: 'off' | 'proportional' | 'performance') {
		if (!goals || goals.macro_adjust_mode === mode) return;
		savingMacroMode = true;
		try {
			goals = await api.put<Goals>('/goals', { ...goals, macro_adjust_mode: mode });
		} catch {
			toast.error(t('settings.errSaveConfig'));
		} finally {
			savingMacroMode = false;
		}
	}

	function logout() {
		auth.logout();
		goto('/login');
	}
</script>

<!-- ── Header ── -->
<div style="display:flex; align-items:center; gap:0.75rem; padding:0.25rem 0 1rem;">
	<div style="flex:1; min-width:0;">
		<h1 style="font-size:1.875rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1; margin:0; font-family:'Lora','Georgia',serif;">{t('settings.title')}</h1>
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.25rem;">{t('settings.subtitle')}</div>
	</div>
</div>

<!-- ── Group: Objetivos ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">{t('settings.group.goals')}</div>
	<div class="settings-group">
		<!-- Kcal y macros -->
		<button class="settings-row" onclick={() => goto('/goals')}>
			<div class="icon-box">🎯</div>
			<div class="row-content">
				<div class="row-label">{t('settings.kcalMacros')}</div>
				{#if goals}
					<div class="row-detail">{Math.round(goals.kcal)} kcal · P{Math.round(goals.protein ?? 0)} / C{Math.round(goals.carbs ?? 0)} / G{Math.round(goals.fat ?? 0)}</div>
				{/if}
			</div>
			<span class="chevron">›</span>
		</button>
		<div class="row-divider"></div>
		<!-- Suplementos -->
		<button class="settings-row" onclick={() => goto('/supplements')}>
			<div class="icon-box">💊</div>
			<div class="row-content">
				<div class="row-label">{t('settings.supplements')}</div>
				<div class="row-detail">{t('settings.supplementsDetail')}</div>
			</div>
			<span class="chevron">›</span>
		</button>
		<div class="row-divider"></div>
		<!-- Cheat day -->
		<div class="settings-row" style="cursor:default;">
			<div class="icon-box">🍕</div>
			<div class="row-content">
				<div class="row-label">{t('settings.cheatDays')}</div>
				<div class="row-detail">{goals?.cheat_days_enabled ? t('settings.active') : t('settings.inactive')}</div>
			</div>
			{#if goals}
				<button
					onclick={toggleCheatDays}
					disabled={savingCheatDays}
					class="toggle-btn"
					aria-label={t('settings.cheatDays')}
					aria-pressed={goals.cheat_days_enabled}
					style="background:{goals.cheat_days_enabled ? 'oklch(75% 0.18 165 / 0.35)' : 'rgba(255,255,255,0.08)'}; border-color:{goals.cheat_days_enabled ? 'oklch(80% 0.17 165 / 0.5)' : 'rgba(255,255,255,0.1)'};"
				>
					<span class="toggle-knob" style="left:{goals.cheat_days_enabled ? '18px' : '2px'};"></span>
				</button>
			{/if}
		</div>
		<div class="row-divider"></div>
		<!-- Macro adjust mode -->
		<div class="settings-row" style="cursor:default; flex-direction:column; align-items:flex-start; gap:0.625rem;">
			<div style="display:flex; align-items:center; gap:0.75rem; width:100%;">
				<div class="icon-box">⚡</div>
				<div class="row-content">
					<div class="row-label">{t('settings.macroAdjust')}</div>
					<div class="row-detail">{t('settings.macroAdjustDetail')}</div>
				</div>
			</div>
			{#if goals}
				<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.375rem; width:100%; padding-left:2.75rem;">
					{#each [
						{ value: 'off',          label: t('settings.macroOff'),          note: t('settings.macroOffNote'),          pro: false },
						{ value: 'proportional', label: t('settings.macroProportional'), note: t('settings.macroProportionalNote'), pro: true  },
						{ value: 'performance',  label: t('settings.macroPerformance'),  note: t('settings.macroPerformanceNote'),  pro: true  },
					] as opt}
						{@const locked = opt.pro && !subscription.is_premium}
						<button
							onclick={() => locked ? goto('/premium') : setMacroAdjustMode(opt.value as 'off' | 'proportional' | 'performance')}
							disabled={savingMacroMode && !locked}
							style="
								padding:0.5rem 0.25rem;
								border-radius:0.625rem;
								border:1px solid {goals.macro_adjust_mode === opt.value ? 'oklch(80% 0.17 165 / 0.6)' : 'rgba(255,255,255,0.1)'};
								background:{goals.macro_adjust_mode === opt.value ? 'oklch(75% 0.18 165 / 0.15)' : 'rgba(255,255,255,0.04)'};
								box-shadow:none;
								color:{locked ? 'rgba(255,255,255,0.3)' : goals.macro_adjust_mode === opt.value ? 'oklch(85% 0.17 165)' : 'rgba(255,255,255,0.55)'};
								font-size:0.6875rem;
								font-weight:{goals.macro_adjust_mode === opt.value ? '700' : '400'};
								text-align:center;
								cursor:{locked ? 'pointer' : 'pointer'};
								transition:all 0.15s;
								line-height:1.3;
								position:relative;
							"
						>
							{opt.label}<br>
							<span style="font-size:0.5625rem; opacity:0.7;">{locked ? '🔒 PRO' : opt.note}</span>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</div>

<!-- ── Group: Social ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">{t('settings.group.social')}</div>
	<div class="settings-group">
		<!-- Mi perfil (avatar y nombre: es lo que ven tus amigos) -->
		<button class="settings-row" onclick={() => goto('/profile')}>
			<!-- Su cara, no un icono: es la fila que lleva al perfil, y de paso se
			     ve de un vistazo qué avatar tienen puesto tus amigos de ti. El aro
			     va en su color de identidad, como en el propio perfil. -->
			<Avatar
				name={auth.user?.name ?? t('settings.user')}
				avatarId={auth.user?.avatar_id ?? null}
				avatarPhoto={auth.user?.avatar_photo ?? null}
				size={32}
				identityHue={auth.user?.identity_hue ?? null}
				ring="1.5px solid {identityColor(auth.user?.name ?? '?', auth.user?.identity_hue ?? null)}"
			/>
			<div class="row-content">
				<div class="row-label">{auth.user?.name ?? t('settings.user')}</div>
				<div class="row-detail">{t('settings.profileDetail')}</div>
			</div>
			<span class="chevron">›</span>
		</button>
		<div class="row-divider"></div>
		<button class="settings-row" onclick={() => goto('/friends')}>
			<div class="icon-box">💑</div>
			<div class="row-content">
				<div class="row-label" style="display:flex; align-items:center; gap:0.4rem;">
					{t('settings.friends')}
					{#if pendingFriends.count > 0}
						<span style="background:oklch(55% 0.23 25); color:#fff; border-radius:99px; padding:0.05rem 0.4rem; font-size:0.625rem; font-weight:800; line-height:1.5;">{pendingFriends.count}</span>
					{/if}
				</div>
				<div class="row-detail">{t('settings.friendsDetail')}</div>
			</div>
			<span class="chevron">›</span>
		</button>
		<div class="row-divider"></div>
		<!-- Percentil anónimo de constancia -->
		<div class="settings-row" style="cursor:default;">
			<div class="icon-box medal-{percentile?.medal ?? 0}">{percentile?.medal ? MEDALS[percentile.medal - 1] : '🏅'}</div>
			<div class="row-content">
				<div class="row-label">{t('settings.consistency')}{#if percentile?.in_ranking && percentile.active_users > 1}<span class="rank-chip medal-{percentile.medal ?? 0}">{#if showRank}{ordinal(percentile.rank ?? 1)}<span class="of">{t('settings.consistencyOfTotal', { total: percentile.active_users })}</span>{:else}{t('settings.consistencyTop', { pct: percentile.top_percent ?? 0 })}{/if}</span>{/if}</div>
				<div class="row-detail">
					{#if percentile?.in_ranking}
						{#if percentile.active_users > 1}
							{t('settings.consistencyPct', { pct: percentile.pct ?? 0 })}{#if rise}<span class="rank-move">{t(showRank ? 'settings.consistencyMoveRank' : 'settings.consistencyMove', { prev: rise })}</span>{:else if percentile.gap_to_next != null}<span class="rank-gap">{t('settings.consistencyGap', { points: percentile.gap_to_next })}</span>{t('settings.consistencyGapOf', { rank: ordinal((percentile.rank ?? 2) - 1) })}{:else}{t('settings.consistencyThisWeek')}{/if}
						{:else}
							{t('settings.consistencyAlone', { pct: percentile.pct ?? 0 })}
						{/if}
					{:else if percentile}
						{t('settings.consistencyEmpty')}
					{:else}
						—
					{/if}
				</div>
			</div>
		</div>
		<div class="row-divider"></div>
		<!-- Invitar -->
		<button class="settings-row" onclick={shareApp}>
			<div class="icon-box">📤</div>
			<div class="row-content">
				<div class="row-label">{inviteCopied ? t('settings.inviteCopied') : t('settings.invite')}</div>
				<div class="row-detail">{t('settings.inviteDetail')}</div>
			</div>
			<span class="chevron">›</span>
		</button>
	</div>
</div>

<!-- ── Group: Salud ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">{t('settings.group.health')}</div>
	<div class="settings-group">
		<!-- Alergias (gratis: /premium promete que lo son y el backend no las restringe) -->
		<button class="settings-row" onclick={() => goto('/allergies')}>
			<div class="icon-box" style="background:oklch(35% 0.15 40 / 0.3); border:1px solid oklch(60% 0.2 40 / 0.3);">⚠️</div>
			<div class="row-content">
				<div class="row-label">{t('settings.allergies')}</div>
				<div class="row-detail">{allergyCount > 0 ? tc('settings.allergiesCount', allergyCount) : t('settings.allergiesEmpty')}</div>
			</div>
			<span class="chevron">›</span>
		</button>
	</div>
</div>
<!-- ── Group: Datos ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">{t('settings.group.data')}</div>
	<div class="settings-group">
		<button class="settings-row" onclick={() => goto('/weight')}>
			<div class="icon-box">⚖️</div>
			<div class="row-content">
				<div class="row-label">{t('settings.weightLog')}</div>
				<div class="row-detail">{t('settings.weightLogDetail')}</div>
			</div>
			<span class="chevron">›</span>
		</button>
		<div class="row-divider"></div>
		<button class="settings-row" onclick={() => goto('/measurements')}>
			<div class="icon-box">📏</div>
			<div class="row-content">
				<div class="row-label">{t('settings.measurements')}</div>
				<div class="row-detail">{subscription.is_premium ? t('settings.measurementsDetail') : t('settings.premiumOnly')}</div>
			</div>
			{#if !subscription.is_premium}<span class="pro-badge-row">PRO</span>{:else}<span class="chevron">›</span>{/if}
		</button>
		<div class="row-divider"></div>
		<button class="settings-row" onclick={() => goto('/exercises')}>
			<div class="icon-box">💪</div>
			<div class="row-content">
				<div class="row-label">{t('settings.exercises')}</div>
				<div class="row-detail">{subscription.is_premium ? t('settings.exercisesDetail') : t('settings.premiumOnly')}</div>
			</div>
			{#if !subscription.is_premium}<span class="pro-badge-row">PRO</span>{:else}<span class="chevron">›</span>{/if}
		</button>
		<div class="row-divider"></div>
		<!-- Estado del día toggle -->
		<div class="settings-row" style="cursor:default;">
			<div class="icon-box">🫥</div>
			<div class="row-content">
				<div class="row-label">{t('settings.mood')}</div>
				<div class="row-detail">{moodEnabled ? t('settings.moodVisible') : t('settings.moodHidden')}{t('settings.moodDetail')}</div>
			</div>
			<button
				onclick={toggleMood}
				class="toggle-btn"
				aria-label={t('settings.mood')}
				aria-pressed={moodEnabled}
				style="background:{moodEnabled ? 'oklch(75% 0.18 165 / 0.35)' : 'rgba(255,255,255,0.08)'}; border-color:{moodEnabled ? 'oklch(80% 0.17 165 / 0.5)' : 'rgba(255,255,255,0.1)'};"
			>
				<span class="toggle-knob" style="left:{moodEnabled ? '18px' : '2px'};"></span>
			</button>
		</div>
		<div class="row-divider"></div>

		<!-- Inventario toggle + nav -->
		<div class="settings-row" style="cursor:default;">
			<div class="icon-box">🏠</div>
			<div class="row-content">
				<div class="row-label">{t('settings.inventory')}</div>
				<div class="row-detail">{goals?.inventory_enabled ? t('settings.active') : t('settings.inactive')}</div>
			</div>
			<button
				onclick={toggleInventory}
				disabled={savingInventory}
				class="toggle-btn"
				aria-label={t('settings.inventory')}
				aria-pressed={goals?.inventory_enabled ?? false}
				style="background:{goals?.inventory_enabled ? 'oklch(75% 0.18 165 / 0.35)' : 'rgba(255,255,255,0.08)'}; border-color:{goals?.inventory_enabled ? 'oklch(80% 0.17 165 / 0.5)' : 'rgba(255,255,255,0.1)'};"
			>
				<span class="toggle-knob" style="left:{goals?.inventory_enabled ? '18px' : '2px'};"></span>
			</button>
		</div>
		{#if goals?.inventory_enabled}
			<div class="row-divider"></div>
			<button class="settings-row" onclick={() => goto('/inventory')}>
				<div class="icon-box">📦</div>
				<div class="row-content">
					<div class="row-label">{t('settings.inventoryView')}</div>
					<div class="row-detail">{t('settings.inventoryViewDetail')}</div>
				</div>
				<span class="chevron">›</span>
			</button>
			<div class="row-divider"></div>
			<button class="settings-row" onclick={() => goto('/shopping-list')}>
				<div class="icon-box">🛒</div>
				<div class="row-content">
					<div class="row-label">{t('settings.shoppingList')}</div>
					<div class="row-detail">{t('settings.shoppingListDetail')}</div>
				</div>
				<span class="chevron">›</span>
			</button>
		{/if}
		<div class="row-divider"></div>
		<button class="settings-row" onclick={() => goto('/history')}>
			<div class="icon-box">📤</div>
			<div class="row-content">
				<div class="row-label">{t('settings.export')}</div>
				<div class="row-detail">{t('settings.exportDetail')}</div>
			</div>
			<span class="chevron">›</span>
		</button>
	</div>
</div>

<!-- ── Group: Notificaciones ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">{t('settings.group.notifs')}</div>
	<div class="settings-group">
		{#if isNativeApp && !pushStore.isSupported}
			<!-- Native app but plugin not ready yet — show spinner / wait for init -->
			<div class="settings-row" style="cursor:default; opacity:0.6;">
				<div class="icon-box">🔔</div>
				<div class="row-content">
					<div class="row-label">{t('settings.notifs')}</div>
					<div class="row-sub">{t('settings.notifsInit')}</div>
				</div>
			</div>
		{:else if !isNativeApp && !pushStore.isSupported}
			<div class="settings-row" style="cursor:default; opacity:0.5;">
				<div class="icon-box">🔔</div>
				<div class="row-content">
					<div class="row-label">{t('settings.notifsUnsupported')}</div>
					<div class="row-sub">{t('settings.notifsUnsupportedSub')}</div>
				</div>
			</div>
		{:else if pushStore.permission === 'denied'}
			<div class="settings-row" style="cursor:default;">
				<div class="icon-box">🔕</div>
				<div class="row-content">
					<div class="row-label">{t('settings.notifsBlocked')}</div>
					<div class="row-sub">{t('settings.notifsBlockedSub')}</div>
				</div>
			</div>
		{:else}
			<!-- Master toggle -->
			<div class="settings-row" style="cursor:default;">
				<div class="icon-box">🔔</div>
				<div class="row-content">
					<div class="row-label">{t('settings.notifsEnable')}</div>
					<div class="row-sub">
						{prefs?.enabled ? t('settings.notifsOn') : t('settings.notifsOff')}
					</div>
				</div>
				<button
					class="toggle-btn"
					class:toggle-on={prefs?.enabled}
					onclick={() => prefs?.enabled ? disableNotifs() : enableNotifs()}
					disabled={savingPrefs}
					aria-label={t('settings.notifsEnable')}
					aria-pressed={prefs?.enabled ?? false}
				>
					<span class="toggle-thumb"></span>
				</button>
			</div>

			{#if prefs?.enabled}
				{#if !subscription.is_premium}
					<!-- Notifs avanzadas bloqueadas para free -->
					<button class="settings-row" onclick={() => goto('/premium')} style="border-top:1px solid rgba(255,255,255,0.06);">
						<div class="icon-box">⚙️</div>
						<div class="row-content">
							<div class="row-label">{t('settings.notifsCustom')}</div>
							<div class="row-detail">{t('settings.notifsCustomDetail')}</div>
						</div>
						<span class="pro-badge-row">PRO</span>
					</button>
				{:else}
				<!-- Meal reminders -->
				<div class="notif-subsection">
					<div class="notif-sub-label">{t('settings.notifMeals')}</div>
					{#each [
						{ key: 'breakfast', label: mealLabel('breakfast'), emoji: '🍳', on: prefs.breakfast_on, time: prefs.breakfast_time },
						{ key: 'lunch',     label: mealLabel('lunch'), emoji: '🥗', on: prefs.lunch_on,     time: prefs.lunch_time     },
						{ key: 'dinner',    label: mealLabel('dinner'),     emoji: '🍽️', on: prefs.dinner_on,    time: prefs.dinner_time    },
					] as meal}
						<div class="notif-row">
							<span class="notif-emoji">{meal.emoji}</span>
							<span class="notif-meal-label">{meal.label}</span>
							<input
								type="time"
								class="time-input"
								value={meal.time}
								disabled={!meal.on}
								onchange={(e) => savePrefs({ [`${meal.key}_time`]: (e.target as HTMLInputElement).value } as Partial<NotifPrefs>)}
							/>
							<button
								class="toggle-btn toggle-sm"
								class:toggle-on={meal.on}
								onclick={() => savePrefs({ [`${meal.key}_on`]: !meal.on } as Partial<NotifPrefs>)}
								aria-label={t('settings.notifToggle', { what: meal.label })}
							><span class="toggle-thumb"></span></button>
						</div>
					{/each}
				</div>

				<!-- Streak alert -->
				<div class="notif-subsection">
					<div class="notif-sub-label">{t('settings.notifStreak')}</div>
					<div class="notif-row">
						<span class="notif-emoji">🔥</span>
						<span class="notif-meal-label">{t('settings.notifStreakDanger')}</span>
						<input type="time" class="time-input" value={prefs.streak_time} disabled={!prefs.streak_on}
							onchange={(e) => savePrefs({ streak_time: (e.target as HTMLInputElement).value })} />
						<button class="toggle-btn toggle-sm" class:toggle-on={prefs.streak_on}
							onclick={() => savePrefs({ streak_on: !prefs.streak_on })}
							aria-label={t('settings.notifToggle', { what: t('settings.notifStreak') })}><span class="toggle-thumb"></span></button>
					</div>
					<div class="notif-row">
						<span class="notif-emoji">🏆</span>
						<span class="notif-meal-label">{t('settings.notifStreakMilestones')}</span>
						<span class="notif-hint">{t('settings.milestoneHint')}</span>
						<span class="notif-always">{t('settings.notifAlways')}</span>
					</div>
				</div>

				<!-- Summary + water -->
				<div class="notif-subsection">
					<div class="notif-sub-label">{t('settings.notifSummaryWater')}</div>
					<div class="notif-row">
						<span class="notif-emoji">📊</span>
						<span class="notif-meal-label">{t('settings.notifDailySummary')}</span>
						<input type="time" class="time-input" value={prefs.summary_time} disabled={!prefs.summary_on}
							onchange={(e) => savePrefs({ summary_time: (e.target as HTMLInputElement).value })} />
						<button class="toggle-btn toggle-sm" class:toggle-on={prefs.summary_on}
							onclick={() => savePrefs({ summary_on: !prefs.summary_on })}
							aria-label={t('settings.notifToggle', { what: t('settings.notifDailySummary') })}><span class="toggle-thumb"></span></button>
					</div>
					<div class="notif-row">
						<span class="notif-emoji">💧</span>
						<span class="notif-meal-label">{t('settings.notifWater')}</span>
						<input type="time" class="time-input" value={prefs.water_time} disabled={!prefs.water_on}
							onchange={(e) => savePrefs({ water_time: (e.target as HTMLInputElement).value })} />
						<button class="toggle-btn toggle-sm" class:toggle-on={prefs.water_on}
							onclick={() => savePrefs({ water_on: !prefs.water_on })}
							aria-label={t('settings.notifToggle', { what: t('settings.notifWater') })}><span class="toggle-thumb"></span></button>
					</div>
				</div>

				<!-- Quiet hours + Timezone -->
				<div class="notif-subsection">
					<div class="notif-sub-label">{t('settings.notifQuiet')}</div>
					<div class="notif-row" style="gap:0.5rem;">
						<span class="notif-emoji">🌙</span>
						<span class="notif-meal-label">{t('settings.notifQuietFrom')}</span>
						<input type="number" min="0" max="23" class="hour-input" value={prefs.quiet_start}
							onchange={(e) => savePrefs({ quiet_start: Number((e.target as HTMLInputElement).value) })} />
						<span style="color:var(--text-muted); font-size:0.8rem;">{t('settings.notifQuietTo')}</span>
						<input type="number" min="0" max="23" class="hour-input" value={prefs.quiet_end}
							onchange={(e) => savePrefs({ quiet_end: Number((e.target as HTMLInputElement).value) })} />
						<span style="color:var(--text-muted); font-size:0.75rem;">h</span>
					</div>
					<div class="notif-row" style="gap:0.5rem; margin-top:0.25rem;">
						<span class="notif-emoji">🌍</span>
						<span class="notif-meal-label">{t('settings.notifTimezone')}</span>
						<select
							class="tz-select"
							value={prefs.timezone}
							onchange={(e) => savePrefs({ timezone: (e.target as HTMLSelectElement).value })}
						>
							{#each TIMEZONES as tz}
								<option value={tz.value}>{tz.label}</option>
							{/each}
						</select>
					</div>
				</div>

				<!-- Test button -->
				<button class="settings-row" onclick={sendTestNotif} style="border-top:1px solid rgba(255,255,255,0.06);">
					<div class="icon-box">📨</div>
					<div class="row-content">
						<div class="row-label">{testSent ? t('settings.notifTestSent') : t('settings.notifTest')}</div>
						<div class="row-sub">{t('settings.notifTestSub')}</div>
					</div>
					<div class="row-arrow">›</div>
				</button>
				{/if}
			{/if}
		{/if}
	</div>
</div>

<!-- ── Group: Idioma ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">{t('settings.language.group')}</div>
	<div class="settings-group">
		{#each LOCALES as loc, i}
			{#if i > 0}<div class="row-divider"></div>{/if}
			<button class="settings-row" onclick={() => setLocale(loc)} aria-pressed={i18n.locale === loc}>
				<div class="icon-box"><Flag locale={loc} /></div>
				<div class="row-content">
					<div class="row-label">{LOCALE_NAMES[loc]}</div>
					{#if i18n.locale === loc}
						<div class="row-detail">{t('settings.language.active')}</div>
					{/if}
				</div>
				{#if i18n.locale === loc}
					<span style="color:oklch(80% 0.17 165); font-weight:800;">✓</span>
				{/if}
			</button>
		{/each}
	</div>
	<div class="group-hint">{t('settings.language.hint')}</div>
</div>

<!-- ── Group: Novedades ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">{t('settings.group.news')}</div>
	<div class="settings-group">
		<div class="settings-row" style="cursor:default;">
			<div class="icon-box">📣</div>
			<div class="row-content">
				<div class="row-label">{t('settings.news')}</div>
				<div class="row-detail">{changelogOptOut ? t('settings.newsOff') : t('settings.newsOn')}</div>
			</div>
			<button
				onclick={toggleChangelog}
				disabled={savingChangelog}
				class="toggle-btn"
				aria-label={t('settings.news')}
				aria-pressed={!changelogOptOut}
				style="background:{!changelogOptOut ? 'oklch(75% 0.18 165 / 0.35)' : 'rgba(255,255,255,0.08)'}; border-color:{!changelogOptOut ? 'oklch(80% 0.17 165 / 0.5)' : 'rgba(255,255,255,0.1)'};"
			>
				<span class="toggle-knob" style="left:{!changelogOptOut ? '18px' : '2px'};"></span>
			</button>
		</div>
	</div>
</div>

<!-- ── Group: Plan ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">{t('settings.group.plan')}</div>
	<div class="settings-group">
		<!-- Tier status -->
		<button class="settings-row" onclick={() => goto('/premium')}>
			<div class="icon-box" style="
				background:{subscription.status === 'premium' ? 'oklch(75% 0.2 165 / 0.2)' : subscription.status === 'trial' ? 'oklch(72% 0.18 55 / 0.2)' : 'rgba(255,255,255,0.05)'};
				border:1px solid {subscription.status === 'premium' ? 'oklch(75% 0.2 165 / 0.35)' : subscription.status === 'trial' ? 'oklch(72% 0.18 55 / 0.35)' : 'rgba(255,255,255,0.08)'};
			">
				{subscription.status === 'premium' ? '👑' : subscription.status === 'trial' ? '⏳' : '🔓'}
			</div>
			<div class="row-content">
				<div class="row-label" style="color:{subscription.status === 'premium' ? 'oklch(85% 0.19 160)' : subscription.status === 'trial' ? 'oklch(85% 0.16 60)' : '#fff'};">
					{subscription.status === 'premium' ? t('settings.planPremium') : subscription.status === 'trial' ? t('settings.planTrial') : t('settings.planFree')}
				</div>
				<div class="row-detail">
					{#if subscription.status === 'trial' && subscription.trial_days_left !== null}
						{subscription.trial_days_left === 0 ? t('settings.trialEndsToday') : tc('settings.trialLeft', subscription.trial_days_left)}
					{:else if subscription.status === 'premium'}
						{t('settings.planPremiumDetail')}
					{:else}
						{t('settings.planFreeDetail')}
					{/if}
				</div>
			</div>
			<span class="chevron">›</span>
		</button>
		<div class="row-divider"></div>
		<!-- Onboarding -->
		<button class="settings-row" onclick={() => goto('/onboarding')}>
			<div class="icon-box">🧭</div>
			<div class="row-content">
				<div class="row-label">{t('settings.onboarding')}</div>
				<div class="row-detail">{t('settings.onboardingDetail')}</div>
			</div>
			<span class="chevron">›</span>
		</button>
	</div>
</div>

<!-- ── Group: Cuenta ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">{t('settings.group.account')}</div>
	<div class="settings-group">
		<div class="settings-row" style="cursor:default;">
			<div class="icon-box">✉️</div>
			<div class="row-content">
				<div class="row-label">{auth.user?.email ?? ''}</div>
				<div class="row-detail">{t('settings.signedIn')}</div>
			</div>
		</div>
		<div class="row-divider"></div>
		<button class="settings-row" onclick={logout} style="cursor:pointer;">
			<div class="icon-box" style="background:oklch(55% 0.23 25 / 0.15);">→</div>
			<div class="row-content">
				<div class="row-label" style="color:oklch(75% 0.2 25);">{t('settings.logout')}</div>
			</div>
		</button>
		<div class="row-divider"></div>
		<button class="settings-row" onclick={() => { showDeleteModal = true; deleteConfirmText = ''; }} style="cursor:pointer;">
			<div class="icon-box" style="background:oklch(40% 0.2 25 / 0.2);">🗑️</div>
			<div class="row-content">
				<div class="row-label" style="color:oklch(65% 0.2 25);">{t('settings.deleteAccount')}</div>
				<div class="row-detail">{t('settings.deleteAccountDetail')}</div>
			</div>
		</button>
	</div>
</div>

<!-- ── Group: Legal ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">{t('settings.group.legal')}</div>
	<div class="settings-group">
		<button class="settings-row" onclick={() => goto('/privacy')}>
			<div class="icon-box">🔒</div>
			<div class="row-content">
				<div class="row-label">{t('settings.privacy')}</div>
				<div class="row-detail">{t('settings.privacyDetail')}</div>
			</div>
			<span class="chevron">›</span>
		</button>
		<div class="row-divider"></div>
		<button class="settings-row" onclick={() => goto('/terms')}>
			<div class="icon-box">📜</div>
			<div class="row-content">
				<div class="row-label">{t('settings.terms')}</div>
				<div class="row-detail">{t('settings.termsDetail')}</div>
			</div>
			<span class="chevron">›</span>
		</button>
	</div>
</div>

<!-- ── Modal eliminar cuenta ── -->
{#if showDeleteModal}
	<div style="position:fixed; inset:0; background:rgba(0,0,0,0.75); z-index:1000; display:flex; align-items:center; justify-content:center; padding:1.5rem;" onclick={() => showDeleteModal = false}>
		<div style="background:#0f1520; border:1px solid rgba(255,255,255,0.1); border-radius:20px; padding:1.5rem; width:100%; max-width:360px;" onclick={(e) => e.stopPropagation()}>
			<div style="font-size:2rem; text-align:center; margin-bottom:0.75rem;">⚠️</div>
			<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.5rem; text-align:center;">{t('settings.deleteAccount')}</h2>
			<p style="font-size:0.8125rem; color:rgba(255,255,255,0.6); margin:0 0 1.25rem; text-align:center; line-height:1.5;">
				{@html t('settings.deleteWarning')}
			</p>
			<p style="font-size:0.75rem; color:rgba(255,255,255,0.5); margin:0 0 0.5rem;">{t('settings.deleteConfirmPre')} <strong style="color:#fff;">{t('settings.deleteConfirmWord')}</strong> {t('settings.deleteConfirmPost')}</p>
			<input
				bind:value={deleteConfirmText}
				placeholder={t('settings.deleteConfirmWord')}
				style="width:100%; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); border-radius:12px; padding:0.75rem; color:#fff; font-family:inherit; font-size:0.875rem; box-sizing:border-box; margin-bottom:1rem; outline:none;"
			/>
			<div style="display:flex; gap:0.75rem;">
				<button onclick={() => showDeleteModal = false}
					style="flex:1; padding:0.75rem; border-radius:12px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.06); color:rgba(255,255,255,0.7); font-family:inherit; font-size:0.875rem; cursor:pointer; box-shadow:none;">
					{t('common.cancel')}
				</button>
				<button onclick={deleteAccount}
					disabled={deleteConfirmText !== t('settings.deleteConfirmWord') || deletingAccount}
					style="flex:1; padding:0.75rem; border-radius:12px; border:none; background:{deleteConfirmText === t('settings.deleteConfirmWord') ? 'oklch(50% 0.22 25)' : 'rgba(255,255,255,0.05)'}; color:{deleteConfirmText === t('settings.deleteConfirmWord') ? '#fff' : 'rgba(255,255,255,0.3)'}; font-family:inherit; font-size:0.875rem; font-weight:700; cursor:{deleteConfirmText === t('settings.deleteConfirmWord') ? 'pointer' : 'not-allowed'}; transition:background 0.2s; box-shadow:none;">
					{deletingAccount ? t('settings.deleting') : t('common.delete')}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Ko-fi -->
<div style="text-align:center; margin-top:1rem; padding-bottom:0.5rem;">
	<a href="https://ko-fi.com/Z8Z81OW7UV" target="_blank" rel="noopener noreferrer"
		style="display:inline-flex; align-items:center; gap:0.4rem; font-size:0.75rem; color:rgba(255,255,255,0.45); text-decoration:none; padding:0.35rem 0.875rem; border-radius:99px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.03);">
		{t('settings.kofi')}
	</a>
</div>

<div style="text-align:center; margin-top:0.5rem; color:rgba(255,255,255,0.25); font-size:0.6875rem; padding-bottom:6rem;">v{APP_VERSION}</div>

<style>
	
	.group-label {
		font-size: 0.625rem;
		letter-spacing: 0.12em;
		color: rgba(255,255,255,0.45);
		text-transform: uppercase;
		font-weight: 700;
		padding: 0 0.375rem 0.5rem;
	}
	.group-hint {
		font-size: 0.6875rem;
		line-height: 1.45;
		color: rgba(255,255,255,0.35);
		padding: 0.5rem 0.375rem 0;
	}
	.settings-group {
		background: rgba(255,255,255,0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 18px;
		overflow: hidden;
	}
	.settings-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.875rem;
		width: 100%;
		background: none;
		border: none;
		box-shadow: none;
		color: #fff;
		font-family: inherit;
		text-align: left;
	}
	.row-divider {
		height: 1px;
		background: rgba(255,255,255,0.05);
		margin: 0 0.875rem;
	}
	.icon-box {
		width: 32px;
		height: 32px;
		border-radius: 10px;
		background: rgba(255,255,255,0.05);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.875rem;
		flex-shrink: 0;
	}
	.row-content {
		flex: 1;
		min-width: 0;
	}
	.row-label {
		font-size: 0.8125rem;
		font-weight: 600;
		color: #fff;
	}
	.row-detail {
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.45);
		margin-top: 0.125rem;
	}
	.rank-chip,
	.rank-move,
	.rank-gap {
		display: inline-flex;
		align-items: center;
		padding: 0.05rem 0.4rem;
		border-radius: 99px;
		font-weight: 700;
		white-space: nowrap;
		font-variant-numeric: tabular-nums;
	}
	/* The position is information: same place, same size, whatever it says. The
	   medal tint is the reward, and only lands when the podium was earned. */
	.rank-chip {
		margin-left: 0.4rem;
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.55);
		background: rgba(255,255,255,0.07);
	}
	/* The chip is an inline-flex row, so the gap has to be a margin: whitespace
	   between flex items is dropped. */
	.rank-chip .of { font-weight: 400; color: rgba(255,255,255,0.32); margin-left: 0.25rem; }
	.rank-chip.medal-1 { color: oklch(88% 0.15 95); background: oklch(88% 0.15 95 / 0.16); }
	.rank-chip.medal-2 { color: rgba(255,255,255,0.75); background: rgba(255,255,255,0.11); }
	.rank-chip.medal-3 { color: oklch(78% 0.12 55); background: oklch(78% 0.12 55 / 0.16); }
	.icon-box.medal-1 { background: oklch(88% 0.15 95 / 0.15); }
	.icon-box.medal-2 { background: rgba(255,255,255,0.11); }
	.icon-box.medal-3 { background: oklch(70% 0.12 55 / 0.16); }
	/* Only rises are chipped, so this is always the good-news green. */
	.rank-move {
		margin-left: 0.35rem;
		color: oklch(82% 0.16 165);
		background: oklch(82% 0.16 165 / 0.15);
	}
	.rank-gap {
		margin: 0 0.3rem;
		color: oklch(82% 0.14 70);
		background: oklch(82% 0.14 70 / 0.15);
	}
	.chevron {
		color: rgba(255,255,255,0.3);
		font-size: 0.875rem;
		flex-shrink: 0;
	}
	.row-sub {
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.45);
		margin-top: 0.125rem;
	}
	.row-arrow {
		color: rgba(255,255,255,0.3);
		font-size: 0.875rem;
		flex-shrink: 0;
	}
	.toggle-btn {
		position: relative;
		width: 40px;
		height: 24px;
		border-radius: 99px;
		border: 1px solid;
		box-shadow: none;
		cursor: pointer;
		flex-shrink: 0;
		padding: 0;
		transition: background 0.2s, border-color 0.2s;
	}
	.toggle-knob {
		position: absolute;
		top: 2px;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: linear-gradient(135deg, #fff, oklch(85% 0.1 165));
		box-shadow: 0 2px 5px rgba(0,0,0,0.3);
		transition: left 0.2s;
		display: block;
	}
	/* Toggle-thumb variant (CSS-driven, no inline style needed) */
	.toggle-thumb {
		position: absolute;
		top: 2px;
		left: 2px;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: linear-gradient(135deg, #fff, oklch(85% 0.1 165));
		box-shadow: 0 2px 5px rgba(0,0,0,0.3);
		transition: left 0.2s;
		display: block;
	}
	.toggle-on .toggle-thumb { left: 18px; }
	.toggle-btn:not(.toggle-on) { background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.15); }
	.toggle-btn.toggle-on { background: var(--primary); border-color: var(--primary); }
	.toggle-sm { width: 34px; height: 20px; }
	.toggle-sm .toggle-thumb { width: 14px; height: 14px; top: 2px; }
	.toggle-sm.toggle-on .toggle-thumb { left: 16px; }

	/* Notification rows */
	.notif-subsection {
		border-top: 1px solid rgba(255,255,255,0.06);
		padding: 0.625rem 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}
	.notif-sub-label {
		font-size: 0.65rem;
		font-weight: 700;
		color: oklch(55% 0.05 260);
		text-transform: uppercase;
		letter-spacing: 0.07em;
		margin-bottom: 0.1rem;
	}
	.notif-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.notif-emoji { font-size: 1rem; flex-shrink: 0; width: 1.25rem; text-align: center; }
	.notif-meal-label { flex: 1; font-size: 0.8rem; color: rgba(255,255,255,0.85); min-width: 0; }
	.notif-hint { font-size: 0.7rem; color: oklch(55% 0.05 260); }
	.notif-always {
		font-size: 0.68rem;
		font-weight: 700;
		color: oklch(65% 0.15 160);
		background: oklch(65% 0.15 160 / 0.1);
		border: 1px solid oklch(65% 0.15 160 / 0.2);
		border-radius: 99px;
		padding: 0.1rem 0.4rem;
	}
	.time-input {
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.12);
		border-radius: 8px;
		color: #fff;
		font-family: inherit;
		font-size: 0.75rem;
		padding: 0.2rem 0.4rem;
		width: 5.5rem;
		flex-shrink: 0;
	}
	.time-input:disabled { opacity: 0.35; }
	.time-input::-webkit-calendar-picker-indicator { filter: invert(1); opacity: 0.5; }
	.hour-input {
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.12);
		border-radius: 8px;
		color: #fff;
		font-family: inherit;
		font-size: 0.8rem;
		padding: 0.2rem 0.4rem;
		width: 3rem;
		text-align: center;
		flex-shrink: 0;
	}
	.tz-select {
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.12);
		border-radius: 8px;
		color: #fff;
		font-family: inherit;
		font-size: 0.75rem;
		padding: 0.2rem 0.4rem;
		flex: 1;
		min-width: 0;
		cursor: pointer;
	}
	.tz-select option { background: #1a1f2e; color: #fff; }

	/* PRO badge in settings rows */
	.pro-badge-row {
		font-size: 0.5625rem;
		font-weight: 800;
		letter-spacing: 0.06em;
		padding: 0.2rem 0.5rem;
		border-radius: 99px;
		background: linear-gradient(90deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		flex-shrink: 0;
	}
</style>
