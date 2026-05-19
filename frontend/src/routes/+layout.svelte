<!--
  Layout con sidebar en escritorio (≥900px) y bottom-nav pill en móvil.
  - Sidebar: 8 ítems (incluye Ejercicios, Peso, Medidas, Amigos).
  - Nav móvil: 4 ítems + FAB verde centrado.
  - Sin cambios de lógica, stores ni rutas.
-->
<script lang="ts">
	import '../app.css';
	import { auth } from '$lib/stores/auth.svelte';
	import { pendingFriends } from '$lib/stores/friends.svelte';
	import { connectivity } from '$lib/stores/connectivity.svelte';
	import { syncQueue } from '$lib/stores/sync-queue.svelte';
	import { pushStore } from '$lib/stores/push.svelte';
	import { page } from '$app/state';
	import Toast from '$lib/components/Toast.svelte';

	let { children } = $props();

	$effect(() => {
		if (auth.isLoggedIn) {
			pendingFriends.start();
			pushStore.init();
		} else {
			pendingFriends.stop();
		}
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

	// Móvil: 4 items + FAB en el centro
	type NavLink = { href: string; label: string };
	type FabSlot = { fab: true };
	type NavItem = NavLink | FabSlot;

	const mobileNav: NavItem[] = [
		{ href: '/', label: 'Diario' },
		{ href: '/history', label: 'Historial' },
		{ fab: true },
		{ href: '/recipes', label: 'Recetas' },
		{ href: '/settings', label: 'Ajustes' },
	];

	// Escritorio: todos los ítems en el sidebar (con emoji como icono)
	const sidebarNav = [
		{ href: '/', label: 'Diario', icon: '📋' },
		{ href: '/history', label: 'Historial', icon: '📅' },
		{ href: '/recipes', label: 'Recetas', icon: '🍳' },
		{ href: '/exercises', label: 'Ejercicios', icon: '💪' },
		{ href: '/weight', label: 'Peso', icon: '⚖️' },
		{ href: '/measurements', label: 'Medidas', icon: '📏' },
		{ href: '/friends', label: 'Amigos', icon: '👥' },
		{ href: '/settings', label: 'Ajustes', icon: '⚙️' },
	];

	function isActive(href: string): boolean {
		const p = page.url.pathname;
		return href === '/' ? p === '/' : p === href || p.startsWith(href + '/');
	}
</script>

{#if auth.isLoggedIn}
	<div class="app-shell">
		<!-- Sidebar (solo visible en escritorio ≥900px) -->
		<aside class="sidebar" aria-label="Navegación lateral">
			<div class="sidebar-brand">
				<img src="/logo.png" alt="uroboros" class="sidebar-logo" />
				<div class="sidebar-brand-text">
					<span class="sidebar-app-name">uroboros</span>
					<span class="sidebar-user-name">
						Hola, {auth.user?.name?.split(' ')[0] ?? 'tú'}
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
							<span class="sidebar-badge" aria-label="{pendingFriends.count} solicitudes">{pendingFriends.count}</span>
						{/if}
					</a>
				{/each}
			</nav>
		</aside>

		<!-- Contenido principal -->
		<div class="main-content">
			{#if connectivity.isOffline}
				<div class="offline-strip" role="alert" aria-live="assertive">
					<span>⚽</span>
					<span>Sin conexión — probablemente es el fútbol</span>
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

{#if auth.isLoggedIn}
	<nav class="bottom" aria-label="Navegación principal">
		{#each mobileNav as item}
			{#if 'fab' in item}
				<!-- FAB centrado, flota por encima del pill -->
				<a href="/add" class="nav-fab-link" aria-label="Añadir comida">
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
							<path d="M12 3C8 3 5 6 5 9c0 2.4 1.4 4.5 3.5 5.6V17h7v-2.4C17.6 13.5 19 11.4 19 9c0-3-3-6-7-6z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
							<path d="M9 17h6v1a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1v-1z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
						</svg>
					{:else if link.href === '/settings'}
						<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
							<circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
							<path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
						</svg>
					{/if}
					<span>{link.label}</span>
					{#if link.href === '/settings' && pendingFriends.count > 0}
						<span class="nav-badge" aria-label="{pendingFriends.count} solicitudes pendientes">
							{pendingFriends.count}
						</span>
					{/if}
				</a>
			{/if}
		{/each}
	</nav>
{/if}

<style>
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
</style>
