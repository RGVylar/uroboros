<!--
  Layout con sidebar en escritorio (≥900px) y bottom-nav pill en móvil.
  - Sidebar: 8 ítems (incluye Ejercicios, Peso, Medidas, Amigos).
  - Nav móvil: 4 ítems + FAB verde centrado.
  - Sin cambios de lógica, stores ni rutas.
-->
<script lang="ts">
	import '../app.css';
	import { untrack, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import type { User } from '$lib/types';
	import { auth } from '$lib/stores/auth.svelte';
	import { pendingFriends } from '$lib/stores/friends.svelte';
	import { connectivity } from '$lib/stores/connectivity.svelte';
	import { syncQueue } from '$lib/stores/sync-queue.svelte';
	import { pushStore, isNativeApp } from '$lib/stores/push.svelte';
	import { subscription } from '$lib/stores/subscription.svelte';
	import { page } from '$app/state';
	import Toast from '$lib/components/Toast.svelte';
	import ChangelogModal from '$lib/components/ChangelogModal.svelte';
	import { APP_VERSION, UPDATE_URL, getSeen, type ChangelogResponse, type ReleaseNote, type UpdateInfo } from '$lib/changelog';
	import { t, i18n } from '$lib/i18n/index.svelte';

	let { children } = $props();

	// ── Deep links desde los widgets de Android ──────────────────────────────
	// uroboros://add        -> pantalla de añadir
	// uroboros://add?scan=1 -> añadir con el escáner QR/barras abierto de golpe
	// Navegamos con el router de la SPA (goto) para no recargar la webview.
	function openWidgetTarget(url: string | undefined | null) {
		if (!url || !url.startsWith('uroboros://')) return;
		const rest = url.slice('uroboros://'.length); // "add?scan=1"
		const qIdx = rest.indexOf('?');
		const path = (qIdx === -1 ? rest : rest.slice(0, qIdx)).replace(/\/+$/, '');
		const search = qIdx === -1 ? '' : rest.slice(qIdx);
		goto('/' + path + search);
	}

	onMount(async () => {
		if (!isNativeApp) return;
		const { App } = await import('@capacitor/app');
		// App ya abierta (MainActivity es singleTask -> onNewIntent)
		App.addListener('appUrlOpen', (data) => openWidgetTarget(data?.url));
		// Arranque en frío: la URL con la que el widget lanzó la app
		const launch = await App.getLaunchUrl();
		openWidgetTarget(launch?.url);
	});

	// Solo debe depender de auth.isLoggedIn: sin untrack, pushStore.init()
	// lee $state que él mismo escribe y el efecto se re-ejecutaba, duplicando
	// las llamadas a /friends/pending/count y /users/me/subscription.
	$effect(() => {
		const logged = auth.isLoggedIn;
		untrack(() => {
			if (logged) {
				connectivity.ping();
				pendingFriends.start();
				pushStore.init();
				subscription.load();
				// The user copy in localStorage is only written at login, so it goes
				// stale when it changes on another device (picking an avatar on the
				// phone wouldn't show up on the desktop). Refresh it from the server;
				// on failure we keep the cached copy so offline still works.
				api.get<User>('/auth/me').then((u) => auth.updateUser(u)).catch(() => {});
			} else {
				pendingFriends.stop();
			}
		});
	});

	// Drain offline write queue when connectivity is restored
	let wasOffline = false;
	$effect(() => {
		const isOffline = connectivity.isOffline;
		if (wasOffline && !isOffline && syncQueue.count > 0) {
			syncQueue.drain();
		}
		wasOffline = isOffline;
	});

	// Changelog + update nudge — served from the DB, fetched once after login.
	// The server decides what to show from the version we report (APP_VERSION),
	// the last version we dismissed (getSeen), and the user's opt-out flag.
	let changelogNotes = $state<ReleaseNote[]>([]);
	let showChangelog = $state(false);
	let updateInfo = $state<UpdateInfo | null>(null);
	let updateDismissed = $state(false);
	$effect(() => {
		if (!auth.isLoggedIn) return;
		untrack(() => {
			const q = `current=${encodeURIComponent(APP_VERSION)}&seen=${encodeURIComponent(getSeen())}&lang=${i18n.locale}`;
			api.get<ChangelogResponse>(`/release-notes?${q}`)
				.then((res) => {
					changelogNotes = res.news;
					showChangelog = res.news.length > 0;
					updateInfo = res.update;
				})
				.catch(() => {});
		});
	});

	// App update detection via service worker controllerchange
	let updateAvailable = $state(false);
	$effect(() => {
		if (!('serviceWorker' in navigator)) return;
		// Only show banner on updates, not on first SW activation
		const hadController = !!navigator.serviceWorker.controller;
		navigator.serviceWorker.addEventListener('controllerchange', () => {
			if (hadController) updateAvailable = true;
		});
	});

	// Móvil: 4 items + FAB en el centro
	type NavLink = { href: string; label: string; pro?: boolean };
	type FabSlot = { fab: true };
	type NavItem = NavLink | FabSlot;

	// $derived, no const: al cambiar de idioma en Ajustes la nav se retraduce sola.
	let mobileNav = $derived<NavItem[]>([
		{ href: '/', label: t('nav.diary') },
		{ href: '/history', label: t('nav.history'), pro: true },
		{ fab: true },
		{ href: '/recipes', label: t('nav.recipes') },
		{ href: '/settings', label: t('nav.settings') },
	]);

	// Escritorio: todos los ítems en el sidebar (con emoji como icono)
	let sidebarNav = $derived([
		{ href: '/', label: t('nav.diary'), icon: '📋' },
		{ href: '/history', label: t('nav.history'), icon: '📅', pro: true },
		{ href: '/recipes', label: t('nav.recipes'), icon: '📖' },
		{ href: '/exercises', label: t('nav.exercises'), icon: '💪', pro: true },
		{ href: '/weight', label: t('nav.weight'), icon: '⚖️' },
		{ href: '/measurements', label: t('nav.measurements'), icon: '📏', pro: true },
		{ href: '/friends', label: t('nav.friends'), icon: '👥' },
		{ href: '/settings', label: t('nav.settings'), icon: '⚙️' },
	]);

	function isActive(href: string): boolean {
		const p = page.url.pathname;
		return href === '/' ? p === '/' : p === href || p.startsWith(href + '/');
	}

	const NO_NAV_ROUTES = ['/onboarding', '/premium'];
	let hideNav = $derived(NO_NAV_ROUTES.some(r => page.url.pathname.startsWith(r)));
</script>

{#if auth.isLoggedIn}
	<div class="app-shell">
		<!-- Sidebar (solo visible en escritorio ≥900px) -->
		<aside class="sidebar" aria-label={t('nav.aria.sidebar')}>
			<div class="sidebar-brand">
				<img src="/logo-192.png" alt="uroboros" class="sidebar-logo" />
				<div class="sidebar-brand-text">
					<span class="sidebar-app-name">uroboros</span>
					<span class="sidebar-user-name">
						{t('layout.greeting', { name: auth.user?.name?.split(' ')[0] ?? t('layout.you') })}
					</span>
				</div>
			</div>

			<nav class="sidebar-nav">
				{#each sidebarNav as item}
					<a
						href={item.href}
						class:active={isActive(item.href)}
						aria-current={isActive(item.href) ? 'page' : undefined}
					>
						<span class="icon" aria-hidden="true">{item.icon}</span>
						<span>{item.label}</span>
						{#if item.href === '/friends' && pendingFriends.count > 0}
							<span class="sidebar-badge" aria-label={t('nav.aria.requests', { count: pendingFriends.count })}>{pendingFriends.count}</span>
						{:else if item.pro && !subscription.is_premium}
							<span class="pro-badge">PRO</span>
						{/if}
					</a>
				{/each}
			</nav>
		</aside>

		<!-- Contenido principal -->
		<div class="main-content">
			{#if updateInfo && !updateDismissed}
				<!-- Server-driven update nudge: teaser of what the newer version brings. -->
				<div class="update-nudge" role="alert">
					<div class="update-nudge-body">
						<div class="update-nudge-title">{t('layout.update.new', { version: updateInfo.version, title: updateInfo.title })}</div>
						{#if updateInfo.teaser.length}
							<div class="update-nudge-teaser">
								{updateInfo.teaser.join(' · ')}{#if updateInfo.more > 0}{t('layout.update.more', { count: updateInfo.more })}{/if}
							</div>
						{/if}
					</div>
					<div class="update-nudge-actions">
						{#if isNativeApp}
							<!-- Android: el frontend va empaquetado en el APK; recargar no sirve. -->
							<a class="update-nudge-cta" href={UPDATE_URL} target="_blank" rel="noopener noreferrer">{t('layout.update.cta')}</a>
						{:else}
							<!-- Web: recargar ya trae el bundle nuevo tras un deploy. -->
							<button class="update-nudge-cta" onclick={() => window.location.reload()}>{t('layout.update.cta')}</button>
						{/if}
						<button class="update-nudge-later" aria-label={t('layout.update.later')} onclick={() => updateDismissed = true}>✕</button>
					</div>
				</div>
			{:else if updateAvailable}
				<div class="update-strip" role="alert">
					<span>{t('layout.update.available')}</span>
					<button onclick={() => window.location.reload()}>{t('layout.update.cta')}</button>
				</div>
			{/if}
			{#if connectivity.isOffline}
				<div class="offline-strip" role="alert" aria-live="assertive">
					<span>⚽</span>
					<span>{t('layout.offline')}</span>
				</div>
			{/if}
			<div class="container page">
				{@render children()}
			</div>
		</div>
	</div>
{:else}
	<div class="container page">
		{@render children()}
	</div>
{/if}

<!-- Nav móvil (pill flotante) — oculta en escritorio vía CSS -->
<Toast />

{#if showChangelog}
	<ChangelogModal notes={changelogNotes} onclose={() => showChangelog = false} />
{/if}

{#if auth.isLoggedIn && !hideNav}
	<nav class="bottom" aria-label={t('nav.aria.main')}>
		{#each mobileNav as item}
			{#if 'fab' in item}
				<!-- FAB centrado, flota por encima del pill -->
				<a href="/add" class="nav-fab-link" aria-label={t('nav.aria.addFood')}>
					<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
						<path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
					</svg>
				</a>
			{:else}
				{@const link = item as NavLink}
				<a
					href={link.href}
					class:active={page.url.pathname === link.href}
					aria-current={page.url.pathname === link.href ? 'page' : undefined}
				>
					<!-- SVG icons por ruta -->
					{#if link.href === '/'}
						<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
							<rect x="4" y="4" width="16" height="16" rx="4"
								fill={page.url.pathname === '/' ? 'oklch(85% 0.17 160 / 0.2)' : 'none'}
								stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
							<path d="M8 10h8M8 14h5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
						</svg>
					{:else if link.href === '/history'}
						<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
							<circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
							<path d="M12 8v4l3 2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
						</svg>
					{:else if link.href === '/recipes'}
						<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
							<path d="M12 7c-1.6-1.4-4-2-7-2v12c3 0 5.4.6 7 2c1.6-1.4 4-2 7-2V5c-3 0-5.4.6-7 2z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
							<path d="M12 7v12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
						</svg>
					{:else if link.href === '/settings'}
						<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
							<circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
							<path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
						</svg>
					{/if}
					<span>{link.label}</span>
					{#if link.href === '/settings' && pendingFriends.count > 0}
						<span class="nav-badge" aria-label={t('nav.aria.pendingRequests', { count: pendingFriends.count })}>
							{pendingFriends.count}
						</span>
					{:else if link.pro && !subscription.is_premium}
						<span class="pro-badge">PRO</span>
					{/if}
				</a>
			{/if}
		{/each}
	</nav>
{/if}

<style>
	/* ── Strip de actualización disponible ── */
	.update-strip {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		padding: 0.35rem 1rem;
		background: oklch(28% 0.06 160 / 0.9);
		border-bottom: 1px solid oklch(55% 0.18 160 / 0.4);
		font-size: 0.72rem;
		font-weight: 600;
		color: oklch(88% 0.16 160);
		letter-spacing: 0.01em;
		animation: strip-in 0.25s ease;
	}
	.update-strip button {
		padding: 0.2rem 0.65rem;
		border-radius: 99px;
		border: 1px solid oklch(72% 0.2 160 / 0.6);
		background: oklch(72% 0.2 160 / 0.15);
		color: oklch(88% 0.16 160);
		font-size: 0.68rem;
		font-weight: 700;
		cursor: pointer;
		font-family: inherit;
		transition: background 0.15s;
	}
	.update-strip button:hover {
		background: oklch(72% 0.2 160 / 0.3);
	}

	/* ── Nudge de actualización (data-driven, con teaser) ── */
	.update-nudge {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		padding: 0.5rem 1rem;
		background: oklch(28% 0.06 160 / 0.92);
		border-bottom: 1px solid oklch(55% 0.18 160 / 0.4);
		animation: strip-in 0.25s ease;
	}
	.update-nudge-body { min-width: 0; }
	.update-nudge-title {
		font-size: 0.74rem;
		font-weight: 700;
		color: oklch(90% 0.15 160);
		letter-spacing: 0.01em;
	}
	.update-nudge-teaser {
		font-size: 0.66rem;
		color: oklch(78% 0.08 160);
		margin-top: 0.1rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.update-nudge-actions { display: flex; align-items: center; gap: 0.4rem; flex-shrink: 0; }
	.update-nudge-cta {
		padding: 0.25rem 0.7rem;
		border-radius: 99px;
		border: 1px solid oklch(72% 0.2 160 / 0.6);
		background: oklch(72% 0.2 160 / 0.18);
		color: oklch(90% 0.15 160);
		font-size: 0.68rem;
		font-weight: 700;
		cursor: pointer;
		font-family: inherit;
		transition: background 0.15s;
		text-decoration: none;
		display: inline-block;
		white-space: nowrap;
	}
	.update-nudge-cta:hover { background: oklch(72% 0.2 160 / 0.32); }
	.update-nudge-later {
		background: none;
		border: none;
		box-shadow: none;
		color: oklch(80% 0.05 160 / 0.7);
		font-size: 0.7rem;
		cursor: pointer;
		padding: 0.2rem 0.35rem;
		line-height: 1;
	}

	/* ── Strip sin conexión (dentro del main-content, no flotante) ── */
	.offline-strip {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.4rem;
		padding: 0.3rem 1rem;
		background: oklch(28% 0.04 260 / 0.85);
		border-bottom: 1px solid oklch(45% 0.06 260 / 0.4);
		font-size: 0.72rem;
		font-weight: 600;
		color: oklch(80% 0.05 260);
		letter-spacing: 0.01em;
		animation: strip-in 0.25s ease;
	}
	@keyframes strip-in {
		from { opacity: 0; transform: translateY(-6px); }
		to   { opacity: 1; transform: translateY(0); }
	}

	/* ── Badge móvil ── */
	.nav-badge {
		position: absolute;
		top: 2px;
		right: 6px;
		background: var(--danger);
		color: #fff;
		border-radius: 99px;
		font-size: 0.55rem;
		font-weight: 800;
		padding: 0.08rem 0.35rem;
		line-height: 1.4;
		pointer-events: none;
		box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
	}
	nav.bottom a { position: relative; }

	/* ── FAB en la nav (slot central del grid) ── */
	.nav-fab-link {
		justify-self: center;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 56px;
		height: 56px;
		border-radius: 50%;
		background: linear-gradient(180deg, var(--primary), var(--primary-dim));
		box-shadow:
			0 1px 0 rgba(255,255,255,0.3) inset,
			0 8px 22px -4px var(--primary-glow);
		margin-top: -22px;
		flex-shrink: 0;
		transition: transform 0.15s, box-shadow 0.18s;
		/* Reset herencia de nav.bottom a */
		padding: 0 !important;
		flex-direction: row !important;
		gap: 0 !important;
		font-size: unset !important;
		color: var(--primary-ink) !important;
		border-radius: 50% !important;
	}
	.nav-fab-link:hover {
		transform: translateY(-3px);
		box-shadow: 0 1px 0 rgba(255,255,255,0.35) inset, 0 14px 30px -6px var(--primary-glow);
	}
	.nav-fab-link:active { transform: translateY(0); }

	/* ── Badge sidebar ── */
	.sidebar-badge {
		margin-left: auto;
		background: var(--danger);
		color: #fff;
		border-radius: 99px;
		font-size: 0.58rem;
		font-weight: 800;
		padding: 0.1rem 0.4rem;
		line-height: 1.4;
	}

	/* ── Badge PRO ── */
	.pro-badge {
		margin-left: auto;
		background: linear-gradient(90deg, oklch(72% 0.2 170), oklch(80% 0.18 200));
		color: #041010;
		border-radius: 99px;
		font-size: 0.52rem;
		font-weight: 900;
		padding: 0.1rem 0.4rem;
		line-height: 1.4;
		letter-spacing: 0.04em;
		flex-shrink: 0;
	}
	/* En bottom nav el badge va posicionado arriba a la derecha */
	.bottom a .pro-badge {
		position: absolute;
		top: 2px;
		right: 2px;
		margin-left: 0;
		font-size: 0.45rem;
		padding: 0.05rem 0.3rem;
	}
</style>
