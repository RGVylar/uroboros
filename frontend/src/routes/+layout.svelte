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
	import { page } from '$app/state';

	let { children } = $props();

	$effect(() => {
		if (auth.isLoggedIn) {
			pendingFriends.start();
		} else {
			pendingFriends.stop();
		}
	});

	// Móvil: 4 items + FAB en el centro
	type NavLink = { href: string; label: string; icon: string };
	type FabSlot = { fab: true };
	type NavItem = NavLink | FabSlot;

	const mobileNav: NavItem[] = [
		{ href: '/', label: 'Diario', icon: '📋' },
		{ href: '/history', label: 'Historial', icon: '📅' },
		{ fab: true },
		{ href: '/recipes', label: 'Recetas', icon: '🍳' },
		{ href: '/settings', label: 'Ajustes', icon: '⚙️' },
	];

	// Escritorio: todos los ítems en el sidebar
	const sidebarNav: NavLink[] = [
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
				<div class="sidebar-logo">U</div>
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
{#if auth.isLoggedIn}
	<nav class="bottom" aria-label="Navegación principal">
		{#each mobileNav as item}
			{#if 'fab' in item}
				<a href="/add" class="nav-fab-link" aria-label="Añadir comida">
					<span class="nav-fab-icon" aria-hidden="true">＋</span>
				</a>
			{:else}
				{@const link = item as NavLink}
				<a
					href={link.href}
					class:active={page.url.pathname === link.href}
					aria-current={page.url.pathname === link.href ? 'page' : undefined}
				>
					<span class="icon" aria-hidden="true">{link.icon}</span>
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

	/* ── FAB en la nav ── */
	.nav-fab-link {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 46px;
		height: 46px;
		border-radius: 50%;
		background: linear-gradient(180deg, var(--primary), var(--primary-dim));
		box-shadow:
			0 1px 0 rgba(255,255,255,0.3) inset,
			0 8px 22px -4px var(--primary-glow);
		margin: 0 0.2rem;
		flex-shrink: 0;
		transition: transform 0.15s, box-shadow 0.18s;
		/* Reset herencia de nav.bottom a */
		padding: 0 !important;
		min-width: unset !important;
		flex-direction: row !important;
		gap: 0 !important;
		font-size: unset !important;
		color: var(--primary-ink) !important;
	}
	.nav-fab-link:hover {
		transform: translateY(-2px);
		box-shadow: 0 1px 0 rgba(255,255,255,0.35) inset, 0 14px 30px -6px var(--primary-glow);
	}
	.nav-fab-link:active { transform: translateY(0); }
	.nav-fab-icon {
		font-size: 1.4rem;
		font-weight: 800;
		line-height: 1;
	}

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
